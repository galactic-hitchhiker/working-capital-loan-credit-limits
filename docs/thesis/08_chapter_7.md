# 7 Credit-Limit Policy Results

The policy translates the primary model experiment's random-forest 60-day disclosure probability into a monthly credit limit. It replays historical SEC financial information under stated facility assumptions. The source data do not contain actual commitments, utilization, repayments, losses, pricing or profitability.

## 7.1 Replay Design

The replay applies the capacity, risk, cap and monthly update rules in Chapter 5. It uses continuous probabilities and the stated assumptions about cash eligibility, debt payments and facility exposure.

## 7.2 Base Scenario

After excluding rows with missing or invalid required policy inputs, the primary model experiment's policy replay covers 99,619 company-months from 3,869 companies and 5,176 continuous company segments in 2023–2025.

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

*Figure 7.1. Base policy and selected sensitivity scenarios. Source: primary model experiment policy replay.*

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

The risk adjustment reduces mean limit/assets from 0.6751% in the capacity-only scenario to 0.6678% in the base scenario: 0.0073 percentage points, or 1.08% relative. Capacity assumptions and caps have a larger aggregate effect in these scenarios. This comparison measures policy behavior, not a lending benefit.

Using another fitted model changes the mean little: random forest gives 0.6678% of assets, XGBoost 0.6658% and either logistic model 0.6669%. Aggregate means can conceal larger differences for individual companies.

The fixed initial-limit assumption exceeds current raw capacity in 19.80% of included rows. The replay is therefore a study of rule behavior, not a recommended starting portfolio.

## 7.4 Scope of the Evidence

The reported limits are conditional outputs from an assumed policy. A zero limit does not remove an outstanding balance. The simulation cannot estimate expected loss, profitability, approval rates or customer effects without facility-level data. The probability refers to a bankruptcy or payment-failure disclosure episode, not verified contractual default. The limits are not shown to be optimal or ready for production use.
