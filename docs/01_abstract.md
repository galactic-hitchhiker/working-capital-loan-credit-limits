# Abstract

This thesis studies how financial information and machine learning can support dynamic short-term corporate credit limits. The proposed facility has a 30-day statement period and up to 30 additional days for payment. The framework separates event-risk prediction from a monetary policy based on financial capacity, a risk adjustment and an exposure cap.

The empirical analysis uses real SEC company-facts and submissions data supplied for the project. It constructs 588,111 labeled company-month observations from 9,075 companies over 2011–2025. Twelve point-in-time accounting predictors cover liquidity, leverage, profitability, cash flow, growth and firm size. The target is the first recorded bankruptcy or receivership-related Item 1.03 disclosure within the next 60 days. It is a disclosure outcome, not payment default.

Logistic regression, L2 logistic regression, random forest and XGBoost are compared through chronological training, rolling temporal tuning, pre-COVID calibration, multi-regime selection and held-out evaluation periods. Random forest with its raw identity probability mapping is selected because it improves both average precision and Brier score over the constant selection benchmark; sigmoid calibration worsens its selection-period Brier score. On 136,177 observations from 2023–2025, the selected forest achieves ROC-AUC 0.9089, average precision 0.02747 and Brier score 0.0020872. At the frozen threshold, precision is 3.97% and recall is 12.85%. Average precision is about 13 times the event share, but the low absolute precision and recall show that the event remains difficult to predict.

The hypothetical credit-limit simulation uses the selected forest and covers 99,674 observations from 3,872 companies. Its median limit is USD 3.79 million, its mean limit is 0.653% of assets and 5.69% of observations receive a zero limit. These outputs depend on assumed facility inputs because realized exposure, loss, pricing and profitability data are unavailable.

The study provides a reproducible framework and evidence of a useful disclosure-ranking signal. It does not establish payment-default probabilities, optimal limits or realized loss reductions. The 2023–2025 period is held out within the reported run, although those years were examined during earlier development and should not be described as a never-seen external validation sample.

**Keywords:** corporate credit risk; credit limits; SEC disclosures; machine learning; probability calibration; historical simulation.
