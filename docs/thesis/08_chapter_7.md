# 7 Credit-Limit Policy Results

The 2023–2025 replay combines SEC accounts, random-forest probabilities and hypothetical facility assumptions. It tests rule behavior, not observed lending decisions.

## 7.1 Replay Sample and Reference Assumptions

The replay requires valid point-in-time financial inputs and probability, but no future label:

| Policy-sample step | Company-months |
|---|---:|
| Candidate financial observations | 141,460 |
| Missing required revenue, operating cash flow, cash or assets | −41,799 |
| Invalid required financial values | −42 |
| Included in the policy replay | 99,619 |

*Table 18. Construction of the policy-replay sample.*

The 99,619 included rows cover 3,869 companies. Among candidates, 29.6% lack required, non-imputed values. The included rows form 5,176 consecutive-month segments. After a gap, a new segment begins as a hypothetical initial assessment, only as a replay convention.

This sample differs from later model evaluation because policy calculation does not require an outcome observable 60 days afterward. It instead requires the financial amounts needed to assign money, which explains why its inclusion rules and row count are reported separately.

The reference, or base, scenario uses the following assumptions:

| Input or policy rule | Reference assumption |
|---|---:|
| Probability model | Selected random forest |
| Reported cash treated as eligible | 100% |
| Additional external debt payment due within 60 days | Zero |
| Maximum exposure | 1% of reported assets |
| Outstanding facility exposure | Zero |
| Risk sensitivity | $$k=10$$ |
| Increase smoothing | 50% |
| Maximum monthly increase | 10% |
| Increase deadband | 2% |

*Table 19. Reference policy assumptions.*

Revenue, cash flow, cash and assets are observed. Cash eligibility, debt payments, cap and facility exposure are assumptions. The reference is not an optimal standard.

## 7.2 Reference-Scenario Results

The reference policy produces the following results:

| Outcome | Reference result |
|---|---:|
| Mean assigned limit | USD 55.09 million |
| Median assigned limit | USD 4.23 million |
| Mean assigned limit / assets | 0.668% |
| Zero-limit share | 3.55% |
| Known-disclosure hard-stop rows | 262 |
| Preliminary limit determined by the exposure cap | 53.42% |
| Mean absolute monthly change / assets | 0.0290% |

*Table 20. Reference-scenario credit-limit results.*

Large public companies raise the mean above the median, so neither represents a typical small private borrower. The 0.668% figure averages row-level limit/assets ratios. Zeros arise from capacity, hard stops or non-reopening. The 262 hard-stop rows are not distinct companies or episodes. The 1%-of-assets cap binds in 53.42% of rows.

Frequent cap binding also explains why probability changes have a modest aggregate effect: when the cap is already below risk-adjusted capacity, a small movement in probability leaves the preliminary limit unchanged. Probability matters more where capacity rather than the cap binds.

The replay contains 94,443 transitions between consecutive months within the same company segment:

| Monthly result | Transitions | Share |
|---|---:|---:|
| Increase | 17,088 | 18.09% |
| Decrease | 9,309 | 9.86% |
| No change | 68,046 | 72.05% |

*Table 21. Monthly transitions under the reference policy.*

Most limits are unchanged because statements are carried forward. Gaps are not transitions.

The remaining changes can reflect a new financial filing, a probability update, a change in the asset cap or state carried by the monthly rules. Counting only consecutive observations avoids treating a post-gap initial assessment as an ordinary monthly movement.

## 7.3 Sensitivity to Policy Assumptions

Each sensitivity changes one assumption on the same observations.

| Scenario | Meaning | Mean limit / assets | Zero-limit share |
|---|---|---:|---:|
| Reference policy | Assumptions listed in Section 7.1 | 0.668% | 3.55% |
| No probability-based risk adjustment | Removes the exponential reduction but retains the cap, monthly rules and hard stops | 0.675% | 3.55% |
| 50% of reported cash eligible | Treats half of reported cash as available | 0.593% | 3.55% |
| No reported cash eligible | Excludes reported cash from the capacity proxy | 0.312% | 48.30% |
| Exposure cap: 0.5% of assets | Reduces the maximum exposure from 1% to 0.5% of assets | 0.388% | 3.55% |
| Exposure cap: 2% of assets | Raises the maximum exposure from 1% to 2% of assets | 0.954% | 3.55% |
| 60-day debt payment: 0.5% of assets | Deducts an assumed near-term payment equal to 0.5% of assets | 0.429% | 36.48% |
| Stronger risk reduction, $$k=20$$ | Doubles the sensitivity of the limit to the estimated probability | 0.659% | 3.55% |

*Table 22. Sensitivity of policy results to alternative assumptions.*

Removing probability reduction raises mean limit/assets only from 0.6678% to 0.6751%, as probabilities are low and the cap often binds. By contrast, no eligible cash raises zero limits to 48.30%, and a debt deduction of 0.5% of assets raises them to 36.48%. Cap changes also have large effects. These are sensitivities to unobserved assumptions, not borrower facts. Alternative model probabilities barely change the mean. The values are 0.6678% for random forest, 0.6658% for XGBoost and 0.6669% for logistic, although individual limits may differ.

The comparison identifies which inputs would merit the strongest evidence in a real application. Cash eligibility and contractual payment schedules must be measured borrower by borrower. An aggregate similarity across probability models cannot compensate for uncertainty in those capacity inputs.

Figure 3 compares scenarios on identical historical observations.

![Policy sensitivity](figures/policy_sensitivity.png)

*Figure 3. Policy sensitivity.*

## 7.4 Effect of the Monthly Update Rules

Two benchmarks isolate monthly safeguards:

| Monthly-rule version | Mean limit / assets | Mean absolute monthly change / assets |
|---|---:|---:|
| Reference policy | 0.6678% | 0.02904% |
| Keep each segment's initial limit | 0.6786% | 0.02107% |
| Apply each month's preliminary limit without smoothing | 0.7399% | 0.04227% |

*Table 23. Effect of alternative monthly update rules.*

Keeping each segment's initial limit reduces movement but exceeds the current preliminary limit in 19.80% of rows. Applying each preliminary limit directly increases movement and can reopen after zero. The reference instead phases in increases, applies reductions immediately and bars automatic reopening.

These benchmarks show the trade-off between stability and responsiveness. Fewer changes are not inherently safer if the retained limit exceeds current support, while immediate application can create operationally costly increases and decreases.

## 7.5 Scope of the Evidence

Results are conditional on full cash eligibility, no additional 60-day debt payment, a 1%-of-assets cap and zero facility exposure. Thus, assigned limit equals available credit only in this replay. A zero blocks new credit but does not repay existing exposure. The replay has no actual commitments, utilization, repayments, losses, pricing, decisions or customer effects. It also uses a disclosure rather than facility-default target. It therefore cannot establish suitability, loss reduction or profit.
