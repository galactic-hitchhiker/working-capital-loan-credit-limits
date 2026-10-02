# 8 Discussion, Limitations and Conclusion

## 8.1 Main Findings

The final experiment selects an unweighted random forest with 300 trees, unrestricted depth and a minimum leaf size of 20. Its raw identity probability mapping is retained because sigmoid calibration worsens selection-period Brier error. In the 2023–2025 held-out evaluation, the model achieves ROC-AUC 0.9089, average precision 0.02747 and Brier score 0.0020872. These results show strong ranking relative to the rare-event baseline and a small probability-error improvement.

The fixed-threshold results are less strong. Precision is 3.97%, recall is 12.85%, and only 24 of 160 event companies have at least one detected positive row. The model is therefore more convincing as a graded risk-ranking input than as a stand-alone binary alert.

The policy simulation shows how that continuous prediction can alter a transparent monthly limit. Capacity, exposure caps and assumed additional debt drive much of the aggregate result. The base mean limit is 0.653% of assets, and the median is USD 3.79 million. These figures describe the implemented assumptions, not an empirically optimized lending policy.

## 8.2 Contribution

The research combines point-in-time SEC accounting data, a clearly dated 60-day label, chronological model development, rolling temporal tuning, an explicit probability-selection rule and an auditable credit policy. It also separates model ranking, probability quality, threshold classification and monetary decisions. That separation is useful because each answers a different question.

The expanded 12-predictor design adds leverage, cash-flow coverage, cash holdings, growth and negative-performance indicators to the original liquidity and profitability variables. Tree models benefit materially from this broader information set and nonlinear interactions.

## 8.3 Limitations

The target is an Item 1.03 bankruptcy or receivership disclosure. It is not a direct payment-default label. Payment default can occur without Item 1.03, while an Item 1.03 filing does not by itself identify every contractual missed payment, cure, exposure or loss.

The outcome is extremely rare, accounting values can contain filing and taxonomy noise, and some predictors remain missing. Monthly rows from the same company are dependent, although company-cluster bootstrap intervals partly address that dependence. The stage event rates differ, and probability quality may drift as reporting and market regimes change.

The 2023–2025 labels are excluded from all fitting, tuning, calibration, model selection and threshold selection in the reported run. Those years were nevertheless examined during earlier project development. The reported evaluation should therefore be read as a chronologically held-out assessment of the final run, not as a pristine external validation performed once after all research choices were fixed.

The policy uses assumed initial limits, cash eligibility, sales conversion, additional debt and collateral behavior. No facility-level utilization, repayments, contractual defaults, recoveries, losses, pricing or customer outcomes are observed. The simulation cannot demonstrate that the policy improves profit or reduces realized credit loss.

## 8.4 Further Work

A stronger follow-up study should obtain direct payment-performance or default labels and facility economics. It should freeze the complete pipeline before testing on a new future period or independent lender portfolio. Probability calibration should be monitored by period and recalibrated only through a predeclared governance process.

Further model work can evaluate additional point-in-time predictors, alternative missing-data treatments and constrained or monotone models. Any larger hyperparameter search should remain nested inside temporal validation. Policy evaluation should then measure expected loss, utilization, approval effects, limit volatility and profitability under realistic operational constraints.

## 8.5 Conclusion

The thesis demonstrates that public accounting and filing data contain a meaningful signal for near-term Item 1.03 disclosures. The selected random forest ranks risk well relative to the rare event rate and modestly improves probability error over a constant benchmark. Its threshold classification remains incomplete, and the result does not amount to payment-default prediction.

The policy layer turns this signal into transparent, reproducible decisions and exposes which assumptions drive credit limits. That is the central practical contribution: a traceable framework linking dated information, model evidence and policy rules while keeping the limits of the available data explicit.
