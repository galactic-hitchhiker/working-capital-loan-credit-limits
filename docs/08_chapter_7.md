# 7 Credit-Limit Policy Results

The policy translates the run 006 random forest's 60-day disclosure probability into a monthly credit limit. It replays historical SEC financial information under stated facility assumptions. The source data do not contain actual commitments, utilization, repayments, losses, pricing or profitability.

## 7.1 Policy Rule

For each eligible company-month, raw capacity is the smaller of a cash-based and sales-based amount. A risk multiplier reduces capacity as predicted disclosure risk rises. An asset-based cap and monthly update safeguards determine the assigned limit. A known qualifying disclosure activates a hard stop during the episode quiet gap.

The policy uses the continuous probability. The frozen classification threshold in Chapter 6 is only an evaluation convention.

## 7.2 Base Scenario

After excluding rows with missing or invalid required policy inputs, the run 006 replay covers 99,619 company-months from 3,869 companies and 5,176 continuous company segments in 2023–2025.

| Outcome | Base result |
|---|---:|
| Mean limit | USD 55.09 million |
| Median limit | USD 4.23 million |
| Mean limit / assets | 0.668% |
| Zero-limit share | 3.55% |
| Hard-stop observations | 262 |
| Cap-binding share | 53.42% |
| Mean absolute monthly change / assets | 0.0290% |

Among 94,443 month-to-month transitions, 17,088 are increases, 9,309 are decreases and 68,046 are unchanged. A missing month starts a new hypothetical assessment, so change statistics do not bridge gaps. The recorded reasons include unchanged inputs, phased increases, immediate reductions and hard stops.

![Policy sensitivity](figures/policy_sensitivity.png)

*Figure 7.1. Base policy and selected sensitivity scenarios. Source: run 006 policy replay.*

## 7.3 Sensitivity

The average limit changes most when assumptions affecting capacity and the cap change:

| Scenario | Mean limit / assets | Zero-limit share |
|---|---:|---:|
| Base | 0.668% | 3.55% |
| Capacity only | 0.675% | 3.55% |
| Eligible cash halved | 0.593% | 3.55% |
| No eligible cash | 0.312% | 48.30% |
| Exposure cap 0.5% of assets | 0.388% | 3.55% |
| Exposure cap 2.0% of assets | 0.954% | 3.55% |
| Additional debt due 0.5% of assets | 0.429% | 36.48% |
| Risk sensitivity doubled | 0.659% | 3.55% |

Using another fitted model changes the mean less under this policy: random forest gives 0.6678% of assets, XGBoost 0.6658% and either logistic model 0.6669%. This aggregate pattern reflects frequent capacity and cap constraints. It does not show that the risk model is unimportant for an individual company.

The fixed initial-limit assumption exceeds current raw capacity in 19.80% of included rows. The replay is therefore a study of rule behavior, not a recommended starting portfolio.

## 7.4 Scope of the Evidence

The reported limits are conditional outputs from an assumed policy. A zero limit does not remove an outstanding balance. The simulation cannot estimate expected loss, profitability, approval rates or customer effects without facility-level data. The probability refers to a bankruptcy or payment-failure disclosure episode, not verified contractual default. The limits are not shown to be optimal or ready for production use.

File references: results/run_006_full_statement_enrichment/policy/ and policy_report/; policy code in mcf/policy/credit.py and mcf/policy/empirical.py.
