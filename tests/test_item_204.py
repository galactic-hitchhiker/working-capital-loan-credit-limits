"""Item 2.04 source discovery performs no event classification.

Run from the repository root:
    PYTHONPATH=. .venv/bin/python tests/test_item_204.py [parameters]

Parameters (standard unittest options):
    TEST ...: Optional test class or Class.method names (default: all tests here).
    -v, --verbose: Print individual test names and results.
    -q, --quiet: Print only the summary and failures.
    --locals: Include local variables in failure tracebacks (default: off).
    --durations N: Report the N slowest tests; 0 reports all (default: disabled).
    -f, --failfast: Stop at the first failure or error.
    -b, --buffer: Hide captured stdout/stderr unless a test fails.
    -c, --catch: Finish the current test on Ctrl-C and report results.
    -k PATTERN: Run tests whose names match the substring or wildcard pattern.
    -h, --help: Show command usage and exit.
"""
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from mcf.enrichment.item204.discover import extract_item_204, has_item, iter_item_204, run


class Item204DiscoveryTests(unittest.TestCase):
    def test_exact_item(self):
        self.assertTrue(has_item('1.01; 2.04,9.01', '2.04'))
        self.assertFalse(has_item('12.04', '2.04'))

    def test_section_isolation(self):
        html = '<p>Item 1.01 Other terms.</p><p>Item 2.04 ' + 'The issuer failed to pay interest. ' * 8 + '</p><p>Item 9.01 Exhibits</p>'
        text, status = extract_item_204(html)
        self.assertEqual(status, 'isolated_item_section')
        self.assertNotIn('Other terms', text)
        self.assertIn('failed to pay interest', text)

    def test_inventory_includes_exact_204_forms_and_date_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'CIK0000001800.json').write_text(json.dumps({'name': 'Test'}))
            filings = [dict(form=form, items=items, filingDate='2020-01-01',
                            accessionNumber=f'0001104659-20-{index:06d}', primaryDocument='filing.htm')
                       for index, (form, items) in enumerate([('8-K', '2.04'), ('8-K/A', '2.04'),
                                                             ('8-K', '12.04'), ('10-K', '2.04')])]
            with patch('mcf.enrichment.item204.discover.filing_rows', return_value=(filings, [])):
                rows = list(iter_item_204(root))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all('classification' not in row for row in rows))

    def test_downloader_never_assigns_rule_labels_or_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html_dir = root / 'html'
            html_dir.mkdir()
            record = dict(company_id='0000001800', accessionNumber='0001104659-20-000001',
                          filingDate='2020-01-01', source_url='https://www.sec.gov/filing.htm')
            (html_dir / '0000001800_0001104659-20-000001.html').write_text(
                '<p>Item 2.04 The issuer failed to pay interest. ' + 'Details. ' * 30 + '</p>')
            args = Namespace(submissions=root, output_dir=root / 'source', html_dir=html_dir,
                             start=None, cutoff=None, discover_only=False, offline=True,
                             user_agent='', interval=.25, limit=None)
            with patch('mcf.enrichment.item204.discover.iter_item_204', return_value=iter([record])), patch('builtins.print'):
                run(args)
            saved = json.loads((args.output_dir / 'filings.jsonl').read_text())
            self.assertEqual(saved['status'], 'parsed')
            self.assertIn('failed to pay interest', saved['item_204_text'])
            self.assertNotIn('classification', saved)
            self.assertNotIn('rule_version', saved)
            self.assertNotIn('evidence', saved)
            self.assertEqual(json.loads((args.output_dir / 'audit.json').read_text())['filings'], 1)


if __name__ == '__main__':
    unittest.main()
