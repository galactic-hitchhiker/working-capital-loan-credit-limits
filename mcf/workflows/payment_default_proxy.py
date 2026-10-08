"""Build and train recurrent bankruptcy/payment-failure disclosure models.

The default target automatically includes Item 1.03 bankruptcy/receivership
and includes Item 2.04 only with explicit payment-failure evidence within 60 days.

Run from the repository root:
    .venv/bin/python -m mcf.workflows.payment_default_proxy [parameters]

Parameters:
    --dataset PATH: Local SEC dataset with submissions/ and companyfacts/ (default: ../dataset).
    --config PATH: Payment-disclosure study-design JSON; also supplies the disclosure cutoff
        (default: configs/study.bankruptcy_or_payment_failure.json).
    --output-dir PATH: Required fresh root for inventory, panel and model outputs.
    --disclosure-results PATH: Completed payment-specific or earlier OpenAI 2.04 reviews;
        skips enrichment; 1.03 qualifies automatically in the default composite design.
    --item-204-results PATH: Backward-compatible alias for --disclosure-results.
    --batch-max-requests N: Maximum requests per sequential Batch job (default: 200).
    --user-agent TEXT: SEC identification with contact email (default: SEC_USER_AGENT).
    --interval SECONDS: SEC request spacing, at least 0.1 (default: 0.25).
    --offline: Use cached filing HTML only; OpenAI calls still occur (default: off).
    --llm-limit N: Limit new filing review attempts per run (default: 0, all).
    --smoke: Use a smaller model-training grid for a software check (default: off).
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
Training waits until enrichment has no pending or limit-deferred reviews.
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
    PAYMENT_FAILURE_TARGET,
    BANKRUPTCY_PAYMENT_TARGET,
    RECURRENT_TARGETS,
    inventory,
    panel,
)
from mcf.enrichment.item204.workflow import run as run_item_204
from mcf.enrichment.item204.reviewers.openai_batch import DEFAULT_MODEL, add_options
from mcf.enrichment.item204.reviewers.common import APIReviewError
from mcf.models.train import run as train


def run(args):
    """Create reviewed disclosures, episode inventory, panel, and fitted models."""
    config = load_design(args.config)
    target = config["event_type"]
    payment_target = target in RECURRENT_TARGETS
    if target not in {PAYMENT_DEFAULT_PROXY_TARGET, *RECURRENT_TARGETS}:
        raise ValueError(
            "Config must define a supported payment-disclosure target"
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
                output_dir=root / ("disclosures" if payment_target else "item204"),
                start=None,
                cutoff=cutoff,
                user_agent=args.user_agent,
                interval=args.interval,
                filing_limit=0,
                offline=args.offline,
                batch_id=getattr(args, "batch_id", None),
                reasoning_effort=getattr(args, "reasoning_effort", "medium"),
                max_output_tokens=getattr(args, "max_output_tokens", 3000),
                model=args.model,
                llm_limit=args.llm_limit,
                dry_run=False,
                refresh=args.refresh,
                retry_fallbacks=args.retry_fallbacks,
                items=["1.03", "2.04"] if target == PAYMENT_FAILURE_TARGET else ["2.04"],
                payment_failure_only=payment_target,
                batch_max_requests=getattr(args, "batch_max_requests", 200),
            )
        )

    review_audit = Path(item_204_results) / "audit.json"
    if review_audit.exists():
        review_state = json.loads(review_audit.read_text())
        review_counts = review_state.get("review_counts", {})
        if review_counts.get("batch_pending", 0) or (
            review_state.get("provider") == "openai_batch" and review_counts.get("deferred_limit", 0)
        ):
            raise ValueError(
                "Disclosure reviews are pending or limited. Rerun enrichment to collect "
                "all results before building inventory, panel, and models."
            )

    inventory_report = inventory(
        args.dataset,
        root / "inventory",
        cutoff,
        item_204_results,
        target=target,
        episode_gap_days=config.get("episode_gap_days", 90),
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
        "workflow": "bankruptcy-or-payment-failure-v1" if target == BANKRUPTCY_PAYMENT_TARGET else "disclosed-payment-failure-v1" if payment_target else "payment-default-disclosure-proxy-v1",
        "target": target,
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
        "exploratory_low_event": config.get("exploratory_low_event", False),
        "validation_status": config.get("validation_status"),
        "limitation": (
            "All 1.03 bankruptcy/receivership or explicitly reviewed 2.04 payment-failure episodes; "
            "not verified contractual nonpayment or cure. "
            if target == BANKRUPTCY_PAYMENT_TARGET else
            "Recurrent disclosed payment-failure episodes; filing dates and an operational quiet gap, "
            "not complete actual-default coverage or verified cure."
            if payment_target else
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
        default=Path("configs/study.bankruptcy_or_payment_failure.json"),
    )
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument(
        "--disclosure-results", "--item-204-results", dest="item_204_results",
        type=Path,
        help="Reuse completed payment-specific or earlier OpenAI 2.04 reviews and skip enrichment",
    )
    result.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    result.add_argument("--interval", type=float, default=0.25)
    result.add_argument("--offline", action="store_true")
    result.add_argument("--batch-id", help="Recover an interrupted OpenAI Batch submission")
    result.add_argument("--batch-max-requests", type=int, default=200)
    add_options(result)
    result.add_argument("--model", default=DEFAULT_MODEL)
    result.add_argument("--llm-limit", type=int, default=0)
    result.add_argument("--refresh", action="store_true")
    result.add_argument("--retry-fallbacks", action="store_true")
    result.add_argument("--smoke", action="store_true")
    return result


def main():
    command = parser()
    args = command.parse_args()
    if args.interval < 0.1 or args.llm_limit < 0:
        command.error("--interval must be at least 0.1 and --llm-limit nonnegative")
    if args.refresh and args.retry_fallbacks:
        command.error("Use either --refresh or --retry-fallbacks")
    try:
        run(args)
    except (APIReviewError, OSError, ValueError, KeyError) as exc:
        command.exit(2, f"Workflow stopped: {exc}\n")


if __name__ == "__main__":
    main()
