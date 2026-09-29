"""Small, shared data contracts and reproducibility helpers (standard library)."""

import csv
import hashlib
import importlib.metadata
import json
import math
import platform
from datetime import date, datetime, timezone
from pathlib import Path

FEATURES = (
    "current_ratio",
    "cash_and_equivalents_to_assets",
    "working_capital_to_assets",
    "return_on_average_assets",
    "operating_cashflow_to_average_assets",
    "log_assets",
)
STAGES = ("training", "tuning", "calibration", "selection", "test")


def read_csv(path, required=()):
    """Read string-valued rows, allowing a UTF-8 BOM and checking required columns."""
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = set(required) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"{path}: malformed CSV row")
    return rows


def write_csv(path, rows, fields=None):
    """Write rows in the supplied column order, or infer it from the first row."""
    rows = list(rows)
    fields = list(fields or (rows[0] if rows else []))
    if not fields:
        raise ValueError("Column names required for an empty CSV")
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def boolean(value):
    if isinstance(value, str):
        value = value.strip().lower()
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    raise ValueError(f"Expected true/false, received {value!r}")


def finite(value, name, *, missing=False):
    """Parse a finite number; optionally preserve empty inputs as None."""
    if value in (None, "") and missing:
        return None
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name}: expected a number") from exc
    if isinstance(value, bool) or not math.isfinite(number):
        raise ValueError(f"{name}: expected a finite number")
    return number


def cik(value):
    """Normalize an SEC Central Index Key to its ten-digit filename representation."""
    value = str(value).strip()
    if not value.isdigit() or not 0 < int(value) < 10**10:
        raise ValueError(f"Invalid CIK: {value!r}")
    return value.zfill(10)


def months(start, end):
    """Yield every month start in the inclusive date range."""
    if start.day != 1 or end.day != 1 or end < start:
        raise ValueError("Monthly dates must be increasing month starts")
    while start <= end:
        yield start
        start = date(start.year + (start.month == 12), start.month % 12 + 1, 1)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_output(path):
    """Prepare an empty run directory without overwriting previous research outputs."""
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError(
            f"Output directory is not empty: {path}; choose a new run directory"
        )
    path.mkdir(parents=True, exist_ok=True)
    return path


def manifest(paths, **details):
    """Record input/code hashes and environment versions to identify a research run."""
    packages = {}
    for name in ("numpy", "scipy", "scikit-learn", "xgboost", "matplotlib", "joblib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    code = {p.name: file_hash(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "packages": packages,
        "inputs_sha256": {str(p): file_hash(p) for p in paths},
        "code_sha256": code,
        **details,
    }


def load_design(path):
    """Validate the fixed target, chronology and predictor contract before a run."""
    config = json.loads(Path(path).read_text())
    if config.get("design_status") != "fixed":
        raise ValueError(
            "Study design is draft: define the target, dates and controls, then set design_status to fixed"
        )
    required = (
        "data_kind",
        "event_type",
        "event_definition",
        "horizon_days",
        "start",
        "end",
        "tuning_start",
        "calibration_start",
        "selection_start",
        "test_start",
        "observed_as_of",
        "features",
        "max_balance_age_days",
        "max_flow_age_days",
        "min_class_count",
        "min_event_companies",
        "bootstrap_repeats",
        "seed",
    )
    unresolved = [name for name in required if config.get(name) is None]
    if unresolved:
        raise ValueError(
            f"Complete these study settings before execution: {', '.join(unresolved)}"
        )
    if config.get("data_kind") not in {"empirical", "synthetic"}:
        raise ValueError("data_kind must be empirical or synthetic")
    if not config.get("event_type") or not config.get("event_definition"):
        raise ValueError("One explicit event type and definition are required")
    for name in (
        "horizon_days",
        "max_balance_age_days",
        "max_flow_age_days",
        "min_class_count",
        "min_event_companies",
        "bootstrap_repeats",
    ):
        if type(config.get(name)) is not int or config[name] < 1:
            raise ValueError(f"{name} must be a positive integer")
    boundaries = [
        date.fromisoformat(config[k])
        for k in (
            "start",
            "tuning_start",
            "calibration_start",
            "selection_start",
            "test_start",
        )
    ]
    if boundaries != sorted(set(boundaries)) or any(d.day != 1 for d in boundaries):
        raise ValueError("Study boundaries must be strictly increasing month starts")
    end = date.fromisoformat(config["end"])
    observed = date.fromisoformat(config["observed_as_of"])
    if end.day != 1 or end < boundaries[-1] or observed <= end:
        raise ValueError("Invalid study end or observation cutoff")
    features = config.get("features", [])
    if (
        not features
        or len(features) != len(set(features))
        or set(features) - set(FEATURES)
    ):
        raise ValueError(
            f"Select unique implemented predictors from {FEATURES}; identifiers/outcomes are forbidden"
        )
    if type(config.get("seed")) is not int:
        raise ValueError("Integer random seed required")
    return config
