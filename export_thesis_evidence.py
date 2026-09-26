"""Copy small real-study evidence/figures and build supplementary appendices.

This intentionally refreshes docs/tables, docs/figures and Appendices C/D from
completed runs. It never trains a model or replaces source datasets.
"""
import argparse
import json
import shutil
from pathlib import Path

from research_common import file_hash, manifest, read_csv, write_csv, write_json


def md_table(headers, rows):
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *["| " + " | ".join(str(v) for v in row) + " |" for row in rows],
    ]) + "\n"


def export(args):
    docs = args.docs
    tables, figures = docs / "tables", docs / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    selections = {
        args.inventory: ["inventory_audit.json"],
        args.panel: ["panel_audit.json", "design.json"],
        args.models: ["stage_audit.json", "selection.json", "tuning_scores.csv", "metrics.csv",
                      "bootstrap_intervals.json", "coefficients.csv", "permutation_importance.csv"],
        args.descriptive: ["feature_summary.csv", "feature_correlations.csv", "sector_summary.csv", "data_summary.json"],
        args.model_report: ["annual_test_metrics.csv", "event_detection.csv", "probability_summary.csv", "quantile_calibration.csv"],
        args.policy: ["policy_audit.json", "policy_sensitivity.csv", "scenario_parameters.json"],
        args.policy_report: ["case_summary.csv", "case_paths.csv", "policy_report.json"],
        args.examples: ["worked_examples.csv", "sensitivity.csv"],
    }
    crosswalk = []
    for directory, filenames in selections.items():
        for name in filenames:
            source = directory / name
            shutil.copy2(source, tables / name)
            crosswalk.append(dict(filename=name, source=str(source), sha256=file_hash(source)))
    for directory, name in [(args.descriptive,"sample_over_time"), (args.model_report,"model_diagnostics"),
                            (args.policy_report,"policy_cases"), (args.policy_report,"policy_sensitivity")]:
        for extension in ("png","pdf"):
            source = directory / f"{name}.{extension}"
            shutil.copy2(source, figures / source.name)
            crosswalk.append(dict(filename=source.name, source=str(source), sha256=file_hash(source)))
    write_csv(tables / "source_crosswalk.csv", crosswalk)
    scores = read_csv(args.models / "metrics.csv")
    intervals = json.loads((args.models / "bootstrap_intervals.json").read_text())
    c = "# Appendix C: Supplementary Empirical Results\n\n"
    c += "These tables are generated from the completed real-data run. Probabilities and metrics are decimal fractions unless marked as percentages. No model passed the selection rule.\n\n"
    c += "## C.1 Test probability error before and after calibration\n\n"
    c += md_table(["Model","Raw Brier","Calibrated Brier"], [
        [name, *(f"{float(next(r for r in scores if r['model']==name and r['stage']=='test' and r['calibrated']==flag)['brier']):.8f}" for flag in ("False","True"))]
        for name in ("logistic","logistic_l2","random_forest","xgboost")])
    c += "\nRaw threshold metrics use 0.5; calibrated threshold metrics use the frozen selection threshold. Probability metrics do not depend on that threshold. Calibration worsens the forest's Brier score in this experiment.\n\n"
    c += "## C.2 Company-cluster 95% percentile intervals\n\n"
    c += md_table(["Model","ROC-AUC interval","Average-precision interval","Brier interval"], [
        [name, *[f"{result['intervals'][key]['lower_95']:.6f}–{result['intervals'][key]['upper_95']:.6f}"
                 for key in ("roc_auc","average_precision","brier")]] for name,result in intervals.items()])
    c += "\nAll models use 500 valid bootstrap repetitions. These intervals condition on fitted models and omit shared time shocks and model-selection uncertainty. They are not paired confidence intervals for model differences.\n\n"
    c += "## C.3 Test event detection at frozen thresholds\n\n"
    c += md_table(["Model","Threshold","Event companies detected","Total event companies","Company-level recall"], [
        [r["model"],f"{float(r['threshold']):.6f}",r["detected_event_companies"],r["event_companies"],
         f"{100*float(r['event_company_recall']):.2f}%"] for r in read_csv(args.model_report/"event_detection.csv")])
    c += "\nA company is detected if at least one positive monthly row meets its model's threshold. This differs from row-level recall and does not measure detection of every legal bankruptcy.\n\n"
    c += "## C.4 Predictor distributions before chronological purging\n\n"
    c += md_table(["Predictor","Missing","1st percentile","Median","99th percentile"], [
        [r["feature"],f"{100*float(r['missing_share']):.2f}%",*(f"{float(r[k]):.5g}" for k in ("p01","median","p99"))]
        for r in read_csv(args.descriptive/"feature_summary.csv")])
    c += "\nThe full minima/maxima and quality flags are in feature_summary.csv and data_summary.json. Extreme ratios are retained; these summaries do not certify source accounting quality.\n\n"
    c += "## C.5 Full policy sensitivity\n\n"
    c += md_table(["Scenario","Mean limit/assets","Zero limits","Mean absolute change/assets"], [
        [r["scenario"],f"{100*float(r['mean_limit_to_assets']):.4f}%",f"{100*float(r['zero_limit_share']):.2f}%",
         f"{100*float(r['mean_absolute_change_to_assets']):.5f}%"] for r in read_csv(args.policy/"policy_sensitivity.csv")])
    c += "\nThe base and capacity-only scenarios share monthly safeguards. The independent unsmoothed formula can reopen after zero, while the base cannot do so automatically. Exploratory model mappings are not validated policy choices. Additional-debt and cash cases are assumptions, not observed borrower obligations.\n\n"
    c += "## C.6 Evidence files\n\nFull local paths and hashes are in tables/source_crosswalk.csv. Small evidence copies are in tables/. Complete row-level predictions and policy histories remain under results/. File references: metrics.csv, bootstrap_intervals.json, annual_test_metrics.csv, event_detection.csv, feature_summary.csv, feature_correlations.csv, sector_summary.csv, policy_sensitivity.csv.\n"
    (docs/"appendix_c.md").write_text(c)
    d = "# Appendix D: Hypothetical Worked Policy Examples\n\n"
    d += "These examples support Chapter 5 and are separate from the empirical results. The borrower, probabilities and facility amounts are hypothetical. Each row changes the original example independently; the rows are not a time sequence.\n\n"
    d += md_table(["Case","Capacity (USD)","Preliminary limit (USD)","Assigned limit (USD)","Available credit (USD)","Excess exposure (USD)"], [
        [r["scenario"],*(f"{float(r[k]):,.2f}" for k in ("capacity","raw_limit","assigned_limit","available_credit","excess_exposure"))]
        for r in read_csv(args.examples/"worked_examples.csv")])
    d += "\nThe base uses annual revenue of USD 12 million, operating cash flow of USD 1.2 million, eligible cash of USD 500,000, additional principal due of USD 50,000, a 2% illustrative event probability and a USD 150,000 cap. The previous limit is USD 70,000 and outstanding exposure is USD 60,000.\n\n"
    d += "Risk stress raises the probability to 8%; cash-flow stress halves operating cash flow; the lower-cap case sets the cap to USD 40,000. The information case holds the previous limit, and the hard stop sets the assigned limit to zero. Neither a lower limit nor a hard stop removes outstanding exposure.\n\n"
    d += "The separate sensitivity.csv contains 18 combinations of risk probability and risk sensitivity for this hypothetical borrower. It is not the empirical policy_sensitivity.csv. File references: policy_examples.py, credit_policy.py, worked_examples.csv, sensitivity.csv.\n"
    (docs/"appendix_d.md").write_text(d)
    write_json(tables/"release_manifest.json", manifest([r["source"] for r in crosswalk],
        artifact="Completed thesis evidence", data_kind="empirical_except_explicit_hypothetical_worked_examples"))
    print(f"Exported {len(crosswalk)} evidence files and Appendices C/D")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = dict(
        docs="docs", inventory="results/empirical_inventory", panel="results/empirical_panel",
        models="results/empirical_models", descriptive="results/empirical_descriptive_final",
        model_report="results/empirical_model_figures_final", policy="results/empirical_policy",
        policy_report="results/empirical_policy_figures_final", examples="results/policy")
    for key,value in defaults.items():
        parser.add_argument("--"+key.replace("_","-"),type=Path,default=Path(value))
    export(parser.parse_args())
