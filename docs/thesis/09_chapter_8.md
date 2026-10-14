# 8 Discussion, Limitations and Conclusion

## 8.1 Main Findings

The primary model experiment selects a random forest with raw probabilities. In the 2023–2025 evaluation, it reaches ROC-AUC 0.8866, average precision 0.02599 and Brier score 0.0023840. The Brier improvement over the constant benchmark is small. At the frozen threshold, precision is 5.63% and recall is 9.12%, with 18 of 176 episodes detected. The ranking signal requires further validation before use in lending decisions.

The policy replay translates probabilities into monthly limits. Capacity assumptions and caps have a larger aggregate effect than the risk multiplier, which reduces mean limit/assets by 1.08% relative to the capacity-only scenario. These results describe rule behavior, not improved lending outcomes.

## 8.2 Contribution

The research links dated SEC records, a 60-day disclosure-episode label, chronological model development and an auditable credit rule. It evaluates ranking, probability error, threshold detection and monetary outputs separately.

Company Facts and Financial Statement and Notes facts form a single accounting panel. Filing-date availability, consistent reporting periods and recorded source provenance make the financial inputs traceable at each decision date.

## 8.3 Limitations

The target is a bankruptcy or reviewed payment-failure disclosure episode. Filing dates and the 90-day episode gap do not establish the precise onset or cure of contractual default. Neither disclosure type verifies default on the proposed facility. Item 2.04 classification uses automated reviews; no independent human validation sample is documented in the saved run.

The rare outcome, missing accounting values, reporting noise and sample exclusions limit generalization. Company-cluster bootstrap intervals account for dependence within companies but omit common calendar shocks and uncertainty from model and target selection.

Although the final run excludes 2023–2025 from model development, earlier project versions examined those years before the broader target was specified. The evaluation is retrospective rather than untouched external validation.

The policy assumes initial limits, cash eligibility, additional debt and facility exposure. Actual utilization, repayments, contractual defaults, recoveries, losses, pricing and customer outcomes are unavailable. The simulation cannot demonstrate higher profit or lower realized credit loss.

## 8.4 Further Work

A stronger study should independently validate a sample of automated disclosure reviews, resolve ambiguous filings and improve accounting reconciliation. This would improve confidence in both the outcome labels and the financial predictors.

The predictor set could be extended with macroeconomic indicators such as interest rates, inflation, unemployment, industrial production growth and credit spreads. These variables would represent the economic conditions shared by companies at each monthly decision date. Their interactions with company characteristics could also be examined, for example whether interest-rate changes are more informative for highly indebted firms. Each value must be aligned with its publication date and the version available at that time, since subsequently revised data would introduce future information. Added predictive value should be assessed against the accounting-only model using the same chronological evaluation periods.

A further priority is a richer monthly dataset. The current panel has monthly decision dates, but its accounting inputs can remain unchanged between filings and its flow measures use the last reported annual period. Where access permits, future work could combine monthly management accounts and bank transactions with sales, operating cash flow, receivables and payables, unrestricted cash, debt-payment schedules and facility utilization. Dated payment records could establish when arrears begin, whether obligations are repaid and when a borrower recovers. Such information would support more timely predictors, clearer episode boundaries and better measurement of the resources available for repayment. Each company-month should retain the source, measurement period and availability date of every input, with explicit treatment of missing or delayed reports.

Direct facility data would also allow evaluation of payment risk, limit changes, losses and profitability under realistic operational constraints. The expanded target definition, predictor set and selection rules should be fixed before evaluation on a future period or an independent lender portfolio. Probability calibration should then be monitored through a predefined process.

## 8.5 Conclusion

Public accounting and filing data provide a ranking signal for near-term bankruptcy or payment-failure disclosures. The analysis uses one panel combining Company Facts and Financial Statement and Notes facts. Threshold detection is limited, and the model does not estimate verified facility-default probability.

The policy layer provides transparent, reproducible limit calculations and identifies influential assumptions. Its practical value remains to be tested with facility outcomes and independent validation.
