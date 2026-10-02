# 6 Empirical Results

The experiment selects a random forest with its raw identity probability mapping. It produces materially better ranking than the logistic benchmarks and a small improvement in Brier score over the constant benchmark. The results support prediction of the defined SEC disclosure event, while leaving substantial classification error and no direct evidence about payment default.

## 6.1 Sample and Chronological Design

The labeled panel contains 588,111 company-months from 9,075 companies and 472 distinct event companies. Boundary purging removes observations whose 60-day outcome windows would cross stages.

| Stage | Calendar period | Observations | Positive rows | Companies | Event companies |
|---|---|---:|---:|---:|---:|
| Training | 2011–2016 | 206,760 | 249 | 6,050 | 133 |
| Tuning | 2017–2018 | 52,952 | 84 | 3,719 | 47 |
| Calibration | 2019 | 32,269 | 59 | 3,928 | 35 |
| Selection and robustness | 2020–2022 | 124,931 | 152 | 5,006 | 85 |
| Held-out evaluation | 2023–2025 | 136,177 | 288 | 4,766 | 160 |

The model-selection stages exclude 2023–2025 labels. Earlier versions of this research examined results from these years while the pipeline was being developed. The period is therefore held out within the final reported run, but it is not a completely untouched external validation sample.

![Annual sample coverage and disclosure-label share](figures/sample_over_time.png)

*Figure 6.1. Labeled panel before chronological purging. Positive rows are monthly prediction outcomes, not separate defaults. Source: panel_audit.json and empirical_report.py.*

## 6.2 Predictors and Rolling Tuning

The models use 12 point-in-time predictors: current ratio, cash and equivalents to assets, liabilities to assets, 12-month asset growth, 12-month change in liabilities to assets, working capital to assets, return on average assets, operating cash flow to average assets, operating cash flow to average liabilities, negative net income, negative operating cash flow and log assets.

Hyperparameters are evaluated with expanding-window temporal folds: fit through 2016 and validate in 2017, then fit through 2017 and validate in 2018. Selection uses mean average-precision lift and mean Brier skill across those folds. This design checks transfer to later years instead of mixing both tuning years into one aggregate score.

The winning specifications are balanced logistic regression, balanced L2 logistic regression with C = 10, an unweighted random forest with 300 trees, unrestricted depth and minimum leaf size 20, and balanced XGBoost with 200 trees, depth 2 and learning rate 0.05.

## 6.3 Probability Mapping and Model Selection

The calibration period is 2019, before the COVID-19 regime. Sigmoid mappings are fitted for the logistic and XGBoost models. For the random forest, the selection comparison retains the raw identity mapping. Its selection Brier score is 0.0012007, while sigmoid mapping worsens it to 0.0012217.

The selection benchmark is a constant probability with Brier score 0.0012152 and average precision equal to the 0.1217% event share. The predefined acceptance rule requires average precision above the event share and Brier score below the constant benchmark.

| Model and mapping | ROC-AUC | Average precision | Brier score | Accepted |
|---|---:|---:|---:|---|
| Logistic, sigmoid | 0.8514 | 0.005624 | 0.0012467 | No |
| L2 logistic, sigmoid | 0.8513 | 0.005605 | 0.0012467 | No |
| Random forest, identity | 0.8594 | 0.037377 | 0.0012007 | Yes |
| XGBoost, sigmoid | 0.8892 | 0.034594 | 0.0012093 | Yes |

Both tree models pass. Random forest is selected because it has the lower selection Brier score. The frozen threshold chosen on the selection period is 0.0410103.

## 6.4 Held-out Evaluation

| Model | ROC-AUC | Average precision | Brier score | Precision at frozen threshold | Recall at frozen threshold |
|---|---:|---:|---:|---:|---:|
| Constant | 0.5000 | 0.002115 | 0.0021113 | 0.00% | 0.00% |
| Logistic, sigmoid | 0.8221 | 0.009283 | 0.0021024 | 1.79% | 1.04% |
| L2 logistic, sigmoid | 0.8219 | 0.009265 | 0.0021024 | 1.68% | 1.04% |
| **Random forest, identity** | **0.9089** | **0.027475** | **0.0020872** | **3.97%** | **12.85%** |
| XGBoost, sigmoid | 0.9100 | 0.035369 | 0.0020896 | 4.00% | 19.10% |

The selected forest's average precision is 12.99 times the event share. Its Brier skill against the constant benchmark is 1.14%. XGBoost ranks slightly better, but random forest remains the model fixed by the preceding selection stage.

The forest produces 37 true-positive and 895 false-positive rows and misses 251 positive rows. It detects at least one positive row for 24 of 160 event companies. XGBoost detects 32 event companies. These figures show why the probability output is more useful for graded policy adjustment than the frozen threshold is as a stand-alone alert.

The selected forest's annual ROC-AUC is 0.9081 in 2023, 0.8969 in 2024 and 0.9294 in 2025. Annual average precision is 0.03483, 0.03533 and 0.02522, respectively. Performance varies by year but the ranking signal persists.

Company-cluster bootstrap intervals for the selected forest are 0.8934–0.9243 for ROC-AUC, 0.01928–0.04957 for average precision and 0.001750–0.002420 for Brier score. The corresponding XGBoost intervals overlap, so the evaluation does not establish statistically significant superiority between the two tree models.

![Held-out ranking and probability diagnostics](figures/model_diagnostics.png)

*Figure 6.2. Precision-recall and reliability diagnostics for 2023–2025. Source: predictions.csv and quantile_calibration.csv.*

## 6.5 Interpretation

Permutation importance identifies log assets as the strongest predictor for the selected forest, followed by working capital to assets, 12-month asset growth and current ratio. Importance measures predictive contribution in this fitted model; it does not establish a causal relationship.

The results are good enough to demonstrate a repeatable ranking signal for a rare SEC disclosure outcome. They are modest as a classification system: only 3.97% of flagged company-months are positive at the frozen threshold, and recall is 12.85%. The selected probabilities refer to filing an Item 1.03 bankruptcy or receivership disclosure within 60 days. Item 1.03 can accompany a bankruptcy or receivership, but it is neither a necessary nor sufficient definition of payment default. Payment defaults can occur without such a filing, and a filing does not reveal the timing or amount of every payment failure.

These results therefore support the thesis's methodological contribution and a hypothetical policy simulation. They do not validate a payment-default probability, prove deployable lending performance or measure realized loss reduction.

File references: metrics.csv, stage_audit.json, tuning_scores.csv, tuning_fold_scores.csv, selection.json, bootstrap_intervals.json, annual_test_metrics.csv, event_detection.csv, permutation_importance.csv and empirical_report.py.
