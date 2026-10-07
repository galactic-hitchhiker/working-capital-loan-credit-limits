"""LLM review safety checks; no API calls."""
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from mcf.enrichment.item204.reviewers.common import validate_review


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

    def test_fulfilled_sale_triggered_prepayment_cannot_qualify_as_acceleration(self):
        text = (
            "Item 2.04 TRIGGERING EVENTS THAT ACCELERATE OR INCREASE A DIRECT FINANCIAL OBLIGATION. "
            "The disposition of Patterson Medical on August 28, 2015 triggered the Company’s "
            "obligation to prepay certain loans made under the Credit Agreement. "
            "To satisfy its prepayment obligation, the Company applied net proceeds of $670 million "
            "from the sale of Patterson Medical to prepay certain term loans made under the Credit Agreement."
        )
        with self.assertRaisesRegex(ValueError, 'contractual prepayment'):
            validate_review(self.review(event_type='ACCELERATION', evidence_quotes=[text]), text)
        benign = validate_review(self.review(classification='NON_DEFAULT', event_type='BENIGN',
            reason='The issuer satisfied a sale-triggered contractual prepayment obligation.',
            evidence_quotes=[text]), text)
        self.assertEqual(benign['classification'], 'NON_DEFAULT')

    def test_acceleration_requires_default_trigger_and_realized_action_quotes(self):
        text = "The Company breached its debt covenant. The lenders declared all loans immediately due and payable."
        validated = validate_review(self.review(event_type='ACCELERATION', evidence_quotes=[
            'The Company breached its debt covenant.',
            'The lenders declared all loans immediately due and payable.',
        ]), text)
        self.assertEqual(validated['classification'], 'QUALIFIED_DEFAULT')
        for quote in ('The Company breached its debt covenant.',
                      'The lenders declared all loans immediately due and payable.'):
            with self.subTest(quote=quote), self.assertRaises(ValueError):
                validate_review(self.review(event_type='ACCELERATION', evidence_quotes=[quote]), text)


    def test_filing_answer_is_final_across_configuration_and_input_changes(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            record = dict(company_id="0000001800", accessionNumber="0001104659-19-074388",
                          classification="MANUAL_REVIEW",
                          item_204_text="The issuer failed to pay interest.")
            # Duplicate input rows must produce one request and one stored answer.
            source.write_text((json.dumps(record) + "\n") * 2)
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="first-model", dry_run=False, limit=0)
            with patch('builtins.print'):
                request = Mock(return_value=(self.review(), {}))
                run_reviews(args, request, provider="legacy_provider")
                self.assertEqual(request.call_count, 1)
                stored_path = next((args.output_dir / "reviews").rglob("*.json"))
                original = stored_path.read_bytes()
                # Reclassification, changed text, model/provider and a dry run
                # must all preserve the existing response and its provenance.
                record.update(classification="NON_DEFAULT", item_204_text="Different narrative.")
                source.write_text(json.dumps(record) + "\n")
                args.model = "second-model"
                args.dry_run = True
                with patch('mcf.enrichment.item204.reviewers.common.visible_text',
                           side_effect=AssertionError("Cached filings should not be parsed")):
                    run_reviews(args, request, provider="openai")
                self.assertEqual(request.call_count, 1)
                result = json.loads((args.output_dir / "classifications.jsonl").read_text())
                self.assertEqual(result['classification'], 'QUALIFIED_DEFAULT')
                self.assertEqual(result['llm_status'], 'cached')
                self.assertEqual(result['llm_review']['requested_model'], 'first-model')
                self.assertEqual(result['llm_review']['provider'], 'legacy_provider')
                self.assertEqual(stored_path.read_bytes(), original)
                self.assertEqual(len((args.output_dir / 'review_log.jsonl').read_text().splitlines()), 1)
                # Only an explicit refresh requests another answer.
                record['classification'] = 'MANUAL_REVIEW'
                source.write_text(json.dumps(record) + "\n")
                args.dry_run = False
                args.refresh = True
                request.return_value = (self.review(classification="MANUAL_REVIEW",
                    event_type="UNCERTAIN", certainty="UNCERTAIN", evidence_quotes=[]), {})
                run_reviews(args, request, provider="openai")
                self.assertEqual(request.call_count, 2)
                args.refresh = False
                run_reviews(args, request, provider="legacy_provider")
                self.assertEqual(request.call_count, 2)
                result = json.loads((args.output_dir / "classifications.jsonl").read_text())
                self.assertEqual(result['classification'], 'MANUAL_REVIEW')
                self.assertEqual(result['llm_review']['requested_model'], 'second-model')

    def test_cancel_during_request_exports_progress_and_resumes(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            records = [dict(company_id="0000001800",
                            accessionNumber=f"0001104659-19-{suffix}",
                            classification="MANUAL_REVIEW",
                            item_204_text="The issuer failed to pay interest.")
                       for suffix in ("074388", "074389", "074390")]
            source.write_text(''.join(json.dumps(r) + "\n" for r in records))
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="test", dry_run=False, limit=0)
            request = Mock(side_effect=[(self.review(), {}), KeyboardInterrupt()])
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertTrue(audit['interrupted'])
            self.assertEqual(request.call_count, 2)
            rows = [json.loads(line) for line in
                    (args.output_dir / "classifications.jsonl").read_text().splitlines()]
            self.assertEqual([r['llm_status'] for r in rows],
                             ['reviewed', 'deferred_interrupted', 'deferred_interrupted'])
            self.assertEqual(len(list((args.output_dir / "reviews").rglob("*.json"))), 1)
            self.assertEqual(len((args.output_dir / "review_log.jsonl").read_text().splitlines()), 1)
            self.assertEqual(len((args.output_dir / "classifications.csv").read_text().splitlines()), 4)
            request = Mock(return_value=(self.review(), {}))
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertFalse(audit['interrupted'])
            self.assertEqual(request.call_count, 2)
            rows = [json.loads(line) for line in
                    (args.output_dir / "classifications.jsonl").read_text().splitlines()]
            self.assertEqual([r['llm_status'] for r in rows], ['cached', 'reviewed', 'reviewed'])
            self.assertEqual(len((args.output_dir / "review_log.jsonl").read_text().splitlines()), 3)

    def test_cancel_after_atomic_save_keeps_response(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            source.write_text(json.dumps(dict(company_id="0000001800",
                accessionNumber="0001104659-19-074388", classification="MANUAL_REVIEW",
                item_204_text="The issuer failed to pay interest.")) + "\n")
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="test", dry_run=False, limit=0)
            request = Mock(return_value=(self.review(), {}))
            with patch('builtins.print'), patch(
                'mcf.enrichment.item204.reviewers.common.log_review', side_effect=KeyboardInterrupt
            ):
                audit = run_reviews(args, request)
            self.assertTrue(audit['interrupted'])
            result = json.loads((args.output_dir / "classifications.jsonl").read_text())
            self.assertEqual(result['classification'], 'QUALIFIED_DEFAULT')
            with patch('builtins.print'):
                run_reviews(args, request)
            self.assertEqual(request.call_count, 1)

    def test_filing_date_bounds_filter_before_review_and_preserve_resume(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            records = [dict(company_id="0000001800",
                            accessionNumber=f"0001104659-19-{74388 + index:06d}",
                            filingDate=filed, classification="MANUAL_REVIEW",
                            item_204_text="The issuer failed to pay interest.")
                       for index, filed in enumerate(
                           ("2009-12-31", "2010-01-01", "2012-12-31", "2013-01-01"))]
            source.write_text(''.join(json.dumps(r) + "\n" for r in records))
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="test", dry_run=False, limit=1,
                             start=date(2010, 1, 1), cutoff=date(2013, 1, 1))
            request = Mock(return_value=(self.review(), {}))
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertEqual(request.call_count, 1)
            self.assertEqual(audit['selected_records'], 2)
            self.assertEqual(audit['excluded_records'], 2)
            self.assertEqual(audit['start'], '2010-01-01')
            self.assertEqual(audit['cutoff'], '2013-01-01')
            rows = [json.loads(line) for line in
                    (args.output_dir / "classifications.jsonl").read_text().splitlines()]
            self.assertEqual([r['filingDate'] for r in rows], ['2010-01-01', '2012-12-31'])
            self.assertEqual([r['llm_status'] for r in rows], ['reviewed', 'deferred_limit'])
            # Widening the scope retains the saved answer and processes new filings.
            args.cutoff = None
            args.limit = 0
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertEqual(request.call_count, 3)
            self.assertEqual(audit['review_counts'], {'cached': 1, 'reviewed': 2})
            # Narrowing the scope must also exclude previously cached answers.
            args.cutoff = date(2012, 1, 1)
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertEqual(request.call_count, 3)
            self.assertEqual(audit['selected_records'], 1)
            self.assertEqual(len(list((args.output_dir / "reviews").rglob("*.json"))), 3)

    def test_date_filter_rejects_unknown_dates_before_requests(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            record = dict(company_id="0000001800", accessionNumber="0001104659-19-074388",
                          classification="MANUAL_REVIEW")
            args = Namespace(input=source, html_dir=root, output_dir=root / "output",
                             model="test", dry_run=False, limit=0,
                             start=date(2010, 1, 1), cutoff=None)
            request = Mock()
            for invalid in (None, "invalid", "2010-02-30"):
                with self.subTest(filingDate=invalid):
                    record['filingDate'] = invalid
                    source.write_text(json.dumps(record) + "\n")
                    with self.assertRaisesRegex(ValueError, 'filingDate'):
                        run_reviews(args, request)
            request.assert_not_called()
            args.cutoff = args.start
            with self.assertRaisesRegex(ValueError, '--start must precede --cutoff'):
                run_reviews(args, request)

    def test_review_parser_accepts_date_bounds(self):
        from mcf.enrichment.item204.reviewers.common import make_parser, check_args

        parser = make_parser("test", "output", "test-model")
        args = parser.parse_args(['--start', '2010-01-01', '--cutoff', '2013-01-01'])
        check_args(parser, args)
        self.assertEqual(args.start, date(2010, 1, 1))
        self.assertEqual(args.cutoff, date(2013, 1, 1))
        args.cutoff = args.start
        with patch('sys.stderr'), self.assertRaises(SystemExit):
            check_args(parser, args)

    def test_retry_fallbacks_only_retries_provider_errors(self):
        from mcf.enrichment.item204.reviewers.common import run as run_reviews

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.jsonl"
            output = root / "output"
            cache = output / "reviews" / "manual_review"
            cache.mkdir(parents=True)
            statuses = (
                "fallback_missing_input", "fallback_context_budget",
                "fallback_validation_error", "fallback_unknown",
                "fallback_generation_error", "fallback_provider_error",
                "fallback_provider_unavailable",
            )
            records = []
            preserved = {}
            for index, status in enumerate(statuses):
                record = dict(company_id="0000001800",
                              accessionNumber=f"0001104659-19-{74388 + index:06d}",
                              classification="MANUAL_REVIEW",
                              item_204_text="The issuer failed to pay interest.")
                if status == "fallback_missing_input":
                    record["item_204_text"] = ""
                records.append(record)
                saved = dict(company_id=record['company_id'], accessionNumber=record['accessionNumber'],
                             status=status, fallback=True, provider='openai_batch', requested_model='old-model',
                             review=self.review(classification='MANUAL_REVIEW', event_type='UNCERTAIN',
                                                certainty='UNCERTAIN', evidence_quotes=[]))
                path = cache / f"{index}.json"
                path.write_text(json.dumps(saved))
                if index < 5:
                    preserved[path] = path.read_bytes()
            source.write_text(''.join(json.dumps(r) + "\n" for r in records))
            args = Namespace(input=source, html_dir=root, output_dir=output,
                             model="test", dry_run=False, limit=0,
                             retry_fallbacks=True)
            request = Mock(return_value=(self.review(), {}))
            with patch('builtins.print'):
                audit = run_reviews(args, request)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(audit['review_counts'], {'cached': 5, 'reviewed': 2})
            rows = [json.loads(line) for line in (output / 'classifications.jsonl').read_text().splitlines()]
            self.assertEqual([r['llm_status'] for r in rows], ['cached'] * 5 + ['reviewed'] * 2)
            for path, original in preserved.items():
                self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len((output / 'review_log.jsonl').read_text().splitlines()), 2)
            self.assertEqual(len(list((output / 'reviews').rglob('*.json'))), 7)
            # The same flag now resumes without retrying preserved manual outcomes.
            with patch('builtins.print'):
                run_reviews(args, request)
            self.assertEqual(request.call_count, 2)
