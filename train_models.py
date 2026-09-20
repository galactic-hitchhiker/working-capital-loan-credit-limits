"""Fit, calibrate and compare Chapter 4 models with strictly chronological stages.

No real-data model can be trained from the blank templates. Run the synthetic
demo for a software check, then provide an audited panel for empirical analysis.
"""

import argparse
import json
import warnings
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.exceptions import ConvergenceWarning
from sklearn.frozen import FrozenEstimator
from sklearn.inspection import permutation_importance

from build_panel import PANEL_FIELDS
from model_evaluation import (
    choose_threshold,
    cluster_intervals,
    metrics,
    reliability_bins,
    select_model,
)
from research_common import (
    STAGES,
    file_hash,
    finite,
    load_design,
    manifest,
    new_output,
    read_csv,
    write_csv,
    write_json,
)
from risk_models import MODEL_ORDER, candidates, estimator, fit
from temporal_validation import LabeledObservation, chronological_partition


def prepare(panel_path, config):
    rows = read_csv(panel_path, PANEL_FIELDS)
    if not rows:
        raise ValueError("No verified labeled rows in panel")
    observations, lookup = [], {}
    for i, row in enumerate(rows):
        if (
            row["data_kind"] != config["data_kind"]
            or row["event_type"] != config["event_type"]
        ):
            raise ValueError("Panel data kind/target does not match the study design")
        decision = date.fromisoformat(row["decision_date"])
        horizon_end = date.fromisoformat(row["horizon_end"])
        if (
            decision.day != 1
            or not date.fromisoformat(config["start"])
            <= decision
            <= date.fromisoformat(config["end"])
            or int(row["horizon_days"]) != config["horizon_days"]
            or horizon_end != decision + timedelta(days=config["horizon_days"])
        ):
            raise ValueError("Panel dates/horizon do not match the study design")
        if date.fromisoformat(row["feature_available_on"]) > decision:
            raise ValueError("Future information in panel predictors")
        for name, limit in (
            ("balance", config["max_balance_age_days"]),
            ("flow", config["max_flow_age_days"]),
        ):
            age = (decision - date.fromisoformat(row[f"{name}_period_end"])).days
            if age != int(row[f"{name}_age_days"]) or not 0 <= age <= limit:
                raise ValueError("Stale or inconsistent reporting dates in panel")
        if all(row[f] == "" for f in config["features"]):
            raise ValueError("All predictors missing in a labeled observation")
        if (
            row["label"] not in {"0", "1"}
            or not row["label_source"]
            or not row["coverage_source"]
        ):
            raise ValueError("Labels require binary values and source evidence")
        if (row["label"] == "1") != bool(row["event_id"]):
            raise ValueError("Only positive labels must carry an event identifier")
        observation = LabeledObservation(
            row["company_id"],
            decision,
            horizon_end,
            date.fromisoformat(row["label_available_on"]),
            int(row["label"]),
        )
        observations.append(observation)
        key = (observation.company_id, observation.decision_date)
        if key in lookup:
            raise ValueError("Duplicate company-month")
        lookup[key] = i
    parts = chronological_partition(
        observations,
        **{
            k: date.fromisoformat(config[k])
            for k in (
                "tuning_start",
                "calibration_start",
                "selection_start",
                "test_start",
                "observed_as_of",
            )
        },
    )
    indices = {
        stage: np.array(
            [lookup[(o.company_id, o.decision_date)] for o in group], dtype=int
        )
        for stage, group in parts.items()
    }
    audit = {}
    for stage in STAGES:
        subset = [rows[j] for j in indices[stage]]
        positives = sum(r["label"] == "1" for r in subset)
        event_companies = {r["company_id"] for r in subset if r["label"] == "1"}
        audit[stage] = dict(
            rows=len(subset),
            positives=positives,
            negatives=len(subset) - positives,
            companies=len({r["company_id"] for r in subset}),
            event_companies=len(event_companies),
            distinct_events=len({r["event_id"] for r in subset if r["event_id"]}),
        )
        if min(positives, len(subset) - positives) < config["min_class_count"]:
            raise ValueError(
                f"{stage}: too few positive or negative labels for the fixed design"
            )
        if len(event_companies) < config["min_event_companies"]:
            raise ValueError(f"{stage}: too few distinct companies with events")
    audit["purged"] = {"rows": len(indices["purged"])}
    x = np.array(
        [
            [
                finite(r[f], f, missing=True) if r[f] != "" else np.nan
                for f in config["features"]
            ]
            for r in rows
        ],
        dtype=float,
    )
    y = np.array([int(r["label"]) for r in rows])
    if np.isnan(x[indices["training"]]).all(axis=0).any():
        raise ValueError(
            "A predictor is entirely missing in training; revise the design before evaluation"
        )
    return rows, x, y, indices, audit


def run(config_path, panel_path, output, *, smoke=False):
    config = load_design(config_path)
    if smoke and config["data_kind"] != "synthetic":
        raise ValueError("Smoke mode is only available for synthetic data")
    rows, x, y, idx, audit = prepare(panel_path, config)
    output = new_output(output)
    write_json(output / "design.json", config)
    write_json(output / "stage_audit.json", audit)
    membership = [
        {
            "company_id": rows[j]["company_id"],
            "decision_date": rows[j]["decision_date"],
            "stage": stage,
        }
        for stage, js in idx.items()
        for j in js
    ]
    write_csv(output / "stage_membership.csv", membership)
    train, tune, cal, selection, test = (idx[s] for s in STAGES)
    refit = np.concatenate([train, tune])
    seed, thresholds, bundles, selection_scores, tuning_results = (
        config["seed"],
        {},
        {},
        {},
        [],
    )
    # A documented constant benchmark estimated from the ORIGINAL training stage.
    prevalence = float(y[train].mean())
    base_selection = metrics(y[selection], np.full(len(selection), prevalence))
    # Convergence problems stop the run rather than silently accepting unstable fits.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        for name in MODEL_ORDER:
            print(f"Fitting {name} ({config['data_kind']})", flush=True)
            best = None
            for candidate_index, spec in enumerate(candidates(name, smoke=smoke)):
                model = fit(
                    estimator(name, spec["parameters"], seed),
                    x[train],
                    y[train],
                    spec["weighting"],
                )
                score = metrics(y[tune], model.predict_proba(x[tune])[:, 1])
                tuning_results.append(
                    dict(
                        model=name,
                        candidate=candidate_index,
                        parameters=json.dumps(spec["parameters"], sort_keys=True),
                        weighting=spec["weighting"],
                        **score,
                    )
                )
                # Fixed tuning rule: AP, then Brier, then candidate enumeration.
                rank = (-score["average_precision"], score["brier"], candidate_index)
                if best is None or rank < best[0]:
                    best = (rank, spec)
            spec = best[1]
            base = fit(
                estimator(name, spec["parameters"], seed),
                x[refit],
                y[refit],
                spec["weighting"],
            )
            calibrated = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
            calibrated.fit(x[cal], y[cal])
            probability = calibrated.predict_proba(x[selection])[:, 1]
            threshold = choose_threshold(y[selection], probability)
            thresholds[name] = threshold
            selection_scores[name] = metrics(y[selection], probability, threshold)
            bundles[name] = dict(
                base=base,
                calibrated=calibrated,
                specification=spec,
                threshold=threshold,
                features=config["features"],
                design=config,
            )
    chosen = select_model(
        selection_scores,
        base_selection["brier"],
        float(y[selection].mean()),
        list(MODEL_ORDER),
    )
    decision = dict(
        selected_model=chosen,
        status="selected_on_selection_period"
        if chosen
        else "no_validated_predictive_improvement",
        data_kind=config["data_kind"],
        constant_training_prevalence=prevalence,
        baseline_selection_brier=base_selection["brier"],
        selection_event_share=float(y[selection].mean()),
        thresholds=thresholds,
        selection_scores=selection_scores,
        selection_rule="AP > selection event share and Brier < training-prevalence baseline; lowest Brier; simpler on exact tie",
    )
    # Persist selection BEFORE generating any final-test model predictions.
    write_json(output / "selection.json", decision)
    write_csv(output / "tuning_scores.csv", tuning_results)
    joblib.dump({"models": bundles, "selection": decision}, output / "models.joblib")
    evaluations, predictions, reliability, intervals = [], [], [], {}
    coefficients, importance = [], []
    for name in ("constant", *MODEL_ORDER):
        threshold = thresholds.get(name, 0.5)
        for stage in ("selection", "test"):
            js = idx[stage]
            p = (
                np.full(len(js), prevalence)
                if name == "constant"
                else bundles[name]["calibrated"].predict_proba(x[js])[:, 1]
            )
            evaluations.append(
                dict(
                    model=name,
                    stage=stage,
                    calibrated=name != "constant",
                    **metrics(y[js], p, threshold),
                )
            )
            for j, probability in zip(js, p):
                predictions.append(
                    dict(
                        company_id=rows[j]["company_id"],
                        decision_date=rows[j]["decision_date"],
                        data_kind=config["data_kind"],
                        event_type=config["event_type"],
                        horizon_days=config["horizon_days"],
                        event_id=rows[j]["event_id"],
                        label=int(y[j]),
                        model=name,
                        stage=stage,
                        probability=float(probability),
                        threshold=threshold,
                        selected=name == chosen,
                        prediction_ready_on=config["test_start"],
                    )
                )
            for bin_row in reliability_bins(y[js], p):
                reliability.append(dict(model=name, stage=stage, **bin_row))
            if stage == "test":
                intervals[name] = cluster_intervals(
                    y[js],
                    p,
                    [rows[j]["company_id"] for j in js],
                    threshold,
                    config["bootstrap_repeats"],
                    seed,
                )
        if name == "constant":
            continue
        base = bundles[name]["base"]
        for stage in ("selection", "test"):
            js = idx[stage]
            raw = base.predict_proba(x[js])[:, 1]
            evaluations.append(
                dict(
                    model=name,
                    stage=stage,
                    calibrated=False,
                    **metrics(y[js], raw, 0.5),
                )
            )
        if name.startswith("logistic"):
            feature_names = base.named_steps["imputer"].get_feature_names_out(
                config["features"]
            )
            for feature, coefficient in zip(
                feature_names, base.named_steps["model"].coef_[0]
            ):
                coefficients.append(
                    dict(
                        model=name,
                        feature=feature,
                        coefficient=float(coefficient),
                        scale="one standard deviation after imputation; before calibration",
                    )
                )
    # Interpretation on SELECTION only; final-test errors are left as reporting.
    if chosen:
        result = permutation_importance(
            bundles[chosen]["calibrated"],
            x[selection],
            y[selection],
            scoring="neg_brier_score",
            n_repeats=5 if smoke else 20,
            random_state=seed,
            n_jobs=1,
        )
        for f, mean, std in zip(
            config["features"], result.importances_mean, result.importances_std
        ):
            importance.append(
                dict(
                    model=chosen,
                    feature=f,
                    mean_brier_increase=float(mean),
                    std=float(std),
                )
            )
    write_csv(output / "metrics.csv", evaluations)
    write_csv(output / "predictions.csv", predictions)
    write_csv(output / "reliability.csv", reliability)
    write_csv(output / "coefficients.csv", coefficients)
    write_csv(
        output / "permutation_importance.csv",
        importance,
        ("model", "feature", "mean_brier_increase", "std"),
    )
    write_json(output / "bootstrap_intervals.json", intervals)
    write_json(
        output / "manifest.json",
        manifest(
            [config_path, panel_path],
            data_kind=config["data_kind"],
            smoke=smoke,
            selected_model=chosen,
            status="synthetic_software_check_only"
            if config["data_kind"] == "synthetic"
            else "empirical_run",
            note="Four implemented financial predictors; no causal, realized-loss or private-company transfer claim",
        ),
    )
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.config, args.panel, args.output_dir, smoke=args.smoke)
        print(
            json.dumps(
                {k: result[k] for k in ("selected_model", "status", "data_kind")},
                indent=2,
            )
        )
    except (ValueError, KeyError, OSError, ConvergenceWarning) as exc:
        parser.exit(2, f"Model run stopped: {exc}\n")


if __name__ == "__main__":
    main()
