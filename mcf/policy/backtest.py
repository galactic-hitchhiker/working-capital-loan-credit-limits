"""Sequential Chapter 5 policy replay with explicit borrower inputs and provenance.

This is an exposure-policy simulation. It does not simulate drawdowns, repayments,
recoveries, profit, causality or realized loss. Never substitutes accounting cash
or total debt for verified cash eligibility or payments due.

Run from the repository root:
    .venv/bin/python -m mcf.policy.backtest [parameters]

Parameters:
    --predictions PATH: Required monthly policy_predictions.csv from model scoring.
    --inputs PATH: Required borrower/facility input CSV, including provenance and initial limits.
    --policy PATH: Required policy-parameter JSON.
    --output-dir PATH: Required destination for sequential limit paths and audit.
    -h, --help: Show command usage and exit.
"""

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from mcf.policy.credit import PolicyConfig, PolicyInputs, determine_limit
from mcf.common import (
    boolean,
    finite,
    manifest,
    new_output,
    read_csv,
    write_csv,
    write_json,
)

INPUT_FIELDS = (
    "company_id",
    "decision_date",
    "currency",
    "revenue_annual",
    "operating_cashflow_annual",
    "eligible_cash",
    "external_debt_service_60d",
    "hard_cap",
    "outstanding_exposure",
    "initial_limit",
    "information_changed",
    "hard_stop",
    "reopen",
    "inputs_available_on",
    "assessment_status",
    "input_basis",
    "input_source",
)
MONEY_FIELDS = (
    "revenue_annual",
    "operating_cashflow_annual",
    "eligible_cash",
    "external_debt_service_60d",
    "hard_cap",
    "outstanding_exposure",
)


def replay(predictions, inputs, policy):
    """Join frozen predictions to monthly facility inputs and carry limits forward.

    Unlike empirical scenarios, this register-based replay requires continuous
    monthly reviews and explicit authorization in the inputs to reopen a facility.
    Returns decision rows and the number of predictions without facility inputs.
    """
    predictions_by_month = {}
    for row in predictions:
        if not boolean(row["selected"]) or row["stage"] not in {"test", "policy"}:
            continue
        key = (row["company_id"], row["decision_date"])
        if key in predictions_by_month:
            raise ValueError("Duplicate selected-model prediction")
        if date.fromisoformat(row["prediction_ready_on"]) > date.fromisoformat(
            row["decision_date"]
        ):
            raise ValueError(
                "Policy prediction uses a model selected after the decision date"
            )
        predictions_by_month[key] = row
    groups, seen = defaultdict(list), set()
    for row in inputs:
        key = (row["company_id"], row["decision_date"])
        if key in seen or key not in predictions_by_month:
            raise ValueError(
                f"Duplicate decision or missing selected-model prediction: {key}"
            )
        seen.add(key)
        groups[key[0]].append(row)
    if not groups:
        raise ValueError("No policy inputs; complete the policy-input register")
    results = []
    for company, company_rows in sorted(groups.items()):
        previous_date, previous_limit, previous_signature, previous_ledger = (
            None,
            None,
            None,
            None,
        )
        for row in sorted(company_rows, key=lambda r: r["decision_date"]):
            decision = date.fromisoformat(row["decision_date"])
            if decision.day != 1:
                raise ValueError("Policy dates must be month starts")
            if previous_date:
                expected = date(
                    previous_date.year + (previous_date.month == 12),
                    previous_date.month % 12 + 1,
                    1,
                )
                if decision != expected:
                    raise ValueError(
                        "Missing review month: do not replay a gap as one monthly update"
                    )
                if row["initial_limit"] != "":
                    raise ValueError(
                        "Initial limit may only appear on the first company row"
                    )
            else:
                previous_limit = finite(
                    row["initial_limit"], "initial_limit", missing=True
                )
            prediction = predictions_by_month[(company, str(decision))]
            if (
                not row["input_source"].strip()
                or row["input_basis"] not in {"observed", "assumed"}
                or row["assessment_status"] not in {"eligible", "blocked"}
            ):
                raise ValueError(
                    "Policy inputs require a source, basis and completed eligibility assessment"
                )
            if date.fromisoformat(row["inputs_available_on"]) > decision:
                raise ValueError("Future borrower information in policy inputs")
            hard_stop, reopen = boolean(row["hard_stop"]), boolean(row["reopen"])
            if row["assessment_status"] == "blocked" and not hard_stop:
                raise ValueError("Blocked borrower requires a hard stop")
            if reopen:
                if (
                    previous_limit != 0
                    or hard_stop
                    or not boolean(row["information_changed"])
                ):
                    raise ValueError(
                        "Reopening requires a zero prior limit, new information and eligibility"
                    )
                previous_limit = None
            numbers = {f: finite(row[f], f) for f in MONEY_FIELDS}
            ledger = (
                row["currency"],
                prediction["model"],
                prediction["event_type"],
                int(prediction["horizon_days"]),
                prediction["data_kind"],
            )
            if previous_ledger is not None and ledger != previous_ledger:
                raise ValueError(
                    "Currency/model/target/horizon cannot change inside one policy replay"
                )
            # A supported change can be financial, risk or policy-related; a new
            # timestamp alone does not permit a repeated smoothed increase.
            signature = (
                tuple(numbers[f] for f in MONEY_FIELDS),
                finite(prediction["probability"], "probability"),
                hard_stop,
                row["assessment_status"],
            )
            changed = boolean(row["information_changed"]) and (
                previous_signature is None or signature != previous_signature
            )
            inputs_obj = PolicyInputs(
                **numbers,
                risk_probability=finite(prediction["probability"], "probability"),
                previous_limit=previous_limit,
                information_changed=changed,
                hard_stop=hard_stop,
                currency=row["currency"],
                risk_target=prediction["event_type"],
                risk_horizon_days=int(prediction["horizon_days"]),
                risk_is_illustrative=prediction["data_kind"] == "synthetic",
            )
            result = determine_limit(inputs_obj, policy)
            delta = (
                result.assigned_limit - previous_limit
                if previous_limit is not None
                else None
            )
            results.append(
                dict(
                    company_id=company,
                    decision_date=str(decision),
                    data_kind=prediction["data_kind"],
                    input_basis=row["input_basis"],
                    input_source=row["input_source"],
                    inputs_available_on=row["inputs_available_on"],
                    model=prediction["model"],
                    **asdict(inputs_obj),
                    **asdict(result),
                    limit_change=delta,
                    relative_change=(
                        delta / previous_limit
                        if previous_limit and delta is not None
                        else None
                    ),
                )
            )
            previous_date, previous_limit, previous_signature, previous_ledger = (
                decision,
                result.assigned_limit,
                signature,
                ledger,
            )
    if (
        len(
            {
                (
                    r["currency"],
                    r["model"],
                    r["risk_target"],
                    r["risk_horizon_days"],
                    r["data_kind"],
                )
                for r in results
            }
        )
        != 1
    ):
        raise ValueError(
            "Use separate policy runs for different currencies, models, targets, horizons or data kinds"
        )
    return results, len(predictions_by_month) - len(seen)


def run(predictions_path, input_path, policy_path, output):
    """Validate input files, replay the policy and export decisions with an audit."""
    policy_config = json.loads(Path(policy_path).read_text())
    policy = PolicyConfig(**policy_config["parameters"])
    predictions = read_csv(
        predictions_path,
        (
            "company_id",
            "decision_date",
            "data_kind",
            "event_type",
            "horizon_days",
            "model",
            "probability",
            "selected",
            "stage",
            "prediction_ready_on",
        ),
    )
    results, unused = replay(predictions, read_csv(input_path, INPUT_FIELDS), policy)
    output = new_output(output)
    write_csv(output / "limit_path.csv", results)
    changes = [r["limit_change"] for r in results if r["limit_change"] is not None]
    summary = dict(
        rows=len(results),
        companies=len({r["company_id"] for r in results}),
        changes=len(changes),
        increases=sum(d > 0 for d in changes),
        decreases=sum(d < 0 for d in changes),
        unchanged=sum(d == 0 for d in changes),
        mean_absolute_change=(
            sum(abs(d) for d in changes) / len(changes) if changes else None
        ),
        maximum_absolute_change=max(map(abs, changes)) if changes else None,
        exposure_above_limit_rows=sum(r["excess_exposure"] > 0 for r in results),
        unused_predictions=unused,
        input_basis=sorted({r["input_basis"] for r in results}),
        data_kind=sorted({r["data_kind"] for r in results}),
        scope="supplied borrower-months only; no repayment, utilization or realized-loss model",
    )
    write_json(output / "summary.json", summary)
    write_json(output / "policy.json", policy_config)
    write_json(
        output / "manifest.json",
        manifest([predictions_path, input_path, policy_path], **summary),
    )
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("predictions", "inputs", "policy", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                run(args.predictions, args.inputs, args.policy, args.output_dir),
                indent=2,
            )
        )
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Policy replay stopped: {exc}\n")


if __name__ == "__main__":
    main()
