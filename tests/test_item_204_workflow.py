"""Wiring checks for the unified Item 2.04 workflow; no network or LLM calls.

Run from the repository root:
    PYTHONPATH=. .venv/bin/python tests/test_item_204_workflow.py [parameters]

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

from mcf.enrichment.item204.workflow import run


class Item204WorkflowTests(unittest.TestCase):
    def test_discovery_feeds_all_filings_to_batch_reviewer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = Namespace(
                submissions=root / "submissions",
                output_dir=root / "output",
                start=None,
                cutoff=None,
                user_agent="Test test@example.com",
                interval=0.25,
                filing_limit=0,
                offline=True,
                model="test-model",
                llm_limit=0,
                dry_run=False,
                refresh=False,
                retry_fallbacks=False,
            )

            def discovery(source_args):
                source_args.output_dir.mkdir(parents=True)
                (source_args.output_dir / "html").mkdir()
                (source_args.output_dir / "filings.jsonl").write_text(
                    json.dumps({"classification": "MANUAL_REVIEW"}) + "\n"
                )
                (source_args.output_dir / "audit.json").write_text(
                    json.dumps({"counts": {"status_parsed": 1}})
                )

            def review(review_args):
                self.assertEqual(review_args.input.parent.name, "source")
                self.assertEqual(review_args.html_dir.name, "html")
                self.assertEqual(review_args.start, args.start)
                self.assertEqual(review_args.cutoff, args.cutoff)
                review_args.output_dir.mkdir(parents=True)
                (review_args.output_dir / "classifications.jsonl").write_text(
                    json.dumps({"classification": "QUALIFIED_DEFAULT"}) + "\n"
                )
                (review_args.output_dir / "audit.json").write_text(
                    json.dumps(
                        {"final_labels": {"QUALIFIED_DEFAULT": 1, "MANUAL_REVIEW": 0}}
                    )
                )

            with patch(
                "mcf.enrichment.item204.workflow.run_discovery", side_effect=discovery
            ) as rule_call, patch(
                "mcf.enrichment.item204.workflow.run_openai_batch", side_effect=review
            ) as llm_call, patch("builtins.print"):
                final_dir = run(args)

            self.assertEqual(final_dir, root / "output" / "final")
            rule_call.assert_called_once()
            llm_call.assert_called_once()
            audit = json.loads((root / "output" / "workflow_audit.json").read_text())
            self.assertEqual(
                audit["final_labels"],
                {"QUALIFIED_DEFAULT": 1, "MANUAL_REVIEW": 0},
            )

            # Cancellation must propagate to callers before inventory/model work.
            final_audit_path = final_dir / "audit.json"
            final_audit = json.loads(final_audit_path.read_text())
            final_audit["interrupted"] = True
            final_audit_path.write_text(json.dumps(final_audit))
            with patch("mcf.enrichment.item204.workflow.run_discovery"), patch(
                "mcf.enrichment.item204.workflow.run_openai_batch"
            ), patch("builtins.print"), self.assertRaises(SystemExit) as stopped:
                run(args)
            self.assertEqual(stopped.exception.code, 130)
            audit = json.loads((root / "output" / "workflow_audit.json").read_text())
            self.assertTrue(audit["interrupted"])


if __name__ == "__main__":
    unittest.main()
