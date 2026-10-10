#!/usr/bin/env python3
"""Download and unpack SEC bulk data without project dependencies.

Run: python3 scripts/download_sec_dataset.py --output-dir ../dataset_full
     --start-year 2009 --end-year 2026 --user-agent 'Name email@example.com'

Required: --output-dir and --user-agent (or SEC_USER_AGENT environment variable).
Optional: --datasets companyfacts submissions statements (default: all),
--start-year (2009), --end-year (current year), --download-only, --dry-run,
--retries (4), --interval (0.5 seconds), --timeout (120 seconds).
Year filters apply only to statements. Existing completed archives are reused;
use a new output directory for a refreshed snapshot. ZIPs are retained.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import stat
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import zipfile


INDEX = "https://www.sec.gov/data-research/sec-markets-data/financial-statement-notes-data-sets"
BULK = {
    "companyfacts": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
    "submissions": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
}
CHUNK = 1024 * 1024
MARKER = ".sec-extraction.json"


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


class ArchiveLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href")
        if tag == "a" and href:
            self.links.add(urljoin(INDEX, href))


def statement_archives(html, start_year, end_year):
    parser = ArchiveLinks()
    parser.feed(html)
    archives = {}
    for url in sorted(parser.links):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "www.sec.gov":
            continue
        match = re.fullmatch(
            r"/files/dera/data/financial-statement-notes-data-sets/"
            r"((\d{4})(?:q([1-4])|_(0[1-9]|1[0-2]))_notes(?:_[0-9]+)?)\.zip",
            parsed.path,
        )
        if not match or not start_year <= int(match[2]) <= end_year:
            continue
        stem, year, quarter, month = match.groups()
        months = (
            tuple(range((int(quarter) - 1) * 3 + 1, int(quarter) * 3 + 1))
            if quarter
            else (int(month),)
        )
        archives[stem] = dict(url=url, year=int(year), months=months, stem=stem)
    # When the SEC consolidates monthly files, prefer the quarterly archive.
    quarters = {
        (a["year"], m)
        for a in archives.values()
        if len(a["months"]) == 3
        for m in a["months"]
    }
    selected = [
        a
        for a in archives.values()
        if len(a["months"]) == 3 or (a["year"], a["months"][0]) not in quarters
    ]
    if not selected:
        raise ValueError("No statement archives found for these years on the SEC index")
    return sorted(selected, key=lambda a: (a["year"], a["months"][0]))


class Downloader:
    def __init__(self, user_agent, interval=0.5, retries=4, timeout=120):
        self.user_agent, self.interval = user_agent, interval
        self.retries, self.timeout = retries, timeout
        self.last_request = 0.0
        self.ssl_context = ssl.create_default_context()
        # Python.org macOS installs can lack their own CA bundle. Add the
        # system bundle when available, retaining certificate verification.
        if Path("/etc/ssl/cert.pem").is_file():
            self.ssl_context.load_verify_locations("/etc/ssl/cert.pem")

    def open(self, url, headers=None):
        time.sleep(max(0, self.interval - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        return urlopen(
            Request(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "identity",
                    **(headers or {}),
                },
            ),
            timeout=self.timeout,
            context=self.ssl_context,
        )

    def retry(self, exc, attempt):
        if isinstance(exc, HTTPError) and exc.code not in {
            408,
            429,
            500,
            502,
            503,
            504,
        }:
            raise exc
        if attempt == self.retries:
            raise exc
        delay = min(30, 2 ** (attempt + 1))
        if isinstance(exc, HTTPError):
            retry_after = exc.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = max(delay, int(retry_after))
        print(f"Request failed: {exc}. Retrying in {delay}s.", flush=True)
        time.sleep(delay)

    def index(self):
        for attempt in range(self.retries + 1):
            try:
                with self.open(INDEX) as response:
                    return response.read().decode("utf-8")
            except (
                URLError,
                TimeoutError,
                ConnectionError,
                http.client.HTTPException,
            ) as exc:
                self.retry(exc, attempt)

    def download(self, url, target):
        if target.exists():
            print(f"Reusing {target}", flush=True)
            with zipfile.ZipFile(target) as archive:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f"Existing ZIP CRC check failed: {target}: {bad}")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        state_path = partial.with_suffix(partial.suffix + ".json")
        for attempt in range(self.retries + 1):
            try:
                state = (
                    json.loads(state_path.read_text()) if state_path.exists() else {}
                )
                offset = partial.stat().st_size if partial.exists() else 0
                validator = state.get("validator") if state.get("url") == url else None
                if not validator:
                    offset = (
                        0  # Never append to a potentially different nightly snapshot.
                    )
                headers = (
                    {"Range": f"bytes={offset}-", "If-Range": validator}
                    if offset
                    else {}
                )
                print(
                    f"Downloading {target.name} (resume offset {offset:,} bytes)",
                    flush=True,
                )
                with self.open(url, headers) as response:
                    if response.status == 206:
                        content_range = re.fullmatch(
                            r"bytes (\d+)-(\d+)/(\d+)",
                            response.headers.get("Content-Range", ""),
                        )
                        if not content_range or int(content_range[1]) != offset:
                            raise ValueError(
                                "Server returned an unexpected download range"
                            )
                        expected_size = int(content_range[3])
                    elif response.status == 200:
                        offset = (
                            0  # Server ignored Range, or If-Range detected an update.
                        )
                        length = response.headers.get("Content-Length")
                        expected_size = int(length) if length else None
                    else:
                        raise ValueError(f"Unexpected HTTP status {response.status}")
                    etag = response.headers.get("ETag", "")
                    validator = (
                        etag
                        if etag and not etag.startswith("W/")
                        else response.headers.get("Last-Modified")
                    )
                    write_json(state_path, dict(url=url, validator=validator))
                    with partial.open("ab" if offset else "wb") as output:
                        last_progress = time.monotonic()
                        while block := response.read(CHUNK):
                            output.write(block)
                            if time.monotonic() - last_progress >= 10:
                                print(
                                    f"  {output.tell() / 1024**2:,.0f} MiB downloaded",
                                    flush=True,
                                )
                                last_progress = time.monotonic()
                if (
                    expected_size is not None
                    and partial.stat().st_size != expected_size
                ):
                    raise ConnectionError(
                        "Incomplete response; partial download retained"
                    )
                with zipfile.ZipFile(partial) as archive:
                    bad = archive.testzip()
                    if bad:
                        raise ValueError(f"ZIP CRC check failed: {bad}")
                partial.replace(target)
                state_path.unlink(missing_ok=True)
                return
            except HTTPError as exc:
                if exc.code == 416 and offset:
                    # A finished partial file, or a changed remote object: restart.
                    state_path.unlink(missing_ok=True)
                    if attempt == self.retries:
                        raise
                    continue
                self.retry(exc, attempt)
            except (
                URLError,
                TimeoutError,
                ConnectionError,
                http.client.HTTPException,
            ) as exc:
                self.retry(exc, attempt)


def members(archive):
    result, seen = [], set()
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in info.filename
            or ":" in info.filename
            or not path.parts
            or path.as_posix() == MARKER
            or stat.S_ISLNK(info.external_attr >> 16)
        ):
            raise ValueError(f"Unsafe ZIP member: {info.filename}")
        if path.as_posix() in seen:
            raise ValueError(f"Duplicate ZIP member: {info.filename}")
        seen.add(path.as_posix())
        result.append(info)
    return result


def unpack(source, destination, digest):
    with zipfile.ZipFile(source) as archive:
        entries = members(archive)
        if destination.exists():
            marker = destination / MARKER
            if (
                marker.is_file()
                and json.loads(marker.read_text()).get("sha256") == digest
                and all(
                    (destination / i.filename).is_file()
                    and (destination / i.filename).stat().st_size == i.file_size
                    for i in entries
                    if not i.is_dir()
                )
            ):
                print(f"Already unpacked: {destination}", flush=True)
                return
            raise ValueError(
                f"Refusing to overwrite an existing or incomplete dataset: {destination}. "
                "Use a fresh --output-dir; existing datasets are not merged."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        required = sum(i.file_size for i in entries)
        if shutil.disk_usage(destination.parent).free < required:
            raise ValueError(
                f"Insufficient disk space to unpack {source.name}: needs {required:,} bytes"
            )
        stage = Path(
            tempfile.mkdtemp(
                prefix=f".{destination.name}-unpacking-", dir=destination.parent
            )
        )
        try:
            print(f"Unpacking {source.name}: {required / 1024**3:.2f} GiB", flush=True)
            for info in entries:
                archive.extract(
                    info, stage
                )  # Validated paths; extraction verifies each file's CRC.
            write_json(stage / MARKER, dict(sha256=digest, archive=source.name))
            stage.rename(destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=[*BULK, "statements"],
        default=[*BULK, "statements"],
    )
    parser.add_argument("--start-year", type=int, default=2009)
    parser.add_argument("--end-year", type=int, default=datetime.now().year)
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch the archive index and print the plan only",
    )
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    if (
        not args.user_agent
        or "@" not in args.user_agent
        or any(c in args.user_agent for c in "\r\n")
    ):
        parser.error(
            "Set --user-agent or SEC_USER_AGENT to your name/organization and contact email"
        )
    if not 2009 <= args.start_year <= args.end_year <= datetime.now().year:
        parser.error("Years must be ordered and between 2009 and the current year")
    if args.interval < 0.1 or args.retries < 0 or args.timeout <= 0:
        parser.error("Require interval >= 0.1, retries >= 0, timeout > 0")
    client = Downloader(args.user_agent, args.interval, args.retries, args.timeout)
    root = args.output_dir
    jobs = [
        (url, root / f"{name}.zip", root / name)
        for name, url in BULK.items()
        if name in args.datasets
    ]
    index_html = None
    if "statements" in args.datasets:
        index_html = client.index()
        for item in statement_archives(index_html, args.start_year, args.end_year):
            jobs.append(
                (
                    item["url"],
                    root / "financial_statements" / "archives" / f"{item['stem']}.zip",
                    root / "financial_statements" / item["stem"],
                )
            )
    print(f"Plan: {len(jobs)} archives; output {root.resolve()}", flush=True)
    for url, archive, destination in jobs:
        print(
            f"  {url}\n    -> {archive}"
            + ("" if args.download_only else f" -> {destination}")
        )
    if args.dry_run:
        return 0
    root.mkdir(parents=True, exist_ok=True)
    if index_html is not None:
        (root / "statement_archive_index.html").write_text(index_html)
    manifest_path = root / "download_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"archives": {}}
    )
    for url, archive, destination in jobs:
        client.download(url, archive)
        digest = sha256(archive)
        if not args.download_only:
            unpack(archive, destination, digest)
        manifest["archives"][str(archive.relative_to(root))] = dict(
            url=url,
            sha256=digest,
            bytes=archive.stat().st_size,
            unpacked_to=str(destination.relative_to(root))
            if not args.download_only
            else None,
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
        write_json(manifest_path, manifest)
    print(f"Done. Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, zipfile.BadZipFile, http.client.HTTPException) as exc:
        sys.exit(f"Download stopped: {exc}")
    except KeyboardInterrupt:
        sys.exit("Interrupted. Rerun the same command to resume downloads.")
