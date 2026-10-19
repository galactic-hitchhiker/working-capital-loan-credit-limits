# 5 Credit Limit Methodology

The proposed policy translates company financial data and the model's estimated 60-day disclosure probability into a hypothetical credit limit. It combines a financial capacity proxy, a risk reduction, an exposure cap and monthly update rules. Chapter 7 replays this policy on historical SEC data under stated assumptions about a lending facility.

The calculation has five main steps:

1. Estimate a capacity proxy from revenue, operating cash flow, cash and near-term external debt payments.
2. Reduce that amount when the model estimates higher disclosure risk.
3. Apply a maximum exposure cap.
4. Compare the result with the previous limit and control monthly changes.
5. Set the limit to zero when a qualifying disclosure is already known.

## 5.1 Design Principles

The credit limit represents the maximum total amount that may be outstanding on the facility, including unpaid balances from earlier periods. It is not the amount of new credit available. New available credit is the assigned limit minus the amount already outstanding.

The prediction model and the limit policy have different roles. The model estimates the probability of the disclosure event defined in Chapter 3. The policy converts that probability and the financial inputs into an amount. A low estimated probability alone does not justify a large limit because the company must also have a sufficient capacity proxy under the policy.

All inputs must be available on the review date and monetary values must use the same currency. The policy coefficients are research assumptions tested through sensitivity analysis. They are not fitted lending standards.

## 5.2 Capacity Proxy and Input Assumptions

The historical replay combines reported SEC values, model outputs and assumptions about a hypothetical lending facility. This distinction is important because SEC filings do not report whether cash is available to a lender, the company's exact debt payments over the next 60 days or the balance on the studied facility.

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

For company $$i$$ at review date $$t$$, define:

- $$R_{i,t}$$ as annual revenue;
- $$F_{i,t}$$ as annual operating cash flow for the same period;
- $$B_{i,t}$$ as cash considered eligible to support repayment;
- $$D_{i,t}^{60}$$ as additional external debt payments due within the next 60 days.

The policy first calculates a revenue-based amount:

$$
C_{i,t}^{R}=a\frac{R_{i,t}}{6}.
$$

It also calculates an amount based on operating cash flow and eligible cash:

$$
C_{i,t}^{F}=b\frac{\max(F_{i,t},0)}{6}+cB_{i,t}.
$$

The capacity proxy is:

$$
C_{i,t}=\max\left(0,\min(C_{i,t}^{R},C_{i,t}^{F})-D_{i,t}^{60}\right).
$$

The policy uses the smaller of the two amounts. This prevents high revenue from supporting a large limit when cash generation is weak. Additional external payments due during the 60-day horizon then reduce the result.

Annual revenue and operating cash flow are divided by six because 60 days are approximately one-sixth of a year. This simple conversion assumes that activity is evenly distributed through the year and therefore does not capture seasonality. Cash is an existing balance, so it is not divided by six. Negative operating cash flow adds nothing to the proxy, although eligible cash can still produce a positive amount.

The starting values are $$a=0.20$$, $$b=0.50$$ and $$c=0.10$$. They are illustrative policy choices. Revenue and operating cash flow use the same annual period, and cumulative year-to-date values are not treated as separate quarters.

Eligible cash is not directly observed in the SEC data. Restricted or otherwise unavailable cash should be excluded in a real assessment, but the base replay cannot identify it and therefore assumes that all reported cash is eligible. The replay also cannot observe the exact external debt payments due within 60 days, so the base scenario assumes $$D_{i,t}^{60}=0$$. Alternative assumptions are tested in Chapter 7.

## 5.3 Risk Adjustment

Let $$q_{i,t}$$ be the selected model's estimated probability of a qualifying disclosure within 60 days. The proposed risk multiplier is:

$$
g(q_{i,t})=\exp(-kq_{i,t}),\qquad k\geq0.
$$

The risk-adjusted capacity proxy is:

$$
C_{i,t}^{risk}=C_{i,t}\exp(-kq_{i,t}).
$$

The multiplier is greater than zero and at most one: $$0<e^{-kq}\leq1$$. A larger $$k$$ makes the reduction stronger for the same estimated probability, while $$k=0$$ applies no risk reduction. The starting value $$k=10$$ is an illustrative assumption. At an estimated probability of 5% ($$q=0.05$$), the multiplier is $$e^{-10\times0.05}\approx0.607$$, so about 61% of the capacity proxy remains. Values of 5 and 20 are examined in the sensitivity scenarios; the study does not establish that 10 is optimal.

The estimated probability concerns the SEC disclosure outcome defined in Chapter 3. It is not a probability of default on the hypothetical facility. The exponential reduction is a proposed policy rule, not an estimate of an optimal or safe exposure.

## 5.4 Exposure Cap and Existing Exposure

Let $$K_{i,t}$$ be the maximum exposure permitted by the research policy. The preliminary limit is:

$$
L_{i,t}^{*}=\min\left(K_{i,t},C_{i,t}^{risk}\right).
$$

The worked example uses a cap of USD 150,000. The historical base scenario assumes a cap equal to 1% of reported assets, with 0.5% and 2% tested as alternatives. These values are scenario assumptions. The policy has no positive minimum because a minimum could exceed both the capacity proxy and the cap.

Total liabilities and near-term debt payments have different roles. Liabilities to assets and its 12-month change are predictors in the risk model. Only additional external payments due within 60 days reduce the capacity proxy through $$D_{i,t}^{60}$$. The full liability balance is not deducted from the limit.

Let $$E_{i,t}$$ be the current outstanding balance on the hypothetical facility and $$L_{i,t}$$ the assigned limit after the monthly rules. New available credit is:

$$
A_{i,t}=\max(0,L_{i,t}-E_{i,t}).
$$

If the limit is below the outstanding balance, excess exposure is $$\max(0,E_{i,t}-L_{i,t})$$. Reducing the limit prevents further use under the policy. It does not remove an existing balance or show that the borrower can repay it.

## 5.5 Monthly Update Rules and Safeguards

The policy is reviewed monthly using information available on each decision date. Accounting values usually remain unchanged between SEC reports, so a new month does not necessarily provide new financial information.

For an existing positive limit, the policy uses a 2% deadband $$\delta$$, a 50% smoothing factor $$\alpha$$ and a 10% maximum monthly increase $$u$$. The rules are applied as follows:

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

For a supported increase, the assigned limit is:

$$
L_{i,t}=\min\left\{
L_{i,t}^{*},\;
L_{i,t-1}+\alpha(L_{i,t}^{*}-L_{i,t-1}),\;
(1+u)L_{i,t-1}
\right\}.
$$

For example, if the previous limit is USD 100,000 and the new preliminary limit is USD 101,500, the increase is only 1.5%. Because it is within the 2% deadband, the assigned limit remains USD 100,000. The deadband avoids small changes that may reflect rounding or minor input movements.

Increase controls never delay a reduction and never permit a limit above the current cap. Missing required inputs, unresolved accounting conflicts or stale information require review rather than replacement with zero. The freshness limits are 180 days from the balance-sheet period end and 540 days from the annual-flow period end.

A known qualifying disclosure produces an immediate hard stop. When the disclosure's quiet-gap period ends, the hard-stop indicator can end, but the previous zero limit still prevents automatic reopening. In the historical replay, the limit therefore remains zero within the same continuous company segment. A missing-month gap starts a new hypothetical segment and is treated as a new initial assessment. This reset is a replay convention, not evidence that a real lender would reopen the facility.

## 5.6 Worked Example

Combining the capacity proxy, risk reduction and exposure cap gives:

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
| Estimated disclosure probability | 2% |
| Exposure cap | USD 150,000 |
| Previous assigned limit | USD 70,000 |
| Outstanding facility exposure | USD 60,000 |

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

The exposure cap does not bind in this example. The smoothing rule produces the smallest permitted amount and therefore determines the assigned limit. The Python implementation generates these values using full precision; the table rounds displayed amounts. The example does not represent an actual company or a fitted model result.

## 5.7 Scenario Assumptions and Limitations

Each decision record preserves the input values and dates, currency, event definition, prediction horizon, model version and policy settings. It also records the capacity proxy, risk multiplier, preliminary limit, assigned limit, binding constraint and reason for the change. Outstanding exposure and new available credit remain separate. Appendix A maps the supporting code and saved results.

The base replay assumes that all reported cash is eligible, no additional external debt payment is due within 60 days, outstanding facility exposure is zero and the exposure cap equals 1% of assets. These are not observed borrower facts. Rows without the required accounting inputs are excluded, and a reporting gap starts a new hypothetical assessment.

The probability is a prediction of an SEC disclosure proxy, not a verified facility default. The data contain no actual credit limits, drawings, repayments, losses, prices or profits against which to test the policy. The parameters were fixed before model fitting, and the sensitivity cases show how the rules react to alternative assumptions rather than identify optimal settings. The replay therefore tests the behavior of the proposed rules; it does not demonstrate that the limits are safe, profitable or beneficial to a lender.
