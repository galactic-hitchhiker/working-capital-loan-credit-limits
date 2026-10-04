"""Local Ollama reviewer for cached Item 2.04 filings; no API key required.

Run from the repository root with: python -m mcf.enrichment.item204.reviewers.ollama
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .common import (
    APIReviewError,
    PROMPT,
    SCHEMA,
    validate_review,
    make_parser,
    check_args,
)
from .common import run as run_reviews

DEFAULT_MODEL = "qwen3.5:9b"


def check_context(text, num_ctx):
    """Conservative input budget including schema, output and template overhead."""
    system = PROMPT + "\nReturn JSON matching this schema:\n" + json.dumps(SCHEMA)
    user = "UNTRUSTED SEC FILING TEXT:\n" + text
    if len((system + user).encode("utf-8")) + 4096 + 1024 > num_ctx:
        raise ValueError(
            "Filing exceeds conservative context budget; increase --num-ctx or review manually"
        )


def request_review(
    text, model, host="http://localhost:11434", num_ctx=32768, timeout=600, think=False
):
    """Use local /api/chat with a JSON schema and verify the returned quotes."""
    system = PROMPT + "\nReturn JSON matching this schema:\n" + json.dumps(SCHEMA)
    user = "UNTRUSTED SEC FILING TEXT:\n" + text
    check_context(text, num_ctx)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": SCHEMA,
        "stream": False,
        "think": think,
        "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": 4096},
        "keep_alive": "5m",
    }
    request = Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        try:
            message = str(
                json.loads(exc.read()).get("error", "Ollama request rejected")
            )[:1000]
        except (ValueError, AttributeError):
            message = "Ollama request rejected"
        raise APIReviewError(f"Ollama HTTP {exc.code}: {message}") from None
    except (URLError, TimeoutError) as exc:
        raise APIReviewError(
            f"Cannot complete local Ollama request: {exc}. Start Ollama and check the model; "
            "increase --timeout if generation is slow."
        ) from None
    if payload.get("error"):
        raise APIReviewError(str(payload["error"])[:1000])
    if not payload.get("done") or payload.get("done_reason") == "length":
        raise ValueError("Ollama response incomplete; no classification accepted")
    review = json.loads(payload["message"]["content"])
    return validate_review(review, text), {
        "returned_model": payload.get("model"),
        "usage": {
            "input_tokens": payload.get("prompt_eval_count"),
            "output_tokens": payload.get("eval_count"),
        },
        "total_duration_ns": payload.get("total_duration"),
    }


def run(args):
    parsed = urlparse(args.host)
    if parsed.scheme != "http" or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("--host must be a local HTTP Ollama server")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("--host must contain only a local server address and port")
    settings = dict(
        host=args.host,
        num_ctx=args.num_ctx,
        think=args.think,
        temperature=0,
        num_predict=4096,
    )
    return run_reviews(
        args,
        lambda text: request_review(
            text, args.model, args.host, args.num_ctx, args.timeout, args.think
        ),
        provider="ollama",
        cache_settings=settings,
        check_text=lambda text: check_context(text, args.num_ctx),
    )


if __name__ == "__main__":
    parser = make_parser(__doc__, "results/item_204_ollama_review", DEFAULT_MODEL)
    parser.set_defaults(max_chars=24000)
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=32768,
        help="Context tokens; larger values need more RAM",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Seconds allowed for each local generation",
    )
    parser.add_argument(
        "--think",
        action="store_true",
        help="Enable thinking (slower; may exhaust output budget)",
    )
    args = parser.parse_args()
    check_args(parser, args)
    if args.num_ctx < 8192 or args.timeout <= 0:
        parser.error("--num-ctx must be at least 8192 and --timeout positive")
    run(args)
