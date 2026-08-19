"""parse_lmstudio_log.py -- bench-tier converter, NOT part of K2/K4.

Turns a raw LM Studio server debug-log export into one structured JSON
object per real `/v1/chat/completions` call, so it can be diffed against
`bench_ledger.jsonl` without hand-rolling ad hoc regexes over the raw log
every time (as the last two rounds of this cross-check did).

Why this is needed at all: LM Studio's log is a flat stream where only the
FIRST physical line of a multi-line message carries a `[timestamp][LEVEL]`
prefix -- continuation lines (a pretty-printed JSON body, or the trailing
`prompt eval time` / `eval time` / `total time` / `graphs reused` block
that follows a generation) have no prefix of their own. A naive per-line
regex either misses multi-line blocks entirely or mis-attributes a
continuation line to the wrong timestamp. This groups lines into records
on that same boundary, then classifies each record.

**Message CONTENT is not recoverable from this log.** LM Studio itself
truncates long `content` fields in its own debug view (literal
`"... <Truncated in logs> ..."` markers, confirmed in both 2026-08-18 and
2026-08-19 exports) -- this converter does not try to reconstruct full
conversation text, only the structured numeric/timing data the log DOES
carry in full: task ids, `prompt eval time`/`eval time`/`total time`
(tokens and ms), the `usage` block inside `Generated prediction`, and
`[ERROR]` lines. That is everything a cross-check against
`bench_ledger.jsonl` (a throughput/timing table, not a content table)
actually needs.

Stdlib only. Read-only over the log; never touches K2/K4 or anything
under `chronicler/pipeline`.

Usage:
    python parse_lmstudio_log.py INPUT.log --out calls.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_RECORD_START = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\[(\w+)\]\s?(.*)$")
_TASK_RE = re.compile(r"task\s+(\d+)\b")
_PROMPT_EVAL_RE = re.compile(r"prompt eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens")
#: Negative lookbehind, NOT `[^/]eval time` -- the naive version also
#: matched the trailing " eval time" substring INSIDE "prompt eval time"
#: itself (the char before "eval" there is a space, which satisfies
#: `[^/]` too), silently duplicating prompt_ms/prompt_tok into eval_ms/
#: eval_tok on every single row. Caught by cross-checking against this
#: same call's `response_completion_tokens` (from the `usage` block),
#: which disagreed with `eval_tok` on every row until this was fixed.
_EVAL_RE = re.compile(r"(?<!prompt )eval time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens")
_TOTAL_RE = re.compile(r"total time\s*=\s*([\d.]+)\s*ms\s*/\s*(\d+)\s*tokens")
_LOAD_MODEL_RE = re.compile(r"load_model: loading model '([^']+)'")
_UNLOAD_RE = re.compile(r"Unloading model (\S+) due to (.+)")


def _records(lines: list[str]):
    """Yield (timestamp, level, text) for each log record -- text is the
    full multi-line body, first-line prefix stripped, continuation lines
    verbatim. A leading run of lines before the first bracketed line (rare,
    only if the export starts mid-record) is dropped -- there is nothing to
    attribute it to."""
    ts, level, buf = None, None, []
    for line in lines:
        m = _RECORD_START.match(line)
        if m:
            if ts is not None:
                yield ts, level, "\n".join(buf)
            ts, level, first = m.group(1), m.group(2), m.group(3)
            buf = [first] if first else []
        else:
            buf.append(line)
    if ts is not None:
        yield ts, level, "\n".join(buf)


def _try_json_after(text: str, marker: str):
    idx = text.find(marker)
    if idx == -1:
        return None
    brace = text.find("{", idx)
    if brace == -1:
        return None
    # Bracket-match from the first `{` to find the real end of the JSON
    # blob -- `json.loads` with a growing slice would be O(n^2) and fragile
    # against trailing content; counting braces is exact and cheap.
    depth = 0
    for i in range(brace, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                chunk = text[brace:i + 1]
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    return None
    return None


def parse_log(path: Path) -> list[dict]:
    """Returns a list of call dicts, in the order LM Studio processed them
    (this backend serves one request per slot at a time here, so simple
    sequential association of "next timing/response after a request" is
    reliable -- confirmed by every request's own `task` id in this log
    always increasing until a model reload resets the counter to 0)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    calls: list[dict] = []
    current: dict | None = None
    load_events: list[dict] = []

    def flush():
        nonlocal current
        if current is not None:
            calls.append(current)
        current = None

    for ts, level, text in _records(lines):
        if "Received request: POST to /v1/chat/completions" in text:
            flush()
            body = _try_json_after(text, "with body")
            current = {
                "request_ts": ts,
                "model": (body or {}).get("model"),
                "max_tokens": (body or {}).get("max_tokens"),
                "is_probe": bool(body and body.get("max_tokens") == 1),
                "message_count": len((body or {}).get("messages", [])),
                "task_id": None,
                "error": None,
                "prompt_ms": None, "prompt_tok": None,
                "eval_ms": None, "eval_tok": None,
                "total_ms": None, "total_tok": None,
                "response_prompt_tokens": None, "response_completion_tokens": None,
                "response_ts": None,
            }
            continue

        if level == "ERROR" and current is not None and current["error"] is None:
            current["error"] = text.strip()
            continue

        if "load_model: loading model" in text:
            m = _LOAD_MODEL_RE.search(text)
            load_events.append({"ts": ts, "kind": "load", "model": m.group(1) if m else None})
            continue
        if "Unloading model" in text:
            m = _UNLOAD_RE.search(text)
            load_events.append({"ts": ts, "kind": "unload",
                                 "model": m.group(1) if m else None,
                                 "reason": m.group(2) if m else None})
            continue

        pm = _PROMPT_EVAL_RE.search(text)
        if pm and current is not None:
            tm = _TASK_RE.search(text)
            if tm:
                current["task_id"] = int(tm.group(1))
            current["prompt_ms"] = float(pm.group(1))
            current["prompt_tok"] = int(pm.group(2))
            em = _EVAL_RE.search(text)
            if em:
                current["eval_ms"] = float(em.group(1))
                current["eval_tok"] = int(em.group(2))
            tot = _TOTAL_RE.search(text)
            if tot:
                current["total_ms"] = float(tot.group(1))
                current["total_tok"] = int(tot.group(2))
            continue

        if "Generated prediction:" in text and current is not None:
            resp = _try_json_after(text, "Generated prediction:")
            if resp:
                usage = resp.get("usage") or {}
                current["response_ts"] = ts
                current["response_prompt_tokens"] = usage.get("prompt_tokens")
                current["response_completion_tokens"] = usage.get("completion_tokens")
            continue

    flush()
    for c in calls:
        c["load_events_seen_before"] = sum(1 for e in load_events if e["ts"] <= c["request_ts"])
    return calls


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("log_path", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    calls = parse_log(args.log_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for c in calls:
            f.write(json.dumps(c) + "\n")

    real = [c for c in calls if not c["is_probe"]]
    errored = [c for c in calls if c["error"]]
    print(f"{len(calls)} calls parsed ({len(real)} real extraction calls, "
          f"{len(calls) - len(real)} probes), {len(errored)} carried an [ERROR] line "
          f"-> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
