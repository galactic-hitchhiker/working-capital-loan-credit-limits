# Master Thesis Structure

## Dynamic Determination of Short Term Corporate Credit Limits Using Machine Learning

This outline follows the structure of the provided completed thesis while adapting it to the topic, objectives, and methodology defined in the master thesis application. The central design principle is to separate the prediction of borrower risk from the policy used to assign a monetary credit limit.

## Recommended Thesis Scope

### Included

- Corporate borrowers, with the empirical study focused on listed companies for which financial statements are available.
- A short-term revolving facility with a 30-day statement period and payment due within 30 days, creating up to approximately 60 days of exposure.
- Financial-statement variables covering liquidity, leverage, profitability, cash flow, working capital, debt-service capacity, size, and recent trends.
- Interpretable benchmark models: logistic regression and regularized logistic regression.
- Non-linear comparison models: random forest and one gradient-boosting implementation.
- Chronological model validation that reflects how the framework would operate in practice.
- Probability calibration and model interpretation, not only ranking accuracy.
- A transparent credit-limit policy that combines estimated risk, borrower capacity, existing indebtedness, and explicit policy caps.
- Monthly limit updates using only information available at each decision date.
- Historical backtesting and a small set of clearly defined stress scenarios.

### Optional Extension

- A discrete-time hazard or survival model, but only if the event data and remaining time permit a reliable implementation.
- Market and macroeconomic indicators for listed companies.
- Direct prediction of 60-day delinquency if suitable private-company payment or account data becomes available.

### Excluded

- A machine-learning model that directly predicts the monetary limit without an explainable policy layer.
- Consumer or retail credit scoring.
- Long-term project finance, mortgages, or other facilities whose structure differs materially from the 30-plus-30-day product.
- Real-time transaction monitoring, fraud detection, collections optimization, and portfolio pricing.
- A production lending system or automated approval engine.
- Causal claims that a model or limit policy reduces realized defaults.

## Front Matter

### Title Page

Use the faculty format from the example. Include the university and program, thesis title, student name and ID, supervisor, location, and submission date.

### Abstract

Summarize the business problem, dataset, risk target, models, credit-limit policy, validation approach, main predictive results, and main limit-policy results. Write this last, when all results are known.

### Keywords

Include five to seven terms such as corporate credit risk, credit scoring, credit limits, probability of default, machine learning, financial ratios, and model calibration.

### Table of Contents

Generate this automatically from numbered heading styles after the thesis is complete.

### List of Figures and List of Tables

Include separate lists if the thesis contains enough figures and tables to justify them. Use consistent numbered captions throughout the document.

## 1 Introduction

### 1.1 Background and Business Context

Explain why short-term corporate credit limits matter to banks and fintech lenders. Describe the 30-day statement plus 30-day payment structure and why it can create exposure of up to approximately 60 days.

### 1.2 Problem Statement

Define the weakness of static or judgment-only limits: they may react too slowly to deterioration or fluctuate without a consistent link to borrower risk and repayment capacity.

### 1.3 Research Question and Subquestions

State one central question: how can statistical and machine-learning estimates of corporate credit risk be translated into transparent, stable, and responsive short-term credit limits?

Support it with subquestions on model performance, calibration, interpretability, borrower capacity, limit stability, and stress responsiveness.

### 1.4 Research Objectives

List the concrete objectives: build the dataset, define the risk target, compare models, select and calibrate a risk estimate, design the limit policy, and evaluate the resulting limits historically and under stress.

### 1.5 Contributions and Practical Relevance

Explain that the thesis contributes an end-to-end framework rather than only a prediction model. Emphasize the separation between risk estimation and the explainable lending-policy decision.

### 1.6 Scope and Limitations

State the borrower population, facility type, data frequency, prediction horizon, geographical or market coverage, observation period, and excluded lending problems. Briefly flag the limits of using listed-company data as a proxy for private borrowers.

### 1.7 Structure of the Thesis

Give one short paragraph explaining what each remaining chapter contains.

## 2 Theoretical Background and Literature Review

### 2.1 Corporate Credit Risk

Define default, delinquency, financial distress, probability of default, exposure at default, loss given default, and expected loss. Clarify which concept the empirical target represents.

### 2.2 Short Term Corporate Credit Facilities

Describe the economics and exposure profile of the facility studied in the thesis. Explain how the billing cycle, payment window, utilization, and existing debt affect lender exposure.

### 2.3 Corporate Credit Scoring

Review traditional expert systems, scorecards, internal ratings, and data-driven borrower assessment. Explain the difference between ranking borrowers and estimating calibrated probabilities.

### 2.4 Financial Ratio Analysis

Explain why liquidity, leverage, profitability, cash flow, working capital, debt-service capacity, size, and trends are relevant to short-term repayment capacity and deterioration risk.

### 2.5 Statistical and Machine Learning Models

Introduce logistic regression, regularization, random forests, and gradient boosting. Compare interpretability, non-linearity, interaction handling, overfitting risk, and calibration.

### 2.6 Credit Limit Determination

Review risk-based limits, capacity-based limits, expected-loss concepts, concentration or exposure caps, floors, and policy overlays. Establish why a risk score alone is not a monetary limit.

### 2.7 Dynamic Limit Management

Discuss periodic reassessment, information availability, smoothing, hysteresis or change thresholds, and controls that prevent excessive month-to-month limit changes.

### 2.8 Research Gap

Identify the gap addressed by the thesis: many studies predict credit risk, but fewer show how to convert calibrated risk estimates into explainable, operationally stable short-term corporate limits.

## 3 Data and Target Definition

### 3.1 Study Population and Observation Unit

Define the companies included, selection rules, industry treatment, observation period, and whether each row represents a company-month, company-quarter, or another decision date.

### 3.2 Data Sources

Describe the financial-statement, company, market, and macroeconomic sources. State the publication or availability date used for every source so the analysis can avoid look-ahead bias.

### 3.3 Credit Risk Target

Define one primary event unambiguously. State what counts as default, delinquency, or financial distress; the forward horizon; how repeated observations are handled; and why the target is suitable for the available data.

For a public-data study, do not describe the target as 60-day delinquency unless actual payment-performance data is available. Use a defensible public-data distress or default proxy and explain how its estimated probability informs a facility with up to 60 days of exposure.

### 3.4 Feature Construction

Define each feature, its formula, source statement, units, lag, and expected economic relationship with risk. Group features into liquidity, leverage, profitability, cash flow, working capital, debt service, size, and trend variables.

### 3.5 Data Preprocessing

Explain missing-value treatment, winsorization or outlier handling, scaling, categorical encoding, duplicate handling, and any exclusion rules. Fit all learned preprocessing steps only on training data.

### 3.6 Exploratory Data Analysis

Show target frequency, time distribution, industry composition, summary statistics, missingness, correlations, and selected variable distributions. Focus on evidence that affects modeling decisions.

### 3.7 Data Limitations

Discuss reporting frequency, survivorship risk, restatements, target noise, class imbalance, and the difference between listed-company information and data normally available in private-company lending.

## 4 Risk Modeling and Validation Methodology

### 4.1 Modeling Framework

Present the end-to-end flow from information available at a decision date to features, predicted risk, calibrated probability, and model evaluation.

### 4.2 Baseline Models

Specify a simple benchmark and logistic regression. Include regularized logistic regression to control instability and multicollinearity.

### 4.3 Non Linear Models

Specify random forest and one gradient-boosting model. Document the main hyperparameters and the tuning range without turning the thesis into an exhaustive model search.

### 4.4 Chronological Validation Design

Define separate chronological training, tuning, calibration, model-selection and final-test periods. Purge observations whose outcome windows or label availability cross the next stage boundary. Explain how company overlap and time leakage are controlled. Fix the dates after the event-coverage audit and before fitting.

### 4.5 Class Imbalance and Decision Thresholds

Describe unweighted and class-weighted training. Keep calibration and evaluation at the observed event prevalence. Select the classification threshold on the model-selection period by highest F1, with higher recall as the tie-breaker. The credit-limit policy uses continuous probabilities, not this classification threshold.

### 4.6 Evaluation Metrics

Report ROC-AUC, average precision, recall, precision, F1-score, Brier score, and calibration measures. Distinguish average precision from trapezoidal precision-recall area. Include confusion matrices at the selected operating point.

### 4.7 Probability Calibration

Explain how calibration is measured and, if required, improved. This section is essential because the probability feeds directly into the credit-limit policy.

### 4.8 Model Interpretability

Use coefficients for linear models and feature importance or SHAP-style explanations for tree models. Include global findings and a small number of borrower-level examples.

### 4.9 Model Selection Rule

Choose the model on the separate model-selection period before the final test. Require average precision above the period's event share and Brier score below the constant training-prevalence predictor. Among eligible models select the lowest Brier score, using simplicity for exact ties. If none qualifies, report that no predictive improvement was validated.

## 5 Credit Limit Methodology

### 5.1 Design Principles

Define the desired properties of the limit: explainable, capacity-aware, risk-sensitive, capped, stable across months, and responsive to material deterioration.

### 5.2 Borrower Capacity Component

Construct a base capacity amount using selected measures such as revenue, operating cash flow, liquidity, debt-service coverage, and existing debt. Explain every coefficient or policy parameter economically.

### 5.3 Risk Adjustment Component

Map the calibrated risk estimate to a multiplier or haircut. The mapping should be monotonic: higher predicted risk must not produce a higher limit when all other inputs are unchanged.

### 5.4 Exposure Constraints and Existing Indebtedness

Define the hard exposure cap, additional external debt payments and outstanding exposure on the studied facility. Do not impose a positive floor that exceeds supported capacity. Separate the assigned total limit from available new credit and exposure above a reduced limit.

### 5.5 Final Limit Formula and Worked Example

Present one explicit formula or decision sequence combining base capacity, the risk adjustment, existing indebtedness, and policy constraints. Include a worked numerical example.

### 5.6 Monthly Update Rule

Explain how the latest available information is carried forward between financial-reporting dates and how limits are recalculated monthly.

### 5.7 Stability Safeguards and Risk Overrides

Define smoothing, minimum-change thresholds and maximum monthly increases. Apply all decreases immediately and preserve current caps. Require documented new information for increases and a fresh assessment before reopening a zero-limit account. Define hard-stop events and data-freshness rules before simulation.

### 5.8 Governance and Explainability

List the values that a credit officer should see: model risk, key drivers, capacity amount, applied haircut, binding cap, previous limit, proposed limit, and reason for the change.

## 6 Empirical Results

### 6.1 Sample and Target Results

Summarize the final dataset, event rate, time coverage, and train-validation-test composition.

### 6.2 Baseline and Logistic Regression Results

Report predictive metrics, calibration, coefficients, threshold results, and main errors. Interpret the results in credit-risk terms.

### 6.3 Random Forest Results

Report the same core metrics and explanations using a consistent table format so the result is directly comparable with the baselines.

### 6.4 Gradient Boosting Results

Report the same evaluation set and discuss whether added complexity produces a meaningful improvement.

### 6.5 Model Comparison and Assessment of the Selected Model

Report final-test performance after the Chapter 4 selection rule has been applied on the earlier model-selection period. Assess the already selected model and benchmark comparisons without selecting a different model in response to the final-test scores.

### 6.6 Error Analysis

Examine false negatives and false positives by time, industry, and borrower condition. Identify systematic weaknesses that matter for lending decisions.

## 7 Credit Limit Results and Robustness

### 7.1 Historical Limit Backtest

Apply the selected model and policy to historical decision dates. Show the distribution of limits, changes over time, and the relationship between borrower risk, capacity, and assigned exposure.

### 7.2 Borrower Case Studies

Present several representative borrower paths: stable healthy borrower, improving borrower, gradual deterioration, sudden stress, and a case in which a policy cap binds.

### 7.3 Stability and Responsiveness

Measure month-to-month limit changes, turnover, frequency of increases and decreases, maximum changes, and response time around deterioration events.

### 7.4 Stress Scenarios

Apply a small set of transparent shocks to revenue, cash flow, leverage, liquidity, or model probability. Explain how and why each shock changes the limit.

### 7.5 Sensitivity Analysis

Vary the most important policy parameters, including the risk haircut, capacity multiple, caps, and smoothing rule. Show which conclusions remain stable.

### 7.6 Robustness Checks

Test reasonable alternative target definitions, feature sets, model windows, or subperiods. Keep the checks focused on the assumptions most likely to change the conclusion.

### 7.7 Discussion

Connect the predictive and limit-policy results to the literature and business problem. Explain where a simpler model is preferable and what the framework adds beyond a conventional score.

### 7.8 Limitations

Discuss data availability, target quality, listed-to-private-company transferability, reporting lags, model drift, macroeconomic regime change, and the fact that historical simulation is not a live lending experiment.

## 8 Conclusion

### 8.1 Summary of the Study

Restate the problem, method, and framework without repeating the full introduction.

### 8.2 Answers to the Research Questions

Answer the central question and each subquestion directly using the empirical findings.

### 8.3 Main Contributions

Summarize the predictive, methodological, and practical contributions, especially the explainable separation of risk estimation and limit assignment.

### 8.4 Practical Implications

Explain how a lender could use the framework as decision support, what controls would be required, and why expert review remains necessary.

### 8.5 Future Research

Propose extensions such as private payment data, direct 60-day delinquency modeling, additional macro indicators, utilization modeling, portfolio constraints, and prospective validation.

## References

Use one citation style consistently. Include peer-reviewed credit-risk and machine-learning literature, primary model papers where appropriate, regulatory or institutional sources, and documentation for material data sources.

## Appendix

### Appendix A Reproducibility and Code Availability

Record the primary configuration, model settings, software environment, implementation map, evidence locations and limitations of the automated disclosure review. Detailed result tables and worked examples remain in the accompanying repository rather than the thesis.

## Suggested Page Allocation

| Part | Approximate pages |
|---|---:|
| Front matter and abstract | 3–5 |
| 1 Introduction | 4–5 |
| 2 Theoretical background and literature | 8–10 |
| 3 Data and target definition | 6–8 |
| 4 Modeling and validation methodology | 7–9 |
| 5 Credit limit methodology | 6–8 |
| 6 Empirical results | 7–9 |
| 7 Limit results and robustness | 6–8 |
| 8 Conclusion | 2–3 |
| References and appendices | As needed |

The main text should target approximately 45–60 pages, close to the scale of the supplied completed-thesis example. The empirical content should receive at least as much space as the theoretical review.

## Minimum Figures and Tables to Plan

1. End-to-end framework diagram.
2. Dataset timeline and chronological split.
3. Target-event frequency over time.
4. Feature correlation or selected distribution plots.
5. Model comparison table.
6. Calibration curves for shortlisted models.
7. Confusion matrix at the chosen threshold.
8. Feature importance or coefficient plot.
9. Final credit-limit formula or decision flow.
10. Limit paths for representative borrowers.
11. Limit stability and change-distribution table.
12. Stress-scenario and sensitivity-results table.

## Decisions to Lock Before Writing the Empirical Chapters

1. The company universe and geographical coverage.
2. The exact public data sources and observation period.
3. The observation unit and information-availability rule.
4. One primary risk event and its forward horizon.
5. The treatment of companies without an observed event.
6. The final benchmark and non-linear models.
7. The validation windows and model-selection rule.
8. The borrower-capacity formula.
9. The risk-to-limit mapping and policy caps.
10. The monthly smoothing and override rules.
