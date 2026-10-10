"""Build point-in-time SEC disclosure targets from the supplied local dataset.

The combined target automatically includes Item 1.03 and evidence-reviewed
2.04 payment failures. A narrower payment-only target and historical
first-disclosure targets remain available for comparison and reproduction.
Filing dates do not establish the contractual date of payment default.

Run from the repository root:
    .venv/bin/python -m mcf.data.empirical [parameters]

Parameters:
    action: Required inventory (screen issuers/find disclosures) or panel (build monthly data).
    --dataset PATH: Local SEC dataset (default: dataset).
    --output-dir PATH: Required destination for the selected action's outputs.
    --cutoff YYYY-MM-DD: Exclusive disclosure cutoff for inventory (default: 2026-09-07);
        panel uses the study config instead.
    --inventory PATH: Inventory output directory; required for panel.
    --config PATH: Study-design JSON; required for panel.
    --statement-facts PATH: Optional per-issuer statement supplement directory for panel.
    --target NAME: Inventory target; defaults to a historical target when omitted.
    --episode-gap-days N: Quiet-gap grouping for payment episodes (default: 90).
    --disclosure-results PATH: Completed review directory or classifications.jsonl;
        inventory only; accepts payment-specific or earlier OpenAI Item 2.04 reviews.
    --item-204-results PATH: Alias for --disclosure-results.
    -h, --help: Show command usage and exit.
"""

import argparse
import csv
import json
from bisect import bisect_left
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from mcf.data.panel import PANEL_FIELDS
from mcf.common import (
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
from mcf.data.sec import filing_items, filing_rows
from mcf.data.point_in_time import FactIndex
from mcf.data.payment_failure import (
    TARGET as PAYMENT_FAILURE_TARGET,
    REVIEW_TARGET,
    BANKRUPTCY_PAYMENT_TARGET,
    RECURRENT_TARGETS,
    payment_disclosures,
    episode_label,
)

PERIODIC = {"10-K", "10-K/A", "10-Q", "10-Q/A"}
ISSUER_FORMS = PERIODIC | {"8-K", "8-K/A"}
ITEM_103_TARGET = "first_sec_item_1_03_disclosure"
PAYMENT_DEFAULT_PROXY_TARGET = "first_sec_payment_default_disclosure_proxy"
TARGET = ITEM_103_TARGET  # Backwards-compatible name for the original study target.
SUPPORTED_TARGETS = {ITEM_103_TARGET, PAYMENT_DEFAULT_PROXY_TARGET, *RECURRENT_TARGETS}


def item_103(value):
    """Match the exact disclosure item across the separators used in SEC files."""
    return "1.03" in filing_items(value)


def item_204(value):
    """Match the exact Item 2.04 token across SEC item separators."""
    return "2.04" in filing_items(value)


def load_item_204_results(path):
    """Load final rule-plus-LLM decisions keyed by CIK and accession number."""
    if path is None:
        return {}, None
    path = Path(path)
    source = path / "classifications.jsonl" if path.is_dir() else path
    if not source.is_file():
        raise ValueError(f"Item 2.04 classifications do not exist: {source}")
    records = {}
    for line_number, line in enumerate(source.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        company = str(row.get("company_id", ""))
        accession = str(row.get("accessionNumber", ""))
        classification = row.get("classification")
        if (
            not company.isdigit()
            or len(company) != 10
            or not accession
            or classification
            not in {"QUALIFIED_DEFAULT", "NON_DEFAULT", "MANUAL_REVIEW"}
        ):
            raise ValueError(f"Invalid Item 2.04 result at line {line_number}")
        key = (company, accession)
        if key in records:
            raise ValueError(f"Duplicate Item 2.04 result: {company} {accession}")
        records[key] = row
    return records, source


def combine_disclosures(company, filings, item_204_results):
    """Combine Item 1.03 with qualified 2.04 and retain unresolved 2.04 dates.

    Missing Item 2.04 results are unresolved rather than assumed negative. A filing
    containing Item 1.03 is already a positive composite event, even if its Item
    2.04 narrative remains unresolved.
    """
    events = {}
    unresolved = []
    stats = Counter()
    for filing in filings:
        if filing["form"] not in {"8-K", "8-K/A"}:
            continue
        accession = filing["accessionNumber"]
        has_103 = item_103(filing["items"])
        has_204 = item_204(filing["items"])
        review = item_204_results.get((company, accession)) if has_204 else None
        classification = review.get("classification") if review else None
        if has_204:
            if review is None:
                stats["item_204_missing_review"] += 1
            else:
                if review.get("filingDate") not in {None, "", filing["filingDate"]}:
                    raise ValueError(
                        f"Item 2.04 filing-date mismatch: {company} {accession}"
                    )
                stats[f"item_204_{classification.lower()}"] += 1
            if not has_103 and classification not in {
                "QUALIFIED_DEFAULT",
                "NON_DEFAULT",
            }:
                unresolved.append(filing)
        if not has_103 and classification != "QUALIFIED_DEFAULT":
            continue
        component = (
            "ITEM_1_03_AND_QUALIFIED_ITEM_2_04"
            if has_103 and classification == "QUALIFIED_DEFAULT"
            else "ITEM_1_03"
            if has_103
            else "QUALIFIED_ITEM_2_04"
        )
        llm_review = (review or {}).get("llm_review", {}).get("review", {})
        events[accession] = dict(
            filing,
            target=PAYMENT_DEFAULT_PROXY_TARGET,
            event_component=component,
            item_204_classification=classification or "",
            item_204_event_type=llm_review.get("event_type", ""),
            item_204_payment_evidence=bool(
                (review or {}).get("payment_default_evidence")
                or llm_review.get("event_type") == "PAYMENT_FAILURE"
            ),
            item_204_review_status=(review or {}).get("llm_status", "rule_only"),
        )
    ordering = lambda row: (row["filingDate"], row["accessionNumber"])
    return sorted(events.values(), key=ordering), sorted(unresolved, key=ordering), stats


def inventory(dataset, output, cutoff, item_204_results_path=None, target=None, episode_gap_days=90):
    """Audit filing histories and record the selected disclosure target."""
    item_204_results, item_204_source = load_item_204_results(
        item_204_results_path
    )
    target = target or (
        PAYMENT_DEFAULT_PROXY_TARGET
        if item_204_results_path is not None
        else ITEM_103_TARGET
    )
    if target not in SUPPORTED_TARGETS:
        raise ValueError("Unsupported disclosure target")
    if target in RECURRENT_TARGETS:
        if type(episode_gap_days) is not int or episode_gap_days < 1:
            raise ValueError("episode_gap_days must be a positive integer")
        if item_204_source is None:
            raise ValueError("Payment-failure target requires completed OpenAI disclosure reviews")
        for row in item_204_results.values():
            saved = row.get("llm_review") or {}
            review_target = (saved.get("settings") or {}).get("target")
            if review_target not in {None, REVIEW_TARGET} or (review_target is None and saved.get("provider") != "openai_batch"):
                raise ValueError("Use completed payment-specific reviews or earlier OpenAI Item 2.04 reviews; rule-only labels cannot be reused")
    output = new_output(output)
    paths = sorted((Path(dataset) / "companyfacts").glob("CIK*.json"))
    rows, events, errors, counts, years = [], [], [], Counter(), Counter()
    item_204_counts = Counter()
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
                if target in RECURRENT_TARGETS:
                    disclosures, unresolved_204, company_204_counts = payment_disclosures(
                        company, dated, item_204_results, episode_gap_days,
                        include_item_103=target == BANKRUPTCY_PAYMENT_TARGET,
                    )
                    item_204_counts.update(company_204_counts)
                elif target == PAYMENT_DEFAULT_PROXY_TARGET:
                    disclosures, unresolved_204, company_204_counts = combine_disclosures(
                        company, dated, item_204_results
                    )
                    item_204_counts.update(company_204_counts)
                else:
                    disclosures = sorted(
                        [
                            dict(
                                f,
                                target=ITEM_103_TARGET,
                                event_component="ITEM_1_03",
                                item_204_classification="",
                                item_204_event_type="",
                                item_204_payment_evidence=False,
                                item_204_review_status="",
                            )
                            for f in dated
                            if f["form"] in {"8-K", "8-K/A"}
                            and item_103(f["items"])
                        ],
                        key=lambda f: (f["filingDate"], f["accessionNumber"]),
                    )
                    unresolved_204 = []
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
                row = {
                    "company_id": company,
                    "entity_name": submissions.get("name", ""),
                    "sic": sic,
                    "sic_description": submissions.get("sicDescription", ""),
                    "current_tickers": ";".join(submissions.get("tickers", [])),
                    "screen": exclusion,
                    "first_periodic": periodic[0] if periodic else "",
                    "last_issuer_filing": issuer[-1] if issuer else "",
                    "periodic_filings": len(periodic),
                    "issuer_dates": json.dumps(issuer),
                    "issuer_filings": len(issuer),
                    "missing_archives": len(missing),
                    "archive_count_mismatches": len(count_mismatches),
                    "first_disclosure_date": (
                        disclosures[0]["filingDate"] if disclosures else ""
                    ),
                    "first_disclosure_accession": (
                        disclosures[0]["accessionNumber"] if disclosures else ""
                    ),
                    "disclosure_records": len(disclosures),
                    "first_unresolved_item_204_date": (
                        unresolved_204[0]["filingDate"] if unresolved_204 else ""
                    ),
                    "first_unresolved_item_204_accession": (
                        unresolved_204[0]["accessionNumber"]
                        if unresolved_204
                        else ""
                    ),
                    "unresolved_item_204_records": len(unresolved_204),
                }
                rows.append(row)
                if target in RECURRENT_TARGETS:
                    row.update(
                        payment_failure_disclosures=json.dumps(disclosures),
                        unresolved_payment_disclosures=json.dumps(unresolved_204),
                    )
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
                errors.append({"company_id": company, "error": str(exc)})
            if n % 1000 == 0:
                print(f"Inventory: {n}/{len(paths)} companies", flush=True)
    write_csv(output / "issuer_inventory.csv", rows, fields=None if rows else (
        "company_id", "entity_name", "screen",
    ))
    write_csv(output / "disclosure_events.csv", events, fields=None if events else (
        "company_id", "accessionNumber", "filingDate", "target", "event_component",
        "episode_id", "episode_start", "is_episode_start",
    ))
    report = {
        "companyfacts_files": len(paths),
        "inventoried_companies": len(rows),
        "screen_counts": dict(counts),
        "disclosure_records": len(events),
        "target": target,
        "episode_gap_days": episode_gap_days if target in RECURRENT_TARGETS else None,
        "item_204_results": str(item_204_source) if item_204_source else None,
        "item_204_counts": dict(item_204_counts),
        "candidate_first_disclosures_by_year": dict(sorted(years.items())),
        "candidate_payment_episodes_by_year": dict(sorted(Counter(
            e["filingDate"][:4] for e in events
            if e["screen"] == "candidate" and e.get("is_episode_start")
        ).items())) if target in RECURRENT_TARGETS else None,
        "cutoff": str(cutoff),
        "errors": errors,
        "target_note": (
            "Recurrent bankruptcy/receivership (all 1.03) or explicit 2.04 payment-failure disclosures; "
            "quiet-gap grouping is operational, and the target does not establish contractual nonpayment. "
            if target == BANKRUPTCY_PAYMENT_TARGET else
            "Recurrent disclosed payment-failure episodes from explicit payment evidence in 1.03/2.04; "
            "earlier OpenAI 2.04 PAYMENT_FAILURE/BENIGN reviews may be reused; other legacy distress stays unresolved; "
            "quiet-gap grouping is not contractual cure and filing date is not default onset"
            if target in RECURRENT_TARGETS else
            "First Item 1.03 or conservatively qualified Item 2.04 filing; a "
            "payment-default disclosure proxy, not a verified contractual default date"
            if target == PAYMENT_DEFAULT_PROXY_TARGET
            else "Observed Item 1.03 disclosure dates only; includes receivership "
            "and reorganization disclosures, not verified default dates"
        ),
    }
    write_json(output / "inventory_audit.json", report)
    write_json(
        output / "manifest.json",
        manifest(
            [item_204_source] if item_204_source else [],
            data_kind="empirical",
            **report,
            source_hash_list_sha256=file_hash(output / "source_hashes.jsonl"),
        ),
    )
    if target in RECURRENT_TARGETS and errors:
        raise ValueError("Payment-failure inventory has errors; inspect inventory_audit.json before proceeding")
    return report


def disclosure_label(
    decision,
    event_date,
    last_issuer_date,
    horizon_days,
    cutoff,
    unresolved_date=None,
):
    """Observed reporting event; right-censor negative windows after issuer follow-up.

    Event labels are retained once the disclosure itself is observed, even if the
    issuer stops reporting after it. Negative windows need an issuer filing at or
    after their horizon. Both wait until the full horizon has elapsed before use.
    """
    horizon = decision + timedelta(days=horizon_days)
    first_known_or_unresolved = min(
        (value for value in (event_date, unresolved_date) if value is not None),
        default=None,
    )
    if first_known_or_unresolved is not None and first_known_or_unresolved <= decision:
        if unresolved_date is not None and unresolved_date == first_known_or_unresolved:
            return None, "post_unresolved_item_204"
        return None, "post_first_disclosure"
    if horizon + timedelta(days=1) >= cutoff:
        return None, "cutoff_censoring"
    if event_date is not None and event_date <= horizon and (
        unresolved_date is None or event_date <= unresolved_date
    ):
        return 1, "observed_disclosure"
    if unresolved_date is not None and unresolved_date <= horizon:
        return None, "unresolved_item_204_in_window"
    if last_issuer_date < horizon:
        return None, "issuer_followup_censoring"
    return 0, "no_recorded_disclosure_in_observed_window"


def panel(dataset, inventory_dir, config_path, output, statement_facts=None):
    """Write monthly predictors, disclosure labels, source provenance and exclusions."""
    config = load_design(config_path)
    if statement_facts is not None and not Path(statement_facts).is_dir():
        raise ValueError(f"Statement-fact directory does not exist: {statement_facts}")
    target = config["event_type"]
    if config["data_kind"] != "empirical" or target not in SUPPORTED_TARGETS:
        raise ValueError("Unsupported empirical SEC disclosure target")
    output = new_output(output)
    dates = list(
        months(date.fromisoformat(config["start"]), date.fromisoformat(config["end"]))
    )
    cutoff = date.fromisoformat(config["observed_as_of"])
    inventory_path = Path(inventory_dir) / "issuer_inventory.csv"
    inventory_audit_path = Path(inventory_dir) / "inventory_audit.json"
    inventory_audit = json.loads(inventory_audit_path.read_text())
    inventory_target = inventory_audit.get("target", ITEM_103_TARGET)
    if inventory_target != target:
        raise ValueError(
            f"Inventory target {inventory_target!r} does not match design {target!r}"
        )
    payment_target = target in RECURRENT_TARGETS
    if payment_target and inventory_audit.get("errors"):
        raise ValueError("Resolve payment-failure inventory errors before building the panel")
    if payment_target and (config["horizon_days"] != 60 or config.get("episode_gap_days") != inventory_audit.get("episode_gap_days")):
        raise ValueError("Payment-failure design requires a 60-day horizon and the inventory's episode gap")
    if payment_target:
        gap_days = config["episode_gap_days"]
    issuers = [r for r in read_csv(inventory_path) if r["screen"] == "candidate"]
    counts, companies, event_ids, year_counts, missing = (
        Counter(),
        set(),
        set(),
        {},
        Counter(),
    )
    financial_exclusions = Counter()
    derivations = Counter()
    supplement_hashes = []
    feature_fields = (
        "company_id",
        "decision_date",
        "data_kind",
        "event_type",
        "horizon_days",
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
        panel_writer, feature_writer = (
            csv.DictWriter(panel_stream, fieldnames=panel_fields),
            csv.DictWriter(feature_stream, fieldnames=feature_fields),
        )
        panel_writer.writeheader()
        feature_writer.writeheader()
        for n, issuer in enumerate(issuers, 1):
            company = issuer["company_id"]
            path = Path(dataset) / "companyfacts" / f"CIK{company}.json"
            document = json.loads(path.read_text())
            if statement_facts is not None:
                from mcf.data.statement_facts import attach

                supplement = attach(document, statement_facts)
                if supplement:
                    supplement_hashes.append(supplement)
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
            unresolved = (
                date.fromisoformat(issuer.get("first_unresolved_item_204_date", ""))
                if issuer.get("first_unresolved_item_204_date", "")
                else None
            )
            payment_events = json.loads(issuer["payment_failure_disclosures"]) if payment_target else []
            payment_unknown = json.loads(issuer["unresolved_payment_disclosures"]) if payment_target else []
            for decision in dates:
                if decision <= first or decision > last:
                    counts["outside_observed_reporting_life"] += 1
                    continue
                values, source_facts = index.snapshot(decision)
                reasons = []
                if values["assets"] is None:
                    reasons.append("missing_or_conflicting_assets")
                elif values["assets"] <= 0:
                    reasons.append("nonpositive_assets")
                if values["balance_age_days"] is not None and values["balance_age_days"] > config["max_balance_age_days"]:
                    reasons.append("stale_balance")
                if values["flow_age_days"] is None:
                    reasons.append("missing_or_conflicting_annual_operating_cashflow")
                elif values["flow_age_days"] > config["max_flow_age_days"]:
                    reasons.append("stale_annual_operating_cashflow")
                if reasons:
                    counts["missing_or_stale_financials"] += 1
                    financial_exclusions.update(reasons)
                    continue
                for field in ("cash", "liabilities", "net_income"):
                    source = source_facts.get(field + "_derivation")
                    derivations[f"{field}:{source['basis'] if source else 'missing'}"] += 1
                for field in ("assets", "liabilities", "current_assets", "current_liabilities", "cash"):
                    fact = source_facts.get(field)
                    if fact and fact.get("source"):
                        derivations[f"statement:{field}:{fact['source']['basis']}"] += 1
                if source_facts.get("assets", {}).get("tag") == "LiabilitiesAndStockholdersEquity":
                    derivations["assets:balance_sheet_identity"] += 1
                available = max(
                    date.fromisoformat(v["filed"]) + timedelta(days=1)
                    for v in source_facts.values()
                    if v
                )
                feature = dict(
                    company_id=company,
                    decision_date=str(decision),
                    data_kind="empirical",
                    event_type=target,
                    horizon_days=config["horizon_days"],
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
                    known_disclosure=(
                        any(0 <= (decision - date.fromisoformat(e["filingDate"])).days <= gap_days for e in payment_events if e["filingDate"] <= str(decision))
                        if payment_target else event is not None and event < decision
                    ),
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
                payment_event = None
                if payment_target:
                    label, reason, payment_event = episode_label(
                        decision, payment_events, payment_unknown, last, cutoff, gap_days
                    )
                else:
                    label, reason = disclosure_label(
                        decision, event, last, config["horizon_days"], cutoff, unresolved,
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
                event_id = (
                    payment_event["episode_id"] if payment_target and label
                    else f"{company}:{target}:{event}" if label else ""
                )
                source = f"dataset/submissions/CIK{company}.json and referenced historical files"
                record = dict(
                    company_id=company,
                    decision_date=str(decision),
                    data_kind="empirical",
                    event_type=target,
                    horizon_days=config["horizon_days"],
                    horizon_end=str(end),
                    label_available_on=str(label_available),
                    label=label,
                    event_id=event_id,
                    label_source=(
                        payment_event["accessionNumber"] if payment_target and label
                        else issuer["first_disclosure_accession"] if label else source
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
        target=target,
        candidate_companies=len(issuers),
        included_companies=len(companies),
        distinct_positive_events=len(event_ids),
        counts=dict(counts),
        annual_counts={k: dict(v) for k, v in sorted(year_counts.items())},
        missing_predictors=dict(missing),
        financial_exclusion_reasons=dict(financial_exclusions),
        financial_exclusion_note="Reasons overlap; a company-month can fail multiple checks.",
        feature_row_derivations=dict(derivations),
        item_204_results=inventory_audit.get("item_204_results"),
        item_204_resolved_reviews=sum(
            inventory_audit.get("item_204_counts", {}).get(name, 0)
            for name in (
                "qualified_default", "non_default",
                "item_204_qualified_default", "item_204_non_default",
            )
        ),
        statement_facts_directory=(
            str(Path(statement_facts).resolve()) if statement_facts is not None else None
        ),
        statement_supplement_companies=len(supplement_hashes),
        limitation=(
            "Bankruptcy/receivership or payment-failure disclosure episodes; 1.03 qualifies without payment review. "
            "Filing dates and episode gaps are operational, not verified failure/cure. Unresolved 2.04 censors labels. "
            if target == BANKRUPTCY_PAYMENT_TARGET else
            "Disclosed payment-failure episodes, not all actual defaults. Filing dates define disclosure timing. "
            "Episode gaps are operational, not verified cure. Unresolved 1.03/2.04 evidence censors later rows; "
            "negative labels require reporting follow-up, not verified absence of contractual default."
            if payment_target else
            "Current SIC screen; the composite is a payment-default disclosure "
            "proxy rather than verified contractual default. Unresolved Item 2.04 "
            "filings censor affected windows; negative labels concern reporting only."
            if target == PAYMENT_DEFAULT_PROXY_TARGET
            else "Current SIC screen; first recorded disclosure is not verified "
            "bankruptcy onset; negative labels concern reporting only"
        ),
    )
    write_json(output / "panel_audit.json", report)
    write_json(output / "design.json", config)
    write_json(output / "statement_facts_hashes.json", supplement_hashes)
    write_json(
        output / "manifest.json",
        manifest(
            [config_path, inventory_path, inventory_audit_path],
            panel_sha256=file_hash(output / "panel.csv"),
            companyfacts_hash_list_sha256=file_hash(
                output / "companyfacts_hashes.jsonl"
            ),
            statement_facts_hash_list_sha256=file_hash(output / "statement_facts_hashes.json"),
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
    parser.add_argument("--statement-facts", type=Path,
                        help="Optional directory of per-issuer audited statement supplements")
    parser.add_argument("--target", choices=sorted(SUPPORTED_TARGETS), help="Inventory target; default derives from supplied reviews")
    parser.add_argument("--episode-gap-days", type=int, default=90, help="Quiet-gap grouping for recurrent payment disclosures (default: 90)")
    parser.add_argument(
        "--disclosure-results", "--item-204-results", dest="item_204_results",
        type=Path,
        help=(
            "Completed disclosure-review directory or classifications.jsonl"
        ),
    )
    args = parser.parse_args()
    if args.action == "inventory":
        result = inventory(
            args.dataset,
            args.output_dir,
            args.cutoff,
            args.item_204_results,
            target=args.target,
            episode_gap_days=args.episode_gap_days,
        )
    else:
        if args.inventory is None or args.config is None:
            parser.error("panel requires --inventory and --config")
        if args.item_204_results is not None:
            parser.error("--item-204-results applies only to inventory")
        result = panel(args.dataset, args.inventory, args.config, args.output_dir, args.statement_facts)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
