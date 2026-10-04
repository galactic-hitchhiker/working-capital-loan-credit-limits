"""One-at-a-time policy parameter scenarios on the same monthly inputs.

These are policy alternatives, not independently estimated optimal parameters.
Each scenario starts from the same supplied initial conditions and replays its
own previous limits. Probability, facility utilization and borrower behavior are
held fixed, so comparisons do not estimate behavioral or causal effects.
"""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from mcf.policy.backtest import INPUT_FIELDS, replay
from mcf.policy.credit import PolicyConfig
from mcf.common import manifest, new_output, read_csv, write_csv, write_json


def scenarios(base):
    """Yield the base first, then change exactly one coefficient per scenario."""
    yield "base", base
    for field, values in {
        "revenue_fraction": (0.1, 0.3),
        "cashflow_fraction": (0.25, 0.75),
        "cash_fraction": (0.05, 0.15),
        "risk_sensitivity": (5.0, 20.0),
        "increase_smoothing": (0.25, 1.0),
        "monthly_increase_cap": (0.05, 0.2),
        "increase_deadband": (0.0, 0.05),
    }.items():
        for value in values:
            yield f"{field}_{value:g}", replace(base, **{field: value})


def run(prediction_path, input_path, policy_path, output):
    """Replay each alternative independently on identical predictions and inputs."""
    predictions, inputs = read_csv(prediction_path), read_csv(input_path, INPUT_FIELDS)
    base = PolicyConfig(**json.loads(Path(policy_path).read_text())["parameters"])
    output = new_output(output)
    summaries, paths, configs = [], [], {}
    for name, policy in scenarios(base):
        rows, unused = replay(predictions, inputs, policy)
        changes = [r["limit_change"] for r in rows if r["limit_change"] is not None]
        summaries.append(
            dict(
                scenario=name,
                rows=len(rows),
                data_kind=rows[0]["data_kind"],
                currency=rows[0]["currency"],
                mean_assigned_limit=sum(r["assigned_limit"] for r in rows) / len(rows),
                mean_absolute_change=(
                    sum(abs(d) for d in changes) / len(changes) if changes else None
                ),
                increases=sum(d > 0 for d in changes),
                decreases=sum(d < 0 for d in changes),
                exposure_above_limit_rows=sum(r["excess_exposure"] > 0 for r in rows),
                unused_predictions=unused,
            )
        )
        paths.extend(
            dict(
                scenario=name,
                company_id=r["company_id"],
                decision_date=r["decision_date"],
                assigned_limit=r["assigned_limit"],
                available_credit=r["available_credit"],
                excess_exposure=r["excess_exposure"],
            )
            for r in rows
        )
        configs[name] = asdict(policy)
    write_csv(output / "policy_sensitivity.csv", summaries)
    write_csv(output / "scenario_paths.csv", paths)
    write_json(output / "scenario_parameters.json", configs)
    write_json(
        output / "manifest.json",
        manifest(
            [prediction_path, input_path, policy_path],
            data_kind=summaries[0]["data_kind"],
            scenarios=len(summaries),
            note="One-at-a-time policy assumptions; borrower behavior and probabilities held fixed",
        ),
    )
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("predictions", "inputs", "policy", "output-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.predictions, args.inputs, args.policy, args.output_dir)
    print(f"Saved {len(result)} parameter scenarios")
