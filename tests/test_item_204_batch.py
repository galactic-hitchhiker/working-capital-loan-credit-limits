"""Batch lifecycle tests with mocked HTTP; no paid requests.

Run from the repository root:
    PYTHONPATH=. .venv/bin/python tests/test_item_204_batch.py [parameters]

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

from mcf.enrichment.item204.reviewers import openai_batch as batch
from mcf.enrichment.item204.reviewers.common import APIReviewError


class BatchReviewTests(unittest.TestCase):
    def test_payment_profile_round_trip(self):
        self.args.payment_failure_only = True
        self.submit()
        path, job, lines = self.result_lines()
        request = json.loads((path.parent / "input.jsonl").read_text().splitlines()[0])
        self.assertIn("Bankruptcy/receivership", request["body"]["instructions"])
        self.collect(lines)
        for row in self.rows():
            self.assertEqual(row["classification"], "QUALIFIED_DEFAULT")
            self.assertEqual(
                row["llm_review"]["settings"]["target"], "disclosed_payment_failure"
            )
        with patch.object(
            batch,
            "api_request",
            side_effect=AssertionError("Cached collection must not call API"),
        ):
            self.assertEqual(batch.run(self.args)["review_counts"], {"cached": 2})

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.jsonl"
        self.records = [
            dict(
                company_id="0000001800",
                accessionNumber=f"0001104659-19-{i:06d}",
                classification="MANUAL_REVIEW",
                filingDate="2019-01-01",
                item_204_text=f"The issuer failed to pay interest on loan {i}.",
            )
            for i in (1, 2)
        ]
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.args = Namespace(
            input=self.source,
            html_dir=self.root,
            output_dir=self.root / "output",
            model="test-model",
            dry_run=False,
            limit=0,
            refresh=False,
            retry_fallbacks=False,
            start=None,
            cutoff=None,
        )
        self.addCleanup(patch.stopall)
        patch("builtins.print").start()
        patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}).start()

    def rows(self):
        return [
            json.loads(line)
            for line in (self.args.output_dir / "classifications.jsonl")
            .read_text()
            .splitlines()
        ]

    def submit(self):
        with (
            patch.object(batch, "upload", return_value="file-input") as upload,
            patch.object(
                batch,
                "api_request",
                return_value={"id": "batch-1", "status": "validating"},
            ) as api,
        ):
            audit = batch.run(self.args)
        upload.assert_called_once()
        self.assertEqual(api.call_args.args[0], "/batches")
        body = json.loads(api.call_args.args[2])
        self.assertEqual(body["endpoint"], "/v1/responses")
        self.assertEqual(body["completion_window"], "24h")
        return audit

    def result_lines(self, invalid=False):
        path, job = batch.load_jobs(self.args.output_dir / "batches")[0]
        inputs = [
            json.loads(line)
            for line in (path.parent / "input.jsonl").read_text().splitlines()
        ]
        lines = []
        for request in reversed(inputs):
            text = request["body"]["input"].split("\n", 1)[1]
            review = dict(
                classification="QUALIFIED_DEFAULT",
                event_type="PAYMENT_FAILURE",
                certainty="HIGH",
                reason="Explicit missed payment",
                evidence_quotes=["invented" if invalid else text],
            )
            payload = dict(
                status="completed",
                id=request["custom_id"],
                model="test-model",
                usage={"input_tokens": 10},
                output=[
                    {"content": [{"type": "output_text", "text": json.dumps(review)}]}
                ],
            )
            lines.append(
                dict(
                    custom_id=request["custom_id"],
                    error=None,
                    response={"status_code": 200, "body": payload},
                )
            )
        return path, job, lines

    def collect(self, lines, status="completed", errors=None):
        def api(path, *args, **kwargs):
            if path == "/batches/batch-1":
                return {
                    "status": status,
                    "output_file_id": "file-output",
                    "error_file_id": None,
                    "errors": errors,
                }
            if path == "/files/file-output/content":
                return "".join(json.dumps(line) + "\n" for line in lines)
            raise AssertionError(path)

        with patch.object(batch, "api_request", side_effect=api):
            return batch.run(self.args)

    def test_submit_pending_then_collect_out_of_order_and_resume_offline(self):
        audit = self.submit()
        self.assertEqual(audit["batch_pending"], 2)
        self.assertEqual([r["llm_status"] for r in self.rows()], ["batch_pending"] * 2)
        self.assertEqual(list((self.args.output_dir / "reviews").rglob("*.json")), [])
        path, job, lines = self.result_lines()
        for line in (path.parent / "input.jsonl").read_text().splitlines():
            self.assertTrue(json.loads(line)["body"]["text"]["format"]["strict"])
        audit = self.collect(lines)
        self.assertEqual(audit["batch_pending"], 0)
        rows = self.rows()
        self.assertEqual([r["classification"] for r in rows], ["QUALIFIED_DEFAULT"] * 2)
        for row in rows:
            self.assertIn(
                row["item_204_text"], row["llm_review"]["review"]["evidence_quotes"][0]
            )
            self.assertEqual(row["llm_review"]["batch_id"], "batch-1")
        self.assertEqual(len(json.loads(path.read_text())["consumed"]), 2)
        with (
            patch.object(batch, "api_request") as api,
            patch.object(batch, "upload") as upload,
        ):
            audit = batch.run(self.args)
        api.assert_not_called()
        upload.assert_not_called()
        self.assertEqual(audit["review_counts"], {"cached": 2})
        self.assertEqual(
            len((self.args.output_dir / "review_log.jsonl").read_text().splitlines()), 2
        )
        self.assertEqual(
            self.source.read_text(), "".join(json.dumps(r) + "\n" for r in self.records)
        )

    def test_pending_rerun_never_submits_again_even_with_refresh(self):
        self.submit()
        self.args.refresh = True
        with (
            patch.object(
                batch, "api_request", return_value={"status": "in_progress"}
            ) as api,
            patch.object(batch, "upload") as upload,
        ):
            audit = batch.run(self.args)
        upload.assert_not_called()
        api.assert_called_once_with("/batches/batch-1", "test-key")
        self.assertEqual(audit["batch_pending"], 2)
        self.assertEqual(len(batch.load_jobs(self.args.output_dir / "batches")), 1)

    def test_dry_run_avoids_all_network_and_job_creation(self):
        self.args.dry_run = True
        with (
            patch.object(batch, "api_request") as api,
            patch.object(batch, "upload") as upload,
        ):
            audit = batch.run(self.args)
        api.assert_not_called()
        upload.assert_not_called()
        self.assertFalse((self.args.output_dir / "batches").exists())
        self.assertEqual(audit["review_counts"], {"ready": 2})

    def test_invalid_quotes_are_conservative_terminal_reviews(self):
        self.submit()
        _, _, lines = self.result_lines(invalid=True)
        self.collect(lines)
        self.assertEqual(
            [r["llm_status"] for r in self.rows()], ["fallback_validation_error"] * 2
        )
        self.assertTrue(
            all(r["classification"] == "MANUAL_REVIEW" for r in self.rows())
        )

    def test_manual_answer_requires_consistent_uncertainty(self):
        self.submit()
        _, _, lines = self.result_lines()
        message = lines[0]["response"]["body"]["output"][0]["content"][0]
        review = json.loads(message["text"])
        review.update(
            classification="MANUAL_REVIEW", event_type="UNCERTAIN", certainty="HIGH"
        )
        message["text"] = json.dumps(review)
        self.collect(lines)
        self.assertEqual(
            [r["llm_status"] for r in self.rows()],
            ["reviewed", "fallback_validation_error"],
        )

    def test_partial_expiration_imports_success_and_marks_missing_retryable(self):
        self.submit()
        _, _, lines = self.result_lines()
        self.collect(lines[:1], status="expired")
        rows = self.rows()
        self.assertEqual(
            [r["llm_status"] for r in rows], ["fallback_provider_error", "reviewed"]
        )
        self.args.retry_fallbacks = True
        self.submit()
        jobs = batch.load_jobs(self.args.output_dir / "batches")
        self.assertEqual(sorted(len(job["custom_ids"]) for _, job in jobs), [1, 2])

    def test_request_error_does_not_block_other_results_and_redacts_key(self):
        self.submit()
        _, _, lines = self.result_lines()
        lines[0]["response"] = None
        lines[0]["error"] = {"code": "batch_expired", "message": "failed test-key"}
        self.collect(lines)
        self.assertEqual(
            [r["llm_status"] for r in self.rows()],
            ["reviewed", "fallback_provider_error"],
        )
        self.assertNotIn(
            "test-key", (self.args.output_dir / "classifications.jsonl").read_text()
        )

    def test_failed_validation_without_files_marks_all_requests(self):
        self.submit()
        with patch.object(
            batch,
            "api_request",
            return_value={"status": "failed", "errors": {"message": "invalid model"}},
        ):
            batch.run(self.args)
        self.assertEqual(
            [r["llm_status"] for r in self.rows()], ["fallback_provider_error"] * 2
        )
        self.assertIn("invalid model", self.rows()[0]["llm_error"])

    def test_ambiguous_creation_blocks_duplicate_and_can_recover(self):
        with (
            patch.object(batch, "upload", return_value="file-input"),
            patch.object(batch, "api_request", side_effect=TimeoutError("timed out")),
        ):
            with self.assertRaises(TimeoutError):
                batch.run(self.args)
        with (
            patch.object(batch, "api_request") as api,
            self.assertRaisesRegex(ValueError, "--batch-id"),
        ):
            batch.run(self.args)
        api.assert_not_called()
        self.args.batch_id = "batch-1"
        with (
            patch.object(
                batch,
                "api_request",
                return_value={
                    "id": "batch-1",
                    "status": "in_progress",
                    "input_file_id": "file-input",
                    "endpoint": batch.ENDPOINT,
                },
            ),
            patch.object(batch, "upload") as upload,
        ):
            batch.run(self.args)
        upload.assert_not_called()
        self.assertEqual(
            batch.load_jobs(self.args.output_dir / "batches")[0][1]["batch_id"],
            "batch-1",
        )

    def test_refresh_creates_new_job_after_completed_review(self):
        self.submit()
        _, _, lines = self.result_lines()
        self.collect(lines)
        self.args.refresh = True
        self.submit()
        self.assertEqual(len(batch.load_jobs(self.args.output_dir / "batches")), 2)

    def test_manual_retry_preserves_resolved_and_resumes_once_per_configuration(self):
        self.submit()
        _, _, lines = self.result_lines()
        content = lines[0]["response"]["body"]["output"][0]["content"][0]
        content["text"] = json.dumps(
            dict(
                classification="MANUAL_REVIEW",
                event_type="UNCERTAIN",
                certainty="UNCERTAIN",
                reason="The evidence is incomplete.",
                evidence_quotes=[],
            )
        )
        self.collect(lines)
        original = self.rows()[0]["llm_review"]
        self.args.retry_manual_review = True
        self.args.model = "gpt-6-sol"
        self.args.max_output_tokens = 8000
        self.args.reasoning_effort = "medium"
        self.submit()
        path, job = next(
            (p, j)
            for p, j in batch.load_jobs(self.args.output_dir / "batches")
            if not j["consumed"]
        )
        request = json.loads((path.parent / "input.jsonl").read_text())
        self.assertEqual(len(job["custom_ids"]), 1)
        self.assertEqual(request["body"]["model"], "gpt-6-sol")
        self.assertEqual(request["body"]["max_output_tokens"], 8000)
        self.assertIn("loan 2", request["body"]["input"])
        self.assertEqual(self.rows()[0]["llm_review"], original)
        with (
            patch.object(batch, "api_request", return_value={"status": "in_progress"}),
            patch.object(batch, "upload") as upload,
        ):
            batch.run(self.args)
        upload.assert_not_called()
        lines[0]["custom_id"] = request["custom_id"]
        self.collect(lines[:1])
        self.assertEqual(self.rows()[0]["llm_review"], original)
        self.assertEqual(self.rows()[1]["classification"], "MANUAL_REVIEW")
        self.assertEqual(self.rows()[1]["llm_review"]["requested_model"], "gpt-6-sol")
        with (
            patch.object(batch, "api_request") as api,
            patch.object(batch, "upload") as upload,
        ):
            batch.run(self.args)
        api.assert_not_called()
        upload.assert_not_called()

    def test_manual_retry_includes_validation_failures_but_not_missing_text(self):
        self.records[0]["item_204_text"] = ""
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.submit()
        _, _, lines = self.result_lines(invalid=True)
        self.collect(lines)
        self.args.retry_manual_review = True
        self.args.max_output_tokens = 8000
        self.submit()
        jobs = batch.load_jobs(self.args.output_dir / "batches")
        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(len(j["custom_ids"]) == 1 for _, j in jobs))
        self.assertEqual(
            self.rows()[0]["llm_review"]["status"], "fallback_missing_input"
        )

    def test_manual_retry_requires_existing_reviews_and_rejects_refresh(self):
        self.args.retry_manual_review = True
        with (
            patch.object(batch, "api_request") as api,
            self.assertRaisesRegex(ValueError, "requires saved OpenAI reviews"),
        ):
            batch.run(self.args)
        api.assert_not_called()
        from mcf.enrichment.item204.reviewers.common import check_args

        command = batch.parser()
        for conflict in ("--refresh", "--retry-fallbacks"):
            args = command.parse_args(["--retry-manual-review", conflict])
            with self.assertRaises(SystemExit):
                check_args(command, args)

    def test_split_limits_and_identical_request_deduplication(self):
        self.records[1]["item_204_text"] = self.records[0]["item_204_text"]
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.submit()
        self.assertEqual(
            len(batch.load_jobs(self.args.output_dir / "batches")[0][1]["custom_ids"]),
            1,
        )
        requests = {str(i): batch.request_line(str(i), "test") for i in range(3)}
        with patch.object(batch, "MAX_REQUESTS", 2):
            jobs = batch.prepare_jobs(self.root, requests)
        self.assertEqual([len(job["custom_ids"]) for _, job in jobs], [2, 1])
        line_size = len((json.dumps(next(iter(requests.values()))) + "\n").encode())
        with patch.object(batch, "MAX_BYTES", line_size):
            self.assertEqual(len(batch.prepare_jobs(self.root, requests)), 3)

    def test_small_jobs_are_submitted_sequentially(self):
        self.args.batch_max_requests = 1
        self.submit()
        jobs = batch.load_jobs(self.args.output_dir / "batches")
        self.assertEqual(
            sorted(j["status"] for _, j in jobs), ["prepared", "validating"]
        )
        _active_path, active_job = next(
            (p, j) for p, j in jobs if j["status"] == "validating"
        )
        with (
            patch.object(
                batch, "api_request", return_value={"status": "in_progress"}
            ) as api,
            patch.object(batch, "upload") as upload,
        ):
            batch.run(self.args)
        upload.assert_not_called()
        api.assert_called_once_with("/batches/batch-1", "test-key")
        result = {
            "custom_id": active_job["custom_ids"][0],
            "error": None,
            "response": {
                "status_code": 200,
                "body": {
                    "status": "completed",
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": json.dumps(
                                        {
                                            "classification": "MANUAL_REVIEW",
                                            "event_type": "UNCERTAIN",
                                            "certainty": "UNCERTAIN",
                                            "reason": "Incomplete evidence",
                                            "evidence_quotes": [],
                                        }
                                    ),
                                }
                            ]
                        }
                    ],
                },
            },
        }

        def api(path, *args, **kwargs):
            if path == "/batches/batch-1":
                return {"status": "completed", "output_file_id": "finished-output"}
            if path == "/files/finished-output/content":
                return json.dumps(result) + "\n"
            if path == "/batches":
                return {"id": "batch-2", "status": "validating"}
            if path == "/batches/batch-2":
                return {"status": "in_progress"}
            raise AssertionError(path)

        with (
            patch.object(batch, "api_request", side_effect=api),
            patch.object(batch, "upload", return_value="next-input") as upload,
        ):
            batch.run(self.args)
        upload.assert_called_once()
        self.assertEqual(
            sorted(
                j["status"]
                for _, j in batch.load_jobs(self.args.output_dir / "batches")
            ),
            ["completed", "in_progress"],
        )

    def test_queue_rejected_large_job_is_split_without_filing_failures(self):
        self.submit()
        self.args.batch_max_requests = 1

        def api(path, *args, **kwargs):
            if path == "/batches/batch-1":
                return {
                    "status": "failed",
                    "errors": {"data": [{"message": "Enqueued token limit reached"}]},
                }
            if path == "/batches":
                return {"id": "batch-small", "status": "validating"}
            if path == "/batches/batch-small":
                return {"status": "in_progress"}
            raise AssertionError(path)

        with (
            patch.object(batch, "api_request", side_effect=api),
            patch.object(batch, "upload", return_value="small-input") as upload,
        ):
            audit = batch.run(self.args)
        upload.assert_called_once()
        self.assertEqual(audit["batch_pending"], 2)
        self.assertTrue(all(r["llm_status"] == "batch_pending" for r in self.rows()))
        jobs = batch.load_jobs(self.args.output_dir / "batches")
        self.assertEqual(len(jobs), 3)
        old = next(j for _, j in jobs if j["status"] == "failed")
        self.assertEqual(old["consumed"], sorted(old["custom_ids"]))
        self.assertEqual(len(old["replaced_by"]), 2)

    def test_full_large_filing_is_submitted_without_extract_fallback(self):
        full = (
            "Item 2.04 "
            + "Filing detail. " * 12000
            + "The issuer failed to pay interest."
        )
        record = self.records[0]
        path = self.root / f"{record['company_id']}_{record['accessionNumber']}.html"
        path.write_text("<p>" + full + "</p>")
        self.submit()
        manifest, _ = batch.load_jobs(self.args.output_dir / "batches")[0]
        bodies = [
            json.loads(line)["body"]
            for line in (manifest.parent / "input.jsonl").read_text().splitlines()
        ]
        self.assertIn(
            "UNTRUSTED SEC FILING TEXT:\n" + full, [body["input"] for body in bodies]
        )
        self.assertEqual(self.rows()[0]["llm_input_scope"], "full_filing")
        self.assertGreater(len(full), 100000)

    def test_missing_input_stays_explicit_and_other_files_are_submitted(self):
        self.records[0]["item_204_text"] = ""
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.submit()
        self.assertEqual(
            [r["llm_status"] for r in self.rows()],
            ["fallback_missing_input", "batch_pending"],
        )
        _, job = batch.load_jobs(self.args.output_dir / "batches")[0]
        self.assertEqual(len(job["custom_ids"]), 1)

    def test_cli_defaults_process_all_and_removed_options_are_absent(self):
        command = batch.parser()
        args = command.parse_args([])
        self.assertEqual(args.model, "gpt-6-luna")
        self.assertEqual(args.limit, 0)
        self.assertIsNone(args.start)
        self.assertIsNone(args.cutoff)
        flags = {flag for action in command._actions for flag in action.option_strings}
        for removed in (
            "--provider",
            "--max-chars",
            "--budget-usd",
            "--batch-input-price",
            "--host",
            "--num-ctx",
        ):
            self.assertNotIn(removed, flags)

    def test_all_prior_labels_are_reviewed_and_metadata_only_input_works(self):
        self.records[0]["classification"] = "NON_DEFAULT"
        self.records[0]["llm_review"] = {"review": {"classification": "NON_DEFAULT"}}
        self.records[1]["classification"] = "QUALIFIED_DEFAULT"
        metadata_only = dict(
            self.records[1],
            accessionNumber="0001104659-19-000003",
            item_204_text="The issuer failed to pay interest on loan 3.",
        )
        metadata_only.pop("classification")
        self.records.append(metadata_only)
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.submit()
        self.assertEqual(
            [r["classification"] for r in self.rows()], ["MANUAL_REVIEW"] * 3
        )
        self.assertTrue(all("llm_review" not in row for row in self.rows()))
        _, job = batch.load_jobs(self.args.output_dir / "batches")[0]
        self.assertEqual(len(job["custom_ids"]), 3)
        _, _, lines = self.result_lines()
        self.collect(lines)
        self.assertEqual([r["llm_status"] for r in self.rows()], ["reviewed"] * 3)

    def test_removed_provider_cache_cannot_bypass_openai_review(self):
        cache = self.args.output_dir / "reviews"
        cache.mkdir(parents=True)
        (cache / "old.json").write_text(
            json.dumps(
                {
                    "company_id": self.records[0]["company_id"],
                    "accessionNumber": self.records[0]["accessionNumber"],
                    "provider": "legacy_provider",
                    "review": {"classification": "NON_DEFAULT"},
                }
            )
        )
        self.submit()
        self.assertEqual([r["llm_status"] for r in self.rows()], ["batch_pending"] * 2)

    def test_newly_available_html_retries_missing_input_without_refresh(self):
        self.records[0]["item_204_text"] = ""
        self.source.write_text("".join(json.dumps(r) + "\n" for r in self.records))
        self.submit()
        (self.root / "0000001800_0001104659-19-000001.html").write_text(
            "<p>Item 2.04 The issuer failed to pay principal.</p>"
        )
        with (
            patch.object(batch, "api_request", return_value={"status": "in_progress"}),
            patch.object(batch, "upload") as upload,
        ):
            batch.run(self.args)
        upload.assert_not_called()
        self.assertEqual([r["llm_status"] for r in self.rows()], ["batch_pending"] * 2)
        self.assertEqual(len(batch.load_jobs(self.args.output_dir / "batches")), 2)

    def test_limit_and_date_bounds_are_applied_before_submission(self):
        self.args.limit = 1
        self.submit()
        self.assertEqual(
            [r["llm_status"] for r in self.rows()], ["batch_pending", "deferred_limit"]
        )

    def test_reasoning_and_output_cap_are_in_paid_request_identity(self):
        normal = batch.request_line("text", "gpt-6-luna")
        limited = batch.request_line("text", "gpt-6-luna", "low", 1000)
        self.assertNotEqual(normal["custom_id"], limited["custom_id"])
        self.assertEqual(normal["body"]["reasoning"], {"effort": "medium"})
        self.assertEqual(limited["body"]["max_output_tokens"], 1000)
        nonreasoning = batch.request_line("text", "gpt-4.1-mini")
        self.assertNotIn("reasoning", nonreasoning["body"])


class BatchWorkflowTests(unittest.TestCase):
    def test_batch_provider_routes_and_reports_pending(self):
        from mcf.enrichment.item204 import workflow

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = workflow.parser().parse_args(
                [
                    "--submissions",
                    str(root),
                    "--output-dir",
                    str(root / "output"),
                    "--model",
                    "test-model",
                    "--batch-id",
                    "batch-recover",
                ]
            )

            def discovery(value):
                value.output_dir.mkdir(parents=True)
                (value.output_dir / "filings.jsonl").write_text("{}\n")
                (value.output_dir / "audit.json").write_text(
                    json.dumps({"counts": {"MANUAL_REVIEW": 1}})
                )

            def review(value):
                self.assertEqual(value.batch_id, "batch-recover")
                self.assertEqual(value.max_output_tokens, 3000)
                self.assertEqual(value.reasoning_effort, "medium")
                self.assertEqual(value.input.parent.name, "source")
                value.output_dir.mkdir()
                (value.output_dir / "classifications.jsonl").write_text("{}\n")
                (value.output_dir / "audit.json").write_text(
                    json.dumps(
                        {
                            "final_labels": {"MANUAL_REVIEW": 1},
                            "batch_pending": 1,
                        }
                    )
                )

            with (
                patch.object(workflow, "run_discovery", side_effect=discovery),
                patch.object(
                    workflow, "run_openai_batch", side_effect=review
                ) as reviewer,
                patch("builtins.print"),
            ):
                workflow.run(args)
            reviewer.assert_called_once()
            audit = json.loads((args.output_dir / "workflow_audit.json").read_text())
            self.assertEqual(audit["batch_pending"], 1)

    def test_composite_stops_before_training_pending_batches(self):
        from mcf.workflows import payment_default_proxy as workflow
        from mcf.data.empirical import PAYMENT_DEFAULT_PROXY_TARGET

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audit.json").write_text(
                json.dumps(
                    {
                        "provider": "openai_batch",
                        "review_counts": {"batch_pending": 1},
                    }
                )
            )
            args = Namespace(
                config=root / "config",
                output_dir=root / "output",
                item_204_results=root,
                statement_facts=root,
            )
            with (
                patch.object(
                    workflow,
                    "load_design",
                    return_value={
                        "event_type": PAYMENT_DEFAULT_PROXY_TARGET,
                        "observed_as_of": "2026-01-01",
                    },
                ),
                patch.object(workflow, "inventory") as inventory,
                patch.object(workflow, "train") as train,
            ):
                with self.assertRaisesRegex(ValueError, "pending"):
                    workflow.run(args)
            inventory.assert_not_called()
            train.assert_not_called()


if __name__ == "__main__":
    unittest.main()
