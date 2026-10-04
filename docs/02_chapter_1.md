# 1 Introduction

## 1.1 Background

Companies often pay suppliers before they receive money from customers. Short-term credit can help them manage this timing difference and continue their daily operations. The lender must decide both whether to provide credit and how much credit the company can use. A limit that is too high may create exposure that the borrower cannot repay. A limit that is too low may restrict useful business activity.

This thesis studies a corporate facility with a 30-day statement period and up to 30 additional days for payment. A transaction made at the beginning of a statement period can therefore remain outstanding for about 60 days before its scheduled payment date. This is the exposure horizon used to motivate the study. It is not a period of overdue payment. If payment is missed, actual exposure can continue for longer.

The credit limit is the maximum total outstanding balance on the facility. It includes unpaid amounts from earlier statement periods. Available credit is the part of the limit that has not already been used. This distinction is important because a limit reduction does not remove an existing debt.

Financial statements provide information about liquidity, profitability, cash generation and company size. However, they are published with a delay, and they do not directly show how a particular facility will be used or repaid. Credit assessment must distinguish between the information observed in the data and the assumptions needed to make a lending decision.

Statistical and machine learning models can combine financial indicators into a risk estimate. The historical literature includes financial-ratio classification, logistic bankruptcy prediction and models that account for changes through time. These approaches provide the background for this thesis. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

## 1.2 Research Problem

A risk estimate does not directly specify a monetary limit. Two companies can have similar estimated risk but very different revenue, cash resources and repayment capacity. A practical limit framework needs to combine these dimensions and explain how each affects the final amount.

The first problem is to estimate a clearly defined event probability from information available at the decision date. The second is to translate that estimate into a limit. The third is to update the limit over time while avoiding unsupported increases and allowing prompt reductions.

There is also a data problem. The supplied SEC dataset contains financial facts and filing histories, but it does not contain the payment history of the proposed facility. It cannot directly support a model of 60-day payment default, utilization or recovery. The empirical target is therefore the company's **first recorded Form 8-K or 8-K/A Item 1.03 disclosure within the next 60 calendar days**.

Item 1.03 concerns bankruptcy or receivership-related disclosures. Its filing date is a reporting event and may differ from the date of the underlying legal event. The model output is therefore called a *60-day disclosure probability*. It is not called a payment-default probability. [SEC, Form 8-K](https://www.sec.gov/files/form8-k.pdf).

This definition allows the study to use observed outcomes from the supplied data. It also limits the conclusions. The research can test disclosure prediction and the behavior of a proposed limit policy, but it cannot establish the losses or profits that a lender would have experienced.

## 1.3 Research Questions

The thesis addresses four questions:

1. Can financial information available at monthly decision dates predict a first recorded Item 1.03 disclosure within the next 60 days better than a constant event-rate benchmark?
2. Do random forest and gradient boosting improve prediction compared with logistic regression under the same chronological evaluation design?
3. How can the estimated probability be combined with financial capacity and an exposure cap to produce a clear monetary limit?
4. How do monthly limits respond to new financial information, changes in estimated risk and alternative policy assumptions?

The first two questions concern prediction. The last two concern policy design and historical simulation. A useful answer to one group does not automatically establish a useful answer to the other.

## 1.4 Research Objectives

The first objective is to construct a monthly dataset from the downloaded SEC company facts and submissions. The construction records reporting periods, filing dates and the source of each selected financial fact. Later filings must not enter an earlier decision.

The second objective is to compare unregularized logistic regression, L2-regularized logistic regression, random forest and XGBoost. All models use the same 12 point-in-time predictors covering liquidity, leverage, profitability, cash flow, growth and company size. Separate chronological periods are used for fitting, rolling temporal tuning, calibration, model selection and held-out evaluation.

The third objective is to define a reproducible credit-limit policy. It combines a capacity proxy based on annual revenue, annual operating cash flow and cash with a decreasing risk multiplier and an explicit cap. Monthly rules restrict increases, while reductions follow the current calculation immediately.

The fourth objective is to evaluate the policy on real financial histories and model probabilities, with unavailable facility inputs represented by stated scenarios. The analysis examines limit movements, binding constraints, response to disclosures and sensitivity to policy parameters.

The final objective is to provide supporting Python files and result tables so that the analysis can be reviewed and reproduced. File references are included throughout the thesis.

## 1.5 Contributions

The main contribution is an implemented connection between dated financial information, a defined reporting-event probability and a monetary credit-limit rule. Each part has a clear role. The model estimates a probability; the capacity calculation describes financial resources under stated assumptions; the policy determines the limit.

A second contribution is the explicit treatment of information timing. Financial periods are separated from filing dates, labels require observable follow-up, and observations are removed from an earlier modeling stage when their outcomes are not yet available at the next stage boundary.

A third contribution is the distinction between predictive evidence and policy assumptions. The model uses real SEC records. Eligible cash, near-term additional debt payments and facility exposure are not claimed to be observed when the dataset does not establish them.

The study does not claim to introduce a new prediction algorithm or to estimate an optimal lending rule. Its contribution is an auditable research implementation and an assessment of its strengths and limits.

## 1.6 Scope and Limitations

The study covers monthly decision dates from January 2011 to December 2025. It starts from the supplied company-facts inventory and retains eligible issuers with domestic periodic filings, adequate financial data and complete referenced submission archives. The current SIC range 6000–6999 is excluded. Current ticker status is not used as a requirement, so a company is not removed simply because it is no longer listed.

This is an observed SEC reporting sample, not a complete reconstruction of the historical population of listed US companies. Current industry codes may differ from historical codes. Companies without usable standard US-GAAP facts in USD are outside the implemented scope.

The predictors describe liquidity, cash holdings, leverage, working capital, profitability, operating cash flow, growth and size. The study does not include market prices, payment behavior, news or macroeconomic predictors. Annual flows are the last reported annual amounts, not trailing twelve-month estimates.

The held-out evaluation covers 2023–2025. Companies can appear in both earlier and later periods, which reflects monitoring existing borrowers. The evaluation does not establish performance on entirely new companies. These years were excluded from fitting, tuning, calibration, selection and threshold setting in the reported run, but they were examined during earlier project development. They are therefore not presented as a completely untouched external validation sample. Repeated observations and overlapping 60-day windows are considered when interpreting uncertainty.

The limit analysis is a historical scenario simulation. Reported cash is used under an explicit eligibility assumption. Additional debt service and facility exposure are specified as assumptions. No realized loan losses, recovery rates or lending profits are estimated.

## 1.7 Structure of the Thesis

Chapter 2 presents the credit-risk concepts and literature. Chapter 3 explains the SEC dataset, the disclosure target and financial predictors. Chapter 4 describes the models and chronological validation. Chapter 5 defines the limit policy and its monthly rules.

Chapter 6 reports the empirical predictive results. Chapter 7 evaluates the resulting policy scenarios, historical paths and sensitivity analysis. Chapter 8 answers the research questions and presents the conclusions. The appendices provide variable definitions, reproducibility instructions, supplementary results and worked policy examples.

File references: mcf/data/empirical.py, mcf/data/point_in_time.py, study.sec_disclosure.json, mcf/models/train.py, mcf/policy/credit.py.
