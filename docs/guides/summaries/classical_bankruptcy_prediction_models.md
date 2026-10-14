# Classical Approaches to Corporate Bankruptcy Prediction

Altman (1968), Ohlson (1980) and Shumway (2001) mark three important stages in the development of corporate bankruptcy prediction. Altman shows how several financial ratios can be combined into one classification score. Ohlson replaces discriminant classification with a probabilistic logistic model. Shumway then reframes bankruptcy as an event that can occur over time and argues that the model should use every period during which a company remains at risk. Together, the papers illustrate a progression from static classification, to probability estimation, to dynamic event modeling.

## Altman (1968): combining ratios into a bankruptcy score

Altman studies whether financial ratios are more informative when evaluated jointly rather than one at a time. He applies multiple discriminant analysis to a matched sample of bankrupt and non-bankrupt manufacturing companies. The method constructs a weighted combination of variables that separates the two groups as clearly as possible.

The resulting Z-score uses five dimensions of financial condition:

- working capital relative to total assets, representing short-term liquidity;
- retained earnings relative to total assets, representing accumulated profitability and company maturity;
- earnings before interest and taxes relative to total assets, representing operating profitability;
- market value of equity relative to the book value of liabilities, representing the decline in asset value that could be absorbed before liabilities exceed assets; and
- sales relative to total assets, representing asset turnover.

The main contribution is not simply the particular formula. More broadly, the paper demonstrates that financial weakness is multidimensional. A company may look acceptable on one ratio while the combined pattern of weak liquidity, profitability, solvency and operating efficiency indicates distress. This insight remains central to modern credit scoring and machine-learning models, which also combine several borrower characteristics.

The Z-score is a classification measure rather than a direct probability of bankruptcy. Its original coefficients and thresholds were estimated from a small, historically specific sample of publicly traded US manufacturing companies. The matched-sample design, discriminant-analysis assumptions and industry focus limit the extent to which the published formula can be transferred unchanged to other periods, countries, industries or event definitions. The paper therefore supports using multiple financial dimensions, but it does not justify applying the original Z-score mechanically to the population in this thesis.

## Ohlson (1980): estimating bankruptcy probability with logistic regression

Ohlson uses a conditional logit model to relate company characteristics to the probability of bankruptcy. This addresses several limitations of discriminant analysis. Logistic regression does not require the predictors in the two groups to follow multivariate normal distributions with equal covariance matrices, and it can naturally include indicator variables. Its fitted value is bounded between zero and one and can therefore be interpreted as an estimated event probability under the model and sampling design.

Ohlson examines nine predictors representing company size, leverage, liquidity, profitability, cash generation and recent earnings performance. They include total liabilities relative to total assets, working capital relative to total assets, net income relative to total assets, funds from operations relative to liabilities, indicators of negative net worth and repeated losses, and the change in net income. The results emphasize four broad influences on bankruptcy risk: company size, financial structure, operating performance and liquidity.

The paper also draws attention to information timing. A financial statement dated before bankruptcy may not have been published or available to a decision-maker before the event. A credible forecasting exercise must therefore distinguish the accounting period from the date on which the information became observable. This is particularly relevant to the present thesis, which uses filing dates to construct point-in-time monthly observations.

Logistic regression improves interpretability because each coefficient describes a relationship with bankruptcy log-odds while the fitted model produces a probability-like output. Nevertheless, the estimated probability is conditional on the chosen population, variables, event definition, horizon and sampling process. A coefficient or cutoff estimated in Ohlson's historical sample is not automatically valid for a different borrower population. The paper is therefore most useful here as the foundation for an interpretable probability benchmark, not as a source of coefficients to reuse.

## Shumway (2001): treating bankruptcy as a time-dependent event

Shumway argues that many earlier bankruptcy models are statistically misspecified because they reduce a multi-year company history to one observation. A common static design observes a bankrupt company shortly before failure but observes a surviving company at an arbitrarily selected date. This discards earlier periods during which the future bankrupt company was still operating and can create selection bias.

The proposed solution is a discrete-time hazard model. Each company contributes one observation for every period in which it is observed and remains at risk. The dependent variable is zero in surviving periods and one in the period of bankruptcy. Companies that leave the sample for another reason can be treated as censored rather than incorrectly classified as permanent survivors. Time-varying financial and market information can be updated in each period.

An important practical result is that a discrete-time hazard model can be estimated as a multi-period logistic regression using company-period observations. The interpretation, however, is different from an ordinary static classifier: the fitted value is the conditional probability of bankruptcy in the current period given survival up to that period. Inference must also recognize that repeated observations from the same company are related.

Shumway finds that several accounting ratios used in earlier models lose statistical significance under the hazard specification. Market-based variables—relative market size, past stock returns and idiosyncratic return volatility—add useful information, and a model combining market and accounting variables produces stronger out-of-sample rankings in the paper's setting. The broader lesson is that model design, information timing and repeated observations can matter as much as the choice of financial ratios.

The current thesis does not estimate a survival or hazard model and does not use market variables. It instead estimates whether a defined SEC disclosure occurs within the next 60 days from each monthly decision date. Shumway remains relevant because it motivates repeated company assessment, time-varying predictors, careful treatment of the period at risk and strict use of information available at each decision date. The thesis should not claim that its monthly classifier is a Shumway hazard model.

## Comparison and relevance to this thesis

The three approaches answer related but different questions:

| Study | Main method | Primary output | Treatment of time | Main lesson for this thesis |
| --- | --- | --- | --- | --- |
| Altman (1968) | Multiple discriminant analysis | Classification score | One static observation per company | Combine several dimensions of financial condition rather than relying on one ratio. |
| Ohlson (1980) | Conditional logistic regression | Estimated bankruptcy probability | Static model at selected horizons | Use an interpretable probability benchmark and respect the date on which financial information becomes available. |
| Shumway (2001) | Discrete-time hazard model | Conditional period-by-period bankruptcy probability | Repeated observations with censoring and changing predictors | Represent firms repeatedly through time and align every predictor with the period in which it was known. |

These papers motivate the architecture of the present study without supplying a directly transferable model. The thesis combines accounting ratios as suggested by the broader Altman tradition, uses logistic regression as an interpretable benchmark following the probabilistic direction represented by Ohlson, and constructs repeated monthly observations with point-in-time information in line with the timing concerns emphasized by Shumway.

Important differences remain. The empirical target in this thesis is a new bankruptcy or payment-failure disclosure episode within 60 days, not the exact bankruptcy outcomes and horizons used in the three papers. The sample, reporting environment and evaluation period also differ. Consequently, their published coefficients, scores, thresholds and performance results are historical evidence about modeling approaches, not ready-made parameters for the current credit-limit policy.

## References

- Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. *The Journal of Finance, 23*(4), 589–609. <https://doi.org/10.1111/j.1540-6261.1968.tb00843.x>
- Ohlson, J. A. (1980). Financial ratios and the probabilistic prediction of bankruptcy. *Journal of Accounting Research, 18*(1), 109–131. <https://doi.org/10.2307/2490395>
- Shumway, T. (2001). Forecasting bankruptcy more accurately: A simple hazard model. *The Journal of Business, 74*(1), 101–124. <https://doi.org/10.1086/209665>
