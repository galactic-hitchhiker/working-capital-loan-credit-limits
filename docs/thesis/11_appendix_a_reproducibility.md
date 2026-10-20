# Appendix A: Reproducibility and Code Availability

## A.1 Primary Experiment and Evidence

The accompanying project repository contains the source code, configuration files and saved evidence used in this thesis. The primary model experiment uses `configs/study.bankruptcy_or_payment_failure.json`. The policy uses `configs/policy.sec_disclosure.json`. The internal artifact directory is `results/run_006_full_statement_enrichment/`. The internal name is retained here so the reported results can be traced to the saved files.

| Material | Location |
|---|---|
| SEC inventory and disclosure events | `results/run_006_full_statement_enrichment/inventory/` |
| Monthly panel and input provenance | `results/run_006_full_statement_enrichment/panel/` |
| Fitted models, selection and evaluation | `results/run_006_full_statement_enrichment/models/` |
| Policy replay and sensitivity results | `results/run_006_full_statement_enrichment/policy/` |
| Thesis evidence copies | `docs/thesis/tables/` and `docs/thesis/figures/` |
| Reproduction instructions | `docs/guides/workflow.md` |

*Table 24. Primary experiment evidence and locations.*

The SEC source snapshot has an observation cutoff of 7 September 2026. Each completed stage records a manifest and hashes of its inputs. Output directories must be empty before a run, preventing an existing result from being overwritten silently.

## A.2 Model and Validation Settings

All model families use median imputation fitted only on the relevant training data, with separate missing-value indicators. Logistic models also standardize their inputs. The experiment applies no winsorization or synthetic oversampling.

| Model family | Candidate settings |
|---|---|
| Logistic regression | No penalty, LBFGS, 5,000 maximum iterations |
| L2 logistic regression | $$C=0.1$$, $$1$$ or $$10$$ |
| Random forest | 300 trees, depth 3 or unrestricted, minimum leaf size 5 or 20 |
| XGBoost | 200 trees, depth 2 or 4, learning rate 0.05 or 0.1 |

*Table 25. Candidate settings by model family.*

Each setting is fitted with and without balanced class weights, producing 24 candidates. Tuning uses two expanding temporal folds: fit through 2016 and validate on 2017, then fit through 2017 and validate on 2018. Candidates are ranked within each family by mean annual average-precision lift, followed by mean annual Brier skill and a fixed candidate order.

Probability correction is fitted on 2019 observations. Raw and sigmoid-corrected probabilities are compared on 2020–2022 by Brier score. A family is accepted only when its average precision exceeds the selection-period event share and its Brier score is lower than the constant training-rate benchmark. The lowest-Brier accepted family is selected. Alert thresholds maximize selection-period F1 and are then frozen for 2023–2025.

The random seed is 42. Tree fitting uses up to four CPU threads, and the company-cluster bootstrap uses 500 repetitions. All monthly observations for a sampled company remain together in each bootstrap repetition.

## A.3 Implementation Map

| Component | Main location |
|---|---|
| SEC extraction, accounting reconciliation and panel construction | `mcf/data/` |
| Automated Item 2.04 review workflow | `mcf/enrichment/item204/` |
| Model fitting, calibration and evaluation | `mcf/models/` |
| Credit-limit calculation and historical replay | `mcf/policy/` |
| Tables, figures and evidence export | `mcf/reporting/` |
| Automated tests | `tests/` |

*Table 26. Implementation components and main code locations.*

## A.4 Software Environment

| Software | Version |
|---|---:|
| Python | 3.13.15 |
| NumPy | 2.2.6 |
| SciPy | 1.15.3 |
| scikit-learn | 1.6.1 |
| XGBoost | 3.0.2 |
| Matplotlib | 3.10.3 |
| joblib | 1.5.1 |

*Table 27. Software environment used for the primary experiment.*

The full dependency set is recorded in `requirements-lock.txt`. Sigmoid correction uses scikit-learn's `CalibratedClassifierCV` with `FrozenEstimator`.

## A.5 Reproduction and Label-Review Limits

The command sequence is documented in `docs/guides/workflow.md`. Tests cover information availability, restatements, period matching, conflicting facts, disclosure windows, chronological purging, preprocessing isolation, temporal folds, model selection and policy invariants. These tests verify implemented behavior. They do not establish that every filing fact is economically correct or that the policy is suitable for lending.

Item 2.04-only filings were reviewed through an automated language-model workflow. A filing qualifies only when the saved review has high certainty, includes supporting quotations and explicitly identifies a missed principal or interest payment. Acceleration or enforcement alone does not qualify, and unresolved reviews remain excluded or censor affected outcomes. The saved classifications and hashes support reproduction, but no independent human-validation sample is available. A new automated review could produce different classifications.
