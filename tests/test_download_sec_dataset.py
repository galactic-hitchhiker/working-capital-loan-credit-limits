"""Download recovery and extraction checks without contacting the SEC."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.download_sec_dataset import (
    Downloader,
    face_statement_archives,
    main,
    sha256,
    statement_archives,
    unpack,
)


def zipped(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, value in entries.items():
            archive.writestr(name, value)
    return stream.getvalue()


class Response(io.BytesIO):
    def __init__(self, body, status=200, **headers):
        super().__init__(body)
        self.status = status
        self.headers = headers


class DownloadTests(unittest.TestCase):
    def test_discovery_handles_monthly_quarterly_overlap_and_filters_sources(self):
        base = "/files/dera/data/financial-statement-notes-data-sets/"
        html = "".join(
            f'<a href="{base}{name}_notes.zip">zip</a>'
            for name in ["2009q4", "2025q3", "2025_07", "2025_10", "2026_01"]
        )
        html += '<a href="https://evil.example/2025q1_notes.zip">ignore</a>'
        html += f'<a href="{base}2010q1_notes_1.zip">reprocessed Q1</a>'
        actual = statement_archives(html, 2025, 2025)
        self.assertEqual([r["stem"] for r in actual], ["2025q3_notes", "2025_10_notes"])
        self.assertEqual([r["stem"] for r in statement_archives(html, 2010, 2010)], ["2010q1_notes_1"])
        with self.assertRaisesRegex(ValueError, "No statement archives"):
            statement_archives(html, 2011, 2011)

    def test_face_statement_discovery_selects_latest_quarter_version(self):
        base = "/files/dera/data/financial-statement-data-sets/"
        html = "".join(
            f'<a href="{base}{name}.zip">zip</a>'
            for name in ["2024q4", "2025q1", "2025q1_1", "2025q2", "2026q1"]
        )
        html += '<a href="https://evil.example/2025q3.zip">ignore</a>'
        actual = face_statement_archives(html, 2025, 2025)
        self.assertEqual([r["stem"] for r in actual], ["2025q1_1", "2025q2"])
        with self.assertRaisesRegex(ValueError, "No face financial statement"):
            face_statement_archives(html, 2011, 2011)

    def test_resume_uses_if_range_and_validates_complete_zip(self):
        body = zipped({"CIK1.json": "{}"})
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "facts.zip"
            target.with_suffix(".zip.part").write_bytes(body[:20])
            target.with_suffix(".zip.part.json").write_text(
                json.dumps({"url": "https://example.test/a", "validator": '"v1"'})
            )
            response = Response(
                body[20:],
                206,
                **{
                    "Content-Range": f"bytes 20-{len(body) - 1}/{len(body)}",
                    "ETag": '"v1"',
                },
            )
            client = Downloader("Research contact@example.com")
            with patch.object(client, "open", return_value=response) as request:
                client.download("https://example.test/a", target)
            self.assertEqual(
                request.call_args.args[1], {"Range": "bytes=20-", "If-Range": '"v1"'}
            )
            self.assertEqual(target.read_bytes(), body)
            self.assertFalse(target.with_suffix(".zip.part").exists())

    def test_changed_snapshot_replaces_partial_instead_of_appending(self):
        body = zipped({"new.json": "new"})
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "facts.zip"
            target.with_suffix(".zip.part").write_bytes(b"old partial")
            target.with_suffix(".zip.part.json").write_text(
                json.dumps({"url": "url", "validator": '"old"'})
            )
            client = Downloader("Research contact@example.com")
            with patch.object(
                client,
                "open",
                return_value=Response(
                    body, **{"Content-Length": str(len(body)), "ETag": '"new"'}
                ),
            ):
                client.download("url", target)
            self.assertEqual(target.read_bytes(), body)

    def test_invalid_range_and_truncated_response_never_become_completed_zip(self):
        for response, error in [
            (Response(b"bad", 206, **{"Content-Range": "bytes 5-7/8"}), ValueError),
            (Response(b"bad", **{"Content-Length": "100"}), ConnectionError),
        ]:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / "facts.zip"
                client = Downloader("Research contact@example.com", retries=0)
                with (
                    patch.object(client, "open", return_value=response),
                    self.assertRaises(error),
                ):
                    client.download("url", target)
                self.assertFalse(target.exists())

    def test_unpack_preserves_layout_and_can_be_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "source.zip", Path(tmp) / "submissions"
            source.write_bytes(
                zipped({"CIK0001.json": "{}", "CIK0001-submissions-001.json": "{}"})
            )
            digest = sha256(source)
            unpack(source, dest, digest)
            unpack(source, dest, digest)
            self.assertTrue((dest / "CIK0001-submissions-001.json").exists())
            (dest / "CIK0001.json").unlink()
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                unpack(source, dest, digest)

    def test_unpack_rejects_path_escape_symlink_and_existing_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "source.zip", Path(tmp) / "output"
            for name in ["../escape", "/absolute", "a/../../escape", "..\\escape"]:
                source.write_bytes(zipped({name: "data"}))
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, "Unsafe ZIP"),
                ):
                    unpack(source, dest, sha256(source))
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = 0o120777 << 16
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr(info, "../escape")
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP"):
                unpack(source, dest, sha256(source))
            source.write_bytes(zipped({"good": "data"}))
            dest.mkdir()
            with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
                unpack(source, dest, sha256(source))

    def test_corrupt_extraction_never_publishes_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "source.zip", Path(tmp) / "output"
            source.write_bytes(
                zipped({"facts.json": "unique-value"}).replace(
                    b"unique-value", b"broken-value"
                )
            )
            with self.assertRaises(zipfile.BadZipFile):
                unpack(source, dest, sha256(source))
            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(tmp).glob(".output-unpacking-*")), [])

    def test_all_datasets_cli_layout_and_manifest_with_local_fixture_downloads(self):
        html = '<a href="/files/dera/data/financial-statement-notes-data-sets/2025q1_notes.zip">Q1</a>'
        face_html = '<a href="/files/dera/data/financial-statement-data-sets/2025q1.zip">Q1</a>'

        def download(client, url, target):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                zipped(
                    {"sub.tsv": "adsh\n"}
                    if "notes.zip" in url or "2025q1.zip" in url
                    else {"CIK0001.json": "{}"}
                )
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "dataset"
            args = [
                "--output-dir",
                str(root),
                "--user-agent",
                "Research contact@example.com",
                "--start-year",
                "2025",
                "--end-year",
                "2025",
            ]
            with (
                patch.object(Downloader, "index", side_effect=lambda url=None: face_html if url else html),
                patch.object(Downloader, "download", download),
            ):
                self.assertEqual(main([*args, "--dry-run"]), 0)
                self.assertFalse(root.exists())
                self.assertEqual(main(args), 0)
            manifest = json.loads((root / "download_manifest.json").read_text())
            self.assertEqual(len(manifest["archives"]), 4)
            self.assertTrue((root / "companyfacts/CIK0001.json").exists())
            self.assertTrue((root / "submissions/CIK0001.json").exists())
            self.assertTrue(
                (root / "financial_statements/2025q1_notes/sub.tsv").exists()
            )
            self.assertTrue(
                (root / "financial_statements/archives/2025q1_notes.zip").exists()
            )
            self.assertTrue(
                (root / "financial_statements/face/2025q1/sub.tsv").exists()
            )
            self.assertTrue(
                (root / "financial_statements/face/archives/2025q1.zip").exists()
            )


if __name__ == "__main__":
    unittest.main()
