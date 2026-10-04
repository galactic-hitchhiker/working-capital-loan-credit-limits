"""Wiring checks for the unified Item 2.04 workflow; no network or LLM calls."""

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from mcf.enrichment.item204.workflow import run


class Item204WorkflowTests(unittest.TestCase):
    def test_rules_feed_only_manual_cases_to_selected_provider(self):
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
                provider="ollama",
                model="test-model",
                llm_limit=0,
                max_chars=24000,
                dry_run=False,
                refresh=False,
                retry_fallbacks=False,
                host="http://localhost:11434",
                num_ctx=32768,
                timeout=600,
                think=False,
            )

            def rules(rule_args):
                rule_args.output_dir.mkdir(parents=True)
                (rule_args.output_dir / "html").mkdir()
                (rule_args.output_dir / "classifications.jsonl").write_text(
                    json.dumps({"classification": "MANUAL_REVIEW"}) + "\n"
                )
                (rule_args.output_dir / "audit.json").write_text(
                    json.dumps({"counts": {"MANUAL_REVIEW": 1}})
                )

            def ollama(review_args):
                self.assertEqual(review_args.input.parent.name, "rules")
                self.assertEqual(review_args.html_dir.name, "html")
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
                "mcf.enrichment.item204.workflow.run_rules", side_effect=rules
            ) as rule_call, patch(
                "mcf.enrichment.item204.workflow.run_ollama", side_effect=ollama
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


if __name__ == "__main__":
    unittest.main()
