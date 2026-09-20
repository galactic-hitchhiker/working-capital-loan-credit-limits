"""Metrics, threshold selection and company-cluster uncertainty estimates."""

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    precision_recall_curve,
)


def metrics(y, probability, threshold=0.5):
    y, p = np.asarray(y), np.asarray(probability, dtype=float)
    if (
        len(y) == 0
        or y.shape != p.shape
        or not np.isfinite(p).all()
        or ((p < 0) | (p > 1)).any()
    ):
        raise ValueError("Invalid labels or predicted probabilities")
    if not set(np.unique(y)) <= {0, 1}:
        raise ValueError("Labels must be binary")
    two_classes = len(np.unique(y)) == 2
    predicted = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return dict(
        rows=len(y),
        positives=int(y.sum()),
        event_share=float(y.mean()),
        roc_auc=float(roc_auc_score(y, p)) if two_classes else None,
        average_precision=float(average_precision_score(y, p)) if two_classes else None,
        brier=float(brier_score_loss(y, p)),
        precision=float(precision_score(y, predicted, zero_division=0)),
        recall=float(recall_score(y, predicted, zero_division=0)),
        f1=float(f1_score(y, predicted, zero_division=0)),
        threshold=float(threshold),
        true_negative=int(tn),
        false_positive=int(fp),
        false_negative=int(fn),
        true_positive=int(tp),
    )


def choose_threshold(y, probability):
    if len(np.unique(y)) != 2:
        raise ValueError("Threshold selection requires both classes")
    precision, recall, thresholds = precision_recall_curve(y, probability)
    # The terminal precision=1, recall=0 point has no threshold.
    f1 = np.divide(
        2 * precision[:-1] * recall[:-1],
        precision[:-1] + recall[:-1],
        out=np.zeros_like(thresholds),
        where=(precision[:-1] + recall[:-1]) > 0,
    )
    index = max(range(len(thresholds)), key=lambda j: (f1[j], recall[j], thresholds[j]))
    return float(thresholds[index])


def select_model(scores, baseline_brier, event_share, simplicity):
    eligible = [
        name
        for name, result in scores.items()
        if result["average_precision"] is not None
        and result["average_precision"] > event_share
        and result["brier"] < baseline_brier
    ]
    return (
        min(eligible, key=lambda name: (scores[name]["brier"], simplicity.index(name)))
        if eligible
        else None
    )


def reliability_bins(y, probability, bins=10):
    y, p = np.asarray(y), np.asarray(probability)
    assignments = np.minimum((p * bins).astype(int), bins - 1)
    result = []
    for b in range(bins):
        mask = assignments == b
        if mask.any():
            result.append(
                dict(
                    bin=b,
                    lower=b / bins,
                    upper=(b + 1) / bins,
                    rows=int(mask.sum()),
                    mean_probability=float(p[mask].mean()),
                    event_share=float(y[mask].mean()),
                )
            )
    return result


def cluster_intervals(y, probability, companies, threshold, repeats, seed):
    """Resample entire companies. Does not model common calendar-time shocks."""
    rng = np.random.default_rng(seed)
    y, p, companies = np.asarray(y), np.asarray(probability), np.asarray(companies)
    groups = [np.flatnonzero(companies == company) for company in np.unique(companies)]
    values = {
        name: []
        for name in (
            "roc_auc",
            "average_precision",
            "brier",
            "recall",
            "precision",
            "f1",
        )
    }
    skipped = 0
    for _ in range(repeats):
        indices = np.concatenate(
            [groups[j] for j in rng.integers(0, len(groups), len(groups))]
        )
        if len(np.unique(y[indices])) < 2:
            skipped += 1
            continue
        result = metrics(y[indices], p[indices], threshold)
        for name in values:
            values[name].append(result[name])
    intervals = {
        name: {
            "lower_95": float(np.quantile(v, 0.025)),
            "upper_95": float(np.quantile(v, 0.975)),
        }
        if v
        else {"lower_95": None, "upper_95": None}
        for name, v in values.items()
    }
    return {
        "intervals": intervals,
        "replicates_requested": repeats,
        "replicates_used": repeats - skipped,
        "single_class_replicates_skipped": skipped,
        "method": "company_cluster_percentile_bootstrap",
        "limitation": "Conditional on fitted model; common time shocks and model-selection uncertainty are not captured",
    }
