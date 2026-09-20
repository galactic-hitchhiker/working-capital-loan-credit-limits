"""Export standalone PNG/PDF research figures from saved run outputs."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from research_common import boolean, manifest, new_output, read_csv, write_json


def figures(model_dir, output, policy_dir=None):
    model_dir = Path(model_dir)
    output = new_output(output)
    selection = json.loads((model_dir / "selection.json").read_text())
    synthetic = selection["data_kind"] == "synthetic"
    banner = (
        "Synthetic software check — not thesis evidence"
        if synthetic
        else "Final test period"
    )
    rows = [
        r
        for r in read_csv(model_dir / "metrics.csv")
        if r["stage"] == "test"
        and (boolean(r["calibrated"]) or r["model"] == "constant")
    ]
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False}
    )

    def save(fig, name):
        fig.suptitle(banner, fontsize=11)
        fig.tight_layout()
        fig.savefig(output / f"{name}.png", dpi=160, bbox_inches="tight")
        fig.savefig(output / f"{name}.pdf", bbox_inches="tight")
        plt.close(fig)

    names = [r["model"].replace("_", "\n") for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for axis, metric, title in zip(
        axes,
        ("average_precision", "brier"),
        ("Average precision (higher is better)", "Brier score (lower is better)"),
    ):
        axis.bar(names, [float(r[metric]) for r in rows], color="#28798e")
        axis.set_title(title)
        axis.set_ylim(bottom=0)
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    save(fig, "model_comparison")
    fig, axis = plt.subplots(figsize=(6, 5.5))
    axis.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    grouped = defaultdict(list)
    for row in read_csv(model_dir / "reliability.csv"):
        if row["stage"] == "test":
            grouped[row["model"]].append(row)
    for name, bins in grouped.items():
        axis.plot(
            [float(r["mean_probability"]) for r in bins],
            [float(r["event_share"]) for r in bins],
            marker="o",
            markersize=4,
            label=name.replace("_", " "),
        )
    axis.set(
        xlabel="Mean predicted probability",
        ylabel="Observed event share",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axis.legend(fontsize=8)
    save(fig, "calibration")
    files = [
        model_dir / "selection.json",
        model_dir / "metrics.csv",
        model_dir / "reliability.csv",
    ]
    if policy_dir is not None:
        path = Path(policy_dir) / "limit_path.csv"
        groups = defaultdict(list)
        for row in read_csv(path):
            groups[row["company_id"]].append(row)
        fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), squeeze=False)
        for axis, (company, records) in zip(axes.flat, sorted(groups.items())[:4]):
            from datetime import date

            dates = [date.fromisoformat(r["decision_date"]) for r in records]
            axis.plot(
                dates,
                [float(r["assigned_limit"]) for r in records],
                label="Assigned limit",
            )
            axis.plot(
                dates,
                [float(r["outstanding_exposure"]) for r in records],
                "--",
                label="Outstanding exposure",
            )
            axis.set(title=f"Company {company}", ylabel=records[0]["currency"])
            axis.tick_params(axis="x", rotation=25, labelsize=8)
            axis.legend(fontsize=8)
        for axis in list(axes.flat)[min(4, len(groups)) :]:
            axis.set_visible(False)
        save(fig, "limit_paths")
        files.append(path)
    write_json(
        output / "manifest.json",
        manifest(
            files,
            data_kind=selection["data_kind"],
            note="Equal-width calibration bins; counts available in reliability.csv; plots do not show confidence intervals",
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    figures(args.models, args.output_dir, args.policy)
