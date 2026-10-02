"""Export descriptive statistics and publication figures from completed real runs."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve

from model_evaluation import metrics
from research_common import (
    FEATURES,
    manifest,
    new_output,
    read_csv,
    write_csv,
    write_json,
)


def table(path, rows, columns):
    text = "| " + " | ".join(label for key, label in columns) + " |\n"
    text += "|" + "|".join("---" for _ in columns) + "|\n"
    for row in rows:
        text += (
            "| " + " | ".join(str(row.get(key, "")) for key, label in columns) + " |\n"
        )
    Path(path).write_text(text)


def data_report(panel, output):
    """Describe the original labeled panel before chronological stage purging."""
    output = new_output(output)
    values, labels, sectors, annual = [], [], defaultdict(Counter), defaultdict(Counter)
    with Path(panel).open() as stream:
        for r in csv.DictReader(stream):
            values.append([float(r[f]) if r[f] else np.nan for f in FEATURES])
            y = int(r["label"])
            labels.append(y)
            sectors[r["sic"][:2]]["rows"] += 1
            sectors[r["sic"][:2]]["positives"] += y
            annual[r["decision_date"][:4]]["rows"] += 1
            annual[r["decision_date"][:4]]["positives"] += y
    x = np.array(values)
    stats = []
    for j, f in enumerate(FEATURES):
        v = x[:, j]
        good = v[np.isfinite(v)]
        stats.append(
            dict(
                feature=f,
                rows=len(v),
                missing=int(np.isnan(v).sum()),
                missing_share=float(np.isnan(v).mean()),
                minimum=float(good.min()),
                p01=float(np.quantile(good, 0.01)),
                p25=float(np.quantile(good, 0.25)),
                median=float(np.median(good)),
                p75=float(np.quantile(good, 0.75)),
                p99=float(np.quantile(good, 0.99)),
                maximum=float(good.max()),
            )
        )
    correlations = []
    for j, f in enumerate(FEATURES):
        for k, g in enumerate(FEATURES):
            good = np.isfinite(x[:, j]) & np.isfinite(x[:, k])
            correlations.append(
                dict(
                    feature_1=f,
                    feature_2=g,
                    pairwise_rows=int(good.sum()),
                    pearson=float(np.corrcoef(x[good, j], x[good, k])[0, 1]),
                )
            )
    write_csv(output / "feature_summary.csv", stats)
    write_csv(output / "feature_correlations.csv", correlations)
    write_csv(
        output / "sector_summary.csv",
        [
            dict(sic_division=k, **v, event_share=v["positives"] / v["rows"])
            for k, v in sorted(sectors.items())
        ],
    )
    write_json(
        output / "data_summary.json",
        dict(
            rows=len(labels),
            positives=sum(labels),
            predictors=stats,
            quality_flags=dict(
                negative_current_ratio_rows=int(np.sum(x[:, 0] < 0)),
                assets_below_10000_rows=int(
                    np.sum(x[:, FEATURES.index("log_assets")] < np.log(10000))
                ),
            ),
            annual={k: dict(v) for k, v in sorted(annual.items())},
        ),
    )
    years = sorted(annual)
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True, constrained_layout=True)
    axes[0].bar(years, [annual[y]["rows"] for y in years], color="#346699")
    axes[0].set_ylabel("Company-month observations")
    axes[1].plot(
        years,
        [100 * annual[y]["positives"] / annual[y]["rows"] for y in years],
        marker="o",
        color="#a34b25",
    )
    axes[1].set_ylabel("Positive row share (%)")
    axes[1].tick_params(axis="x", rotation=45)
    fig.suptitle("Real SEC disclosure panel, before chronological purging")
    save(fig, output, "sample_over_time")
    write_json(output / "manifest.json", manifest([panel], data_kind="empirical"))


def save(fig, output, name):
    fig.savefig(output / (name + ".png"), dpi=180, bbox_inches="tight")
    fig.savefig(output / (name + ".pdf"), bbox_inches="tight")
    plt.close(fig)


def model_report(models, output):
    """Report frozen test predictions at row, event-company and calendar-year levels."""
    output = new_output(output)
    groups = defaultdict(list)
    with (Path(models) / "predictions.csv").open() as stream:
        for r in csv.DictReader(stream):
            if r["stage"] == "test":
                groups[r["model"]].append(r)
    annual, events, probability_stats, quantiles = [], [], [], []
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), constrained_layout=True)
    colors = dict(zip(groups, plt.rcParams["axes.prop_cycle"].by_key()["color"]))
    for name, rows in groups.items():
        y = np.array([int(r["label"]) for r in rows])
        p = np.array([float(r["probability"]) for r in rows])
        threshold = float(rows[0]["threshold"])
        years = np.array([r["decision_date"][:4] for r in rows])
        for year in sorted(set(years)):
            mask = years == year
            annual.append(
                dict(model=name, year=year, **metrics(y[mask], p[mask], threshold))
            )
        by_event = defaultdict(list)
        for r in rows:
            if r["event_id"]:
                by_event[r["event_id"]].append(r)
        detected = sum(
            any(float(r["probability"]) >= threshold for r in company_rows)
            for company_rows in by_event.values()
        )
        events.append(
            dict(
                model=name,
                event_companies=len(by_event),
                detected_event_companies=detected,
                event_company_recall=detected / len(by_event),
                threshold=threshold,
            )
        )
        probability_stats.append(
            dict(
                model=name,
                mean_probability=float(p.mean()),
                observed_share=float(y.mean()),
                p50=float(np.median(p)),
                p95=float(np.quantile(p, 0.95)),
                p99=float(np.quantile(p, 0.99)),
                maximum=float(p.max()),
            )
        )
        precision, recall, _ = precision_recall_curve(y, p)
        if name == "constant":
            axes[0].axhline(
                float(y.mean()),
                linestyle="--",
                color=colors[name],
                label="constant event-rate baseline",
            )
        else:
            axes[0].step(
                recall,
                precision,
                where="post",
                color=colors[name],
                label=name.replace("_", " "),
            )
        if name != "constant":
            # Ties stay in the same bin; no arbitrary splitting of equal scores.
            edges = np.unique(np.quantile(p, np.linspace(0, 1, 11)))
            assigned = np.searchsorted(edges[1:-1], p, side="right")
            model_bins = []
            for b in np.unique(assigned):
                mask = assigned == b
                r = dict(
                    model=name,
                    bin=int(b),
                    rows=int(mask.sum()),
                    positives=int(y[mask].sum()),
                    mean_probability=float(p[mask].mean()),
                    event_share=float(y[mask].mean()),
                    min_probability=float(p[mask].min()),
                    max_probability=float(p[mask].max()),
                )
                model_bins.append(r)
                quantiles.append(r)
            axes[1].plot(
                [r["mean_probability"] * 100 for r in model_bins],
                [r["event_share"] * 100 for r in model_bins],
                marker="o",
                color=colors[name],
                label=name.replace("_", " "),
            )
    axes[0].set(
        xlabel="Recall",
        ylabel="Precision",
        ylim=(0, 0.25),
        title="Held-out precision–recall (precision axis 0–25%)",
    )
    axes[0].legend(fontsize=8)
    upper = max(axes[1].get_xlim()[1], axes[1].get_ylim()[1])
    axes[1].plot([0, upper], [0, upper], "--", color="gray", linewidth=1)
    axes[1].set(
        xlabel="Mean predicted probability (%)",
        ylabel="Observed event share (%)",
        title="Held-out reliability by probability quantile",
    )
    fig.suptitle("Frozen models, held-out SEC observations, 2023–2025")
    save(fig, output, "model_diagnostics")
    write_csv(output / "annual_test_metrics.csv", annual)
    write_csv(output / "event_detection.csv", events)
    write_csv(output / "probability_summary.csv", probability_stats)
    write_csv(output / "quantile_calibration.csv", quantiles)
    write_json(
        output / "model_summary.json",
        dict(
            event_detection=events,
            probability_summary=probability_stats,
            annual_metrics=annual,
        ),
    )
    write_json(
        output / "manifest.json",
        manifest([Path(models) / "predictions.csv"], data_kind="empirical"),
    )


def policy_report(policy, output):
    """Plot illustrative company paths and summarize the saved policy scenarios."""
    output = new_output(output)
    audit = json.loads((Path(policy) / "policy_audit.json").read_text())
    selected_model = audit["selected_model"]
    base_label = (
        f"Selected {selected_model.replace('_', ' ')}"
        if selected_model
        else "Constant-probability fallback"
    )
    comparison_model = "xgboost" if selected_model != "xgboost" else "random_forest"
    rows = read_csv(Path(policy) / "comparison_paths.csv")
    groups = defaultdict(list)
    for r in rows:
        groups[r["company_id"]].append(r)
    # Illustrative, disclosed case selection: Apple if present, followed by two
    # issuers with observed hard stops and the longest available pre-stop paths.
    stop_candidates = []
    for company, company_rows in groups.items():
        before = [r for r in company_rows if r["known_disclosure"] == "False"]
        after = [r for r in company_rows if r["known_disclosure"] == "True"]
        if before and after:
            stop_candidates.append((len(before), company))
    choices = ["0000320193"] if "0000320193" in groups else []
    choices += [
        company
        for _, company in sorted(stop_candidates, key=lambda t: (-t[0], t[1]))[:2]
    ]
    cases, case_rows = [], []
    fig, axes = plt.subplots(
        len(choices),
        1,
        figsize=(9, 3 * len(choices)),
        squeeze=False,
        constrained_layout=True,
    )
    for ax, company in zip(axes[:, 0], choices):
        company_rows = groups[company]
        dates = np.array([np.datetime64(r["decision_date"]) for r in company_rows])
        for key, label in [
            ("assigned_limit", base_label),
            ("capacity_only_limit", "Capacity only"),
            (
                f"exploratory_{comparison_model}_limit",
                f"{comparison_model.replace('_', ' ').title()} comparison",
            ),
        ]:
            ax.plot(dates, [float(r[key]) / 1e6 for r in company_rows], label=label)
        known = [r for r in company_rows if r["known_disclosure"] == "True"]
        if known:
            ax.axvline(
                np.datetime64(known[0]["decision_date"]),
                color="black",
                linestyle=":",
                label="First observed monthly hard stop",
            )
        ax.set(title=company_rows[0]["entity_name"], ylabel="Limit (USD million)")
        ax.legend(fontsize=8)
        cases.append(
            dict(
                company_id=company,
                entity_name=company_rows[0]["entity_name"],
                rows=len(company_rows),
                first_month=company_rows[0]["decision_date"],
                last_month=company_rows[-1]["decision_date"],
                initial_limit=float(company_rows[0]["assigned_limit"]),
                final_limit=float(company_rows[-1]["assigned_limit"]),
                first_hard_stop=known[0]["decision_date"] if known else "",
                initial_probability=float(company_rows[0]["probability"]),
                selection_basis="Apple reference case, or longest observed pre-hard-stop path; illustrative post hoc cases",
            )
        )
        case_rows.extend(company_rows)
    fig.suptitle("Historical policy scenarios; facility inputs are assumptions")
    save(fig, output, "policy_cases")
    write_csv(output / "case_paths.csv", case_rows)
    write_csv(output / "case_summary.csv", cases)
    # Report limitations of a fixed cap-only benchmark and sensitivity in equal-row units.
    fixed_above = sum(
        float(r["fixed_initial_limit"]) > float(r["raw_limit"]) + 1e-8 for r in rows
    )
    write_json(
        output / "policy_report.json",
        dict(
            cases=cases,
            fixed_above_current_preliminary_rows=fixed_above,
            fixed_above_current_preliminary_share=fixed_above / len(rows),
            rows=len(rows),
        ),
    )
    summaries = read_csv(Path(policy) / "policy_sensitivity.csv")
    selected = [
        r
        for r in summaries
        if r["scenario"]
        in {
            "base",
            "capacity_only",
            "cash_eligible_half",
            "cash_eligible_zero",
            "additional_debt_assets_0.005",
            "cap_assets_0.005",
            "cap_assets_0.02",
            f"exploratory_{comparison_model}",
        }
    ]
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.barh(
        [r["scenario"].replace("_", " ") for r in selected],
        [100 * float(r["mean_limit_to_assets"]) for r in selected],
        color="#346699",
    )
    ax.set(
        xlabel="Mean assigned limit / reported total assets (%)",
        title="Policy sensitivity on the same real financial histories",
    )
    save(fig, output, "policy_sensitivity")
    write_json(
        output / "manifest.json",
        manifest(
            [Path(policy) / "comparison_paths.csv"], data_kind="empirical_scenarios"
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("data", "models", "policy"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    {"data": data_report, "models": model_report, "policy": policy_report}[args.action](
        args.input, args.output_dir
    )
