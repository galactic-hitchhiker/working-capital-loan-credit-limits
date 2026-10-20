# Abstract

This thesis develops a framework for dynamic short-term corporate credit limits, separating event-risk prediction from a monetary policy based on capacity, risk and an exposure cap. The proposed facility has a 30-day statement period and up to 30 further days for payment.

SEC Company Facts, Financial Statement and Notes data, and submissions are combined into 565,222 labeled company-months for 8,780 companies over 2011–2025. Twelve point-in-time accounting predictors cover liquidity, leverage, profitability, cash flow, growth and size. The target is a new bankruptcy or reviewed payment-failure disclosure episode within 60 days, not verified payment default.

Logistic regression, L2 logistic regression, random forest and XGBoost are compared chronologically. The selected random forest uses raw probabilities. On 131,842 observations from 2023–2025, it achieves ROC-AUC 0.8866 and average precision 2.60%, or 10.77 times the 0.241% event share. Its Brier score is 0.95% below the constant benchmark. Frozen-threshold precision is 5.63% and recall 9.12%. Thus, ranking is useful, but probability improvement and detection are limited.

The hypothetical policy replay covers 99,619 observations from 3,869 companies. The median limit is USD 4.23 million and the mean is 0.668% of assets. Capacity assumptions and caps affect aggregate limits more than the risk adjustment. Because realized exposure, losses, pricing and profitability are unavailable, lending benefits cannot be established. The 2023–2025 evaluation is retrospective rather than untouched external validation.

**Keywords:** corporate credit risk, credit limits, SEC disclosures, machine learning, probability calibration, historical simulation.
