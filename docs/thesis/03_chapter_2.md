# 2 Theoretical Background and Literature Review

This chapter explains the concepts needed to separate credit-risk prediction from credit-limit determination. It reviews the main model families and describes why information timing, probability quality and financial capacity matter.

## 2.1 Corporate Credit Risk

Corporate credit risk is the risk that a company will not meet its financial obligations as agreed. Several related outcomes must be distinguished. Delinquency means that a payment is overdue. Default means that a borrower meets a defined failure-to-pay or other default condition. Financial distress describes difficulty in meeting obligations. Bankruptcy is a formal legal process. These outcomes can be related without being identical.

Expected credit loss is commonly separated into three components. Probability of default (PD) is the likelihood that the borrower defaults within a defined period. Exposure at default (EAD) is the amount the lender expects to be owed when default occurs; it may differ from the current balance because the borrower can draw or repay funds before then. Loss given default (LGD) is the proportion of that exposure the lender expects not to recover after default. A simplified expected-loss (EL) amount is therefore:

$$ EL = PD \times LGD \times EAD. $$

This decomposition distinguishes how likely default is, how much would be outstanding and how severe the resulting loss would be. Combining the components requires consistent definitions and time horizons, as well as separate evidence about default events, exposure, recoveries, collection costs and their timing.

The empirical outcome in this thesis is an SEC disclosure. Its probability cannot be inserted into the default-loss formula as if it were PD. The supplied data also does not establish facility recoveries or EAD. Expected loss is therefore a theoretical concept here, not an empirical result.

## 2.2 Short-Term Corporate Credit Facilities

Short-term credit supports working-capital needs, including payments made before customers settle invoices. The studied facility assumes a 30-day statement period and up to 30 further days for payment. A transaction at the start can therefore create about 60 days of scheduled exposure. A transaction near the end has a shorter scheduled repayment period.

The limit applies to the total outstanding balance across statement periods. If the limit is represented by L and the outstanding exposure by E, available credit is:

$$ A = \max(0,L-E). $$

A reduction in the limit restricts further use but leaves the outstanding debt in place. The policy therefore records the assigned limit and existing exposure separately.

The 60-day prediction horizon is motivated by this payment schedule. It does not establish that all transactions last exactly 60 days or that a disclosure during that period causes a missed payment on the facility.

## 2.3 Corporate Credit Scoring

Credit scoring combines borrower information into a measure of credit quality. The output can be a score, a category or an event probability. A score and a calibrated probability are different objects.

Altman (1968), Ohlson (1980) and Shumway (2001) provide three relevant approaches. Altman combines financial ratios through discriminant analysis to classify bankrupt and non-bankrupt firms. Ohlson uses logistic regression to express bankruptcy risk as a probability. Shumway uses a hazard approach that accounts for event timing and changing company information. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

These approaches motivate different parts of this study: accounting ratios describe financial condition, logistic regression provides a probability benchmark, and attention to time supports repeated borrower assessment. Their published coefficients and performance cannot be transferred directly because the target, population and horizon differ. The thesis therefore compares models on one common dataset and outcome.

The present model is a monthly classifier for a disclosure within the next 60 days. It uses changing company information but does not estimate a survival model or daily hazard. This choice matches the proposed review schedule while retaining a simple binary outcome.

A predictive model can be useful in two different ways. First, it can distinguish relatively higher-risk companies from relatively lower-risk companies. This quality is called discrimination. A model has useful discrimination when companies that later experience the target disclosure event generally receive higher scores than companies that do not. Discrimination is therefore mainly concerned with the ordering of observations rather than with the exact numerical value of each prediction.

Second, the estimated probabilities should correspond reasonably well to observed event frequencies. This quality is called calibration. For example, if the model assigns a probability of 10% to a group of comparable company-month observations, approximately 10% of those observations should experience the target event within the stated horizon. If only 2% do so, the model overstates the probability even though it may still rank companies correctly.

The distinction matters because different decisions require different properties. A well-ranked score can help determine which companies should be reviewed first. A monetary rule, however, uses the size of the estimated probability and therefore also requires an appropriate probability scale. If an overstated probability directly reduces a credit limit, the resulting limit may be unnecessarily restrictive. Chapter 4 therefore evaluates both the model's ability to rank observations and the accuracy of its probability estimates.

## 2.4 Financial Ratio Analysis

Financial ratios compare accounting values to make companies of different sizes easier to assess. They help answer practical questions such as whether a company has enough short-term resources, relies heavily on liabilities, earns a profit or generates cash. Ratios must still be interpreted carefully because companies have different business models. For example, two companies can have the same current ratio even though one holds mainly cash and the other holds inventory that may take time to sell.

Liquidity measures describe the company's ability to cover obligations due in the near future. The current ratio compares current assets with current liabilities, while working capital measures the difference between them. Cash relative to assets provides a narrower view of available resources. However, reported cash may be restricted or needed to keep the business operating, and receivables or inventory may not be converted into cash quickly.

Leverage measures show how much of the company's assets are financed by liabilities. A company with high or increasing leverage may have less room to absorb financial difficulties, although the meaning depends on the type and timing of its obligations. Profitability and cash flow provide different information. A company can report a profit without receiving the related cash, so the model considers both accounting income and cash generated by normal operations.

Changes over time can also reveal information that a single financial statement cannot. Rapid growth may show successful expansion, but it may also require additional borrowing. A reduction in assets may reflect either improved efficiency or financial pressure. Company size provides further context, but a larger company is not automatically safer.

These measures do not show exactly how much debt must be paid during the next 60 days. Total liabilities are measured at one date, while debt service consists of interest and principal payments due over time. The ratios are therefore indicators of general financial condition rather than direct measures of short-term repayment capacity. Chapter 3 defines the twelve predictors and their construction and timing rules.

## 2.5 Statistical and Machine Learning Models

A model looks for patterns that connect the twelve financial predictors to the target event. It learns these patterns from earlier company observations and then estimates the probability of an event for later observations. This study compares four models. They range from a simple and easy-to-explain method to more flexible methods that can identify complicated relationships.

### 2.5.1 Logistic regression

Logistic regression combines the financial predictors into an estimated probability between zero and one. It can be understood as a weighted checklist: each predictor contributes to the result, and the model learns how much weight to give it. For example, leverage, liquidity and cash flow can all contribute to the estimated probability.

Its main advantage is simplicity. It is fast to train, its results are relatively easy to inspect, and the direction and size of its fitted coefficients help explain which predictors are associated with higher or lower estimates. It therefore provides a useful benchmark against which more complicated models can be compared.

Its main limitation is that it represents relationships in a fairly simple form. It may not capture a sharp risk threshold or a situation in which one predictor matters only when another predictor has a particular value. Its coefficients describe patterns in the study data; they do not prove that changing a financial ratio would cause the event probability to change. Logistic regression is a good candidate because it offers an understandable starting point and directly produces probability estimates.

### 2.5.2 Regularized logistic regression

Regularized logistic regression uses the same basic approach but adds a rule that discourages the model from placing very large weights on individual predictors. This restraint is called regularization. It can be helpful when several predictors contain similar information, such as different measures of profitability or cash generation.

The main benefit is that the fitted model may be more stable and less likely to depend too strongly on accidental patterns in the training data. The disadvantage is that useful relationships can also be reduced too much if the restraint is too strong. Regularization does not solve the basic limitation of logistic regression: the model still represents relationships in a relatively simple form. The amount of regularization must therefore be selected using earlier data and checked on later observations. It is a good candidate because it tests whether a more restrained version of the understandable benchmark performs more reliably. [Scikit-learn 1.6, logistic regression](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression).

### 2.5.3 Random forest

A decision tree works like a sequence of questions. It might first ask whether cash flow is negative and then, depending on the answer, ask whether leverage is high. A random forest builds many different decision trees and combines their predictions. Each tree is trained on a somewhat different selection of observations and predictors, so the final result does not depend on a single tree. [Breiman (2001)](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).

The main advantage is flexibility. A random forest can identify thresholds, curved relationships and combinations of predictors without requiring the researcher to specify them in advance. For example, weak liquidity may be especially informative when a company also reports a loss.

The disadvantages are that a forest is harder to explain than logistic regression and can learn patterns that do not continue into later periods. Its probability estimates may also require calibration before they can be used in a monetary formula. Controls on tree size and the minimum number of observations in each branch help limit excessive complexity. A random forest is a good candidate because financial pressure may depend on combinations and thresholds that a simple model could miss.

### 2.5.4 Gradient boosting

Gradient boosting also uses decision trees, but it builds them one after another. Each new tree focuses on improving areas where the existing group of trees performs poorly. The study uses XGBoost, an efficient implementation that includes controls intended to limit unnecessary complexity. [Friedman (2001)](https://doi.org/10.1214/aos/1013203451), [Chen and Guestrin (2016)](https://arxiv.org/abs/1603.02754).

Its main advantage is that it can learn detailed patterns, including thresholds and interactions between financial measures. It often performs well on structured data such as accounting records. Its flexibility is also its main risk: the model can focus too closely on unusual features of the training data, especially when events are rare. Its results are less transparent than those of logistic regression and can change when settings such as tree depth and learning rate are changed.

Gradient boosting is a good candidate because it provides a strong flexible alternative to both logistic regression and random forest. Its inclusion does not assume that it will be the best model. All candidates are trained with the same predictors and compared on later time periods so that added complexity is accepted only when it produces useful results.

### 2.5.5 Evaluation and interpretation

No model should be selected using accuracy alone. The target event is rare, so a model that predicts "no event" for every company could be highly accurate while providing no useful warning. The evaluation must instead consider whether the model ranks event observations above non-event observations and whether its estimated probabilities match observed event rates.

Precision shows how many of the observations flagged by a model actually experience the event. Low precision means many false alerts. Recall shows how many of the actual events the model identifies. Low recall means many events are missed. There is usually a trade-off between the two: flagging more companies can detect more events but can also create more false alerts. Precision-recall analysis is therefore useful for rare outcomes. [Saito and Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).

The Brier score summarizes the difference between estimated probabilities and actual outcomes, while calibration summaries compare estimated probabilities with observed event rates. These measures are important because the selected probability enters the credit-limit framework. [Brier (1950)](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2).

Model explanations must also be treated carefully. Coefficients and variable-importance measures describe patterns used by a fitted model. They can help explain how the model makes predictions, but they do not prove that a financial characteristic causes or prevents the target event.

## 2.6 Credit Limit Determination

A probability describes the chance of an event. A credit limit specifies a monetary exposure. The proposed framework connects them through three components:

$$ L_{i,t}^{*}=\min\left(K_{i,t}, C_{i,t}g(q_{i,t})\right). $$

Here, C is a capacity proxy, K is a hard exposure cap, and g is a risk multiplier between zero and one. The preliminary limit is later subject to monthly update rules.

The multiplier must not increase when estimated risk rises, with other inputs held constant. This property is imposed by the policy design. It is not estimated from observed lending decisions.

When the exposure cap is below risk-adjusted capacity, the cap determines the preliminary limit. Changes in model probability can therefore have little aggregate effect even when the model distinguishes between companies.

The capacity calculation must avoid counting an obligation twice. An interest payment already reflected in operating cash flow should not also be deducted as an additional payment. Chapter 5 defines the treatment used.

## 2.7 Dynamic Limit Management

Dynamic management means reviewing a limit as information changes. A monthly schedule does not imply new statements each month. The system can carry the same financial values through several reviews.

The policy separates a scheduled review from a change in relevant inputs. It limits increases and applies reductions promptly. Chapter 5 specifies the update rules and the conditions for a hard stop.

Stability should be distinguished from usefulness. A limit that never changes is stable but may fail to respond to deterioration. Frequent small changes can create operational costs without improving risk control. Chapter 7 examines both movement and responsiveness.

## 2.8 Research Gap and Position of the Study

The reviewed literature provides methods for corporate failure prediction and flexible classification. This study uses those methods to examine a separate practical question: how can a dated disclosure-risk estimate enter a monthly credit-limit rule?

The policy adds monetary capacity and exposure constraints that a prediction score alone cannot supply. Its coefficients are research assumptions rather than parameters learned from lender outcomes. The contribution is therefore the implemented connection and the separate evaluation of prediction and policy behavior.

This distinction guides the empirical chapters. Model results assess ranking, probability error and event detection. Policy results assess assigned limits, changes and sensitivity. Evidence that a model predicts disclosures does not by itself establish that the resulting policy improves lending outcomes.
