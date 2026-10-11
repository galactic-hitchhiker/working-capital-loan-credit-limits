# 1 Introduction

## 1.1 Background

Companies often pay suppliers before receiving money from customers. Short-term credit helps them manage this timing difference, but the lender must decide how much credit the company can use. A limit that is too high may create exposure the borrower cannot repay; a limit that is too low may restrict useful business activity.

This thesis studies a corporate facility with a 30-day statement period and up to 30 additional days for payment. A transaction at the beginning of a statement period can therefore remain outstanding for about 60 days before its scheduled payment date. This schedule motivates the prediction horizon. Exposure can continue for longer if payment is missed.

The credit limit is the maximum permitted total outstanding balance, including unpaid amounts from earlier periods. Available credit is the unused part of that limit. Reducing a limit restricts further borrowing but does not remove existing debt.

Financial statements provide information about liquidity, profitability and cash generation. Statistical models can combine these measures into a risk estimate. Financial-ratio classification, logistic bankruptcy prediction and models that account for changing information provide the background for this study. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

## 1.2 Research Problem

A risk estimate does not directly specify a monetary limit. Companies with similar estimated risk can have different revenue, cash resources and repayment capacity. The research problem is to combine these dimensions in a clear limit rule and update it as information changes. Increases require support from new information, while reductions should respond promptly to deterioration.

The available data also constrain the analysis. SEC financial statements and filing histories do not contain payment records for the proposed facility. The empirical target is therefore a **new bankruptcy or payment-failure disclosure episode within the next 60 calendar days**. Item 1.03 bankruptcy or receivership filings qualify; Item 2.04-only filings qualify when reviewed evidence explicitly describes a missed debt payment. Chapter 3 defines episode grouping and eligibility.

The model estimates a disclosure probability. Filing dates can differ from the dates of the underlying events, and the records do not establish default on the proposed facility. The study can evaluate disclosure prediction and the behavior of a limit policy, but cannot estimate the losses or profits a lender would have experienced. [SEC, Form 8-K](https://www.sec.gov/files/form8-k.pdf).

## 1.3 Research Questions

The thesis addresses four questions:

1. Can financial information available at monthly decision dates predict a new bankruptcy or payment-failure disclosure episode within the next 60 days better than a constant event-rate benchmark?
2. Do random forest and gradient boosting improve prediction compared with logistic regression under the same chronological evaluation design?
3. How can the estimated probability be combined with financial capacity and an exposure cap to produce a clear monetary limit?
4. How do monthly limits respond to new financial information, changes in estimated risk and alternative policy assumptions?

The first two questions concern prediction. The last two concern policy design and historical simulation.

## 1.4 Objectives and Contribution

The first objective is to construct a monthly dataset from SEC company facts, submissions and imported statement data. Each financial observation retains its reporting period, filing date and source. Only information available at the decision date can enter a prediction.

The study then compares logistic regression, L2-regularized logistic regression, random forest and XGBoost using twelve accounting predictors. Separate chronological periods support fitting, tuning, calibration, model selection and later evaluation. This design evaluates both the ranking of companies and the quality of their estimated probabilities.

The policy combines annual revenue, annual operating cash flow and eligible cash into a capacity measure. A decreasing risk multiplier and an exposure cap determine the preliminary limit. Monthly rules restrict increases and apply reductions immediately. Historical replay examines limit movements, binding constraints and sensitivity to the assumed policy settings.

The contribution is a reproducible framework connecting dated financial information, disclosure prediction and monetary limits. It preserves the distinction between observed accounting data and assumed facility inputs. A matched comparison also examines whether additional statement facts improve predictor coverage and model performance. Supporting Python files, tables and figures allow the analysis to be checked and reproduced.

## 1.5 Scope and Limitations

The study covers monthly decisions from January 2011 to December 2025 for eligible SEC issuers with usable financial data and filing histories. Financial amounts are reported in USD, and issuers in the current SIC range 6000–6999 are excluded. The sample is an observed reporting population rather than a complete historical listing universe. Chapter 3 gives the screening and information-availability rules.

The later evaluation covers 2023–2025. These years are excluded from model development within the final run, but were examined during earlier project work. The evaluation is therefore retrospective. Companies may appear in both earlier and later periods, reflecting continued monitoring rather than evaluation on an entirely separate borrower population.

The policy replay assumes cash eligibility, additional debt payments and facility exposure. It evaluates the resulting limits without observed utilization, repayments or lending losses. Chapter 8 discusses how these limitations affect the conclusions.

## 1.6 Structure of the Thesis

Chapter 2 presents the relevant concepts and literature. Chapters 3 and 4 explain the data, disclosure target, predictors and model evaluation. Chapter 5 defines the credit-limit policy and its monthly rules.

Chapters 6 and 7 report predictive results and policy scenarios. Chapter 8 discusses the findings, limitations and further work. The appendices provide variable definitions, implementation details, supplementary results and worked examples.
