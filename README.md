# Master thesis: real-data study and complete draft

**Dynamic Determination of Short-Term Corporate Credit Limits Using Machine Learning**

Start with the [thesis index](docs/README.md). It links the abstract, eight separate chapters, references and four appendices. The draft uses simple English and double-dollar LaTeX delimiters. [Reproduction commands](docs/workflow.md) and the [review plan to 13 October 2026](docs/review_plan.md) are included.

## Completed empirical work

The models were trained and tested on the supplied local data in dataset/, with no synthetic training observations or generated outcome labels.

- 20,335 company-facts files inventoried.
- 588,111 labeled company-months from 9,075 issuers, before chronological purging.
- Target: first recorded SEC Form 8-K/8-K/A Item 1.03 disclosure within 60 days. This is not payment default.
- Four fitted families and 24 tuning candidates; separate chronological calibration and selection.
- Final test: 136,177 observations, 288 positive rows and 160 distinct event companies.
- XGBoost test ROC-AUC 0.8441 and average precision 0.01683.
- **No calibrated model passed the predefined selection-period probability-quality rule.** The main policy retains the predeclared constant fallback; fitted-model mappings are exploratory.
- Historical policy scenarios: 97,803 observations from 3,793 companies, with explicit assumptions for cash eligibility, additional payments, caps and facility exposure.

The thesis reports extreme accounting ratios and other sample limitations. It does not claim validated default probabilities, optimal lending amounts or observed loss reductions.

## Main supporting files

| File | Purpose |
|---|---|
| empirical_sec.py | Full source inventory, first-disclosure labels and monthly panel |
| sec_data.py, sec_point_in_time.py | Reference and efficient point-in-time financial extraction |
| configs/study.sec_disclosure.json | Fixed empirical target, dates and controls |
| risk_models.py, train_models.py | Full model comparison, calibration and preserved selection |
| model_evaluation.py, temporal_validation.py | Metrics, bootstrap uncertainty and chronology |
| credit_policy.py | Capacity, risk multiplier, caps and monthly rules |
| empirical_policy.py | Historical fallback and exploratory policy scenarios |
| configs/policy.sec_disclosure.json | Policy coefficients and scenario assumptions |
| empirical_report.py | Descriptive statistics and PNG/PDF research figures |
| export_thesis_evidence.py | Small evidence copies and generated Appendices C/D |
| tests/ | 78 checks, including real-history extraction equivalence |
| docs/ | Complete thesis draft, figures, evidence and instructions |

Full results are in results/empirical_inventory/, results/empirical_panel/, results/empirical_models/ and results/empirical_policy/. Final reports are in results/empirical_descriptive_final/, results/empirical_model_figures_final/ and results/empirical_policy_figures_final/. Small evidence files are copied to docs/tables/.

## Run and verify

The installed .venv uses Python 3.13.4 and the pinned requirements-lock.txt environment. Homebrew OpenMP is installed, and XGBoost runs directly. The launcher keeps plotting caches local.

~~~sh
.venv/bin/python run_research.py -m unittest discover -s tests -v
.venv/bin/python export_thesis_evidence.py
~~~

The second command refreshes thesis evidence copies and Appendices C/D from the completed outputs. The full offline inventory-to-report commands are in docs/workflow.md and use fresh output directories to preserve earlier results.

The original generic verified-event and facility-register workflow remains available through build_panel.py, predict_monthly.py and backtest_policy.py. It is separate from the approved SEC disclosure target. Synthetic examples remain software checks only.

## Rebuild the empirical study from scratch

The commands below rebuild the study when `results/` does not exist. Run them
from the repository root. They use only the local SEC files in `dataset/`; they
do not download data or create synthetic observations.

### 1. Check the source data

The empirical workflow requires company financial facts and filing histories:

~~~sh
ls dataset/companyfacts/CIK*.json | head
ls dataset/submissions/CIK*.json | head
~~~

`companyfacts/` contains reported accounting values. `submissions/` contains
filing dates, forms, Item 1.03 disclosures and references to older submission
files. Both sources are needed to reconstruct what was known at each historical
decision date.

### 2. Create the Python environment

Skip this step if `.venv/` already exists and has the locked dependencies.

~~~sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-lock.txt
~~~

Create local result and plotting-cache directories:

~~~sh
mkdir -p results/.matplotlib results/.cache
~~~

`run_research.py` directs Matplotlib and other caches into these project-local
directories. It does not change the research calculations.

### 3. Verify the code

~~~sh
.venv/bin/python run_research.py -m unittest discover -s tests -v
~~~

The tests check input contracts, point-in-time SEC extraction, chronological
partitioning, model preprocessing, training-only winsorization, model selection
and policy behavior. Passing tests verify the software; they are not empirical
model results.

### 4. Build the eligible issuer inventory

~~~sh
.venv/bin/python empirical_sec.py inventory \
  --dataset dataset \
  --cutoff 2026-09-07 \
  --output-dir results/full_run/inventory
~~~

This stage scans the SEC files and:

- matches company-facts and submissions histories by CIK;
- checks whether referenced historical submission files are present;
- identifies the issuer's observed reporting life;
- applies the study's domestic-filer and non-financial-sector screen;
- locates the first recorded Form 8-K or 8-K/A Item 1.03 disclosure; and
- records source hashes and exclusion counts for reproducibility.

The explicit cutoff matches `observed_as_of` in
`configs/study.sec_disclosure.json`. Do not change one date without reviewing
the other. Inspect `inventory_audit.json`, `issuer_inventory.csv` and
`disclosure_events.csv` after this command.

### 5. Construct the monthly point-in-time panel

~~~sh
.venv/bin/python empirical_sec.py panel \
  --dataset dataset \
  --inventory results/full_run/inventory \
  --config configs/study.sec_disclosure.json \
  --output-dir results/full_run/panel
~~~

For every eligible company and monthly decision date, this stage uses only
facts filed before that date. It period-matches balance-sheet and annual-flow
facts, calculates the configured ratios, retains missing values, and creates a
60-day forward disclosure label only when the outcome window is observable.

The active model panel includes `cash_and_equivalents_to_assets`.
`cash_only_to_assets` remains available in the SEC extraction logic for audit
and future experiments, but it is excluded from the configured predictors
because its empirical coverage is too low. Cash-and-equivalents reconstruction
keeps its source facts and derivation method in the provenance output.

Review these files before training:

- `panel_audit.json`: row counts, labels, exclusions and missing predictors;
- `panel.csv`: labeled observations used by the model workflow;
- `features.csv`: financial observations, including rows without usable labels;
- `feature_provenance.jsonl`: the SEC facts behind every retained row; and
- `companyfacts_hashes.jsonl`: hashes of the raw company-facts inputs.

### 6. Train, calibrate, select and evaluate models

~~~sh
.venv/bin/python run_research.py train_models.py \
  --config configs/study.sec_disclosure.json \
  --panel results/full_run/panel/panel.csv \
  --output-dir results/full_run/models
~~~

This is the full empirical run. Do not pass `--smoke`; smoke mode is only for
the synthetic software demonstration.

The command performs the chronological workflow defined in the study config:

1. Training estimates preprocessing and model parameters.
2. Tuning uses expanding annual folds to choose hyperparameters and class weighting. The first fold fits through 2016 and validates 2017; the second adds labels available by January 2018 and validates 2018.
3. The final base model is refitted on training plus tuning observations.
4. Calibration fits the probability mapping on the later calibration period.
5. Selection chooses the model and freezes its alert threshold.
6. Test evaluates the already frozen choice on the final period.

Ratio winsorization limits are the training period's 1st and 99th percentiles.
Those limits are frozen before tuning and reused for calibration, selection,
test and later predictions. Median imputation and missing-value indicators are
part of each model pipeline. Logistic models additionally standardize their
inputs.

The run compares logistic regression, L2 logistic regression, random forest
and XGBoost. Its main outputs are:

- `selection.json`: selected model, frozen thresholds and selection metrics;
- `evaluation.csv`: selection and untouched-test metrics;
- `tuning_scores.csv`: annual-fold summaries for every candidate;
- `tuning_fold_scores.csv`: each candidate's metrics in each validation year;
- `stage_audit.json`: chronological sample counts and winsorization limits;
- `winsorization.json`: an easy-to-review copy of the frozen limits;
- `models.joblib`: fitted pipelines, calibration objects and selection state;
- `predictions.csv`: row-level selection and test predictions;
- `reliability.csv`: probability-calibration summaries; and
- `coefficients.csv` and `feature_importance.csv`: model interpretation outputs.

Start the review with:

~~~sh
cat results/full_run/models/selection.json
cat results/full_run/models/stage_audit.json
cat results/full_run/models/winsorization.json
~~~

A `null` `selected_model` is an intentional outcome when no fitted model passes
the predefined selection rule. It is not a software failure.

### 7. Run the empirical policy scenarios

~~~sh
.venv/bin/python run_research.py empirical_policy.py \
  --models results/full_run/models/models.joblib \
  --features results/full_run/panel/features.csv \
  --policy configs/policy.sec_disclosure.json \
  --output-dir results/full_run/policy
~~~

This stage converts monthly financial inputs and model probabilities into the
hypothetical credit-policy paths defined by the policy configuration. It
applies cash eligibility, capacity rules, exposure assumptions, caps, hard
stops and reopening rules. If selection accepted no fitted model, the command
uses the predeclared constant fallback and labels fitted-model scenarios as
exploratory.

Policy outputs describe modeled scenarios. They are not observed lending
decisions or demonstrated loss reductions.

### 8. Generate tables and figures

~~~sh
.venv/bin/python run_research.py empirical_report.py data \
  --input results/full_run/panel/panel.csv \
  --output-dir results/full_run/descriptive

.venv/bin/python run_research.py empirical_report.py models \
  --input results/full_run/models \
  --output-dir results/full_run/model_report

.venv/bin/python run_research.py empirical_report.py policy \
  --input results/full_run/policy \
  --output-dir results/full_run/policy_report

.venv/bin/python policy_examples.py \
  --output-dir results/full_run/worked_examples
~~~

The three report commands turn the panel, model evaluations and policy paths
into compact CSV summaries and publication-ready PNG/PDF figures. The final
command creates the hypothetical worked examples used to explain the policy
mechanics.

After a complete run, the directory structure is:

~~~text
results/full_run/
├── inventory/
├── panel/
├── models/
├── policy/
├── descriptive/
├── model_report/
├── policy_report/
└── worked_examples/
~~~

### 9. Optionally refresh the thesis evidence

Only do this after reviewing and accepting the new run. The exporter updates
the evidence copies and generated appendices under `docs/`; it does not retrain
the models.

~~~sh
.venv/bin/python export_thesis_evidence.py \
  --docs docs \
  --inventory results/full_run/inventory \
  --panel results/full_run/panel \
  --models results/full_run/models \
  --descriptive results/full_run/descriptive \
  --model-report results/full_run/model_report \
  --policy results/full_run/policy \
  --policy-report results/full_run/policy_report \
  --examples results/full_run/worked_examples
~~~

Use a different run name in every command, such as `results/robustness_run`, to
preserve `full_run` and compare specifications without overwriting evidence.
The shorter command reference remains in [docs/workflow.md](docs/workflow.md).

The current .gitignore excludes docs/, results/ and dataset/. These deliverables exist locally; include selected manuscript and evidence files deliberately when preparing a repository release.
