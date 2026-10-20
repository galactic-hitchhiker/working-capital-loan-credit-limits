# 5 Credit Limit Methodology

The policy combines capacity, 60-day disclosure probability, an exposure cap and monthly rules to produce a hypothetical limit. A known qualifying disclosure sets it to zero.

## 5.1 Design Principles

The limit covers total facility exposure. Available new credit subtracts the outstanding balance. Low estimated risk cannot substitute for capacity. Inputs must be available on the review date and use one currency. Policy coefficients are sensitivity-tested assumptions, not fitted lending standards.

The design seeks four properties: monotonic risk response, a capacity ceiling, an independent exposure cap and stable monthly changes. Every intermediate amount is retained so a reviewer can identify whether capacity, risk, the cap or an update safeguard determined the final result.

## 5.2 Capacity Proxy and Input Assumptions

The replay combines SEC values, model output and facility assumptions because filings omit cash eligibility, exact 60-day debt payments and the studied facility balance.

Table 8 separates these categories explicitly. This prevents assumed zeros from being mistaken for reported borrower facts and makes sensitivity cases interpretable as policy scenarios rather than alternative historical observations.

| Input | Value used in the replay | Type |
|---|---|---|
| Annual revenue | Latest eligible SEC annual value | Observed accounting data |
| Annual operating cash flow | Latest eligible SEC annual value for the same period | Observed accounting data |
| Reported cash | Latest eligible SEC balance | Observed accounting data |
| Total assets | Latest eligible SEC balance | Observed accounting data |
| 60-day disclosure probability | Output from the selected prediction model | Model estimate |
| Known qualifying disclosure | Derived from SEC filings available by the review date | SEC-derived indicator |
| Eligible cash | 100% of reported cash in the base scenario | Scenario assumption |
| Additional external debt payments due within 60 days | Zero in the base scenario | Scenario assumption |
| Maximum exposure | 1% of reported assets in the base scenario | Scenario assumption |
| Outstanding facility exposure | Zero in the base scenario | Scenario assumption |

*Table 8. Observed and assumed inputs to the policy replay.*

For company $$i$$ at review date $$t$$, define:

- $$R_{i,t}$$ as annual revenue
- $$F_{i,t}$$ as annual operating cash flow for the same period
- $$B_{i,t}$$ as cash considered eligible to support repayment
- $$D_{i,t}^{60}$$ as additional external debt payments due within the next 60 days.

The policy first calculates a revenue-based amount:

$$
C_{i,t}^{R}=a\frac{R_{i,t}}{6}.
\tag{8}
$$

It also calculates an amount based on operating cash flow and eligible cash:

$$
C_{i,t}^{F}=b\frac{\max(F_{i,t},0)}{6}+cB_{i,t}.
\tag{9}
$$

The capacity proxy is:

$$
C_{i,t}=\max\left(0,\min(C_{i,t}^{R},C_{i,t}^{F})-D_{i,t}^{60}\right).
\tag{10}
$$

Taking the smaller amount prevents revenue from supporting a large limit when cash generation is weak. Near-term external payments then reduce it. Annual flows are divided by six as a 60-day approximation that ignores seasonality. Cash is a balance, and negative cash flow contributes zero. The illustrative values are $$a=0.20$$, $$b=0.50$$ and $$c=0.10$$. Annual flows use one period. The base case treats all cash as eligible and sets unobserved $$D_{i,t}^{60}=0$$.

The revenue branch represents activity scale, while the cash-flow-and-cash branch approximates resources that could support repayment. Taking their minimum prevents either branch from overriding weakness in the other. The formula is intentionally conservative in structure but its coefficients are not empirically validated lending standards.

## 5.3 Risk Adjustment

Let $$q_{i,t}$$ be the selected model's estimated probability of a qualifying disclosure within 60 days. The proposed risk multiplier is:

$$
g(q_{i,t})=\exp(-kq_{i,t}),\qquad k\geq0.
\tag{11}
$$

The risk-adjusted capacity proxy is:

$$
C_{i,t}^{risk}=C_{i,t}\exp(-kq_{i,t}).
\tag{12}
$$

The multiplier lies in $$(0,1]$$. Larger $$k$$ strengthens the reduction and $$k=0$$ removes it. With illustrative $$k=10$$, a 5% probability retains about 61% of capacity. Sensitivity uses 5 and 20. This rule is neither facility PD nor an estimated optimal exposure.

The exponential form is continuous and strictly decreasing, so a higher estimated probability can never raise the limit when other inputs are fixed. It also avoids a single approval threshold, although the choice of $$k$$ determines how strongly small rare-event probabilities affect money.

## 5.4 Exposure Cap and Existing Exposure

Let $$K_{i,t}$$ be the maximum exposure permitted by the research policy. The preliminary limit is:

$$
L_{i,t}^{*}=\min\left(K_{i,t},C_{i,t}^{risk}\right).
\tag{13}
$$

The worked example caps exposure at USD 150,000. The replay uses 1% of assets and tests 0.5% and 2%. No positive minimum can override capacity or the cap. Total liabilities affect prediction, but only additional payments due within 60 days reduce capacity.

Deducting the entire liability balance would mix stock obligations with payments due over the short horizon. Conversely, omitting actual near-term debt service in deployment would overstate available capacity. This is why the unobserved payment assumption receives a separate sensitivity case.

Let $$E_{i,t}$$ be the current outstanding balance on the hypothetical facility and $$L_{i,t}$$ the assigned limit after the monthly rules. New available credit is:

$$
A_{i,t}=\max(0,L_{i,t}-E_{i,t}).
\tag{14}
$$

If exposure exceeds the reduced limit, excess is $$\max(0,E_{i,t}-L_{i,t})$$. The reduction prevents new use but neither removes nor proves repayment of the balance.

## 5.5 Monthly Update Rules and Safeguards

Monthly reviews use available information, which often remains unchanged between filings. Existing positive limits use a 2% deadband $$\delta$$, 50% smoothing $$\alpha$$ and 10% increase ceiling $$u$$:

| Situation | Policy action |
|---|---|
| A qualifying disclosure is already known | Set the limit to zero immediately |
| No previous limit exists | Assign the preliminary limit as an initial assessment |
| The preliminary limit is lower than the previous limit | Apply the reduction immediately |
| The preliminary and previous limits are equal | Keep the previous limit |
| The preliminary limit is higher but no relevant input changed | Keep the previous limit |
| The supported increase is no more than 2% | Keep the previous limit |
| A larger increase is supported by new information | Apply smoothing and the monthly increase ceiling |
| The previous limit is zero | Keep it at zero until a new initial assessment is documented |

*Table 9. Monthly credit-limit update rules.*

For a supported increase, the assigned limit is:

$$
L_{i,t}=\min\left\{
L_{i,t}^{*},\;
L_{i,t-1}+\alpha(L_{i,t}^{*}-L_{i,t-1}),\;
(1+u)L_{i,t-1}
\right\}.
\tag{15}
$$

The deadband ignores minor movements. Increase controls never delay reductions or breach the current cap. Missing, conflicting or stale inputs require review rather than zero replacement. Freshness limits are 180 days for balance sheets and 540 for annual flows.

These asymmetric controls prevent a stale favorable assessment from supporting growth while ensuring that a lower current preliminary limit takes effect immediately. They also distinguish a data-quality exception from an economically calculated zero.

A known disclosure immediately stops the limit. After its quiet period, the previous zero still prevents automatic reopening within a continuous segment. A missing-month gap starts a new hypothetical assessment. This is only a replay convention.

In an operating policy, reopening would require documented review rather than a gap in the research data. The replay convention is retained only so disconnected historical segments do not inherit state across months with no eligible observation.

## 5.6 Worked Example

Combining the capacity proxy, risk reduction and exposure cap gives:

$$
L_{i,t}^{*}=\min\left\{K_{i,t},\;
\max\left[0,\min\left(a\frac{R_{i,t}}{6},
b\frac{\max(F_{i,t},0)}{6}+cB_{i,t}\right)-D_{i,t}^{60}\right]
\exp(-kq_{i,t})\right\}.
\tag{16}
$$

Consider a hypothetical borrower with the following inputs:

| Input | Illustrative value |
|---|---:|
| Annual revenue | USD 12,000,000 |
| Annual operating cash flow | USD 1,200,000 |
| Eligible cash | USD 500,000 |
| Additional external principal due within 60 days | USD 50,000 |
| Estimated disclosure probability | 2% |
| Exposure cap | USD 150,000 |
| Previous assigned limit | USD 70,000 |
| Outstanding facility exposure | USD 60,000 |

*Table 10. Inputs to the worked credit-limit example.*

The calculation is:

| Step | Calculation | Result |
|---|---|---:|
| 1. Revenue-based amount | $$0.20\times\text{USD }12{,}000{,}000/6$$ | USD 400,000.00 |
| 2. Cash-flow-and-cash amount | $$0.50\times\text{USD }1{,}200{,}000/6+0.10\times\text{USD }500{,}000$$ | USD 150,000.00 |
| 3. Capacity proxy | $$\min(400{,}000,150{,}000)-50{,}000$$ | USD 100,000.00 |
| 4. Risk multiplier | $$e^{-10\times0.02}$$ | 0.8187 |
| 5. Risk-adjusted amount | $$100{,}000\times0.8187$$ | USD 81,873.08 |
| 6. Preliminary limit | $$\min(150{,}000,81{,}873.08)$$ | USD 81,873.08 |
| 7. Smoothed increase | $$70{,}000+0.50\times(81{,}873.08-70{,}000)$$ | USD 75,936.54 |
| 8. Monthly increase ceiling | $$1.10\times70{,}000$$ | USD 77,000.00 |
| 9. Assigned limit | Smallest of steps 6–8 | USD 75,936.54 |
| 10. New available credit | $$75{,}936.54-60{,}000$$ | USD 15,936.54 |

*Table 11. Worked credit-limit calculation.*

Here the cap does not bind and smoothing determines the assigned limit. Implementation uses full precision, while displayed amounts are rounded. The borrower is hypothetical.

## 5.7 Scenario Assumptions and Limitations

Each record preserves input dates, currency, event and model versions, settings, intermediate amounts, constraints and change reasons. The base case assumes full cash eligibility, no additional 60-day debt payment, zero facility exposure and a 1%-of-assets cap. Missing required inputs are excluded. With no actual limits, drawings, repayments, losses, prices or profits, sensitivity tests behavior rather than optimality, safety or lender benefit.
