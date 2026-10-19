# 4 Risk Modeling and Validation Methodology

This chapter explains how the models are trained, compared and evaluated. Every model uses the same accounting features, outcome definition and information-timing rules. Appendix A records the exact software settings and parameter grids.

## 4.1 Modeling Framework

Each observation represents a company at a monthly decision date. Models use the twelve accounting features and 60-day outcome defined in Chapter 3, but not company names, identifiers, industry codes, future information or policy results. Missing features are replaced with fitting-sample medians and accompanied by missingness indicators; logistic inputs are also scaled. These fitted transformations are applied unchanged to later observations.

The study does not create synthetic companies or outcomes and does not duplicate rare events through oversampling. Unusually large ratios are retained rather than capped. Missing inputs needed for the monetary credit-limit calculation are handled separately and are never filled with model medians.

## 4.2 Models and Constant Benchmark

The constant benchmark assigns every observation the event rate from the original training period. It does not distinguish between companies. A useful model should provide more information than this simple prediction.

Four model families are compared: logistic regression, L2-regularized logistic regression, random forest and XGBoost. The first two provide linear benchmarks; the tree ensembles can capture nonlinearities and interactions.

Both logistic models use the same preprocessing. Their scaled, pre-calibration coefficients describe associations, not causal effects or direct percentage-point probability changes. A convergence warning stops fitting.

## 4.3 Model Tuning

Several settings are tested for each model family. Logistic regression contributes two candidates, L2 logistic regression six, random forest eight and XGBoost eight, for 24 candidates in total. These counts include versions fitted with and without balanced class weights. Appendix A lists the exact settings.

Candidate settings are compared using two expanding yearly tests:

1. Fit on 2011–2016 and evaluate on 2017.
2. Add eligible 2017 observations, refit, and evaluate on 2018.

Only labels available before the beginning of a yearly evaluation are used for fitting. Missing-value replacement and scaling are also recalculated inside each fold.

Candidates are ranked by **average-precision lift** over the year's event rate and **Brier skill** relative to the corresponding fitting-sample event rate. Values above one and zero, respectively, indicate improvement over these baselines.

The candidate with the highest mean annual average-precision lift wins within its family. Mean annual Brier skill and a fixed candidate order break ties. The winning setting is then fitted again using the combined training and tuning observations.

## 4.4 Chronological Validation and Information Timing

A random split would mix observations from different dates and could allow future information to influence earlier predictions. The study therefore uses five ordered stages:

| Stage | Nominal decision dates | Purpose |
|---|---|---|
| Training | January 2011–December 2016 | Fit candidate models |
| Tuning | January 2017–December 2018 | Choose settings within each model family |
| Calibration | January–December 2019 | Fit a possible probability correction |
| Selection | January 2020–December 2022 | Choose raw or corrected probabilities, alert thresholds and the final model |
| Later evaluation | January 2023–December 2025 | Evaluate the frozen choices |

*Table 7. Chronological model-development and evaluation stages.*

These are nominal date ranges. An observation is removed from an earlier stage when its complete 60-day label was not available before the next stage began. The data cutoff is 7 September 2026. Chapter 3 explains when positive and negative labels become available, and Chapter 6 reports the retained observations.

The same company can appear in several stages because the study evaluates continued monitoring, not a separate borrower population. Companies can contribute repeated months based on carried-forward statements, so row-level measures give more influence to issuers with more eligible months. The bootstrap in Section 4.6 keeps each company's observations together.

One disclosure episode can produce positive labels for more than one monthly decision. Results therefore report positive rows, distinct episodes and event companies separately.

The 2023–2025 period is excluded from the reported model's fitting, tuning, calibration and selection. However, these years were examined during earlier project development. The later evaluation is therefore retrospective and is not presented as untouched external validation.

## 4.5 Rare Outcomes and the Alert Threshold

Because the outcome is rare, balanced fitting weights can give the two classes equal total influence:

$$ w_c=\frac{N}{2N_c}, \tag{4} $$

where $$N$$ is the number of fitting observations, $$N_c$$ is the number in class $$c$$, and $$w_c$$ is the weight for that class. The weights are calculated separately in each fitting sample. Calibration and evaluation keep the observed event distribution.

Weighting is a tuning choice because it may improve event detection while distorting raw probabilities. Raw and corrected probabilities are both evaluated.

A threshold converts a probability into a yes-or-no alert. For each model family, the threshold is chosen on the 2020–2022 selection period by maximizing F1. Ties favor higher recall and then the higher threshold. The chosen value is fixed and applied unchanged to 2023–2025, preventing later outcomes from influencing the alert rule.

The threshold is used only to report classification performance. It is not based on lending costs and does not determine credit approval. The credit-limit policy uses the continuous predicted probability.

## 4.6 Performance Measures and Uncertainty

The study evaluates both ranking and probability accuracy.

**ROC-AUC** measures how often an event observation ranks above a non-event observation; 0.5 indicates no useful ranking and 1 perfect ranking. **Average precision** summarizes precision and recall across thresholds and is compared with the event share, its no-skill baseline.

**Brier score** measures the squared difference between predicted probabilities and observed outcomes:

$$ BS=\frac{1}{N}\sum_{n=1}^{N}(q_n-y_n)^2. \tag{5} $$

Lower values are better. Because a constant low probability can score well on a rare outcome, models are compared with the training-rate benchmark.

At the frozen alert threshold, **precision** is the share of alerts followed by an event, while **recall** is the share of actual positive observations detected by the alerts:

$$ \operatorname{Precision}=\frac{TP}{TP+FP},\qquad \operatorname{Recall}=\frac{TP}{TP+FN}. \tag{6} $$

**F1** combines precision and recall into one value:

$$ F_1=\frac{2\,\operatorname{Precision}\,\operatorname{Recall}}{\operatorname{Precision}+\operatorname{Recall}}. \tag{7} $$

The study also reports the confusion matrix, event share, number of observations and number of distinct episodes detected. Precision or recall is set to zero when its denominator is zero.

Uncertainty is estimated with 500 company-cluster bootstrap repetitions. Companies are sampled with replacement, and all monthly observations for each sampled company remain together. The 2.5th and 97.5th percentiles form the reported 95% interval. Repetitions containing only one outcome class are excluded and counted.

These intervals preserve dependence within a company but do not capture shared economic shocks, model-selection uncertainty, changes in sample construction or errors in the disclosure labels. They are conditional on the fitted models and the constructed dataset.

## 4.7 Probability Calibration

Calibration asks whether predicted probabilities match observed event rates.

Each family first produces a **raw probability**. The fitted model is then frozen, and a sigmoid correction is learned from the 2019 calibration observations. This correction changes the probability scale but does not refit the underlying logistic coefficients or decision trees.

The raw and corrected probabilities are compared on the 2020–2022 selection period. The version with the lower Brier score is retained; an exact tie favors the raw probability. This allows calibration to help when needed without forcing an unnecessary adjustment.

Later evaluation compares predicted probabilities with observed rates using ten equal-width groups and probability quantiles, which help when rare-event estimates occupy a narrow range. These diagnostics do not change the model.

## 4.8 Model Interpretation and Error Analysis

Logistic coefficients show associations after feature scaling, not causal effects. Missing-value indicators are reported separately because missing accounting data may reflect reporting coverage rather than the company's financial condition.

For the selected model, each original feature is randomly rearranged 20 times in the selection period. The increase in Brier score shows how much the model relied on that feature during that period. Features can contain overlapping information, so a low importance value does not prove that the underlying financial concept is irrelevant.

Later error analysis reports false alerts, missed events, annual performance and distinct episode detection. It describes the frozen model's limitations and is not used to redesign the model after seeing later outcomes.

## 4.9 Final Model Selection and Connection to the Policy

A model family can qualify only when, on the 2020–2022 selection period:

- its average precision is higher than the observed event share; and
- its Brier score is lower than the constant prediction based on the original training event rate.

These requirements demand improvement in both ranking and probability error. Among qualifying families, the model with the lowest Brier score is selected. An exact tie favors the simpler family in this order: logistic regression, L2 logistic regression, random forest and XGBoost.

The final choice is saved before predictions for 2023–2025 are generated. The rule does not require the highest average precision and does not prove that the selected family is statistically superior. Chapter 6 therefore reports all model families.

The selected probability enters the credit-limit rule in Chapter 5 without refitting on later outcomes. Credit-policy coefficients are separate scenario assumptions and are not optimized using the later evaluation results.
