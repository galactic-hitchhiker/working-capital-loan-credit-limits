# 5 Credit Limit Methodology

The proposed policy combines financial capacity, a risk adjustment and an exposure cap, then applies monthly update rules. A hypothetical example illustrates the calculation. Chapter 7 applies it to historical SEC information under assumed facility terms.

## 5.1 Design Principles

The credit limit represents the maximum total outstanding amount on the facility, including unpaid balances from earlier statement periods. The policy follows five principles: the limit should reflect financial capacity, decrease when estimated risk increases, respect exposure caps, avoid unsupported increases and allow timely reductions.

Risk estimation and limit determination remain separate. The prediction model estimates the probability of the event defined in Chapter 3. The policy then translates this estimate into an amount. A low estimated probability does not, by itself, justify a large limit.

Inputs must be available at the review date and use the same currency. The coefficients are research assumptions evaluated through sensitivity analysis.

## 5.2 Borrower Capacity Component

Borrower capacity is a monetary proxy based on revenue, operating cash flow, available cash and external debt payments. For company $i$ at review date $t$, define:

- $R_{i,t}$: revenue for a consistent annual reporting period;
- $F_{i,t}$: operating cash flow for the same period;
- $B_{i,t}$: eligible cash available to support repayment;
- $D_{i,t}^{60}$: additional external debt payments due within the next 60 days, excluding payments already reflected in the cash-flow estimate.

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

Annual revenue and operating cash flow are divided by six because the policy's 60-day horizon is approximately two months, or one-sixth of a year. This assumes an even flow through the year and does not account for seasonality. Cash is an existing balance, so it is not divided by six. Negative operating cash flow contributes no positive flow capacity. Cash may still support a positive amount, so this rule does not fully model future cash consumption.

The starting values are $a=0.20$, $b=0.50$ and $c=0.10$. These fractions are illustrative policy choices, not estimated coefficients or established lending standards.

Eligible cash excludes restricted or unavailable amounts; reported SEC cash does not establish eligibility. Debt payments already included in operating cash flow must not be deducted again. The example deducts additional principal on another borrowing.

The extraction uses the last reported annual flows. Revenue and cash flow must cover the same period; cumulative year-to-date values cannot be added as separate quarters.

## 5.3 Risk Adjustment Component

Let $q_{i,t}$ be the selected model's 60-day disclosure probability. The proposed risk multiplier is:

$$
g(q_{i,t})=\exp(-kq_{i,t}),\qquad k\geq0.
$$

Risk-adjusted capacity is therefore:

$$
C_{i,t}^{risk}=C_{i,t}\exp(-kq_{i,t}).
$$

The multiplier lies between zero and one. The parameter $k$ controls how strongly estimated risk reduces capacity: a larger value produces a greater reduction at the same probability, while $k=0$ leaves capacity unchanged. The starting value $k=10$ is an illustrative policy assumption. For example, at a predicted probability of 5% ($q=0.05$), the multiplier is $e^{-10\times0.05}\approx0.607$, retaining about 61% of capacity. Values of 5 and 20 are examined in the sensitivity scenarios; the study does not establish that 10 is optimal.

This disclosure probability is not a facility-default probability. A change in the event definition or horizon requires reassessing the mapping and its sensitivity parameter.

The exponential function is a proposed policy rule. It does not estimate an optimal limit or prove that the resulting exposure is safe.

## 5.4 Exposure Constraints and Existing Indebtedness

Let $K_{i,t}$ be the maximum permitted exposure under the research policy. The preliminary limit is:

$$
L_{i,t}^{*}=\min\left(K_{i,t},C_{i,t}^{risk}\right).
$$

The example cap is USD 150,000. The historical scenario uses 1% of reported assets, with 0.5% and 2% alternatives. These are research assumptions. No positive minimum is imposed, as it could exceed capacity or the cap.

Total debt and near-term debt payments have different roles. Liabilities to assets and its 12-month change are fitted leverage predictors. Additional payments due within 60 days reduce capacity through $D_{i,t}^{60}$. The entire debt or liability balance is not subtracted from the proposed limit.

Let $E_{i,t}$ be the current outstanding exposure on the studied facility and $L_{i,t}$ the assigned limit after the monthly rules. Available credit is:

$$
A_{i,t}=\max(0,L_{i,t}-E_{i,t}).
$$

If the limit falls below the outstanding balance, the excess is $\max(0,E_{i,t}-L_{i,t})$. A limit reduction prevents additional credit under the policy; it does not remove an existing balance or demonstrate repayment.

## 5.5 Monthly Update Rules and Safeguards

The policy is reviewed monthly using the information available at each decision date. Financial statements remain unchanged between releases, although debt payments, exposure or other verified inputs may change.

For an existing positive limit, three parameters control increases: a minimum-change threshold $\delta$, a smoothing factor $\alpha$ and a maximum monthly increase $u$. The starting values are 2%, 50% and 10%, respectively.

If the preliminary limit is below the previous assigned limit, it is applied immediately. If no relevant new information is recorded, the previous limit is retained when the calculation would otherwise increase it. An increase of no more than $\delta L_{i,t-1}$ is also held back.

For a larger supported increase, the assigned limit is:

$$
L_{i,t}=\min\left\{
L_{i,t}^{*},\;
L_{i,t-1}+\alpha(L_{i,t}^{*}-L_{i,t-1}),\;
(1+u)L_{i,t-1}
\right\}.
$$

For an initial assessment, no previous limit exists, so the preliminary limit is assigned subject to eligibility checks. An account with an existing zero limit requires a documented reassessment before reopening. Repeated reviews of unchanged information do not automatically move the limit toward a previously calculated higher amount.

Increase controls never delay reductions or allow a limit above the current exposure cap. A predefined, verified ineligibility event activates a hard stop and sets the limit to zero; outstanding exposure remains recorded separately.

Missing required inputs, unresolved accounting conflicts or stale information require review. The freshness limits are 180 days from the balance-sheet period end and 540 days from the annual-flow period end. Missing policy inputs are not imputed or replaced with zero.

## 5.6 Worked Example

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

The risk multiplier is $\exp(-10\times0.02)=0.8187$. The preliminary limit is therefore USD 81,873.08. The exposure cap does not bind.

With new information supporting an increase, Section 5.5 compares USD 81,873.08, the smoothed amount of USD 75,936.54 and the monthly ceiling of USD 77,000. The smallest amount becomes the assigned limit. With USD 60,000 outstanding, available credit is USD 15,936.54. Calculations retain full precision; displayed amounts are rounded to cents.

These values are generated by the Python implementation. They illustrate the calculation and do not describe an actual company or a fitted probability.

## 5.7 Recorded Inputs and Scenario Assumptions

Each decision should preserve inputs, source dates, currency, event definition, horizon, model version and policy settings. Outputs record capacity, the risk multiplier, preliminary and assigned limits, the binding constraint and the reason for change. Outstanding exposure and available credit remain separate. Appendix B maps the supporting code and saved results.

The historical base scenario assumes all reported cash is eligible, no additional external debt payment is deducted and facility exposure is zero. These are scenario values, not verified borrower facts. Rows missing required accounting inputs are excluded. A reporting gap starts a new hypothetical assessment; monthly change statistics do not bridge gaps. A known qualifying disclosure activates a hard stop during the episode quiet gap.

Base settings were fixed before model fitting. Sensitivity cases examine rule behavior without optimizing parameters on test outcomes. Appendix D provides further hypothetical stress examples. The main formula does not require LGD, and the available data cannot establish facility-level expected loss or the economic value of the assigned limits.
