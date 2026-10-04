"""LLM review safety checks; no API calls."""
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from item204_enrichment.reviewers.openai import APIReviewError, request_review, run, validate_review


class LLMReviewTests(unittest.TestCase):
    def review(self, **changes):
        value = dict(classification="QUALIFIED_DEFAULT", event_type="PAYMENT_FAILURE",
                     certainty="HIGH", reason="Explicit failure", evidence_quotes=["failed to pay interest"])
        value.update(changes)
        return value

    def test_supported_review(self):
        validate_review(self.review(), "The issuer failed to pay interest.")

    def test_valid_quotes_survive_model_added_ellipsis(self):
        text = (
            "The Company failed to make payment of principal and interest under "
            "the terms of the Series A Notes, thereby causing an Event of Default."
        )
        review = self.review(
            evidence_quotes=[
                "The Company failed to make payment of principal and interest "
                "under the terms of the Series A Notes\\u2026",
                "thereby causing an Event of Default.",
            ]
        )
        validated = validate_review(review, text)
        self.assertEqual(
            validated["evidence_quotes"],
            [
                "The Company failed to make payment of principal and interest "
                "under the terms of the Series A Notes",
                "thereby causing an Event of Default.",
            ],
        )

    def test_invalid_evidence_and_uncertainty(self):
        for changes in ({"evidence_quotes": ["invented quote"]},
                        {"evidence_quotes": []}, {"certainty": "UNCERTAIN"},
                        {"event_type": "BENIGN"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_review(self.review(**changes), "The issuer failed to pay interest.")

    def test_resume_preserves_original_and_uses_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_dir = root / "html"
            html_dir.mkdir()
            source = root / "source.jsonl"
            record = dict(company_id="0000001800", accessionNumber="0001104659-19-074388",
                          classification="MANUAL_REVIEW")
            source.write_text(json.dumps(record) + "\n")
            text = "Item 2.04 The issuer failed to pay interest. " + "Disclosure details. " * 10
            (html_dir / "0000001800_0001104659-19-074388.html").write_text('<p>' + text + '</p>')
            args = Namespace(input=source, html_dir=html_dir, output_dir=root / "output",
                             model="test-model", dry_run=False, limit=1, max_chars=10000)
            original = source.read_bytes()
            with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}), patch(
                'item204_enrichment.reviewers.openai.request_review', return_value=(self.review(), {})
            ) as request, patch('builtins.print'):
                run(args)
                run(args)
                self.assertEqual(request.call_count, 1)
            result = json.loads((args.output_dir / "classifications.jsonl").read_text())
            self.assertEqual(result['classification'], 'QUALIFIED_DEFAULT')
            self.assertEqual(result['llm_status'], 'cached')
            self.assertEqual(source.read_bytes(), original)

    def test_missing_html_remains_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            source.write_text(json.dumps(dict(company_id="0000001800",
                accessionNumber="0001104659-19-074388", classification="MANUAL_REVIEW")))
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="test", dry_run=False, limit=1, max_chars=10000)
            with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}), patch(
                'item204_enrichment.reviewers.openai.request_review'
            ) as request, patch('builtins.print'):
                run(args)
                request.assert_not_called()
            result = json.loads((args.output_dir / "classifications.jsonl").read_text())
            self.assertEqual(result['classification'], 'MANUAL_REVIEW')
            self.assertEqual(result['llm_status'], 'fallback_missing_input')
            self.assertEqual(result['llm_review']['review']['classification'], 'MANUAL_REVIEW')
            review_files = list((args.output_dir / 'reviews').rglob('*.json'))
            self.assertEqual(len(review_files), 1)
            self.assertEqual(review_files[0].parent.name, 'fallback_missing_input')
            stored = json.loads(review_files[0].read_text())
            self.assertEqual(stored['status'], 'fallback_missing_input')
            self.assertTrue(stored['fallback'])
            with patch.dict('os.environ', {"OPENAI_API_KEY": "test-key"}), patch(
                'item204_enrichment.reviewers.openai.request_review'
            ) as request, patch('builtins.print'):
                run(args)
                request.assert_not_called()
            result = json.loads((args.output_dir / "classifications.jsonl").read_text())
            self.assertEqual(result['llm_status'], 'cached')
            self.assertEqual(len(list((args.output_dir / 'reviews').rglob('*.json'))), 1)
            self.assertEqual(
                len((args.output_dir / 'review_log.jsonl').read_text().splitlines()), 1
            )

    def test_http_error_details_redact_key(self):
        from io import BytesIO
        from urllib.error import HTTPError
        error = HTTPError('https://api.openai.com/v1/responses', 429, 'Too Many Requests', {},
                          BytesIO(json.dumps({'error': {'code': 'insufficient_quota',
                          'message': 'Quota exhausted test-key'}}).encode()))
        with patch('item204_enrichment.reviewers.openai.urlopen', side_effect=error):
            with self.assertRaises(APIReviewError) as raised:
                request_review('filing', 'test', 'test-key')
        self.assertIn('insufficient_quota', str(raised.exception))
        self.assertNotIn('test-key', str(raised.exception))

    def test_api_failure_stops_new_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.jsonl'
            records = []
            for suffix in ('074388', '074389'):
                accession = '0001104659-19-' + suffix
                records.append(dict(company_id='0000001800', accessionNumber=accession,
                                    classification='MANUAL_REVIEW'))
                (root / ('0000001800_' + accession + '.html')).write_text(
                    '<p>Item 2.04 The issuer failed to pay interest. ' + 'Details. ' * 20 + accession + '</p>')
            source.write_text(''.join(json.dumps(r) + '\n' for r in records))
            args = Namespace(input=source, html_dir=root, output_dir=root / 'output',
                             model='test', dry_run=False, limit=20, max_chars=10000)
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), patch(
                'item204_enrichment.reviewers.openai.request_review', side_effect=APIReviewError('HTTP 429 [insufficient_quota]')
            ) as request, patch('builtins.print'):
                run(args)
                self.assertEqual(request.call_count, 1)
            rows = [json.loads(x) for x in (args.output_dir / 'classifications.jsonl').read_text().splitlines()]
            self.assertEqual(
                [r['llm_status'] for r in rows],
                ['fallback_provider_error', 'fallback_provider_unavailable'],
            )
            self.assertTrue(all(r['classification'] == 'MANUAL_REVIEW' for r in rows))
            self.assertEqual(len(list((args.output_dir / 'reviews').rglob('*.json'))), 2)

            args.retry_fallbacks = True
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), patch(
                'item204_enrichment.reviewers.openai.request_review',
                return_value=(self.review(), {}),
            ) as request, patch('builtins.print'):
                run(args)
                self.assertEqual(request.call_count, 2)
            rows = [json.loads(x) for x in
                    (args.output_dir / 'classifications.jsonl').read_text().splitlines()]
            self.assertEqual([r['llm_status'] for r in rows], ['reviewed', 'reviewed'])
            self.assertTrue(all(r['classification'] == 'QUALIFIED_DEFAULT' for r in rows))
            stored = [json.loads(path.read_text()) for path in
                      (args.output_dir / 'reviews').rglob('*.json')]
            self.assertEqual(len(stored), 2)
            self.assertTrue(all(not item.get('fallback', False) for item in stored))

            args.limit = 1
            args.output_dir = root / 'output-success'
            args.retry_fallbacks = False
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), patch(
                'item204_enrichment.reviewers.openai.request_review', return_value=(self.review(), {})
            ) as request, patch('builtins.print'):
                run(args)
                self.assertEqual(request.call_count, 1)
            rows = [json.loads(x) for x in (args.output_dir / 'classifications.jsonl').read_text().splitlines()]
            self.assertEqual([r['llm_status'] for r in rows], ['reviewed', 'deferred_limit'])
