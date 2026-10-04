# Results history

This directory preserves completed and partial research runs as project-evolution
evidence. Numbered folders show the order in which each track developed. Original
artifacts, manifests, model files, row-level outputs and review caches remain
inside each snapshot. `model_comparison.csv` and
`item_204_enrichment_comparison.csv` provide compact machine-readable comparisons;
`index.json` records the original names, dependencies and purpose of every folder.
`artifact_hashes.json` preserves SHA-256 hashes for key audit, design, metric,
classification and review artifacts so later comparisons can verify integrity.

## Item 1.03 model evolution

| Snapshot | Original folder | Main change | Selected model | Held-out ROC-AUC | Average precision | Brier | Precision | Recall |
|---|---|---|---|---:|---:|---:|---:|---:|
| `01_initial_full_pipeline_xgboost` | `full_run` | First complete 12-feature SEC run | XGBoost | 0.911792 | 0.031478 | 0.002114 | 0.049242 | 0.180556 |
| `02_improved_sec_fact_coverage_xgboost` | `full_run_1` | Improved liabilities extraction and predictor coverage | XGBoost | 0.910044 | 0.035369 | 0.002090 | 0.040000 | 0.190972 |
| `03_rolling_temporal_validation_random_forest` | `full_run_2` | Rolling temporal tuning and final reporting/policy materials | Random forest | 0.908873 | 0.027475 | 0.002087 | 0.039700 | 0.128472 |

The second snapshot reused the inventory from snapshot 01. The third snapshot
reused the improved panel from snapshot 02. Consequently, the thesis evidence is
assembled from:

- snapshot 01: `inventory/`;
- snapshot 02: `panel/`;
- snapshot 03: `models/`, reports, policy output and worked examples.

Metrics above use each selected model, its selected calibration mapping and its
frozen threshold on the 2023–2025 test period. They document historical runs and
must be interpreted with the design stored inside each snapshot.

## Item 2.04 enrichment evolution

| Snapshot | Original folder | Purpose | Completeness |
|---|---|---|---|
| `01_rule_classifier_v3_local_evidence` | `item_204_review` | Rule-based discovery, HTML cache and v3 classifications | 2,688 records; 237 qualified, 977 non-default, 1,474 manual |
| `02_openai_gpt_5_6_luna_incomplete_review` | `item_204_llm_review` | Early OpenAI LLM review attempt | Incomplete because the provider stopped after an API error |
| `03_ollama_qwen3_5_9b_pilot` | `item_204_ollama_review` | Local Qwen review and cache pilot | 10 stored decisions; pilot only |
| `04_ollama_gemma3_4b_pilot` | `item_204_gemma4b_review` | Local Gemma review and fallback-storage pilot | 10 stored decisions; pilot only |

These are development artifacts. They predate the unified rules-then-LLM workflow
and must not be treated as a completed composite payment-default-proxy dataset.

## Incomplete experiments

`incomplete_experiments/01_empty_ocf_feature_run` preserves the empty directory
created for an OCF feature experiment. It contains no result artifacts and is kept
only to document the abandoned run name.

## Adding future runs

Write new work to a fresh directory under `results/`. After it is complete, move
it into the appropriate numbered history track and add an entry to both this file
and `index.json`. Never overwrite an existing historical snapshot.
