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
    """Return probability scores and alert counts for binary outcome labels y.

    Ranking scores are undefined here for a single-class sample. Brier error
    still measures probability quality, independently of the alert threshold.
    """
    y, probabilities = np.asarray(y), np.asarray(probability, dtype=float)
    if (
        len(y) == 0
        or y.shape != probabilities.shape
        or not np.isfinite(probabilities).all()
        or ((probabilities < 0) | (probabilities > 1)).any()
    ):
        raise ValueError("Invalid labels or predicted probabilities")
    if not set(np.unique(y)) <= {0, 1}:
        raise ValueError("Labels must be binary")
    two_classes = len(np.unique(y)) == 2
    predicted = probabilities >= threshold
    true_negative, false_positive, false_negative, true_positive = confusion_matrix(
        y, predicted, labels=[0, 1]
    ).ravel()
    return dict(
        rows=len(y),
        positives=int(y.sum()),
        event_share=float(y.mean()),
        roc_auc=float(roc_auc_score(y, probabilities)) if two_classes else None,
        average_precision=(
            float(average_precision_score(y, probabilities)) if two_classes else None
        ),
        brier=float(brier_score_loss(y, probabilities)),
        precision=float(precision_score(y, predicted, zero_division=0)),
        recall=float(recall_score(y, predicted, zero_division=0)),
        f1=float(f1_score(y, predicted, zero_division=0)),
        threshold=float(threshold),
        true_negative=int(true_negative),
        false_positive=int(false_positive),
        false_negative=int(false_negative),
        true_positive=int(true_positive),
    )


def choose_threshold(y, probability):
    """Maximize selection-period F1, then recall, then the threshold on ties."""
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
    """Require both ranking and probability gains; return None if none qualify.

    Average precision must beat the selection event share, while Brier error
    must beat the constant training-prevalence prediction on selection rows.
    """
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
    """Summarize nonempty, equal-width probability bins for calibration checks."""
    y, probabilities = np.asarray(y), np.asarray(probability)
    # Include probability 1.0 in the last bin instead of creating an extra bin.
    assignments = np.minimum((probabilities * bins).astype(int), bins - 1)
    result = []
    for bin_index in range(bins):
        mask = assignments == bin_index
        if mask.any():
            result.append(
                dict(
                    bin=bin_index,
                    lower=bin_index / bins,
                    upper=(bin_index + 1) / bins,
                    rows=int(mask.sum()),
                    mean_probability=float(probabilities[mask].mean()),
                    event_share=float(y[mask].mean()),
                )
            )
    return result


def cluster_intervals(y, probability, companies, threshold, repeats, seed):
    """Resample entire companies. Does not model common calendar-time shocks."""
    rng = np.random.default_rng(seed)
    y, probabilities, companies = (
        np.asarray(y),
        np.asarray(probability),
        np.asarray(companies),
    )
    # Build groups once without scanning the entire panel for every company.
    order = np.argsort(companies, kind="stable")
    sorted_companies = companies[order]
    boundaries = np.flatnonzero(sorted_companies[1:] != sorted_companies[:-1]) + 1
    groups = np.split(order, boundaries)
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
        # Sample companies with replacement, keeping all their monthly rows.
        # Repeated draws intentionally repeat the same company's observations.
        indices = np.concatenate(
            [groups[j] for j in rng.integers(0, len(groups), len(groups))]
        )
        if len(np.unique(y[indices])) < 2:
            skipped += 1
            continue
        result = metrics(y[indices], probabilities[indices], threshold)
        for name in values:
            values[name].append(result[name])
    intervals = {
        name: (
            {
                "lower_95": float(np.quantile(replicate_scores, 0.025)),
                "upper_95": float(np.quantile(replicate_scores, 0.975)),
            }
            if replicate_scores
            else {"lower_95": None, "upper_95": None}
        )
        for name, replicate_scores in values.items()
    }
    return {
        "intervals": intervals,
        "replicates_requested": repeats,
        "replicates_used": repeats - skipped,
        "single_class_replicates_skipped": skipped,
        "method": "company_cluster_percentile_bootstrap",
        "limitation": "Conditional on fitted model; common time shocks and model-selection uncertainty are not captured",
    }
