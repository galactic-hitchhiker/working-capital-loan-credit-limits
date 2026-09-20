"""Score later monthly features with an already selected, frozen model.

Outcome labels are not required for scoring. Eligibility and hard-stop decisions
remain part of the separately documented credit policy.
"""

import argparse
from datetime import date
from pathlib import Path

import joblib
import numpy as np

from research_common import (
    finite,
    manifest,
    new_output,
    read_csv,
    write_csv,
    write_json,
)


def predict(model_path, features_path, output):
    bundle = joblib.load(model_path)
    name = bundle["selection"]["selected_model"]
    if name is None:
        raise ValueError(
            "No model passed the predefined selection rule; policy predictions are unavailable"
        )
    selected = bundle["models"][name]
    config, features = selected["design"], selected["features"]
    rows = read_csv(
        features_path,
        ("company_id", "decision_date", "data_kind", "feature_available_on", *features),
    )
    later, seen, excluded = [], set(), 0
    for row in rows:
        decision = date.fromisoformat(row["decision_date"])
        key = (row["company_id"], decision)
        if key in seen:
            raise ValueError("Duplicate monthly predictor row")
        seen.add(key)
        if (
            row["data_kind"] != config["data_kind"]
            or date.fromisoformat(row["feature_available_on"]) > decision
        ):
            raise ValueError("Data kind mismatch or future feature information")
        if decision.day != 1:
            raise ValueError("Monthly decisions must occur on month starts")
        if decision < date.fromisoformat(config["test_start"]):
            excluded += 1
            continue
        if all(row[f] == "" for f in features):
            raise ValueError("All predictors missing for a policy decision")
        later.append(row)
    if not later:
        raise ValueError("No decision dates after model selection")
    x = np.array(
        [[finite(r[f], f, missing=True) for f in features] for r in later], dtype=float
    )
    p = selected["calibrated"].predict_proba(x)[:, 1]
    output = new_output(output)
    predictions = [
        dict(
            company_id=r["company_id"],
            decision_date=r["decision_date"],
            data_kind=config["data_kind"],
            event_type=config["event_type"],
            horizon_days=config["horizon_days"],
            model=name,
            probability=float(probability),
            threshold=selected["threshold"],
            selected=True,
            stage="policy",
            prediction_ready_on=config["test_start"],
        )
        for r, probability in zip(later, p)
    ]
    write_csv(output / "policy_predictions.csv", predictions)
    write_json(
        output / "manifest.json",
        manifest(
            [model_path, features_path],
            data_kind=config["data_kind"],
            rows=len(later),
            excluded_before_model_selection=excluded,
            selected_model=name,
            note="Frozen-model scoring only; these probabilities do not establish borrower eligibility",
        ),
    )
    return predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("models", "features", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = predict(args.models, args.features, args.output_dir)
        print(f"Saved {len(rows)} monthly predictions")
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Prediction stopped: {exc}\n")


if __name__ == "__main__":
    main()
