"""ledger.py -- Task 2, COWORK_BRIEF_conductor_governor.md.

The calibration ledger: an append-only record of `generation_ms_per_token`
observations, fed by Task 1's timing records (K2's per-window, K4's
per-claim, or `curator_control.run_stage`'s streamed `on_timing_line`
callback -- all three already carry the exact fields this module needs).

**Throughput per model, in the finest unit available, normalised by size.**
Seconds-per-conversation is not comparable across conversations of
different sizes; `generation_ms_per_token` already is (Addendum 2's whole
point). This module does nothing to that number except store it and
summarise it.

**Partitioned on the cool-down flag, always.** A post-gap unit paid a JIT
reload cost the rest of its population didn't -- merging the two inflates
the spread and hides the reload cost that is worth knowing separately
(Task 1 item 2's whole reason for existing). Every read here takes
`cool_down_preceded` as part of its filter, never averages across it
silently.

**Report the spread, not a mean alone.** A wide error bar is a fact about
the estimate; Task 4's planner has to carry it, not have it hidden by a
single number that looks more confident than the data supports.

**No measurements for the selected model → no estimate.** `summarize`
returns `None`, plainly, when nothing matches the filter -- the caller
(Task 4's `build_plan`, ultimately) is expected to say so and offer an
unbudgeted ordering instead, never fabricate a number. This is the same
discipline `governor.py` and `planner.py` already apply to a missing
measurement, carried through to where those measurements actually live.

Stdlib only. Plain functions over a JSONL file -- no database, matching the
append-only, one-record-per-line shape this repo already uses for
`--timing-log`/`--window-timing-log`/`--claim-timing-log`.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from l5gntools.common import DATA_DIR

DEFAULT_LEDGER_PATH: Path = DATA_DIR / "knowledge_curator" / "calibration_ledger.jsonl"

#: The only fields a ledger entry carries. Anything else in a source timing
#: record (window_index, token_count, project_id, ...) is provenance for
#: THAT record, not calibration data this module needs to remember.
_ENTRY_FIELDS = ("model_id", "stage", "cool_down_preceded", "generation_ms_per_token")


# ---------------------------------------------------------------------------
# Recording -- append-only, one JSON object per line.
# ---------------------------------------------------------------------------

def record_from_timing(timing: dict, *, stage: str) -> dict | None:
    """Turn a K2/K4 timing record (a `TIMING_WINDOW`/`TIMING_CLAIM` dict, as
    `make_window_timing_reporter`/`make_claim_timing_reporter` produce, or
    the same shape read back from a `--window-timing-log`/`--claim-timing-
    log` JSONL file) into a ledger entry -- or `None` if the record's
    `generation_ms_per_token` is absent. **Never estimates a missing
    figure** -- absence in, absence out, the record is simply not written.

    `stage` is supplied by the caller (`"K2"` or `"K4"`) rather than
    inferred from the record's shape, because the timing record itself
    doesn't carry it -- K2/K4 don't know their own stage key, only
    `curator_control.STAGE_TABLE` does."""
    ms = timing.get("generation_ms_per_token")
    if ms is None:
        return None
    model_id = timing.get("model_id")
    cool_down_preceded = timing.get("cool_down_preceded")
    if model_id is None or cool_down_preceded is None:
        return None
    return {
        "model_id": model_id, "stage": stage,
        "cool_down_preceded": bool(cool_down_preceded),
        "generation_ms_per_token": float(ms),
    }


def append_entry(entry: dict, path: Path | None = None) -> None:
    """One JSON line, appended -- never rewrites, never truncates. Missing
    parent directories are created; a malformed `entry` (missing a required
    field) is refused loudly rather than written half-formed."""
    missing = [f for f in _ENTRY_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"ledger entry missing required field(s) {missing}: {entry}")
    p = path or DEFAULT_LEDGER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    stamped = dict(entry)
    stamped["timestamp"] = datetime.now(timezone.utc).isoformat()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({k: stamped[k] for k in (*_ENTRY_FIELDS, "timestamp")}) + "\n")


def make_ledger_feeder(path: Path | None = None, *, stage: str):
    """Returns an `on_timing_line`-shaped callback (`curator_control.
    run_stage`'s own contract: `(kind, ms_per_token, line)`) that appends a
    ledger entry for every window/claim line carrying a real measurement,
    and does nothing for a line with no measurement or no timing content at
    all. Wire it straight into `execute_with_lock(..., on_timing_line=...)`
    to feed the ledger live from a real run -- purely additive, changes
    nothing about the run itself."""
    p = path or DEFAULT_LEDGER_PATH

    def feed(kind: str | None, ms_per_token: float | None, line: str) -> None:
        if kind not in ("window", "claim") or ms_per_token is None:
            return
        # `line` carries model_id/cool_down_preceded too, in the same
        # `key=value` shape `make_window_timing_reporter`/`make_claim_
        # timing_reporter` write -- extracted directly rather than parsing
        # the whole line into a dict, since only these two fields are
        # needed here. This module stays pipeline-tier (stdlib +
        # l5gntools only) and does not import `chronicler.review` --
        # dependency direction runs app -> pipeline, never back.
        model_m = _FIELD_RE("model_id").search(line)
        cdp_m = _FIELD_RE("cool_down_preceded").search(line)
        if model_m is None or cdp_m is None:
            return
        append_entry({
            "model_id": model_m.group(1), "stage": stage,
            "cool_down_preceded": cdp_m.group(1) == "True",
            "generation_ms_per_token": ms_per_token,
        }, path=p)

    return feed


def _FIELD_RE(name: str):
    import re
    return re.compile(rf"\b{re.escape(name)}=(\S+)")


def load_entries(path: Path | None = None) -> list[dict]:
    """Every entry, in file order. An absent or empty ledger is `[]`, never
    an error -- day one's normal state (nothing measured yet)."""
    p = path or DEFAULT_LEDGER_PATH
    if not p.is_file():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a corrupt line is skipped, never crashes the whole read
    return out


# ---------------------------------------------------------------------------
# Summarising -- spread, not a mean alone; None when there's nothing to say.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalibrationSummary:
    model_id: str
    stage: str
    cool_down_preceded: bool
    n: int
    median_ms_per_token: float
    p25_ms_per_token: float
    p75_ms_per_token: float
    min_ms_per_token: float
    max_ms_per_token: float


def summarize(entries: list[dict], *, model_id: str, stage: str,
              cool_down_preceded: bool) -> CalibrationSummary | None:
    """`None` when nothing matches this exact `(model_id, stage,
    cool_down_preceded)` filter -- "no measurements for the selected model"
    is a fact to report plainly, per the brief's own words, never papered
    over with a figure borrowed from a different model, stage, or the
    other side of the cool-down partition."""
    values = sorted(
        e["generation_ms_per_token"] for e in entries
        if e.get("model_id") == model_id and e.get("stage") == stage
        and e.get("cool_down_preceded") == cool_down_preceded
    )
    if not values:
        return None
    n = len(values)
    # Nearest-rank percentile over the sorted, 0-indexed list -- simple and
    # exact at the sample sizes this ledger will realistically hold (tens to
    # low thousands of units), not interpolated; no external stats library.
    p25_idx = int(round(0.25 * (n - 1)))
    p75_idx = int(round(0.75 * (n - 1)))
    return CalibrationSummary(
        model_id=model_id, stage=stage, cool_down_preceded=cool_down_preceded, n=n,
        median_ms_per_token=statistics.median(values),
        p25_ms_per_token=values[p25_idx],
        p75_ms_per_token=values[p75_idx],
        min_ms_per_token=values[0],
        max_ms_per_token=values[-1],
    )


def known_models(entries: list[dict]) -> list[str]:
    """Every distinct `model_id` this ledger has ever recorded a
    measurement for -- what a caller iterates to build a full calibration
    report, without needing to already know which models exist."""
    return sorted({e["model_id"] for e in entries if e.get("model_id")})
