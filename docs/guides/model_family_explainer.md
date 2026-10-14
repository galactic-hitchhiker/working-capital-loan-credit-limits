# Model family explainer (standalone note)

This note explains the four model families used in this project. It is supporting documentation, **not a chapter or appendix of the master's thesis**.

All four models take the same twelve accounting predictors for a company at a monthly decision date and estimate the probability of a qualifying SEC disclosure episode in the next 60 days. That outcome is a bankruptcy or reviewed payment-failure **disclosure**, not a verified default on a credit facility. The main difference between the models is how they turn predictors into a probability.

## The short comparison

| Model | How it learns | Relationships it can represent directly | Main advantage | Main limitation |
|---|---|---|---|---|
| Logistic regression | Fits one coefficient per input to predict event log-odds | Additive, linear effects on log-odds | Simple coefficient-based benchmark | Needs explicitly added transformations or interactions for more complex patterns |
| L2-regularized logistic regression | Fits the same form while penalizing large coefficients | The same relationships as logistic regression | Can make coefficients less sensitive to noisy or correlated inputs | The penalty does not create nonlinear effects or interactions |
| Random forest | Averages predictions from many trees fitted to varied samples | Thresholds, nonlinearities and interactions | Handles complex patterns without specifying their form in advance | Harder to explain globally; raw probabilities may need calibration |
| XGBoost | Adds trees sequentially, each improving the current prediction | Thresholds, nonlinearities and interactions | Often captures detailed predictive structure efficiently | More tuning and greater risk of fitting patterns that do not persist |

## Logistic regression

Logistic regression first calculates a score from the predictors:

$$
z = \beta_0 + \beta_1 x_1 + \cdots + \beta_p x_p.
$$

It then converts that score to a number between zero and one with the logistic function, $q=1/(1+e^{-z})$. Each coefficient changes the **log-odds** of the event while the other inputs are held fixed. A positive coefficient does not mean the probability rises by a fixed number of percentage points: the probability change depends on the starting score.

The model is linear in log-odds. For example, if the effect of liquidity depends on whether operating cash flow is negative, ordinary logistic regression cannot express that interaction unless a corresponding interaction term is added. Its coefficients are associations in the fitted data, not causal effects.

## What L2 regularization changes

L2-regularized logistic regression uses the same logistic equation but adds a penalty for large coefficients during fitting. The penalty pulls coefficients toward zero; it normally does not set them exactly to zero. This can reduce sensitivity to noise and overlapping information, such as related liquidity and leverage ratios.

The project tunes the inverse penalty parameter `C`: **smaller `C` means stronger regularization**. L2 regularization changes how strongly the coefficients are fitted, not the basic shape of the model. It should therefore be compared with ordinary logistic regression as a more constrained version of the same model family, rather than as a nonlinear model.

## Random forest

A decision tree repeatedly divides observations using rules such as “liabilities to assets exceeds this value.” A leaf assigns a prediction to observations satisfying its chain of rules. A random forest fits many trees to bootstrap samples and considers random subsets of predictors at splits, then averages their predictions.

Different branches can represent different relationships. For example, low cash may matter differently for companies with positive and negative operating cash flow. Averaging trees makes the result less dependent on one tree, but the collection is less transparent than a short logistic equation. A forest can rank observations well while its raw predicted probabilities still differ from observed event frequencies.

## XGBoost

XGBoost is a gradient-boosted tree model. Instead of fitting many trees independently and averaging them, it builds a sequence of trees. Each new tree is chosen to improve the current model's objective; a learning rate limits the size of each addition. Tree depth controls how detailed each tree's rules can be.

This sequential process can capture fine structure, but it also makes the result sensitive to settings such as depth, learning rate and number of trees. Strong ranking performance does not guarantee good probability calibration, particularly when the event is rare or its frequency changes over time.

## How the comparison works in this repository

The [model definitions](../../mcf/models/risk.py) use median imputation and missing-value indicators for all four families. The logistic pipelines also standardize inputs. Each candidate is fitted both with and without balanced class weights. The project tunes candidates on chronological folds, fits a possible sigmoid probability correction on a separate period, and selects a model using the later selection period. The binary alert threshold is chosen separately from the continuous probability used by the credit-limit policy. See [Chapter 4](../thesis/05_chapter_4.md) for the full procedure.

In the primary model experiment, the balanced logistic candidates required sigmoid correction: their raw probabilities had very large Brier errors. The selected random forest retained its raw probability because sigmoid correction worsened its selection-period Brier score. On the retrospective 2023–2025 evaluation, XGBoost had the highest ROC-AUC and average precision of the four fitted families, while the selected forest had the lowest Brier score. These are results for this dataset, target and time split; they are not general rankings of the algorithms. The [main-analysis metrics](../../results/run_006_full_statement_enrichment/models/metrics.csv) contain the exact values.

The practical reading is: logistic regression supplies a clear linear benchmark; L2 tests whether shrinking that benchmark's coefficients helps; random forest and XGBoost test whether learned thresholds and interactions improve prediction. For a credit limit, the probability scale matters as well as ranking, because the policy applies a continuous risk adjustment to the estimated probability.

## Why these models were chosen for the thesis

The thesis asks whether more flexible models improve on a straightforward accounting-based risk estimate. These four models make that question testable as a progression of modeling choices:

1. **Logistic regression** provides a familiar, interpretable starting point for a binary 60-day outcome. It shows what can be achieved with additive effects of the accounting predictors.
2. **L2-regularized logistic regression** tests whether shrinking coefficients improves that linear starting point when financial ratios overlap or contain noise. Comparing it with ordinary logistic regression isolates the effect of regularization.
3. **Random forest** tests whether thresholds and interactions in the financial measures add useful information without specifying each relationship in advance. Averaging trees provides one way to control the variability of individual trees.
4. **XGBoost** supplies a second, distinct tree-based approach. Its sequential boosting tests whether a more detailed fit improves ranking or probability accuracy beyond the forest.

Together they compare a simple linear model, its regularized version, and two different ways to combine trees. All four can produce event probabilities from the same predictors, which allows the thesis to compare ranking, probability error and threshold detection on common chronological periods. This choice also connects directly to the credit-limit question: the study needs to know whether added model complexity improves the probability used by the policy, rather than assuming that the most flexible model is best. The four families were chosen for those comparisons; the random forest was selected only after the thesis's stated selection procedure was applied.
