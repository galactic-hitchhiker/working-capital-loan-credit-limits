"""Check that the staged coordinator preserves the existing study builders."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from mcf.data.empirical import BANKRUPTCY_PAYMENT_TARGET, ITEM_103_TARGET
from mcf.workflows import pipeline


class PipelineTests(unittest.TestCase):
    def test_inventory_screens_issuers_then_imports_notes_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            archives = dataset / "financial_statements" / "archives"
            archives.mkdir(parents=True)
            source = archives / "2025q1_notes.zip"
            source.touch()
            output = root / "run"
            args = pipeline.parser().parse_args([
                "inventory", "--dataset", str(dataset), "--output-dir", str(output),
            ])

            def inventory_stub(dataset_path, destination, cutoff, *, target):
                destination.mkdir(parents=True)
                (destination / "issuer_inventory.csv").write_text("company_id,screen\n")
                (destination / "inventory_audit.json").write_text(json.dumps({
                    "target": target, "cutoff": str(cutoff), "errors": [],
                }))
                return {"errors": []}

            with patch.object(pipeline, "inventory", side_effect=inventory_stub) as build, patch.object(
                pipeline, "extract"
            ) as extract:
                result = pipeline.build_source_inventory(args)
            self.assertEqual(result, dataset / "statement_facts" / "companies")
            self.assertEqual(build.call_args.args[:3], (
                dataset, output / "source_inventory", date(2026, 9, 7),
            ))
            self.assertEqual(build.call_args.kwargs["target"], ITEM_103_TARGET)
            self.assertEqual(extract.call_args.args, (
                [source], dataset,
                output / "source_inventory" / "issuer_inventory.csv",
                dataset / "statement_facts",
            ))

    def test_panel_uses_supplied_reviews_and_statements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviews = root / "reviews"
            reviews.mkdir()
            (reviews / "classifications.jsonl").write_text(json.dumps({
                "company_id": "0000000001", "accessionNumber": "filing-1",
                "classification": "NON_DEFAULT",
            }) + "\n")
            statements = root / "statements"
            statements.mkdir()
            output = root / "run"
            args = pipeline.parser().parse_args([
                "panel", "--dataset", str(root / "dataset"),
                "--output-dir", str(output),
                "--disclosure-results", str(reviews),
                "--statement-facts", str(statements),
            ])
            with patch.object(pipeline, "inventory") as inventory, patch.object(
                pipeline, "panel", return_value={"rows": 1}
            ) as panel:
                result = pipeline.build_panel(args)
            self.assertEqual(result, {"rows": 1})
            self.assertEqual(inventory.call_args.args[:4], (
                root / "dataset", output / "inventory", date(2026, 9, 7), reviews,
            ))
            self.assertEqual(inventory.call_args.kwargs["target"], BANKRUPTCY_PAYMENT_TARGET)
            self.assertEqual(panel.call_args.kwargs["statement_facts"], statements)

    def test_classify_reuses_supplied_results_without_openai(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviews = root / "reviews"
            reviews.mkdir()
            (reviews / "classifications.jsonl").write_text(json.dumps({
                "company_id": "0000000001", "accessionNumber": "filing-1",
                "classification": "NON_DEFAULT",
            }) + "\n")
            args = pipeline.parser().parse_args([
                "classify", "--output-dir", str(root / "run"),
                "--disclosure-results", str(reviews),
            ])
            with patch.object(pipeline, "review_item_204") as review:
                self.assertEqual(pipeline.classify(args), reviews)
            review.assert_not_called()

    def test_pending_reviews_stop_panel_even_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reviews = root / "reviews"
            reviews.mkdir()
            (reviews / "classifications.jsonl").write_text("")
            (reviews / "audit.json").write_text(json.dumps({
                "provider": "openai_batch", "review_counts": {"batch_pending": 1},
            }))
            args = pipeline.parser().parse_args([
                "panel", "--output-dir", str(root / "run"),
                "--disclosure-results", str(reviews),
            ])
            with patch.object(pipeline, "inventory") as inventory:
                with self.assertRaisesRegex(ValueError, "pending"):
                    pipeline.build_panel(args)
            inventory.assert_not_called()

    def test_all_runs_stages_in_order_without_changing_the_builders(self):
        args = pipeline.parser().parse_args([
            "all", "--output-dir", "results/new_run", "--skip-download",
        ])
        called = []
        with patch.object(pipeline, "build_source_inventory", side_effect=lambda _: called.append("inventory")), patch.object(
            pipeline, "classify", side_effect=lambda _: called.append("classify")
        ), patch.object(
            pipeline, "build_panel", side_effect=lambda _: called.append("panel")
        ), patch.object(
            pipeline, "train", side_effect=lambda _: called.append("train")
        ):
            pipeline.run(args)
        self.assertEqual(called, ["inventory", "classify", "panel", "train"])


if __name__ == "__main__":
    unittest.main()
