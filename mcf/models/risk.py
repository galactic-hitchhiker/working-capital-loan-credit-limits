"""Chapter 4 model definitions. No fitting happens when this module is imported."""

from itertools import product

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

# Also defines the simplicity preference when selection scores tie exactly.
MODEL_ORDER = ("logistic", "logistic_l2", "random_forest", "xgboost")


def candidates(name, *, smoke=False):
    """Fixed small grids; smoke mode is only permitted with synthetic data."""
    if name == "logistic":
        grid = [{}]
    elif name == "logistic_l2":
        # C is inverse regularization strength: larger values penalize less.
        grid = [
            {"C": inverse_regularization} for inverse_regularization in (0.1, 1.0, 10.0)
        ]
    elif name == "random_forest":
        grid = [
            {
                "max_depth": max_depth,
                "min_samples_leaf": min_leaf_samples,
                "n_estimators": 300,
            }
            for max_depth, min_leaf_samples in product((3, None), (5, 20))
        ]
    elif name == "xgboost":
        grid = [
            {
                "max_depth": max_depth,
                "learning_rate": learning_rate,
                "n_estimators": 200,
            }
            for max_depth, learning_rate in product((2, 4), (0.05, 0.1))
        ]
    else:
        raise ValueError(f"Unknown model: {name}")
    if smoke:
        grid = grid[:1]
        if "n_estimators" in grid[0]:
            grid[0]["n_estimators"] = 30
    # Compare each specification with and without inverse-frequency class weights.
    return [
        {"parameters": params, "weighting": weighting}
        for params in grid
        for weighting in ("unweighted", "balanced")
    ]


def estimator(name, parameters, seed):
    """Build an unfitted classifier with preprocessing learned during fit only."""
    if name in {"logistic", "logistic_l2"}:
        classifier = LogisticRegression(
            penalty=None if name == "logistic" else "l2",
            solver="lbfgs",
            max_iter=5000,
            random_state=seed,
            **parameters,
        )
    elif name == "random_forest":
        classifier = RandomForestClassifier(random_state=seed, n_jobs=4, **parameters)
    elif name == "xgboost":
        # Keep XGBoost optional for callers using only the other model families.
        from xgboost import XGBClassifier

        classifier = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            random_state=seed,
            n_jobs=4,
            **parameters,
        )
    else:
        raise ValueError(name)
    # Missing-value flags let the classifier use reporting gaps as predictors.
    steps = [("imputer", SimpleImputer(strategy="median", add_indicator=True))]
    if name in {"logistic", "logistic_l2"}:
        # Scaling is useful for logistic optimization and the L2 penalty;
        # tree splits do not require comparable feature scales.
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps + [("model", classifier)])


def fit(estimator, x, y, weighting):
    """Fit the pipeline; x contains predictors and y contains binary outcomes."""
    # Route weights to the classifier, leaving imputation/scaling unweighted.
    weights = compute_sample_weight("balanced", y) if weighting == "balanced" else None
    return estimator.fit(x, y, model__sample_weight=weights)
