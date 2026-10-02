# References

Altman, E. I. (1968). Financial ratios, discriminant analysis and the prediction of corporate bankruptcy. *The Journal of Finance, 23*(4), 589–609. [Original article](https://doi.org/10.1111/j.1540-6261.1968.tb00843.x).

Basel Committee on Banking Supervision. (n.d.). *Basel Framework: CRE35, Treatment of expected losses and recognition of provisions*. Bank for International Settlements. [Framework chapter](https://www.bis.org/basel_framework/chapter/CRE/35.htm). Accessed 21 September 2026. Used for conceptual definitions, not as a statement that this research implements regulatory capital requirements.

Breiman, L. (2001). Random forests. *Machine Learning, 45*, 5–32. DOI: 10.1023/A:1010933404324. [Author's paper](https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf).

Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785–794). DOI: 10.1145/2939672.2939785. [Authors' paper](https://arxiv.org/abs/1603.02754).

European Banking Authority. (2020). *Guidelines on loan origination and monitoring* (EBA/GL/2020/06). [Official publication](https://eba.europa.eu/activities/single-rulebook/regulatory-activities/credit-risk/guidelines-loan-origination-and-monitoring). Accessed 21 September 2026.

Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. *The Annals of Statistics, 29*(5), 1189–1232. [Original article](https://doi.org/10.1214/aos/1013203451).

Ohlson, J. A. (1980). Financial ratios and the probabilistic prediction of bankruptcy. *Journal of Accounting Research, 18*(1), 109–131. [Original article](https://www.jstor.org/stable/2490395).

Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. *PLOS ONE, 10*(3), e0118432. [Original article](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0118432).

Scikit-learn developers. (2025). *Scikit-learn 1.6.1 documentation: Logistic regression*. [Versioned documentation](https://scikit-learn.org/1.6/modules/linear_model.html#logistic-regression). Accessed 21 September 2026.

Scikit-learn developers. (2025). *Scikit-learn 1.6.1 documentation: CalibratedClassifierCV*. [Versioned API documentation](https://scikit-learn.org/1.6/modules/generated/sklearn.calibration.CalibratedClassifierCV.html). Accessed 21 September 2026.

Shumway, T. (2001). Forecasting bankruptcy more accurately: A simple hazard model. *The Journal of Business, 74*(1), 101–124. [Original article](https://www.jstor.org/stable/10.1086/209665).

U.S. Securities and Exchange Commission. (n.d.). *EDGAR application programming interfaces*. [Official source documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Accessed 21 September 2026.

U.S. Securities and Exchange Commission. (n.d.). *Form 8-K: Current report*, Item 1.03, Bankruptcy or Receivership. [Official form](https://www.sec.gov/files/form8-k.pdf). Accessed 21 September 2026.

## Research data and implementation

U.S. Securities and Exchange Commission. *EDGAR company facts and submissions*, local snapshot supplied for this project in September 2026. Local sources: dataset/companyfacts/ and dataset/submissions/. Observation cutoff: 7 September 2026. Individual source hashes, filing accessions and selected facts are recorded in source_hashes.jsonl, companyfacts_hashes.jsonl and feature_provenance.jsonl.

Project implementation. *Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning*, Python research files and September 2026 empirical outputs. Chapter file references identify the implementation and result artifacts. Their full local paths are mapped in 12_appendix_b_reproducibility.md; repository URLs can replace the filename references when published.
