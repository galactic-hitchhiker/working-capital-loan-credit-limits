"""Check recurrent payment labels and strict-review isolation without API calls.

Run: .venv/bin/python -m unittest discover -s tests -p test_payment_failure.py
Parameters: -v prints test names; -q prints only the summary; -f stops on failure;
    -k PATTERN selects matching tests; -h shows standard unittest options.
"""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from mcf.common import FEATURES, load_design, read_csv
from mcf.data.empirical import inventory, panel
from mcf.data.payment_failure import TARGET, BANKRUPTCY_PAYMENT_TARGET, REVIEW_TARGET, payment_disclosures, episode_label
from mcf.enrichment.item204.discover import iter_item_204
from mcf.enrichment.item204.reviewers.common import cached_decision_index
from mcf.enrichment.item204.reviewers.openai_batch import parse_review_response, review_body


def filing(number, filed, items="2.04", form="8-K"):
    return dict(accessionNumber=f"0000000001-25-{number:06d}", filingDate=filed,
                reportDate=filed, items=items, form=form, primaryDocument="report.htm")


def review(f, classification="QUALIFIED_DEFAULT", event_type="PAYMENT_FAILURE"):
    return dict(company_id="0000000001", accessionNumber=f["accessionNumber"],
                filingDate=f["filingDate"], classification=classification,
                llm_review=dict(settings={"target": REVIEW_TARGET},
                                review=dict(classification=classification, event_type=event_type,
                                            certainty="HIGH", evidence_quotes=["Missed interest payment."])))


class PaymentFailureTests(unittest.TestCase):
    def test_composite_includes_unreviewed_item_103_and_only_payment_item_204(self):
        fs = [filing(1, "2025-01-01", "1.03"), filing(2, "2025-02-01", "1.03,2.04"),
              filing(3, "2025-06-01"), filing(4, "2025-07-01"), filing(5, "2025-08-01")]
        rows = {}
        for f, classification, event_type in [(fs[1], "MANUAL_REVIEW", "UNCERTAIN"),
                                             (fs[2], "QUALIFIED_DEFAULT", "PAYMENT_FAILURE"),
                                             (fs[3], "QUALIFIED_DEFAULT", "ACCELERATION"),
                                             (fs[4], "QUALIFIED_DEFAULT", "ENFORCEMENT")]:
            row = review(f, classification, event_type)
            row["llm_review"].update(provider="openai_batch", settings={})
            rows[("0000000001", f["accessionNumber"])] = row
        events, unknown, counts = payment_disclosures("0000000001", fs, rows, 90, include_item_103=True)
        self.assertEqual([e["accessionNumber"] for e in events], [f["accessionNumber"] for f in fs[:3]])
        self.assertEqual([e["is_episode_start"] for e in events], [True, False, True])
        self.assertTrue(all(e["target"] == BANKRUPTCY_PAYMENT_TARGET for e in events))
        self.assertTrue(all(BANKRUPTCY_PAYMENT_TARGET in e["episode_id"] for e in events))
        self.assertEqual([e["accessionNumber"] for e in unknown], [f["accessionNumber"] for f in fs[3:]])
        self.assertEqual(counts["item_103_automatic"], 2)
        self.assertEqual(counts["combined_disclosures"], 3)
        self.assertEqual(counts["payment_failure_disclosures"], 1)
        self.assertFalse(events[0]["item_204_payment_evidence"])

    def test_composite_103_overrides_negative_204_review_without_duplicate_event(self):
        f = filing(1, "2025-02-01", "1.03,2.04")
        rows = {("0000000001", f["accessionNumber"]): review(f, "NON_DEFAULT", "BENIGN")}
        events, unknown, _ = payment_disclosures("0000000001", [f], rows, 90, include_item_103=True)
        self.assertEqual(len(events), 1)
        self.assertFalse(unknown)
        self.assertEqual(events[0]["event_component"], "ITEM_1_03")
        self.assertFalse(events[0]["item_204_payment_evidence"])

    def test_exploratory_config_keeps_target_and_chronology(self):
        configs = Path(__file__).resolve().parents[1] / "configs"
        standard = load_design(configs / "study.disclosed_payment_failure.json")
        exploratory = load_design(configs / "study.disclosed_payment_failure.exploratory.json")
        self.assertEqual(standard["min_event_companies"], 10)
        self.assertEqual(standard["min_class_count"], 10)
        self.assertEqual(exploratory["min_event_companies"], 3)
        self.assertEqual(exploratory["min_class_count"], 5)
        self.assertTrue(exploratory["exploratory_low_event"])
        for key in ("event_type", "horizon_days", "episode_gap_days", "features", "start", "end",
                    "tuning_start", "calibration_start", "selection_start", "test_start", "observed_as_of"):
            self.assertEqual(standard[key], exploratory[key])

    def events(self, filings):
        reviews = {("0000000001", f["accessionNumber"]): review(f) for f in filings}
        return payment_disclosures("0000000001", filings, reviews, 90)

    def label(self, events=(), unknown=(), decision=date(2025, 1, 1), last=date(2025, 12, 31)):
        return episode_label(decision, events, unknown, last, date(2026, 9, 7), 90)

    def test_both_items_and_recurrent_episodes(self):
        fs = [filing(1, "2025-02-01", "1.03"), filing(2, "2025-03-01", "1.03,2.04"),
              filing(3, "2025-05-30"), filing(4, "2025-08-30")]
        events, unknown, counts = self.events(fs)
        self.assertEqual(len(events), 4)
        self.assertEqual(counts["episodes"], 2)
        self.assertEqual([e["is_episode_start"] for e in events], [True, False, False, True])
        self.assertEqual(events[0]["episode_id"], events[2]["episode_id"])
        self.assertNotEqual(events[0]["episode_id"], events[3]["episode_id"])
        self.assertFalse(unknown)

    def test_bankruptcy_alone_is_not_payment_failure(self):
        f = filing(1, "2025-02-01", "1.03")
        result = payment_disclosures("0000000001", [f],
                                    {("0000000001", f["accessionNumber"]): review(f, "NON_DEFAULT", "BENIGN")}, 90)
        self.assertEqual(result[0], [])
        self.assertEqual(self.label()[0], 0)

    def test_missing_and_manual_reviews_are_unresolved(self):
        fs = [filing(1, "2025-02-01", "1.03"), filing(2, "2025-02-02")]
        rows = {("0000000001", fs[1]["accessionNumber"]): review(fs[1], "MANUAL_REVIEW", "UNCERTAIN")}
        events, unknown, counts = payment_disclosures("0000000001", fs, rows, 90)
        self.assertFalse(events)
        self.assertEqual(len(unknown), 2)
        self.assertEqual(counts["missing_review"], 1)

    def test_rule_only_or_strict_acceleration_reviews_rejected(self):
        f = filing(1, "2025-02-01")
        row = review(f)
        row["llm_review"]["settings"] = {}
        with self.assertRaisesRegex(ValueError, "earlier OpenAI"):
            payment_disclosures("0000000001", [f], {("0000000001", f["accessionNumber"]): row}, 90)
        with self.assertRaisesRegex(ValueError, "PAYMENT_FAILURE"):
            payment_disclosures("0000000001", [f], {("0000000001", f["accessionNumber"]): review(f, event_type="ACCELERATION")}, 90)

    def test_reuse_legacy_payment_and_benign_but_censor_other_distress(self):
        fs = [filing(i, f"2025-0{i}-01") for i in range(1, 6)]
        categories = [("QUALIFIED_DEFAULT", "PAYMENT_FAILURE"), ("NON_DEFAULT", "BENIGN"),
                      ("QUALIFIED_DEFAULT", "ACCELERATION"), ("QUALIFIED_DEFAULT", "ENFORCEMENT"),
                      ("MANUAL_REVIEW", "UNCERTAIN")]
        rows = {}
        for f, (classification, event_type) in zip(fs, categories):
            row = review(f, classification, event_type)
            row["llm_review"].update(provider="openai_batch", settings={"context_version": "old"})
            rows[("0000000001", f["accessionNumber"])] = row
        # A filing containing both items can reuse its actual 2.04 review.
        fs[0]["items"] = "1.03,2.04"
        fs.append(filing(6, "2025-06-01", "1.03"))
        events, unknown, counts = payment_disclosures("0000000001", fs, rows, 90)
        self.assertEqual([e["accessionNumber"] for e in events], [fs[0]["accessionNumber"]])
        self.assertEqual(events[0]["review_definition"], "legacy_item_204")
        self.assertEqual([f["accessionNumber"] for f in unknown], [f["accessionNumber"] for f in fs[2:]])
        self.assertEqual(counts["legacy_payment_failure_reused"], 1)
        self.assertEqual(counts["legacy_non_default_reused"], 1)
        self.assertEqual(counts["legacy_non_payment_unresolved"], 2)

    def test_legacy_review_cannot_qualify_item_103_only(self):
        f = filing(1, "2025-02-01", "1.03")
        row = review(f)
        row["llm_review"].update(provider="openai_batch", settings={})
        with self.assertRaisesRegex(ValueError, "earlier OpenAI Item 2.04"):
            payment_disclosures("0000000001", [f], {("0000000001", f["accessionNumber"]): row}, 90)

    def test_horizon_inclusive_and_same_day_excluded(self):
        for filed, expected in [("2025-03-02", 1), ("2025-03-03", 0), ("2025-01-01", None)]:
            events, _, _ = self.events([filing(1, filed)])
            self.assertEqual(self.label(events)[0], expected)

    def test_washout_reentry_and_future_do_not_change_eligibility(self):
        fs = [filing(1, "2025-01-01"), filing(2, "2025-06-01")]
        events, _, _ = self.events(fs)
        self.assertIsNone(self.label(events, decision=date(2025, 4, 1))[0])
        self.assertEqual(self.label(events, decision=date(2025, 4, 2))[0], 1)
        self.assertEqual(self.label(events[:1], decision=date(2025, 4, 2))[0], 0)
        self.assertEqual(self.label(events, decision=date(2025, 7, 1))[1], "payment_episode_washout")

    def test_unknown_censors_horizon_and_all_later_rows(self):
        unknown = [filing(1, "2025-02-01")]
        self.assertEqual(self.label(unknown=unknown)[1], "unresolved_payment_disclosure_in_window")
        self.assertEqual(self.label(unknown=unknown, decision=date(2025, 8, 1))[1], "post_unresolved_payment_disclosure")
        self.assertEqual(self.label(unknown=[filing(1, "2025-04-01")])[0], 0)
        events, _, _ = self.events([filing(2, "2025-01-20")])
        self.assertEqual(self.label(events, unknown)[0], 1)

    def test_negatives_require_followup_but_observed_positives_do_not(self):
        self.assertIsNone(self.label(last=date(2025, 3, 1))[0])
        self.assertEqual(self.label(last=date(2025, 3, 2))[0], 0)
        events, _, _ = self.events([filing(1, "2025-02-01")])
        self.assertEqual(self.label(events, last=date(2025, 2, 1))[0], 1)

    def test_payment_prompt_and_schema_validation(self):
        self.assertNotEqual(review_body("text", "test-model"), review_body("text", "test-model", payment_failure_only=True))
        r = review(filing(1, "2025-02-01"), event_type="ACCELERATION")["llm_review"]["review"]
        r["reason"] = "Debt accelerated."
        r["evidence_quotes"] = ["Following a covenant default, the debt was accelerated."]
        payload = dict(status="completed", output=[{"content": [{"type": "output_text", "text": json.dumps(r)}]}])
        with self.assertRaisesRegex(ValueError, "excludes acceleration"):
            parse_review_response(payload, r["evidence_quotes"][0], payment_failure_only=True)

    def test_cache_profiles_cannot_cross(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            for name, settings in [("legacy", {}), ("payment", {"target": REVIEW_TARGET})]:
                saved = dict(provider="openai_batch", company_id="0000000001", accessionNumber=name,
                             settings=settings, review={"classification": "NON_DEFAULT"})
                (cache / f"{name}.json").write_text(json.dumps(saved))
            broad, _, _ = cached_decision_index(cache, "openai_batch", "test-model")
            strict, _, _ = cached_decision_index(cache, "openai_batch", "test-model", {"target": REVIEW_TARGET})
            self.assertEqual(set(broad), {("0000000001", "legacy")})
            self.assertEqual(set(strict), {("0000000001", "payment")})

    def test_discover_both_items_once_per_filing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "CIK0000000001.json").write_text("{}")
            fs = [filing(1, "2025-01-01", "1.03"), filing(2, "2025-02-01", "2.04"),
                  filing(3, "2025-03-01", "1.03,2.04"), filing(4, "2025-04-01", "12.04")]
            with patch("mcf.enrichment.item204.discover.filing_rows", return_value=(fs, [])):
                found = list(iter_item_204(path, items=["1.03", "2.04"]))
            self.assertEqual([f["accessionNumber"] for f in found], [f["accessionNumber"] for f in fs[:3]])

    def test_inventory_and_panel_retain_two_episodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for directory in ("companyfacts", "submissions"):
                (root / directory).mkdir()
            (root / "companyfacts/CIK0000000001.json").write_text("{}")
            (root / "submissions/CIK0000000001.json").write_text(json.dumps({"name": "Test", "sic": "2000"}))
            fs = [filing(1, "2010-01-01", "", "10-K"), filing(2, "2012-02-01", "1.03"),
                  filing(3, "2012-03-01"), filing(4, "2014-02-01", "1.03,2.04"),
                  filing(5, "2026-09-01", "", "10-K")]
            reviews = root / "reviews.jsonl"
            reviews.write_text("".join(json.dumps(review(f)) + "\n" for f in fs[1:4]))
            config = Path(__file__).resolve().parents[1] / "configs/study.disclosed_payment_failure.json"
            load_design(config)
            with patch("mcf.data.empirical.filing_rows", return_value=(fs, [])):
                audit = inventory(root, root / "inventory", date(2026, 9, 7), reviews, target=TARGET)
            self.assertEqual(audit["disclosure_records"], 3)

            def snapshot(decision):
                values = dict.fromkeys(FEATURES, 0.1)
                values.update(assets=100, revenue=10, operating_cashflow=5, cash=10,
                              balance_period_end=str(decision - timedelta(days=30)),
                              flow_period_end=str(decision - timedelta(days=30)),
                              balance_age_days=30, flow_age_days=30, flow_basis="annual")
                return values, {"assets": {"filed": str(decision - timedelta(days=1))}}

            with patch("mcf.data.empirical.FactIndex") as index:
                index.return_value.snapshot.side_effect = snapshot
                result = panel(root, root / "inventory", config, root / "panel")
            self.assertEqual(result["distinct_positive_events"], 2)
            rows = read_csv(root / "panel/panel.csv")
            positives = [r for r in rows if r["label"] == "1"]
            self.assertEqual({r["label_source"] for r in positives}, {fs[1]["accessionNumber"], fs[3]["accessionNumber"]})
            self.assertTrue(any(r["decision_date"] == "2013-01-01" and r["label"] == "0" for r in rows))
            features = {r["decision_date"]: r for r in read_csv(root / "panel/features.csv")}
            self.assertEqual(features["2012-02-01"]["known_disclosure"], "True")
            self.assertEqual(features["2013-01-01"]["known_disclosure"], "False")
            self.assertEqual(features["2013-01-01"]["event_type"], TARGET)
            self.assertEqual(audit["candidate_payment_episodes_by_year"], {"2012": 1, "2014": 1})

            legacy_rows = [review(f) for f in fs[2:4]]
            for row in legacy_rows:
                row["llm_review"].update(provider="openai_batch", settings={})
            reviews.write_text("".join(json.dumps(row) + "\n" for row in legacy_rows))
            with patch("mcf.data.empirical.filing_rows", return_value=(fs, [])):
                reused = inventory(root, root / "legacy", date(2026, 9, 7), reviews, target=TARGET)
            self.assertEqual(reused["item_204_counts"]["legacy_payment_failure_reused"], 2)
            self.assertEqual(reused["item_204_counts"]["missing_review"], 1)


            # An all-negative reviewed inventory still writes a valid empty event CSV.
            reviews.write_text("".join(json.dumps(review(f, "NON_DEFAULT", "BENIGN")) + "\n" for f in fs[1:4]))
            with patch("mcf.data.empirical.filing_rows", return_value=(fs, [])):
                negative = inventory(root, root / "negative", date(2026, 9, 7), reviews, target=TARGET)
            self.assertEqual(negative["disclosure_records"], 0)
            self.assertEqual(read_csv(root / "negative/disclosure_events.csv"), [])
            composite_config = config.parent / "study.bankruptcy_or_payment_failure.json"
            with patch("mcf.data.empirical.filing_rows", return_value=(fs, [])):
                combined = inventory(root, root / "composite_inventory", date(2026, 9, 7), reviews,
                                     target=BANKRUPTCY_PAYMENT_TARGET)
            self.assertEqual(combined["disclosure_records"], 2)
            with patch("mcf.data.empirical.FactIndex") as index:
                index.return_value.snapshot.side_effect = snapshot
                result = panel(root, root / "composite_inventory", composite_config, root / "composite_panel")
            self.assertEqual(result["target"], BANKRUPTCY_PAYMENT_TARGET)
            self.assertEqual(result["distinct_positive_events"], 2)
            self.assertTrue(all(r["event_type"] == BANKRUPTCY_PAYMENT_TARGET for r in read_csv(root / "composite_panel/panel.csv")))
            reviews.write_text("".join(json.dumps(review(f, event_type="ACCELERATION")) + "\n" for f in fs[1:4]))
            with patch("mcf.data.empirical.filing_rows", return_value=(fs, [])):
                with self.assertRaisesRegex(ValueError, "inventory has errors"):
                    inventory(root, root / "invalid", date(2026, 9, 7), reviews, target=TARGET)
            self.assertEqual(len(json.loads((root / "invalid/inventory_audit.json").read_text())["errors"]), 1)

    def test_new_workflow_requests_both_items_and_waits_for_collection(self):
        from mcf.workflows.payment_default_proxy import parser, run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "reviews"
            final.mkdir()
            (final / "audit.json").write_text(json.dumps({"review_counts": {"batch_pending": 1}}))
            config = Path(__file__).resolve().parents[1] / "configs/study.disclosed_payment_failure.json"
            args = parser().parse_args(["--output-dir", str(root / "run"), "--config", str(config)])
            with patch("mcf.workflows.payment_default_proxy.run_item_204", return_value=final) as enrichment, patch(
                "mcf.workflows.payment_default_proxy.inventory"
            ) as build_inventory:
                with self.assertRaisesRegex(ValueError, "pending"):
                    run(args)
            settings = enrichment.call_args.args[0]
            self.assertEqual(settings.items, ["1.03", "2.04"])
            self.assertTrue(settings.payment_failure_only)
            self.assertEqual(settings.batch_max_requests, 200)
            build_inventory.assert_not_called()

    def test_default_composite_workflow_only_reviews_item_204(self):
        from mcf.workflows.payment_default_proxy import parser, run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "reviews"
            final.mkdir()
            (final / "audit.json").write_text(json.dumps({"review_counts": {"batch_pending": 1}}))
            args = parser().parse_args(["--output-dir", str(root / "run")])
            self.assertEqual(load_design(args.config)["event_type"], BANKRUPTCY_PAYMENT_TARGET)
            with patch("mcf.workflows.payment_default_proxy.run_item_204", return_value=final) as enrichment:
                with self.assertRaisesRegex(ValueError, "pending"):
                    run(args)
            self.assertEqual(enrichment.call_args.args[0].items, ["2.04"])
            self.assertTrue(enrichment.call_args.args[0].payment_failure_only)


if __name__ == "__main__":
    unittest.main()
