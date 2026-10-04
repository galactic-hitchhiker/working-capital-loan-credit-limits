"""Local provider request and resumability checks without model inference."""
import json
import hashlib
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
from io import BytesIO

from mcf.enrichment.item204.reviewers.ollama import DEFAULT_MODEL, request_review, run
from mcf.enrichment.item204.reviewers.common import visible_text


class OllamaReviewTests(unittest.TestCase):
    def review(self):
        return dict(classification='QUALIFIED_DEFAULT', event_type='PAYMENT_FAILURE',
                    certainty='HIGH', reason='Explicit missed interest',
                    evidence_quotes=['failed to pay interest'])

    def test_request_schema_and_defaults(self):
        payload = dict(model=DEFAULT_MODEL, done=True, done_reason='stop',
                       message={'content': json.dumps(self.review())})
        with patch('mcf.enrichment.item204.reviewers.ollama.urlopen',
                   return_value=BytesIO(json.dumps(payload).encode())) as call:
            review, metadata = request_review('The issuer failed to pay interest.', DEFAULT_MODEL)
        body = json.loads(call.call_args.args[0].data)
        self.assertEqual(body['model'], 'gemma3:12b')
        self.assertFalse(body['stream'])
        self.assertFalse(body['think'])
        self.assertEqual(body['format']['type'], 'object')
        self.assertEqual(body['options']['num_ctx'], 32768)
        self.assertEqual(review['classification'], 'QUALIFIED_DEFAULT')
        self.assertNotIn('Authorization', call.call_args.args[0].headers)

    def test_incomplete_answer_rejected(self):
        payload = dict(done=True, done_reason='length', message={'content': '{}'})
        with patch('mcf.enrichment.item204.reviewers.ollama.urlopen',
                   return_value=BytesIO(json.dumps(payload).encode())), self.assertRaises(ValueError):
            request_review('The issuer failed to pay interest.', DEFAULT_MODEL)

    def test_context_budget_never_truncates(self):
        with patch('mcf.enrichment.item204.reviewers.ollama.urlopen') as call, self.assertRaises(ValueError):
            request_review('x' * 40000, DEFAULT_MODEL)
        call.assert_not_called()

    def test_resume_without_openai_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accession = '0001104659-19-074388'
            source = root / 'source.jsonl'
            source.write_text(json.dumps(dict(company_id='0000001800',
                accessionNumber=accession, classification='MANUAL_REVIEW')))
            (root / ('0000001800_' + accession + '.html')).write_text(
                '<p>Item 2.04 The issuer failed to pay interest. ' + 'Details. ' * 20 + '</p>')
            args = Namespace(input=source, html_dir=root, output_dir=root / 'output',
                             model=DEFAULT_MODEL, dry_run=False, limit=1, max_chars=24000,
                             host='http://localhost:11434', num_ctx=32768, timeout=600, think=False)
            with patch.dict('os.environ', {}, clear=True), patch(
                'mcf.enrichment.item204.reviewers.ollama.request_review', return_value=(self.review(), {})
            ) as call, patch('builtins.print'):
                run(args)
                args.retry_fallbacks = True
                run(args)
                self.assertEqual(call.call_count, 1)
            audit = json.loads((args.output_dir / 'audit.json').read_text())
            self.assertEqual(audit['provider'], 'ollama')
            self.assertEqual(audit['review_counts'], {'cached': 1})
            logs = [json.loads(line) for line in
                    (args.output_dir / 'review_log.jsonl').read_text().splitlines()]
            self.assertEqual([entry['status'] for entry in logs], ['reviewed'])
            self.assertEqual(logs[0]['reason'], self.review()['reason'])
            self.assertEqual(logs[0]['evidence_quotes'], self.review()['evidence_quotes'])
            self.assertEqual(logs[0]['provider'], 'ollama')
            review_files = list((args.output_dir / 'reviews').rglob('*.json'))
            self.assertEqual(len(review_files), 1)
            self.assertEqual(review_files[0].parent.name, 'qualified_default')
            stored = json.loads(review_files[0].read_text())
            self.assertEqual(stored['accessionNumber'], accession)
            self.assertEqual(stored['review']['classification'], 'QUALIFIED_DEFAULT')

    def test_legacy_input_hash_cache_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accession = '0001104659-19-074388'
            source = root / 'source.jsonl'
            source.write_text(json.dumps(dict(company_id='0000001800',
                accessionNumber=accession, classification='MANUAL_REVIEW')))
            html = '<p>Item 2.04 The issuer failed to pay interest. ' + 'Details. ' * 20 + '</p>'
            html_path = root / ('0000001800_' + accession + '.html')
            html_path.write_text(html)
            text = visible_text(html.encode())
            output = root / 'output'
            reviews = output / 'reviews'
            reviews.mkdir(parents=True)
            legacy = dict(
                review=self.review(), requested_model=DEFAULT_MODEL,
                returned_model=DEFAULT_MODEL, provider='ollama',
                input_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
            (reviews / 'legacy.json').write_text(json.dumps(legacy))
            args = Namespace(input=source, html_dir=root, output_dir=output,
                             model=DEFAULT_MODEL, dry_run=False, limit=0,
                             max_chars=24000, host='http://localhost:11434',
                             num_ctx=32768, timeout=600, think=False,
                             retry_fallbacks=True, refresh=False)
            with patch('mcf.enrichment.item204.reviewers.ollama.request_review') as call, \
                    patch('builtins.print'):
                run(args)
                call.assert_not_called()
            result = json.loads((output / 'classifications.jsonl').read_text())
            self.assertEqual(result['llm_status'], 'cached')
