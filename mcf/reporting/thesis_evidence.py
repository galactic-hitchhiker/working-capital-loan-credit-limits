"""Copy small real-study evidence and figures into the thesis directories.

This refreshes ``docs/thesis/tables`` and ``docs/thesis/figures`` from completed
runs. It never trains a model or replaces source datasets.

Run from the repository root:
    .venv/bin/python -m mcf.reporting.thesis_evidence [parameters]

Parameters:
    --docs PATH: Thesis destination for copied tables and figures.
    --inventory PATH: Inventory audit source.
    --panel PATH: Panel audit and design source.
    --models PATH: Training metrics and model evidence source.
    --descriptive PATH: Descriptive-report source.
    --model-report PATH: Model-report source.
    --policy PATH: Policy-scenario source.
    --policy-report PATH: Policy-report source.
    --examples PATH: Illustrative worked-example source.
    -h, --help: Show command usage and exit.
"""

import argparse
import shutil
from pathlib import Path

from mcf.common import file_hash, manifest, write_csv, write_json


def export(args):
    """Refresh selected evidence copies from completed run files."""
    docs = args.docs
    tables, figures = docs / "tables", docs / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    selections = {
        args.inventory: ["inventory_audit.json"],
        args.panel: ["panel_audit.json", "design.json"],
        args.models: [
            "stage_audit.json",
            "selection.json",
            "tuning_scores.csv",
            "tuning_fold_scores.csv",
            "metrics.csv",
            "bootstrap_intervals.json",
            "coefficients.csv",
            "permutation_importance.csv",
        ],
        args.descriptive: [
            "feature_summary.csv",
            "feature_correlations.csv",
            "sector_summary.csv",
            "data_summary.json",
        ],
        args.model_report: [
            "annual_test_metrics.csv",
            "event_detection.csv",
            "probability_summary.csv",
            "quantile_calibration.csv",
        ],
        args.policy: [
            "policy_audit.json",
            "policy_sensitivity.csv",
            "scenario_parameters.json",
        ],
        args.policy_report: [
            "case_summary.csv",
            "case_paths.csv",
            "policy_report.json",
        ],
        args.examples: ["worked_examples.csv", "sensitivity.csv"],
    }
    crosswalk = []
    for directory, filenames in selections.items():
        for name in filenames:
            source = directory / name
            shutil.copy2(source, tables / name)
            crosswalk.append(
                {"filename": name, "source": str(source), "sha256": file_hash(source)}
            )
    for directory, name in [
        (args.descriptive, "sample_over_time"),
        (args.model_report, "model_diagnostics"),
        (args.policy_report, "policy_cases"),
        (args.policy_report, "policy_sensitivity"),
    ]:
        for extension in ("png", "pdf"):
            source = directory / f"{name}.{extension}"
            shutil.copy2(source, figures / source.name)
            crosswalk.append(
                {
                    "filename": source.name,
                    "source": str(source),
                    "sha256": file_hash(source),
                }
            )
    write_csv(tables / "source_crosswalk.csv", crosswalk)
    write_json(
        tables / "release_manifest.json",
        manifest(
            [r["source"] for r in crosswalk],
            artifact="Completed thesis evidence",
            data_kind="empirical_except_explicit_hypothetical_worked_examples",
        ),
    )
    print(f"Exported {len(crosswalk)} evidence files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = {
        "docs": "docs/thesis",
        "inventory": "results/empirical_inventory",
        "panel": "results/empirical_panel",
        "models": "results/empirical_models",
        "descriptive": "results/empirical_descriptive_final",
        "model_report": "results/empirical_model_figures_final",
        "policy": "results/empirical_policy",
        "policy_report": "results/empirical_policy_figures_final",
        "examples": "results/policy",
    }
    for key, value in defaults.items():
        parser.add_argument(
            "--" + key.replace("_", "-"), type=Path, default=Path(value)
        )
    export(parser.parse_args())
