"""bench_failures.py -- Task 3, docs/COWORK_BRIEF_model_bench.md.

The failure taxonomy: "a failed run is data, not an error to retry away --
but only if the *kind* is recorded" (the brief's own words), enforced by its
own stop condition: "A failure is recorded without its kind -> stop." This
module classifies a bench run's failures from signals K2/K4 ALREADY emit --
the whole-stage exit code and merged stdout/stderr text `curator_control.
run_stage` already captures (`StageOutcome`), the per-window `token_count`
`bench_ledger.parse_timing_line` already recovers, and the per-conversation
`parse_failed`/`scanned_with_zero` flags K2's own `--out` report already
writes. Nothing here asks K2/K4 to compute or print anything new -- see
`bench_ledger.py`'s module docstring for why that line is held this round;
the same discipline applies here.

**Classification is called explicitly, on evidence the caller already has a
reason to suspect is a failure -- never run automatically over every
ledger row.** `generation_ms_per_token` is `None` both when a call
genuinely failed AND when the endpoint simply doesn't report a `usage`
block at all (a normal, common degrade -- Addendum 2's own words: "not
every runtime returns it ... recorded as absent, never estimated"). Auto-
classifying every missing-usage row as a failure would manufacture failures
out of a harmless backend quirk, which is worse than under-classifying.
The bench harness calls `classify_stage_outcome`/`classify_conversation_
result` only where it already has independent evidence of an actual
failure (`StageOutcome.state == "failed"`, or `parse_failed=True` in K2's
own report) -- this module's job is naming the kind, never deciding
whether something failed in the first place.

**One honest structural gap, stated plainly rather than worked around.**
The brief names FIVE kinds: context overflow, schema violation, refusal,
timeout, transport/endpoint error. This module distinguishes four of those
five from what K2 already emits -- SCHEMA VIOLATION and REFUSAL collapse
into one bucket here, `"schema_violation_or_refusal"`, because telling them
apart needs the model's raw response text for a failed parse, and K2
discards that text the moment `_extract_json_array` fails to parse it
(`extract_claims.py extract_for_conversation`'s `if records is None:`
branch) -- nothing persists it anywhere this module can read afterwards.
Capturing it would mean editing `extract_claims.py` to stash the raw text
before discarding it, which is a K2 code change, and the brief's own stop
condition forbids "Any change to K2/K4 logic" this round. Reporting a
fabricated 5-way split on data that cannot support it would be exactly the
invented precision 0037 refuses -- so this module reports the honest 4-way
split and names the fifth as a known gap (see `docs/COWORK_REPORT_
model_bench.md` once written), rather than guessing (e.g. "contains
'sorry' == refusal") and calling that a measurement.

Stdlib only, `chronicler.pipeline` tier. Does NOT import `chronicler.review`
(so not even `curator_control.StageOutcome` itself) -- `classify_stage_
outcome` takes anything with `.state`/`.stdout_tail` attributes, duck-typed,
same dependency-direction discipline `ledger.py`/`bench_ledger.py` already
state for themselves.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from l5gntools.common import DATA_DIR

#: Separate from both `ledger.DEFAULT_LEDGER_PATH` and `bench_ledger.
#: DEFAULT_BENCH_LEDGER_PATH` -- a failure is a different KIND of record
#: (no `generation_ms_per_token` at all, by definition), not a ledger row
#: with a hole in it. Keeping the file separate means a reader of
#: `bench_ledger.jsonl` never has to filter failures out to compute a real
#: throughput summary, and a reader of this file never has to filter
#: successes out to compute a failure rate.
DEFAULT_BENCH_FAILURES_PATH: Path = DATA_DIR / "model_bench" / "bench_failures.jsonl"

#: The taxonomy. Four kinds this module can actually tell apart from what
#: K2/K4 already emit, plus "unknown" (an honest catch-all, never omitted
#: silently) -- see module docstring for why schema_violation and refusal
#: are one bucket here, not two.
FAILURE_KINDS = (
    "context_overflow",
    "schema_violation_or_refusal",
    "timeout",
    "transport_error",
    "unknown",
)

_REQUIRED_FIELDS = (
    "kind", "model_id", "stage", "host", "config_fingerprint",
    "prompt_fingerprint", "position_in_session",
)
_OPTIONAL_FIELDS = ("conversation_id", "project_id", "detail")
_ALL_FIELDS = _REQUIRED_FIELDS + _OPTIONAL_FIELDS


# ---------------------------------------------------------------------------
# Classification -- pure functions, no I/O, so they're trivial to test
# against a hand-built exception message or report fragment.
# ---------------------------------------------------------------------------

#: Matched on the EXCEPTION CLASS NAME as Python's own traceback formatter
#: writes it ("module.ClassName: message", lowercased here) -- stable
#: regardless of which LM Studio backend or model produced the underlying
#: failure, unlike a specific server's wording.
_TIMEOUT_MARKERS = ("timed out", "timeouterror", "socket.timeout")
_TRANSPORT_MARKERS = (
    "urlerror", "httperror", "connectionreseterror", "connectionrefusederror",
    "connection refused", "urllib.error", "oserror",
)
#: NOT verified against a real LM Studio error body -- this repo has never
#: run a request that actually overflowed a model's context (T1 has never
#: run, per the brief's own "why this round exists"). Starting hypothesis
#: only; refine against real Task 0/candidate evidence once it exists,
#: exactly as the brief's own honesty bar asks of every other figure here.
_CONTEXT_OVERFLOW_MARKERS = (
    "context length", "context_length", "context window", "n_ctx",
    "exceeds the model", "too many tokens", "maximum context",
    "prompt is too long", "trying to keep the first",
)


def classify_window_by_size(token_count: int | None, context_length: int | None,
                             *, reserved_for_output: int = 512) -> str | None:
    """Proactive classification, decidable BEFORE any call is made: if a
    window's own `token_count` (already computed and emitted in every
    `TIMING_WINDOW` line, recovered by `bench_ledger.parse_timing_line`)
    plus a fixed reserve for the model's own reply exceeds the candidate's
    configured `context_length` (part of the settings dict `config_
    fingerprint` was built from -- Task 2 item 2), the window cannot fit no
    matter what the endpoint says back. Returns `None` when either figure
    is unknown (never guesses a limit it wasn't told) or the window fits --
    `None` here means "not classifiable as context overflow by this check",
    not "not a failure"."""
    if token_count is None or context_length is None:
        return None
    if token_count + reserved_for_output > context_length:
        return "context_overflow"
    return None


def classify_crash_text(text: str) -> str:
    """Classify a whole-STAGE crash (`StageOutcome.state == "failed"`) from
    its captured stdout/stderr text. An uncaught exception in K2/K4's
    `main()` -- and neither catches the exceptions `call_lmstudio`/`post_
    json_with_retry` raise once retries are exhausted -- prints a Python
    traceback to stderr, merged into the same stream `run_stage` already
    captures, ending in `SomeModule.SomeError: message`. Checked in this
    order: context-overflow markers first (a `urllib.error.HTTPError` IS
    also a transport-marker match, so if its body names a context problem
    that is the more useful classification and must win), then timeout,
    then generic transport, else `"unknown"` -- never silently blank."""
    lowered = text.lower()
    if any(m in lowered for m in _CONTEXT_OVERFLOW_MARKERS):
        return "context_overflow"
    if any(m in lowered for m in _TIMEOUT_MARKERS):
        return "timeout"
    if any(m in lowered for m in _TRANSPORT_MARKERS):
        return "transport_error"
    return "unknown"


def classify_stage_outcome(outcome: Any) -> str | None:
    """`None` for anything that isn't itself a failure by this taxonomy's
    concern (`state in ("success", "skipped", "blocked")`) -- a `blocked`
    stage never reached the model at all, which is a precondition problem
    (COWORK_BRIEF_curator_tab.md's "Grounding"), not a model capability
    limit this taxonomy exists to tier. For `state == "failed"`, classifies
    `outcome.stdout_tail` (the last 10 captured lines `run_stage` already
    keeps) via `classify_crash_text`. Duck-typed on `.state`/`.stdout_tail`
    so this module never has to import `curator_control` (app tier)."""
    if getattr(outcome, "state", None) != "failed":
        return None
    return classify_crash_text(getattr(outcome, "stdout_tail", "") or "")


def classify_conversation_result(conv_report: dict, *, token_count: int | None = None,
                                  context_length: int | None = None) -> str | None:
    """Classify ONE conversation's entry from K2's own `--out` report
    (`report["conversations"][i]`, the shape `extract_claims._build_report`
    already writes: `parse_failed`, `scanned_with_zero`, `windows_parse_
    failed`, `windows_total`). `token_count`, if given, should be the
    LARGEST window's `token_count` among this conversation's `TIMING_WINDOW`
    lines (recovered via `bench_ledger`) -- used only to check the
    context-overflow hypothesis before falling back to the combined bucket.

    Returns `None` when the conversation is NOT a failure by this
    taxonomy's own definition: `scanned_with_zero=True` with
    `parse_failed=False` (every window parsed fine and correctly found zero
    claims) is a CORRECT result, not a failure -- mis-tiering "this
    conversation genuinely had nothing to extract" as a capability limit
    would corrupt exactly the signal Task 3 exists to keep clean."""
    if not conv_report.get("parse_failed"):
        return None
    overflow = classify_window_by_size(token_count, context_length)
    if overflow:
        return overflow
    return "schema_violation_or_refusal"


# ---------------------------------------------------------------------------
# Recording -- append-only, one JSON object per line, own file, own required
# fields. `path` is REQUIRED everywhere, same discipline as `bench_ledger`.
# ---------------------------------------------------------------------------

def record_failure(entry: dict, path: Path) -> None:
    """Append one failure record. `kind` MUST be one of `FAILURE_KINDS` --
    this is the structural enforcement of the brief's own stop condition
    ("A failure is recorded without its kind -> stop"): there is no code
    path in this module that can write a failure row with a missing or
    invalid `kind`, not a convention a caller could forget to follow."""
    if entry.get("kind") not in FAILURE_KINDS:
        raise ValueError(
            f"failure entry must carry a kind from {FAILURE_KINDS}, got "
            f"{entry.get('kind')!r}: {entry}")
    missing = [f for f in _REQUIRED_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"failure entry missing required field(s) {missing}: {entry}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = dict(entry)
    stamped["timestamp"] = datetime.now(timezone.utc).isoformat()
    row = {k: stamped.get(k) for k in _ALL_FIELDS}
    row["timestamp"] = stamped["timestamp"]
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def load_failures(path: Path) -> list[dict]:
    """As `bench_ledger.load_entries` -- absent file is `[]`, a corrupt line
    is skipped rather than fatal to the whole read."""
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# ---------------------------------------------------------------------------
# Reading back -- counts by kind, for Task 5's reliability column
# ("reliability -- failure rate by kind"). Deliberately thin: this module
# classifies and records; Task 5's own report code is where a failure rate
# gets divided by a unit count and rendered.
# ---------------------------------------------------------------------------

def counts_by_kind(entries: list[dict], *, model_id: str, stage: str,
                    config_fingerprint: str, prompt_fingerprint: str) -> dict[str, int]:
    """`{kind: count}` for the exact `(model, stage, config, prompt)` unit
    Task 2 established as comparable -- every kind in `FAILURE_KINDS` is
    present in the result with a count of 0 if unseen, so a caller never
    has to guess whether a kind was absent because it didn't happen or
    because this function forgot to report it."""
    counts = {k: 0 for k in FAILURE_KINDS}
    for e in entries:
        if (e.get("model_id") == model_id and e.get("stage") == stage
                and e.get("config_fingerprint") == config_fingerprint
                and e.get("prompt_fingerprint") == prompt_fingerprint):
            kind = e.get("kind")
            if kind in counts:
                counts[kind] += 1
    return counts
