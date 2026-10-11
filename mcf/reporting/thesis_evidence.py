"""Copy small real-study evidence/figures and build supplementary appendices.

This intentionally refreshes docs/tables, docs/figures and Appendices C/D from
completed runs. It never trains a model or replaces source datasets.

Run from the repository root:
    .venv/bin/python -m mcf.reporting.thesis_evidence [parameters]

Parameters:
    --docs PATH: Thesis documentation destination; refreshes tables, figures and appendices
        (default: docs).
    --inventory PATH: Inventory audit source (default: results/empirical_inventory).
    --panel PATH: Panel audit/design source (default: results/empirical_panel).
    --models PATH: Training metrics and evidence source (default: results/empirical_models).
    --descriptive PATH: Data-report source (default: results/empirical_descriptive_final).
    --model-report PATH: Model-report source (default: results/empirical_model_figures_final).
    --policy PATH: Policy-scenario source (default: results/empirical_policy).
    --policy-report PATH: Policy-report source (default: results/empirical_policy_figures_final).
    --examples PATH: Illustrative worked-example source (default: results/policy).
    -h, --help: Show command usage and exit.
"""

import argparse
import json
import shutil
from pathlib import Path

from mcf.common import file_hash, manifest, read_csv, write_csv, write_json


def md_table(headers, rows):
    return (
        "\n".join(
            [
                "| " + " | ".join(headers) + " |",
                "|" + "|".join("---" for _ in headers) + "|",
                *["| " + " | ".join(str(v) for v in row) + " |" for row in rows],
            ]
        )
        + "\n"
    )


def export(args):
    """Refresh the selected evidence copies and appendices from completed run files."""
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
                dict(filename=name, source=str(source), sha256=file_hash(source))
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
                dict(filename=source.name, source=str(source), sha256=file_hash(source))
            )
    write_csv(tables / "source_crosswalk.csv", crosswalk)
    scores = read_csv(args.models / "metrics.csv")
    selection = json.loads((args.models / "selection.json").read_text())
    selected_model = selection["selected_model"]
    intervals = json.loads((args.models / "bootstrap_intervals.json").read_text())
    appendix_c = "# Appendix C: Supplementary Empirical Results\n\n"
    appendix_c += (
        "These tables are generated from the completed real-data run. "
        "Probabilities and metrics are decimal fractions unless marked as percentages. "
        f"The selection rule accepted {selected_model.replace('_', ' ')}. "
        "The 2023–2025 period was excluded from this run's development steps but "
        "was examined during earlier project work.\n\n"
    )
    appendix_c += "## C.1 2023–2025 probability error for raw and selected mappings\n\n"

    def test_score(model, method):
        return next(
            r
            for r in scores
            if r["model"] == model
            and r["stage"] == "test"
            and r["calibration_method"] == method
        )

    mapping_rows = []
    for name in ("logistic", "logistic_l2", "random_forest", "xgboost"):
        method = selection["calibration_methods"][name]
        selected = test_score(name, method)
        raw = selected if method == "identity" else test_score(name, "identity_diagnostic")
        mapping_rows.append(
            [
                name,
                f"{float(raw['brier']):.8f}",
                method,
                f"{float(selected['brier']):.8f}",
            ]
        )
    appendix_c += md_table(
        ["Model", "Raw Brier", "Selected mapping", "Selected Brier"],
        mapping_rows,
    )
    appendix_c += (
        "\nRaw diagnostic threshold metrics use 0.5; selected mappings use the frozen "
        "selection threshold. Probability metrics do not depend on that threshold. "
        "Sigmoid calibration worsened the forest's selection-period Brier score, so "
        "the workflow retained its raw identity mapping.\n\n"
    )
    appendix_c += "## C.2 Company-cluster 95% percentile intervals\n\n"
    appendix_c += md_table(
        ["Model", "ROC-AUC interval", "Average-precision interval", "Brier interval"],
        [
            [
                name,
                *[
                    f"{result['intervals'][key]['lower_95']:.6f}–{result['intervals'][key]['upper_95']:.6f}"
                    for key in ("roc_auc", "average_precision", "brier")
                ],
            ]
            for name, result in intervals.items()
        ],
    )
    appendix_c += "\nAll models use 500 valid bootstrap repetitions. These intervals condition on fitted models and omit shared time shocks and model-selection uncertainty. They are not paired confidence intervals for model differences.\n\n"
    appendix_c += "## C.3 2023–2025 episode detection at frozen thresholds\n\n"
    appendix_c += md_table(
        [
            "Model",
            "Threshold",
            "Disclosure episodes detected",
            "Total disclosure episodes",
            "Episode-level recall",
        ],
        [
            [
                r["model"],
                f"{float(r['threshold']):.6f}",
                r["detected_episodes"],
                r["disclosure_episodes"],
                f"{100*float(r['episode_recall']):.2f}%",
            ]
            for r in read_csv(args.model_report / "event_detection.csv")
        ],
    )
    appendix_c += "\nAn episode is detected if at least one of its positive monthly rows meets the model's threshold. This differs from row-level recall and does not measure detection of every legal bankruptcy or missed payment.\n\n"
    appendix_c += "## C.4 Predictor distributions before chronological purging\n\n"
    appendix_c += md_table(
        ["Predictor", "Missing", "1st percentile", "Median", "99th percentile"],
        [
            [
                r["feature"],
                f"{100*float(r['missing_share']):.2f}%",
                *(f"{float(r[k]):.5g}" for k in ("p01", "median", "p99")),
            ]
            for r in read_csv(args.descriptive / "feature_summary.csv")
        ],
    )
    appendix_c += "\nThe full minima/maxima and quality flags are in feature_summary.csv and data_summary.json. Extreme ratios are retained; these summaries do not certify source accounting quality.\n\n"
    appendix_c += "## C.5 Full policy sensitivity\n\n"
    appendix_c += md_table(
        ["Scenario", "Mean limit/assets", "Zero limits", "Mean absolute change/assets"],
        [
            [
                r["scenario"],
                f"{100*float(r['mean_limit_to_assets']):.4f}%",
                f"{100*float(r['zero_limit_share']):.2f}%",
                f"{100*float(r['mean_absolute_change_to_assets']):.5f}%",
            ]
            for r in read_csv(args.policy / "policy_sensitivity.csv")
        ],
    )
    appendix_c += (
        "\nThe base scenario uses the selected random-forest disclosure probability. "
        "The base and capacity-only scenarios share monthly safeguards. The independent "
        "unsmoothed formula can reopen after zero, while the base cannot do so automatically. "
        "Other model mappings are comparisons. Additional-debt, cash, exposure and cap "
        "values remain assumptions rather than observed facility terms.\n\n"
    )
    appendix_c += "## C.6 Annual panel counts before chronological purging\n\n"
    annual_counts = json.loads((args.panel / "panel_audit.json").read_text())["annual_counts"]
    appendix_c += md_table(
        ["Decision year", "Observations", "Positive rows"],
        [
            [year, f"{counts['rows']:,}", f"{counts['positives']:,}"]
            for year, counts in sorted(annual_counts.items())
        ],
    )
    appendix_c += "\nPositive rows are monthly outcomes, not distinct episodes. A December decision can refer to a disclosure in the following year. Figure 6.1 summarizes these counts.\n\n"
    appendix_c += "## C.7 Evidence files\n\nFull local paths and hashes are in tables/source_crosswalk.csv. Small evidence copies are in tables/. Complete row-level predictions and policy histories remain under results/. File references: panel_audit.json, metrics.csv, bootstrap_intervals.json, annual_test_metrics.csv, event_detection.csv, feature_summary.csv, feature_correlations.csv, sector_summary.csv, policy_sensitivity.csv.\n"
    (docs / "13_appendix_c.md").write_text(appendix_c)
    appendix_d = "# Appendix D: Hypothetical Worked Policy Examples\n\n"
    appendix_d += "These examples support Chapter 5 and are separate from the empirical results. The borrower, probabilities and facility amounts are hypothetical. Each row changes the original example independently; the rows are not a time sequence.\n\n"
    appendix_d += md_table(
        [
            "Case",
            "Capacity (USD)",
            "Preliminary limit (USD)",
            "Assigned limit (USD)",
            "Available credit (USD)",
            "Excess exposure (USD)",
        ],
        [
            [
                r["scenario"],
                *(
                    f"{float(r[k]):,.2f}"
                    for k in (
                        "capacity",
                        "raw_limit",
                        "assigned_limit",
                        "available_credit",
                        "excess_exposure",
                    )
                ),
            ]
            for r in read_csv(args.examples / "worked_examples.csv")
        ],
    )
    appendix_d += "\nThe base uses annual revenue of USD 12 million, operating cash flow of USD 1.2 million, eligible cash of USD 500,000, additional principal due of USD 50,000, a 2% illustrative event probability and a USD 150,000 cap. The previous limit is USD 70,000 and outstanding exposure is USD 60,000.\n\n"
    appendix_d += "Risk stress raises the probability to 8%; cash-flow stress halves operating cash flow; the lower-cap case sets the cap to USD 40,000. The information case holds the previous limit, and the hard stop sets the assigned limit to zero. Neither a lower limit nor a hard stop removes outstanding exposure.\n\n"
    appendix_d += "The separate sensitivity.csv contains 18 combinations of risk probability and risk sensitivity for this hypothetical borrower. It is not the empirical policy_sensitivity.csv. File references: mcf/policy/examples.py, mcf/policy/credit.py, worked_examples.csv, sensitivity.csv.\n"
    (docs / "14_appendix_d.md").write_text(appendix_d)
    write_json(
        tables / "release_manifest.json",
        manifest(
            [r["source"] for r in crosswalk],
            artifact="Completed thesis evidence",
            data_kind="empirical_except_explicit_hypothetical_worked_examples",
        ),
    )
    print(f"Exported {len(crosswalk)} evidence files and Appendices C/D")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = dict(
        docs="docs",
        inventory="results/empirical_inventory",
        panel="results/empirical_panel",
        models="results/empirical_models",
        descriptive="results/empirical_descriptive_final",
        model_report="results/empirical_model_figures_final",
        policy="results/empirical_policy",
        policy_report="results/empirical_policy_figures_final",
        examples="results/policy",
    )
    for key, value in defaults.items():
        parser.add_argument(
            "--" + key.replace("_", "-"), type=Path, default=Path(value)
        )
    export(parser.parse_args())
