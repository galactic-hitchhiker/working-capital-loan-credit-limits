"""One-time, resumable review of SEC 8-K Item 2.04 disclosures.

This produces candidate disclosure labels, not verified payment-default labels.
It deliberately does not alter the existing inventory, panel or study config.
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

from sec_data import filing_rows

RULE_VERSION = "item204-v5-modal-may"
# Payment failures must name a financial payment, rather than, for example,
# "failed to make a filing". Acceleration and enforcement are separate events.
PAYMENT_DEFAULT = (
    r"\b(?:failed|failure) to (?:pay (?:the |any |scheduled )?(?:interest|principal|installments?|payments?)|make (?:the |a |any |scheduled )?(?:(?:interest|principal|debt[- ]service) )?payments?)\b",
    r"\b(?:missed|did not make) (?:an? |the |scheduled )?(?:(?:interest|principal) )?payments?\b",
    r"\b(?:payment default|non[- ]?payment|default in (?:the )?payment)\b",
    r"\b(?:principal|interest|installments?|payments?)\b.{0,30}?\b(?:was not|has not been|were not|have not been) paid\b",
    r"\b(?:did not|has not|have not) pay (?:the |scheduled )?(?:interest|principal|installments?)\b",
)
STRONG_DEFAULT = list(PAYMENT_DEFAULT) + [
    r"\bdeclared\b.{0,60}?\b(?:immediately )?due and payable\b",
    r"\b(?:debt|obligations?|loans?|notes?|maturity)\b.{0,60}?\b(?:has been|have been|were|was) accelerated\b",
    r"\baccelerated\b.{0,50}?\b(?:debt|obligations?|loans?|notes?|maturity)\b",
    r"\b(?:commenced|initiated|filed|completed)\b.{0,50}?\bforeclosure\b",
    r"\bforeclosure (?:proceedings?|sale)\b.{0,40}?\b(?:commenced|initiated|completed|occurred)\b",
    r"\btrustee['’]?s sale\b.{0,40}?\b(?:occurred|completed|held)\b",
]
ACTUAL_EVENT = [
    r"\b(?:has|have|had) occurred\b", r"\boccurred\b",
    r"\bfailed\b", r"\bmissed\b", r"\bdid not make\b",
    r"\b(?:was not|has not been|were not|have not been) paid\b",
    r"\b(?:did not|has not|have not) pay\b",
    r"\breceived\b.{0,30}?\bnotice\b",
    r"\b(?:declared|accelerated|commenced|initiated|completed|held)\b",
    r"\bbecame\b.{0,30}?\bdue\b",
]
NEGATIVE = [
    r"\btechnical (?:event of )?default\b",
    r"\bcovenant (?:breach|violation)\b",
    r"\b(?:voluntary|optional|scheduled) redemption\b",
    r"\bvoluntary prepayment\b", r"\bconversion price\b",
]
HYPOTHETICAL = [
    # A bare case-insensitive ``may`` also matches the month in filing dates.
    # Require modal language after "may" while retaining the other auxiliaries.
    r"\bmay\s+(?:be|have|constitute|cause|result|occur|trigger|accelerate|increase|become|lead|require|exercise|seek|declare|commence)\b",
    r"\b(?:might|could|would|will|shall)\b",
    r"\bin the event (?:of|that)\b", r"\bupon the occurrence of\b",
    r"\bif\b", r"\b(?:risk|possibility) of\b",
]
# Ambiguous or negated financial-default language stays in manual review.
NEGATED = [
    r"\b(?:no|not|never|without|neither)\b",
    r"\b(?:hasn['’]t|haven['’]t|hadn['’]t|didn['’]t)\b",
    r"\b(?:disputes?|disputed|alleged|alleges?|denies?|denied)\b",
]


ITEM_HEADING = re.compile(r"\bitem\s+(\d[.]\d{2})\b", re.IGNORECASE)


def matches(patterns, text):
    """Return whether any supplied expression matches, including across newlines."""
    return any(re.search(pattern, text, re.I | re.S) for pattern in patterns)


def matching_phrases(patterns, text):
    """Keep exact evidence phrases separately from the boolean classifier."""
    return [
        match.group(0)
        for pattern in patterns
        for match in re.finditer(pattern, text, re.I | re.S)
    ]


def qualifying_event_sentences(text, patterns=STRONG_DEFAULT):
    """Require strong and realized evidence in the same sentence.

    Mixed hypothetical/negated sentences are intentionally left to reviewers:
    regexes cannot reliably resolve which clause or borrower an assertion covers.
    """
    # Newlines and semicolons can sit inside conditional clauses. Normalize
    # whitespace first so a line break cannot turn boilerplate into an event.
    normalized = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", normalized)
    return [
        sentence.strip()
        for sentence in sentences
        if matches(patterns, sentence)
        and matches(ACTUAL_EVENT, sentence)
        and not matches(HYPOTHETICAL, sentence)
        and not matches(
            NEGATED,
            # "Interest was not paid" asserts nonpayment, not absence of default.
            re.sub(
                r"\b(?:was not|has not been|were not|have not been) paid\b|"
                r"\b(?:did not|has not|have not) pay\b",
                "unpaid", sentence, flags=re.I,
            ),
        )
    ]


def classify_item_204(text):
    """Conservatively classify realized events; keep ambiguous evidence for review."""
    if qualifying_event_sentences(text):
        return "QUALIFIED_DEFAULT"
    # Do not let boilerplate elsewhere turn an unresolved payment event negative.
    if matches(STRONG_DEFAULT, text) or matches(
        [r"\b(?:failed|failure) to pay\b", r"\b(?:foreclosure|trustee['’]?s sale)\b",
         r"\b(?<!technical )event of default\b"], text
    ):
        return "MANUAL_REVIEW"
    if matches(NEGATIVE, text) or matches(HYPOTHETICAL, text):
        return "NON_DEFAULT"
    return "MANUAL_REVIEW"


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
    """Rebuild deterministic CSV/audit outputs while reusing cached filing HTML."""
    if not args.submissions.is_dir():
        raise ValueError(f"Submissions directory does not exist: {args.submissions}")
    if not args.discover_only:
        from bs4 import BeautifulSoup  # Fail before creating partial output.

        if not args.offline and (not args.user_agent or "@" not in args.user_agent):
            raise ValueError(
                "Provide --user-agent 'Name email@example.com' for SEC requests"
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = args.output_dir / "html"
    cache.mkdir(exist_ok=True)
    counts = Counter()
    records_path = args.output_dir / "classifications.jsonl"
    with records_path.open("w") as output:
        for n, record in enumerate(
            iter_item_204(args.submissions, args.start, args.cutoff), 1
        ):
            if args.limit and n > args.limit:
                break
            record.update(
                rule_version=RULE_VERSION,
                classification="MANUAL_REVIEW",
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

                    record["evidence"] = {
                        name: matching_phrases(patterns, section)
                        for name, patterns in (
                            ("strong_default", STRONG_DEFAULT),
                            ("actual_event", ACTUAL_EVENT),
                            ("negative", NEGATIVE),
                            ("hypothetical", HYPOTHETICAL),
                            ("payment_default", PAYMENT_DEFAULT),
                        )
                    }

                    if scope == "isolated_item_section":
                        record["classification"] = classify_item_204(section)

                    record["evidence"]["qualifying_event_sentences"] = qualifying_event_sentences(section)
                    record["payment_default_evidence"] = bool(
                        qualifying_event_sentences(section, PAYMENT_DEFAULT)
                    )

                except (OSError, ValueError, URLError, TimeoutError) as exc:
                    record.update(status="error", error=str(exc))

            counts[record["classification"]] += 1
            counts[f"status_{record['status']}"] += 1
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            if n % 100 == 0:
                print(f"Reviewed {n} filings: {dict(counts)}", flush=True)

    fields = [
        "company_id",
        "entity_name",
        "filingDate",
        "reportDate",
        "accessionNumber",
        "form",
        "classification",
        "status",
        "same_filing_item_103",
        "prior_or_same_item_103",
        "first_recorded_item_103_date",
        "payment_default_evidence",
        "source_url",
        "error",
    ]

    with (args.output_dir / "classifications.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        with records_path.open() as records:
            for line in records:
                writer.writerow(json.loads(line))

    audit = {
        "rule_version": RULE_VERSION,
        "counts": dict(counts),
        "start": str(args.start),
        "cutoff": str(args.cutoff),
        "discovery_only": args.discover_only,
        "label_note": "Rule-based candidates; not verified payment defaults. Amendments and repeated filings are not deduplicated economic events.",
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
