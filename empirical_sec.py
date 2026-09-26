"""Build a REAL SEC filing-disclosure target from the supplied local dataset.

The target is first observed 8-K/8-K/A Item 1.03 DISCLOSURE, not legal bankruptcy
onset or payment default. The user selected this target on 2026-09-21. Nothing in
this module converts a missing filing into a verified absence of legal default.
"""

import argparse
import csv
import json
from bisect import bisect_left
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from build_panel import PANEL_FIELDS
from research_common import (
    FEATURES,
    file_hash,
    load_design,
    manifest,
    months,
    new_output,
    read_csv,
    write_csv,
    write_json,
)
from sec_data import filing_rows
from sec_point_in_time import FactIndex

PERIODIC = {"10-K", "10-K/A", "10-Q", "10-Q/A"}
ISSUER_FORMS = PERIODIC | {"8-K", "8-K/A"}
TARGET = "first_sec_item_1_03_disclosure"


def item_103(value):
    """Match the exact disclosure item across the separators used in SEC files."""
    return "1.03" in str(value).replace(";", ",").replace(" ", ",").split(",")


def inventory(dataset, output, cutoff):
    """Audit local filing histories, screen issuers and record observed disclosures."""
    output = new_output(output)
    paths = sorted((Path(dataset) / "companyfacts").glob("CIK*.json"))
    rows, events, errors, counts, years = [], [], [], Counter(), Counter()
    with (output / "source_hashes.jsonl").open("w") as hashes:
        for n, facts_path in enumerate(paths, 1):
            company = facts_path.stem[3:]
            path = Path(dataset) / "submissions" / facts_path.name
            try:
                submissions = json.loads(path.read_text())
                filings, missing = filing_rows(
                    submissions, Path(dataset) / "submissions"
                )
                # Audit every referenced archive's advertised row count as well.
                count_mismatches = []
                for metadata in submissions.get("filings", {}).get("files", []):
                    history = Path(dataset) / "submissions" / metadata["name"]
                    if history.exists():
                        block = json.loads(history.read_text())
                        if len(block.get("accessionNumber", [])) != metadata.get(
                            "filingCount"
                        ):
                            count_mismatches.append(metadata["name"])
                        hashes.write(
                            json.dumps(
                                {"path": str(history), "sha256": file_hash(history)}
                            )
                            + "\n"
                        )
                hashes.write(
                    json.dumps({"path": str(path), "sha256": file_hash(path)}) + "\n"
                )
                dated = [
                    f
                    for f in filings
                    if f["filingDate"] and f["filingDate"] < str(cutoff)
                ]
                periodic = sorted(
                    {f["filingDate"] for f in dated if f["form"] in PERIODIC}
                )
                issuer = sorted(
                    {f["filingDate"] for f in dated if f["form"] in ISSUER_FORMS}
                )
                disclosures = sorted(
                    [
                        f
                        for f in dated
                        if f["form"] in {"8-K", "8-K/A"} and item_103(f["items"])
                    ],
                    key=lambda f: (f["filingDate"], f["accessionNumber"]),
                )
                # SIC is current metadata; this screen does not reconstruct
                # historical industry membership or listing eligibility.
                sic = str(submissions.get("sic", ""))
                # Record the first failed screen, in this fixed priority order.
                if missing or count_mismatches:
                    exclusion = "incomplete_archives"
                elif not periodic:
                    exclusion = "no_domestic_periodic_filings"
                elif not sic.isdigit() or int(sic) == 0:
                    exclusion = "unknown_sic"
                elif 6000 <= int(sic) <= 6999:
                    exclusion = "finance_insurance_real_estate"
                else:
                    exclusion = "candidate"
                counts[exclusion] += 1
                row = dict(
                    company_id=company,
                    entity_name=submissions.get("name", ""),
                    sic=sic,
                    sic_description=submissions.get("sicDescription", ""),
                    current_tickers=";".join(submissions.get("tickers", [])),
                    screen=exclusion,
                    first_periodic=periodic[0] if periodic else "",
                    last_issuer_filing=issuer[-1] if issuer else "",
                    periodic_filings=len(periodic),
                    issuer_dates=json.dumps(issuer),
                    issuer_filings=len(issuer),
                    missing_archives=len(missing),
                    archive_count_mismatches=len(count_mismatches),
                    first_disclosure_date=(
                        disclosures[0]["filingDate"] if disclosures else ""
                    ),
                    first_disclosure_accession=(
                        disclosures[0]["accessionNumber"] if disclosures else ""
                    ),
                    disclosure_records=len(disclosures),
                )
                rows.append(row)
                if disclosures and exclusion == "candidate":
                    years[row["first_disclosure_date"][:4]] += 1
                for j, f in enumerate(disclosures):
                    events.append(
                        dict(
                            company_id=company,
                            entity_name=row["entity_name"],
                            screen=exclusion,
                            first_observed=j == 0,
                            **f,
                            source_url=f"https://www.sec.gov/Archives/edgar/data/{int(company)}/{f['accessionNumber'].replace('-', '')}/{f['primaryDocument']}",
                        )
                    )
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(dict(company_id=company, error=str(exc)))
            if n % 1000 == 0:
                print(f"Inventory: {n}/{len(paths)} companies", flush=True)
    write_csv(output / "issuer_inventory.csv", rows)
    write_csv(output / "disclosure_events.csv", events)
    report = dict(
        companyfacts_files=len(paths),
        inventoried_companies=len(rows),
        screen_counts=dict(counts),
        disclosure_records=len(events),
        candidate_first_disclosures_by_year=dict(sorted(years.items())),
        cutoff=str(cutoff),
        errors=errors,
        target_note="Observed disclosure dates only; includes receivership and reorganization disclosures, not verified default dates",
    )
    write_json(output / "inventory_audit.json", report)
    write_json(
        output / "manifest.json",
        manifest(
            [],
            data_kind="empirical",
            **report,
            source_hash_list_sha256=file_hash(output / "source_hashes.jsonl"),
        ),
    )
    return report


def disclosure_label(decision, event_date, last_issuer_date, horizon_days, cutoff):
    """Observed reporting event; right-censor negative windows after issuer follow-up.

    Event labels are retained once the disclosure itself is observed, even if the
    issuer stops reporting after it. Negative windows need an issuer filing at or
    after their horizon. Both wait until the full horizon has elapsed before use.
    """
    horizon = decision + timedelta(days=horizon_days)
    if event_date is not None and event_date <= decision:
        return None, "post_first_disclosure"
    if horizon + timedelta(days=1) >= cutoff:
        return None, "cutoff_censoring"
    if event_date is not None and event_date <= horizon:
        return 1, "observed_disclosure"
    if last_issuer_date < horizon:
        return None, "issuer_followup_censoring"
    return 0, "no_recorded_disclosure_in_observed_window"


def panel(dataset, inventory_dir, config_path, output):
    """Write monthly predictors, disclosure labels, source provenance and exclusions."""
    config = load_design(config_path)
    if config["data_kind"] != "empirical" or config["event_type"] != TARGET:
        raise ValueError("This builder is only for the real SEC disclosure target")
    output = new_output(output)
    dates = list(
        months(date.fromisoformat(config["start"]), date.fromisoformat(config["end"]))
    )
    cutoff = date.fromisoformat(config["observed_as_of"])
    inventory_path = Path(inventory_dir) / "issuer_inventory.csv"
    issuers = [r for r in read_csv(inventory_path) if r["screen"] == "candidate"]
    counts, companies, event_ids, year_counts, missing = (
        Counter(),
        set(),
        set(),
        {},
        Counter(),
    )
    feature_fields = (
        "company_id",
        "decision_date",
        "data_kind",
        "feature_available_on",
        *FEATURES,
        "entity_name",
        "sic",
        "currency",
        "assets",
        "revenue_annual",
        "operating_cashflow_annual",
        "reported_cash",
        "balance_period_end",
        "flow_period_end",
        "balance_age_days",
        "flow_age_days",
        "known_disclosure",
    )
    panel_fields = (*PANEL_FIELDS, "entity_name", "sic")
    with (
        (output / "panel.csv").open("w", newline="") as panel_stream,
        (output / "features.csv").open("w", newline="") as feature_stream,
        (output / "feature_provenance.jsonl").open("w") as provenance,
        (output / "companyfacts_hashes.jsonl").open("w") as hashes,
    ):
        panel_writer, feature_writer = csv.DictWriter(
            panel_stream, fieldnames=panel_fields
        ), csv.DictWriter(feature_stream, fieldnames=feature_fields)
        panel_writer.writeheader()
        feature_writer.writeheader()
        for n, issuer in enumerate(issuers, 1):
            company = issuer["company_id"]
            path = Path(dataset) / "companyfacts" / f"CIK{company}.json"
            document = json.loads(path.read_text())
            index = FactIndex(document, dates[-1])
            hashes.write(
                json.dumps({"path": str(path), "sha256": file_hash(path)}) + "\n"
            )
            first = date.fromisoformat(issuer["first_periodic"])
            last = date.fromisoformat(issuer["last_issuer_filing"])
            issuer_dates = json.loads(issuer["issuer_dates"])
            event = (
                date.fromisoformat(issuer["first_disclosure_date"])
                if issuer["first_disclosure_date"]
                else None
            )
            for decision in dates:
                if decision <= first or decision > last:
                    counts["outside_observed_reporting_life"] += 1
                    continue
                values, source_facts = index.snapshot(decision)
                if (
                    values["assets"] is None
                    or values["assets"] <= 0
                    or values["balance_age_days"] is None
                    or values["flow_age_days"] is None
                    or values["balance_age_days"] > config["max_balance_age_days"]
                    or values["flow_age_days"] > config["max_flow_age_days"]
                ):
                    counts["missing_or_stale_financials"] += 1
                    continue
                available = max(
                    date.fromisoformat(v["filed"]) + timedelta(days=1)
                    for v in source_facts.values()
                    if v
                )
                feature = dict(
                    company_id=company,
                    decision_date=str(decision),
                    data_kind="empirical",
                    feature_available_on=str(available),
                    **{f: values[f] for f in FEATURES},
                    entity_name=issuer["entity_name"],
                    sic=issuer["sic"],
                    currency="USD",
                    assets=values["assets"],
                    revenue_annual=values["revenue"],
                    operating_cashflow_annual=values["operating_cashflow"],
                    reported_cash=values["cash"],
                    balance_period_end=values["balance_period_end"],
                    flow_period_end=values["flow_period_end"],
                    balance_age_days=values["balance_age_days"],
                    flow_age_days=values["flow_age_days"],
                    known_disclosure=event is not None and event < decision,
                )
                # Keep usable predictors even when the outcome cannot be labeled;
                # later policy scenarios also need unlabeled/post-disclosure rows.
                feature_writer.writerow(feature)
                counts["feature_rows"] += 1
                provenance.write(
                    json.dumps(
                        {
                            "company_id": company,
                            "decision_date": str(decision),
                            "facts": source_facts,
                        }
                    )
                    + "\n"
                )
                label, reason = disclosure_label(
                    decision, event, last, config["horizon_days"], cutoff
                )
                if label is None:
                    counts[reason] += 1
                    continue
                end = decision + timedelta(days=config["horizon_days"])
                # Negative labels wait for the first issuer filing at or after
                # the horizon. Positive labels wait for the full horizon only.
                confirmation = (
                    end
                    if label
                    else date.fromisoformat(
                        issuer_dates[bisect_left(issuer_dates, str(end))]
                    )
                )
                label_available = confirmation + timedelta(days=1)
                if label_available >= cutoff:
                    counts["late_coverage_confirmation"] += 1
                    continue
                event_id = f"{company}:{TARGET}:{event}" if label else ""
                source = f"dataset/submissions/CIK{company}.json and referenced historical files"
                record = dict(
                    company_id=company,
                    decision_date=str(decision),
                    data_kind="empirical",
                    event_type=TARGET,
                    horizon_days=config["horizon_days"],
                    horizon_end=str(end),
                    label_available_on=str(label_available),
                    label=label,
                    event_id=event_id,
                    label_source=(
                        issuer["first_disclosure_accession"] if label else source
                    ),
                    coverage_source=source,
                    feature_available_on=str(available),
                    flow_basis=values["flow_basis"],
                    **{
                        k: feature[k]
                        for k in (
                            "balance_period_end",
                            "flow_period_end",
                            "balance_age_days",
                            "flow_age_days",
                            *FEATURES,
                        )
                    },
                    entity_name=issuer["entity_name"],
                    sic=issuer["sic"],
                )
                panel_writer.writerow(record)
                companies.add(company)
                if event_id:
                    event_ids.add(event_id)
                counts["labeled_rows"] += 1
                counts["positive_rows"] += label
                by_year = year_counts.setdefault(str(decision.year), Counter())
                by_year["rows"] += 1
                by_year["positives"] += label
                missing.update(k for k in FEATURES if values[k] is None)
            if n % 250 == 0:
                print(
                    f"Panel: {n}/{len(issuers)} companies; {counts['labeled_rows']} rows; {counts['positive_rows']} positives",
                    flush=True,
                )
    report = dict(
        data_kind="empirical",
        target=TARGET,
        candidate_companies=len(issuers),
        included_companies=len(companies),
        distinct_positive_events=len(event_ids),
        counts=dict(counts),
        annual_counts={k: dict(v) for k, v in sorted(year_counts.items())},
        missing_predictors=dict(missing),
        limitation="Current SIC screen; first recorded disclosure is not verified bankruptcy onset; negative labels concern reporting only",
    )
    write_json(output / "panel_audit.json", report)
    write_json(output / "design.json", config)
    write_json(
        output / "manifest.json",
        manifest(
            [config_path, inventory_path],
            panel_sha256=file_hash(output / "panel.csv"),
            companyfacts_hash_list_sha256=file_hash(
                output / "companyfacts_hashes.jsonl"
            ),
            **report,
        ),
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inventory", "panel"))
    parser.add_argument("--dataset", type=Path, default=Path("dataset"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cutoff", type=date.fromisoformat, default=date(2026, 9, 7))
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    if args.action == "inventory":
        result = inventory(args.dataset, args.output_dir, args.cutoff)
    else:
        if args.inventory is None or args.config is None:
            parser.error("panel requires --inventory and --config")
        result = panel(args.dataset, args.inventory, args.config, args.output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
