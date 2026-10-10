"""Run the SEC study as separate, reproducible stages or one pipeline.

Run from the repository root:
    .venv/bin/python -m mcf.workflows.pipeline all --output-dir results/new_run
    .venv/bin/python -m mcf.workflows.pipeline STEP --output-dir results/new_run

STEP is download, inventory, classify, panel, train, or all. The inventory step
screens SEC Company Facts and submissions, then imports Financial Statement and
Notes archives. Classification remains a separate OpenAI Batch workflow. The
panel step combines its decisions with SEC filings using the existing inventory
and panel builders; the model step uses the existing trainer.
"""

import argparse
import json
import os
from argparse import Namespace
from datetime import date
from pathlib import Path

from mcf.common import load_design, write_json
from mcf.data.empirical import (
    BANKRUPTCY_PAYMENT_TARGET,
    ITEM_103_TARGET,
    PAYMENT_DEFAULT_PROXY_TARGET,
    PAYMENT_FAILURE_TARGET,
    RECURRENT_TARGETS,
    inventory,
    load_item_204_results,
    panel,
)
from mcf.data.statement_facts import extract
from mcf.enrichment.item204.reviewers.common import APIReviewError
from mcf.enrichment.item204.reviewers.openai_batch import DEFAULT_MODEL, add_options
from mcf.enrichment.item204.workflow import run as review_item_204
from mcf.models.train import run as train_models
from scripts.download_sec_dataset import main as download_sec_dataset


def _design(args):
    config = load_design(args.config)
    if config["event_type"] not in {PAYMENT_DEFAULT_PROXY_TARGET, *RECURRENT_TARGETS}:
        raise ValueError("Pipeline requires a target that uses Item 2.04 reviews")
    return config


def _completed_reviews(path):
    """Validate classifications and stop before using an unfinished Batch job."""
    _, source = load_item_204_results(path)
    if source is None:
        raise ValueError("Item 2.04 classifications are missing; run classify first")
    audit = source.parent / "audit.json"
    if audit.is_file():
        state = json.loads(audit.read_text())
        counts = state.get("review_counts", {})
        if counts.get("batch_pending", 0) or (
            state.get("provider") == "openai_batch" and counts.get("deferred_limit", 0)
        ):
            raise ValueError(
                "Item 2.04 reviews are pending; rerun classify to collect them"
            )
    return path


def download(args):
    """Fetch the SEC source collections using the standalone downloader."""
    command = ["--output-dir", str(args.dataset)]
    if args.user_agent:
        command.extend(("--user-agent", args.user_agent))
    for option in ("start_year", "end_year"):
        value = getattr(args, option)
        if value is not None:
            command.extend(("--" + option.replace("_", "-"), str(value)))
    if args.download_only:
        command.append("--download-only")
    return download_sec_dataset(command)


def build_source_inventory(args):
    """Screen issuers before statement import, without assigning the final target."""
    config = _design(args)
    output = args.output_dir / "source_inventory"
    audit = output / "inventory_audit.json"
    source_marker = output / "pipeline_source.json"
    source = dict(
        dataset=str(args.dataset.resolve()),
        cutoff=config["observed_as_of"],
    )
    if audit.is_file():
        previous = json.loads(audit.read_text())
        if (
            previous.get("target") != ITEM_103_TARGET
            or previous.get("cutoff") != config["observed_as_of"]
            or previous.get("errors")
            or not source_marker.is_file()
            or json.loads(source_marker.read_text()) != source
        ):
            raise ValueError(
                "Source inventory differs from this study; use a new output directory"
            )
    else:
        report = inventory(
            args.dataset,
            output,
            date.fromisoformat(config["observed_as_of"]),
            target=ITEM_103_TARGET,
        )
        if report["errors"]:
            raise ValueError(
                "Resolve source inventory errors before importing statements"
            )
        write_json(source_marker, source)
    if args.statement_facts:
        if not args.statement_facts.is_dir():
            raise ValueError(
                f"Statement-fact directory does not exist: {args.statement_facts}"
            )
        return args.statement_facts
    archives = sorted(
        (args.dataset / "financial_statements" / "archives").glob("*notes*.zip")
    )
    if not archives:
        raise ValueError(
            "No Financial Statement and Notes ZIPs found; run the download step"
        )
    statement_root = args.dataset / "statement_facts"
    extract(
        archives,
        args.dataset,
        output / "issuer_inventory.csv",
        statement_root,
    )
    return statement_root / "companies"


def classify(args):
    """Submit/collect Item 2.04 reviews, or validate supplied classifications."""
    config = _design(args)
    if args.item_204_results:
        results = args.item_204_results
    else:
        payment_target = config["event_type"] in RECURRENT_TARGETS
        results = review_item_204(
            Namespace(
                submissions=args.dataset / "submissions",
                output_dir=args.output_dir
                / ("disclosures" if payment_target else "item204"),
                start=None,
                cutoff=date.fromisoformat(config["observed_as_of"]),
                user_agent=args.user_agent,
                interval=args.interval,
                filing_limit=0,
                offline=args.offline,
                batch_id=args.batch_id,
                reasoning_effort=args.reasoning_effort,
                max_output_tokens=args.max_output_tokens,
                model=args.model,
                llm_limit=args.llm_limit,
                dry_run=False,
                refresh=args.refresh,
                retry_fallbacks=args.retry_fallbacks,
                items=(
                    ["1.03", "2.04"]
                    if config["event_type"] == PAYMENT_FAILURE_TARGET
                    else ["2.04"]
                ),
                payment_failure_only=payment_target,
                batch_max_requests=args.batch_max_requests,
            )
        )
    return _completed_reviews(results)


def build_panel(args):
    """Build the final reviewed inventory and unchanged company-month panel."""
    config = _design(args)
    reviews = args.item_204_results or (
        args.output_dir
        / ("disclosures" if config["event_type"] in RECURRENT_TARGETS else "item204")
        / "final"
    )
    _completed_reviews(reviews)
    statements = args.statement_facts or args.dataset / "statement_facts" / "companies"
    if not statements.is_dir():
        raise ValueError("Statement facts are missing; run inventory first")
    inventory(
        args.dataset,
        args.output_dir / "inventory",
        date.fromisoformat(config["observed_as_of"]),
        reviews,
        target=config["event_type"],
        episode_gap_days=config.get("episode_gap_days", 90),
    )
    return panel(
        args.dataset,
        args.output_dir / "inventory",
        args.config,
        args.output_dir / "panel",
        statement_facts=statements,
    )


def train(args):
    """Fit models from the reviewed company-month panel."""
    _design(args)
    return train_models(
        args.config,
        args.output_dir / "panel" / "panel.csv",
        args.output_dir / "models",
    )


def run(args):
    """Execute only the requested stage or the full stage sequence."""
    if args.step == "download":
        return download(args)
    if args.step == "inventory":
        return build_source_inventory(args)
    if args.step == "classify":
        return classify(args)
    if args.step == "panel":
        return build_panel(args)
    if args.step == "train":
        return train(args)
    if not args.skip_download:
        download(args)
    build_source_inventory(args)
    classify(args)
    build_panel(args)
    return train(args)


def parser():
    command = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    command.add_argument(
        "step", choices=("download", "inventory", "classify", "panel", "train", "all")
    )
    command.add_argument("--dataset", type=Path, default=Path("../dataset"))
    command.add_argument("--output-dir", type=Path, required=True)
    command.add_argument(
        "--config",
        type=Path,
        default=Path("configs/study.bankruptcy_or_payment_failure.json"),
    )
    command.add_argument(
        "--statement-facts", type=Path, help="Reuse imported statement facts"
    )
    command.add_argument(
        "--disclosure-results",
        "--item-204-results",
        dest="item_204_results",
        type=Path,
        help="Reuse completed Item 2.04 classifications",
    )
    command.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT", ""))
    command.add_argument("--start-year", type=int)
    command.add_argument("--end-year", type=int)
    command.add_argument("--download-only", action="store_true")
    command.add_argument("--skip-download", action="store_true")
    command.add_argument("--interval", type=float, default=0.25)
    command.add_argument("--offline", action="store_true")
    command.add_argument("--batch-id")
    command.add_argument("--batch-max-requests", type=int, default=200)
    add_options(command)
    command.add_argument("--model", default=DEFAULT_MODEL)
    command.add_argument("--llm-limit", type=int, default=0)
    command.add_argument("--refresh", action="store_true")
    command.add_argument("--retry-fallbacks", action="store_true")
    return command


def main():
    command = parser()
    args = command.parse_args()
    if args.download_only and args.step != "download":
        command.error("--download-only applies only to the download step")
    if args.skip_download and args.step != "all":
        command.error("--skip-download applies only to all")
    if args.interval < 0.1 or args.llm_limit < 0 or args.batch_max_requests < 1:
        command.error(
            "Require interval >= 0.1, llm-limit >= 0 and batch-max-requests >= 1"
        )
    if args.refresh and args.retry_fallbacks:
        command.error("Use either --refresh or --retry-fallbacks")
    try:
        result = run(args)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        elif isinstance(result, Path):
            print(result)
    except (APIReviewError, OSError, ValueError, KeyError) as exc:
        command.exit(2, f"Pipeline stopped: {exc}\n")


if __name__ == "__main__":
    main()
