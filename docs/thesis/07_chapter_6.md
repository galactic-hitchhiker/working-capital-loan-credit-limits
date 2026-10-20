# 6 Empirical Results

The primary experiment selects raw random-forest probabilities for their lowest 2020–2022 probability error among qualifying models. Later ranking remains useful, but probability improvement and fixed-threshold detection are limited.

## 6.1 Sample and Chronological Design

The labeled panel contains 565,222 company-months from 8,780 companies, with 1,052 positive rows representing 573 episodes in 487 companies. After purging, 531,344 observations enter five stages:

| Stage | Calendar period | Observations | Positive rows | Episodes | Companies | Event companies |
|---|---|---:|---:|---:|---:|---:|
| Training | 2011–2016 | 196,174 | 294 | 160 | 5,783 | 133 |
| Tuning | 2017–2018 | 51,021 | 103 | 58 | 3,591 | 56 |
| Calibration | 2019 | 31,165 | 74 | 45 | 3,814 | 43 |
| Selection | 2020–2022 | 121,142 | 204 | 116 | 4,883 | 100 |
| Later evaluation | 2023–2025 | 131,842 | 318 | 176 | 4,633 | 165 |

*Table 12. Composition of the chronological modeling stages.*

*Source: primary model experiment stage audit. Counts refer to observations retained after chronological purging.*

The purge removes 33,878 boundary rows whose labels were not yet available. One episode can create several positive months. The later period's 318 positive rows represent 176 episodes in 165 companies. Although its outcomes do not enter final model development, that period was examined earlier, before the broader outcome definition, so evaluation is retrospective.

Figure 1 shows that both coverage and event prevalence vary through time. These changes reinforce the use of annual forward folds and period-specific baselines rather than a random split that assumes exchangeable observations.

Figure 1 summarizes annual sample coverage and the share of positive labels before chronological purging.

![Annual sample coverage and disclosure-label share](figures/sample_over_time.png)

*Figure 1. Sample coverage and positive-label share.*

## 6.2 Predictors and Tuning

Chronological tuning selects one setting per family:

| Model family | Selected setting |
|---|---|
| Logistic regression | Balanced class weights |
| L2 logistic regression | Balanced class weights and $$C=10$$ |
| Random forest | Unweighted, 300 trees, unrestricted depth and minimum leaf size 20 |
| XGBoost | Unweighted, 200 trees, depth 4 and learning rate 0.05 |

*Table 13. Selected settings by model family.*

Balanced weights are selected for logistic but not tree models. Appendix A gives the full grid.

This pattern does not mean weighting is generally unsuitable for trees. It means that, under the predefined temporal tuning criterion and candidate grid, the unweighted tree settings transferred better across the two tuning years.

## 6.3 Probability Mapping and Model Selection

Sigmoid correction improves logistic Brier errors and is retained there. Raw outputs are retained for both trees. For the forest, correction worsens Brier score from 0.0016463 to 0.0017675.

The selection-period event share is 0.1684% and constant Brier score 0.0016812. AP lift uses that event share. Negative Brier skill means worse probability error than the constant.

| Model and probability mapping | ROC-AUC | Average precision | AP lift | Brier score | Brier skill | Accepted |
|---|---:|---:|---:|---:|---:|---|
| Logistic, sigmoid | 0.8193 | 0.6182% | 3.67 | 0.0017116 | −1.81% | No |
| L2 logistic, sigmoid | 0.8190 | 0.6168% | 3.66 | 0.0017116 | −1.81% | No |
| Random forest, raw | 0.8601 | 4.3005% | 25.54 | 0.0016463 | 2.08% | Yes |
| XGBoost, raw | 0.8755 | 3.9759% | 23.61 | 0.0016778 | 0.20% | Yes |

*Table 14. Model selection results for 2020–2022.*

Logistic models improve ranking but fail the Brier requirement. Both trees pass. The forest wins on Brier despite XGBoost's higher ROC-AUC. Its F1-maximizing threshold is 0.057971 and is frozen for later alert evaluation. Policy uses continuous probability.

The selection rule therefore favors usable probability scale over the strongest ranking alone. The small difference in tree-model Brier scores should not be read as proof of general forest superiority, especially given the alternative-period result below.

## 6.4 Later Evaluation

For 2023–2025, AP lift uses the 0.2412% event share and Brier skill the constant score of 0.0024070.

| Model | ROC-AUC | Average precision | AP lift | Brier score | Brier skill |
|---|---:|---:|---:|---:|---:|
| Constant | 0.5000 | 0.2412% | 1.00 | 0.0024070 | 0.00% |
| Logistic, sigmoid | 0.8274 | 1.0678% | 4.43 | 0.0023953 | 0.49% |
| L2 logistic, sigmoid | 0.8272 | 1.0671% | 4.42 | 0.0023953 | 0.49% |
| **Random forest, raw** | **0.8866** | **2.5989%** | **10.77** | **0.0023840** | **0.95%** |
| XGBoost, raw | 0.8946 | 2.8057% | 11.63 | 0.0025355 | −5.34% |

*Table 15. Later-period ranking and probability performance.*

Frozen-threshold performance is:

| Model | Precision | Recall |
|---|---:|---:|
| Constant | 0.00% | 0.00% |
| Logistic, sigmoid | 1.49% | 23.27% |
| L2 logistic, sigmoid | 1.48% | 23.27% |
| **Random forest, raw** | **5.63%** | **9.12%** |
| XGBoost, raw | 6.21% | 6.92% |

*Table 16. Later-period performance at the frozen alert thresholds.*

The forest's AP is 10.77 times the event share, but Brier error improves only 0.95%. Its mean probability is 0.284% against a 0.241% observed share. Of 515 alerts, 29 precede a positive row. The model misses 289 of 318 positive rows. At least one alert precedes 18 of 176 episodes (10.23%).

Precision of 5.63% is much higher than prevalence but still means most alerts are false positives under the disclosure definition. Recall of 9.12% means most positive rows remain below the selection-period threshold. These metrics describe an alerting use case and do not determine the continuous policy adjustment.

Annual ROC-AUC is 0.8715, 0.8777 and 0.9329 in 2023–2025. AP is 2.793%, 2.927% and 2.904%. Company-cluster 95% intervals are 0.8668–0.9061 for ROC-AUC, 1.817%–4.378% for AP and 0.002040–0.002799 for Brier score, excluding model-selection uncertainty, shared shocks and label error.

The annual results show that the aggregate ranking is not produced by a single weak or strong year. Nevertheless, only three later years are available, and their confidence intervals do not represent a new economic regime.

Figure 2 summarizes the ranking and probability diagnostics for the 2023–2025 evaluation period.

![Held-out ranking and probability diagnostics](figures/model_diagnostics.png)

*Figure 2. Model diagnostics, 2023–2025.*

## 6.5 Alternative-Period Sensitivity

Changing chronological periods changes the selected model:

| Experiment | Tuning period | Selection period | Selected model |
|---|---|---|---|
| Primary model experiment | 2017–2018 | 2020–2022 | Random forest |
| Alternative-period sensitivity experiment | 2018 | 2023–2024 | XGBoost |

*Table 17. Alternative-period model-selection sensitivity.*

The alternative also changes training dates and excludes 2020–2022, so it establishes period sensitivity rather than a single cause or pandemic effect. Conducted after primary results were examined, it is not independent validation.

## 6.6 Interpretation

Permutation importance is highest for log assets, followed by working capital to assets, asset growth and liabilities to assets. This measures predictive reliance, not causation. Correlated features can share importance. Useful ranking does not make the threshold a stand-alone rule, since most events are missed and most alerts are false. The disclosure proxy also does not establish distress onset or facility default. Results support a reproducible signal and illustrative policy, not measured lending performance.

Company size may proxy for reporting quality, financing access or other omitted differences, so its importance requires caution. Borrower-level deployment would need reason codes and stability checks beyond this global ranking of features.
