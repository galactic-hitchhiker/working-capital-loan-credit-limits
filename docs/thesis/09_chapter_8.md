# 8 Discussion, Limitations and Conclusion

## 8.1 Answers to the Research Questions

### 8.1.1 Prediction Compared with a Constant Benchmark

The first question asks whether financial information available at monthly decision dates can predict a new bankruptcy or payment-failure disclosure episode within 60 days better than a constant event-rate benchmark.

In the retrospective 2023–2025 evaluation, the selected random forest provides substantially better ranking and slightly lower probability error. Its ROC-AUC is 0.8866. Its average precision is 2.60%, compared with an event share of 0.241%, giving an AP lift of 10.77. Its Brier error is 0.95% lower than the constant benchmark. The results therefore show useful ranking information, but only a small improvement in probability accuracy.

Performance at one fixed alert threshold is limited. The forest produces 515 alerts: 29 are followed by a positive outcome and 486 are not. It misses 289 of the 318 positive company-months and detects at least one row for only 18 of 176 disclosure episodes. The threshold is therefore not suitable as a stand-alone decision rule.

### 8.1.2 Tree Models Compared with Logistic Regression

The second question asks whether random forest and XGBoost improve prediction compared with logistic regression under the same chronological design.

Both tree models rank the outcome better than the logistic models in the later evaluation. However, their probability quality is less consistent. The random forest has positive Brier skill of 0.95%, while XGBoost has negative Brier skill of −5.34% despite its slightly higher ROC-AUC and average precision. The predefined selection rule chooses the random forest because it has the lower Brier error during the 2020–2022 selection period.

The alternative-period sensitivity experiment selects XGBoost instead. The evidence therefore supports using tree models for ranking, but it does not establish one tree family as consistently superior across periods.

### 8.1.3 Converting Risk and Financial Capacity into a Limit

The third question asks how the estimated probability can be combined with financial capacity and an exposure cap to produce a monetary limit.

The proposed policy first calculates a capacity proxy from revenue, positive operating cash flow, eligible cash and near-term debt payments. It then applies a probability-based reduction and an asset-based exposure cap. Monthly rules phase in supported increases, apply reductions immediately and prevent automatic reopening after a zero limit without a new assessment.

This produces a transparent and reproducible amount for each eligible company-month. It does not establish that the amount is economically optimal or safe because several facility inputs are assumed rather than observed.

### 8.1.4 Monthly Behavior and Alternative Policy Assumptions

The fourth question asks how limits respond to new information, estimated risk and alternative policy assumptions.

Among consecutive observations, 72.05% of limits remain unchanged, 18.09% increase and 9.86% decrease. The high unchanged share is expected because accounting values are often carried forward between SEC reports rather than refreshed every month. The exposure cap determines the preliminary limit in 53.42% of observations.

Removing the probability-based risk adjustment increases mean limit/assets from 0.6678% to 0.6751%, a relative increase of 1.08%. Assumptions about eligible cash, near-term debt payments and the exposure cap have much larger effects. The policy results are therefore driven more strongly by financial-capacity and exposure assumptions than by the model probability at the aggregate level. Individual high-risk companies can still receive a larger probability-based reduction.

## 8.2 Contribution

The study combines SEC Company Facts, Financial Statement and Notes facts, and submissions in one accounting panel. Each observation retains its reporting period, filing date, availability date and source, allowing the information available at a monthly decision date to be reconstructed.

The modeling design evaluates ranking, probability error and fixed-threshold alerts separately. This distinction is important because a model can rank companies well while producing probabilities that are unsuitable for direct use in a monetary formula.

The policy layer is also separate from the prediction model. It converts the estimated probability and financial inputs into a limit through explicit formulas and monthly rules. Observed accounting data, model estimates and assumed facility inputs remain distinguishable. The supporting code and saved evidence make the process auditable and reproducible.

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
4. **Include more timely firm-level and macroeconomic predictors.** Monthly management accounts and bank transactions could provide fresher company information. Macroeconomic and financial-market variables, such as interest rates, GDP growth, inflation, unemployment, credit spreads and sector-specific indicators, could capture systematic conditions affecting corporate liquidity and payment-failure risk. Every input should retain its measurement period, publication date, data vintage and availability date so that only information available on each decision date is used.

These additions would support a facility-default target, more realistic capacity inputs and direct evaluation of whether limit changes improve lending outcomes. Probability calibration should then be monitored through a predefined process.

## 8.5 Conclusion

Public SEC accounting and filing data contain useful information for ranking near-term bankruptcy or payment-failure disclosure risk. The selected model ranks the rare outcome substantially better than a constant benchmark, but its improvement in probability error is small and its fixed alert threshold misses most disclosure episodes. The model does not estimate verified default on a lending facility.

The policy demonstrates how dated financial information and a disclosure probability can be converted into transparent monthly limits. The calculations are reproducible, but their results depend strongly on unobserved assumptions about eligible cash, debt payments and exposure caps. They are not shown to be optimal, safe or profitable.

The thesis therefore provides a research framework rather than a validated lending system. Its practical value can be established only with independently validated outcomes, actual facility data and prospective evaluation.
