"""Exercise the full workflow with generated data: NEVER empirical thesis results.

The fixture generates latent monthly states, feature values, and subsequent random
events. Company cohorts differ between stages; rows repeat within each cohort.
It is a software fixture, not a calibrated corporate-default simulator.
"""

import argparse
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from backtest_policy import INPUT_FIELDS, run as replay
from build_panel import PANEL_FIELDS
from make_figures import figures
from predict_monthly import predict
from research_common import FEATURES, months, new_output, write_csv, write_json
from train_models import run as train


def fixture(output, companies_per_cohort=100):
    """Write reproducible synthetic histories that exercise every chronological stage."""
    output = Path(output)
    config = dict(
        design_status="fixed",
        data_kind="synthetic",
        event_type="synthetic_adverse_event",
        event_definition="Generated first event from a latent-state fixture; not a real default definition",
        horizon_days=60,
        start="2016-01-01",
        end="2021-10-01",
        tuning_start="2018-01-01",
        calibration_start="2019-01-01",
        selection_start="2020-01-01",
        test_start="2021-01-01",
        observed_as_of="2022-01-01",
        features=list(FEATURES),
        max_balance_age_days=180,
        max_flow_age_days=540,
        min_class_count=5,
        min_event_companies=5,
        bootstrap_repeats=30,
        seed=42,
    )
    rng = random.Random(42)
    rows, all_features, event_dates = [], [], {}
    for cohort, year in enumerate(range(2016, 2022)):
        dates = list(months(date(year, 1, 1), date(year, 12, 1)))
        for company_index in range(companies_per_cohort):
            company = f"synthetic_{cohort:02d}_{company_index:04d}"
            state, event, sequence = rng.gauss(0, 1), None, []
            for decision in dates:
                state = 0.75 * state + rng.gauss(0, 0.65)
                features = dict(
                    current_ratio=max(0.01, 2 - 0.6 * state + rng.gauss(0, 0.1)),
                    cash_only_to_assets=max(
                        0.0, 0.12 - 0.04 * state + rng.gauss(0, 0.01)
                    ),
                    cash_and_equivalents_to_assets=max(
                        0.0, 0.16 - 0.045 * state + rng.gauss(0, 0.01)
                    ),
                    working_capital_to_assets=0.15 - 0.15 * state + rng.gauss(0, 0.02),
                    return_on_average_assets=0.06 - 0.08 * state + rng.gauss(0, 0.01),
                    operating_cashflow_to_average_assets=(
                        0.08 - 0.07 * state + rng.gauss(0, 0.01)
                    ),
                    log_assets=18 - 0.2 * state + rng.gauss(0, 1),
                )
                # Independent feature missingness exercises training-only imputation.
                if rng.random() < 0.08:
                    features["current_ratio"] = ""
                sequence.append((decision, features))
                hazard = 1 / (1 + math.exp(3.4 - 2.6 * state))
                if event is None and rng.random() < hazard:
                    event = decision + timedelta(days=14)
            event_dates[company] = event
            for decision, features in sequence:
                if decision > date.fromisoformat(config["end"]):
                    continue
                all_features.append(
                    dict(
                        company_id=company,
                        decision_date=str(decision),
                        data_kind="synthetic",
                        feature_available_on=str(decision - timedelta(days=1)),
                        **features,
                    )
                )
                if event is not None and event <= decision:
                    continue
                end = decision + timedelta(days=60)
                label = int(event is not None and event <= end)
                rows.append(
                    dict(
                        company_id=company,
                        decision_date=str(decision),
                        data_kind="synthetic",
                        event_type=config["event_type"],
                        horizon_days=60,
                        horizon_end=str(end),
                        label_available_on=str(end + timedelta(days=1)),
                        label=label,
                        event_id=f"{company}:{event}" if label else "",
                        label_source="synthetic://generated-event",
                        coverage_source="synthetic://complete-fixture",
                        balance_period_end=str(decision - timedelta(days=90)),
                        flow_period_end=str(decision - timedelta(days=90)),
                        balance_age_days=90,
                        flow_age_days=90,
                        feature_available_on=str(decision - timedelta(days=1)),
                        flow_basis="synthetic_annual_fixture",
                        **features,
                    )
                )
    write_json(output / "design.json", config)
    write_csv(output / "panel.csv", rows, PANEL_FIELDS)
    write_csv(output / "features.csv", all_features)
    write_csv(
        output / "synthetic_events.csv",
        [
            dict(company_id=c, event_date=str(d) if d else "")
            for c, d in event_dates.items()
        ],
    )
    (output / "SYNTHETIC_ONLY.txt").write_text(
        "Generated software-test data. No observations, probabilities or results in this directory describe real companies.\n"
    )
    return config, rows, event_dates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = new_output(args.output_dir)
    _, _, event_dates = fixture(output)
    selection = train(
        output / "design.json", output / "panel.csv", output / "models", smoke=True
    )
    policy_dir = None
    if selection["selected_model"] is not None:
        predictions = predict(
            output / "models" / "models.joblib",
            output / "features.csv",
            output / "predictions",
        )
        inputs, seen = [], set()
        for row in sorted(
            predictions, key=lambda r: (r["company_id"], r["decision_date"])
        ):
            company = row["company_id"]
            stopped = event_dates[company] is not None and event_dates[
                company
            ] <= date.fromisoformat(row["decision_date"])
            # All facility/cash/debt inputs are explicit hypothetical assumptions.
            inputs.append(
                dict(
                    company_id=company,
                    decision_date=row["decision_date"],
                    currency="USD",
                    revenue_annual=12000000,
                    operating_cashflow_annual=1200000,
                    eligible_cash=500000,
                    external_debt_service_60d=50000,
                    hard_cap=150000,
                    outstanding_exposure=20000,
                    initial_limit=70000 if company not in seen else "",
                    information_changed=True,
                    hard_stop=stopped,
                    reopen=False,
                    inputs_available_on=row["decision_date"],
                    assessment_status="blocked" if stopped else "eligible",
                    input_basis="assumed",
                    input_source="synthetic://fixed-policy-scenario",
                )
            )
            seen.add(company)
        write_csv(output / "policy_inputs.csv", inputs, INPUT_FIELDS)
        policy_dir = output / "policy"
        replay(
            output / "predictions" / "policy_predictions.csv",
            output / "policy_inputs.csv",
            Path(__file__).parent / "configs" / "policy.example.json",
            policy_dir,
        )
    figures(output / "models", output / "figures", policy_dir)
    print(
        json.dumps(
            {
                "output_dir": str(output),
                "status": "synthetic_software_check_only",
                "selected_model": selection["selected_model"],
            }
        )
    )


if __name__ == "__main__":
    main()
