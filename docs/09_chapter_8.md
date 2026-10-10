# 8 Discussion, Limitations and Conclusion

## 8.1 Main Findings

Run 006 selects an unweighted random forest with 300 trees, unrestricted depth and a minimum leaf size of 20. It retains raw probabilities because sigmoid calibration increases selection-period Brier error. In the 2023–2025 evaluation, the model reaches ROC-AUC 0.8866, average precision 0.02599 and Brier score 0.0023840. The Brier improvement over the constant benchmark is small.

At the frozen threshold, precision is 5.63% and recall is 9.12%. The model detects at least one monthly row for 18 of 176 test-period disclosure episodes. It is more useful as a graded risk input than as a stand-alone binary alert.

Statement enrichment fills 135,692 missing predictor cells on the matched panel and increases the number of complete rows by 35,350. The paired comparison gives a small positive point difference in ROC-AUC, but its 95% interval includes zero. Better accounting coverage is established; better predictive performance remains uncertain.

The policy replay shows how a continuous prediction can change a monthly limit. Capacity, exposure caps and assumed additional debt drive much of the aggregate result. The base mean limit is 0.668% of assets and the median is USD 4.23 million. These figures describe assumptions, not optimized lending decisions.

## 8.2 Contribution

The research combines dated SEC accounting and disclosure records, a 60-day episode label, chronological model development, temporal tuning, explicit probability selection and an auditable credit rule. It keeps model ranking, probability quality, threshold classification and monetary decisions separate because each answers a different question.

The statement comparison also shows a practical data lesson: recovering missing financial values can improve coverage substantially without proving a corresponding improvement in predictions. The matched design isolates the statement source within the new SEC snapshot. Direct comparison with run 005 also changes the source snapshot and other construction details, so it cannot identify the statement effect.

## 8.3 Limitations

The target is a new Item 1.03 bankruptcy or receivership or reviewed Item 2.04 payment-failure disclosure episode. Filing dates and the 90-day episode gap are operational definitions. They do not establish the precise onset or cure of contractual default. Item 1.03 can involve reorganization reporting; Item 2.04 evidence does not establish a missed payment on the proposed facility.

The outcome is rare, some accounting predictors remain missing, and filing data can contain taxonomy or reporting noise. Monthly rows within a company are dependent. Company-cluster bootstrap intervals address some of this dependence, but they omit common calendar shocks and uncertainty from selecting the model and target.

The final run excludes 2023–2025 labels from its development stages. Those years were examined during earlier project versions, before the broader target was specified. The later-period results are therefore retrospective, not a pristine external validation. The statement comparison's paired intervals are conditional on the fitted selected models.

The policy assumes initial limits, cash eligibility, additional debt and facility exposure. No actual utilization, repayments, contractual defaults, recoveries, losses, pricing or customer outcomes are observed. The simulation cannot demonstrate improved profit or reduced realized credit loss.

## 8.4 Further Work

A stronger study should obtain direct facility payment outcomes and economics. It should freeze the complete target and pipeline before testing on a future period or independent lender portfolio. Further work can review unresolved Item 2.04 filings, improve accounting reconciliation and evaluate whether the extra coverage helps in a new sample.

Policy evaluation should then measure expected loss, utilization, approval effects, limit volatility and profitability under realistic operational constraints. Probability calibration should be monitored over time using a predeclared process.

## 8.5 Conclusion

Public accounting and filing data provide a useful signal for near-term bankruptcy or payment-failure disclosures. Run 006 improves financial-feature coverage through statement enrichment, while its predictive gain from that enrichment remains uncertain. The selected model's threshold classification is incomplete, and its output is not a verified payment-default probability.

The policy layer turns the signal into transparent, reproducible limit decisions and shows which assumptions matter most. The thesis provides a traceable framework linking dated information, model evidence and policy rules while keeping the limits of the data explicit.
