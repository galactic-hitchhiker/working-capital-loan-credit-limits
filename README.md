# Master thesis research implementation

Supporting files for **Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning**.

The repository contains the Chapter 5 policy and the supporting workflow for monthly SEC data, four risk-model families, calibration, chronological evaluation, monthly predictions, policy replay, sensitivity analysis and figures. The complete workflow has been run on **synthetic software-test data**. Real-company event labels and facility inputs still need verification before an empirical model comparison or limit backtest can be reported.

Start with [workflow instructions](docs/workflow.md), [input requirements](docs/input_contracts.md) and the [reproducibility appendix](docs/reproducibility.md). Chapter 5 is in [chapter_5.md](docs/chapter_5.md).

## Read and run

The data/policy utilities use the standard library. Modeling and figures use the pinned packages in `requirements.txt`; the full checked environment is recorded in `requirements-lock.txt`. The environment is installed in `.venv` and was checked with Python 3.13.4.

```sh
.venv/bin/python run_research.py -m unittest discover -s tests -v
.venv/bin/python run_research.py demo_workflow.py --output-dir results/my_synthetic_check
python3 policy_examples.py
python3 sec_data.py --as-of 2026-09-01 --sample-size 100
```

Run these commands from this directory. They do not download or modify source data. The original example/audit scripts write `results/policy/` and `results/sec_audit/` and replace their reports when rerun. The new workflow scripts require a fresh output directory for each run. All support an explicit output directory. OpenMP is installed through Homebrew on this Mac, and XGBoost loads directly. The `run_research.py` launcher keeps plotting caches inside the project.

The pilot date is a reproducible example, not a chosen start/end date for the final empirical study. A complete inventory run is possible using `--sample-size 20335`, but it still produces only one snapshot per company at the specified date, not a monthly modeling panel.

## File map

| File | Purpose | Thesis location |
|---|---|---|
| `docs/chapter_5.md` | Complete Chapter 5 draft in simple English | Chapter 5 |
| `docs/thesis_review.md` | Review findings and changes still needed | Chapters 1–4 and outline |
| `docs/variable_dictionary.md` | Definitions, provenance rules and unavailable inputs | Chapter 3 / Appendix A |
| `credit_policy.py` | Capacity, exponential risk adjustment, caps, monthly rules and optional expected-loss scenario | Chapter 5 |
| `policy_examples.py` | Reproducible hypothetical cases and sensitivity scenarios | Chapter 5 / Appendix D |
| `sec_data.py` | Offline financial snapshots, provenance and candidate event filings | Chapter 3 |
| `temporal_validation.py` | Verified-label requirements and five chronological stages with purging | Chapters 3–4 |
| `tests/test_research.py` | Tests of financial invariants, information timing and label availability | Appendix B |
| `build_panel.py` | Monthly SEC features and verified outcomes from documented registers | Chapter 3 |
| `inputs/*.template.csv`, `configs/study.example.json` | Empty evidence registers and unresolved study settings | Chapters 3–4 |
| `risk_models.py`, `train_models.py` | Logistic, L2 logistic, random forest and XGBoost fitting, tuning and sigmoid calibration | Chapter 4 |
| `model_evaluation.py` | Metrics, threshold selection, model selection and company bootstrap intervals | Chapters 4 and 6 |
| `predict_monthly.py` | Later monthly predictions from the frozen selected model | Chapters 5 and 7 |
| `backtest_policy.py` | Sequential limits with explicit facility inputs and hard stops | Chapters 5 and 7 |
| `policy_sensitivity.py` | Fifteen policy-parameter scenarios on the same inputs | Chapter 7 |
| `make_figures.py` | Comparison, calibration and limit-path PNG/PDF exports | Chapters 6–7 |
| `research_common.py`, `run_research.py` | Input checks, hashes, version records and portable execution | Appendix B |
| `demo_workflow.py`, `tests/test_workflow.py` | Synthetic end-to-end check and workflow tests | Appendix B |
| `docs/input_contracts.md`, `docs/workflow.md`, `docs/reproducibility.md` | Input definitions, exact commands and implementation appendix | Appendices A–B |

Chapter references use filenames so they can later be replaced with GitHub links.

## Policy assumptions

All financial inputs must share a currency. Revenue and operating cash flow must cover the same annual or reconstructed trailing twelve-month period. The default fractions are 20% of two-month revenue, 50% of positive two-month operating cash flow and 10% of eligible cash. Capacity is the smaller of the revenue and cash-flow/cash amounts, less additional external payments due within 60 days, floored at zero.

`external_debt_service_60d` means payments **not already reflected in the cash-flow capacity estimate** and excludes principal on the studied facility. Do not subtract cash interest again if it is already reflected in operating cash flow. Reported total debt cannot replace a schedule of payments due. Reported cash cannot automatically replace verified eligible cash.

The risk multiplier is `exp(-k*q)` with illustrative `k=10`. An initial assessment uses the preliminary limit. Subsequent increases require a documented information change, must exceed 2% and are restricted by 50% smoothing and 10% monthly growth. All decreases are immediate. A zero-limit account requires an explicit fresh initial assessment to reopen. The hard-stop flag sets the limit to zero and preserves the outstanding balance as excess exposure.

The decision to set `information_changed`, clear eligibility checks or trigger `hard_stop` belongs to an upstream, documented process. The policy function does not automatically verify freshness, restricted cash, credit events or model validity. Its input/output dataclasses and the example exporter expose the relevant assumptions rather than pretending to perform these checks.

No parameter has been optimized or established as a safe lending standard. Negative operating cash flow contributes no positive flow capacity; the cash component can still produce capacity, which requires particular care in cash-burn scenarios. No transaction-level repayment, seasonality or utilization model is included.

## What the SEC pilot does

Source folders are `dataset/companyfacts/` and `dataset/submissions/`. Companyfacts has 20,335 CIK JSON files in the current download. The implemented scope is USD, standard US-GAAP tags and 10-K/10-Q filings including amendments. Other currencies, taxonomies and custom tags are outside this pilot. See the [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) for the source format.

Facts become available on the calendar day after their filing date. For each field, the code selects the latest relevant reporting period and the latest filing vintage known at the decision date. Conflicting facts at that selected vintage remain missing. It does not use fiscal-year labels or XBRL frames as availability dates. Original source tags, periods, filing dates and accession numbers are retained in `fact_provenance.json`.

Annual flows must span 330–400 days to accommodate fiscal-year variation. Revenue and net income are matched to the selected annual operating-cash-flow period. This is deliberately labelled **last reported annual**, not TTM. The annual-period filter and standard-tag coverage require further validation before creating the final sample. The pilot does not reconstruct quarterly flows from cumulative year-to-date reports.

Submissions include the main recent history and all historical files referenced by it. Form 8-K/8-K/A records mentioning Item 1.03 are exported as candidates for manual review. A filing date or report date is not accepted as a verified bankruptcy date. No candidate is automatically labelled a default, and no absence of a candidate is accepted as a negative outcome.

The sample contains evenly spaced CIKs from the sorted inventory. It is a technical pilot, not a representative sample or the final eligible company population. All selected rows are retained, including rows flagged by the conservative current-SIC sector screen. Current tickers and SIC codes do not establish historical listing status or historical eligibility.

## Completed pilot results

The run as of 2026-09-01 attempted 100 companies and produced 100 financial snapshot rows, with no reported file-processing errors. Matching submissions were found for all 100. Assets were available for 80, annual operating cash flow for 69 and period-matched annual revenue for 41. There were 11 **candidate filing records**, not 11 verified or distinct bankruptcy events. None of these counts describes the final non-financial study sample.

Full results are in `results/sec_audit/audit_summary.json`, `financial_snapshots.csv`, `fact_provenance.json` and `event_candidates.csv`. The hypothetical policy run produces six independent cases and 18 risk-sensitivity cases. Its numbers support the Chapter 5 worked example, not the empirical claims planned for Chapters 6–7.

## Before fitting empirical Chapter 4 models

1. Fix a historical company universe and study period without relying only on current listings. Define the sector exclusions and audit data coverage.
2. Verify a single event definition, dated events, source availability and complete observation coverage. Choose the horizon from the available event evidence. Count distinct events, not only positive company-month rows.
3. Build the monthly feature panel with period-consistent flows, documented debt tags, missingness rules and filing provenance. Specify financial-data freshness limits.
4. Freeze chronological training, tuning, calibration, model-selection and final-test periods. Purge labels whose outcome or availability crosses the next boundary. Audit event counts in each stage before fitting.
5. Run the implemented model comparison with the reviewed panel. It fits preprocessing only on fitting data, calibrates on separate data and applies the Chapter 4 selection rule before the final test.
6. Connect the resulting probabilities to explicit policy assumptions for eligible cash, additional debt payments, exposure and caps. Where public data is insufficient, use labelled scenarios or exclude those observations rather than inventing borrower inputs.

`make_label` requires complete verified follow-up and its availability date, including for negative labels. It does not establish those facts itself. `chronological_partition` enforces distinct month-start boundaries and rejects duplicate company-date rows; it does not choose dates or guarantee enough events for reliable modeling.

The raw dataset, virtual environment, binary model files and plotting caches are excluded from Git by `.gitignore`. Small reproducibility reports remain available for review. The current complete demonstration is in `results/synthetic_verified/`, and every figure is marked as synthetic. Its scores must not be used as thesis findings.
