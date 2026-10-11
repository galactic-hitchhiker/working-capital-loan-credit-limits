# 4 Risk Modeling and Validation Methodology

This chapter describes how the 60-day SEC disclosure models are fitted and evaluated. All families face the same information constraints. Appendix B records the settings fixed before fitting.

## 4.1 Modeling Framework

Each observation is an eligible company at a monthly decision date. All models use the twelve accounting predictors and 60-day disclosure-episode outcome defined in Chapter 3. Company identifiers, industry codes, future information and policy outcomes are excluded from predictors. Dates govern availability and chronological stages.

Missing predictors are replaced with fitting-sample medians. A missing-value indicator is added for a predictor when missing values occur in the fitting sample. Logistic models also standardize the resulting columns using fitting-sample means and standard deviations. These fitted transformations are applied unchanged to later observations.

No synthetic observations, synthetic labels or oversampling are used in the empirical experiment. No winsorization is applied. Extreme observed ratios remain, which is a limitation for the linear models. Missing policy inputs are treated separately and are not imputed by these predictive pipelines.

## 4.2 Baselines and Logistic Regression

The first benchmark assigns every observation the event share from the original training period. This is a probability benchmark, not a model of differences between companies.

The fitted linear benchmarks are unregularized and L2-regularized logistic regression. Both use the same preprocessing. Coefficients describe associations on standardized inputs before calibration, not percentage-point changes in final probabilities. Convergence warnings stop the run.

## 4.3 Random Forest and Gradient Boosting

Random forest and XGBoost allow nonlinear relationships and predictor interactions. The grids vary tree depth and, respectively, minimum leaf size or learning rate. Each specification is fitted with and without balanced class weights, giving 24 candidates across the four families. Appendix B gives the grids and software settings.

Within each family, candidates are evaluated with expanding annual tuning folds. The first fold fits the original training period through 2016 and validates on 2017. The second fold adds 2017 observations whose labels were available before January 2018 and validates on 2018. Preprocessing is refitted inside each fold. This prevents a 2018 fit from using labels that were not yet observable at its start.

For each fold, average precision is divided by that year's event share to obtain average-precision lift. Brier skill is measured against a constant probability estimated from that fold's fitting observations. Candidates are ranked by mean annual average-precision lift, then mean annual Brier skill and fixed candidate order. The winning specification is refitted on retained training and tuning observations.

## 4.4 Chronological Validation and Information Timing

Randomly dividing company-month rows would mix nearby observations and information from different dates. The study uses five ordered stages:

| Stage | Nominal decision dates | Purpose |
|---|---|---|
| Training | January 2011–December 2016 | Fit candidates and preprocessing |
| Tuning | January 2017–December 2018 | Select settings within each family |
| Calibration | January–December 2019 | Fit the sigmoid probability mapping |
| Selection | January 2020–December 2022 | Choose raw or sigmoid probabilities, thresholds and final model |
| Held-out evaluation | January 2023–December 2025 | Evaluate frozen choices |

These are nominal windows. An observation is removed from an earlier stage if its label is not available strictly before the next stage begins. The data cutoff is 7 September 2026. Chapter 6 reports retained counts and removals.

Positive labels become usable only after the complete 60-day window. A negative label also waits until the next observed issuer filing at or after the horizon, plus one day. This rule prevents a later confirmation of reporting coverage from entering an earlier fitting period.

The same company may occur in several stages. This evaluates later monitoring of the observed issuer population. It does not establish generalization to an entirely separate set of borrowers. Although 2023–2025 is excluded from every model-development step in the reported run, those years were examined during earlier project development. The final results are therefore a chronological held-out evaluation rather than a completely untouched external validation.

A disclosure episode can produce positive labels at more than one monthly decision. The analysis reports distinct episodes and event companies as well as positive rows. These counts are not interchangeable.

## 4.5 Class Imbalance and Decision Thresholds

The disclosure outcome is rare. Balanced weights give the two outcome classes equal total fitting weight:

$$ w_c=\frac{N}{2N_c}, $$

where N is the total number of fitting observations and the denominator contains the number in class c. Weights are calculated only from the observations being fitted. Calibration and evaluation retain the observed outcome distribution.

Weights can increase attention to rare outcomes, but raw weighted probabilities need not match the observed event rate. Weighting is therefore a tuning choice. Every final family model compares its raw probabilities with a separately fitted sigmoid mapping.

For each family, a binary threshold is chosen on the selection period to maximize F1. Ties favor higher recall and then the higher threshold. The threshold is frozen before test evaluation.

This is a reporting convention. It is not based on lending costs and does not define commercial approval. The limit policy uses the continuous probability, not this binary classification.

## 4.6 Performance Measures and Uncertainty

ROC-AUC measures ranking across thresholds. Average precision summarizes the precision-recall relationship.

The Brier score measures probability error:

$$ BS=\frac{1}{N}\sum_{n=1}^{N}(q_n-y_n)^2. $$

Lower values are better. With a rare outcome, assigning low probabilities almost everywhere can produce a small numerical score. Results must therefore be compared with the constant benchmark.

At the frozen threshold:

$$ \operatorname{Precision}=\frac{TP}{TP+FP},\qquad \operatorname{Recall}=\frac{TP}{TP+FN}. $$

$$ F_1=\frac{2\,\operatorname{Precision}\,\operatorname{Recall}}{\operatorname{Precision}+\operatorname{Recall}}. $$

The study also reports the confusion matrix, event share and sample size. Precision or recall is set to zero when its denominator is zero, following the explicit implementation setting.

Uncertainty is assessed with 500 company-cluster bootstrap repetitions. Companies are sampled with replacement, retaining all their test observations. Percentile intervals use the 2.5th and 97.5th percentiles. Single-class repetitions are excluded and counted.

This preserves dependence within a company. It does not capture shared calendar shocks, uncertainty from model selection or changes in sample construction. The intervals are conditional on the fitted models.

## 4.7 Probability Calibration

Each refitted model is frozen before calibration. A sigmoid map is fitted using only the 2019 calibration observations. The calibrator does not refit the underlying trees or logistic coefficients.

Separate calibration avoids fitting the underlying model and its probability correction on the same observations. On the selection period, the workflow compares the sigmoid probabilities with the unchanged raw probabilities and retains the mapping with the lower Brier score; an exact tie favors the raw mapping.

Calibration can become inaccurate when event rates or predictor relationships change. The thesis compares raw and calibrated Brier scores on later periods and compares predicted probability with observed event share.

The standard exporter uses ten equal-width probability bins. Since rare-event predictions can occupy a narrow range, the empirical report also groups observations by probability quantiles. Test-period diagnostics do not change the fitted model.

## 4.8 Model Interpretation and Error Analysis

Logistic coefficients describe associations on standardized inputs. Missing-value indicators are reported separately; they may reflect reporting coverage rather than an economic characteristic.

For the selected model, each original predictor is permuted 20 times in the selection period. The increase in Brier score measures reliance on that predictor in that period. Correlated predictors can share information, so low importance does not prove that a financial concept is irrelevant.

Held-out error analysis examines false positives, missed events, annual performance and distinct event detection. It describes practical limits and is not used to redesign the model after seeing evaluation outcomes.

## 4.9 Model Selection and Connection to the Policy

A family qualifies only if its selected probability mapping has selection-period average precision above the selection event share and Brier score below the constant training-prevalence benchmark. Among qualifying families, the lowest Brier score wins. An exact tie favors the simpler family in the order logistic regression, L2 logistic regression, random forest and XGBoost.

The choice is saved before held-out predictions are generated. Chapter 6 reports the selected model and probability mapping.

The rule combines a minimum ranking requirement with probability error. It does not require the highest average precision and does not establish statistically significant superiority. Chapter 6 reports all families to show this trade-off.

The chosen probability enters the Chapter 5 rule without refitting on test outcomes. Policy coefficients are separate scenario assumptions and are not optimized against test results.
