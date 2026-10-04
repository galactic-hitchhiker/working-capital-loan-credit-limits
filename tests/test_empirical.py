"""Timing and extraction checks for the observed SEC disclosure study."""

import json
import unittest
from datetime import date
from pathlib import Path

from mcf.data.empirical import disclosure_label, item_103
from mcf.data.sec import snapshot
from mcf.data.point_in_time import FactIndex
from test_research import document, fact
from mcf.policy.credit import PolicyConfig
from mcf.policy.empirical import replay_scenario


class DisclosureTests(unittest.TestCase):
    def test_exact_item_and_separators(self):
        for text in ("1.03", "1.01,1.03,9.01", "1.01; 1.03"):
            self.assertTrue(item_103(text))
        for text in ("11.03", "1.030", "", "9.01"):
            self.assertFalse(item_103(text))

    def label(self, event=None, last=date(2025, 12, 1), cutoff=date(2026, 1, 1)):
        return disclosure_label(date(2025, 1, 1), event, last, 60, cutoff)

    def test_window_boundaries_and_post_event(self):
        self.assertEqual(self.label(date(2025, 3, 2))[0], 1)
        self.assertEqual(self.label(date(2025, 3, 3))[0], 0)
        self.assertIsNone(self.label(date(2025, 1, 1))[0])
        self.assertIsNone(self.label(date(2024, 12, 31))[0])

    def test_followup_and_cutoff_censoring(self):
        self.assertIsNone(self.label(last=date(2025, 3, 1))[0])
        self.assertEqual(self.label(last=date(2025, 3, 2))[0], 0)
        self.assertIsNone(self.label(cutoff=date(2025, 3, 3))[0])
        # A positive disclosure remains observed if the issuer then stops filing.
        self.assertEqual(self.label(date(2025, 2, 1), last=date(2025, 2, 1))[0], 1)


class IncrementalTests(unittest.TestCase):
    def check_document(self, data, decisions):
        index = FactIndex(data, decisions[-1])
        for decision in decisions:
            slow_values, slow_provenance = snapshot(data, decision)
            fast_values, fast_provenance = index.snapshot(decision)
            self.assertEqual(fast_values, slow_values, str(decision))
            self.assertEqual(fast_provenance, slow_provenance, str(decision))

    def test_restatements_conflicts_and_annual_matching(self):
        data = document(
            {
                "Assets": [
                    fact(100),
                    fact(80, end="2023-12-31"),
                    fact(110, filed="2025-05-01"),
                    fact(120, filed="2025-05-01"),
                ],
                "AssetsCurrent": [fact(50)],
                "LiabilitiesCurrent": [fact(25)],
                "NetCashProvidedByUsedInOperatingActivities": [
                    fact(10, start="2024-01-01"),
                    fact(6, start="2025-01-01", end="2025-06-30", filed="2025-08-01"),
                ],
                "Revenues": [fact(200, start="2024-01-01")],
                "NetIncomeLoss": [fact(9, start="2024-01-01")],
            }
        )
        self.check_document(
            data,
            [date(2025, 2, 1), date(2025, 2, 2), date(2025, 5, 2), date(2025, 9, 1)],
        )

    def test_reject_backwards_time(self):
        index = FactIndex(document({}), date(2025, 5, 1))
        index.snapshot(date(2025, 4, 1))
        with self.assertRaises(ValueError):
            index.snapshot(date(2025, 3, 1))

    @unittest.skipUnless(
        Path("dataset/companyfacts/CIK0000320193.json").exists(),
        "local SEC dataset unavailable",
    )
    def test_real_apple_history_matches_reference(self):
        data = json.loads(Path("dataset/companyfacts/CIK0000320193.json").read_text())
        self.check_document(
            data,
            [date(y, m, 1) for y in (2011, 2015, 2020, 2025) for m in (1, 4, 7, 10)],
        )


class ScenarioTests(unittest.TestCase):
    def row(self, decision, **overrides):
        row = dict(
            company_id="1",
            entity_name="Test fixture",
            decision_date=decision,
            feature_available_on="2024-12-01",
            assets=100e6,
            revenue_annual=12e6,
            operating_cashflow_annual=1.2e6,
            reported_cash=500e3,
            probability=0.02,
            known_disclosure=False,
        )
        row.update(overrides)
        return row

    def test_gap_starts_new_assessment_not_one_month_change(self):
        paths = list(
            replay_scenario(
                [self.row("2025-01-01"), self.row("2025-03-01")], PolicyConfig()
            )
        )
        self.assertTrue(paths[1]["segment_initial"])
        self.assertIsNone(paths[1]["limit_change"])
        self.assertIsNone(paths[1]["previous_limit"])

    def test_known_disclosure_stops_and_cannot_reopen_in_segment(self):
        rows = [
            self.row("2025-01-01"),
            self.row("2025-02-01", known_disclosure=True),
            self.row("2025-03-01", known_disclosure=True),
        ]
        paths = list(replay_scenario(rows, PolicyConfig()))
        self.assertGreater(paths[0]["assigned_limit"], 0)
        self.assertEqual(paths[1]["assigned_limit"], 0)
        self.assertEqual(paths[2]["assigned_limit"], 0)

    def test_new_timestamp_does_not_repeat_supported_increase(self):
        rows = [
            self.row("2025-01-01", reported_cash=0, operating_cashflow_annual=600000),
            self.row("2025-02-01"),
            self.row("2025-03-01", feature_available_on="2025-02-28"),
        ]
        paths = list(replay_scenario(rows, PolicyConfig()))
        self.assertEqual(paths[1]["update_reason"], "phased_increase")
        self.assertEqual(paths[2]["update_reason"], "no_new_information")
        self.assertEqual(paths[1]["assigned_limit"], paths[2]["assigned_limit"])

    def test_doubled_probability_equals_doubled_sensitivity(self):
        rows = [self.row("2025-01-01"), self.row("2025-02-01")]
        p = list(replay_scenario(rows, PolicyConfig(), probability_stress=True))
        k = list(replay_scenario(rows, PolicyConfig(risk_sensitivity=20)))
        self.assertEqual(
            [r["assigned_limit"] for r in p], [r["assigned_limit"] for r in k]
        )


if __name__ == "__main__":
    unittest.main()
