"""Statement recovery must preserve scope, period, availability and complete sums."""

import csv
import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from mcf.data.point_in_time import FactIndex
from mcf.data.sec import latest_fact, snapshot
from mcf.data.statement_facts import attach, extract, recover_period


VERSION = "us-gaap/2024"


def node(tag):
    return (tag, VERSION)


def number(value):
    return {"value": value, "rounding": 0}


def document(mapping):
    return {"cik": 1, "facts": {"us-gaap": {
        tag: {"units": {"USD": records}} for tag, records in mapping.items()}}}


def fact(value, filed="2025-02-01", end="2024-12-31", accession="a"):
    return dict(val=value, filed=filed, end=end, accn=accession, form="10-K")


class RecoveryTests(unittest.TestCase):
    def test_header_only_cal_table_keeps_direct_balance_totals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "companyfacts").mkdir()
            (root / "companyfacts/CIK0000000001.json").write_text(
                json.dumps(document({"Assets": [fact(100, end="2024-12-31")]}))
            )
            inventory = root / "inventory.csv"
            inventory.write_text("company_id,screen\n0000000001,candidate\n")
            archive = root / "notes.zip"
            with zipfile.ZipFile(archive, "w") as z:
                def table(name, fields, records):
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=fields.split(), delimiter="\t")
                    writer.writeheader()
                    writer.writerows(records)
                    z.writestr(name, output.getvalue())
                table("sub.tsv", "adsh cik form filed", [dict(adsh="a", cik="1", form="10-K", filed="20250201")])
                table("pre.tsv", "adsh stmt inpth tag version plabel", [
                    dict(adsh="a", stmt="BS", inpth="0", tag=tag, version=VERSION, plabel=tag)
                    for tag in ("Assets", "Liabilities")])
                table("tag.tsv", "tag version custom iord abstract datatype", [
                    dict(tag=tag, version=VERSION, custom="0", iord="I", abstract="0", datatype="monetary")
                    for tag in ("Assets", "Liabilities")])
                table("cal.tsv", "adsh grp negative ptag pversion ctag cversion", [])
                table("num.tsv", "adsh tag version ddate datp dcml iprx qtrs uom dimn coreg value", [
                    dict(adsh="a", tag=tag, version=VERSION, ddate="20241231", datp="0",
                         dcml="0", iprx="0", qtrs="0", uom="USD", dimn="0", coreg="", value=str(value))
                    for tag, value in (("Assets", 100), ("Liabilities", 60))])
            report = extract([archive], root, inventory, root / "recovered")
            self.assertEqual(report["counts"]["archives_without_cal_weights"], 1)
            self.assertEqual(report["counts"]["liabilities:statement_standard_total"], 1)
            (root / "empty_retry/companies").mkdir(parents=True)
            self.assertEqual(extract([archive], root, inventory, root / "empty_retry")["facts"], 2)
            second = root / "later.zip"
            second.write_text("incomplete download")
            partial_output = root / "resumable"
            with self.assertRaises(zipfile.BadZipFile):
                extract([archive, second], root, inventory, partial_output)
            progress = json.loads((partial_output / "audit.json").read_text())
            self.assertEqual(progress["status"], "in_progress")
            self.assertEqual(progress["facts"], 2)
            self.assertEqual(len(progress["archives"]), 1)
            self.assertTrue((partial_output / "companies/CIK0000000001.json").exists())
            second.write_bytes(archive.read_bytes())
            completed = extract([archive, second], root, inventory, partial_output)
            self.assertEqual(completed["status"], "complete")
            self.assertEqual(completed["facts"], 4)
            self.assertEqual(len(json.loads((partial_output / "companies/CIK0000000001.json").read_text())["facts"]), 4)

    def test_assets_identity_is_historical_fallback_and_does_not_hide_conflicts(self):
        doc = document({"LiabilitiesAndStockholdersEquity": [fact(100)],
                        "Assets": [fact(110, filed="2025-03-01")]})
        decisions = [date(2025, 2, 1), date(2025, 2, 2), date(2025, 3, 2)]
        index = FactIndex(doc, decisions[-1])
        for decision, expected in zip(decisions, [None, 100, 110]):
            slow = snapshot(doc, decision)
            self.assertEqual(slow[0]["assets"], expected)
            self.assertEqual(index.snapshot(decision), slow)
        doc["facts"]["us-gaap"]["Assets"]["units"]["USD"].append(fact(120, filed="2025-03-01"))
        doc["facts"]["us-gaap"]["LiabilitiesAndStockholdersEquity"]["units"]["USD"].append(fact(120, filed="2025-04-01"))
        self.assertIsNone(latest_fact(doc, "assets", date(2025, 5, 1)))

    def test_reconciled_branches_separate_temporary_and_noncontrolling_equity(self):
        values = {"LiabilitiesAndStockholdersEquity": 100, "LiabilitiesCurrent": 25,
                  "LongTermDebtNoncurrent": 35, "StockholdersEquity": 20,
                  "MinorityInterest": 5, "TemporaryEquityCarryingAmountAttributableToParent": 15}
        facts = {node(tag): [number(value)] for tag, value in values.items()}
        arcs = [(node(tag), 1) for tag in values if tag != "LiabilitiesAndStockholdersEquity"]
        groups = {("1", node("LiabilitiesAndStockholdersEquity")): arcs}
        result = recover_period(facts, groups, {}, {})
        self.assertEqual(result["liabilities"][0][0], 60)
        # A missing branch is not zero, even if it is an equity branch.
        del facts[node("MinorityInterest")]
        self.assertNotIn("liabilities", recover_period(facts, groups, {}, {}))

    def test_unreconciled_or_unclassified_branches_are_rejected(self):
        parent = node("LiabilitiesAndStockholdersEquity")
        facts = {parent: [number(100)], node("LiabilitiesCurrent"): [number(60)],
                 node("StockholdersEquity"): [number(30)]}
        groups = {("1", parent): [(node("LiabilitiesCurrent"), 1), (node("StockholdersEquity"), 1)]}
        self.assertNotIn("liabilities", recover_period(facts, groups, {}, {}))

    def test_non_amount_commitments_disclosure_requires_reconciliation(self):
        parent = node("LiabilitiesAndStockholdersEquity")
        facts = {parent: [number(100)], node("LiabilitiesCurrent"): [number(60)],
                 node("StockholdersEquity"): [number(40)]}
        groups = {("1", parent): [(node("LiabilitiesCurrent"), 1),
                                   (node("StockholdersEquity"), 1),
                                   (node("CommitmentsAndContingencies"), 1)]}
        result = recover_period(facts, groups, {}, {})
        self.assertEqual(result["liabilities"][0][0], 60)
        facts[parent] = [number(110)]
        self.assertNotIn("liabilities", recover_period(facts, groups, {}, {}))
        unknown = ("UnclassifiedCapital", "a")
        facts[unknown] = [number(10)]
        groups[("1", parent)].append((unknown, 1))
        self.assertNotIn("liabilities", recover_period(facts, groups, {}, {}))

    def test_calculation_groups_are_not_merged_and_conflicting_children_rejected(self):
        parent = node("Liabilities")
        facts = {node("LiabilitiesCurrent"): [number(20)], node("LiabilitiesNoncurrent"): [number(30)]}
        groups = {("1", parent): [(node("LiabilitiesCurrent"), 1), (node("LiabilitiesNoncurrent"), 1)],
                  ("2", parent): [(node("OtherLiabilities"), 1)]}
        self.assertEqual(recover_period(facts, groups, {}, {})["liabilities"][0][0], 50)
        facts[node("LiabilitiesCurrent")].append(number(21))
        self.assertNotIn("liabilities", recover_period(facts, groups, {}, {}))

    def test_custom_total_requires_exact_labels(self):
        custom = ("SpecialTotal", "a")
        facts = {custom: [number(60)]}
        metadata = {custom: {"custom": "1", "tlabel": "Total liabilities"}}
        self.assertEqual(recover_period(facts, {}, {custom: {"Total liabilities"}}, metadata)["liabilities"][0][0], 60)
        self.assertNotIn("liabilities", recover_period(facts, {}, {custom: {"Other liabilities"}}, metadata))

    def test_archive_import_and_snapshot_with_rounded_date_and_dimension_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "companyfacts").mkdir()
            doc = document({"Assets": [fact(100, end="2024-12-28")]})
            (root / "companyfacts/CIK0000000001.json").write_text(json.dumps(doc))
            inventory = root / "inventory.csv"
            inventory.write_text("company_id,screen\n0000000001,candidate\n")
            totals = {"Assets": 100, "LiabilitiesAndStockholdersEquity": 100,
                      "LiabilitiesCurrent": 20, "LongTermDebtNoncurrent": 40, "StockholdersEquity": 40}
            archive = root / "notes.zip"
            with zipfile.ZipFile(archive, "w") as z:
                def table(name, fields, records):
                    text = io.StringIO()
                    writer = csv.DictWriter(text, fieldnames=fields.split(), delimiter="\t")
                    writer.writeheader()
                    writer.writerows(records)
                    z.writestr(name, text.getvalue())
                table("sub.tsv", "adsh cik form filed", [dict(adsh="a", cik="1", form="10-K", filed="20250201")])
                table("pre.tsv", "adsh stmt inpth tag version plabel", [
                    dict(adsh="a", stmt="BS", inpth="0", tag=tag, version=VERSION, plabel=tag) for tag in totals])
                table("tag.tsv", "tag version custom iord abstract datatype", [
                    dict(tag=tag, version=VERSION, custom="0", iord="I", abstract="0", datatype="monetary") for tag in totals])
                table("cal.tsv", "adsh grp negative ptag pversion ctag cversion", [
                    dict(adsh="a", grp="1", negative="1", ptag="LiabilitiesAndStockholdersEquity", pversion=VERSION,
                         ctag=tag, cversion=VERSION) for tag in ("LiabilitiesCurrent", "LongTermDebtNoncurrent", "StockholdersEquity")]
                      + [dict(adsh="unrelated", grp="1", negative="-1", ptag="Assets", pversion=VERSION,
                              ctag="AccumulatedDepreciation", cversion=VERSION)])
                numbers = [dict(adsh="a", tag=tag, version=VERSION, ddate="20241231", datp="3", dcml="0", iprx="0",
                                qtrs="0", uom="USD", dimn="0", coreg="", value=str(value)) for tag, value in totals.items()]
                numbers.append(dict(numbers[2], value="999", dimn="1"))
                table("num.tsv", "adsh tag version ddate datp dcml iprx qtrs uom dimn coreg value", numbers)
            output = root / "recovered"
            extract([archive], root, inventory, output)
            attach(doc, output / "companies")
            decision = date(2025, 2, 2)
            values, sources = snapshot(doc, decision)
            self.assertEqual(values["liabilities"], 60)
            self.assertEqual(values["balance_period_end"], "2024-12-28")
            self.assertEqual(sources["liabilities"]["source"]["basis"], "reconciled_balance_sheet_calculation")
            self.assertEqual((values, sources), FactIndex(doc, decision).snapshot(decision))
            self.assertIsNone(snapshot(doc, date(2025, 2, 1))[0]["liabilities"])
            # A native total blocks same/later fallback evidence.
            doc["facts"]["us-gaap"]["Liabilities"] = {"units": {"USD": [fact(61, end="2024-12-28")]}}
            self.assertEqual(snapshot(doc, decision)[0]["liabilities"], 61)


if __name__ == "__main__":
    unittest.main()
