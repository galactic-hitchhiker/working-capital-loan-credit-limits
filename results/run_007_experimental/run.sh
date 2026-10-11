#!/usr/bin/env bash
set -euo pipefail

run_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$run_dir/../.." && pwd)"
cd "$repo_root"

.venv/bin/python -m mcf.workflows.launcher -m mcf.workflows.payment_default_proxy \
  --dataset ../dataset_full \
  --config "$run_dir/design.json" \
  --item-204-results results/item_204_openai_batch_review \
  --statement-facts ../dataset_full/statement_facts/companies \
  --output-dir "$run_dir"
