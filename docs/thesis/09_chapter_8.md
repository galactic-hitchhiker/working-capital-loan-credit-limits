# 8 Discussion, Limitations and Conclusion

## 8.1 Answers to the Research Questions

### 8.1.1 Prediction Compared with a Constant Benchmark

In retrospective 2023–2025 evaluation, the forest achieves ROC-AUC 0.8866, average precision 2.60% versus a 0.241% event share (10.77 lift), and 0.95% less Brier error than the constant. Ranking improves substantially but probability error only slightly. Its 515 fixed-threshold alerts include 29 positives, while 289 of 318 positive rows and 158 of 176 episodes receive no prior alert. The threshold is not a stand-alone rule.

The evidence therefore answers the first question differently depending on the intended use. It supports prioritizing observations for review, but gives only weak evidence that the numerical probability is more accurate than a constant rare-event rate.

### 8.1.2 Tree Models Compared with Logistic Regression

Both trees rank better than logistic regression, but probability quality differs: random forest has 0.95% Brier skill while XGBoost has −5.34% despite slightly better ranking. The rule selects the forest on 2020–2022 Brier error, whereas the alternative period selects XGBoost. Trees aid ranking, but neither is consistently superior.

This result also illustrates why model family should not be chosen from ROC-AUC alone. A flexible model can order cases effectively while producing a probability scale unsuitable for direct monetary use.

### 8.1.3 Converting Risk and Financial Capacity into a Limit

The policy derives capacity from revenue, positive operating cash flow, eligible cash and near-term debt payments, then applies probability reduction, an asset cap and asymmetric monthly rules. The result is transparent and reproducible, not proven optimal or safe because facility inputs are assumed.

Its value is therefore procedural: it makes each assumption visible, preserves intermediate amounts and supplies a reason for every change. Such transparency allows lender-specific inputs and tolerances to replace research assumptions later.

### 8.1.4 Monthly Behavior and Alternative Policy Assumptions

Among transitions, 72.05% are unchanged, 18.09% increase and 9.86% decrease. The cap binds in 53.42% of rows. Removing risk adjustment raises mean limit/assets only from 0.6678% to 0.6751%, while cash eligibility, debt payments and the cap matter much more. Aggregate limits are thus driven primarily by capacity and exposure assumptions, although probability can matter for individual high-risk firms.

The dominance of capacity assumptions is economically plausible because the model predicts a very rare event and more than half of preliminary limits are capped. It also warns against investing in marginal model improvements while leaving repayment-capacity inputs unmeasured.

## 8.2 Contribution

The contribution is a reproducible point-in-time SEC panel and a separate policy layer that distinguishes observed data, model estimates and facility assumptions. Ranking, probability error and alerts are evaluated separately because ranking alone does not validate probabilities for a monetary formula.

Together, these elements form an end-to-end research design rather than only a prediction exercise. The same audit trail can support later replacement of disclosure labels and scenario inputs with lender outcomes without changing the conceptual separation between estimation and policy.

## 8.3 Limitations

The outcome is a disclosure episode, not verified facility default. Filing dates may lag distress, the 90-day grouping gap does not prove recovery, and automated Item 2.04 review lacks independent human validation.

The rare outcome and accounting data contain missingness, inconsistency and noise. Quarterly or annual inputs remain unchanged between monthly decisions, and the replay excludes 41,841 of 141,460 candidate rows for invalid or missing inputs.

Large SEC issuers may not represent smaller private borrowers. Company overlap across stages also makes this a monitoring evaluation, not a new-borrower sample.

Although 2023–2025 outcomes do not enter final development, those years were examined earlier, making evaluation retrospective. Alternative-period selection also shows temporal sensitivity.

Bootstrap intervals preserve within-company dependence but omit common shocks, selection and sample-construction uncertainty, and label error. The small Brier gain is not precise probability validation.

Policy assumptions include full cash eligibility, no additional 60-day debt payment, zero facility exposure and a 1%-of-assets cap. Without actual commitments, utilization, repayments, defaults, recoveries, losses, pricing, profitability or customer effects, the replay cannot demonstrate lender benefit.

These limitations are related rather than independent. Target noise affects probability estimation, probability uncertainty affects the risk multiplier, and missing facility data prevents observing whether the resulting amount would have changed exposure or loss.

## 8.4 Further Work

Four improvements have priority:

1. **Validate the disclosure labels.** An independent human-reviewed sample should measure the accuracy of the automated Item 2.04 classifications and resolve ambiguous filings.
2. **Use prospective or independent evaluation.** The target, predictors, model settings and selection rules should be fixed before evaluation on a future period or an independent lender portfolio.
3. **Add borrower and facility data.** Unrestricted cash, debt-payment schedules, current utilization, repayments, arrears, contractual defaults, recoveries, losses, pricing and profitability would allow the policy to be tested against actual lending outcomes.
4. **Include timelier predictors.** Management accounts, bank transactions and point-in-time macroeconomic or market variables could capture recent borrower and systematic conditions. Every input should retain its measurement period, publication date, vintage and availability date.

These additions would enable a facility-default target, realistic capacity inputs and direct lending evaluation, with predefined calibration monitoring.

## 8.5 Conclusion

SEC data usefully rank near-term disclosure risk, but probability-error improvement is small and the fixed threshold misses most episodes. The transparent monthly policy depends strongly on unobserved cash, debt-payment and cap assumptions and is not shown optimal, safe or profitable. It is a research framework, not a validated lending system. Practical value requires validated outcomes, facility data and prospective evaluation.
