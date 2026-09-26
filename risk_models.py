"""Chapter 4 model definitions. No fitting happens when this module is imported."""

from itertools import product

from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

MODEL_ORDER = ("logistic", "logistic_l2", "random_forest", "xgboost")


def candidates(name, *, smoke=False):
    """Fixed small grids; smoke mode is only permitted with synthetic data."""
    if name == "logistic":
        grid = [{}]
    elif name == "logistic_l2":
        grid = [{"C": c} for c in (0.1, 1.0, 10.0)]
    elif name == "random_forest":
        grid = [
            dict(max_depth=d, min_samples_leaf=m, n_estimators=300)
            for d, m in product((3, None), (5, 20))
        ]
    elif name == "xgboost":
        grid = [
            dict(max_depth=d, learning_rate=r, n_estimators=200)
            for d, r in product((2, 4), (0.05, 0.1))
        ]
    else:
        raise ValueError(f"Unknown model: {name}")
    if smoke:
        grid = grid[:1]
        if "n_estimators" in grid[0]:
            grid[0]["n_estimators"] = 30
    return [
        {"parameters": params, "weighting": weighting}
        for params in grid
        for weighting in ("unweighted", "balanced")
    ]


def estimator(name, parameters, seed):
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
    steps = [("imputer", SimpleImputer(strategy="median", add_indicator=True))]
    if name in {"logistic", "logistic_l2"}:
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps + [("model", classifier)])


def fit(estimator, x, y, weighting):
    weights = compute_sample_weight("balanced", y) if weighting == "balanced" else None
    return estimator.fit(x, y, model__sample_weight=weights)
