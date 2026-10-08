"""Submit and resume discounted OpenAI Batch reviews of cached SEC filings.

Run from the repository root:
    .venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch [parameters]

Example:
    .venv/bin/python -m mcf.enrichment.item204.reviewers.openai_batch \
    --input results/sec/item204/filings.jsonl \
    --html-dir results/sec/item204/html \
    --output-dir results/item_204_openai_batch_review/


Parameters:
    --retry-manual-review: Retry only saved MANUAL_REVIEW decisions when model or
        settings change. Use the original input/output paths; repeat the same command
        to collect results. Resolved decisions and completed retries are reused.
    --batch-max-requests N: Requests per job (default: 50000). Use 200 for smaller
        sequential jobs when the model's queued input-token allowance is limited.
    --input PATH: Filing-inventory JSONL (default: results/item_204_pipeline/source/filings.jsonl;
        falls back to rules/classifications.jsonl under that root if only the legacy file exists).
    --html-dir PATH: Cached filing HTML (default: results/item_204_pipeline/source/html;
        falls back to rules/html under that root if only the legacy directory exists).
    --output-dir PATH: Jobs, reviews and exports (default: results/item_204_openai_batch_review).
    --start YYYY-MM-DD: Inclusive filing-date lower bound (default: no lower bound).
    --cutoff YYYY-MM-DD: Exclusive filing-date upper bound (default: no upper bound).
    --limit N: Limit new filing review attempts per run (default: 0, all).
    --dry-run: Inspect local sources/write local outputs without API calls (default: off).
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
"""

import hashlib
import json
import os
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .common import (
    APIReviewError,
    BatchRequestError,
    ReviewDeferred,
    PROMPT,
    SCHEMA,
    validate_review,
    check_args,
    make_parser,
    run as run_reviews,
)

CONTEXT_VERSION = "item204-openai-v1-source-bounded"
DEFAULT_MAX_OUTPUT_TOKENS = 3000
OPENAI_PROMPT = (
    PROMPT
    + """

Output contract for this automated classification task:
Return one JSON object matching the supplied schema, with no prose outside it.
If a filing incorporates another item by reference, follow that reference only
when its substantive text is actually present in the supplied filing. An item
heading or a list of exhibits is not evidence. If supplied text is an extracted
narrative, do not assume omitted sections resolve its references. Unavailable
external agreements or exhibits cannot supply evidence.
When uncertainty remains, return MANUAL_REVIEW, event_type UNCERTAIN, certainty
UNCERTAIN, and state the specific missing fact. For resolved answers, certainty
must be HIGH. HIGH describes evidence sufficiency, not a calibrated probability.
Use a reason of at most 80 words. Include 1-4 short, exact, contiguous evidence
quotes (normally at most 200 words total); quote both the trigger and consequence
when classifying acceleration. Do not use ellipses, paraphrases, illustrations,
or this instruction text as evidence. MANUAL_REVIEW may use an empty quote list.
Do not infer a payment failure solely from bankruptcy or technical breach.
Do not ask questions, browse, call tools, or supply hidden reasoning transcripts.
"""
)


def review_body(
    text, model, reasoning_effort="medium", max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS
):
    """Structured Responses request for one Batch review."""
    body = {
        "model": model,
        "store": False,
        "instructions": OPENAI_PROMPT,
        "input": "UNTRUSTED SEC FILING TEXT:\n" + text,
        "max_output_tokens": max_output_tokens,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "item204_review",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }
    # Nonreasoning models (e.g. GPT-4.1/4o) reject reasoning options.
    if model.startswith(("gpt-5", "gpt-6", "o3", "o4")):
        body["reasoning"] = {"effort": reasoning_effort}
    return body


def parse_review_response(payload, text):
    """Validate Batch output against its source filing."""
    if payload.get("status") != "completed":
        raise ValueError("API response did not complete")
    parts = [
        part for item in payload.get("output", []) for part in item.get("content", [])
    ]
    if any(part.get("type") == "refusal" for part in parts):
        raise ValueError("Model refused review")
    result = json.loads(
        "".join(part["text"] for part in parts if part.get("type") == "output_text")
    )
    result = validate_review(result, text)
    if result["classification"] == "MANUAL_REVIEW" and (
        result["event_type"] != "UNCERTAIN" or result["certainty"] != "UNCERTAIN"
    ):
        raise ValueError("MANUAL_REVIEW requires UNCERTAIN event type and certainty")
    return result, {
        "response_id": payload.get("id"),
        "returned_model": payload.get("model"),
        "usage": payload.get("usage"),
    }


DEFAULT_MODEL = "gpt-6-luna"

BASE_URL = "https://api.openai.com/v1"
ENDPOINT = "/v1/responses"
TERMINAL = {"completed", "failed", "expired", "cancelled"}
MAX_REQUESTS = 50000
MAX_BYTES = 200_000_000


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def api_request(path, key, body=None, content_type="application/json", raw=False):
    """Use the existing stdlib HTTP approach; never save credentials."""
    if not key:
        raise APIReviewError("Set OPENAI_API_KEY to submit or check Batch jobs")
    request = Request(
        BASE_URL + path,
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": content_type},
    )
    try:
        with urlopen(request, timeout=180) as response:
            return response.read().decode("utf-8") if raw else json.load(response)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
            message = str(error.get("message", "API request rejected"))
            code = error.get("code") or error.get("type") or "unknown"
        except (ValueError, AttributeError):
            message, code = "API request rejected", "unknown"
        failure = APIReviewError(
            f"HTTP {exc.code} [{code}]: {message.replace(key, '[REDACTED]')[:1000]}"
        )
        failure.status_code = exc.code
        raise failure from None


def upload(path, key):
    boundary = "batch-" + uuid.uuid4().hex
    data = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nbatch\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="input.jsonl"\r\n'
            "Content-Type: application/jsonl\r\n\r\n"
        ).encode()
        + path.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return api_request(
        "/files", key, data, "multipart/form-data; boundary=" + boundary
    )["id"]


def request_line(
    text, model, reasoning_effort="medium", max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS
):
    body = review_body(text, model, reasoning_effort, max_output_tokens)
    custom_id = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return {"custom_id": custom_id, "method": "POST", "url": ENDPOINT, "body": body}


def load_jobs(directory):
    return [
        (path, json.loads(path.read_text()))
        for path in sorted(directory.glob("*/job.json"))
    ]


def submit(path, job, key):
    if job["status"] == "prepared":
        job["input_file_id"] = upload(path.parent / "input.jsonl", key)
        job["status"] = "uploaded"
        atomic_json(path, job)
    if job["status"] == "uploaded":
        # A network timeout may happen AFTER creation. Save this marker first and
        # require recovery of that job ID instead of silently creating a duplicate.
        job["status"] = "submitting"
        atomic_json(path, job)
        try:
            batch = api_request(
                "/batches",
                key,
                json.dumps(
                    {
                        "input_file_id": job["input_file_id"],
                        "endpoint": ENDPOINT,
                        "completion_window": "24h",
                        "metadata": {"local_job": path.parent.name},
                    }
                ).encode(),
            )
        except APIReviewError as exc:
            if getattr(exc, "status_code", 0) < 500:
                # An explicit client rejection did not create a paid job.
                job["status"] = "uploaded"
                atomic_json(path, job)
            raise
        job.update(
            batch_id=batch["id"],
            status=batch["status"],
            output_file_id=batch.get("output_file_id"),
            error_file_id=batch.get("error_file_id"),
            errors=batch.get("errors"),
        )
        atomic_json(path, job)
        print(
            f"Submitted {batch['id']}: {len(job['custom_ids'])} requests. Rerun to collect results.",
            flush=True,
        )


def refresh_job(path, job, key):
    if job["status"] not in TERMINAL:
        batch = api_request("/batches/" + job["batch_id"], key)
        job.update(
            status=batch["status"],
            output_file_id=batch.get("output_file_id"),
            error_file_id=batch.get("error_file_id"),
            errors=batch.get("errors"),
        )
        atomic_json(path, job)
        print(f"{job['batch_id']}: {job['status']}", flush=True)
    if job["status"] in TERMINAL:
        for kind in ("output", "error"):
            file_id = job.get(kind + "_file_id")
            destination = path.parent / (kind + ".jsonl")
            if file_id and not destination.exists():
                data = api_request("/files/" + file_id + "/content", key, raw=True)
                temporary = destination.with_suffix(".tmp")
                temporary.write_text(data)
                temporary.replace(destination)


def prepare_jobs(directory, requests, max_requests=MAX_REQUESTS):
    """Split at both published limits; save input and manifest before submission."""
    chunk, size, prepared = [], 0, []

    def save():
        folder = directory / uuid.uuid4().hex
        folder.mkdir()
        (folder / "input.jsonl").write_bytes(b"".join(chunk))
        job = {
            "status": "prepared",
            "custom_ids": [json.loads(line)["custom_id"] for line in chunk],
            "consumed": [],
        }
        path = folder / "job.json"
        atomic_json(path, job)
        prepared.append((path, job))

    for request in requests.values():
        line = (json.dumps(request) + "\n").encode()
        if len(line) > MAX_BYTES:
            raise ValueError("One Batch request exceeds the 200 MB input limit")
        if chunk and (len(chunk) >= min(max_requests, MAX_REQUESTS) or size + len(line) > MAX_BYTES):
            save()
            chunk, size = [], 0
        chunk.append(line)
        size += len(line)
    if chunk:
        save()
    return prepared


def run(args):
    """One nonblocking submit/collect pass; reruns never resubmit pending inputs."""
    settings = {
        "context_version": CONTEXT_VERSION,
        "reasoning_effort": getattr(args, "reasoning_effort", "medium"),
        "max_output_tokens": getattr(
            args, "max_output_tokens", DEFAULT_MAX_OUTPUT_TOKENS
        ),
    }
    if settings["max_output_tokens"] < 256:
        raise ValueError("--max-output-tokens must be at least 256")

    def make_request(text):
        return request_line(
            text,
            args.model,
            settings["reasoning_effort"],
            settings["max_output_tokens"],
        )

    if args.dry_run:
        return run_reviews(
            args, lambda text: None, provider="openai_batch", cache_settings=settings
        )
    key = os.environ.get("OPENAI_API_KEY", "")
    directory = args.output_dir.resolve() / "batches"
    # Validate the source/output relationship before creating jobs or making calls.
    if args.output_dir.resolve() == args.input.resolve().parent:
        raise ValueError("Use a separate output directory to preserve original results")
    directory.mkdir(parents=True, exist_ok=True)
    jobs = load_jobs(directory)
    max_requests = getattr(args, "batch_max_requests", MAX_REQUESTS)
    if not 1 <= max_requests <= MAX_REQUESTS:
        raise ValueError("--batch-max-requests must be between 1 and 50000")
    recovery_id = getattr(args, "batch_id", None)
    ambiguous = [(path, job) for path, job in jobs if job["status"] == "submitting"]
    if recovery_id:
        if len(ambiguous) != 1:
            raise ValueError(
                "--batch-id requires exactly one interrupted submission in this output directory"
            )
        path, job = ambiguous[0]
        batch = api_request("/batches/" + recovery_id, key)
        if (
            batch["input_file_id"] != job["input_file_id"]
            or batch["endpoint"] != ENDPOINT
        ):
            raise ValueError(
                "Recovery batch does not match the saved input file/endpoint"
            )
        job.update(
            batch_id=batch["id"],
            status=batch["status"],
            output_file_id=batch.get("output_file_id"),
            error_file_id=batch.get("error_file_id"),
            errors=batch.get("errors"),
        )
        atomic_json(path, job)
    elif ambiguous:
        raise ValueError(
            "A previous submission was interrupted; creation may have succeeded. "
            "Find its local_job metadata in the OpenAI dashboard and rerun with --batch-id ID. "
            "No duplicate batch was submitted."
        )
    # Split only jobs that have never been accepted or were rejected for queue
    # capacity. Never replace an active job or discard completed responses.
    capacity_deferred = set()
    for path, job in list(jobs):
        if job["status"] not in {"prepared", "uploaded"} and job["status"] not in TERMINAL:
            refresh_job(path, job, key)
        queue_rejected = job["status"] == "failed" and "enqueued token limit" in json.dumps(job.get("errors")).lower()
        outstanding = set(job["custom_ids"]) - set(job.get("consumed", []))
        if outstanding and (job["status"] in {"prepared", "uploaded"} or queue_rejected) and len(outstanding) > max_requests:
            requests = {
                line["custom_id"]: line
                for line in map(json.loads, (path.parent / "input.jsonl").read_text().splitlines())
                if line["custom_id"] in outstanding
            }
            replacements = prepare_jobs(directory, requests, max_requests)
            job["consumed"] = sorted(set(job.get("consumed", [])) | outstanding)
            job["replaced_by"] = [p.parent.name for p, _ in replacements]
            atomic_json(path, job)
        elif outstanding and queue_rejected:
            job["status"] = "uploaded"
            atomic_json(path, job)
            capacity_deferred.add(path)
            print("Batch queue capacity is exhausted. Wait for other jobs or lower --batch-max-requests.", flush=True)
    jobs = load_jobs(directory)
    active = bool(capacity_deferred) or any(
        job["status"] not in TERMINAL | {"prepared", "uploaded"}
        and set(job["custom_ids"]) - set(job.get("consumed", []))
        for _, job in jobs
    )
    pending, results, owners = set(), {}, {}
    for path, job in jobs:
        outstanding = set(job["custom_ids"]) - set(job.get("consumed", []))
        if not outstanding:
            continue
        if job["status"] in {"prepared", "uploaded"}:
            if active or path in capacity_deferred:
                pending.update(outstanding)
                continue
            submit(path, job, key)
            refresh_job(path, job, key)
        if job["status"] not in TERMINAL:
            active = True
            pending.update(outstanding)
            continue
        lines = {}
        for kind in ("output", "error"):
            saved = path.parent / (kind + ".jsonl")
            if saved.exists():
                for line in saved.read_text().splitlines():
                    if line.strip():
                        entry = json.loads(line)
                        custom_id = entry["custom_id"]
                        if custom_id not in job["custom_ids"] or custom_id in lines:
                            raise ValueError(
                                "Unexpected or duplicate Batch result custom_id"
                            )
                        lines[custom_id] = entry
        for custom_id in outstanding:
            results[custom_id] = lines.get(
                custom_id,
                {
                    "error": {
                        "message": f"Batch {job['status']}: no result for this request",
                        "details": job.get("errors"),
                    }
                },
            )
            owners[custom_id] = (path, job)
    queued, consumed = {}, set()

    def review(text):
        line = make_request(text)
        custom_id = line["custom_id"]
        if custom_id in results:
            consumed.add(custom_id)
            entry = results[custom_id]
            response = entry.get("response") or {}
            if entry.get("error") or response.get("status_code") != 200:
                detail = json.dumps(
                    entry.get("error") or response.get("body") or "Missing response"
                )
                if key:
                    detail = detail.replace(key, "[REDACTED]")
                raise BatchRequestError(detail[:1000])
            value, metadata = parse_review_response(response["body"], text)
            metadata.update(
                batch_id=owners[custom_id][1]["batch_id"], custom_id=custom_id
            )
            return value, metadata
        if custom_id not in pending:
            queued[custom_id] = line
        raise ReviewDeferred()

    audit = run_reviews(
        args, review, provider="openai_batch", cache_settings=settings, print_audit=False
    )
    # Decisions are saved atomically by the shared reviewer before marking consumed.
    if not audit["interrupted"]:
        for path, job in jobs:
            job["consumed"] = sorted(
                set(job.get("consumed", [])) | (consumed & set(job["custom_ids"]))
            )
            atomic_json(path, job)
        for path, job in prepare_jobs(directory, queued, max_requests):
            if not active:
                submit(path, job, key)
                active = job["status"] not in TERMINAL
    audit["batch_jobs"] = [
        {
            "batch_id": job.get("batch_id"),
            "status": job["status"],
            "requests": len(job["custom_ids"]),
            "consumed": len(job.get("consumed", [])),
        }
        for _, job in load_jobs(directory)
    ]
    audit["batch_pending"] = audit["review_counts"].get("batch_pending", 0)
    # These count local filing callbacks, not HTTP calls or paid requests.
    audit["review_attempts"] = audit.pop("api_calls")
    atomic_json(args.output_dir.resolve() / "audit.json", audit)
    print(json.dumps(audit, indent=2))
    if audit["batch_pending"]:
        print(
            f"Waiting for Batch results for {audit['batch_pending']} filings. "
            "MANUAL_REVIEW is a placeholder for pending filings. "
            "Rerun the same command with the same output directory to collect results.",
            flush=True,
        )
    return audit


def parser():
    command = make_parser(
        __doc__, "results/item_204_openai_batch_review", DEFAULT_MODEL
    )
    command.add_argument(
        "--batch-id", help="Recover a job ID after an interrupted submission"
    )
    command.add_argument(
        "--retry-manual-review", action="store_true",
        help="Retry saved MANUAL_REVIEW decisions once with changed model/settings; preserve resolved decisions",
    )
    command.add_argument(
        "--batch-max-requests", type=int, default=MAX_REQUESTS,
        help="Maximum requests per job; jobs are submitted sequentially (try 200 for small token queues)",
    )
    add_options(command)
    return command


def main():
    command = parser()
    args = command.parse_args()
    check_args(command, args)
    try:
        audit = run(args)
    except (APIReviewError, OSError, ValueError, KeyError) as exc:
        command.exit(2, f"Batch review stopped: {exc}\n")
    if audit["interrupted"]:
        raise SystemExit(130)


def add_options(parser):
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="Total output cap including reasoning tokens (default: 3000)",
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="medium",
        help="Model reasoning effort for each review (default: medium)",
    )


if __name__ == "__main__":
    main()
