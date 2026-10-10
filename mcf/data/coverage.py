"""Audit missing liabilities for source-recovery opportunities, without imputation.

Run: python -m mcf.data.coverage --panel results/run_004_recurrent_disclosures_initial/panel/panel.csv
     --dataset ../dataset --output results/run_004_liabilities_coverage/liabilities_review.json

These are review candidates, not permission to treat absent equity components as
zero. Input must be company-grouped, as produced by the empirical panel builder.
"""

import argparse
import csv
import json
from collections import Counter
from itertools import groupby, zip_longest
from pathlib import Path

from mcf.common import FEATURES, file_hash, write_csv, write_json
from mcf.data.sec import FORMS


def latest(rows, end, decision):
    eligible = [r for r in rows if r.get("end") == end and not r.get("start")
                and r.get("filed", "9999") < decision
                and r.get("form") in FORMS and r.get("accn")]
    if not eligible:
        return None
    filed = max(r["filed"] for r in eligible)
    eligible = [r for r in eligible if r["filed"] == filed]
    if len({r["val"] for r in eligible}) != 1:
        return None
    return eligible[0]


def audit(panel, dataset, output):
    counts, examples, queue = Counter(), [], {}
    seen = set()
    with Path(panel).open() as stream:
        for company, group in groupby(csv.DictReader(stream), key=lambda r: r["company_id"]):
            if company in seen:
                raise ValueError("Panel must be grouped by company_id")
            seen.add(company)
            rows = [r for r in group if not r["liabilities_to_assets"]]
            if not rows:
                continue
            doc = json.loads((Path(dataset) / "companyfacts" / f"CIK{company}.json").read_text())
            tags = doc.get("facts", {}).get("us-gaap", {})
            units = lambda tag: tags.get(tag, {}).get("units", {}).get("USD", [])
            for row in rows:
                counts["missing_liabilities_rows"] += 1
                end, decision = row["balance_period_end"], row["decision_date"]
                total = latest(units("LiabilitiesAndStockholdersEquity"), end, decision)
                equity = latest(units("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"), end, decision)
                basis = "consolidated_equity"
                if equity is None:
                    equity = latest(units("StockholdersEquity"), end, decision)
                    basis = "parent_equity_requires_noncontrolling_scope_review"
                if total is None or equity is None or total["accn"] != equity["accn"]:
                    counts["no_unambiguous_same_filing_equity_pair"] += 1
                    continue
                counts["same_filing_equity_pair"] += 1
                counts[basis] += 1
                # All units and earlier periods count as warning evidence. Future
                # disclosures must not influence a historical review candidate.
                temporary_evidence = any(
                    r.get("filed", "9999") < decision and r.get("form") in FORMS
                    for tag, data in tags.items()
                    if "TemporaryEquity" in tag or "Redeemable" in tag
                    for facts in data.get("units", {}).values() for r in facts
                )
                counts["known_temporary_or_redeemable_evidence" if temporary_evidence
                       else "no_standard_tag_evidence_of_temporary_equity_not_proof_of_zero"] += 1
                key = (company, end, total["accn"], basis)
                review = queue.setdefault(key, dict(
                    company_id=company, period_end=end, accession=total["accn"],
                    basis=basis, first_decision=decision, affected_rows=0,
                    temporary_or_redeemable_evidence=temporary_evidence,
                    filing_index=f"https://www.sec.gov/Archives/edgar/data/{int(company)}/{total['accn'].replace('-', '')}/{total['accn']}-index.html",
                ))
                review["affected_rows"] += 1
                if len(examples) < 20 and (not examples or examples[-1]["company_id"] != company):
                    examples.append(dict(company_id=company, decision_date=decision,
                                         period_end=end, accession=total["accn"], basis=basis,
                                         residual_before_temporary_equity=total["val"] - equity["val"],
                                         temporary_or_redeemable_evidence=temporary_evidence))
    queue_path = Path(output).with_name(Path(output).stem + "_queue.csv")
    report = dict(counts=dict(counts), examples=examples,
                  review_periods=len(queue), review_queue=str(queue_path),
                  panel_sha256=file_hash(panel),
                  interpretation="Review opportunities only. Parent equity excludes noncontrolling interests; permanent equity excludes temporary equity. No candidate values were inserted into the ML panel.")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    write_csv(queue_path, sorted(queue.values(), key=lambda r: -r["affected_rows"]),
              ("company_id", "period_end", "accession", "basis", "first_decision",
               "affected_rows", "temporary_or_redeemable_evidence", "filing_index"))
    write_json(output, report)
    return report


def compare_panels(before, after):
    """Verify a fill-only extraction change on identical labeled observations."""
    filled, complete, missing_by_label = Counter(), Counter(), Counter()
    count = 0
    with Path(before).open() as a, Path(after).open() as b:
        for old, new in zip_longest(csv.DictReader(a), csv.DictReader(b)):
            if old is None or new is None or any(
                old[k] != new[k] for k in ("company_id", "decision_date", "label", "event_id")
            ):
                raise ValueError("Comparison requires identical ordered rows and labels")
            if new["feature_available_on"] > new["decision_date"]:
                raise ValueError("Feature availability is after the decision date")
            for field in FEATURES:
                if not old[field] and new[field]:
                    filled[field] += 1
                elif old[field] != new[field]:
                    raise ValueError(f"Previously observed feature changed: {field}")
            complete["before"] += all(old[f] for f in FEATURES)
            complete["after"] += all(new[f] for f in FEATURES)
            missing_by_label["rows_label_" + old["label"]] += 1
            missing_by_label["incomplete_label_" + old["label"]] += any(not old[f] for f in FEATURES)
            count += 1
    return dict(rows=count, filled_feature_cells=dict(filled),
                total_filled_cells=sum(filled.values()), changed_existing_cells={},
                complete_rows=dict(complete), baseline_missingness_by_label=dict(missing_by_label),
                labels_and_row_keys_unchanged=True, feature_availability_checked=True,
                before_sha256=file_hash(before), after_sha256=file_hash(after))


def compare_expanded_panels(before, after):
    """Stream a merge comparison when better period coverage adds observations."""
    counts, recovered, lost, revised, complete = (Counter() for _ in range(5))
    key = lambda r: (r["company_id"], r["decision_date"])
    with Path(before).open() as a, Path(after).open() as b:
        old_rows, new_rows = csv.DictReader(a), csv.DictReader(b)
        old, new = next(old_rows, None), next(new_rows, None)
        while old is not None or new is not None:
            if new is None or (old is not None and key(old) < key(new)):
                counts["removed_rows"] += 1
                old = next(old_rows, None)
            elif old is None or key(new) < key(old):
                counts["added_rows"] += 1
                counts["added_positive_rows"] += int(new["label"])
                if new["feature_available_on"] > new["decision_date"]:
                    raise ValueError("Future feature in expanded panel")
                new = next(new_rows, None)
            else:
                counts["shared_rows"] += 1
                if (old["label"], old["event_id"]) != (new["label"], new["event_id"]):
                    raise ValueError("Labels changed for a shared observation")
                if new["feature_available_on"] > new["decision_date"]:
                    raise ValueError("Future feature in expanded panel")
                for field in FEATURES:
                    if not old[field] and new[field]:
                        recovered[field] += 1
                    elif old[field] and not new[field]:
                        lost[field] += 1
                    elif old[field] != new[field]:
                        revised[field] += 1
                complete["before_shared"] += all(old[f] for f in FEATURES)
                complete["after_shared"] += all(new[f] for f in FEATURES)
                old, new = next(old_rows, None), next(new_rows, None)
    return dict(counts=dict(counts), recovered_cells=dict(recovered), lost_cells=dict(lost),
                revised_observed_cells=dict(revised), complete_rows=dict(complete),
                shared_labels_unchanged=True, feature_availability_checked=True,
                before_sha256=file_hash(before), after_sha256=file_hash(after))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-panel", type=Path,
                        help="Optionally verify a rebuilt panel against --panel")
    args = parser.parse_args()
    result = audit(args.panel, args.dataset, args.output)
    if args.compare_panel:
        comparison = compare_panels(args.panel, args.compare_panel)
        write_json(args.output.with_name("comparison.json"), comparison)
    print(json.dumps(result["counts"], indent=2))
