# Appendix B: Implementation and Reproducibility

## B.1 Completed Experiment

The completed study uses local SEC company-facts and submissions data and first-recorded Item 1.03 disclosure labels. Its settings are in `configs/study.sec_disclosure.json`. The chronological stages are training in 2011–2016, tuning in 2017–2018, calibration in 2019, selection and robustness in 2020–2022, and held-out evaluation in 2023–2025. Boundary observations are purged until their complete 60-day labels are observable.

The reported run selects random forest with its identity probability mapping and freezes a threshold of 0.0410103. The identity mapping is the forest's raw predicted probability; it is retained because sigmoid calibration worsens selection Brier error. The base policy uses this selected model.

## B.2 Implementation Map

| Component | Files |
|---|---|
| Source inventory and disclosure labels | mcf/data/empirical.py |
| Point-in-time financial extraction | mcf/data/sec.py, mcf/data/point_in_time.py |
| Monthly dates, input checks and file hashes | mcf/common.py |
| Chronological label-availability purge | mcf/models/temporal.py |
| Model families and grids | mcf/models/risk.py |
| Rolling tuning, calibration, selection and evaluation | mcf/models/train.py |
| Metrics, thresholds and company bootstrap | mcf/models/evaluation.py |
| Policy calculation and empirical replay | mcf/policy/credit.py, mcf/policy/empirical.py |
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

Probability mapping is fitted on 2019 data and evaluated in 2020–2022. Raw and sigmoid mappings are compared by selection Brier score. Model acceptance requires average precision above the selection event share and Brier error below the constant original-training-prevalence benchmark. Lowest Brier wins among accepted families. Thresholds maximize selection-period F1, with recall and threshold breaking ties.

Company-cluster bootstrap intervals use 500 repetitions and retain all monthly rows for each sampled company. They are conditional on the fitted model and do not capture common time shocks or model-selection uncertainty.

## B.4 Current Result Locations

| Artifact | Location |
|---|---|
| Inventory, disclosure events and source hashes | results/full_run/inventory/ |
| Panel, model features and provenance | results/full_run_1/panel/ |
| Fitted models, selection and evaluation | results/full_run_2/models/ |
| Descriptive summaries | results/full_run_2/descriptive/ |
| Model reports and figures | results/full_run_2/model_report/ |
| Policy decisions and sensitivity | results/full_run_2/policy/ |
| Policy reports and case studies | results/full_run_2/policy_report/ |
| Worked examples | results/full_run_2/worked_examples/ |
| Thesis evidence copies | docs/tables/ and docs/figures/ |

The split run names record successive data and modeling revisions: `full_run` contains the inventory, `full_run_1` the improved panel, and `full_run_2` the final model and policy outputs. Every result stage writes a manifest and hashes its inputs and source files. New output directories must be empty, preventing silent overwrites.

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

The exact command sequence is documented in `docs/workflow.md`. The tests cover information availability, restatements, period matching, conflicting facts, disclosure windows, chronological purging, preprocessing isolation, temporal folds, selection and policy invariants.

Tests establish the implemented software behavior. They do not establish the economic validity of every filing fact or the suitability of a real credit decision. The target is an Item 1.03 disclosure, not payment default. Policy outputs remain hypothetical because exposure, repayments, defaults, recoveries, losses, pricing and profitability are unobserved.

The 2023–2025 period is excluded from all final-run model-development steps. Because the same years were examined in earlier project iterations, the thesis calls this a held-out evaluation and does not claim a pristine external validation.
