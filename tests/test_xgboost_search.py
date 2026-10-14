"""Regression checks for the opt-in wider search and model-family filtering."""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from mcf.models.risk import candidates
    from mcf.models.train import run
    from mcf.workflows.demo import fixture
    HAS_ML = True
except ModuleNotFoundError:
    HAS_ML = False


@unittest.skipUnless(HAS_ML, "Model dependencies are unavailable")
class XGBoostSearchTests(unittest.TestCase):
    def test_expansion_retains_legacy_candidates_and_is_reproducible(self):
        original = candidates("xgboost")
        expanded = candidates("xgboost", xgboost_candidates=64, seed=42)
        self.assertEqual(len(original), 8)
        self.assertEqual(len(expanded), 64)
        self.assertEqual(expanded[:8], original)
        self.assertEqual(expanded, candidates("xgboost", xgboost_candidates=64, seed=42))
        self.assertNotEqual(expanded[8:], candidates("xgboost", xgboost_candidates=64, seed=7)[8:])
        self.assertEqual(len({json.dumps(c, sort_keys=True) for c in expanded}), 64)

    def test_invalid_budgets_are_rejected(self):
        for budget in (0, 7, 9, 8.0, True, "64"):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                candidates("xgboost", xgboost_candidates=budget)

    def test_xgboost_only_run_keeps_constant_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture(root)
            config_path = root / "design.json"
            config = json.loads(config_path.read_text())
            config.update(models=["xgboost"], xgboost_candidates=64, bootstrap_repeats=2)
            config_path.write_text(json.dumps(config))
            output = root / "models"
            result = run(config_path, root / "panel.csv", output, smoke=True)
            self.assertEqual(set(result["selection_scores"]), {"xgboost"})
            from mcf.common import read_csv
            self.assertEqual(
                {row["model"] for row in read_csv(output / "metrics.csv")},
                {"constant", "xgboost"},
            )
            self.assertEqual(len(read_csv(output / "tuning_scores.csv")), 2)


if __name__ == "__main__":
    unittest.main()
