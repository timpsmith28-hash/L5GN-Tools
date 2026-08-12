"""governor.py -- Task 3, COWORK_BRIEF_conductor_governor.md.

Closes the conductor's pacing loop on THROUGHPUT (generation ms/token),
never temperature. `10280L`, the only machine the Curator runs on (0032),
exposes no temperature reading at all -- every route was tried and closed
(see `docs/RUNBOOK_conductor_thermal_trial.md`'s sensor survey). This
module consumes the SAME per-window (K2) / per-claim (K4) timing records
Task 1 already emits (`generation_ms_per_token`, Addendum 2's fixed
instrument) -- it adds no new measurement, just a decision on top of one
that already exists.

**The honesty requirement is the point of this module (0031).** Throughput
decays for reasons other than heat: a longer unit, a larger corpus, another
process competing, a model swap. Every message this module produces reports
an OBSERVATION and an ACTION, never a diagnosis -- "throughput fell to 61%
of this run's baseline over the last four units; pausing 60s", never
"thermal throttling detected". `_FORBIDDEN_WORDS` below exists so a test can
prove this mechanically rather than by review alone.

Two evidence-backed decisions this module does NOT relitigate (real-rig
data, `docs/COWORK_REPORT_conductor_governor.md` Addendum 3):

- **The pause cap is load-bearing, not defensive.** A governor that can
  wait forever is a hang -- see Addendum 2's 10 August finding (a 36% drop
  that never recovered in 11.5 hours).
- **The baseline is per-run, established from THIS run's own opening
  units, never from a ledger.** A ledger baseline would misattribute a
  persistent config-state change (the KV-cache-offload finding) to every
  later run forever.
- **The default profile leads with the token dials, cool-down secondary**
  -- Addendum 3's real `--cool-down 90` data showed no measurable benefit
  (per-conversation ratios 0.90-1.06 against baseline); the token-dial
  reduction (Run 5, first pass) was the one lever with a demonstrated
  effect. The reverse of the original brief's framing, now evidence-backed.

Stdlib only, plain functions/dataclasses a tester calls directly with a
temp directory -- no live process, no live LM Studio, no clock. Same
posture as `chronicler.review.curator_control` and for the same reason
(INTENT: guarantees are structural). This module stays in the pipeline
tier (`chronicler.pipeline`) and does not import the app tier
(`chronicler.review`) -- the dependency runs the other way (DECISIONS
0034 clause 3's direction, applied to this pair even though the auditor
that enforces it only scans `l5gntools/`).
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from l5gntools import config as l5gn_config

# ---------------------------------------------------------------------------
# Profiles -- named, machine-scoped, config/local.json under this hostname.
# ---------------------------------------------------------------------------

DEFAULT_PROFILE_NAME = "default"

#: Every key a profile must carry. `get_profile` always returns a dict with
#: all of these -- a partially-specified stored profile is layered ON TOP of
#: this, never used bare, so a config file written before a new key existed
#: still produces a complete profile.
DEFAULT_PROFILE: dict = {
    "max_window_tokens": 4000,     # primary lever (Addendum 3): Run 5 halved
    "batch_target_tokens": 3000,   #   the un-governed defaults and showed a
                                    #   real improvement; cool-down alone did not.
    "cool_down_seconds": 30.0,     # secondary lever -- kept modest, not relied on
    "baseline_units": 4,           # units to establish this run's own baseline
    "rolling_window": 4,           # units in the rolling-median decay detector
    "pause_threshold": 0.75,       # pause when rolling median < 75% of baseline
    "recovery_threshold": 0.90,    # resume when rolling median >= 90% of baseline
    "pause_seconds": 60.0,         # length of one pause
    "pause_cap": 3,                # consecutive pauses before proceeding anyway
}


def _local_json_path() -> Path:
    return l5gn_config.CONFIG_DIR / "local.json"


def _read_local_json(path: Path | None = None) -> dict:
    p = path or _local_json_path()
    if not p.exists() or p.stat().st_size == 0:
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def get_profile(name: str = DEFAULT_PROFILE_NAME, host: str | None = None,
                 path: Path | None = None) -> dict:
    """This machine's named governor profile, layered over
    :data:`DEFAULT_PROFILE` so a partially-specified stored profile (or none
    at all -- day one's normal state) still returns every key. `host`
    defaults to this machine's own hostname; profiles describe one rig and
    nothing else (0036)."""
    host = host or l5gn_config.hostname()
    data = _read_local_json(path)
    stored = ((data.get(host) or {}).get("governor_profiles") or {}).get(name)
    profile = dict(DEFAULT_PROFILE)
    if stored:
        profile.update(stored)
    return profile


def set_profile(name: str, profile: dict, host: str | None = None,
                 path: Path | None = None) -> dict:
    """Record one named profile under this hostname, preserving every other
    key already in `config/local.json` -- read-modify-write, never a blind
    overwrite (same discipline as `curator_control.set_curator_model`).
    Stores exactly what's given, unmerged; `get_profile` is what layers it
    over the defaults on read."""
    host = host or l5gn_config.hostname()
    p = path or _local_json_path()
    data = _read_local_json(p)
    host_entry = dict(data.get(host) or {})
    profiles = dict(host_entry.get("governor_profiles") or {})
    profiles[name] = dict(profile)
    host_entry["governor_profiles"] = profiles
    data[host] = host_entry
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return {"host": host, "name": name}


# ---------------------------------------------------------------------------
# The decision loop -- baseline from this run's own opening units, a
# rolling-median decay detector, pause/resume/cap, observation-only
# messages. `classify_outcome`'s four states are untouched by this module
# (COWORK_BRIEF_conductor_governor.md: "cooling is a conductor state, never
# a stage state") -- callers track pause state alongside a stage outcome,
# never inside one.
# ---------------------------------------------------------------------------

_FORBIDDEN_WORDS = ("thermal", "overheat", "throttl")  # substrings; catches
                                                          # "throttling"/"throttle" too


@dataclass
class GovernorState:
    """Mutated in place by `observe` -- a plain object a caller keeps across
    a run's whole timing stream, never persisted (0037's "no new source of
    truth about progress": this is live pacing state, not a record of what
    ran)."""
    profile: dict
    baseline: float | None = None
    baseline_samples: list = field(default_factory=list)
    recent: list = field(default_factory=list)
    paused: bool = False
    pause_count: int = 0
    cap_reached: bool = False


@dataclass
class GovernorAction:
    action: str  # "measuring" | "baseline_set" | "observing" | "none" | "pause" | "resume" | "cap_reached"
    message: str
    pause_seconds: float | None = None


def new_governor(profile: dict | None = None) -> GovernorState:
    return GovernorState(profile=dict(profile or DEFAULT_PROFILE))


def observe(state: GovernorState, ms_per_token: float | None) -> GovernorAction:
    """One call per measured unit -- a K2 window's or K4 claim's
    `generation_ms_per_token`. `None` (usage was unavailable for that unit,
    Addendum 2's `usage_available=False` case) is skipped entirely: not
    counted toward the baseline, not counted toward the rolling window,
    never treated as a zero or an estimate -- the module never measures
    what it did not measure.

    Returns the action to take. The caller is responsible for actually
    sleeping `pause_seconds` on a `"pause"` action -- this function has no
    clock and no side effect beyond mutating `state`, exactly the shape
    `sleep_fn` injection uses elsewhere in this codebase."""
    if ms_per_token is None:
        return GovernorAction("none", "unit not measured (usage unavailable) -- skipped")

    profile = state.profile

    if state.baseline is None:
        state.baseline_samples.append(ms_per_token)
        n, want = len(state.baseline_samples), profile["baseline_units"]
        if n < want:
            return GovernorAction("measuring", f"establishing baseline ({n}/{want} units)")
        state.baseline = statistics.median(state.baseline_samples)
        return GovernorAction("baseline_set",
                               f"baseline established at {state.baseline:.1f}ms/token "
                               f"over {n} units")

    state.recent.append(ms_per_token)
    if len(state.recent) > profile["rolling_window"]:
        state.recent.pop(0)
    if len(state.recent) < profile["rolling_window"]:
        return GovernorAction("observing",
                               f"observing ({len(state.recent)}/{profile['rolling_window']} "
                               f"units in window)")

    rolling = statistics.median(state.recent)
    ratio = (rolling / state.baseline) if state.baseline else 1.0
    pct = f"{ratio * 100:.0f}%"
    n = len(state.recent)

    if state.paused:
        if ratio >= profile["recovery_threshold"]:
            state.paused = False
            state.pause_count = 0
            state.cap_reached = False
            return GovernorAction("resume",
                                   f"throughput recovered to {pct} of this run's baseline "
                                   f"over the last {n} units")
        if state.pause_count >= profile["pause_cap"]:
            if not state.cap_reached:
                state.cap_reached = True
                return GovernorAction("cap_reached",
                                       f"throughput still at {pct} of baseline after "
                                       f"{state.pause_count} pause(s) -- cap reached, "
                                       f"proceeding anyway")
            return GovernorAction("none",
                                   f"cap already reached -- proceeding; throughput at "
                                   f"{pct} of baseline")
        state.pause_count += 1
        return GovernorAction("pause",
                               f"throughput still at {pct} of this run's baseline over "
                               f"the last {n} units; pausing {profile['pause_seconds']:.0f}s "
                               f"again ({state.pause_count}/{profile['pause_cap']})",
                               pause_seconds=profile["pause_seconds"])

    if ratio < profile["pause_threshold"]:
        state.paused = True
        state.pause_count = 1
        return GovernorAction("pause",
                               f"throughput fell to {pct} of this run's baseline over "
                               f"the last {n} units; pausing {profile['pause_seconds']:.0f}s",
                               pause_seconds=profile["pause_seconds"])

    return GovernorAction("none", f"throughput at {pct} of this run's baseline -- within range")
