import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from credit_policy import (
    PolicyConfig,
    PolicyInputs,
    determine_limit,
    expected_loss_amount,
)
from sec_data import filing_rows, latest_fact, snapshot
from temporal_validation import chronological_partition, make_label


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.x = PolicyInputs(
            12e6,
            1.2e6,
            500e3,
            50e3,
            0.02,
            150e3,
            outstanding_exposure=60e3,
            previous_limit=70e3,
        )

    def test_worked_example(self):
        r = determine_limit(self.x)
        self.assertEqual(r.capacity, 100000)
        self.assertAlmostEqual(r.raw_limit, 81873.0753077982)
        self.assertAlmostEqual(r.assigned_limit, 75936.5376538991)
        self.assertAlmostEqual(r.available_credit, 15936.5376538991)

    def test_stress_reduces_immediately_and_preserves_actual_exposure(self):
        r = determine_limit(replace(self.x, risk_probability=0.08))
        self.assertAlmostEqual(r.assigned_limit, 44932.89641172215)
        self.assertEqual(r.available_credit, 0)
        self.assertAlmostEqual(r.excess_exposure, 15067.10358827785)

    def test_monotonic_risk(self):
        limits = [
            determine_limit(replace(self.x, risk_probability=i / 100)).assigned_limit
            for i in range(101)
        ]
        self.assertEqual(limits, sorted(limits, reverse=True))

    def test_more_debt_service_never_increases_limit(self):
        limits = [
            determine_limit(
                replace(self.x, external_debt_service_60d=i * 10000)
            ).assigned_limit
            for i in range(25)
        ]
        self.assertEqual(limits, sorted(limits, reverse=True))

    def test_caps_hold_for_many_states(self):
        for previous in [None, 0, 10000, 70000, 1e6]:
            for cap in [0, 10000, 60000, 1e6]:
                for q in [0, 0.02, 0.5, 1]:
                    r = determine_limit(
                        replace(
                            self.x,
                            previous_limit=previous,
                            hard_cap=cap,
                            risk_probability=q,
                        )
                    )
                    self.assertGreaterEqual(r.assigned_limit, 0)
                    self.assertLessEqual(r.assigned_limit, r.raw_limit)
                    self.assertLessEqual(r.assigned_limit, cap)
                    if previous and r.assigned_limit > previous:
                        self.assertLessEqual(r.assigned_limit, 1.1 * previous)

    def test_no_new_information_holds_increase(self):
        r = determine_limit(replace(self.x, information_changed=False))
        self.assertEqual(r.assigned_limit, 70000)

    def test_new_hard_cap_binds_even_without_information_flag(self):
        r = determine_limit(replace(self.x, information_changed=False, hard_cap=30000))
        self.assertEqual(r.assigned_limit, 30000)

    def test_deadband_only_blocks_increases(self):
        self.assertEqual(
            determine_limit(replace(self.x, hard_cap=71000)).assigned_limit, 70000
        )
        self.assertEqual(
            determine_limit(replace(self.x, hard_cap=69000)).assigned_limit, 69000
        )

    def test_initial_and_reopening(self):
        self.assertGreater(
            determine_limit(replace(self.x, previous_limit=None)).assigned_limit, 0
        )
        self.assertEqual(
            determine_limit(replace(self.x, previous_limit=0)).assigned_limit, 0
        )

    def test_hard_stop_preserves_excess(self):
        r = determine_limit(replace(self.x, hard_stop=True))
        self.assertEqual(r.assigned_limit, 0)
        self.assertEqual(r.excess_exposure, 60000)

    def test_negative_ocf_is_not_positive_capacity(self):
        self.assertEqual(
            determine_limit(replace(self.x, operating_cashflow_annual=-1e6)).capacity, 0
        )

    def test_invalid_inputs(self):
        for kwargs in [
            {"risk_probability": 1.1},
            {"risk_probability": float("nan")},
            {"eligible_cash": -1},
            {"operating_cashflow_annual": float("inf")},
            {"external_debt_service_60d": None},
            {"risk_horizon_days": 0},
            {"information_changed": "yes"},
        ]:
            with self.assertRaises(ValueError):
                replace(self.x, **kwargs)
        with self.assertRaises(ValueError):
            PolicyConfig(increase_smoothing=1.1)

    def test_expected_loss_valid(self):
        self.assertEqual(
            expected_loss_amount(pd=0.02, lgd=0.4, ead=100000, pd_horizon_days=60), 800
        )

    def test_expected_loss_rejects_wrong_target_horizon_and_lgd(self):
        for kwargs in [
            {"target": "distress"},
            {"pd_horizon_days": 365},
            {"lgd": 1.2},
            {"exposure_horizon_days": 60.0},
        ]:
            args = dict(pd=0.02, lgd=0.4, ead=100000, pd_horizon_days=60)
            args.update(kwargs)
            with self.assertRaises(ValueError):
                expected_loss_amount(**args)


def fact(value, end="2024-12-31", filed="2025-02-01", start=None, accn="a"):
    row = dict(val=value, end=end, filed=filed, accn=accn, form="10-K")
    if start:
        row["start"] = start
    return row


def document(mapping):
    return {
        "cik": 1,
        "entityName": "Synthetic test company",
        "facts": {
            "us-gaap": {tag: {"units": {"USD": rows}} for tag, rows in mapping.items()}
        },
    }


class SecTests(unittest.TestCase):
    def test_no_same_day_or_future_filing(self):
        d = document({"Assets": [fact(100)]})
        self.assertIsNone(latest_fact(d, "assets", date(2025, 2, 1)))
        self.assertEqual(latest_fact(d, "assets", date(2025, 2, 2)).value, 100)

    def test_later_restatement_cannot_change_past_snapshot(self):
        original = fact(100)
        amended = fact(120, filed="2025-05-01", accn="b")
        d = document({"Assets": [original, amended]})
        self.assertEqual(latest_fact(d, "assets", date(2025, 3, 1)).value, 100)
        self.assertEqual(latest_fact(d, "assets", date(2025, 6, 1)).value, 120)

    def test_latest_period_wins_over_old_comparative(self):
        d = document(
            {"Assets": [fact(100), fact(80, end="2023-12-31", filed="2025-06-01")]}
        )
        self.assertEqual(latest_fact(d, "assets", date(2025, 7, 1)).value, 100)

    def test_ytd_is_not_an_annual_flow(self):
        d = document(
            {
                "NetCashProvidedByUsedInOperatingActivities": [
                    fact(60, start="2024-01-01"),
                    fact(40, start="2025-01-01", end="2025-06-30", filed="2025-08-01"),
                ]
            }
        )
        self.assertEqual(
            latest_fact(d, "operating_cashflow", date(2025, 9, 1), annual=True).value,
            60,
        )

    def test_conflicting_facts_remain_missing(self):
        d = document({"Assets": [fact(100), fact(200)]})
        self.assertIsNone(latest_fact(d, "assets", date(2025, 3, 1)))

    def test_snapshot_matches_flow_periods(self):
        d = document(
            {
                "Assets": [fact(100), fact(80, end="2023-12-31")],
                "AssetsCurrent": [fact(50)],
                "LiabilitiesCurrent": [fact(25)],
                "NetCashProvidedByUsedInOperatingActivities": [
                    fact(10, start="2024-01-01")
                ],
                "Revenues": [fact(200, start="2023-01-01", end="2023-12-31")],
                "NetIncomeLoss": [fact(9, start="2024-01-01")],
            }
        )
        row, prov = snapshot(d, date(2025, 3, 1))
        self.assertIsNone(row["revenue"])
        self.assertEqual(row["current_ratio"], 2)
        self.assertAlmostEqual(row["return_on_average_assets"], 0.1)
        self.assertIsNotNone(prov["opening_assets_for_profitability"])

    def test_nonfinite_fact_is_skipped(self):
        d = document({"Assets": [fact(float("nan"))]})
        self.assertIsNone(latest_fact(d, "assets", date(2025, 3, 1)))

    def test_historical_submissions_and_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            block = {"accessionNumber": ["a"], "form": ["8-K"], "items": ["1.03"]}
            (p / "history.json").write_text(json.dumps(block))
            sub = {
                "filings": {
                    "recent": block,
                    "files": [{"name": "history.json"}, {"name": "missing.json"}],
                }
            }
            rows, missing = filing_rows(sub, p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(missing, ["missing.json"])


class TemporalTests(unittest.TestCase):
    def label(self, **overrides):
        args = dict(
            company_id="1",
            decision_date=date(2025, 1, 1),
            horizon_days=60,
            observed_through=date(2025, 12, 31),
            coverage_verified=True,
        )
        args.update(overrides)
        if "coverage_known_on" not in args:
            args["coverage_known_on"] = args["decision_date"] + timedelta(
                days=args["horizon_days"]
            )
        return make_label(**args)

    def test_unknown_coverage_not_negative(self):
        self.assertIsNone(self.label(coverage_verified=False))

    def test_incomplete_followup_not_negative(self):
        self.assertIsNone(self.label(observed_through=date(2025, 2, 1)))

    def test_missing_coverage_availability_not_negative(self):
        self.assertIsNone(self.label(coverage_known_on=None))

    def test_late_negative_confirmation_retained(self):
        row = self.label(coverage_known_on=date(2025, 5, 1))
        self.assertEqual(row.label, 0)
        self.assertEqual(row.label_available_on, date(2025, 5, 2))

    def test_premature_coverage_confirmation_rejected(self):
        with self.assertRaises(ValueError):
            self.label(coverage_known_on=date(2025, 2, 1))

    def test_unverified_candidate_not_positive(self):
        self.assertIsNone(self.label(event_date=date(2025, 2, 1)))

    def test_event_at_horizon_end_is_positive_and_late_knowledge_retained(self):
        row = self.label(
            event_date=date(2025, 3, 2),
            event_verified=True,
            event_known_on=date(2025, 3, 10),
            event_source="verified filing",
        )
        self.assertEqual(row.label, 1)
        self.assertEqual(row.label_available_on, date(2025, 3, 11))

    def test_post_event_row_removed(self):
        self.assertIsNone(
            self.label(
                event_date=date(2025, 1, 1),
                event_verified=True,
                event_known_on=date(2025, 1, 2),
                event_source="verified filing",
            )
        )

    def test_temporal_purge(self):
        early = self.label(decision_date=date(2024, 10, 1))
        crossing = self.label(decision_date=date(2024, 12, 15))
        parts = chronological_partition(
            [early, crossing],
            tuning_start=date(2025, 1, 1),
            calibration_start=date(2025, 4, 1),
            selection_start=date(2025, 7, 1),
            test_start=date(2025, 10, 1),
            observed_as_of=date(2026, 1, 1),
        )
        self.assertEqual(parts["training"], [early])
        self.assertEqual(parts["purged"], [crossing])

    def test_bad_boundaries_rejected(self):
        with self.assertRaises(ValueError):
            chronological_partition(
                [],
                tuning_start=date(2025, 1, 2),
                calibration_start=date(2025, 4, 1),
                selection_start=date(2025, 7, 1),
                test_start=date(2025, 10, 1),
                observed_as_of=date(2026, 1, 1),
            )


if __name__ == "__main__":
    unittest.main()
