"""Build monthly SEC features and verified fixed-horizon outcomes offline.

Input evidence is supplied through reviewed CSV registers. Empty/unverified
coverage never creates a negative label. Original files remain untouched.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from research_common import (
    FEATURES,
    boolean,
    cik,
    file_hash,
    load_design,
    manifest,
    months,
    new_output,
    read_csv,
    write_csv,
    write_json,
)
from sec_data import snapshot
from temporal_validation import make_label

UNIVERSE_FIELDS = (
    "company_id",
    "eligible_from",
    "eligible_through",
    "verified",
    "source",
)
EVENT_FIELDS = (
    "company_id",
    "event_type",
    "event_date",
    "event_known_on",
    "review_status",
    "source",
)
COVERAGE_FIELDS = (
    "company_id",
    "decision_date",
    "observed_through",
    "coverage_known_on",
    "verified",
    "source",
)
PANEL_FIELDS = (
    "company_id",
    "decision_date",
    "data_kind",
    "event_type",
    "horizon_days",
    "horizon_end",
    "label_available_on",
    "label",
    "event_id",
    "label_source",
    "coverage_source",
    "balance_period_end",
    "flow_period_end",
    "balance_age_days",
    "flow_age_days",
    "feature_available_on",
    "flow_basis",
    *FEATURES,
)


def evidence(universe_path, event_path, coverage_path, config):
    universe, events, coverage = {}, defaultdict(list), {}
    for row in read_csv(universe_path, UNIVERSE_FIELDS):
        key = cik(row["company_id"])
        if key in universe:
            raise ValueError(
                "Duplicate universe company; use one documented continuous eligibility interval"
            )
        start, end = (
            date.fromisoformat(row["eligible_from"]),
            date.fromisoformat(row["eligible_through"]),
        )
        if start > end or not boolean(row["verified"]) or not row["source"].strip():
            raise ValueError(f"Unverified or invalid historical universe entry: {key}")
        universe[key] = (start, end)
    if not universe:
        raise ValueError(
            "Universe is empty; complete the historical eligibility register"
        )
    for row in read_csv(event_path, EVENT_FIELDS):
        key = cik(row["company_id"])
        if key not in universe:
            raise ValueError(f"Event references a company outside the universe: {key}")
        if row["event_type"] != config["event_type"]:
            raise ValueError("Event register mixes target definitions")
        if row["review_status"] not in {"confirmed", "rejected", "pending"}:
            raise ValueError("Event review status must be confirmed/rejected/pending")
        if row["review_status"] != "pending" and not row["source"].strip():
            raise ValueError("Resolved events require supporting evidence")
        if row["review_status"] == "confirmed":
            event, known = (
                date.fromisoformat(row["event_date"]),
                date.fromisoformat(row["event_known_on"]),
            )
            if known < event:
                raise ValueError("An actual event cannot be known before occurrence")
        events[key].append(row)
    for row in read_csv(coverage_path, COVERAGE_FIELDS):
        key = (cik(row["company_id"]), date.fromisoformat(row["decision_date"]))
        if key in coverage or key[0] not in universe:
            raise ValueError("Duplicate coverage row or company outside the universe")
        if boolean(row["verified"]) and not row["source"].strip():
            raise ValueError("Verified coverage requires supporting evidence")
        coverage[key] = row
    return universe, events, coverage


def outcome(company, decision, event_rows, coverage_row, config):
    if any(r["review_status"] == "pending" for r in event_rows):
        return None, "unresolved_event", "", ""
    confirmed = [r for r in event_rows if r["review_status"] == "confirmed"]
    first = min(confirmed, key=lambda r: r["event_date"]) if confirmed else None
    if first and date.fromisoformat(first["event_date"]) <= decision:
        return None, "post_event", "", ""
    if not coverage_row or not boolean(coverage_row["verified"]):
        return None, "unverified_coverage", "", ""
    row = make_label(
        company_id=company,
        decision_date=decision,
        horizon_days=config["horizon_days"],
        coverage_verified=True,
        observed_through=date.fromisoformat(coverage_row["observed_through"]),
        coverage_known_on=date.fromisoformat(coverage_row["coverage_known_on"]),
        event_date=date.fromisoformat(first["event_date"]) if first else None,
        event_verified=bool(first),
        event_known_on=date.fromisoformat(first["event_known_on"]) if first else None,
        event_source=first["source"] if first else "",
    )
    if row is None:
        return None, "incomplete_followup", "", ""
    if row.label_available_on >= date.fromisoformat(config["observed_as_of"]):
        return None, "label_not_available_at_cutoff", "", ""
    event_id = (
        f"{company}:{config['event_type']}:{first['event_date']}" if row.label else ""
    )
    return (
        row,
        "included",
        event_id,
        first["source"] if row.label else coverage_row["source"],
    )


def build(config_path, dataset, universe_path, event_path, coverage_path, output):
    config = load_design(config_path)
    if config["data_kind"] != "empirical":
        raise ValueError("SEC panel construction requires data_kind=empirical")
    universe, events, coverage = evidence(
        universe_path, event_path, coverage_path, config
    )
    output = new_output(output)
    counts, rows, feature_rows, missing_features, raw_hashes = (
        Counter(),
        [],
        [],
        Counter(),
        {},
    )
    dates = list(
        months(date.fromisoformat(config["start"]), date.fromisoformat(config["end"]))
    )
    with (output / "feature_provenance.jsonl").open("w") as provenance:
        for company, (eligible_from, eligible_through) in sorted(universe.items()):
            path = Path(dataset) / "companyfacts" / f"CIK{company}.json"
            document = json.loads(path.read_text())
            if cik(document["cik"]) != company:
                raise ValueError(f"CIK mismatch in {path}")
            raw_hashes[str(path)] = file_hash(path)
            for decision in dates:
                if not eligible_from <= decision <= eligible_through:
                    counts["outside_eligibility"] += 1
                    continue
                values, prov = snapshot(document, decision)
                if (
                    values["balance_age_days"] is None
                    or values["flow_age_days"] is None
                    or values["balance_age_days"] > config["max_balance_age_days"]
                    or values["flow_age_days"] > config["max_flow_age_days"]
                ):
                    counts["missing_or_stale_reporting_period"] += 1
                    continue
                if all(values[f] is None for f in config["features"]):
                    counts["all_predictors_missing"] += 1
                    continue
                available = max(
                    date.fromisoformat(v["filed"]) + timedelta(days=1)
                    for v in prov.values()
                    if v
                )
                feature_rows.append(
                    dict(
                        company_id=company,
                        decision_date=str(decision),
                        data_kind="empirical",
                        feature_available_on=str(available),
                        **{f: values[f] for f in FEATURES},
                    )
                )
                provenance.write(
                    json.dumps(
                        {
                            "company_id": company,
                            "decision_date": str(decision),
                            "facts": prov,
                        }
                    )
                    + "\n"
                )
                label, reason, event_id, source = outcome(
                    company,
                    decision,
                    events[company],
                    coverage.get((company, decision)),
                    config,
                )
                if label is None:
                    counts[reason] += 1
                    continue
                row = dict(
                    company_id=company,
                    decision_date=decision.isoformat(),
                    data_kind="empirical",
                    event_type=config["event_type"],
                    horizon_days=config["horizon_days"],
                    horizon_end=label.horizon_end.isoformat(),
                    label_available_on=label.label_available_on.isoformat(),
                    label=label.label,
                    event_id=event_id,
                    label_source=source,
                    coverage_source=coverage[(company, decision)]["source"],
                    feature_available_on=available.isoformat(),
                )
                for field in (
                    "balance_period_end",
                    "flow_period_end",
                    "balance_age_days",
                    "flow_age_days",
                    "flow_basis",
                    *FEATURES,
                ):
                    row[field] = values[field]
                rows.append(row)
                counts["included"] += 1
                missing_features.update(
                    f for f in config["features"] if values[f] is None
                )
    write_csv(output / "panel.csv", rows, PANEL_FIELDS)
    write_csv(
        output / "features.csv",
        feature_rows,
        ("company_id", "decision_date", "data_kind", "feature_available_on", *FEATURES),
    )
    report = {
        "data_kind": "empirical",
        "counts": dict(counts),
        "rows": len(rows),
        "companies": len({r["company_id"] for r in rows}),
        "positives": sum(r["label"] for r in rows),
        "distinct_events": len({r["event_id"] for r in rows if r["event_id"]}),
        "missing_predictors": dict(missing_features),
        "feature_rows_including_unlabeled": len(feature_rows),
        "flow_basis": "last_reported_annual_not_TTM",
    }
    write_json(output / "panel_audit.json", report)
    write_json(output / "design.json", config)
    write_json(
        output / "manifest.json",
        manifest(
            [config_path, universe_path, event_path, coverage_path],
            raw_companyfacts_sha256=raw_hashes,
            panel_sha256=file_hash(output / "panel.csv"),
            **report,
        ),
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("config", "universe", "events", "coverage", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("dataset"))
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                build(
                    args.config,
                    args.dataset,
                    args.universe,
                    args.events,
                    args.coverage,
                    args.output_dir,
                ),
                indent=2,
            )
        )
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Panel not built: {exc}\n")


if __name__ == "__main__":
    main()
