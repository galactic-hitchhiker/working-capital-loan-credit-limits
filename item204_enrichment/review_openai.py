"""OpenAI Responses reviewer for cached SEC filings."""
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from .review_common import APIReviewError, PROMPT, SCHEMA, validate_review, make_parser, check_args
from .review_common import run as run_reviews

def request_review(text, model, api_key):
    """One Responses API request; no tools, external retrieval, or SEC access."""
    body = {
        "model": model,
        "store": False,
        "instructions": PROMPT,
        "input": "UNTRUSTED SEC FILING TEXT:\n" + text,
        "max_output_tokens": 4000,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "item204_review",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=180) as response:
            payload = json.load(response)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read()).get("error", {})
            code = error.get("code") or error.get("type") or "unknown"
            message = str(error.get("message", "API request rejected"))
        except (ValueError, AttributeError):
            code, message = "unknown", "API request rejected"
        # Some authentication errors echo credentials; never persist the key.
        message = message.replace(api_key, "[REDACTED]")[:1000]
        raise APIReviewError(f"HTTP {exc.code} [{code}]: {message}") from None
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
    return validate_review(result, text), {
        "response_id": payload.get("id"),
        "returned_model": payload.get("model"),
        "usage": payload.get("usage"),
    }


def run(args):
    key = os.environ.get("OPENAI_API_KEY", "")
    if not args.dry_run and not key:
        raise ValueError("Set OPENAI_API_KEY (not required for --dry-run)")
    return run_reviews(args, lambda text: request_review(text, args.model, key))


if __name__ == "__main__":
    parser = make_parser(__doc__, "results/item_204_llm_review")
    args = parser.parse_args()
    check_args(parser, args)
    run(args)
