"""Run Item 2.04 discovery, rule classification, and LLM fallback in one command."""

import argparse
import json
import os
from argparse import Namespace
from datetime import date
from pathlib import Path

from mcf.common import file_hash
from mcf.enrichment.item204.classify import run as run_rules
from mcf.enrichment.item204.reviewers.ollama import (
    DEFAULT_MODEL,
    run as run_ollama,
)
from mcf.enrichment.item204.reviewers.openai import run as run_openai


def run(args):
    """Classify every selected filing with rules, then review only unresolved cases."""
    root = args.output_dir
    rules_dir = root / "rules"
    final_dir = root / "final"
    root.mkdir(parents=True, exist_ok=True)

    run_rules(
        Namespace(
            submissions=args.submissions,
            output_dir=rules_dir,
            start=args.start,
            cutoff=args.cutoff,
            user_agent=args.user_agent,
            interval=args.interval,
            limit=args.filing_limit or None,
            offline=args.offline,
            discover_only=False,
        )
    )

    review_args = Namespace(
        input=rules_dir / "classifications.jsonl",
        html_dir=rules_dir / "html",
        output_dir=final_dir,
        model=args.model,
        limit=args.llm_limit,
        max_chars=args.max_chars,
        dry_run=args.dry_run,
        refresh=args.refresh,
        retry_fallbacks=args.retry_fallbacks,
    )
    if args.provider == "ollama":
        review_args.host = args.host
        review_args.num_ctx = args.num_ctx
        review_args.timeout = args.timeout
        review_args.think = args.think
        run_ollama(review_args)
    else:
        run_openai(review_args)

    rule_audit = json.loads((rules_dir / "audit.json").read_text())
    final_audit = json.loads((final_dir / "audit.json").read_text())
    audit = {
        "workflow": "item204-rules-then-llm-v1",
        "provider": args.provider,
        "model": args.model,
        "rules_dir": str(rules_dir.resolve()),
        "final_dir": str(final_dir.resolve()),
        "rules_sha256": file_hash(rules_dir / "classifications.jsonl"),
        "final_sha256": file_hash(final_dir / "classifications.jsonl"),
        "rule_counts": rule_audit["counts"],
        "final_labels": final_audit["final_labels"],
        "unresolved_filings": final_audit["final_labels"].get("MANUAL_REVIEW", 0),
        "label_note": (
            "QUALIFIED_DEFAULT is a conservative disclosure classification, not "
            "proof of contractual payment default. MANUAL_REVIEW remains unresolved."
        ),
    }
    (root / "workflow_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))
    return final_dir


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--submissions", type=Path, required=True)
    result.add_argument(
        "--output-dir", type=Path, default=Path("results/item_204_pipeline")
    )
    result.add_argument("--start", type=date.fromisoformat)
    result.add_argument("--cutoff", type=date.fromisoformat)
    result.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    result.add_argument("--interval", type=float, default=0.25)
    result.add_argument(
        "--filing-limit", type=int, default=0, help="Pilot filing limit; 0 means all"
    )
    result.add_argument(
        "--offline", action="store_true", help="Use only HTML already in rules/html"
    )
    result.add_argument("--provider", choices=("ollama", "openai"), default="ollama")
    result.add_argument("--model", default=DEFAULT_MODEL)
    result.add_argument(
        "--llm-limit", type=int, default=0, help="New LLM attempts; 0 means all"
    )
    result.add_argument("--max-chars", type=int, default=24000)
    result.add_argument("--dry-run", action="store_true")
    result.add_argument("--refresh", action="store_true")
    result.add_argument("--retry-fallbacks", action="store_true")
    result.add_argument("--host", default="http://localhost:11434")
    result.add_argument("--num-ctx", type=int, default=32768)
    result.add_argument("--timeout", type=int, default=600)
    result.add_argument("--think", action="store_true")
    return result


def main():
    command = parser()
    args = command.parse_args()
    if args.interval < 0.1:
        command.error("--interval must be at least 0.1 seconds")
    if args.filing_limit < 0 or args.llm_limit < 0:
        command.error("limits must be nonnegative")
    if args.max_chars < 100:
        command.error("--max-chars must be at least 100")
    if args.start and args.cutoff and args.start >= args.cutoff:
        command.error("--start must precede --cutoff")
    if args.refresh and args.retry_fallbacks:
        command.error("Use either --refresh or --retry-fallbacks")
    if args.provider == "openai" and args.model == DEFAULT_MODEL:
        command.error("--provider openai requires an explicit OpenAI --model")
    if args.num_ctx < 8192 or args.timeout <= 0:
        command.error("--num-ctx must be at least 8192 and --timeout positive")
    run(args)


if __name__ == "__main__":
    main()
