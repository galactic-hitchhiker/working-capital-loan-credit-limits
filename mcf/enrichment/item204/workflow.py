"""Discover Item 1.03/2.04 filings and review every filing using OpenAI Batch.

Run from the repository root:
    .venv/bin/python -m mcf.enrichment.item204.workflow [parameters]

Parameters:
    --items ITEM ...: Discover 2.04 by default; use 1.03 2.04 for payment failure.
    --payment-failure-only: Use payment-specific classification and separate cache identity.
    --batch-max-requests N: Maximum requests per sequential Batch job (default: 50000).
    --submissions PATH: Required directory of downloaded SEC submissions JSON files.
    --output-dir PATH: Source/cache and final-review root (default: results/item_204_pipeline).
    --start YYYY-MM-DD: Inclusive filing-date lower bound (default: no lower bound).
    --cutoff YYYY-MM-DD: Exclusive filing-date upper bound (default: no upper bound).
    --user-agent TEXT: SEC identification with contact email (default: SEC_USER_AGENT).
    --interval SECONDS: SEC request spacing, at least 0.1 (default: 0.25).
    --filing-limit N: Limit source filings for a pilot (default: 0, all).
    --offline: Use cached HTML only; OpenAI calls still occur (default: off).
    --llm-limit N: Limit new filing review attempts per run (default: 0, all).
    --dry-run: Inspect sources/write local outputs without OpenAI calls; SEC downloads
        still occur unless --offline is also set (default: off).
    --model NAME: OpenAI model for new requests (default: gpt-6-luna).
    --reasoning-effort LEVEL: none, low, medium, high, xhigh or max (default: medium);
        supported levels depend on the selected model.
    --max-output-tokens N: Per-request output cap, including reasoning (default: 3000);
        does not truncate input filing text.
    --batch-id ID: Recover an interrupted submission using its existing OpenAI Batch ID.
    --refresh: Ignore saved decisions and request fresh reviews (default: off).
    --retry-fallbacks: Retry saved provider failures while retaining other decisions
        (default: off); cannot be combined with --refresh.
    -h, --help: Show command usage and exit.

OpenAI calls require OPENAI_API_KEY. Rerun the same command to collect pending
batches and reuse completed reviews. Full available filing text is sent; identical
requests are deduplicated. Missing source text is reported for follow-up.
SEC downloads require --user-agent or SEC_USER_AGENT with a contact email.
"""

import argparse
import json
import os
from argparse import Namespace
from datetime import date
from pathlib import Path

from mcf.common import file_hash
from mcf.enrichment.item204.discover import run as run_discovery
from mcf.enrichment.item204.reviewers.openai_batch import DEFAULT_MODEL, add_options, run as run_openai_batch
from mcf.enrichment.item204.reviewers.common import APIReviewError


def run(args):
    """Discover/download every selected filing, then classify it with OpenAI Batch."""
    root = args.output_dir
    source_dir = root / "source"
    final_dir = root / "final"
    root.mkdir(parents=True, exist_ok=True)
    # Reuse source documents downloaded by the previous workflow without retaining
    # any of its heuristic labels or downloading the same documents again.
    legacy_html = root / "rules" / "html"
    html_dir = source_dir / "html"
    if not html_dir.is_dir() and legacy_html.is_dir():
        html_dir = legacy_html

    run_discovery(
        Namespace(
            submissions=args.submissions,
            output_dir=source_dir,
            html_dir=html_dir,
            start=args.start,
            cutoff=args.cutoff,
            user_agent=args.user_agent,
            interval=args.interval,
            limit=args.filing_limit or None,
            offline=args.offline,
            discover_only=False,
            items=getattr(args, "items", ["2.04"]),
        )
    )

    review_args = Namespace(
        input=source_dir / "filings.jsonl",
        html_dir=html_dir,
        output_dir=final_dir,
        model=args.model,
        start=args.start,
        cutoff=args.cutoff,
        limit=args.llm_limit,
        dry_run=args.dry_run,
        refresh=args.refresh,
        retry_fallbacks=args.retry_fallbacks,
    )
    review_args.batch_id = getattr(args, "batch_id", None)
    for name in ("reasoning_effort", "max_output_tokens", "batch_max_requests", "payment_failure_only"):
        if hasattr(args, name):
            setattr(review_args, name, getattr(args, name))
    run_openai_batch(review_args)

    source_audit = json.loads((source_dir / "audit.json").read_text())
    final_audit = json.loads((final_dir / "audit.json").read_text())
    audit = {
        "workflow": "item204-discovery-then-openai-batch-v2",
        "provider": "openai_batch",
        "model": args.model,
        "interrupted": final_audit.get("interrupted", False),
        "batch_pending": final_audit.get("batch_pending", 0),
        "source_dir": str(source_dir.resolve()),
        "final_dir": str(final_dir.resolve()),
        "source_sha256": file_hash(source_dir / "filings.jsonl"),
        "final_sha256": file_hash(final_dir / "classifications.jsonl"),
        "source_counts": source_audit["counts"],
        "final_labels": final_audit["final_labels"],
        "unresolved_filings": final_audit["final_labels"].get("MANUAL_REVIEW", 0),
        "label_note": (
            "Payment-specific missed principal/interest disclosure evidence from either filing item; "
            "MANUAL_REVIEW remains unresolved; episodes are grouped downstream."
            if getattr(args, "payment_failure_only", False) else
            "QUALIFIED_DEFAULT is a conservative disclosure classification, not "
            "proof of contractual payment default. MANUAL_REVIEW remains unresolved."
        ),
    }
    (root / "workflow_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    if audit["interrupted"]:
        # Stop callers such as the composite model workflow as well.
        raise SystemExit(130)
    return final_dir


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--submissions", type=Path, required=True)
    result.add_argument("--items", nargs="+", choices=("1.03", "2.04"), default=["2.04"])
    result.add_argument("--payment-failure-only", action="store_true")
    result.add_argument("--batch-max-requests", type=int, default=50000)
    result.add_argument(
        "--output-dir", type=Path, default=Path("results/item_204_pipeline")
    )
    result.add_argument("--start", type=date.fromisoformat,
                        help="Inclusive filing-date lower bound (YYYY-MM-DD)")
    result.add_argument("--cutoff", type=date.fromisoformat,
                        help="Exclusive filing-date upper bound (YYYY-MM-DD)")
    result.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    result.add_argument("--interval", type=float, default=0.25)
    result.add_argument(
        "--filing-limit", type=int, default=0, help="Pilot filing limit; 0 means all"
    )
    result.add_argument(
        "--offline", action="store_true", help="Use only cached HTML; do not download missing filings"
    )
    result.add_argument("--batch-id", help="Recover an interrupted OpenAI Batch submission")
    add_options(result)
    result.add_argument("--model", default=DEFAULT_MODEL)
    result.add_argument(
        "--llm-limit", type=int, default=0, help="New LLM attempts; 0 means all"
    )
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--refresh", action="store_true")
    result.add_argument("--retry-fallbacks", action="store_true")
    return result


def main():
    command = parser()
    args = command.parse_args()
    if args.interval < 0.1:
        command.error("--interval must be at least 0.1 seconds")
    if args.filing_limit < 0 or args.llm_limit < 0:
        command.error("limits must be nonnegative")
    if args.start and args.cutoff and args.start >= args.cutoff:
        command.error("--start must precede --cutoff")
    if args.refresh and args.retry_fallbacks:
        command.error("Use either --refresh or --retry-fallbacks")
    try:
        run(args)
    except (APIReviewError, OSError, ValueError) as exc:
        command.exit(2, f"Workflow stopped: {exc}\n")
    except KeyboardInterrupt:
        print("\nJob stopped. Rerun the same command to resume using saved HTML and reviews.")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
