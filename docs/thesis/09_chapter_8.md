# 8 Discussion, Limitations and Conclusion

## 8.1 Answers to the Research Questions

### 8.1.1 Prediction Compared with a Constant Benchmark

The first question is whether information available at monthly decision dates predicts a new disclosure episode within 60 days better than a constant event rate. In the retrospective 2023–2025 evaluation, the selected forest has ROC-AUC 0.8866, average precision of 2.60% versus a 0.241% event share (10.77 lift), and 0.95% less Brier error. It therefore improves ranking substantially but probability accuracy only slightly.

Performance at one fixed alert threshold is limited. The forest produces 515 alerts: 29 are followed by a positive outcome and 486 are not. It misses 289 of the 318 positive company-months and detects at least one row for only 18 of 176 disclosure episodes. The threshold is therefore not suitable as a stand-alone decision rule.

### 8.1.2 Tree Models Compared with Logistic Regression

The second question compares tree models with logistic regression. Both trees rank better in the later evaluation, but their probability quality is inconsistent: random forest has 0.95% Brier skill, while XGBoost has −5.34% despite slightly higher ROC-AUC and average precision. The predefined rule selects the forest for its lower 2020–2022 Brier error.

The alternative-period sensitivity experiment selects XGBoost instead. The evidence therefore supports using tree models for ranking, but it does not establish one tree family as consistently superior across periods.

### 8.1.3 Converting Risk and Financial Capacity into a Limit

The third question concerns converting risk and capacity into a limit. The policy calculates capacity from revenue, positive operating cash flow, eligible cash and near-term debt payments, then applies a probability reduction and asset cap. Monthly rules phase in increases, apply reductions immediately and prevent automatic reopening after zero.

This produces a transparent and reproducible amount for each eligible company-month. It does not establish that the amount is economically optimal or safe because several facility inputs are assumed rather than observed.

### 8.1.4 Monthly Behavior and Alternative Policy Assumptions

The fourth question concerns monthly behavior and alternative assumptions. Among consecutive observations, 72.05% of limits are unchanged, 18.09% increase and 9.86% decrease; accounting values are often carried forward between filings. The cap determines 53.42% of preliminary limits.

Removing the probability-based risk adjustment increases mean limit/assets from 0.6678% to 0.6751%, a relative increase of 1.08%. Assumptions about eligible cash, near-term debt payments and the exposure cap have much larger effects. The policy results are therefore driven more strongly by financial-capacity and exposure assumptions than by the model probability at the aggregate level. Individual high-risk companies can still receive a larger probability-based reduction.

## 8.2 Contribution

The study combines SEC Company Facts, Financial Statement and Notes facts, and submissions in a point-in-time panel that preserves reporting periods, filing and availability dates, and sources.

The design evaluates ranking, probability error and fixed-threshold alerts separately because strong ranking does not ensure probabilities suitable for a monetary formula.

The separate policy layer uses explicit formulas and monthly rules while distinguishing observed data, model estimates and assumed facility inputs. Supporting code and evidence make the process reproducible.

## 8.3 Limitations

The outcome is a bankruptcy or reviewed payment-failure disclosure episode, not verified default on the hypothetical facility. Filing dates do not necessarily identify when financial distress or missed payment began. The 90-day episode gap is an operational grouping rule and does not verify recovery. Item 2.04 classification uses automated reviews, and the saved experiment does not contain an independent human-validation sample.

The outcome is rare, and accounting data contain missing values, inconsistent reporting and measurement noise. Although decisions are monthly, accounting inputs are normally quarterly or annual and can remain unchanged between filings. The policy replay also excludes 41,841 of 141,460 candidate company-months because required financial inputs are missing or invalid.

The population consists of SEC reporting companies and includes very large public businesses. It may not represent smaller private working-capital borrowers. Companies can appear in several chronological stages, so the evaluation reflects continued monitoring rather than performance on a completely separate borrower population.

The final experiment does not use 2023–2025 outcomes for fitting, tuning, calibration or selection. However, those years were examined during earlier development before the broader outcome was specified. The evaluation is retrospective rather than untouched external validation. The different model selected in the alternative-period experiment also shows that model choice is sensitive to the chronological periods used.

Company-cluster bootstrap intervals preserve dependence within each company but do not capture common economic shocks, model-selection uncertainty, changes in sample construction or errors in the disclosure labels. The small Brier improvement should therefore not be interpreted as precise validation of the probability scale.

The policy assumes that all reported cash is eligible, no additional external debt payment is due within 60 days, outstanding facility exposure is zero and the maximum exposure is 1% of assets. Actual commitments, utilization, repayments, contractual defaults, recoveries, losses, pricing, profitability and customer effects are unavailable. The replay cannot demonstrate that the calculated limits reduce losses or improve profit.

## 8.4 Further Work

Future work should prioritize four improvements:

1. **Validate the disclosure labels.** An independent human-reviewed sample should measure the accuracy of the automated Item 2.04 classifications and resolve ambiguous filings.
2. **Use prospective or independent evaluation.** The target, predictors, model settings and selection rules should be fixed before evaluation on a future period or an independent lender portfolio.
3. **Add borrower and facility data.** Unrestricted cash, debt-payment schedules, current utilization, repayments, arrears, contractual defaults, recoveries, losses, pricing and profitability would allow the policy to be tested against actual lending outcomes.
4. **Include timelier predictors.** Management accounts, bank transactions and point-in-time macroeconomic or market variables could capture recent borrower and systematic conditions. Every input should retain its measurement period, publication date, vintage and availability date.

These additions would support a facility-default target, more realistic capacity inputs and direct evaluation of whether limit changes improve lending outcomes. Probability calibration should then be monitored through a predefined process.

## 8.5 Conclusion

Public SEC accounting and filing data contain useful information for ranking near-term bankruptcy or payment-failure disclosure risk. The selected model ranks the rare outcome substantially better than a constant benchmark, but its improvement in probability error is small and its fixed alert threshold misses most disclosure episodes. The model does not estimate verified default on a lending facility.

The policy demonstrates how dated financial information and a disclosure probability can be converted into transparent monthly limits. The calculations are reproducible, but their results depend strongly on unobserved assumptions about eligible cash, debt payments and exposure caps. They are not shown to be optimal, safe or profitable.

The thesis therefore provides a research framework rather than a validated lending system. Its practical value can be established only with independently validated outcomes, actual facility data and prospective evaluation.
