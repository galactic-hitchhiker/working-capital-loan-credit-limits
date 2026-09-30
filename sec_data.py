"""Conservative, offline point-in-time pilot over the downloaded SEC JSON files.

This is NOT a completed modeling panel. It uses annual flows, not reconstructed
TTM flows, and does not infer a default target, cash eligibility, debt service,
facility utilization, or historical listing status. USD/us-gaap/10-K/10-Q only.
Filing-day values become usable on the following calendar day. Provenance is
retained so a filing can be checked before a thesis result is accepted.
"""

import argparse
import csv
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

TAGS = {
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "current_assets": ("AssetsCurrent",),
    "current_liabilities": ("LiabilitiesCurrent",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "operating_cashflow": ("NetCashProvidedByUsedInOperatingActivities",),
    "net_income": ("NetIncomeLoss",),
}
# These concepts are used only to reconstruct cash and cash equivalents when the
# directly reported total is absent. Keeping them separate from TAGS prevents
# intermediate accounting values from becoming model predictors by accident.
CASH_COMPONENT_TAGS = {
    "cash_only": ("Cash",),
    "cash_equivalents_only": ("CashEquivalentsAtCarryingValue",),
    "cash_including_restricted": (
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    "restricted_cash_and_equivalents": ("RestrictedCashAndCashEquivalents",),
    "restricted_cash": ("RestrictedCash",),
    "restricted_cash_current": ("RestrictedCashCurrent",),
    "restricted_cash_noncurrent": ("RestrictedCashNoncurrent",),
}
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A"}


@dataclass(frozen=True)
class Fact:
    value: float
    tag: str
    start: str | None
    end: str
    filed: str
    accession: str


def eligible_facts(document, field: str, as_of: date):
    """Never use a fiscal-year label or a frame as an availability date."""
    tags = TAGS.get(field, CASH_COMPONENT_TAGS.get(field))
    if tags is None:
        raise KeyError(field)
    for tag in tags:
        for r in (
            document.get("facts", {})
            .get("us-gaap", {})
            .get(tag, {})
            .get("units", {})
            .get("USD", [])
        ):
            try:
                filed, end = (
                    date.fromisoformat(r["filed"]),
                    date.fromisoformat(r["end"]),
                )
                value = float(r["val"])
                if isinstance(r["val"], bool) or not math.isfinite(value):
                    continue
                if (
                    filed >= as_of
                    or end > filed
                    or r.get("form") not in FORMS
                    or not r.get("accn")
                ):
                    continue
                start = r.get("start")
                if start and date.fromisoformat(start) > end:
                    continue
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
            yield Fact(value, tag, start, r["end"], r["filed"], r["accn"])


def latest_fact(document, field, as_of, *, annual=False, start=None, end=None):
    """Resolve a period-matched fact using only filings available before as_of."""
    rows = list(eligible_facts(document, field, as_of))
    if annual:
        rows = [
            r
            for r in rows
            if r.start
            and 330
            <= (date.fromisoformat(r.end) - date.fromisoformat(r.start)).days + 1
            <= 400
        ]
    else:
        rows = [r for r in rows if r.start is None]
    if start is not None:
        rows = [r for r in rows if r.start == start]
    if end is not None:
        rows = [r for r in rows if r.end == end]
    if not rows:
        return None
    # Prefer the latest reporting period, then the latest known filing vintage.
    latest_end = max(r.end for r in rows)
    rows = [r for r in rows if r.end == latest_end]
    latest_filed = max(r.filed for r in rows)
    rows = [r for r in rows if r.filed == latest_filed]
    # Conflicting USD totals for one period are flagged missing rather than chosen.
    if len({(r.start, r.value) for r in rows}) != 1:
        return None
    tags = TAGS.get(field, CASH_COMPONENT_TAGS.get(field))
    return min(rows, key=lambda r: (tags.index(r.tag), r.accession))


def prior_year_fact(document, field, as_of, current_end):
    """Find the closest comparable instant fact 330–400 days earlier."""
    current = date.fromisoformat(current_end)
    ends = sorted(
        {
            fact.end
            for fact in eligible_facts(document, field, as_of)
            if fact.start is None
            and 330 <= (current - date.fromisoformat(fact.end)).days <= 400
        },
        reverse=True,
    )
    for end in ends:
        fact = latest_fact(document, field, as_of, end=end)
        if fact:
            return fact
    return None


def resolve_cash_and_equivalents(get_fact, end):
    """Return a consistently defined cash total and auditable derivation details.

    Components must come from the same filing accession. This avoids combining
    values from different amendments or filing vintages for the same period.
    """
    direct = get_fact("cash", end=end)
    if direct:
        return direct.value, "direct", {"cash": direct}

    cash = get_fact("cash_only", end=end)
    equivalents = get_fact("cash_equivalents_only", end=end)
    if cash and equivalents and cash.accession == equivalents.accession:
        return (
            cash.value + equivalents.value,
            "cash_plus_equivalents",
            {"cash_only": cash, "cash_equivalents_only": equivalents},
        )

    combined = get_fact("cash_including_restricted", end=end)
    if not combined:
        return None, "missing", {}

    restricted_candidates = [
        ("restricted_cash_and_equivalents",),
        ("restricted_cash",),
        ("restricted_cash_current", "restricted_cash_noncurrent"),
    ]
    for fields in restricted_candidates:
        restricted = [get_fact(field, end=end) for field in fields]
        if not all(restricted) or any(
            fact.accession != combined.accession for fact in restricted
        ):
            continue
        unrestricted = combined.value - sum(fact.value for fact in restricted)
        if unrestricted < 0:
            continue
        sources = {"cash_including_restricted": combined}
        sources.update(zip(fields, restricted))
        return unrestricted, "combined_minus_restricted", sources
    return None, "missing", {}


def ratio(numerator, denominator):
    """Leave a ratio missing when inputs are absent or its denominator is nonpositive."""
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def snapshot(document, as_of: date):
    """Extract annual-flow and balance-sheet predictors with auditable source facts."""
    balance = latest_fact(document, "assets", as_of)
    annual = latest_fact(document, "operating_cashflow", as_of, annual=True)
    facts = {"assets": balance, "operating_cashflow": annual}
    for field in ("liabilities", "current_assets", "current_liabilities"):
        facts[field] = (
            latest_fact(document, field, as_of, end=balance.end) if balance else None
        )
    cash_value, cash_basis, cash_sources = (
        resolve_cash_and_equivalents(
            lambda field, **kwargs: latest_fact(document, field, as_of, **kwargs),
            balance.end,
        )
        if balance
        else (None, "missing", {})
    )
    # Keep the narrower Cash concept separate from reconstructed cash and cash
    # equivalents so a study can choose one accounting definition explicitly.
    facts["cash_only"] = (
        latest_fact(document, "cash_only", as_of, end=balance.end)
        if balance
        else None
    )
    facts["cash"] = cash_sources.get("cash")
    prior_assets = (
        prior_year_fact(document, "assets", as_of, balance.end) if balance else None
    )
    prior_liabilities = (
        latest_fact(document, "liabilities", as_of, end=prior_assets.end)
        if prior_assets
        else None
    )
    for field in ("revenue", "net_income"):
        facts[field] = (
            latest_fact(
                document, field, as_of, annual=True, start=annual.start, end=annual.end
            )
            if annual
            else None
        )
    values = {key: fact.value if fact else None for key, fact in facts.items()}
    values["cash"] = cash_value
    # Flow-to-assets ratios need period-matched assets, not a newer balance
    # sheet. Require exactly the day before the annual period began.
    from datetime import timedelta

    opening = closing = opening_liabilities = closing_liabilities = None
    if annual:
        opening_end = (date.fromisoformat(annual.start) - timedelta(days=1)).isoformat()
        opening = latest_fact(document, "assets", as_of, end=opening_end)
        closing = latest_fact(document, "assets", as_of, end=annual.end)
        opening_liabilities = latest_fact(
            document, "liabilities", as_of, end=opening_end
        )
        closing_liabilities = latest_fact(
            document, "liabilities", as_of, end=annual.end
        )
    average_assets = (
        (opening.value + closing.value) / 2 if opening and closing else None
    )
    average_liabilities = (
        (opening_liabilities.value + closing_liabilities.value) / 2
        if opening_liabilities and closing_liabilities
        else None
    )
    current_assets, current_liabilities, assets = (
        values["current_assets"],
        values["current_liabilities"],
        values["assets"],
    )
    current_leverage = ratio(values["liabilities"], assets)
    prior_leverage = ratio(
        prior_liabilities.value if prior_liabilities else None,
        prior_assets.value if prior_assets else None,
    )
    result = {
        "cik": str(document.get("cik", "")).zfill(10),
        "entity_name": document.get("entityName", ""),
        "as_of": as_of.isoformat(),
        "currency": "USD",
        "flow_basis": "last_reported_annual_not_TTM",
        "balance_period_end": balance.end if balance else None,
        "balance_age_days": (
            (as_of - date.fromisoformat(balance.end)).days if balance else None
        ),
        "flow_period_start": annual.start if annual else None,
        "flow_period_end": annual.end if annual else None,
        "flow_age_days": (
            (as_of - date.fromisoformat(annual.end)).days if annual else None
        ),
        **values,
        "current_ratio": ratio(current_assets, current_liabilities),
        "cash_only_to_assets": ratio(values["cash_only"], assets),
        "cash_and_equivalents_to_assets": ratio(values["cash"], assets),
        "liabilities_to_assets": current_leverage,
        "assets_growth_12m": ratio(
            assets - prior_assets.value if assets is not None and prior_assets else None,
            prior_assets.value if prior_assets else None,
        ),
        "liabilities_to_assets_change_12m": (
            current_leverage - prior_leverage
            if current_leverage is not None and prior_leverage is not None
            else None
        ),
        "working_capital_to_assets": ratio(
            (
                current_assets - current_liabilities
                if current_assets is not None and current_liabilities is not None
                else None
            ),
            assets,
        ),
        "return_on_average_assets": ratio(values["net_income"], average_assets),
        "operating_cashflow_to_average_assets": ratio(
            values["operating_cashflow"], average_assets
        ),
        "operating_cashflow_to_average_liabilities": ratio(
            values["operating_cashflow"], average_liabilities
        ),
        "negative_net_income": (
            int(values["net_income"] < 0) if values["net_income"] is not None else None
        ),
        "negative_operating_cashflow": (
            int(values["operating_cashflow"] < 0)
            if values["operating_cashflow"] is not None
            else None
        ),
        "log_assets": math.log(assets) if assets is not None and assets > 0 else None,
        "status": "financial_snapshot_only_no_event_label_or_credit_recommendation",
    }
    provenance = {key: asdict(fact) if fact else None for key, fact in facts.items()}
    provenance["cash_derivation"] = (
        {
            "basis": cash_basis,
            # Panel builders use top-level provenance filing dates to determine
            # when a feature first became available.
            "filed": max(fact.filed for fact in cash_sources.values()),
            "sources": {key: asdict(fact) for key, fact in cash_sources.items()},
        }
        if cash_sources
        else None
    )
    provenance["opening_assets_for_profitability"] = (
        asdict(opening) if opening else None
    )
    provenance["closing_assets_for_profitability"] = (
        asdict(closing) if closing else None
    )
    provenance["opening_liabilities_for_cashflow_coverage"] = (
        asdict(opening_liabilities) if opening_liabilities else None
    )
    provenance["closing_liabilities_for_cashflow_coverage"] = (
        asdict(closing_liabilities) if closing_liabilities else None
    )
    provenance["prior_assets_for_12m_change"] = (
        asdict(prior_assets) if prior_assets else None
    )
    provenance["prior_liabilities_for_12m_change"] = (
        asdict(prior_liabilities) if prior_liabilities else None
    )
    return result, provenance


def filing_rows(submissions, directory: Path):
    """Read main history plus every historical file referenced by that main file."""
    blocks = [submissions.get("filings", {}).get("recent", {})]
    missing = []
    for metadata in submissions.get("filings", {}).get("files", []):
        name = metadata.get("name", "")
        if Path(name).name != name or not name:
            raise ValueError("Unsafe historical submission filename")
        path = directory / name
        if path.exists():
            blocks.append(json.loads(path.read_text()))
        else:
            missing.append(name)
    rows, seen = [], set()
    for block in blocks:
        for i, accession in enumerate(block.get("accessionNumber", [])):
            if accession in seen:
                continue
            seen.add(accession)
            rows.append(
                {
                    key: block.get(key, [])[i] if i < len(block.get(key, [])) else ""
                    for key in (
                        "accessionNumber",
                        "filingDate",
                        "reportDate",
                        "form",
                        "items",
                        "primaryDocument",
                    )
                }
            )
    return rows, missing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("dataset"))
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--output-dir", type=Path, default=Path("results/sec_audit"))
    args = parser.parse_args()
    if args.sample_size < 1:
        parser.error("sample-size must be positive")
    files = sorted((args.dataset / "companyfacts").glob("CIK*.json"))
    if not files:
        parser.error("No companyfacts JSON files found")
    n = min(args.sample_size, len(files))
    # Spread the pilot across the sorted inventory; not a representative sample.
    chosen = (
        [files[i * (len(files) - 1) // (n - 1)] for i in range(n)]
        if n > 1
        else files[:1]
    )
    rows, provenance, events, errors = [], [], [], []
    counts = Counter()
    for path in chosen:
        try:
            d = json.loads(path.read_text())
            row, prov = snapshot(d, args.as_of)
            sub_path = args.dataset / "submissions" / path.name
            sub = json.loads(sub_path.read_text()) if sub_path.exists() else {}
            counts["matching_submissions"] += bool(sub)
            sic = str(sub.get("sic", ""))
            # Excluding all finance/insurance/real estate SICs is a conservative
            # pilot screen, not the final historical non-financial universe.
            row["current_sic"] = sic
            row["pilot_sector_screen"] = (
                "excluded_finance_real_estate"
                if sic.isdigit() and 6000 <= int(sic) <= 6999
                else "candidate_nonfinancial" if sic.isdigit() else "unknown"
            )
            row["current_tickers"] = ";".join(sub.get("tickers", []))
            for field in TAGS:
                counts[f"available_{field}"] += row[field] is not None
            rows.append(row)
            provenance.append({"file": path.name, "as_of": row["as_of"], "facts": prov})
            filings, missing = filing_rows(sub, args.dataset / "submissions")
            counts["missing_history_files"] += len(missing)
            for f in filings:
                if (
                    f["form"] not in {"8-K", "8-K/A"}
                    or f["filingDate"] >= args.as_of.isoformat()
                ):
                    continue
                items = str(f["items"]).replace(";", ",").replace(" ", ",").split(",")
                if "1.03" in items:
                    accession_without_dashes = f["accessionNumber"].replace("-", "")
                    events.append(
                        {
                            "cik": row["cik"],
                            **f,
                            "source_url": f"https://www.sec.gov/Archives/edgar/data/{int(row['cik'])}/{accession_without_dashes}/{f['primaryDocument']}",
                            "verified_event_date": "",
                            "verified": False,
                            "status": "item_1_03_candidate_only_manual_review_required",
                        }
                    )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append({"file": path.name, "error": str(exc)})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if rows:
        with (args.output_dir / "financial_snapshots.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    event_fields = [
        "cik",
        "accessionNumber",
        "filingDate",
        "reportDate",
        "form",
        "items",
        "primaryDocument",
        "source_url",
        "verified_event_date",
        "verified",
        "status",
    ]
    with (args.output_dir / "event_candidates.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=event_fields)
        w.writeheader()
        w.writerows(events)
    (args.output_dir / "fact_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    report = {
        "companyfacts_inventory": len(files),
        "sample_size_requested": args.sample_size,
        "sample_files_attempted": n,
        "snapshot_rows": len(rows),
        "as_of": str(args.as_of),
        "sampling": "evenly_spaced_sorted_CIK_pilot_not_representative",
        "coverage_counts": dict(counts),
        "event_candidates": len(events),
        "errors": errors,
        "warnings": [
            "No verified outcome labels; absence of an 8-K item is not a negative label.",
            "Annual flow pilot, not a TTM/monthly modeling dataset.",
            "Cash is an accounting proxy, not verified available/eligible cash.",
            "No debt-service schedule, target-facility exposure, PD, LGD or utilization inferred.",
            "SIC/tickers are current metadata, not historical listing evidence.",
            "Missing/conflicting standard tags remain missing; no custom-tag reconciliation.",
            "No genuine credit limits or model performance calculated from these snapshots.",
        ],
    }
    (args.output_dir / "audit_summary.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
