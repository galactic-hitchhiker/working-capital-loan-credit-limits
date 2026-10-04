"""Reproduce Chapter 5 examples and parameter scenarios; NOT empirical results."""

import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path

from mcf.policy.credit import PolicyConfig, PolicyInputs, determine_limit


def examples():
    """Change one aspect of a hypothetical borrower per case; cases are independent."""
    base = PolicyInputs(
        12_000_000,
        1_200_000,
        500_000,
        50_000,
        0.02,
        150_000,
        outstanding_exposure=60_000,
        previous_limit=70_000,
    )
    cases = {
        "base": base,
        "risk_stress": replace(base, risk_probability=0.08),
        "cashflow_stress": replace(base, operating_cashflow_annual=600_000),
        "lower_hard_cap": replace(base, hard_cap=40_000),
        "no_new_information": replace(base, information_changed=False),
        "hard_stop": replace(base, hard_stop=True),
    }
    return [
        {"scenario": name, **asdict(x), **asdict(determine_limit(x))}
        for name, x in cases.items()
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("results/policy"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = examples()
    for filename, data in [("worked_examples.csv", rows)]:
        with (args.output_dir / filename).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    base = PolicyInputs(
        12_000_000,
        1_200_000,
        500_000,
        50_000,
        0.02,
        150_000,
        outstanding_exposure=0,
        previous_limit=70_000,
    )
    sensitivity = []
    for risk_sensitivity in (5.0, 10.0, 20.0):
        for risk_probability in (0.0, 0.01, 0.02, 0.05, 0.08, 0.10):
            result = determine_limit(
                replace(base, risk_probability=risk_probability),
                PolicyConfig(risk_sensitivity=risk_sensitivity),
            )
            sensitivity.append(
                {
                    "illustrative": True,
                    "risk_sensitivity": risk_sensitivity,
                    "risk_probability": risk_probability,
                    **asdict(result),
                }
            )
    with (args.output_dir / "sensitivity.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sensitivity[0]))
        writer.writeheader()
        writer.writerows(sensitivity)
    (args.output_dir / "policy_config.json").write_text(
        json.dumps(
            {
                "status": "Illustrative research assumptions; not fitted or validated lending parameters",
                "config": asdict(PolicyConfig()),
                "currency": "USD",
                "risk_target": "illustrative_event",
                "risk_horizon_days": 60,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "examples": len(rows),
                "sensitivity_cases": len(sensitivity),
                "status": "illustrative_only",
            }
        )
    )


if __name__ == "__main__":
    main()
