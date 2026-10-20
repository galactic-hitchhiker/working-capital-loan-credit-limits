# 2 Theoretical Background and Literature Review

This chapter separates credit-risk prediction from monetary limit determination and reviews the concepts supporting both.

## 2.1 Corporate Credit Risk

Delinquency is an overdue payment. Default is a defined failure-to-pay or other default condition. Financial distress is difficulty meeting obligations, while bankruptcy is a formal legal process. These outcomes overlap but are not equivalent.

The Basel Framework treats probability of default (PD), loss given default (LGD) and exposure at default (EAD) as distinct [credit-risk components](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/32/inforce/2023-01-01/published/2020-03-27) and uses them in [expected-loss calculations](https://www.bis.org/committees/bcbs/basel-framework/standard/cre/35/inforce/2023-01-01/published/2020-03-27) (Basel Committee on Banking Supervision, 2020).

A simplified expected-loss amount is:

$$ EL = PD \times LGD \times EAD. \tag{1} $$

Combining them requires consistent definitions, horizons and evidence on events, exposure and recoveries. This thesis instead predicts an SEC disclosure and lacks facility EAD and recovery data, so the estimated probability cannot be treated as PD in this formula.

PD asks how likely the defined event is, EAD how much will be owed when it occurs, and LGD what proportion will remain unrecovered. EAD can differ from the current balance because a revolving borrower may draw or repay before default. LGD additionally depends on collateral, seniority, collection costs and recovery timing. These distinct inputs explain why a distress score alone is insufficient for expected-loss or limit setting.

## 2.2 Short-Term Corporate Credit Facilities

The studied facility has a 30-day statement period and up to 30 further days for payment, creating up to about 60 days of scheduled exposure. If $$L$$ is the total limit and $$E$$ outstanding exposure, available credit is:

$$ A = \max(0,L-E). \tag{2} $$

Reducing $$L$$ restricts further use but leaves existing debt in place. The 60-day prediction horizon reflects the payment schedule. It does not imply that every transaction lasts 60 days or that a disclosure establishes facility default.

Transactions late in a statement period have less scheduled time outstanding than transactions made early. Missed payment can also extend exposure beyond the nominal horizon. A functioning limit process must therefore retain both the assigned commitment and current utilization rather than treating the unused amount as total lender exposure.

## 2.3 Corporate Credit Scoring

Credit scoring combines borrower information into a score, category or event probability. A score and a calibrated probability are different objects. Altman (1968) uses financial ratios and discriminant analysis, Ohlson (1980) logistic bankruptcy probabilities, and Shumway (2001) a hazard approach with changing company information. [Altman (1968)](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x), [Ohlson (1980)](https://www.jstor.org/stable/2490395), [Shumway (2001)](https://www.jstor.org/stable/10.1086/209665).

These works motivate the predictors, logistic benchmark and repeated assessment, but their coefficients cannot transfer across targets, populations and horizons. The present model is a monthly classifier, not a daily survival model. Evaluation covers both discrimination, which asks whether events rank higher, and calibration, which asks whether probabilities match observed frequencies. Both matter because the probability enters the monetary policy.

Discrimination and calibration serve different decisions. A well-ranked list can concentrate manual reviews near the top even when its numerical probabilities are biased. A monetary rule, however, changes continuously with the probability scale, so systematic overstatement or understatement can alter every limit. Temporal validation is also necessary: repeated observations, changing reporting practices and economic cycles make a random row split an unrealistic approximation of future monitoring.

## 2.4 Financial Ratio Analysis

Ratios make companies of different sizes more comparable. Liquidity describes near-term resources. Leverage reflects obligations and the equity buffer. Profitability and operating cash flow capture distinct aspects of performance, while changes may reveal deterioration or expansion. Size supplies context. Interpretation remains business-specific: current assets may not convert quickly, cash may be restricted, and accounting profit need not generate cash.

The available ratios measure general financial condition, not debt service due within 60 days. Chapter 3 defines the twelve point-in-time predictors.

Liquidity ratios may overstate accessible resources when receivables are doubtful, inventory is slow moving or cash is restricted. High leverage can indicate vulnerability but has different meanings across industries. Profitability is accrual-based, while operating cash flow reflects cash generation and working-capital movements. Using levels together with annual changes allows the model to distinguish condition from direction, although neither establishes causation.

## 2.5 Statistical and Machine Learning Models

The four candidates trade simplicity for flexibility.

### 2.5.1 Logistic regression

Logistic regression maps a weighted linear combination of predictors to a probability. It is fast and inspectable but may miss thresholds and interactions. Its coefficients are associations, not causal effects.

Its linear log-odds form provides a useful benchmark and exposes coefficient instability. Scaling makes coefficient magnitudes more comparable across differently measured ratios, while missing-value indicators allow missing reporting to carry information separately from median replacement.

### 2.5.2 Regularized logistic regression

L2 regularization discourages large coefficients, which can stabilize correlated predictors but cannot add nonlinearities. Its strength is selected on earlier data. [Scikit-learn 1.6, logistic regression](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression).

Excessive regularization can suppress useful signal, so penalty strength remains a tuning choice rather than an assumed improvement.

### 2.5.3 Random forest

A random forest combines trees fitted to different observations and predictors. It learns nonlinearities and interactions without prespecification, at the cost of transparency and potentially poor probability calibration. [Breiman (2001)](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).

Averaging many trees reduces the instability of a single tree. Depth and minimum leaf size control how narrowly the forest partitions the data, which is especially important when positive outcomes are rare.

### 2.5.4 Gradient boosting

Gradient boosting adds trees sequentially to correct current errors. XGBoost can learn detailed structure but may overfit rare events and depends on depth and learning rate. [Friedman (2001)](https://doi.org/10.1214/aos/1013203451), [Chen and Guestrin (2016)](https://arxiv.org/abs/1603.02754).

Shallow trees and a smaller learning rate restrict how quickly complexity accumulates. The empirical comparison holds predictors and chronological stages fixed so differences reflect model behavior rather than different information sets.

### 2.5.5 Evaluation and interpretation

Accuracy is misleading for a rare outcome because predicting no events may appear successful. Precision measures the event share among alerts, recall the share of events detected, and average precision summarizes their trade-off. [Saito and Rehmsmeier (2015)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432). The Brier score measures probability error, while calibration compares probabilities with observed rates. [Brier (1950)](https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2). Coefficients and importance measures explain fitted patterns rather than causation.

ROC-AUC describes ranking across all thresholds but can look strong despite poor performance in the small high-risk region relevant to rare events. Average precision is therefore compared with event prevalence, while threshold metrics show one frozen operating point. No single metric establishes operational value.

## 2.6 Credit Limit Determination

A probability is not a monetary amount. The framework connects probability $$q$$ to capacity $$C$$, a hard exposure cap $$K$$ and a decreasing risk multiplier $$g$$:

$$ L_{i,t}^{*}=\min\left(K_{i,t}, C_{i,t}g(q_{i,t})\right). \tag{3} $$

The cap can make probability changes immaterial to the preliminary limit. The capacity calculation must also avoid double-counting obligations, such as deducting interest already reflected in operating cash flow. Policy coefficients are assumptions, not parameters learned from observed lending decisions.

Capacity and risk play complementary roles: capacity limits how much the borrower could plausibly support, while the multiplier reduces that amount as estimated risk rises. A hard cap applies an independent exposure constraint. This structure is deliberately more transparent than training a model to reproduce historical limits, which are unavailable and could embed undocumented judgment.

## 2.7 Dynamic Limit Management

Monthly review does not imply monthly statements: unchanged values may be carried forward. The policy allows prompt reductions but requires new relevant information for increases, with smoothing and change thresholds to limit operational noise. Stability alone is insufficient if a limit does not respond to deterioration.

Asymmetric treatment reflects the different costs of delay. Smoothing a supported increase can reduce volatility, whereas smoothing a deterioration would leave the lender above its current calculation. A hard stop addresses known distress separately from gradual changes in estimated probability.

## 2.8 Research Gap and Position of the Study

Prior research supplies corporate-failure models but does not itself convert a dated risk estimate into a stable monetary limit. This study adds explicit capacity and exposure constraints and evaluates prediction separately from policy behavior. Predictive evidence therefore does not establish improved lending outcomes.

The gap is both empirical and operational. Public-data studies rarely observe lender utilization, repayment schedules and recoveries, yet these variables are essential to validate an exposure decision. The present work therefore limits its claim to an implemented, testable bridge whose assumptions can later be replaced with lender-specific evidence.
