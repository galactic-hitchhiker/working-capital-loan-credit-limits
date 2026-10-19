# 2 Theoretical Background and Literature Review

This chapter explains the concepts needed to separate credit-risk prediction from credit-limit determination. It reviews the main model families and describes why information timing, probability quality and financial capacity matter.

## 2.1 Corporate Credit Risk

Corporate credit risk is the risk that a company will not meet its financial obligations as agreed. Several related outcomes must be distinguished. Delinquency means that a payment is overdue. Default means that a borrower meets a defined failure-to-pay or other default condition. Financial distress describes difficulty in meeting obligations. Bankruptcy is a formal legal process. These outcomes can be related without being identical.

Expected credit loss is commonly separated into three components. Probability of default (PD) is the likelihood that the borrower defaults within a defined period. Exposure at default (EAD) is the amount the lender expects to be owed when default occurs; it may differ from the current balance because the borrower can draw or repay funds before then. Loss given default (LGD) is the proportion of that exposure the lender expects not to recover after default. A simplified expected-loss (EL) amount is therefore:

$$ EL = PD \times LGD \times EAD. \tag{1} $$

This decomposition distinguishes how likely default is, how much would be outstanding and how severe the resulting loss would be. Combining the components requires consistent definitions and time horizons, as well as separate evidence about default events, exposure, recoveries, collection costs and their timing.

The empirical outcome in this thesis is an SEC disclosure. Its probability cannot be inserted into the default-loss formula as if it were PD. The supplied data also does not establish facility recoveries or EAD. Expected loss is therefore a theoretical concept here, not an empirical result.

## 2.2 Short-Term Corporate Credit Facilities

Short-term credit supports working-capital needs, including payments made before customers settle invoices. The studied facility assumes a 30-day statement period and up to 30 further days for payment. A transaction at the start can therefore create about 60 days of scheduled exposure. A transaction near the end has a shorter scheduled repayment period.

The limit applies to the total outstanding balance across statement periods. If the limit is represented by L and the outstanding exposure by E, available credit is:

$$ A = \max(0,L-E). \tag{2} $$

A reduction in the limit restricts further use but leaves the outstanding debt in place. The policy therefore records the assigned limit and existing exposure separately.

The 60-day prediction horizon is motivated by this payment schedule. It does not establish that all transactions last exactly 60 days or that a disclosure during that period causes a missed payment on the facility.

## 2.3 Corporate Credit Scoring

Credit scoring combines borrower information into a measure of credit quality. The output can be a score, a category or an event probability. A score and a calibrated probability are different objects.

Altman (1968), Ohlson (1980) and Shumway (2001) provide three relevant approaches. Altman combines financial ratios through discriminant analysis to classify bankrupt and non-bankrupt firms. Ohlson uses logistic regression to express bankruptcy risk as a probability. Shumway uses a hazard approach that accounts for event timing and changing company information. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

These approaches motivate different parts of this study: accounting ratios describe financial condition, logistic regression provides a probability benchmark, and attention to time supports repeated borrower assessment. Their published coefficients and performance cannot be transferred directly because the target, population and horizon differ. The thesis therefore compares models on one common dataset and outcome.

The present model is a monthly classifier for a disclosure within the next 60 days. It uses changing company information but does not estimate a survival model or daily hazard. This choice matches the proposed review schedule while retaining a simple binary outcome.

A predictive model must be assessed for both discrimination and calibration. Discrimination asks whether later event observations generally receive higher scores than non-events; calibration asks whether estimated probabilities correspond to observed event frequencies. A ranking may prioritize reviews even when its probability scale is poor, but the monetary policy uses the probability itself. Chapter 4 therefore evaluates both properties.

## 2.4 Financial Ratio Analysis

Financial ratios compare accounting values to make companies of different sizes easier to assess. They help answer practical questions such as whether a company has enough short-term resources, relies heavily on liabilities, earns a profit or generates cash. Ratios must still be interpreted carefully because companies have different business models. For example, two companies can have the same current ratio even though one holds mainly cash and the other holds inventory that may take time to sell.

Liquidity measures compare near-term resources with obligations, although cash may be restricted and receivables or inventory may convert slowly. Leverage indicates reliance on liabilities and the equity buffer available to absorb losses. Profitability and operating cash flow provide different information because accounting income need not produce cash. Changes over time may reveal deterioration or rapid expansion that current levels miss, while company size provides context without guaranteeing safety.

These measures do not show exactly how much debt must be paid during the next 60 days. Total liabilities are measured at one date, while debt service consists of interest and principal payments due over time. The ratios are therefore indicators of general financial condition rather than direct measures of short-term repayment capacity. Chapter 3 defines the twelve predictors and their construction and timing rules.

## 2.5 Statistical and Machine Learning Models

A model learns relationships between the twelve predictors and later events from earlier observations. The four candidates trade simplicity for flexibility.

### 2.5.1 Logistic regression

Logistic regression combines weighted predictors into a probability between zero and one. It is fast, inspectable and provides an interpretable benchmark, but its simple functional form may miss thresholds and interactions. Its coefficients describe associations, not causal effects.

### 2.5.2 Regularized logistic regression

Regularized logistic regression discourages very large coefficients. This can stabilize correlated predictors and reduce sensitivity to accidental training patterns, but excessive regularization may suppress useful relationships and does not add nonlinearities. Its strength is selected on earlier data. [Scikit-learn 1.6, logistic regression](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression).

### 2.5.3 Random forest

A random forest combines decision trees trained on different selections of observations and predictors. It can learn thresholds, nonlinearities and interactions without specifying them in advance. The cost is lower transparency, a risk that patterns will not persist, and probabilities that may require calibration. Tree-size and leaf-size controls limit complexity. [Breiman (2001)](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).

### 2.5.4 Gradient boosting

Gradient boosting builds trees sequentially, with each tree improving weaknesses in the current ensemble. XGBoost can learn detailed thresholds and interactions in structured data, but may overfit rare events and is less transparent than logistic regression. Its behavior also depends on settings such as depth and learning rate. All candidates use the same predictors and later evaluation periods. [Friedman (2001)](https://doi.org/10.1214/aos/1013203451), [Chen and Guestrin (2016)](https://arxiv.org/abs/1603.02754).

### 2.5.5 Evaluation and interpretation

Accuracy is unsuitable for this rare outcome because predicting no events could appear successful. Evaluation instead considers ranking and probability quality.

Precision is the share of alerts followed by events; recall is the share of events detected. Flagging more companies generally raises recall at the cost of false alerts, making precision-recall analysis useful here. [Saito and Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).

The Brier score summarizes the difference between estimated probabilities and actual outcomes, while calibration summaries compare estimated probabilities with observed event rates. These measures are important because the selected probability enters the credit-limit framework. [Brier (1950)](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2).

Model explanations must also be treated carefully. Coefficients and variable-importance measures describe patterns used by a fitted model. They can help explain how the model makes predictions, but they do not prove that a financial characteristic causes or prevents the target event.

## 2.6 Credit Limit Determination

A probability describes the chance of an event. A credit limit specifies a monetary exposure. The proposed framework connects them through three components:

$$ L_{i,t}^{*}=\min\left(K_{i,t}, C_{i,t}g(q_{i,t})\right). \tag{3} $$

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
