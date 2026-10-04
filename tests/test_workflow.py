import csv
import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path

from mcf.policy.backtest import replay
from mcf.data.panel import outcome, build, UNIVERSE_FIELDS, EVENT_FIELDS, COVERAGE_FIELDS
from mcf.policy.credit import PolicyConfig
from mcf.common import boolean, load_design, read_csv, write_csv, write_json

try:
    import numpy as np
    from mcf.workflows.demo import fixture
    from mcf.models.evaluation import (
        choose_threshold,
        metrics,
        select_model,
        cluster_intervals,
    )
    from mcf.models.risk import estimator, fit
    from mcf.models.train import prepare, rolling_tuning_folds, select_calibration

    HAS_ML = True
except ModuleNotFoundError:
    HAS_ML = False


class InputContractTests(unittest.TestCase):
    def test_boolean_rejects_ambiguous_values(self):
        self.assertTrue(boolean("True"))
        self.assertFalse(boolean("false"))
        for value in ("", "yes", 1, None):
            with self.assertRaises(ValueError):
                boolean(value)

    def test_draft_design_cannot_run(self):
        with self.assertRaisesRegex(ValueError, "draft"):
            load_design(Path(__file__).parent.parent / "configs" / "study.example.json")

    def test_fixed_design_still_requires_complete_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = json.loads(
                (
                    Path(__file__).parent.parent / "configs" / "study.example.json"
                ).read_text()
            )
            config["design_status"] = "fixed"
            path = Path(tmp) / "design.json"
            write_json(path, config)
            with self.assertRaisesRegex(ValueError, "Complete"):
                load_design(path)

    def test_malformed_csv_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("a,b\n1,2,3\n")
            with self.assertRaises(ValueError):
                read_csv(path)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(
            horizon_days=60, event_type="bankruptcy", observed_as_of="2025-12-31"
        )
        self.coverage = dict(
            verified="true",
            observed_through="2025-04-01",
            coverage_known_on="2025-04-01",
            source="test://coverage",
        )
        self.event = dict(
            review_status="confirmed",
            event_date="2025-02-10",
            event_known_on="2025-02-12",
            source="test://event",
        )

    def test_pending_event_blocks_negative(self):
        row, reason, _, _ = outcome(
            "1",
            date(2025, 1, 1),
            [{"review_status": "pending"}],
            self.coverage,
            self.config,
        )
        self.assertIsNone(row)
        self.assertEqual(reason, "unresolved_event")

    def test_verified_event_yields_traceable_positive(self):
        row, _, event_id, source = outcome(
            "1", date(2025, 1, 1), [self.event], self.coverage, self.config
        )
        self.assertEqual(row.label, 1)
        self.assertEqual(event_id, "1:bankruptcy:2025-02-10")
        self.assertEqual(source, "test://event")

    def test_absent_event_without_coverage_is_not_zero(self):
        self.assertIsNone(outcome("1", date(2025, 1, 1), [], None, self.config)[0])

    def test_post_event_excluded(self):
        self.assertEqual(
            outcome("1", date(2025, 3, 1), [self.event], self.coverage, self.config)[1],
            "post_event",
        )

    def test_late_coverage_excluded_at_cutoff(self):
        coverage = {**self.coverage, "coverage_known_on": "2025-12-31"}
        self.assertEqual(
            outcome("1", date(2025, 1, 1), [], coverage, self.config)[1],
            "label_not_available_at_cutoff",
        )


class PanelIntegrationTests(unittest.TestCase):
    def test_file_builder_keeps_unlabeled_features_without_inventing_negative_labels(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = dict(
                design_status="fixed",
                data_kind="empirical",
                event_type="bankruptcy",
                event_definition="Unit-test definition, not a real study",
                horizon_days=60,
                start="2016-01-01",
                end="2021-10-01",
                tuning_start="2018-01-01",
                calibration_start="2019-01-01",
                selection_start="2020-01-01",
                test_start="2021-01-01",
                observed_as_of="2022-01-01",
                features=[
                    "current_ratio",
                    "working_capital_to_assets",
                    "return_on_average_assets",
                    "log_assets",
                ],
                max_balance_age_days=180,
                max_flow_age_days=540,
                min_class_count=1,
                min_event_companies=1,
                bootstrap_repeats=10,
                seed=42,
            )
            write_json(root / "design.json", config)
            write_csv(
                root / "universe.csv",
                [
                    dict(
                        company_id="1",
                        eligible_from="2020-01-01",
                        eligible_through="2020-02-01",
                        verified="true",
                        source="test://universe",
                    )
                ],
                UNIVERSE_FIELDS,
            )
            write_csv(root / "events.csv", [], EVENT_FIELDS)
            write_csv(root / "coverage.csv", [], COVERAGE_FIELDS)
            facts = {}
            for tag, value, annual in (
                ("Assets", 100, False),
                ("AssetsCurrent", 50, False),
                ("LiabilitiesCurrent", 25, False),
                ("NetCashProvidedByUsedInOperatingActivities", 10, True),
                ("NetIncomeLoss", 5, True),
                ("Revenues", 200, True),
            ):
                row = dict(
                    val=value,
                    end="2019-09-30",
                    filed="2019-11-01",
                    form="10-K",
                    accn="test-accession",
                )
                if annual:
                    row["start"] = "2018-10-01"
                facts[tag] = {"units": {"USD": [row]}}
            folder = root / "dataset" / "companyfacts"
            folder.mkdir(parents=True)
            write_json(
                folder / "CIK0000000001.json", {"cik": 1, "facts": {"us-gaap": facts}}
            )
            result = build(
                root / "design.json",
                root / "dataset",
                root / "universe.csv",
                root / "events.csv",
                root / "coverage.csv",
                root / "output",
            )
            self.assertEqual(result["rows"], 0)
            self.assertEqual(result["feature_rows_including_unlabeled"], 2)
            self.assertEqual(result["counts"]["unverified_coverage"], 2)
            features = read_csv(root / "output" / "features.csv")
            self.assertEqual(float(features[0]["current_ratio"]), 2.0)
            self.assertTrue((root / "output" / "manifest.json").exists())


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.pred = dict(
            company_id="one",
            decision_date="2025-01-01",
            data_kind="synthetic",
            event_type="example",
            horizon_days="60",
            model="logistic",
            probability="0.02",
            selected="true",
            stage="policy",
            prediction_ready_on="2025-01-01",
        )
        self.row = dict(
            company_id="one",
            decision_date="2025-01-01",
            currency="USD",
            revenue_annual="12000000",
            operating_cashflow_annual="1200000",
            eligible_cash="500000",
            external_debt_service_60d="50000",
            hard_cap="150000",
            outstanding_exposure="60000",
            initial_limit="70000",
            information_changed="true",
            hard_stop="false",
            reopen="false",
            inputs_available_on="2024-12-31",
            assessment_status="eligible",
            input_basis="assumed",
            input_source="test://policy",
        )

    def second(self, **updates):
        return {
            **self.row,
            "decision_date": "2025-02-01",
            "initial_limit": "",
            **updates,
        }

    def test_previous_limit_is_carried_and_unchanged_inputs_cannot_repeat_increase(
        self,
    ):
        predictions = [self.pred, {**self.pred, "decision_date": "2025-02-01"}]
        result, _ = replay(predictions, [self.row, self.second()], PolicyConfig())
        self.assertAlmostEqual(result[0]["assigned_limit"], 75936.53765, places=4)
        self.assertEqual(result[1]["assigned_limit"], result[0]["assigned_limit"])
        self.assertEqual(result[1]["update_reason"], "no_new_information")

    def test_hard_stop_keeps_outstanding_exposure(self):
        rows, _ = replay(
            [self.pred],
            [{**self.row, "assessment_status": "blocked", "hard_stop": "true"}],
            PolicyConfig(),
        )
        self.assertEqual(rows[0]["assigned_limit"], 0)
        self.assertEqual(rows[0]["excess_exposure"], 60000)

    def test_blocked_cannot_receive_credit(self):
        with self.assertRaises(ValueError):
            replay(
                [self.pred],
                [{**self.row, "assessment_status": "blocked"}],
                PolicyConfig(),
            )

    def test_future_model_rejected(self):
        with self.assertRaises(ValueError):
            replay(
                [{**self.pred, "prediction_ready_on": "2025-02-01"}],
                [self.row],
                PolicyConfig(),
            )

    def test_future_inputs_rejected(self):
        with self.assertRaises(ValueError):
            replay(
                [self.pred],
                [{**self.row, "inputs_available_on": "2025-02-01"}],
                PolicyConfig(),
            )

    def test_month_gap_rejected(self):
        with self.assertRaises(ValueError):
            replay(
                [self.pred, {**self.pred, "decision_date": "2025-03-01"}],
                [self.row, self.second(decision_date="2025-03-01")],
                PolicyConfig(),
            )

    def test_duplicate_predictions_rejected(self):
        with self.assertRaises(ValueError):
            replay([self.pred, self.pred], [self.row], PolicyConfig())

    def test_currency_change_rejected(self):
        with self.assertRaises(ValueError):
            replay(
                [self.pred, {**self.pred, "decision_date": "2025-02-01"}],
                [self.row, self.second(currency="EUR")],
                PolicyConfig(),
            )

    def test_new_cap_forces_reduction(self):
        rows, _ = replay(
            [self.pred, {**self.pred, "decision_date": "2025-02-01"}],
            [self.row, self.second(hard_cap="10000", information_changed="false")],
            PolicyConfig(),
        )
        self.assertEqual(rows[1]["assigned_limit"], 10000)


@unittest.skipUnless(HAS_ML, "Install requirements.txt to run model tests")
class ModelTests(unittest.TestCase):
    def test_metrics_and_constant_ap(self):
        result = metrics([0, 0, 0, 1], [0.25] * 4)
        self.assertEqual(result["average_precision"], 0.25)
        self.assertEqual(result["brier"], 0.1875)

    def test_threshold_agrees_with_exhaustive_f1_and_recall_rule(self):
        y, p = np.array([1, 0, 1, 0, 0, 1]), np.array([0.9, 0.7, 0.5, 0.5, 0.3, 0.2])
        expected = max(
            np.unique(p),
            key=lambda t: (metrics(y, p, t)["f1"], metrics(y, p, t)["recall"], t),
        )
        self.assertEqual(choose_threshold(y, p), expected)

    def test_model_selection_enforces_both_baselines_and_simplicity(self):
        scores = {
            "complex": {"average_precision": 0.5, "brier": 0.1},
            "simple": {"average_precision": 0.4, "brier": 0.1},
            "ineligible": {"average_precision": 0.1, "brier": 0.01},
        }
        self.assertEqual(
            select_model(scores, 0.2, 0.1, ["simple", "complex", "ineligible"]),
            "simple",
        )
        self.assertIsNone(
            select_model(scores, 0.01, 0.1, ["simple", "complex", "ineligible"])
        )

    def test_calibration_selection_uses_brier_and_prefers_identity_on_tie(self):
        self.assertEqual(
            select_calibration(
                {"identity": {"brier": 0.1}, "sigmoid": {"brier": 0.2}}
            ),
            "identity",
        )
        self.assertEqual(
            select_calibration(
                {"identity": {"brier": 0.1}, "sigmoid": {"brier": 0.1}}
            ),
            "identity",
        )

    def test_rolling_tuning_uses_only_labels_available_at_fold_start(self):
        rows = [
            {"decision_date": "2016-06-01", "label_available_on": "2016-09-01"},
            {"decision_date": "2016-12-01", "label_available_on": "2017-02-01"},
            {"decision_date": "2017-06-01", "label_available_on": "2017-09-01"},
            {"decision_date": "2017-12-01", "label_available_on": "2018-02-01"},
            {"decision_date": "2018-06-01", "label_available_on": "2018-09-01"},
        ]
        folds = rolling_tuning_folds(rows, np.array([0, 1]), np.array([2, 3, 4]))
        self.assertEqual([fold["validation_year"] for fold in folds], [2017, 2018])
        np.testing.assert_array_equal(folds[0]["fit_indices"], [0])
        np.testing.assert_array_equal(folds[0]["validation_indices"], [2, 3])
        np.testing.assert_array_equal(folds[1]["fit_indices"], [0, 1, 2])
        np.testing.assert_array_equal(folds[1]["validation_indices"], [4])

    def test_median_and_scaling_fit_only_on_training(self):
        x = np.array(
            [[1.0, 2.0], [2.0, 3.0], [np.nan, 4.0], [4.0, 5.0], [5.0, 6.0], [6.0, 7.0]]
        )
        model = fit(
            estimator("logistic_l2", {"C": 1.0}, 42),
            x,
            np.array([0, 0, 1, 0, 1, 1]),
            "unweighted",
        )
        before = model.named_steps["imputer"].statistics_.copy()
        model.predict_proba(np.array([[1e9, 1e9]]))
        np.testing.assert_equal(model.named_steps["imputer"].statistics_, before)
        self.assertEqual(before[0], 4.0)

    def test_cluster_intervals_reproducible(self):
        args = ([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9], ["a", "a", "b", "b"], 0.5, 20, 42)
        self.assertEqual(cluster_intervals(*args), cluster_intervals(*args))

    def test_synthetic_fixture_has_disjoint_time_stages_and_purged_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, _, _ = fixture(Path(tmp), companies_per_cohort=60)
            _, _, _, indices, audit = prepare(Path(tmp) / "panel.csv", config)
            self.assertGreater(audit["purged"]["rows"], 0)
            arrays = [
                set(indices[s])
                for s in ("training", "tuning", "calibration", "selection", "test")
            ]
            self.assertEqual(sum(map(len, arrays)), len(set.union(*arrays)))

    def test_future_feature_in_panel_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            config, rows, _ = fixture(path, companies_per_cohort=60)
            rows[0]["feature_available_on"] = "2099-01-01"
            write_csv(path / "panel.csv", rows)
            with self.assertRaisesRegex(ValueError, "Future"):
                prepare(path / "panel.csv", config)

    def test_stale_period_in_panel_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            config, rows, _ = fixture(path, companies_per_cohort=60)
            rows[0]["balance_period_end"] = "2000-01-01"
            write_csv(path / "panel.csv", rows)
            with self.assertRaisesRegex(ValueError, "reporting dates"):
                prepare(path / "panel.csv", config)

    def test_unverified_input_cannot_be_used_as_empirical(self):
        with tempfile.TemporaryDirectory() as tmp:
            config, _, _ = fixture(Path(tmp), companies_per_cohort=60)
            config["data_kind"] = "empirical"
            with self.assertRaisesRegex(ValueError, "kind/target"):
                prepare(Path(tmp) / "panel.csv", config)


if __name__ == "__main__":
    unittest.main()
