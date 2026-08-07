"""extract_claims.py -- K2, COWORK_BRIEF_knowledge_curator.md.

Per mapped MCF conversation, newest-first by real modified time, extracts
atomic claims ``{claim_text, quoted_source}`` via a local LM Studio model,
where ``quoted_source`` must be a literal substring of the conversation's own
transcript text. Anything else is rejected and counted, never silently
dropped or retried. A conversation yielding zero claims is recorded as
scanned-with-zero, never omitted. Caches per conversation on its source
files' identity (path + mtime), so an unchanged conversation is never
re-extracted.

Stdlib transport only (``urllib.request``) against LM Studio's
OpenAI-compatible ``/v1/chat/completions`` endpoint -- no ``requests``, no
``openai`` client, per the brief's working rules.

Usage:
    python3 extract_claims.py --index data/knowledge_curator/knowledge_index.json \\
        --map config/mcf_conversation_map.tsv [--endpoint URL] [--model ID] \\
        [--cache PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_PIPE = Path(__file__).resolve().parent
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))
import local_transcripts as lt  # noqa: E402
import bootstrap_conversation_map as k0  # noqa: E402
import knowledge_index as k1  # noqa: E402

DEFAULT_ENDPOINT = "http://localhost:1234/v1/chat/completions"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT = 900.0
DEFAULT_CACHE = Path("data/knowledge_curator/claims_cache.json")
DEFAULT_OUT = Path("data/knowledge_curator/claims.json")

SYSTEM_PROMPT = (
    "You extract atomic factual or decision claims from a work conversation "
    "transcript. Return ONLY a JSON array, no prose, no markdown fence. Each "
    "element is an object with exactly two string fields: `claim_text` (a "
    "short, self-contained statement of what was established, decided, or "
    "learned) and `quoted_source` (a LITERAL, VERBATIM substring copied "
    "character-for-character from the transcript below that supports the "
    "claim -- not a paraphrase, not a summary). If the transcript contains "
    "no claims worth recording, return an empty array []."
)

# Grammar-constrained output (llama.cpp / LM Studio's OpenAI-compatible
# `response_format: json_schema` -- structurally cannot return prose, unlike
# a prompt instruction the model is free to ignore. Real-run evidence for
# why this exists: qwen3.5 on a 65k-token transcript ignored the "return
# ONLY a JSON array" instruction outright and replied with a normal chatty
# assistant message -- 14 minutes of prompt processing for zero usable
# claims, correctly caught as parse_failed rather than silently accepted,
# but wasted all the same. A schema-constrained grammar makes that failure
# mode structurally impossible rather than something the prompt merely asks
# the model not to do.
CLAIMS_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "claim_text": {"type": "string"},
            "quoted_source": {"type": "string"},
        },
        "required": ["claim_text", "quoted_source"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# LM Studio transport -- stdlib only.
# ---------------------------------------------------------------------------

def call_lmstudio(transcript_text: str, *, endpoint: str, model: str,
                   temperature: float, timeout: float = DEFAULT_TIMEOUT,
                   json_mode: bool = True) -> str:
    """POST to an OpenAI-compatible chat/completions endpoint; returns the
    assistant message content as a raw string. Raises ``OSError`` /
    ``urllib.error.URLError`` on any transport failure -- callers must NOT
    swallow this (brief: 'loud failure, no partial report').

    ``json_mode`` requests grammar-constrained output matching
    ``CLAIMS_JSON_SCHEMA`` via ``response_format``. Not every model runtime
    honours it (some MLX/GGUF backends silently ignore an unsupported
    field rather than erroring) -- when it's respected it forecloses the
    conversational-reply failure mode entirely; when it isn't, behaviour is
    identical to before. Set ``json_mode=False`` if a given endpoint errors
    on the field outright."""
    body: dict = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
    }
    if json_mode:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "claims", "strict": True, "schema": CLAIMS_JSON_SCHEMA},
        }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        response_body = json.loads(resp.read().decode("utf-8"))
    return response_body["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Response parsing -- tolerant of a markdown fence or leading/trailing prose,
# but never tolerant of a non-literal quote (that is K2's whole contract).
# ---------------------------------------------------------------------------

def _extract_json_array(text: str) -> list | None:
    start = text.find("[")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                candidate = text[start:i + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, list) else None
    return None


@dataclass
class Claim:
    claim_text: str
    quoted_source: str


@dataclass
class ExtractionResult:
    conversation_id: str
    real_time: str | None
    claims: list = field(default_factory=list)          # list[Claim]
    rejected: list = field(default_factory=list)         # list[dict]
    parse_failed: bool = False
    scanned_with_zero: bool = False


def full_transcript_text(conv) -> str:
    """Every message, every file, in file/sequence order -- the substring
    universe `quoted_source` is checked against. Includes both roles: a
    claim's supporting quote can come from either side of the conversation."""
    parts = []
    for sess in conv.sessions:
        for _, role, text, _, _ in sess.messages:
            if text:
                parts.append(text)
    return "\n".join(parts)


def extract_for_conversation(conv, *, caller, endpoint: str, model: str,
                              temperature: float) -> ExtractionResult:
    text = full_transcript_text(conv)
    result = ExtractionResult(conversation_id=conv.conversation_id, real_time=conv.real_time)

    if not text:
        result.scanned_with_zero = True
        return result

    raw = caller(text, endpoint=endpoint, model=model, temperature=temperature)
    records = _extract_json_array(raw)
    if records is None:
        result.parse_failed = True
        result.scanned_with_zero = True
        return result

    for rec in records:
        if not isinstance(rec, dict) or "claim_text" not in rec or "quoted_source" not in rec:
            result.rejected.append({"raw": rec, "reason": "malformed record shape"})
            continue
        claim_text = rec["claim_text"]
        quoted = rec["quoted_source"]
        if not isinstance(claim_text, str) or not isinstance(quoted, str):
            result.rejected.append({"raw": rec, "reason": "claim_text/quoted_source not strings"})
            continue
        if quoted not in text:
            result.rejected.append({
                "claim_text": claim_text, "quoted_source": quoted,
                "reason": "quoted_source is not a literal substring of the transcript",
            })
            continue
        result.claims.append(Claim(claim_text=claim_text, quoted_source=quoted))

    if not result.claims:
        result.scanned_with_zero = True
    return result


# ---------------------------------------------------------------------------
# Cache -- keyed on conversation_id, invalidated on any source file's
# (path, mtime) changing. A re-run with nothing changed re-extracts zero
# conversations.
# ---------------------------------------------------------------------------

def source_identity(conv) -> list:
    ids = []
    for s in conv.sessions:
        try:
            mtime = s.path.stat().st_mtime
        except OSError:
            mtime = None
        ids.append([str(s.path), mtime])
    return sorted(ids, key=lambda pair: pair[0])


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(cache: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _cache_entry(result: ExtractionResult, sources: list) -> dict:
    return {
        "sources": sources,
        "claims": [vars(c) for c in result.claims],
        "rejected": result.rejected,
        "parse_failed": result.parse_failed,
        "scanned_with_zero": result.scanned_with_zero,
        "real_time": result.real_time,
    }


def _result_from_cache(conv, entry: dict) -> ExtractionResult:
    return ExtractionResult(
        conversation_id=conv.conversation_id,
        real_time=entry.get("real_time"),
        claims=[Claim(**c) for c in entry.get("claims", [])],
        rejected=entry.get("rejected", []),
        parse_failed=entry.get("parse_failed", False),
        scanned_with_zero=entry.get("scanned_with_zero", False),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_extraction(conversations: list, excluded: list, *, caller, endpoint: str,
                     model: str, temperature: float, cache: dict) -> dict:
    """`conversations` must already be newest-first (lt.order_newest_first's
    first return value). `excluded` are conversations lt.group_conversations
    could not resolve a real timestamp for -- excluded and named here too,
    never silently omitted."""
    results: list[ExtractionResult] = []
    reextracted = 0
    from_cache = 0

    for conv in conversations:
        sources = source_identity(conv)
        cached = cache.get(conv.conversation_id)
        if cached is not None and cached.get("sources") == sources:
            results.append(_result_from_cache(conv, cached))
            from_cache += 1
            continue
        result = extract_for_conversation(
            conv, caller=caller, endpoint=endpoint, model=model, temperature=temperature,
        )
        results.append(result)
        cache[conv.conversation_id] = _cache_entry(result, sources)
        reextracted += 1

    total_claims = sum(len(r.claims) for r in results)
    total_rejected = sum(len(r.rejected) for r in results)
    total_offered = total_claims + total_rejected
    rejection_rate = (total_rejected / total_offered) if total_offered else 0.0

    return {
        "model_id": model,
        "endpoint": endpoint,
        "temperature": temperature,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "conversations_scanned": len(results),
        "conversations_reextracted": reextracted,
        "conversations_from_cache": from_cache,
        "conversations_excluded_no_timestamp": [
            {"conversation_id": c.conversation_id, "reason": c.exclude_reason} for c in excluded
        ],
        "claims_extracted": total_claims,
        "claims_rejected": total_rejected,
        "quote_rejection_rate": rejection_rate,
        "conversations": [
            {
                "conversation_id": r.conversation_id,
                "real_time": r.real_time,
                "claims": [vars(c) for c in r.claims],
                "rejected": r.rejected,
                "parse_failed": r.parse_failed,
                "scanned_with_zero": r.scanned_with_zero,
            }
            for r in results
        ],
    }


def main() -> None:
    import functools

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", type=Path, default=k1.DEFAULT_MAP)
    ap.add_argument("--host", help="census as if run on this hostname")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--model", required=True, help="LM Studio model id (recorded as provenance)")
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                     help="per-request timeout in seconds (default 900)")
    ap.add_argument("--no-json-mode", dest="json_mode", action="store_false",
                     help="disable response_format grammar constraint, if the "
                          "endpoint errors on it")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    bound_caller = functools.partial(call_lmstudio, timeout=args.timeout, json_mode=args.json_mode)

    map_rows = k1.load_map(args.map)
    mapped_ids = {r.session_id for r in map_rows}
    conversations, access_errors = k0.discover_conversations(args.host)
    if access_errors:
        print("** filesystem access errors while discovering the store -- "
              "results below are NOT proof of a complete population **", file=sys.stderr)
        for e in access_errors:
            print(f"   {e}", file=sys.stderr)

    mapped_conversations = [c for c in conversations if c.conversation_id in mapped_ids]
    included, excluded = lt.order_newest_first(mapped_conversations)

    cache = load_cache(args.cache)
    report = run_extraction(
        included, excluded, caller=bound_caller, endpoint=args.endpoint,
        model=args.model, temperature=args.temperature, cache=cache,
    )
    save_cache(cache, args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"scanned:            {report['conversations_scanned']} "
          f"({report['conversations_reextracted']} re-extracted, "
          f"{report['conversations_from_cache']} from cache)")
    print(f"excluded (no ts):   {len(report['conversations_excluded_no_timestamp'])}")
    print(f"claims extracted:   {report['claims_extracted']}")
    print(f"claims rejected:    {report['claims_rejected']} "
          f"(rate {report['quote_rejection_rate']:.1%})")
    print(f"\nreport written: {args.out}")


if __name__ == "__main__":
    main()
