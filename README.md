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
| tests/ | 70 checks, including real-history extraction equivalence |
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

The current .gitignore excludes docs/, results/ and dataset/. These deliverables exist locally; include selected manuscript and evidence files deliberately when preparing a repository release.
