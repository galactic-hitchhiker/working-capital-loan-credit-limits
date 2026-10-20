<!--
Draft report for formal review by the Commission.
Complete every bracketed administrative placeholder before approval or signature.
-->

**UNION UNIVERSITY – SCHOOL OF COMPUTING**  
Knez Mihailova 6/VI, 11000 Belgrade  
[raf.edu.rs](https://raf.edu.rs/) · [raf@raf.rs](mailto:raf@raf.rs)

**TO THE TEACHING AND SCIENTIFIC COUNCIL OF THE SCHOOL OF COMPUTING IN BELGRADE**

*The Teaching and Scientific Council of the School of Computing in Belgrade, at its [SESSION NUMBER] session held on [SESSION DATE], appointed us to the Commission for the review and evaluation of the master’s thesis submitted by Đorđe Veličković, student ID [STUDENT ID], under the title “Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning”, prepared under the supervision of Prof. Dr. Branko Urošević. After reviewing the thesis, the Commission submits the following:*

# REPORT

## 1. Biographical data of the candidate

Đorđe Veličković is a software and data engineer with professional experience in financial technology and large-scale data systems. He has worked at Rho as a Senior Data Engineer since 2022. Previously, he worked as a Software Engineer at Kindred Group plc / Hooloovoo from 2020 to 2022, as a Junior Software Engineer and Software Engineer at Centili from 2018 to 2020, and as a Software Engineer Intern at Infobip in 2017.

The candidate is enrolled in the Master in Computational Finance programme at the School of Computing, Union University. He completed a master’s programme in Software Engineering at the same institution in 2023 and a bachelor’s programme in Computer Science in 2019. His principal technical skills include SQL, Python and Java, with a professional focus on data engineering and software engineering. He has professional working proficiency in English.

## 2. Description of the master thesis

The master’s thesis comprises 45 pages in the submitted Word edition and cites 15 sources. It contains an abstract, eight chapters, a reference list and a reproducibility appendix. The thesis examines how point-in-time accounting information and machine-learning estimates can be combined in a transparent framework for dynamic short-term corporate credit limits.

The empirical study combines SEC Company Facts, Financial Statement and Notes data, and submissions in a monthly panel covering 2011–2025. The completed modeling panel contains 565,222 labeled company-month observations from 8,780 companies. Twelve accounting predictors describe liquidity, leverage, profitability, cash generation, growth and company size. The outcome is a new bankruptcy or reviewed payment-failure disclosure episode within 60 days. The candidate clearly distinguishes this disclosure proxy from verified default on a lending facility.

Four model families are compared using a chronological development design: logistic regression, L2-regularized logistic regression, random forest and XGBoost. The thesis then translates the selected probability into a preliminary limit through a financial-capacity proxy, a probability-based risk adjustment and an exposure cap. Monthly update rules introduce immediate reductions, controlled increases, a deadband and explicit hard stops.

The work is logically organized and supported by documented filters, formulas, tables, figures and reproducibility material. The candidate also states the main empirical limitations directly: the automated Item 2.04 payment-failure classifications were not independently validated, the later evaluation is retrospective, and facility utilization, repayment, loss, pricing and profitability data are unavailable.

## 3. Analysis of the work and key results

The selected random forest produces a meaningful ranking signal on 131,842 company-month observations from 2023–2025. It achieves ROC-AUC of 0.8866 and average precision of 2.5989%, or 10.77 times the 0.2412% event share. Its Brier score is 0.0023840, which is 0.95% better than the constant-probability benchmark. At the frozen alert threshold, precision is 5.63% and recall is 9.12%, so the results support cautious use as a risk-ranking input rather than a complete default-detection system.

The historical policy replay covers 99,619 observations from 3,869 companies. Under the reference assumptions, the median assigned limit is USD 4.23 million, the mean assigned limit is 0.668% of reported assets, and 72.05% of monthly transitions leave the limit unchanged. Sensitivity analysis shows that cash eligibility, assumed near-term debt payments and the exposure cap have a larger aggregate effect than the probability multiplier. This is an important practical result because it identifies the assumptions that require lender-specific evidence before implementation.

## 4. Conclusion and proposal

In the submitted master’s thesis, Đorđe Veličković demonstrates knowledge of corporate credit-risk modeling, chronological validation, rare-event evaluation and rule-based credit-limit design. The candidate connects the predictive and policy components coherently, documents the empirical evidence, and interprets the results with appropriate caution.

Subject to confirmation of the official administrative details and the signatures below, the Commission proposes that the Teaching and Scientific Council accept the master’s thesis entitled “Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning” and approve its public oral defense.

Belgrade, **[REPORT DATE]**

**Members of the Commission:**

Signature: _________________________________________  
Prof. Dr. Branko Urošević (**[ROLE]**)

Signature: _________________________________________  
**[COMMISSION MEMBER] ([ROLE])**

Signature: _________________________________________  
**[COMMISSION MEMBER] ([ROLE])**
