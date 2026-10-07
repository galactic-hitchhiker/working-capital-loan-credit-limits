"""Discover and download SEC 8-K Item 2.04 filings for OpenAI Batch review.

This gathers source documents and metadata without assigning event labels.
It deliberately does not alter the existing inventory, panel or study config.

Run from the repository root:
    .venv/bin/python -m mcf.enrichment.item204.discover [parameters]

Example:
    .venv/bin/python -m mcf.enrichment.item204.discover \
        --submissions ../dataset/submissions \
        --output-dir results/sec/item204 \
        --start 2010-01-01 \
        --cutoff 2026-09-07 \
        --user-agent "My Name fake.email@gmail.com" \
        --limit 10


Parameters:
    --submissions PATH: Required directory of downloaded SEC submissions JSON files.
    --output-dir PATH: Required destination for filings.jsonl/CSV, HTML cache and audit.
    --start YYYY-MM-DD: Inclusive filing-date lower bound (default: no lower bound).
    --cutoff YYYY-MM-DD: Exclusive filing-date upper bound (default: no upper bound).
    --user-agent TEXT: SEC identification with contact email (default: SEC_USER_AGENT).
    --interval SECONDS: SEC request spacing, at least 0.1 (default: 0.25).
    --limit N: Positive pilot filing limit; omit to discover all matching filings.
    --offline: Parse cached HTML only; do not download missing filings (default: off).
    --discover-only: Write the metadata inventory without downloading/parsing HTML (default: off).
    -h, --help: Show command usage and exit.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from mcf.data.sec import filing_rows

DISCOVERY_VERSION = "item204-discovery-v1"
ITEM_HEADING = re.compile(r"\bitem\s+(\d[.]\d{2})\b", re.IGNORECASE)


def extract_item_204(html):
    """Use Beautiful Soup to isolate Item 2.04 and discard scripts/hidden facts.

    Repeated headings (for example a table of contents) are resolved by selecting
    the longest section. Missing or short sections require manual review.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for node in soup.find_all(["script", "style", "ix:hidden"]):
        node.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    headings = list(ITEM_HEADING.finditer(text))
    sections = []
    for i, heading in enumerate(headings):
        if heading.group(1) != "2.04":
            continue
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        sections.append(text[heading.end() : end].strip())
    if not sections:
        return "", "missing_item_section"
    section = max(sections, key=len)
    # A pointer to another item is not evidence from that other item's narrative.
    if len(section) < 100:
        return section, "short_or_cross_referenced_section"
    return section, "isolated_item_section"


def has_item(items, item):
    return item in re.split(r"[,;\s]+", str(items))


def iter_item_204(submissions_dir, start=None, cutoff=None):
    """Scan all main submission records and their referenced historical archives."""
    for path in sorted(Path(submissions_dir).glob("CIK*.json")):
        if not re.fullmatch(r"CIK\d{10}\.json", path.name):
            continue
        company = json.loads(path.read_text())
        filings, missing = filing_rows(company, Path(submissions_dir))
        item_103_dates = sorted(
            f["filingDate"]
            for f in filings
            if f["form"] in {"8-K", "8-K/A"} and has_item(f["items"], "1.03")
        )
        for filing in filings:
            if filing["form"] not in {"8-K", "8-K/A"} or not has_item(
                filing["items"], "2.04"
            ):
                continue
            filed = date.fromisoformat(filing["filingDate"])
            if (start and filed < start) or (cutoff and filed >= cutoff):
                continue
            cik = path.stem[3:]
            accession = filing["accessionNumber"]

            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                raise ValueError(f"Invalid accession: {accession}")

            primary = filing["primaryDocument"]

            if not primary or Path(primary).name != primary:
                raise ValueError(f"Invalid primary document: {primary}")

            yield dict(
                company_id=cik,
                entity_name=company.get("name", ""),
                **filing,
                source_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{quote(primary)}",
                same_filing_item_103=has_item(filing["items"], "1.03"),
                prior_or_same_item_103=any(
                    d <= filing["filingDate"] for d in item_103_dates
                ),
                first_recorded_item_103_date=item_103_dates[0]
                if item_103_dates
                else "",
                missing_archives=missing,
            )


def fetch_html(url, cache_path, user_agent, interval, retries=3):
    """Cache successful HTML; serial requests are paced and transient errors retried."""
    if cache_path.exists():
        return cache_path.read_bytes(), "cached"
    for attempt in range(retries + 1):
        time.sleep(interval * (2**attempt))
        try:
            request = Request(
                url, headers={"User-Agent": user_agent, "Accept": "text/html"}
            )
            with urlopen(request, timeout=45) as response:
                content_type = response.headers.get("Content-Type", "")
                payload = response.read()
            if "html" not in content_type.lower() or not payload.strip():
                raise ValueError(f"Unexpected/empty filing response: {content_type}")
            temporary = cache_path.with_suffix(".tmp")
            temporary.write_bytes(payload)
            temporary.replace(cache_path)
            return payload, "downloaded"
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == retries:
                raise
        except (URLError, TimeoutError):
            if attempt == retries:
                raise
    raise RuntimeError("Download retry exhausted")


def run(args):
    """Build a filing inventory while reusing cached HTML; never classify events."""
    if not args.submissions.is_dir():
        raise ValueError(f"Submissions directory does not exist: {args.submissions}")
    if not args.discover_only:
        from bs4 import BeautifulSoup  # Fail before creating partial output.

        if not args.offline and (not args.user_agent or "@" not in args.user_agent):
            raise ValueError(
                "Provide --user-agent 'Name email@example.com' for SEC requests"
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = getattr(args, "html_dir", None) or args.output_dir / "html"
    cache.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    records_path = args.output_dir / "filings.jsonl"
    with records_path.open("w") as output:
        for n, record in enumerate(
            iter_item_204(args.submissions, args.start, args.cutoff), 1
        ):
            if args.limit and n > args.limit:
                break
            record.update(
                status="discovered",
            )
            if not args.discover_only:
                path = (
                    cache / f"{record['company_id']}_{record['accessionNumber']}.html"
                )
                try:
                    if args.offline and not path.exists():
                        raise FileNotFoundError("Filing not present in offline cache")

                    html, record["download_status"] = fetch_html(
                        record["source_url"], path, args.user_agent, args.interval
                    )

                    section, scope = extract_item_204(html)

                    record.update(
                        status="parsed",
                        extraction_status=scope,
                        item_204_text=section,
                        html_sha256=hashlib.sha256(html).hexdigest(),
                        html_path=str(path),
                    )

                except (OSError, ValueError, URLError, TimeoutError) as exc:
                    record.update(status="error", error=str(exc))

            counts[f"status_{record['status']}"] += 1
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(f"Discovered {n} filings: {dict(counts)}", flush=True)

    fields = [
        "company_id",
        "entity_name",
        "filingDate",
        "reportDate",
        "accessionNumber",
        "form",
        "status",
        "same_filing_item_103",
        "prior_or_same_item_103",
        "first_recorded_item_103_date",
        "source_url",
        "error",
    ]

    with (args.output_dir / "filings.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        with records_path.open() as records:
            for line in records:
                writer.writerow(json.loads(line))

    audit = {
        "discovery_version": DISCOVERY_VERSION,
        "counts": dict(counts),
        "start": str(args.start),
        "cutoff": str(args.cutoff),
        "discovery_only": args.discover_only,
        "filings": sum(counts.values()),
        "html_dir": str(cache.resolve()),
        "label_note": "Source inventory only; event labels are assigned by OpenAI Batch.",
    }

    (args.output_dir / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")

    print(json.dumps(audit, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument(
        "--cutoff", type=date.fromisoformat, help="Exclusive filing-date cutoff"
    )
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--limit", type=int, help="Limit a pilot to this many filings")
    parser.add_argument("--offline", action="store_true", help="Parse cached HTML only")
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Inventory metadata without downloading",
    )
    args = parser.parse_args()
    if args.interval < 0.1 or (args.limit is not None and args.limit < 1):
        parser.error("interval must be >= 0.1 seconds and limit must be positive")
    if args.start and args.cutoff and args.start >= args.cutoff:
        parser.error("start must precede cutoff")
    run(args)


if __name__ == "__main__":
    main()
