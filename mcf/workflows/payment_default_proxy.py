"""Build and train the composite SEC payment-default disclosure proxy workflow.

The workflow combines Item 1.03 with conservatively qualified Item 2.04 filings.
It produces a disclosure proxy model; it does not claim verified payment defaults.
"""

import argparse
import json
import os
from argparse import Namespace
from datetime import date
from pathlib import Path

from mcf.common import load_design
from mcf.data.empirical import (
    PAYMENT_DEFAULT_PROXY_TARGET,
    inventory,
    panel,
)
from mcf.enrichment.item204.reviewers.ollama import DEFAULT_MODEL
from mcf.enrichment.item204.workflow import run as run_item_204
from mcf.models.train import run as train


def run(args):
    """Create Item 2.04 decisions, combined inventory, panel, and fitted models."""
    config = load_design(args.config)
    if config["event_type"] != PAYMENT_DEFAULT_PROXY_TARGET:
        raise ValueError(
            f"Config must use {PAYMENT_DEFAULT_PROXY_TARGET!r}"
        )
    cutoff = date.fromisoformat(config["observed_as_of"])
    root = args.output_dir
    root.mkdir(parents=True, exist_ok=True)

    if args.item_204_results:
        item_204_results = args.item_204_results
    else:
        item_204_results = run_item_204(
            Namespace(
                submissions=args.dataset / "submissions",
                output_dir=root / "item204",
                start=None,
                cutoff=cutoff,
                user_agent=args.user_agent,
                interval=args.interval,
                filing_limit=0,
                offline=args.offline,
                provider=args.provider,
                model=args.model,
                llm_limit=args.llm_limit,
                max_chars=args.max_chars,
                dry_run=False,
                refresh=args.refresh,
                retry_fallbacks=args.retry_fallbacks,
                host=args.host,
                num_ctx=args.num_ctx,
                timeout=args.timeout,
                think=args.think,
            )
        )

    inventory_report = inventory(
        args.dataset,
        root / "inventory",
        cutoff,
        item_204_results,
    )
    panel_report = panel(
        args.dataset,
        root / "inventory",
        args.config,
        root / "panel",
    )
    selection = train(
        args.config,
        root / "panel" / "panel.csv",
        root / "models",
        smoke=args.smoke,
    )
    summary = {
        "workflow": "payment-default-disclosure-proxy-v1",
        "target": PAYMENT_DEFAULT_PROXY_TARGET,
        "item_204_results": str(Path(item_204_results).resolve()),
        "inventory": {
            "directory": str((root / "inventory").resolve()),
            "companies": inventory_report["inventoried_companies"],
            "disclosure_records": inventory_report["disclosure_records"],
            "item_204_counts": inventory_report["item_204_counts"],
            "errors": len(inventory_report["errors"]),
        },
        "panel": {
            "directory": str((root / "panel").resolve()),
            "included_companies": panel_report["included_companies"],
            "distinct_positive_events": panel_report["distinct_positive_events"],
            "counts": panel_report["counts"],
        },
        "models": str((root / "models").resolve()),
        "selected_model": selection["selected_model"],
        "selection_status": selection["status"],
        "limitation": (
            "The model predicts a composite SEC disclosure proxy. It does not "
            "estimate a verified contractual payment-default probability."
        ),
    }
    (root / "workflow_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--dataset", type=Path, default=Path("../dataset"))
    result.add_argument(
        "--config",
        type=Path,
        default=Path("configs/study.payment_default_proxy.json"),
    )
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument(
        "--item-204-results",
        type=Path,
        help="Reuse a completed Item 2.04 final directory and skip LLM enrichment",
    )
    result.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    result.add_argument("--interval", type=float, default=0.25)
    result.add_argument("--offline", action="store_true")
    result.add_argument("--provider", choices=("ollama", "openai"), default="ollama")
    result.add_argument("--model", default=DEFAULT_MODEL)
    result.add_argument("--llm-limit", type=int, default=0)
    result.add_argument("--max-chars", type=int, default=24000)
    result.add_argument("--refresh", action="store_true")
    result.add_argument("--retry-fallbacks", action="store_true")
    result.add_argument("--host", default="http://localhost:11434")
    result.add_argument("--num-ctx", type=int, default=32768)
    result.add_argument("--timeout", type=int, default=600)
    result.add_argument("--think", action="store_true")
    result.add_argument("--smoke", action="store_true")
    return result


def main():
    command = parser()
    args = command.parse_args()
    if args.interval < 0.1 or args.llm_limit < 0 or args.max_chars < 100:
        command.error("invalid interval, LLM limit, or maximum input size")
    if args.refresh and args.retry_fallbacks:
        command.error("Use either --refresh or --retry-fallbacks")
    if args.provider == "openai" and args.model == DEFAULT_MODEL:
        command.error("--provider openai requires an explicit OpenAI --model")
    if args.num_ctx < 8192 or args.timeout <= 0:
        command.error("--num-ctx must be at least 8192 and --timeout positive")
    try:
        run(args)
    except (OSError, ValueError, KeyError) as exc:
        command.exit(2, f"Workflow stopped: {exc}\n")


if __name__ == "__main__":
    main()
