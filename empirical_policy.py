"""Historical limit SCENARIOS using real SEC financials and frozen probabilities.

Cash eligibility, additional debt payments, caps and facility exposure are
assumptions. No losses, borrower behavior, utilization or recoveries are modeled.
Gaps start new hypothetical facilities; no monthly change crosses a gap.
"""
import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path

import joblib
import numpy as np

from credit_policy import PolicyConfig, PolicyInputs, determine_limit
from policy_sensitivity import scenarios
from research_common import manifest, new_output, read_csv, write_csv, write_json


def consecutive(earlier, later):
    return earlier is not None and (later.year * 12 + later.month) - (earlier.year * 12 + earlier.month) == 1


def replay_scenario(rows, policy, *, cash_fraction=1., cap_fraction=.01,
                    debt_fraction=0., probability_stress=False, no_risk=False,
                    probability_column="probability"):
    previous_company = previous_date = previous_limit = previous_signature = None
    segment = 0
    for row in rows:
        company, decision = row["company_id"], date.fromisoformat(row["decision_date"])
        reset = company != previous_company or not consecutive(previous_date, decision)
        if reset:
            previous_limit = previous_signature = None
            segment += 1
        probability = 0. if no_risk else row[probability_column]
        if probability_stress:
            probability = min(1., probability * 2.)
        inputs = PolicyInputs(
            revenue_annual=row["revenue_annual"],
            operating_cashflow_annual=row["operating_cashflow_annual"],
            eligible_cash=row["reported_cash"] * cash_fraction,
            external_debt_service_60d=row["assets"] * debt_fraction,
            risk_probability=probability, hard_cap=row["assets"] * cap_fraction,
            outstanding_exposure=0., previous_limit=previous_limit,
            hard_stop=row["known_disclosure"], risk_target="first_sec_item_1_03_disclosure",
            risk_horizon_days=60, risk_is_illustrative=probability_stress)
        signature = (inputs.revenue_annual, inputs.operating_cashflow_annual, inputs.eligible_cash,
                     inputs.external_debt_service_60d, probability, inputs.hard_cap, inputs.hard_stop)
        inputs = replace(inputs, information_changed=signature != previous_signature)
        result = determine_limit(inputs, policy)
        yield dict(company_id=company, entity_name=row["entity_name"], decision_date=str(decision),
            segment=segment, segment_initial=reset, input_basis="observed_financials_assumed_facility",
            feature_available_on=row["feature_available_on"], assets=row["assets"],
            probability=probability, known_disclosure=row["known_disclosure"],
            revenue_annual=inputs.revenue_annual, operating_cashflow_annual=inputs.operating_cashflow_annual,
            eligible_cash=inputs.eligible_cash, external_debt_service_60d=inputs.external_debt_service_60d,
            hard_cap=inputs.hard_cap, outstanding_exposure=inputs.outstanding_exposure,
            previous_limit=previous_limit,
            limit_change=None if reset else result.assigned_limit - previous_limit,
            **asdict(result))
        previous_company, previous_date = company, decision
        previous_limit, previous_signature = result.assigned_limit, signature


def summarize(paths):
    assigned = np.array([r["assigned_limit"] for r in paths])
    assets = np.array([r["assets"] for r in paths])
    changes = [r for r in paths if r["limit_change"] is not None]
    return dict(rows=len(paths), companies=len({r["company_id"] for r in paths}),
        segments=sum(r["segment_initial"] for r in paths),
        mean_limit_usd=float(assigned.mean()), median_limit_usd=float(np.median(assigned)),
        mean_limit_to_assets=float(np.mean(assigned / assets)),
        zero_limit_share=float(np.mean(assigned == 0)), continuous_changes=len(changes),
        increases=sum(r["limit_change"] > 1e-8 for r in changes),
        decreases=sum(r["limit_change"] < -1e-8 for r in changes),
        unchanged=sum(abs(r["limit_change"]) <= 1e-8 for r in changes),
        mean_absolute_change_usd=float(np.mean([abs(r["limit_change"]) for r in changes])) if changes else None,
        mean_absolute_change_to_assets=float(np.mean([abs(r["limit_change"]) / r["assets"] for r in changes])) if changes else None,
        hard_stop_rows=sum(r["known_disclosure"] for r in paths),
        cap_binding_share=sum(r["binding_constraint"] == "hard_cap" for r in paths) / len(paths))


def run(models, features, policy_path, output):
    output = new_output(output)
    bundle = joblib.load(models)
    choice = bundle["selection"]["selected_model"]
    model_name = choice or "constant_training_prevalence_fallback"
    model = bundle["models"][choice] if choice else next(iter(bundle["models"].values()))
    config = model["design"]
    rows, excluded = [], Counter()
    with Path(features).open() as stream:
        for row in csv.DictReader(stream):
            if row["decision_date"] < config["test_start"]:
                continue
            if row["data_kind"] != "empirical" or row["feature_available_on"] > row["decision_date"]:
                raise ValueError("Invalid empirical information timing")
            names = ("assets", "revenue_annual", "operating_cashflow_annual", "reported_cash")
            if any(row[n] == "" for n in names):
                excluded["missing_required_financial_input"] += 1
                continue
            for n in names:
                row[n] = float(row[n])
            if (not all(np.isfinite(row[n]) for n in names) or row["assets"] <= 0
                    or min(row["revenue_annual"], row["reported_cash"]) < 0):
                excluded["invalid_required_financial_input"] += 1
                continue
            row["known_disclosure"] = row["known_disclosure"] == "True"
            rows.append(row)
    rows.sort(key=lambda r: (r["company_id"], r["decision_date"]))
    x = np.array([[float(r[f]) if r[f] else np.nan for f in config["features"]] for r in rows])
    probabilities = (bundle["models"][choice]["calibrated"].predict_proba(x)[:, 1] if choice else
                     np.full(len(rows), bundle["selection"]["constant_training_prevalence"]))
    for row, probability in zip(rows, probabilities):
        row["probability"] = float(probability)
    # Exploratory mappings are reported for every fitted family, without
    # promoting any family that failed the selection-period acceptance rule.
    for name, fitted in bundle["models"].items():
        for row, probability in zip(rows, fitted["calibrated"].predict_proba(x)[:, 1]):
            row["probability_" + name] = float(probability)
    write_csv(output / "policy_probabilities.csv",
        [dict(company_id=r["company_id"], decision_date=r["decision_date"], model=model_name,
              probability=r["probability"], known_disclosure=r["known_disclosure"]) for r in rows])
    policy = PolicyConfig(**json.loads(Path(policy_path).read_text())["parameters"])
    summaries, base_paths = [], None
    specifications = [(name, c, {}) for name, c in scenarios(policy)]
    specifications += [
        ("cash_eligible_half", policy, dict(cash_fraction=.5)),
        ("cash_eligible_zero", policy, dict(cash_fraction=0.)),
        ("cap_assets_0.005", policy, dict(cap_fraction=.005)),
        ("cap_assets_0.02", policy, dict(cap_fraction=.02)),
        ("additional_debt_assets_0.005", policy, dict(debt_fraction=.005)),
        ("probability_doubled", policy, dict(probability_stress=True)),
        ("capacity_only", policy, dict(no_risk=True)),
    ]
    specifications += [
        ("exploratory_" + name, policy, dict(probability_column="probability_" + name))
        for name in bundle["models"]
    ]
    for name, setting, overrides in specifications:
        print(f"Policy scenario: {name}", flush=True)
        paths = list(replay_scenario(rows, setting, **overrides))
        summaries.append(dict(scenario=name, **summarize(paths)))
        if name == "base":
            base_paths = paths
            write_csv(output / "limit_paths.csv", paths)
        if name == "capacity_only":
            for base, other in zip(base_paths, paths):
                base["capacity_only_limit"] = other["assigned_limit"]
        if name.startswith("exploratory_"):
            for base, other in zip(base_paths, paths):
                base[name + "_limit"] = other["assigned_limit"]
                base[name + "_probability"] = other["probability"]
    # Fixed-initial benchmark preserves its initial amount, subject to current
    # cap and disclosure stop. Unsmoothed benchmark takes each current raw limit.
    fixed = None
    for row in base_paths:
        if row["segment_initial"]:
            fixed = row["raw_limit"]
        row["fixed_initial_limit"] = 0. if row["known_disclosure"] else min(fixed, row["hard_cap"])
        row["unsmoothed_limit"] = row["raw_limit"]
    write_csv(output / "comparison_paths.csv", base_paths)
    for name, field in (("fixed_initial", "fixed_initial_limit"), ("unsmoothed", "unsmoothed_limit")):
        alternative, previous = [], None
        for row in base_paths:
            r = dict(row, assigned_limit=row[field])
            r["limit_change"] = None if row["segment_initial"] else r["assigned_limit"] - previous
            previous = r["assigned_limit"]
            alternative.append(r)
        summary = summarize(alternative)
        # These benchmarks do not apply the base formula; its binding flag is not theirs.
        summary["cap_binding_share"] = None
        summaries.append(dict(scenario=name, **summary))
    write_csv(output / "policy_sensitivity.csv", summaries)
    write_json(output / "policy_audit.json", dict(model=model_name, selected_model=choice,
        excluded=dict(excluded), base=summaries[0], update_reasons=dict(Counter(r["update_reason"] for r in base_paths)),
        binding_constraints=dict(Counter(r["binding_constraint"] for r in base_paths)),
        assumptions=config["policy_scenario"], outcome="Limits only; no observed exposure, loss or profitability"))
    write_json(output / "scenario_parameters.json", {
        name: dict(parameters=asdict(setting), overrides=overrides) for name, setting, overrides in specifications})
    write_json(output / "manifest.json", manifest([models, features, policy_path],
        data_kind="empirical_financials_with_policy_assumptions", model=model_name, rows=len(rows)))
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("models", "features", "policy", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    run(args.models, args.features, args.policy, args.output_dir)
