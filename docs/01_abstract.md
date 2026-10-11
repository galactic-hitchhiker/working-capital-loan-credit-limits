# Abstract

This thesis studies how financial information and machine learning can support dynamic short-term corporate credit limits. The proposed facility has a 30-day statement period and up to 30 additional days for payment. The framework separates event-risk prediction from a monetary policy based on financial capacity, a risk adjustment and an exposure cap.

The empirical analysis uses SEC company facts, submissions and financial-statement facts. It constructs 565,222 labeled company-month observations from 8,780 companies over 2011–2025. Twelve point-in-time accounting predictors cover liquidity, leverage, profitability, cash flow, growth and firm size. The target is a new bankruptcy or reviewed payment-failure disclosure episode within the next 60 days. It is a disclosure outcome, not verified payment default.

Logistic regression, L2 logistic regression, random forest and XGBoost are compared through chronological training, temporal tuning, calibration, selection and later evaluation. The selected random forest retains its raw probability because sigmoid calibration worsens selection-period Brier error. On 131,842 observations from 2023–2025, it achieves ROC-AUC 0.8866, average precision 0.0260 and Brier score 0.0023840. At the frozen threshold, precision is 5.63% and recall is 9.12%. These results show a ranking signal, but limited detection at one threshold.

Adding SEC financial-statement facts fills 135,692 missing predictor cells on a matched panel. In a paired test comparison, the resulting ROC-AUC gain is 0.0069, while the 95% interval includes zero. Feature coverage improves clearly; a reliable predictive gain is not established.

The hypothetical credit-limit replay uses the selected model and covers 99,619 observations from 3,869 companies. Its median limit is USD 4.23 million and its mean limit is 0.668% of assets. Capacity assumptions and caps have a larger aggregate effect than the risk adjustment. Realized exposure, loss, pricing and profitability data are unavailable, so lending benefits cannot be established. The 2023–2025 evaluation is retrospective: these years were examined during earlier development and are not an untouched external validation sample.

**Keywords:** corporate credit risk; credit limits; SEC disclosures; machine learning; probability calibration; historical simulation.
