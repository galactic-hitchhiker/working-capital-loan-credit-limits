# 4 Risk Modeling and Validation Methodology

All models use the same features, outcome and timing rules. Appendix A gives exact settings.

## 4.1 Modeling Framework

Models use the twelve Chapter 3 features but exclude identifiers, industry, future information and policy results. Fitting-sample medians and missingness indicators handle missing predictors. Logistic inputs are also scaled. Transformations remain fixed later. There is no synthetic oversampling or outlier capping, and monetary-policy inputs are never imputed with model medians.

Keeping a common feature set makes family comparisons interpretable. Excluding company identifiers prevents direct memorization, although repeated financial patterns from the same issuer can still appear across stages as part of the monitoring design.

## 4.2 Models and Constant Benchmark

The constant benchmark assigns every observation the original training event rate. Logistic regression, L2 logistic regression, random forest and XGBoost are compared. The tree models can capture nonlinearities and interactions. Scaled, pre-calibration logistic coefficients are associations rather than causal or percentage-point effects, and a convergence warning stops fitting.

The constant is a demanding probability benchmark for a rare outcome because assigning a small rate to every row can achieve a low Brier score. A candidate must therefore add ranking information without degrading probability error.

## 4.3 Model Tuning

The search contains 24 candidates including weighted and unweighted versions: two logistic, six L2 logistic, eight random-forest and eight XGBoost settings.

Candidate settings are compared using two expanding yearly tests:

1. Fit on 2011–2016 and evaluate on 2017.
2. Add eligible 2017 observations, refit, and evaluate on 2018.

Each fold uses only labels then available and refits preprocessing. Candidates rank first by mean annual **average-precision lift** over the event rate, then by **Brier skill** relative to the fitting-sample rate and a fixed tie order. The winner within each family is refitted on combined training and tuning data.

Lift and skill normalize each year against its own prevalence, limiting the influence of changes in the event rate. Expanding folds preserve temporal order and expose candidates to two distinct forward tests before a family setting is fixed.

## 4.4 Chronological Validation and Information Timing

Five ordered stages prevent future information from entering earlier predictions:

| Stage | Nominal decision dates | Purpose |
|---|---|---|
| Training | January 2011–December 2016 | Fit candidate models |
| Tuning | January 2017–December 2018 | Choose settings within each model family |
| Calibration | January–December 2019 | Fit a possible probability correction |
| Selection | January 2020–December 2022 | Choose raw or corrected probabilities, alert thresholds and the final model |
| Later evaluation | January 2023–December 2025 | Evaluate the frozen choices |

*Table 7. Chronological model-development and evaluation stages.*

Rows whose complete label was unavailable before the next stage are purged. The data cutoff is 7 September 2026. Companies may span stages and contribute repeated months, reflecting monitoring rather than a separate borrower sample. One episode may create several positive rows, so rows, episodes and companies are reported separately. Although excluded from final model development, 2023–2025 was examined during earlier work. Evaluation is retrospective, not untouched external validation.

Repeated company-months also mean that ordinary row-level intervals would understate dependence. The cluster bootstrap keeps a sampled company's full history together, while chronological stages address time ordering. Neither device removes dependence caused by market-wide shocks.

## 4.5 Rare Outcomes and the Alert Threshold

Balanced fitting weights can give the rare and common classes equal total influence:

$$ w_c=\frac{N}{2N_c}, \tag{4} $$

where $$N$$ is the number of fitting observations, $$N_c$$ is the number in class $$c$$, and $$w_c$$ is the weight for that class. The weights are calculated separately in each fitting sample. Calibration and evaluation keep the observed event distribution.

Weighting is tuned because it can improve detection while distorting probabilities. Each family's 2020–2022 threshold maximizes F1, with ties favoring recall and then the higher threshold, and is frozen for 2023–2025. Thresholds only report alerts. The policy uses continuous probability and is not an approval rule.

Balanced weights are recalculated inside each fitting sample. Evaluation always retains the observed class distribution, avoiding artificially favorable precision or calibration results.

## 4.6 Performance Measures and Uncertainty

**ROC-AUC** measures how often an event observation ranks above a non-event observation. A value of 0.5 indicates no useful ranking and 1 indicates perfect ranking. **Average precision** summarizes precision and recall across thresholds and is compared with the event share, its no-skill baseline.

ROC-AUC uses the full score distribution, whereas average precision focuses more directly on the rare positive class. Reporting both reduces the risk of treating a strong global ranking as sufficient evidence at the operationally relevant high-risk end.

**Brier score** measures the squared difference between predicted probabilities and observed outcomes:

$$ BS=\frac{1}{N}\sum_{n=1}^{N}(q_n-y_n)^2. \tag{5} $$

Lower values are better. Because a constant low probability can score well on a rare outcome, models are compared with the training-rate benchmark.

At the frozen alert threshold, **precision** is the share of alerts followed by an event, while **recall** is the share of actual positive observations detected by the alerts:

$$ \operatorname{Precision}=\frac{TP}{TP+FP},\qquad \operatorname{Recall}=\frac{TP}{TP+FN}. \tag{6} $$

**F1** combines precision and recall into one value:

$$ F_1=\frac{2\,\operatorname{Precision}\,\operatorname{Recall}}{\operatorname{Precision}+\operatorname{Recall}}. \tag{7} $$

Uncertainty is estimated with 500 company-cluster bootstrap repetitions. Companies are sampled with replacement, and all monthly observations for each sampled company remain together. The 2.5th and 97.5th percentiles form the reported 95% interval. Repetitions containing only one outcome class are excluded and counted.

These are conditional empirical intervals around the frozen fitted model, not guarantees about another population or future economic regime.
The study also reports confusion matrices and episode detection. Bootstrap intervals preserve within-company dependence but exclude shared shocks, model-selection and sample-construction uncertainty, and label errors.

## 4.7 Probability Calibration

With each fitted model frozen, a sigmoid correction is learned on 2019 data. Raw and corrected probabilities are compared on 2020–2022 by Brier score, with ties favoring raw output. Later equal-width and quantile diagnostics compare predicted and observed rates without changing the model.

Separating calibration from model fitting prevents the correction sample from influencing coefficients or tree structure. Quantile groups remain informative when rare-event probabilities occupy only a small part of the zero-to-one range.

## 4.8 Model Interpretation and Error Analysis

Scaled logistic coefficients are associative. For the selected model, each original feature is permuted 20 times in the selection period. The Brier increase measures reliance, although correlated features can share importance. Later error analysis reports false alerts, missed events, annual performance and episode detection without redesigning the model.

Permutation is applied to original features after the full prediction pipeline, so it measures the fitted system rather than an isolated tree split. It remains a global diagnostic and does not explain any individual limit decision.

## 4.9 Final Model Selection and Connection to the Policy

A model family can qualify only when, on the 2020–2022 selection period:

- its average precision is higher than the observed event share
- its Brier score is lower than the constant prediction based on the original training event rate.

Among qualifying families, the lowest Brier score wins. Exact ties favor logistic, L2 logistic, random forest, then XGBoost. The choice is saved before 2023–2025 prediction, does not imply statistical superiority and need not maximize average precision. The selected probability enters the policy without later refitting. Policy coefficients are separate assumptions.
