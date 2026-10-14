# Appendix B: Implementation and Reproducibility

## B.1 Completed Experiment

The primary model experiment's dataset combines local SEC Company Facts, Financial Statement and Notes facts, and submissions in one panel. Its target is a new qualifying Item 1.03 bankruptcy or receivership or reviewed Item 2.04 payment-failure disclosure episode within 60 days. Settings are in `configs/study.bankruptcy_or_payment_failure.json`. The stages are training in 2011–2016, tuning in 2017–2018, calibration in 2019, selection in 2020–2022 and later evaluation in 2023–2025. Boundary observations are purged until their complete labels are observable.

The primary model experiment selects a random forest with its raw probability and freezes a threshold of 0.0579707. Sigmoid calibration worsens selection Brier error. Its policy replay uses this selected model.

## B.2 Implementation Map

| Component | Files |
|---|---|
| Source inventory and disclosure labels | mcf/data/empirical.py, mcf/data/payment_failure.py |
| Automated Item 2.04 reviews | mcf/enrichment/item204/reviewers/openai_batch.py |
| Point-in-time financial extraction | mcf/data/sec.py, mcf/data/point_in_time.py |
| Monthly dates, input checks and file hashes | mcf/common.py |
| Chronological label-availability purge | mcf/models/temporal.py |
| Model families and grids | mcf/models/risk.py |
| Rolling tuning, calibration, selection and evaluation | mcf/models/train.py |
| Metrics, thresholds and company bootstrap | mcf/models/evaluation.py |
| Policy calculation and empirical replay | mcf/policy/credit.py, mcf/policy/empirical.py |
| Hypothetical worked examples | mcf/policy/examples.py |
| Tables, figures and thesis evidence | mcf/reporting/empirical.py, mcf/reporting/thesis_evidence.py |
| Tests | tests/test_research.py, tests/test_workflow.py, tests/test_empirical.py |

The generic `mcf/data/panel.py`, `mcf/models/predict.py`, `mcf/policy/backtest.py` and `mcf/policy/sensitivity.py` workflow remains available for independently verified event and facility registers. It is separate from the disclosure-specific experiment.

## B.3 Models and Numerical Settings

All model families use fitting-only median imputation with missing indicators. Logistic models also standardize inputs. No winsorization or synthetic oversampling is applied.

| Family | Grid |
|---|---|
| Logistic | No penalty; LBFGS; 5,000 maximum iterations |
| L2 logistic | C = 0.1, 1, 10 |
| Random forest | 300 trees; depth 3 or unrestricted; minimum leaf 5 or 20 |
| XGBoost | 200 trees; depth 2 or 4; learning rate 0.05 or 0.1 |

Unweighted and balanced fits produce 24 candidates. Tuning uses two expanding temporal folds: fit through 2016 and validate 2017, then fit through 2017 and validate 2018. Candidates are ranked by mean annual average-precision lift, then mean annual Brier skill and fixed candidate order. The winner in each family is refitted on training plus tuning.

The random seed is 42 and tree fitting uses up to four CPU threads. XGBoost uses the histogram method and binary logistic objective. Logistic convergence warnings stop the run. Sigmoid calibration uses scikit-learn's `CalibratedClassifierCV` with `FrozenEstimator`. Average precision uses the step-weighted implementation; undefined precision and recall are set to zero. Remaining defaults follow the pinned package versions below.

Probability mapping is fitted on 2019 data and evaluated in 2020–2022. Raw and sigmoid mappings are compared by selection Brier score. Model acceptance requires average precision above the selection event share and Brier error below the constant original-training-prevalence benchmark. Lowest Brier wins among accepted families. Thresholds maximize selection-period F1, with recall and threshold breaking ties.

Company-cluster bootstrap intervals use 500 repetitions and retain all monthly rows for each sampled company. They are conditional on the fitted model and do not capture common time shocks or model-selection uncertainty.

## B.4 Current Result Locations

| Artifact | Location |
|---|---|
| Inventory, disclosure events and source hashes | results/run_006_full_statement_enrichment/inventory/ |
| Saved Item 2.04 reviews and audit | results/item_204_openai_batch_review/ |
| Panel, model features and provenance | results/run_006_full_statement_enrichment/panel/ |
| Fitted models, selection and evaluation | results/run_006_full_statement_enrichment/models/ |
| Descriptive summaries and model figures | results/run_006_full_statement_enrichment/descriptive/ and model_report/ |
| Policy decisions and sensitivity | results/run_006_full_statement_enrichment/policy/ |
| Policy reports and case studies | results/run_006_full_statement_enrichment/policy_report/ |
| Separate hypothetical worked examples | results/history/item_103_model_evolution/03_rolling_temporal_validation_random_forest/worked_examples/ |
| Thesis evidence copies | docs/thesis/tables/ and docs/thesis/figures/ |

Each result stage writes a manifest and hashes its inputs. New output directories must be empty, preventing silent overwrites. The older Item 1.03-only work is retained under `results/history/`.

## B.5 Software Environment

| Technology | Version or role |
|---|---|
| Python | 3.13.15 |
| NumPy | 2.2.6 |
| SciPy | 1.15.3 |
| scikit-learn | 1.6.1 |
| XGBoost | 3.0.2 |
| Matplotlib | 3.10.3 |
| joblib | 1.5.1 |
| CSV, JSON and JSONL | Data, audits, predictions and provenance |
| Markdown, PNG and PDF | Thesis text and figures |

The pinned packages are recorded in `requirements-lock.txt`. `mcf/workflows/launcher.py` directs plotting caches to project-local paths.

## B.6 Reproduction and Verification

The exact command sequence is documented in `docs/guides/workflow.md`. The tests cover information availability, restatements, period matching, conflicting facts, disclosure windows, chronological purging, preprocessing isolation, temporal folds, selection and policy invariants.

Tests establish the implemented software behavior. They do not establish the economic validity of every filing fact or the suitability of a real credit decision. The target is a bankruptcy or reviewed payment-failure disclosure episode, not verified facility default. Policy outputs remain hypothetical because exposure, repayments, defaults, recoveries, losses, pricing and profitability are unobserved.

The 2023–2025 period is excluded from all primary model experiment development steps. Because the same years were examined in earlier project iterations, including before the broader target was specified, the thesis treats this evaluation as retrospective and does not claim pristine external validation.

## B.7 Automated Disclosure Review Provenance

The saved `classifications.jsonl` contains 2,968 filing records reviewed through OpenAI Batch. Per-record requested models are `gpt-6-luna` for 2,027 records and `gpt-6-sol` for 941. The audit names `gpt-6-sol`, so the audit alone does not describe the mixed review history. Per-record metadata preserve requested and returned models, review status, settings and input hashes where available. Missing or failed reviews remain unresolved.

The review version is `item204-llm-v6-all-filings`, with context version `item204-openai-v1-source-bounded`. The primary model experiment reuses these saved reviews but applies the narrower payment-failure rule in `mcf/data/payment_failure.py`: high certainty, supporting quotations and an explicit payment-failure classification are required. Acceleration or enforcement alone does not qualify. The original review's broad classification totals are therefore not the final target counts.

No independent human validation sample is documented in the saved run. Model certainty and supporting quotations aid traceability but do not establish label accuracy. Reproduction uses the saved reviews and hashes; a fresh automated review could produce different labels.
