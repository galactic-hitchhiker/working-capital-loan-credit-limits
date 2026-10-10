"""Recover balance-sheet facts from SEC Financial Statement and Notes ZIPs.

Uses SUB/PRE/NUM/TAG/CAL, consolidated USD instant facts, exact filing-period
anchors in Company Facts, and complete calculation groups. Original source files
are never modified. Output is an optional supplement for mcf.data.empirical.

python -m mcf.data.statement_facts --archives ARCHIVE.zip ... --dataset ../dataset
    --inventory results/run_005_recurrent_disclosures_retrained/inventory/issuer_inventory.csv --output-dir OUTPUT
"""

import argparse
import csv
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from mcf.common import file_hash, new_output, read_csv, write_json
from mcf.data.sec import FORMS, TAGS

FIELDS = {f: TAGS[f][0] for f in (
    "assets", "liabilities", "liabilities_noncurrent", "current_assets",
    "current_liabilities", "cash",
)}
LABELS = {
    "assets": {"assets", "total assets"},
    "liabilities": {"liabilities", "total liabilities"},
    "liabilities_noncurrent": {"noncurrent liabilities", "total noncurrent liabilities"},
    "current_assets": {"current assets", "total current assets"},
    "current_liabilities": {"current liabilities", "total current liabilities"},
    "cash": {"cash and cash equivalents"},
}
EQUITY_TAGS = {
    "StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "MinorityInterest", "PartnersCapital", "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest",
    "LimitedLiabilityCompanyMembersEquity", "MembersEquity",
    "TemporaryEquityCarryingAmountAttributableToParent",
    "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests",
    "RedeemableNoncontrollingInterestEquityCarryingAmount",
}
LIABILITY_TAGS = {
    "Liabilities", "LiabilitiesCurrent", "LiabilitiesNoncurrent",
    "LongTermDebt", "LongTermDebtCurrent", "LongTermDebtNoncurrent",
    "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
    "LongTermDebtAndFinanceLeaseObligationsCurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    "ShortTermBorrowings", "DeferredRevenueNoncurrent", "DeferredRevenueCurrent",
    "OtherLiabilitiesNoncurrent", "OtherLiabilitiesCurrent", "OtherLiabilities",
    "LiabilitiesOtherThanLongtermDebtNoncurrent", "DeferredIncomeTaxLiabilitiesNet",
    "DeferredTaxLiabilitiesNoncurrent", "DeferredIncomeTaxLiabilitiesNetNoncurrent",
    "OperatingLeaseLiabilityNoncurrent", "FinanceLeaseLiabilityNoncurrent",
    "CapitalLeaseObligationsNoncurrent", "PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent",
    "PensionAndOtherPostretirementAndPostemploymentBenefitPlansLiabilitiesNoncurrent",
    "ContractWithCustomerLiabilityNoncurrent", "AssetRetirementObligation",
    "AccruedIncomeTaxesNoncurrent", "DefinedBenefitPensionPlanLiabilitiesNoncurrent",
    "OtherPostretirementDefinedBenefitPlanLiabilitiesNoncurrent", "AssetRetirementObligationsNoncurrent",
    "SelfInsuranceReserveNoncurrent",
}


def normalized(label):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", label.lower())).strip()


def rows(archive, name):
    csv.field_size_limit(16 * 1024 * 1024)
    with archive.open(name) as stream:
        # SEC TSV fields contain literal quotation marks, not CSV quote escapes.
        yield from csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"),
                                  delimiter="\t", quoting=csv.QUOTE_NONE)


def standard(node, tag):
    return node[0] == tag and node[1].startswith("us-gaap/")


def one_value(records):
    """Reject conflicting contexts instead of selecting a convenient iprx value."""
    if not records or len({r["value"] for r in records}) != 1:
        return None
    return records[0]


def complete_sum(arcs, facts):
    """Require every explicit child, with no duplicated or conflicting weights."""
    weights = {}
    for child, weight in arcs:
        if child in weights and weights[child] != weight:
            return None
        weights[child] = weight
    components = []
    for child, weight in weights.items():
        fact = one_value(facts.get(child, []))
        if fact is None:
            return None
        components.append(dict(tag=child[0], version=child[1], weight=weight, **fact))
    if not components:
        return None
    return sum(c["weight"] * c["value"] for c in components), components


def recover_period(facts, groups, labels, metadata):
    """Return independently supported candidates; caller rejects disagreement."""
    candidates = defaultdict(list)
    for node, records in facts.items():
        fact = one_value(records)
        if fact is None or fact["value"] < 0:
            continue
        for field, tag in FIELDS.items():
            basis = None
            if standard(node, tag):
                basis = "statement_standard_total"
            elif metadata.get(node, {}).get("custom") == "1":
                # Both the taxonomy label and face-statement label must describe
                # the exact total. Substring matching would confuse components.
                if (normalized(metadata[node].get("tlabel", "")) in LABELS[field]
                        and any(normalized(l) in LABELS[field] for l in labels.get(node, []))):
                    basis = "statement_custom_total"
            if basis:
                candidates[field].append((fact["value"], basis,
                                          [dict(tag=node[0], version=node[1], **fact)]))
    for (group, parent), arcs in groups.items():
        observed = one_value(facts.get(parent, []))
        omitted_disclosures = []
        if standard(parent, "LiabilitiesAndStockholdersEquity") and observed:
            # Some filers place the non-amount commitments disclosure in CAL.
            # It can be omitted only if the remaining explicit amounts reconcile
            # to the reported parent (checked below); never use this for a
            # missing parent or for a missing monetary liability/equity component.
            omitted_disclosures = [child for child, _ in arcs
                                   if standard(child, "CommitmentsAndContingencies")
                                   and child not in facts]
            arcs = [(child, weight) for child, weight in arcs if child not in omitted_disclosures]
        total = complete_sum(arcs, facts)
        if total is None:
            continue
        value, components = total
        tolerance = sum(c["rounding"] for c in components)
        if observed and abs(observed["value"] - value) > tolerance + observed["rounding"] + 1e-6:
            continue
        for field, tag in FIELDS.items():
            if standard(parent, tag) and value >= 0:
                candidates[field].append((value, "complete_calculation_children", components))
        if not standard(parent, "LiabilitiesAndStockholdersEquity") or observed is None:
            continue
        # The complete top-level equation must reconcile. Classify every nonzero
        # branch explicitly so temporary equity or unusual capital is never debt.
        liability_parts, equity_parts, unknown = [], [], False
        for component in components:
            tag, version = component["tag"], component["version"]
            if component["value"] == 0:
                continue
            if not version.startswith("us-gaap/") or component["weight"] != 1:
                unknown = True
            elif tag in EQUITY_TAGS:
                equity_parts.append(component)
            elif tag in LIABILITY_TAGS:
                liability_parts.append(component)
            else:
                unknown = True
        if unknown or not liability_parts or not equity_parts:
            continue
        liability = sum(c["value"] for c in liability_parts)
        if liability >= 0:
            evidence = [dict(tag=parent[0], version=parent[1], **observed), *components]
            if omitted_disclosures:
                evidence[0] = dict(evidence[0], omitted_non_amount_disclosures=omitted_disclosures)
            candidates["liabilities"].append((liability, "reconciled_balance_sheet_calculation", evidence))
    return candidates


def extract(archive_paths, dataset, inventory, output):
    output = Path(output)
    company_dir = output / "companies"
    audit_path = output / "audit.json"
    audit_temporary = output / "audit.json.tmp"
    if not (output.is_dir() and set(output.iterdir()) <= {company_dir, audit_path, audit_temporary}
            and company_dir.is_dir() and (not audit_path.exists() or audit_path.is_file())):
        output = new_output(output)
        company_dir.mkdir()
    def checkpoint():
        write_json(audit_temporary, report)
        audit_temporary.replace(audit_path)
    # A failed early run can leave only an empty companies directory. Later
    # runs have a checkpoint in audit.json and company files written atomically.
    candidates = {r["company_id"] for r in read_csv(inventory) if r["screen"] == "candidate"}
    planned_archives = [str(Path(path)) for path in archive_paths]
    inventory_hash = file_hash(inventory)
    if audit_path.exists():
        report = json.loads(audit_path.read_text())
        if (report.get("planned_archives") != planned_archives
                or report.get("inventory_sha256") != inventory_hash):
            raise ValueError("Statement import inputs changed; use a new output directory")
        if report.get("status") == "complete":
            return report
        audit = Counter(report["counts"])
        archive_hashes = report["archives"]
    else:
        audit, archive_hashes = Counter(), {}
        report = dict(status="in_progress", counts={}, companies=0, facts=0,
                      archives={}, planned_archives=planned_archives,
                      inventory_sha256=inventory_hash,
                      scope="Consolidated USD balance sheets; period anchored to original Company Facts; no duration inference.")
        checkpoint()
    for archive_path in archive_paths:
        archive_path = Path(archive_path)
        sha = file_hash(archive_path)
        if str(archive_path) in archive_hashes:
            if archive_hashes[str(archive_path)] != sha:
                raise ValueError(f"Previously imported archive changed: {archive_path}")
            print(f"Already imported {archive_path.name}", flush=True)
            continue
        report["archive_in_progress"] = str(archive_path)
        checkpoint()
        emitted = defaultdict(list)
        print(f"Reading {archive_path.name}: submissions and statement structure", flush=True)
        with zipfile.ZipFile(archive_path) as archive:
            submissions = {r["adsh"]: r for r in rows(archive, "sub.tsv")
                           if r["form"] in FORMS and r["cik"].zfill(10) in candidates}
            presentation = defaultdict(lambda: defaultdict(set))
            for row in rows(archive, "pre.tsv"):
                if row["adsh"] in submissions and row["stmt"] == "BS" and row["inpth"] == "0":
                    presentation[row["adsh"]][(row["tag"], row["version"])].add(row["plabel"])
            relevant_nodes = {node for nodes in presentation.values() for node in nodes}
            metadata = { (r["tag"], r["version"]): r for r in rows(archive, "tag.tsv")
                         if (r["tag"], r["version"]) in relevant_nodes}
            calculations = defaultdict(lambda: defaultdict(list))
            sign_values = set()
            for row in rows(archive, "cal.tsv"):
                sign_values.add(row["negative"])
                adsh = row["adsh"]
                parent = (row["ptag"], row["pversion"])
                child = (row["ctag"], row["cversion"])
                if adsh in presentation and (parent in presentation[adsh]
                        or any(standard(parent, tag) for tag in FIELDS.values())):
                    # Every child must be in the primary balance sheet, not a
                    # similarly named footnote schedule or parent-only statement.
                    calculations[adsh][(row["grp"], parent)].append((child, row["negative"]))
            # Actual reprocessed archives use signed weights despite the older
            # PDF's boolean description. Determine the encoding from its domain;
            # an all-ones archive is ambiguous and must not be guessed.
            if not sign_values:
                # Header-only CAL tables have no arcs to interpret. Direct
                # statement totals remain usable.
                parse_weight = int
                audit["archives_without_cal_weights"] += 1
            elif sign_values <= {"-1", "1"} and "-1" in sign_values:
                parse_weight = int
                audit["archives_with_signed_cal_weights"] += 1
            elif sign_values <= {"0", "1"} and "0" in sign_values:
                parse_weight = lambda value: -1 if value == "1" else 1
                audit["archives_with_boolean_cal_weights"] += 1
            else:
                raise ValueError(f"Ambiguous or unsupported CAL weight encoding: {sign_values}")
            for groups in calculations.values():
                for key, arcs in groups.items():
                    groups[key] = [(child, parse_weight(weight)) for child, weight in arcs]
            print(f"Reading {archive_path.name}: consolidated balance-sheet numbers", flush=True)
            numbers = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
            for row in rows(archive, "num.tsv"):
                adsh, node = row["adsh"], (row["tag"], row["version"])
                if adsh not in presentation or node not in presentation[adsh]:
                    continue
                if row["qtrs"] != "0" or row["uom"] != "USD" or row["dimn"] != "0" or row["coreg"]:
                    continue
                meta = metadata.get(node, {})
                if meta.get("iord") != "I" or meta.get("abstract") != "0" or meta.get("datatype") != "monetary":
                    continue
                try:
                    value = float(row["value"])
                    dcml = int(row["dcml"])
                    if not math.isfinite(value) or dcml < -15:
                        continue
                except (ValueError, OverflowError):
                    continue
                numbers[adsh][(row["ddate"], row["datp"])][node].append(
                    dict(value=value, rounding=0 if dcml >= 15 else 0.5 * 10 ** (-dcml),
                         ddate=row["ddate"], datp=row["datp"], dcml=dcml, iprx=row["iprx"]))
        by_company = defaultdict(list)
        for adsh in numbers:
            by_company[submissions[adsh]["cik"].zfill(10)].append(adsh)
        for company, accessions in by_company.items():
            document = json.loads((Path(dataset) / "companyfacts" / f"CIK{company}.json").read_text())
            anchors = defaultdict(set)
            for tag in ("Assets", "LiabilitiesAndStockholdersEquity"):
                for r in document.get("facts", {}).get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", []):
                    if not r.get("start") and r.get("form") in FORMS:
                        anchors[(r.get("accn"), tag, float(r["val"]))].add(r["end"])
            for adsh in accessions:
                filed = date.fromisoformat(submissions[adsh]["filed"]).isoformat()
                for (rounded, proximity), facts in numbers[adsh].items():
                    # The bulk date is rounded. Pin the exact end to an agreeing
                    # Company Facts balance total in this same filing and context.
                    ends = set()
                    for node, records in facts.items():
                        if not node[1].startswith("us-gaap/") or node[0] not in {"Assets", "LiabilitiesAndStockholdersEquity"}:
                            continue
                        fact = one_value(records)
                        if fact:
                            ends.update(e for e in anchors.get((adsh, node[0], fact["value"]), ())
                                        if abs((date.fromisoformat(e) - date.fromisoformat(rounded)).days) <= 16)
                    if len(ends) != 1:
                        audit["period_without_unique_exact_date_anchor"] += 1
                        continue
                    end = ends.pop()
                    if end > filed:
                        audit["period_after_filing"] += 1
                        continue
                    recovered = recover_period(facts, calculations[adsh], presentation[adsh], metadata)
                    for field, choices in recovered.items():
                        # Prefer an explicit total. Otherwise all independent
                        # calculation groups must yield the same number.
                        direct = [x for x in choices if x[1].startswith("statement_")]
                        choices = direct or choices
                        if len({v for v, _, _ in choices}) != 1:
                            audit["conflicting_reconstructions"] += 1
                            continue
                        value, basis, sources = choices[0]
                        record = dict(field=field, value=value, tag=f"statement:{FIELDS[field]}",
                                      start=None, end=end, filed=filed, accession=adsh,
                                      source=dict(kind="SEC_statement_notes", basis=basis,
                                                  archive=str(archive_path), archive_sha256=sha,
                                                  sources=sources))
                        if record not in emitted[company]:
                            emitted[company].append(record)
                            audit[f"{field}:{basis}"] += 1
        for company, facts in emitted.items():
            path = company_dir / f"CIK{company}.json"
            existing = json.loads(path.read_text())["facts"] if path.exists() else []
            for fact in facts:
                if fact not in existing:
                    existing.append(fact)
            temporary = path.with_suffix(".json.tmp")
            write_json(temporary, dict(cik=company, facts=existing))
            temporary.replace(path)
        report["facts"] += sum(map(len, emitted.values()))
        report["companies"] = sum(1 for _ in company_dir.glob("CIK*.json"))
        report["counts"] = dict(audit)
        archive_hashes[str(archive_path)] = sha
        report["archives"] = archive_hashes
        report.pop("archive_in_progress", None)
        checkpoint()
        print(f"Saved {sum(map(len, emitted.values()))} facts from {archive_path.name}; "
              f"total {report['facts']} facts across {report['companies']} companies", flush=True)
    report["status"] = "complete"
    checkpoint()
    return report


def attach(document, directory):
    """Attach independently sourced facts without modifying original JSON files."""
    path = Path(directory) / f"CIK{str(document['cik']).zfill(10)}.json"
    if not path.exists():
        return None
    supplement = json.loads(path.read_text())
    if str(supplement["cik"]).zfill(10) != str(document["cik"]).zfill(10):
        raise ValueError(f"CIK mismatch in {path}")
    document["_statement_facts"] = supplement["facts"]
    return dict(path=str(path), sha256=file_hash(path))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, nargs="+", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.archives, args.dataset, args.inventory, args.output_dir), indent=2))
