#!/usr/bin/env bash
set -euo pipefail

run_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$run_dir/../.." && pwd)"
cd "$repo_root"

# Optional first argument reuses a panel and its adjacent provenance files.
panel="${1:-$run_dir/panel/panel.csv}"
if [[ ! -f "$panel" ]]; then
  echo "Panel not found: $panel. Build it first or pass an existing panel.csv." >&2
  exit 1
fi

.venv/bin/python -u -m mcf.workflows.launcher -m mcf.models.train \
  --config "$run_dir/design.json" \
  --panel "$panel" \
  --output-dir "$run_dir/models" 2>&1 | tee "$run_dir/train.log"
