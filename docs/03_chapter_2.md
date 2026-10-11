# 2 Theoretical Background and Literature Review

This chapter explains the concepts needed to separate credit-risk prediction from credit-limit determination. It reviews the main model families and describes why information timing, probability quality and financial capacity matter.

## 2.1 Corporate Credit Risk

Corporate credit risk is the risk that a company will not meet its financial obligations as agreed. Several related outcomes must be distinguished. Delinquency means that a payment is overdue. Default means that a borrower meets a defined failure-to-pay or other default condition. Financial distress describes difficulty in meeting obligations. Bankruptcy is a formal legal process. These outcomes can be related without being identical.

Three terms are commonly used to describe credit loss. Probability of default, or PD, measures the likelihood of default within a specified period. Loss given default, or LGD, measures the share of exposure lost if default occurs. Exposure at default, or EAD, is the amount exposed when default occurs. A simplified expected-loss amount is:

$$ EL = PD \times LGD \times EAD. $$

The Basel framework uses these components in its treatment of expected loss. This thesis uses the relationship to explain the concepts, without implementing a regulatory capital framework. Definitions and horizons must be consistent. [Basel Committee on Banking Supervision, CRE35](https://www.bis.org/basel_framework/chapter/CRE/35.htm).

LGD depends on recoveries, collection costs and their timing. It is conditional on default. The expected-loss relationship therefore requires separate evidence about event probability, recoveries and exposure.

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

Two qualities matter. Discrimination describes how well a model ranks event observations above non-event observations. Calibration describes the relationship between estimated probabilities and observed event rates. A model may rank companies reasonably well while systematically overstating their probability.

This distinction matters when a probability enters a limit formula. A ranking can support a review queue, but an incorrect probability scale can produce an unsuitable monetary adjustment. Chapter 4 therefore evaluates both ranking and probability error.

## 2.4 Financial Ratio Analysis

Financial ratios help compare companies with different sizes. Their meaning still depends on the business model, accounting policies and reporting period. The same current ratio can describe different positions when one company holds mainly cash and another holds mainly slow-moving inventory.

The twelve predictors cover liquidity, leverage, profitability, cash generation, growth and size. Together, they describe both the current financial position and changes in that position. Chapter 3 defines their construction; Appendix A records source fields and timing rules.

Profitability is not the same as cash generation. A company can report profit while cash remains tied up in receivables. Reported cash also does not prove that all cash is available for repayment. Restrictions, business needs and legal arrangements may reduce the usable amount.

Debt requires careful definition. Total debt is a stock at a reporting date. Debt service is a flow of payments due during a period. Interest coverage measures interest capacity, while full debt-service coverage must also consider principal. A schedule of payments due within 60 days cannot be inferred from total debt alone.

The EBA's guidelines treat borrower financial condition and continuing credit monitoring as parts of the lending process. They provide institutional context. The proposed coefficients and limit formula are research choices, not EBA requirements. [EBA (2020)](https://eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring).

A zero or negative denominator can make a ratio undefined or misleading. The implementation treats unsuitable denominators as missing. It also matches annual profitability to the assets at the beginning and end of that annual period. These controls avoid assigning a convenient zero to every missing measure.

## 2.5 Statistical and Machine Learning Models

### 2.5.1 Logistic regression

Logistic regression links predictors to the probability of a binary outcome. For company i at date t:

$$ q_{i,t} = \frac{1}{1+\exp(-z_{i,t})}, \qquad z_{i,t} = \beta_0+\sum_{j=1}^{p}\beta_j x_{i,t,j}. $$

The coefficients describe relationships with event log-odds. A positive coefficient raises the fitted probability when the other predictors are held fixed. The basic model is linear in log-odds, so it cannot represent every nonlinear relationship without transformations or interactions.

The study uses logistic regression as an interpretable benchmark. Its estimated coefficients are associations in this sample, not causal effects of changing a company's finances.

### 2.5.2 Regularized logistic regression

Regularization adds a penalty that discourages large coefficients. L2 regularization uses a squared-coefficient penalty:

$$ \mathcal{J}(\beta) = -\sum_{n=1}^{N}\left[y_n\log(q_n)+(1-y_n)\log(1-q_n)\right]+\lambda\sum_{j=1}^{p}\beta_j^2. $$

This describes the general penalty idea; the software's scaling of the objective follows its implementation. In scikit-learn, C controls inverse regularization strength. Smaller C means stronger regularization. The study tunes C and compares the result with the unregularized model. [Scikit-learn 1.6, logistic regression](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression).

Regularization can help when predictors contain overlapping information. It does not guarantee improvement, especially with a small predictor set and rare events. Its value is assessed on later observations.

### 2.5.3 Random forest

A random forest combines decision trees fitted to bootstrap samples. Random subsets of predictors are considered at splits, and tree predictions are averaged. It can represent thresholds and interactions that a simple logistic specification may miss. [Breiman (2001)](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).

For example, liquidity may be more informative among companies with negative profitability than among profitable companies. A tree can represent this conditional relationship without a manually specified interaction.

The flexibility can also fit patterns that do not persist. Tree depth and leaf size control complexity, while later-period evaluation checks whether the ranking and probability scale remain useful.

### 2.5.4 Gradient boosting

Gradient boosting adds models in stages to reduce a chosen loss. Small decision trees can represent nonlinear relationships and interactions. Friedman (2001) provides the general framework. XGBoost provides an efficient regularized tree-boosting implementation. [Friedman (2001)](https://doi.org/10.1214/aos/1013203451), [Chen and Guestrin (2016)](https://arxiv.org/abs/1603.02754).

The study uses XGBoost with a limited grid for tree depth and learning rate. Including it does not assume that it will outperform the other models. All models use the same sample, predictors and date boundaries.

### 2.5.5 Evaluation and interpretation

Rare-event classification needs more than accuracy. If only one observation in a thousand has the event, a model that always predicts no event is highly accurate but detects nothing.

Precision measures the share of predicted event observations that are actual events. Recall measures the share of actual event observations detected. Precision-recall analysis is useful for evaluating imbalanced datasets. [Saito and Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).

The Brier score measures squared probability error. It reflects more than calibration alone. The study reports it alongside ranking metrics and reliability summaries.

Interpretation also has limits. A logistic coefficient describes a fitted association. Permutation importance describes how prediction changes when a variable's information is disrupted. Neither demonstrates that changing the variable would change real default risk.

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
