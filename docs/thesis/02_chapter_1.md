# 1 Introduction

## 1.1 Background

Companies often pay suppliers before customers pay them. Short-term credit bridges this gap, but an excessive limit creates exposure the borrower may not repay, while an insufficient limit restricts useful activity.

The studied facility has a 30-day statement period and up to 30 further days for payment. A transaction early in the period can therefore remain scheduled for about 60 days, motivating the prediction horizon. The limit covers all outstanding balances, including unpaid earlier amounts. Reducing it restricts new borrowing but does not remove existing debt.

Financial statements describe liquidity, profitability and cash generation. Statistical models can combine these measures into risk estimates, building on financial-ratio classification, logistic bankruptcy prediction and time-varying models. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

## 1.2 Research Problem

A risk estimate does not determine a monetary limit: companies with similar estimated risk can differ greatly in revenue, cash and repayment capacity. The problem is to combine these dimensions in a transparent rule that responds to deterioration while requiring new support for increases.

SEC statements and filing histories do not contain payment records for the proposed facility. The empirical target is therefore a **new bankruptcy or payment-failure disclosure episode within 60 days**: Item 1.03 bankruptcy or receivership filings, plus Item 2.04-only filings whose reviewed evidence explicitly describes a missed debt payment. The model estimates disclosure probability, not facility default. Filing and underlying-event dates can differ. Consequently, the study evaluates disclosure prediction and policy behavior, not lender losses or profits. [SEC, Form 8-K](https://www.sec.gov/files/form8-k.pdf).

## 1.3 Research Questions

1. Can monthly point-in-time financial information predict a qualifying disclosure within 60 days better than a constant event-rate benchmark?
2. Do random forest and gradient boosting improve prediction over logistic regression under the same chronological design?
3. How can estimated probability, financial capacity and an exposure cap produce a transparent monetary limit?
4. How do monthly limits respond to new information, risk changes and alternative policy assumptions?

## 1.4 Objectives and Contribution

The study constructs a monthly panel from SEC Company Facts, Financial Statement and Notes data, and submissions, retaining reporting periods, filing dates and sources. It compares logistic regression, L2-regularized logistic regression, random forest and XGBoost on twelve accounting predictors using separate chronological stages for fitting, tuning, calibration, selection and later evaluation.

The policy combines annual revenue, operating cash flow and eligible cash into capacity, then applies a decreasing risk multiplier, an exposure cap and asymmetric monthly update rules. Historical replay examines movements, binding constraints and sensitivity. The contribution is a reproducible connection between dated accounting information, disclosure prediction and monetary limits while keeping observed data distinct from assumed facility inputs.

This separation is central to the design. A model may rank risky companies without producing probabilities accurate enough for a monetary calculation, while a sound probability still cannot determine exposure without evidence of repayment capacity. The thesis therefore reports ranking, probability error and alert performance before evaluating the policy as a separate layer. Its saved code, tables and figures make both layers auditable.

## 1.5 Scope and Limitations

The study covers eligible SEC issuers from January 2011 to December 2025, excluding current SIC 6000–6999 because financial-sector statements are not comparable with ordinary operating companies. It uses an observed reporting population rather than a complete historical listing universe.

The retrospective later evaluation covers 2023–2025. These years were excluded from the final model's development but examined during earlier project work. Companies may appear in multiple periods, reflecting continued monitoring. The replay assumes cash eligibility, additional debt payments and facility exposure, and lacks observed utilization, repayments and losses.

Financial values are stated in USD and generally update only when a new filing appears. The resulting monthly panel is therefore a sequence of decision-time information sets, not monthly management accounts. These scope choices limit claims about private-company lending and changes between reporting dates.

## 1.6 Structure of the Thesis

Chapter 2 reviews concepts and literature. Chapters 3–4 define data and validation. Chapter 5 specifies the policy. Chapters 6–7 present predictive and policy results, and Chapter 8 concludes. Appendix A records reproducibility details.
