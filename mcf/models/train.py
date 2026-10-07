"""Fit, calibrate and compare Chapter 4 models with strictly chronological stages.

The empirical SEC disclosure study uses mcf.data.empirical and the fixed design
in configs/study.sec_disclosure.json. Synthetic mode is only a software check.

Run from the repository root:
    .venv/bin/python -m mcf.models.train [parameters]

Parameters:
    --config PATH: Required study-design JSON defining features and chronological stages.
    --panel PATH: Required labeled monthly panel CSV.
    --output-dir PATH: Required destination for fitted models, metrics and audit files.
    --smoke: Use a smaller training grid for a software check (default: off).
    -h, --help: Show command usage and exit.
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

from mcf.data.panel import PANEL_FIELDS
from mcf.models.evaluation import (
    choose_threshold,
    cluster_intervals,
    metrics,
    reliability_bins,
    select_model,
)
from mcf.common import (
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
from mcf.models.risk import MODEL_ORDER, candidates, estimator, fit
from mcf.models.temporal import LabeledObservation, chronological_partition

CALIBRATION_ORDER = ("identity", "sigmoid")


def select_calibration(scores):
    """Choose the lowest-Brier mapping, preferring raw probabilities on a tie."""
    return min(
        CALIBRATION_ORDER,
        key=lambda method: (scores[method]["brier"], CALIBRATION_ORDER.index(method)),
    )


def rolling_tuning_folds(rows, training_indices, tuning_indices):
    """Build expanding annual folds without using labels unavailable at fold start."""
    years = sorted(
        {date.fromisoformat(rows[j]["decision_date"]).year for j in tuning_indices}
    )
    folds = []
    for year in years:
        fold_start = date(year, 1, 1)
        available_history = np.array(
            [
                j
                for j in np.concatenate([training_indices, tuning_indices])
                if date.fromisoformat(rows[j]["decision_date"]) < fold_start
                and date.fromisoformat(rows[j]["label_available_on"]) < fold_start
            ],
            dtype=int,
        )
        validation_indices = np.array(
            [
                j
                for j in tuning_indices
                if date.fromisoformat(rows[j]["decision_date"]).year == year
            ],
            dtype=int,
        )
        if len(validation_indices):
            folds.append(
                {
                    "validation_year": year,
                    "fit_indices": available_history,
                    "validation_indices": validation_indices,
                }
            )
    if not folds:
        raise ValueError("No annual tuning folds could be constructed")
    return folds


def prepare(panel_path, config):
    """Validate the panel and return rows, predictors, labels, stage indices and audit."""
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
    # Purge labels that would not yet be available when the next stage starts.
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
    """Tune, refit, calibrate and select before evaluating the untouched test stage."""
    config = load_design(config_path)
    if smoke and config["data_kind"] != "synthetic":
        raise ValueError("Smoke mode is only available for synthetic data")
    rows, x, y, stage_indices, audit = prepare(panel_path, config)
    output = new_output(output)
    write_json(output / "design.json", config)
    membership = [
        {
            "company_id": rows[j]["company_id"],
            "decision_date": rows[j]["decision_date"],
            "stage": stage,
        }
        for stage, stage_rows in stage_indices.items()
        for j in stage_rows
    ]
    write_csv(output / "stage_membership.csv", membership)
    train, tune, calibration, selection, test = (stage_indices[s] for s in STAGES)
    tuning_folds = rolling_tuning_folds(rows, train, tune)
    for fold in tuning_folds:
        validation_indices = fold["validation_indices"]
        positives = int(y[validation_indices].sum())
        event_companies = {
            rows[j]["company_id"] for j in validation_indices if y[j] == 1
        }
        if min(positives, len(validation_indices) - positives) < config[
            "min_class_count"
        ]:
            raise ValueError(
                f"tuning fold {fold['validation_year']}: too few positive or negative labels"
            )
        if len(event_companies) < config["min_event_companies"]:
            raise ValueError(
                f"tuning fold {fold['validation_year']}: too few event companies"
            )
    audit["rolling_tuning"] = {
        "ranking_rule": "highest mean annual AP lift; then highest mean annual Brier skill; then fixed candidate order",
        "folds": [
            {
                "validation_year": fold["validation_year"],
                "fit_rows": len(fold["fit_indices"]),
                "fit_positives": int(y[fold["fit_indices"]].sum()),
                "validation_rows": len(fold["validation_indices"]),
                "validation_positives": int(y[fold["validation_indices"]].sum()),
            }
            for fold in tuning_folds
        ],
    }
    write_json(output / "stage_audit.json", audit)
    # Only training and tuning observations may enter the final base-model fit.
    refit_indices = np.concatenate([train, tune])
    seed = config["seed"]
    thresholds = {}
    calibration_methods = {}
    calibration_scores = {}
    bundles = {}
    selection_scores = {}
    tuning_results = []
    tuning_fold_results = []
    # A documented constant benchmark estimated from the ORIGINAL training stage.
    prevalence = float(y[train].mean())
    base_selection = metrics(y[selection], np.full(len(selection), prevalence))
    # Convergence problems stop the run rather than silently accepting unstable fits.
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        for name in MODEL_ORDER:
            print(f"Fitting {name} ({config['data_kind']})", flush=True)
            best = None
            for candidate_index, specification in enumerate(
                candidates(name, smoke=smoke)
            ):
                fold_scores = []
                for fold in tuning_folds:
                    fit_indices = fold["fit_indices"]
                    validation_indices = fold["validation_indices"]
                    model = fit(
                        estimator(name, specification["parameters"], seed),
                        x[fit_indices],
                        y[fit_indices],
                        specification["weighting"],
                    )
                    score = metrics(
                        y[validation_indices],
                        model.predict_proba(x[validation_indices])[:, 1],
                    )
                    fold_prevalence = float(y[fit_indices].mean())
                    baseline = metrics(
                        y[validation_indices],
                        np.full(len(validation_indices), fold_prevalence),
                    )
                    ap_lift = score["average_precision"] / score["event_share"]
                    brier_skill = 1 - score["brier"] / baseline["brier"]
                    fold_scores.append(
                        {
                            "ap_lift": ap_lift,
                            "brier_skill": brier_skill,
                            **score,
                        }
                    )
                    tuning_fold_results.append(
                        dict(
                            model=name,
                            candidate=candidate_index,
                            validation_year=fold["validation_year"],
                            fit_rows=len(fit_indices),
                            fit_positives=int(y[fit_indices].sum()),
                            baseline_brier=baseline["brier"],
                            ap_lift=ap_lift,
                            brier_skill=brier_skill,
                            parameters=json.dumps(
                                specification["parameters"], sort_keys=True
                            ),
                            weighting=specification["weighting"],
                            **score,
                        )
                    )
                mean_ap_lift = float(
                    np.mean([score["ap_lift"] for score in fold_scores])
                )
                mean_brier_skill = float(
                    np.mean([score["brier_skill"] for score in fold_scores])
                )
                tuning_results.append(
                    dict(
                        model=name,
                        candidate=candidate_index,
                        folds=len(fold_scores),
                        parameters=json.dumps(
                            specification["parameters"], sort_keys=True
                        ),
                        weighting=specification["weighting"],
                        mean_roc_auc=float(
                            np.mean([score["roc_auc"] for score in fold_scores])
                        ),
                        mean_average_precision=float(
                            np.mean(
                                [score["average_precision"] for score in fold_scores]
                            )
                        ),
                        mean_ap_lift=mean_ap_lift,
                        minimum_ap_lift=float(
                            np.min([score["ap_lift"] for score in fold_scores])
                        ),
                        mean_brier=float(
                            np.mean([score["brier"] for score in fold_scores])
                        ),
                        mean_brier_skill=mean_brier_skill,
                    )
                )
                print(
                    f"  candidate {candidate_index + 1}: "
                    f"mean annual AP lift={mean_ap_lift:.3f}, "
                    f"Brier skill={mean_brier_skill:.4f}",
                    flush=True,
                )
                rank = (-mean_ap_lift, -mean_brier_skill, candidate_index)
                if best is None or rank < best[0]:
                    best = (rank, specification)
            specification = best[1]
            # Start a fresh pipeline so preprocessing is refitted on these rows too.
            base = fit(
                estimator(name, specification["parameters"], seed),
                x[refit_indices],
                y[refit_indices],
                specification["weighting"],
            )
            # Fit sigmoid calibration on its separate period, then let the
            # selection stage choose it or the untouched raw probabilities.
            sigmoid = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
            sigmoid.fit(x[calibration], y[calibration])
            calibration_models = {"identity": base, "sigmoid": sigmoid}
            candidate_probabilities = {
                method: model.predict_proba(x[selection])[:, 1]
                for method, model in calibration_models.items()
            }
            method_scores = {
                method: metrics(y[selection], probabilities)
                for method, probabilities in candidate_probabilities.items()
            }
            calibration_method = select_calibration(method_scores)
            probability = candidate_probabilities[calibration_method]
            predictor = calibration_models[calibration_method]
            # Freeze the alert threshold here for the held-out evaluation.
            threshold = choose_threshold(y[selection], probability)
            thresholds[name] = threshold
            calibration_methods[name] = calibration_method
            calibration_scores[name] = method_scores
            selection_scores[name] = metrics(y[selection], probability, threshold)
            bundles[name] = dict(
                base=base,
                # Retain this key for scoring compatibility. It now contains the
                # selected probability mapping, which may be the raw base model.
                calibrated=predictor,
                sigmoid=sigmoid,
                calibration_method=calibration_method,
                specification=specification,
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
        status=(
            "selected_on_selection_period"
            if chosen
            else "no_validated_predictive_improvement"
        ),
        data_kind=config["data_kind"],
        constant_training_prevalence=prevalence,
        baseline_selection_brier=base_selection["brier"],
        selection_event_share=float(y[selection].mean()),
        thresholds=thresholds,
        calibration_methods=calibration_methods,
        calibration_scores=calibration_scores,
        selection_scores=selection_scores,
        calibration_rule="Lowest selection-period Brier; identity/raw probabilities on exact tie",
        selection_rule="AP > selection event share and Brier < training-prevalence baseline; lowest Brier; simpler on exact tie",
    )
    # Persist selection before generating any held-out model predictions.
    write_json(output / "selection.json", decision)
    write_csv(output / "tuning_scores.csv", tuning_results)
    write_csv(output / "tuning_fold_scores.csv", tuning_fold_results)
    joblib.dump({"models": bundles, "selection": decision}, output / "models.joblib")
    evaluations, predictions, reliability, intervals = [], [], [], {}
    coefficients, importance = [], []
    for name in ("constant", *MODEL_ORDER):
        threshold = thresholds.get(name, 0.5)
        for stage in ("selection", "test"):
            stage_rows = stage_indices[stage]
            probabilities = (
                np.full(len(stage_rows), prevalence)
                if name == "constant"
                else bundles[name]["calibrated"].predict_proba(x[stage_rows])[:, 1]
            )
            evaluations.append(
                dict(
                    model=name,
                    stage=stage,
                    calibrated=(
                        name != "constant"
                        and calibration_methods[name] == "sigmoid"
                    ),
                    calibration_method=(
                        "constant" if name == "constant" else calibration_methods[name]
                    ),
                    **metrics(y[stage_rows], probabilities, threshold),
                )
            )
            for j, probability in zip(stage_rows, probabilities):
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
            for bin_row in reliability_bins(y[stage_rows], probabilities):
                reliability.append(dict(model=name, stage=stage, **bin_row))
            if stage == "test":
                intervals[name] = cluster_intervals(
                    y[stage_rows],
                    probabilities,
                    [rows[j]["company_id"] for j in stage_rows],
                    threshold,
                    config["bootstrap_repeats"],
                    seed,
                )
        if name == "constant":
            continue
        base = bundles[name]["base"]
        # When sigmoid wins, retain raw probabilities as diagnostics. When
        # identity wins, the primary evaluation above already contains them.
        if calibration_methods[name] != "identity":
            for stage in ("selection", "test"):
                stage_rows = stage_indices[stage]
                raw_probabilities = base.predict_proba(x[stage_rows])[:, 1]
                evaluations.append(
                    dict(
                        model=name,
                        stage=stage,
                        calibrated=False,
                        calibration_method="identity_diagnostic",
                        **metrics(y[stage_rows], raw_probabilities, 0.5),
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
    # Interpret on selection only; held-out errors remain reporting evidence.
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
            status=(
                "synthetic_software_check_only"
                if config["data_kind"] == "synthetic"
                else "empirical_run"
            ),
            note=(
                f"{len(config['features'])} configured financial predictors; "
                "no causal, realized-loss or private-company transfer claim"
            ),
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
