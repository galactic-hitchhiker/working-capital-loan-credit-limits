# 5 Credit Limit Methodology

This chapter explains how the risk estimate from Chapter 4 is used to calculate a monetary credit limit. The proposed policy combines borrower capacity, a risk adjustment and an exposure cap. It also defines how the limit changes at each monthly review. The worked example is hypothetical. Chapter 7 separately applies the rule to real SEC financial histories and probabilities from the completed model comparison, under explicit facility assumptions.

## 5.1 Design Principles

The credit limit represents the maximum total outstanding amount on the facility, including unpaid balances from earlier statement periods. The policy follows five principles: the limit should reflect financial capacity, decrease when estimated risk increases, respect exposure caps, avoid unsupported increases and allow timely reductions.

Risk estimation and limit determination remain separate. The prediction model estimates the probability of the event defined in Chapter 3. The policy then translates this estimate into an amount. A low estimated probability does not, by itself, justify a large limit.

All inputs must be available at the review date. Financial amounts must use the same currency, and missing policy inputs must not be silently replaced with zero. The coefficients below are research assumptions. Their practical value must be assessed through sensitivity analysis and historical simulation.

## 5.2 Borrower Capacity Component

Borrower capacity is a monetary proxy based on revenue, operating cash flow, available cash and external debt payments. For company $$ i $$ at review date $$ t $$, define:

- $$ R_{i,t} $$: revenue for a consistent annual reporting period;
- $$ F_{i,t} $$: operating cash flow for the same period;
- $$ B_{i,t} $$: eligible cash available to support repayment;
- $$ D_{i,t}^{60} $$: additional external debt payments due within the next 60 days, excluding payments already reflected in the cash-flow estimate.

Two preliminary amounts are calculated:

$$
C_{i,t}^{R}=a\frac{R_{i,t}}{6}
$$

$$
C_{i,t}^{F}=b\frac{\max(F_{i,t},0)}{6}+cB_{i,t}
$$

The capacity amount is:

$$
C_{i,t}=\max\left(0,\min(C_{i,t}^{R},C_{i,t}^{F})-D_{i,t}^{60}\right).
$$

The revenue component limits exposure relative to business activity. The cash-flow and cash component connects it to financial resources. Taking the smaller amount prevents high revenue alone from supporting a large limit when cash generation is weak.

Dividing annual flows by six gives a simple two-month approximation. It does not forecast exact cash receipts over 60 days or account for seasonality. Negative operating cash flow contributes no positive flow capacity. Cash may still support a positive amount, so this rule does not fully model future cash consumption.

The starting values are $$ a=0.20 $$, $$ b=0.50 $$ and $$ c=0.10 $$. These fractions are illustrative policy choices, not estimated coefficients or established lending standards.

Eligible cash must exclude restricted or otherwise unavailable amounts. Reported cash in the SEC dataset is only a starting measure; it does not establish that all cash can support this facility. The debt-payment adjustment must also avoid double counting. For example, interest already included in operating cash flow must not be deducted again. The worked example uses an additional principal payment on another borrowing.

The completed empirical extraction uses the last reported annual flows. Future research may use reconstructed trailing twelve-month values, but revenue and cash flow must cover the same period. Cumulative year-to-date amounts must not be added as if each represented a separate quarter.

File references: `mcf/policy/credit.py`, `mcf/data/sec.py`, `11_appendix_a_variable_dictionary.md`.

## 5.3 Risk Adjustment Component

Let $$ q_{i,t} $$ represent the probability of the defined event. The completed study uses the selected random forest's raw probability, called the identity mapping because no additional transformation is applied. This mapping is selected because it has lower selection-period Brier error than sigmoid calibration. The proposed risk multiplier is:

$$
g(q_{i,t})=\exp(-kq_{i,t}),\qquad k\geq0.
$$

Risk-adjusted capacity is therefore:

$$
C_{i,t}^{risk}=C_{i,t}\exp(-kq_{i,t}).
$$

The multiplier lies between zero and one. When $$ k>0 $$, higher estimated risk produces a lower amount, with capacity and other inputs held constant. The parameter $$ k $$ controls the strength of the reduction. The initial example uses $$ k=10 $$, with alternative values of 5 and 20 included in the supporting scenarios.

The meaning of $$ q_{i,t} $$ must remain explicit. A bankruptcy or distress probability is not automatically a payment-default probability. A longer-horizon estimate must also not be relabelled as a 60-day probability. If the event definition or horizon changes, the risk mapping requires a new assessment; the same value of $$ k $$ cannot be assumed to have the same meaning.

The exponential function is a proposed policy rule. It does not estimate an optimal limit or prove that the resulting exposure is safe.

File references: `mcf/policy/credit.py`, `mcf/policy/examples.py`, `policy_sensitivity.csv`.

## 5.4 Exposure Constraints and Existing Indebtedness

Let $$ K_{i,t} $$ be the maximum permitted exposure under the research policy. The preliminary limit is:

$$
L_{i,t}^{*}=\min\left(K_{i,t},C_{i,t}^{risk}\right).
$$

The cap is an explicit policy input. The worked example uses USD 150,000. For the historical scenario in Chapter 7, the cap is set to 1% of reported total assets, with 0.5% and 2% alternatives. This size-based cap is an assumption, not an inferred lender decision or regulatory requirement. No positive minimum limit is imposed, because a minimum could exceed the amount supported by capacity or the cap.

Total debt and near-term debt payments have different roles. Liabilities to assets and its 12-month change are fitted leverage predictors. Additional payments due within 60 days reduce capacity through $$ D_{i,t}^{60} $$. The entire debt or liability balance is not subtracted from the proposed limit.

Let $$ E_{i,t} $$ be the current outstanding exposure on the studied facility and $$ L_{i,t} $$ the assigned limit after the monthly rules. Available credit is:

$$
A_{i,t}=\max(0,L_{i,t}-E_{i,t}).
$$

If the limit falls below the outstanding balance, the excess is $$ \max(0,E_{i,t}-L_{i,t}) $$. A limit reduction prevents additional credit under the policy; it does not remove an existing balance or demonstrate repayment.

## 5.5 Final Limit Formula and Worked Example

Combining the components gives the preliminary limit:

$$
L_{i,t}^{*}=\min\left\{K_{i,t},\;
\max\left[0,\min\left(a\frac{R_{i,t}}{6},
b\frac{\max(F_{i,t},0)}{6}+cB_{i,t}\right)-D_{i,t}^{60}\right]
\exp(-kq_{i,t})\right\}.
$$

Consider a hypothetical borrower with the following inputs:

| Input | Illustrative value |
|---|---:|
| Annual revenue | USD 12,000,000 |
| Annual operating cash flow | USD 1,200,000 |
| Eligible cash | USD 500,000 |
| Additional external principal due within 60 days | USD 50,000 |
| Estimated event probability | 2% |
| Exposure cap | USD 150,000 |
| Previous assigned limit | USD 70,000 |
| Outstanding facility exposure | USD 60,000 |

Using the starting coefficients, the revenue amount is USD 400,000. The cash-flow and cash amount is USD 150,000. After deducting the additional principal payment, capacity equals USD 100,000.

The risk multiplier is $$ \exp(-10\times0.02)=0.8187 $$. The preliminary limit is therefore USD 81,873.08. The exposure cap does not bind.

Assuming new information supports an increase, the monthly rule in Section 5.6 assigns USD 75,936.54. With USD 60,000 outstanding, available credit is USD 15,936.54. Calculations retain full precision; displayed amounts are rounded to cents.

These values are generated by the Python implementation. They illustrate the calculation and do not describe an actual company or a fitted probability.

File references: `mcf/policy/examples.py`, `worked_examples.csv`.

## 5.6 Monthly Update Rule

The policy is reviewed monthly using the information available at each decision date. Financial statements remain unchanged between releases, although debt payments, exposure or other verified inputs may change.

For an existing positive limit, three parameters control increases: a minimum-change threshold $$ \delta $$, a smoothing factor $$ \alpha $$ and a maximum monthly increase $$ u $$. The starting values are 2%, 50% and 10%, respectively.

If the preliminary limit is below the previous assigned limit, it is applied immediately. If no relevant new information is recorded, the previous limit is retained when the calculation would otherwise increase it. An increase of no more than $$ \delta L_{i,t-1} $$ is also held back.

For a larger supported increase, the assigned limit is:

$$
L_{i,t}=\min\left\{
L_{i,t}^{*},\;
L_{i,t-1}+\alpha(L_{i,t}^{*}-L_{i,t-1}),\;
(1+u)L_{i,t-1}
\right\}.
$$

In the worked example, these three amounts are USD 81,873.08, USD 75,936.54 and USD 77,000. The smallest amount becomes the assigned limit.

For an initial assessment, no previous limit exists, so the preliminary limit is assigned subject to eligibility checks. An account with an existing zero limit requires a documented reassessment before reopening. Repeated reviews of unchanged information do not automatically move the limit toward a previously calculated higher amount.

File references: `mcf/policy/credit.py`, `mcf/policy/backtest.py`.

## 5.7 Stability Safeguards and Risk Overrides

The threshold, smoothing factor and monthly cap restrict increases only. They never delay a reduction or allow the assigned limit to exceed the current exposure cap. This makes the trade-off explicit: increases are gradual, while reductions follow the current calculation.

A verified event that makes the borrower ineligible can activate a hard stop, setting the assigned limit to zero. The qualifying events must be defined before the historical simulation. A zero limit records the withdrawal of further credit; outstanding exposure remains recorded separately.

For illustration, increasing the example probability from 2% to 8%, while holding other inputs constant, lowers the limit to USD 44,932.90. The reduction is immediate. If USD 60,000 remains outstanding, no further credit is available and excess exposure is USD 15,067.10. This is a probability stress scenario, not evidence that a trained model would produce that change.

Data checks must take place before applying the policy. Missing required inputs, unresolved accounting conflicts or information older than a predefined freshness limit require review. The empirical design allows at most 180 days since the balance-sheet period end and 540 days since the annual-flow period end. Required policy inputs are not estimated automatically from missing values.

Chapter 7 assesses limit changes, response to deterioration and sensitivity to the capacity fractions, risk sensitivity, cap and increase rules. The base settings and input assumptions were fixed before model fitting. The sensitivity cases are comparisons, not attempts to select parameters from test-period outcomes.

File references: `mcf/policy/credit.py`, `test_research.py`, `worked_examples.csv`, `mcf/policy/sensitivity.py`.

## 5.8 Governance and Explainability

Each decision should preserve its inputs, source dates, currency, event definition, prediction horizon, model version and policy settings. The output should show capacity, the risk multiplier, the preliminary limit, the assigned limit, the binding constraint and the reason for any change. Outstanding exposure and available credit must be shown separately.

The supporting implementation records calculation components and update reasons. The data extraction also retains filing references. The monthly prediction and policy-replay scripts connect these records to model outputs and decision dates. The empirical prediction target is a new qualifying bankruptcy or payment-failure disclosure episode. The historical policy explicitly identifies reported financial values and assumed facility inputs.

LGD is not required by the main limit formula. An optional expected-loss scenario can use the relationship discussed in Chapter 2, but only with a default probability for the relevant horizon and explicit assumptions about LGD and exposure at default. A distress probability must not be substituted for default probability. Current data does not establish facility utilization or recovery outcomes, so such scenarios cannot be presented as observed loss estimates.

The policy is intended to support a reproducible research comparison. Its usefulness will depend on both the quality of the risk estimates and the observed behavior of the resulting limits.

File references: `mcf/policy/credit.py`, `feature_provenance.jsonl`, `policy.sec_disclosure.json`, `mcf/models/predict.py`, `mcf/policy/backtest.py`, `mcf/policy/empirical.py`, `12_appendix_b_reproducibility.md`.

The historical base scenario assumes all reported cash is eligible, no additional external debt payment is deducted, and facility exposure is zero. These are explicit scenario values, not missing-data replacements or verified borrower facts. Rows without revenue, cash or other required accounting inputs are excluded. A reporting gap starts a new hypothetical assessment; monthly change statistics do not bridge the gap. A known qualifying disclosure activates a hard stop during the episode quiet gap.
