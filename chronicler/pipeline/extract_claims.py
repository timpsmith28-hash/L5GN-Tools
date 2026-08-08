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
import re
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

# Real-run evidence (2026-08-07, qwen3.5, work rig): prompt-processing
# throughput fell from ~158 tok/s (tokens 8192-16384) to ~48 tok/s (tokens
# 56320-64955) WITHIN a single 65k-token call -- attention cost scales worse
# than linear as context fills, so a conversation windowed into several
# smaller calls processes disproportionately faster than one huge call, not
# just proportionately. These three knobs are the pace levers that evidence
# argues for:
#   - windowing: split a conversation over this size into turn-aligned
#     chunks, so each chunk stays near the fast end of that curve.
#   - batching: several SHORT conversations share one call, so the fixed
#     per-call overhead (system prompt, round trip, generation floor) is
#     paid once instead of once-per-conversation.
DEFAULT_MAX_WINDOW_TOKENS = 8000
DEFAULT_SMALL_CONV_TOKENS = 1500
DEFAULT_BATCH_TARGET_TOKENS = 6000
DEFAULT_BATCH_MAX_CONVERSATIONS = 6

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

SYSTEM_PROMPT_BATCH = (
    "You extract atomic factual or decision claims from SEVERAL short work "
    "conversation transcripts, presented below as numbered sections "
    "'=== CONVERSATION <n> ==='. Return ONLY a JSON array, no prose, no "
    "markdown fence. Each element is an object with exactly three fields: "
    "`conversation_index` (the integer n of the section the claim came "
    "from), `claim_text`, and `quoted_source` (a LITERAL, VERBATIM substring "
    "copied character-for-character from THAT SAME numbered section -- "
    "never from a different section, never a paraphrase). If none of the "
    "conversations have claims worth recording, return an empty array []."
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

CLAIMS_BATCH_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "conversation_index": {"type": "integer"},
            "claim_text": {"type": "string"},
            "quoted_source": {"type": "string"},
        },
        "required": ["conversation_index", "claim_text", "quoted_source"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# LM Studio transport -- stdlib only.
# ---------------------------------------------------------------------------

def call_lmstudio(transcript_text: str, *, endpoint: str, model: str,
                   temperature: float, timeout: float = DEFAULT_TIMEOUT,
                   json_mode: bool = True, batch: bool = False) -> str:
    """POST to an OpenAI-compatible chat/completions endpoint; returns the
    assistant message content as a raw string. Raises ``OSError`` /
    ``urllib.error.URLError`` on any transport failure -- callers must NOT
    swallow this (brief: 'loud failure, no partial report').

    ``json_mode`` requests grammar-constrained output via ``response_format``
    (``CLAIMS_JSON_SCHEMA``, or ``CLAIMS_BATCH_JSON_SCHEMA`` when
    ``batch=True``). Not every model runtime honours it (some MLX/GGUF
    backends silently ignore an unsupported field rather than erroring) --
    when it's respected it forecloses the conversational-reply failure mode
    entirely; when it isn't, behaviour is identical to before. Set
    ``json_mode=False`` if a given endpoint errors on the field outright.

    ``batch=True`` selects ``SYSTEM_PROMPT_BATCH`` -- only ``extract_batch``
    should ever pass it; the single-conversation path never does."""
    system = SYSTEM_PROMPT_BATCH if batch else SYSTEM_PROMPT
    schema = CLAIMS_BATCH_JSON_SCHEMA if batch else CLAIMS_JSON_SCHEMA
    schema_name = "claims_batch" if batch else "claims"
    body: dict = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": transcript_text},
        ],
    }
    if json_mode:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
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
    windows_total: int = 1
    windows_parse_failed: int = 0


# ---------------------------------------------------------------------------
# Wrapper-noise stripping -- pure token bloat for K2's purpose. Scoped to
# THIS module rather than local_transcripts.py's shared parser: ingest and
# census consumers of ParsedSession.messages need the untouched text (ingest
# writes it into chronicler.db verbatim), so the strip happens here, once,
# right before text is either sent to the model or checked for a literal
# quote -- both call sites go through `_conversation_parts` so the two never
# disagree about what "the transcript" contains.
# ---------------------------------------------------------------------------

_WRAPPER_PATTERNS = (
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
)


def _strip_wrapper_noise(text: str) -> str:
    out = text
    for pat in _WRAPPER_PATTERNS:
        out = pat.sub("", out)
    return out


def _conversation_parts(conv) -> list[str]:
    """Every message's text, every file, in file/sequence order, with
    wrapper noise stripped and empty-after-stripping messages dropped."""
    parts: list[str] = []
    for sess in conv.sessions:
        for _, role, text, _, _ in sess.messages:
            if not text:
                continue
            stripped = _strip_wrapper_noise(text)
            if stripped.strip():
                parts.append(stripped)
    return parts


def full_transcript_text(conv) -> str:
    """The substring universe `quoted_source` is checked against for an
    unwindowed call. Includes both roles: a claim's supporting quote can
    come from either side of the conversation."""
    return "\n".join(_conversation_parts(conv))


def approx_token_count(text: str) -> int:
    """Cheap stdlib-only estimate (~4 chars/token for English prose). There
    is no stdlib tokenizer, and adding a real one would be a dependency
    beyond the brief's 'stdlib only for transport' rule. Used only to decide
    whether/how to window or batch -- never trusted for anything that needs
    to be exact (the model's own accounting, visible in LM Studio's own
    logs, is the real number)."""
    return len(text) // 4


def build_windows(conv, max_tokens: int) -> list[str]:
    """Split a conversation's own message stream into windows of roughly
    ``max_tokens`` each, joined the same way `full_transcript_text` joins
    them, NEVER splitting a single message across a window boundary -- a
    claim's `quoted_source` must remain a literal substring of whichever
    window produced it. Real-run evidence for why this exists is in the
    module docstring's rate figures: a windowed conversation processes
    disproportionately faster than one huge call, not just proportionately,
    because attention cost was observed to scale worse than linear as
    context fills."""
    parts = _conversation_parts(conv)
    if not parts:
        return []
    windows: list[list[str]] = [[]]
    tokens_in_window = 0
    for part in parts:
        part_tokens = approx_token_count(part)
        if windows[-1] and tokens_in_window + part_tokens > max_tokens:
            windows.append([])
            tokens_in_window = 0
        windows[-1].append(part)
        tokens_in_window += part_tokens
    return ["\n".join(w) for w in windows if w]


def extract_for_conversation(conv, *, caller, endpoint: str, model: str,
                              temperature: float,
                              max_window_tokens: int | None = None) -> ExtractionResult:
    """Single-conversation path (used when a conversation is too large to
    batch with others, or batching is disabled). Windows internally when
    ``max_window_tokens`` is set and the conversation exceeds it; each
    window gets its own model call and its own literal-substring check
    against ITS OWN text, never the full transcript."""
    full_text = full_transcript_text(conv)
    result = ExtractionResult(conversation_id=conv.conversation_id, real_time=conv.real_time)

    if not full_text:
        result.scanned_with_zero = True
        result.windows_total = 0
        return result

    if max_window_tokens and approx_token_count(full_text) > max_window_tokens:
        windows = build_windows(conv, max_window_tokens) or [full_text]
    else:
        windows = [full_text]
    result.windows_total = len(windows)

    for window_text in windows:
        raw = caller(window_text, endpoint=endpoint, model=model, temperature=temperature)
        records = _extract_json_array(raw)
        if records is None:
            result.windows_parse_failed += 1
            continue

        for rec in records:
            if not isinstance(rec, dict) or "claim_text" not in rec or "quoted_source" not in rec:
                result.rejected.append({"raw": rec, "reason": "malformed record shape"})
                continue
            claim_text = rec["claim_text"]
            quoted = rec["quoted_source"]
            if not isinstance(claim_text, str) or not isinstance(quoted, str):
                result.rejected.append({"raw": rec, "reason": "claim_text/quoted_source not strings"})
                continue
            if quoted not in window_text:
                result.rejected.append({
                    "claim_text": claim_text, "quoted_source": quoted,
                    "reason": "quoted_source is not a literal substring of the transcript",
                })
                continue
            result.claims.append(Claim(claim_text=claim_text, quoted_source=quoted))

    result.parse_failed = result.windows_total > 0 and result.windows_parse_failed == result.windows_total
    if not result.claims:
        result.scanned_with_zero = True
    return result


def extract_batch(convs: list, *, caller, endpoint: str, model: str,
                   temperature: float) -> tuple[dict, list]:
    """Several SHORT conversations in one call. Returns
    ``({conversation_id: ExtractionResult}, unattributed_rejections)``.

    A record whose ``conversation_index`` doesn't resolve to one of
    ``convs``, or whose ``quoted_source`` isn't a literal substring of THAT
    specific conversation's own text (cross-conversation leakage is treated
    exactly like a fabricated quote -- never trusted just because it's a
    real substring of a DIFFERENT conversation in the batch), is rejected
    and counted, never silently dropped."""
    sections = []
    texts_by_index: dict[int, tuple] = {}
    for i, conv in enumerate(convs):
        text = full_transcript_text(conv)
        texts_by_index[i] = (conv, text)
        sections.append(f"=== CONVERSATION {i} (id={conv.conversation_id}) ===\n{text}")
    combined = "\n\n".join(sections)

    results = {
        conv.conversation_id: ExtractionResult(conversation_id=conv.conversation_id,
                                                  real_time=conv.real_time)
        for conv in convs
    }
    unattributed: list[dict] = []

    raw = caller(combined, endpoint=endpoint, model=model, temperature=temperature, batch=True)
    records = _extract_json_array(raw)
    if records is None:
        for conv in convs:
            r = results[conv.conversation_id]
            r.parse_failed = True
            r.scanned_with_zero = True
        return results, unattributed

    for rec in records:
        if (not isinstance(rec, dict) or "conversation_index" not in rec
                or "claim_text" not in rec or "quoted_source" not in rec):
            unattributed.append({"raw": rec, "reason": "malformed batch record shape"})
            continue
        idx = rec["conversation_index"]
        if not isinstance(idx, int) or idx not in texts_by_index:
            unattributed.append({"raw": rec, "reason": f"conversation_index {idx!r} not in this batch"})
            continue
        conv, text = texts_by_index[idx]
        claim_text = rec["claim_text"]
        quoted = rec["quoted_source"]
        result = results[conv.conversation_id]
        if not isinstance(claim_text, str) or not isinstance(quoted, str):
            result.rejected.append({"raw": rec, "reason": "claim_text/quoted_source not strings"})
            continue
        if quoted not in text:
            result.rejected.append({
                "claim_text": claim_text, "quoted_source": quoted,
                "reason": "quoted_source is not a literal substring of its own conversation "
                          "in the batch (cross-conversation leakage is treated the same as a "
                          "fabricated quote)",
            })
            continue
        result.claims.append(Claim(claim_text=claim_text, quoted_source=quoted))

    for conv in convs:
        r = results[conv.conversation_id]
        if not r.claims:
            r.scanned_with_zero = True
    return results, unattributed


def group_into_batches(conversations: list, *, small_token_floor: int,
                         batch_target_tokens: int, batch_max_conversations: int) -> list[list]:
    """Greedy grouping, in the order given (already newest-first). A
    conversation whose own text exceeds ``small_token_floor`` (or is empty)
    is never batched -- it comes back as its own group of one, meaning
    "process individually" to the caller. Batches never exceed
    ``batch_target_tokens`` combined or ``batch_max_conversations`` members."""
    groups: list[list] = []
    current: list = []
    current_tokens = 0
    for conv in conversations:
        tok = approx_token_count(full_transcript_text(conv))
        if tok == 0 or tok > small_token_floor:
            if current:
                groups.append(current)
                current = []
                current_tokens = 0
            groups.append([conv])
            continue
        if current and (current_tokens + tok > batch_target_tokens
                          or len(current) >= batch_max_conversations):
            groups.append(current)
            current = []
            current_tokens = 0
        current.append(conv)
        current_tokens += tok
    if current:
        groups.append(current)
    return groups


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
        "windows_total": result.windows_total,
        "windows_parse_failed": result.windows_parse_failed,
    }


def _result_from_cache(conv, entry: dict) -> ExtractionResult:
    return ExtractionResult(
        conversation_id=conv.conversation_id,
        real_time=entry.get("real_time"),
        claims=[Claim(**c) for c in entry.get("claims", [])],
        rejected=entry.get("rejected", []),
        parse_failed=entry.get("parse_failed", False),
        scanned_with_zero=entry.get("scanned_with_zero", False),
        windows_total=entry.get("windows_total", 1),
        windows_parse_failed=entry.get("windows_parse_failed", 0),
    )


# ---------------------------------------------------------------------------
# Progress reporting -- a plain "label: done/total" line, overwritten in
# place via \r rather than scrolling. Opt-in via a callback so hermetic
# tests (which pass none) are completely unaffected; the cost of the writes
# themselves is unmeasurable next to a several-hundred-ms-or-slower LM
# Studio call, so there is no real pace tradeoff here.
# ---------------------------------------------------------------------------

def make_progress_reporter(label: str, *, stream=None):
    stream = stream if stream is not None else sys.stderr

    def report(done: int, total: int) -> None:
        if total <= 0:
            return
        end = "\n" if done >= total else ""
        stream.write(f"\r{label}: {done}/{total}{end}")
        stream.flush()
    return report


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_extraction(conversations: list, excluded: list, *, caller, endpoint: str,
                     model: str, temperature: float, cache: dict,
                     max_window_tokens: int | None = DEFAULT_MAX_WINDOW_TOKENS,
                     small_conv_tokens: int | None = DEFAULT_SMALL_CONV_TOKENS,
                     batch_target_tokens: int = DEFAULT_BATCH_TARGET_TOKENS,
                     batch_max_conversations: int = DEFAULT_BATCH_MAX_CONVERSATIONS,
                     progress=None) -> dict:
    """`conversations` must already be newest-first (lt.order_newest_first's
    first return value). `excluded` are conversations lt.group_conversations
    could not resolve a real timestamp for -- excluded and named here too,
    never silently omitted.

    Conversations needing (re-)extraction are split three ways: large ones
    (over ``max_window_tokens``) go through the windowed single-conversation
    path; short ones (at or under ``small_conv_tokens``) are grouped and
    sent through `extract_batch`; everything in between is a normal
    single-call extraction. The final `results` list is reassembled in the
    ORIGINAL newest-first order regardless of which path processed each
    conversation, so K4's ordering assumption downstream is unaffected by
    how the network calls were shaped.

    Set ``max_window_tokens``/``small_conv_tokens`` to ``None``/``0`` to
    disable that lever. Changing either between runs should be paired with
    a fresh ``--cache`` (or a cleared one) -- the cache is keyed on source
    file identity only, not on these settings, by design (brief: an
    unchanged conversation is never re-extracted), so a stale cache entry
    from a differently-windowed prior run would otherwise be served as-is.
    """
    results_by_id: dict[str, ExtractionResult] = {}
    reextracted = 0
    from_cache = 0
    batch_unattributed: list[dict] = []

    needing_extraction: list = []
    for conv in conversations:
        sources = source_identity(conv)
        cached = cache.get(conv.conversation_id)
        if cached is not None and cached.get("sources") == sources:
            results_by_id[conv.conversation_id] = _result_from_cache(conv, cached)
            from_cache += 1
        else:
            needing_extraction.append(conv)

    total = len(conversations)
    if progress:
        progress(len(results_by_id), total)

    if small_conv_tokens:
        groups = group_into_batches(
            needing_extraction, small_token_floor=small_conv_tokens,
            batch_target_tokens=batch_target_tokens, batch_max_conversations=batch_max_conversations,
        )
    else:
        groups = [[c] for c in needing_extraction]

    for group in groups:
        if len(group) == 1:
            conv = group[0]
            result = extract_for_conversation(
                conv, caller=caller, endpoint=endpoint, model=model, temperature=temperature,
                max_window_tokens=max_window_tokens,
            )
            results_by_id[conv.conversation_id] = result
            cache[conv.conversation_id] = _cache_entry(result, source_identity(conv))
            reextracted += 1
            if progress:
                progress(len(results_by_id), total)
        else:
            batch_results, unattributed = extract_batch(
                group, caller=caller, endpoint=endpoint, model=model, temperature=temperature,
            )
            batch_unattributed.extend(unattributed)
            for conv in group:
                result = batch_results[conv.conversation_id]
                results_by_id[conv.conversation_id] = result
                cache[conv.conversation_id] = _cache_entry(result, source_identity(conv))
                reextracted += 1
            if progress:
                progress(len(results_by_id), total)

    results = [results_by_id[c.conversation_id] for c in conversations]

    total_claims = sum(len(r.claims) for r in results)
    total_rejected = sum(len(r.rejected) for r in results) + len(batch_unattributed)
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
        "batch_unattributed_rejections": batch_unattributed,
        "conversations": [
            {
                "conversation_id": r.conversation_id,
                "real_time": r.real_time,
                "claims": [vars(c) for c in r.claims],
                "rejected": r.rejected,
                "parse_failed": r.parse_failed,
                "scanned_with_zero": r.scanned_with_zero,
                "windows_total": r.windows_total,
                "windows_parse_failed": r.windows_parse_failed,
            }
            for r in results
        ],
    }


def merge_report(old: dict | None, new: dict, touched_ids: set) -> dict:
    """Merge a scoped (--project-filtered) run's report into the existing
    output file, so re-running just one project's conversations doesn't
    clobber everyone else's already-computed results. Conversations in
    `touched_ids` come from `new` (this run's own results, even a cache
    hit counts as "touched" since it was in scope); every other
    conversation is carried over unchanged from `old`. Aggregate stats are
    recomputed over the merged set, not just this run's slice, so the
    persisted file always reads as one coherent whole.

    `old is None` (no prior output, or first-ever run) returns `new`
    unchanged -- there is nothing to merge into."""
    if old is None:
        return new

    by_id = {c["conversation_id"]: c for c in old.get("conversations", [])}
    for c in new["conversations"]:
        by_id[c["conversation_id"]] = c
    merged_conversations = list(by_id.values())

    excluded_by_id = {c["conversation_id"]: c for c in old.get("conversations_excluded_no_timestamp", [])}
    for c in new["conversations_excluded_no_timestamp"]:
        excluded_by_id[c["conversation_id"]] = c
    # An excluded conversation that got resolved and now appears among the
    # touched, successfully-processed ones must not linger in "excluded" too.
    for cid in touched_ids:
        excluded_by_id.pop(cid, None)
    merged_excluded = list(excluded_by_id.values())

    total_claims = sum(len(c["claims"]) for c in merged_conversations)
    total_rejected = (sum(len(c["rejected"]) for c in merged_conversations)
                        + len(new.get("batch_unattributed_rejections", [])))
    total_offered = total_claims + total_rejected
    rejection_rate = (total_rejected / total_offered) if total_offered else 0.0

    merged = dict(new)  # keep this run's own provenance (model_id, run_timestamp, etc.)
    merged["conversations"] = merged_conversations
    merged["conversations_excluded_no_timestamp"] = merged_excluded
    merged["conversations_scanned"] = len(merged_conversations)
    merged["claims_extracted"] = total_claims
    merged["claims_rejected"] = total_rejected
    merged["quote_rejection_rate"] = rejection_rate
    merged["partial_run_projects"] = sorted(new.get("partial_run_projects") or [])
    return merged


def main() -> None:
    import functools

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", type=Path, default=k1.DEFAULT_MAP)
    ap.add_argument("--project", action="append",
                     help="only (re-)extract conversations mapped to this project_id "
                          "(repeatable). Omit to process the whole map. Results are "
                          "merged into --out's existing content, if any, rather than "
                          "overwriting other projects' data.")
    ap.add_argument("--host", help="census as if run on this hostname")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--model", required=True, help="LM Studio model id (recorded as provenance)")
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                     help="per-request timeout in seconds (default 900)")
    ap.add_argument("--no-json-mode", dest="json_mode", action="store_false",
                     help="disable response_format grammar constraint, if the "
                          "endpoint errors on it")
    ap.add_argument("--max-window-tokens", type=int, default=DEFAULT_MAX_WINDOW_TOKENS,
                     help="split a conversation over this size into turn-aligned "
                          "windows (0 disables windowing, default 8000)")
    ap.add_argument("--small-conv-tokens", type=int, default=DEFAULT_SMALL_CONV_TOKENS,
                     help="conversations at or under this size are grouped into "
                          "one call each (0 disables batching, default 1500)")
    ap.add_argument("--batch-target-tokens", type=int, default=DEFAULT_BATCH_TARGET_TOKENS,
                     help="max combined size of a batch (default 6000)")
    ap.add_argument("--batch-max-conversations", type=int, default=DEFAULT_BATCH_MAX_CONVERSATIONS,
                     help="max conversations per batch (default 6)")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-progress", dest="progress", action="store_false",
                     help="suppress the 'extracting: done/total' terminal progress line")
    args = ap.parse_args()

    bound_caller = functools.partial(call_lmstudio, timeout=args.timeout, json_mode=args.json_mode)

    map_rows = k1.load_map(args.map)
    project_filter = set(args.project) if args.project else None
    if project_filter:
        map_rows = [r for r in map_rows if r.project_id in project_filter]
        unknown = project_filter - {r.project_id for r in k1.load_map(args.map)}
        if unknown:
            print(f"** --project value(s) not found in the map: {sorted(unknown)} **", file=sys.stderr)
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
    reporter = make_progress_reporter("extracting") if args.progress else None
    report = run_extraction(
        included, excluded, caller=bound_caller, endpoint=args.endpoint,
        model=args.model, temperature=args.temperature, cache=cache,
        max_window_tokens=args.max_window_tokens or None,
        small_conv_tokens=args.small_conv_tokens or None,
        batch_target_tokens=args.batch_target_tokens,
        batch_max_conversations=args.batch_max_conversations,
        progress=reporter,
    )
    save_cache(cache, args.cache)

    if project_filter:
        report["partial_run_projects"] = sorted(project_filter)
        old = None
        if args.out.exists():
            try:
                old = json.loads(args.out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                old = None
        touched_ids = {c["conversation_id"] for c in report["conversations"]}
        report = merge_report(old, report, touched_ids)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if project_filter:
        print(f"scoped to project(s): {sorted(project_filter)}")
    print(f"scanned:            {report['conversations_scanned']} "
          f"({report['conversations_reextracted']} re-extracted this run, "
          f"{report['conversations_from_cache']} from cache this run)")
    print(f"excluded (no ts):   {len(report['conversations_excluded_no_timestamp'])}")
    print(f"claims extracted:   {report['claims_extracted']}")
    print(f"claims rejected:    {report['claims_rejected']} "
          f"(rate {report['quote_rejection_rate']:.1%})")
    if report["batch_unattributed_rejections"]:
        print(f"batch-unattributed: {len(report['batch_unattributed_rejections'])} "
              f"(malformed/misindexed batch records -- see report)")
    windows_total = sum(c["windows_total"] for c in report["conversations"])
    windows_failed = sum(c["windows_parse_failed"] for c in report["conversations"])
    if windows_total > report["conversations_scanned"]:
        print(f"windows:            {windows_total} calls across "
              f"{report['conversations_scanned']} conversations "
              f"({windows_failed} window parse failures)")
    print(f"\nreport written: {args.out}")


if __name__ == "__main__":
    main()
