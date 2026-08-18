"""bench_ledger.py -- Task 2, docs/COWORK_BRIEF_model_bench.md.

**A widened SIBLING of `ledger.py`, never a replacement for it.** `ledger.py`
keeps exactly four fields on purpose ("Anything else ... is provenance for
THAT record, not calibration data this module needs to remember") because it
feeds the planner's real production estimate, and a wide row there is a wide
surface for a candidate model's numbers to leak into work the estate actually
budgets against. This module carries the row the brief's Task 2 actually
wants -- `prompt_fingerprint`, `config_fingerprint`, the discarded numerics,
`position_in_session`, `host` -- for the bench alone, and it is structurally
incapable of writing where `ledger.py` writes: there is no module-level
default path here, `DEFAULT_BENCH_LEDGER_PATH` is a different file under a
different directory, and every recording function takes `path` as a required
argument, never an optional one that could silently fall back to
`ledger.DEFAULT_LEDGER_PATH`. The brief's own stop condition --
"Bench runs write to `data/calibration_ledger.jsonl`" -- cannot happen by
accident through this module; it would take a caller explicitly importing
`ledger` instead, which is a different, visible mistake.

**No K2/K4 logic is touched to build this.** Every field this module adds
either (a) is parsed straight out of the existing `TIMING_WINDOW`/
`TIMING_CLAIM` line text K2/K4 already write to stderr (the "discarded
numerics" -- `prompt_tokens`, `completion_tokens`, `token_count`,
`wall_clock_seconds`, `usage_available` -- Addendum 2 already computes and
emits every one of them; nothing here asks K2/K4 to compute anything new),
or (b) is supplied once per bench session by the CALLER, who is the only
party that actually knows it: `config_fingerprint` (LM Studio's settings,
which K2/K4 have no notion of), `host` (the machine running the bench),
`position_in_session` (the candidate's slot in this repeat's counterbalanced
order), and `prompt_fingerprint` (available via
`chronicler.pipeline.extract_claims.prompt_fingerprint()`, an existing
function this module calls rather than duplicates -- recording it is not
changing the prompt, per the brief's own words on this exact point).

**Time-to-first-token is NOT implemented here, on purpose.** The brief's
Task 2 item 5 wants it, but `extract_claims.call_lmstudio` makes a plain
(non-streaming) request -- capturing TTFT means observing when the first
streamed token arrives, which requires changing how K2/K4 call the model.
That is exactly what the brief's own "Explicitly out of scope" section
forbids this round ("Any change to K2/K4 logic ... Changing the stage while
benchmarking models measures neither"). `time_to_first_token_ms` is still a
field on every entry, always `None` this round, so a future round that DOES
revisit that stop condition needs no ledger schema migration -- an absent
measurement recorded as `None` is this codebase's own discipline (0037),
applied to the schema itself rather than invented as a workaround.

Stdlib only, `chronicler.pipeline` tier (imports `extract_claims`, a sibling
module, never `chronicler.review` -- dependency direction runs app ->
pipeline, never back, same rule `ledger.py` already states for itself).
"""
from __future__ import annotations

import hashlib
import json
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from l5gntools.common import DATA_DIR

#: Deliberately NOT `ledger.DEFAULT_LEDGER_PATH` and not even the same
#: directory -- `data/knowledge_curator/` is where production calibration
#: data lives (DECISIONS 0044); the bench's numbers do not belong near it,
#: so a careless `cp`/glob over one directory never picks up the other.
DEFAULT_BENCH_LEDGER_PATH: Path = DATA_DIR / "model_bench" / "bench_ledger.jsonl"

#: Every field a bench ledger entry carries. Wider than `ledger.py`'s
#: `_ENTRY_FIELDS` by design -- see module docstring. `time_to_first_token_ms`
#: is always None this round (not implemented); kept as a field so the shape
#: doesn't need to change if a later round adds it.
_REQUIRED_FIELDS = (
    "model_id", "stage", "cool_down_preceded", "generation_ms_per_token",
    "prompt_fingerprint", "config_fingerprint", "host", "position_in_session",
)
_OPTIONAL_FIELDS = (
    "conversation_id", "project_id", "window_index", "windows_total", "kind",
    "usage_available", "prompt_tokens", "completion_tokens", "token_count",
    "wall_clock_seconds", "time_to_first_token_ms",
)
_ALL_FIELDS = _REQUIRED_FIELDS + _OPTIONAL_FIELDS

#: Task 2 item 2's own list of what belongs in a config fingerprint -- named
#: here so a caller building the settings dict has one place to check the
#: expected shape against, not a private convention only this docstring
#: remembers. `build_config_fingerprint` does not enforce this list (a
#: caller on an endpoint with a different settings surface should still be
#: able to fingerprint it); it is documentation, not validation.
CONFIG_FINGERPRINT_FIELDS = (
    "context_length", "gpu_offload_layers", "quantisation", "kv_cache_type",
    "flash_attention", "batch_size", "ttl_seconds", "auto_unload",
)


# ---------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------

def build_config_fingerprint(settings: dict) -> str:
    """sha256 hex digest over a canonical (sorted-key, compact) JSON encoding
    of ``settings`` -- same shape as `extract_claims.prompt_fingerprint()`
    (sha256 hex over a deterministic encoding), so the two fingerprints read
    the same way in a report. Two settings dicts that differ in ANY key,
    including one the caller forgot to set, hash differently -- there is no
    partial credit and no default fill-in, because a silently-defaulted
    setting is exactly the kind of untracked configuration drift Task 2
    exists to stop ("the existing 116 entries may span several
    configurations with no way to tell now")."""
    canon = json.dumps(settings, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Parsing a real TIMING_WINDOW / TIMING_CLAIM / TIMING line
# ---------------------------------------------------------------------------

_KV_RE = re.compile(r"(\w+)=(\S+)")

_INT_FIELDS = {"window_index", "windows_total", "token_count", "prompt_tokens", "completion_tokens"}
_FLOAT_FIELDS = {"generation_ms_per_token", "wall_clock_seconds"}
_BOOL_FIELDS = {"cool_down_preceded", "usage_available"}
_NULLABLE = {"None", "none", "unavailable", "null"}


def _coerce(key: str, raw: str):
    if raw in _NULLABLE:
        return None
    if key in _BOOL_FIELDS:
        return raw == "True"
    if key in _INT_FIELDS:
        try:
            return int(raw)
        except ValueError:
            return None
    if key in _FLOAT_FIELDS:
        try:
            return float(raw)
        except ValueError:
            return None
    return raw


def parse_timing_line(line: str) -> dict:
    """Every ``key=value`` pair a real `TIMING`/`TIMING_WINDOW`/`TIMING_CLAIM`
    line carries (exactly as `make_timing_reporter`/`make_window_timing_
    reporter`/`make_claim_timing_reporter` in `extract_claims.py`/
    `match_claims.py` already write them), type-coerced where this module
    knows the field's type. A field the line doesn't carry (e.g.
    `token_count` on a `TIMING_CLAIM` line -- K4 never emits it) is simply
    absent from the result, never defaulted or guessed. Read-only parsing of
    an existing output format -- this is the "recording is not changing"
    half of Task 2, not a change to what K2/K4 compute or print."""
    return {key: _coerce(key, raw) for key, raw in _KV_RE.findall(line)}


# ---------------------------------------------------------------------------
# Recording -- append-only, one JSON object per line. `path` is REQUIRED
# everywhere below: there is no bench-side default that could coincide with
# (or silently drift onto) `ledger.DEFAULT_LEDGER_PATH`.
# ---------------------------------------------------------------------------

def append_entry(entry: dict, path: Path) -> None:
    """As `ledger.append_entry`, but against the wider field set and with no
    optional-path fallback -- a caller that forgets to pass `path` gets a
    `TypeError` at the call site, not a write to the wrong file."""
    missing = [f for f in _REQUIRED_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"bench ledger entry missing required field(s) {missing}: {entry}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = dict(entry)
    stamped["timestamp"] = datetime.now(timezone.utc).isoformat()
    row = {k: stamped.get(k) for k in _ALL_FIELDS}
    row["timestamp"] = stamped["timestamp"]
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def make_bench_ledger_feeder(path: Path, *, stage: str, host: str,
                              config_fingerprint: str,
                              position_in_session: int,
                              prompt_fingerprint: str | None = None):
    """Returns an `on_timing_line`-shaped callback (`curator_control.
    run_stage`'s own contract: `(kind, ms_per_token, line)`) -- drops into
    `execute_with_lock(..., on_timing_line=...)` exactly where `ledger.
    make_ledger_feeder` does for a production run, just pointed at the
    bench's own ledger with the widened row.

    `host`, `config_fingerprint` and `position_in_session` are supplied ONCE
    here, at feeder construction, because they describe the WHOLE bench
    session this feeder is wired into (one candidate model, one config, one
    slot in this repeat's counterbalanced order) -- not something that
    changes window to window or claim to claim. Build a fresh feeder per
    candidate run, not one feeder reused across candidates, or every row
    would carry the first candidate's config/position regardless of which
    model actually produced it.

    `prompt_fingerprint`, if omitted, is computed once here via
    `extract_claims.prompt_fingerprint()` -- calling the existing function,
    never re-deriving the hash a second way.

    A line with no `generation_ms_per_token` (a window/claim whose call
    failed or whose usage wasn't available) is not written -- same "absence
    in, absence out" discipline as `ledger.record_from_timing`. Task 3's
    failure taxonomy is a SEPARATE record, not a ledger row with a missing
    number standing in for it."""
    from chronicler.pipeline import extract_claims

    fp = prompt_fingerprint if prompt_fingerprint is not None else extract_claims.prompt_fingerprint()

    def feed(kind: str | None, ms_per_token: float | None, line: str) -> None:
        if kind not in ("window", "claim") or ms_per_token is None:
            return
        parsed = parse_timing_line(line)
        model_id = parsed.get("model_id")
        cool_down_preceded = parsed.get("cool_down_preceded")
        if model_id is None or cool_down_preceded is None:
            return
        entry = {
            "model_id": model_id, "stage": stage,
            "cool_down_preceded": bool(cool_down_preceded),
            "generation_ms_per_token": float(ms_per_token),
            "prompt_fingerprint": fp,
            "config_fingerprint": config_fingerprint,
            "host": host,
            "position_in_session": position_in_session,
            "kind": kind,
            "time_to_first_token_ms": None,  # not implemented this round -- see module docstring
        }
        for key in ("conversation_id", "project_id", "window_index", "windows_total",
                    "usage_available", "prompt_tokens", "completion_tokens",
                    "token_count", "wall_clock_seconds"):
            if key in parsed:
                entry[key] = parsed[key]
        append_entry(entry, path)

    return feed


def load_entries(path: Path) -> list[dict]:
    """As `ledger.load_entries` -- absent file is `[]`, a corrupt line is
    skipped rather than fatal to the whole read."""
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
# Summarising -- partitioned on (model_id, stage, cool_down_preceded,
# config_fingerprint, prompt_fingerprint), per the brief's own words: "The
# comparable unit is (model, config, prompt), not model ... so mixed
# configurations become visible rather than silently pooled."
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchSummary:
    model_id: str
    stage: str
    cool_down_preceded: bool
    config_fingerprint: str
    prompt_fingerprint: str
    n: int
    median_ms_per_token: float
    p25_ms_per_token: float
    p75_ms_per_token: float
    min_ms_per_token: float
    max_ms_per_token: float
    median_wall_clock_seconds: float | None
    n_wall_clock: int


def _percentiles(values: list[float]) -> tuple[float, float]:
    n = len(values)
    p25_idx = int(round(0.25 * (n - 1)))
    p75_idx = int(round(0.75 * (n - 1)))
    return values[p25_idx], values[p75_idx]


def summarize(entries: list[dict], *, model_id: str, stage: str,
              cool_down_preceded: bool, config_fingerprint: str,
              prompt_fingerprint: str) -> BenchSummary | None:
    """`None` when nothing matches this exact 5-way filter -- one more axis
    than `ledger.summarize`'s 3-way filter (adds `config_fingerprint` and
    `prompt_fingerprint`), because a bench comparison across configs or
    prompt versions pooled together is exactly the silent mixing Task 2 was
    written to prevent."""
    matched = [
        e for e in entries
        if e.get("model_id") == model_id and e.get("stage") == stage
        and e.get("cool_down_preceded") == cool_down_preceded
        and e.get("config_fingerprint") == config_fingerprint
        and e.get("prompt_fingerprint") == prompt_fingerprint
    ]
    values = sorted(e["generation_ms_per_token"] for e in matched)
    if not values:
        return None
    n = len(values)
    p25, p75 = _percentiles(values)

    wall = sorted(e["wall_clock_seconds"] for e in matched
                  if e.get("wall_clock_seconds") is not None)
    median_wall = statistics.median(wall) if wall else None

    return BenchSummary(
        model_id=model_id, stage=stage, cool_down_preceded=cool_down_preceded,
        config_fingerprint=config_fingerprint, prompt_fingerprint=prompt_fingerprint,
        n=n,
        median_ms_per_token=statistics.median(values),
        p25_ms_per_token=p25, p75_ms_per_token=p75,
        min_ms_per_token=values[0], max_ms_per_token=values[-1],
        median_wall_clock_seconds=median_wall, n_wall_clock=len(wall),
    )


def known_configurations(entries: list[dict]) -> list[tuple[str, str, str]]:
    """Every distinct `(model_id, config_fingerprint, prompt_fingerprint)`
    triple this ledger has ever recorded -- what a report iterates to find
    every comparable population without needing to already know they exist.
    Sorted for deterministic output."""
    return sorted({
        (e["model_id"], e["config_fingerprint"], e["prompt_fingerprint"])
        for e in entries
        if e.get("model_id") and e.get("config_fingerprint") and e.get("prompt_fingerprint")
    })
