# Statement Enrichment Comparison

This matched comparison supports the primary model experiment, stored internally as `run_006_full_statement_enrichment`. The full importer completed for 79 SEC Financial Statement and Notes archives,
yielding 2,928,745 dated source facts for 10,759 companies. Most are direct
statement totals and many duplicate Company Facts; the panel's native priority
rules determine which values actually change a monthly feature. The importer
audit is `../dataset_full/statement_facts/audit.json`.

## Matched comparison on the new SEC snapshot

I rebuilt `results/run_006_full_statement_enrichment/panel_without_statements` using the **same**
`../dataset_full` snapshot, inventory, study configuration and code as the
enriched panel, omitting only `--statement-facts`. Both panels have 565,222
labeled company-months, 8,780 included companies, 1,052 positive rows and
573 positive events. The ordered comparison confirms unchanged labels and
feature availability before each decision date.

| Feature | Missing without statements | Missing with statements | Recovered cells |
| --- | ---: | ---: | ---: |
| Liabilities / assets | 99,831 | 52,646 | 47,185 |
| 12-month leverage change | 131,621 | 87,963 | 43,658 |
| Operating cash flow / average liabilities | 104,108 | 59,801 | 44,307 |
| Current ratio | 27,675 | 27,431 | 244 |
| Working capital / assets | 27,540 | 27,296 | 244 |
| Cash / assets | 51,097 | 51,043 | 54 |

Across all features, **135,692 missing cells were filled**, none became
missing, and 5,021 previously observed cells were revised. Fully observed
rows increased from **362,979 to 398,329** (+35,350). Other feature
missingness did not change. The exact comparison, with panel hashes, is
`results/run_006_full_statement_enrichment/statement_enrichment_comparison.json`.

I trained the same model workflow on each matched panel. Both selected a
random forest on the 2020–2022 selection period. Test results use the same
131,842 rows, 318 positive rows and 4,633 companies in 2023–2025:

| Test metric | Without statements | With statements |
| --- | ---: | ---: |
| ROC AUC | 0.87967 | 0.88659 |
| Average precision | 0.02555 | 0.02599 |
| Brier score (lower is better) | 0.00238501 | 0.00238402 |
| Precision at selected threshold | 5.56% | 5.63% |
| Recall at selected threshold | 10.69% | 9.12% |
| True positives / false positives | 34 / 578 | 29 / 486 |

The selected threshold changed from 0.05405 to 0.05797. A paired
company-cluster bootstrap over the matched test rows (300 replicates, seed 42)
estimated 95% intervals for **enriched minus unenriched** differences:

| Metric difference | Point difference | Paired 95% interval |
| --- | ---: | ---: |
| ROC AUC | +0.00692 | -0.00184 to +0.01545 |
| Average precision | +0.00044 | -0.00395 to +0.00298 |
| Brier score | -0.00000099 | -0.00000444 to +0.00000230 |

Every interval includes zero. This is strong evidence of improved **feature
coverage**, but not of a reliable predictive gain. The paired intervals are
conditional on the fitted and selected models; they do not incorporate model
selection uncertainty, calendar shocks or the earlier target-design revision.
The bootstrap details are in `results/run_006_full_statement_enrichment/paired_test_comparison.json`.

## Direct comparison with run 005

Run 005 used the earlier local SEC snapshot and lacked full statement
enrichment. The new panel has 565,222 rows and 8,780 companies versus
563,607 and 8,770 in run 005. On 562,193 shared rows, 135,444 feature cells
were recovered, 60 became missing and 5,472 observed values changed. There
were 3,029 added and 1,414 removed rows. Shared labels were unchanged.
These differences combine the source-snapshot change, the assets fallback
and statement enrichment; use the matched comparison above to isolate the
statement effect. The exact comparison is
`results/run_006_full_statement_enrichment/comparison_to_run_005.json`.

Run 005 selected XGBoost: test AUC 0.90501, AP 0.02647, Brier 0.00242906,
precision 5.30%, recall 14.78%. The enriched primary model experiment selected random forest:
test AUC 0.88659, AP 0.02599, Brier 0.00238402, precision 5.63%, recall
9.12%. The test samples differ slightly (131,866 vs 131,842 rows), and the
model family and threshold changed. The run 005 versus primary model experiment comparison
does not isolate the effect of statement data. Both evaluations remain
retrospective; the 2023–2025 period was examined during prior development.

## Thesis policy replay

The primary model experiment's selected model was also replayed with the thesis's existing
illustrative policy settings. After excluding missing or invalid required
policy inputs, the base scenario covers 99,619 company-months from 3,869
companies. Its median limit is USD 4.23 million and its mean limit is 0.6678%
of assets. These are conditional policy outputs, not observed lending results.
The audit and sensitivity results are under
`results/run_006_full_statement_enrichment/policy/`.
