"""curator_control.py -- Task 3, COWORK_BRIEF_curator_tab.md.

The control strip's logic: preconditions probed before anything offers to
run, per-stage model selection (K2/K4 confirm only -- everything else is
deterministic and gets no selector), real cache-invalidation counts before a
model change is accepted, a hard execution allowlist, and a real single-run
lock.

Nothing here is embedded in a route handler (standing rule) -- every check,
every count, the lock, and the allowlist are plain functions a tester can
call directly with a temp directory, never touching a live process or a live
LM Studio.

**The execution allowlist is the whole security story of this task.**
:data:`STAGE_TABLE` is the one place a stage key is declared; the execute
route (wired in app.py) validates against ``set(STAGE_TABLE)`` and nothing
else ever reaches the caller -- no argv, no path, no flag is accepted from
outside this module for what actually runs.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from l5gntools import config as l5gn_config

from .curator_data import (CURATOR_DATA_DIR, RATIFIED_MAP_PATH,
                            ratified_map_path_for_estate, ratified_row_count)

_PIPE = Path(__file__).resolve().parents[2] / "chronicler" / "pipeline"

#: The hard allowlist. Each stage: its script (run as a subprocess, exactly
#: as run.py's own `_run_chronicler` pattern does for the ingest chain --
#: never a caller-supplied command), whether it calls a model at all, and
#: the fixed argv template. `{model}` / `{endpoint}` / `{temperature}` are
#: filled from config/local.json (validated, server-side) -- never from an
#: execute request, which carries only a stage key.
STAGE_TABLE: dict[str, dict] = {
    "K0": {"label": "K0 -- bootstrap conversation map", "script": "bootstrap_conversation_map.py",
           "deterministic": True, "model_stage": None,
           "argv": lambda cfg: ["--out", str(CURATOR_DATA_DIR / "candidate_map.tsv")]},
    "K1": {"label": "K1 -- knowledge index", "script": "knowledge_index.py",
           "deterministic": True, "model_stage": None,
           "argv": lambda cfg: ["--out", str(CURATOR_DATA_DIR / "knowledge_index.json")]},
    "K2": {"label": "K2 -- extract claims", "script": "extract_claims.py",
           "deterministic": False, "model_stage": "extraction",
           "argv": lambda cfg: (["--endpoint", chat_completions_endpoint(cfg.get("endpoint") or DEFAULT_ENDPOINT),
                                  "--model", cfg["K2"]] if cfg.get("K2") else None)},
    "K3": {"label": "K3 -- corpus index", "script": "corpus_index.py",
           "deterministic": True, "model_stage": None,
           "argv": lambda cfg: []},
    "K4": {"label": "K4 -- match claims", "script": "match_claims.py",
           "deterministic": False, "model_stage": "confirm",
           "argv": lambda cfg: (["--endpoint", chat_completions_endpoint(cfg.get("endpoint") or DEFAULT_ENDPOINT),
                                  "--model", cfg["K4"]] if cfg.get("K4") else None)},
    "K5": {"label": "K5 -- compile report", "script": "compile_report.py",
           "deterministic": True, "model_stage": None,
           "argv": lambda cfg: []},
}
EXECUTION_ALLOWLIST: frozenset[str] = frozenset(STAGE_TABLE)

#: Stages whose script reads the ratified map directly, and so must be told
#: THIS machine's estate-resolved path explicitly (DECISIONS 0044 clause 4)
#: rather than falling back to each script's own hardcoded work-estate
#: default. K0 produces the CANDIDATE map and does not read the ratified
#: one; K3/K5 don't touch it either.
MAP_SCOPED_STAGES: frozenset[str] = frozenset({"K1", "K4"})

#: Stages that get a model selector at all (Task 3: "only for stages that
#: call a model"). K0/K1/K3/K5 are deterministic and get none.
MODEL_SELECTABLE_STAGES: tuple[str, ...] = ("K2", "K4")

#: Stages that accept a `--project` filter -- exactly the two that call a
#: model AND already ship their own `--project` CLI flag (extract_claims.py
#: / match_claims.py, `action="append"`, scoped-merge on write). K0/K1/K3/K5
#: are deterministic, whole-corpus builds with no `--project` flag of their
#: own; a `project_id` given to `run_stage` for one of those is silently
#: not applied here, never passed through as an argv this repo's own CLI
#: parsers don't accept. The conductor's execution loop (COWORK_BRIEF_
#: conductor_governor.md, the execution-loop task) is what actually needs
#: this -- a `PlanStep` names one project, and running the WHOLE corpus for
#: every step in a multi-project plan would silently duplicate work and
#: defeat the point of having a plan at all.
PROJECT_SCOPED_STAGES: frozenset[str] = frozenset({"K2", "K4"})

DEFAULT_ENDPOINT = "http://localhost:1234"  # chat/completions + /v1/models both hang off this


def chat_completions_endpoint(endpoint: str) -> str:
    """K2/extract_claims.py and K4/match_claims.py both POST to a literal
    ``--endpoint`` string with no path of their own appended (see
    ``call_lmstudio`` in extract_claims.py) -- their own CLI default is the
    full ``.../v1/chat/completions`` URL. The control strip's ``DEFAULT_ENDPOINT``
    and ``config/local.json``'s stored ``endpoint`` are both base URLs (the
    same base ``probe_lm_studio`` appends ``/v1/models`` to), so it must be
    turned into the full chat-completions URL here before being handed to
    either stage -- passing the base straight through POSTs to ``/`` and LM
    Studio answers "Unexpected endpoint or method"."""
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/v1/chat/completions"):
        return endpoint
    return endpoint + "/v1/chat/completions"

K2_CACHE_PATH = CURATOR_DATA_DIR / "claims_cache.json"
K4_CACHE_PATH = CURATOR_DATA_DIR / "matches_cache.json"
K2_CLAIMS_PATH = CURATOR_DATA_DIR / "claims.json"

LOCK_PATH = CURATOR_DATA_DIR / ".curator_run.lock"


# ---------------------------------------------------------------------------
# Preflight -- probed and shown before anything offers to run
# ---------------------------------------------------------------------------

def probe_lm_studio(endpoint: str = DEFAULT_ENDPOINT, timeout: float = 3.0) -> dict:
    """Reachability + the loaded model list, in one honest round-trip against
    ``/v1/models``. Never raises -- a probe failure is a fact to report, not
    an exception to propagate into a 500."""
    url = endpoint.rstrip("/") + "/v1/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        models = [m.get("id") for m in body.get("data", []) if isinstance(m, dict) and m.get("id")]
        return {"reachable": True, "endpoint": endpoint, "models": models, "error": None}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"reachable": False, "endpoint": endpoint, "models": [],
                "error": f"{type(exc).__name__}: {exc}"}


def stage_output_exists(curator) -> dict[str, bool]:
    """Which stage outputs already exist -- thin wrapper over curator_data's
    own per-stage state, so the control strip and the header agree by
    construction rather than by two modules independently checking disk."""
    states = curator.stage_states()
    return {k: v.exists for k, v in states.items()}


def preflight(curator, endpoint: str = DEFAULT_ENDPOINT) -> dict:
    """Everything Task 3 requires probed before a run is offered: LM Studio
    reachability + round trip, the loaded model list, whether the map is
    ratified, which stage outputs exist. This is a read: it changes nothing
    and it is safe to call on every page load."""
    lm = probe_lm_studio(endpoint)
    ratified = ratified_row_count(curator.ratified_map_path)
    return {
        "lm_studio": lm,
        "map_ratified": ratified > 0,
        "ratified_row_count": ratified,
        "stage_outputs_exist": stage_output_exists(curator),
        "lock": lock_status(),
    }


# ---------------------------------------------------------------------------
# K4's shortlist step -- a capability display, never a model selector
# (match_claims.similarity == difflib.SequenceMatcher.ratio(); no embedding
# path exists in the code today, so this states that rather than offering a
# choice that isn't real).
# ---------------------------------------------------------------------------

def shortlist_capability() -> dict:
    return {
        "stage": "K4-shortlist",
        "method": "stdlib difflib.SequenceMatcher(None, a, b).ratio() over "
                  "casefolded text -- a sequence-similarity score, not an "
                  "embedding.",
        "selectable": False,
        "note": "No embedding path exists in match_claims.py today. If one is "
                "added, this display changes to name it; until then a model "
                "selector here would offer a choice that does not exist.",
    }


# ---------------------------------------------------------------------------
# Model selection -- config/local.json, keyed by hostname, never travels
# ---------------------------------------------------------------------------

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


def get_curator_models(host: str | None = None, path: Path | None = None) -> dict:
    """This machine's stored per-stage model selections. Empty dict if none
    have ever been recorded here -- absence, not a default guess."""
    host = host or l5gn_config.hostname()
    data = _read_local_json(path)
    return dict((data.get(host) or {}).get("curator_models") or {})


def set_curator_model(stage: str, model_id: str, host: str | None = None,
                       path: Path | None = None) -> dict:
    """Record one stage's model selection under this hostname, preserving
    every other key already in ``config/local.json`` -- a read-modify-write,
    never a blind overwrite of the whole file. ``config/local.json`` is
    gitignored (see .gitignore) -- this never writes anything that travels."""
    if stage not in MODEL_SELECTABLE_STAGES:
        raise ValueError(
            f"{stage!r} is not a model-selectable stage -- only "
            f"{MODEL_SELECTABLE_STAGES} take a selection. K0/K1/K3/K5 are "
            "deterministic and offer no selector.")
    host = host or l5gn_config.hostname()
    p = path or _local_json_path()
    data = _read_local_json(p)
    host_entry = dict(data.get(host) or {})
    models = dict(host_entry.get("curator_models") or {})
    models[stage] = model_id
    host_entry["curator_models"] = models
    data[host] = host_entry
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return {"host": host, "stage": stage, "model_id": model_id}


# ---------------------------------------------------------------------------
# Cache-invalidation counts -- real numbers, read before a change is accepted
# ---------------------------------------------------------------------------

def _cache_entry_count(cache_path: Path) -> int:
    """Number of per-conversation/per-claim decision entries in a Curator
    cache file, excluding meta keys (`corpus_fingerprint`)."""
    if not cache_path.is_file():
        return 0
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if "results" in data and isinstance(data["results"], dict):
        return len(data["results"])  # K4 shape: {"corpus_fingerprint": ..., "results": {...}}
    return len([k for k in data if k != "corpus_fingerprint"])


def k2_model_change_impact(cache_path: Path | None = None) -> dict:
    """K2's per-conversation cache entries carry no per-entry model
    attribution (`_cache_entry` in extract_claims.py stores `sources` --
    file identity -- and the result, never the model that produced it). A
    model change therefore cannot be selectively invalidated: the honest
    count is that every cached conversation is suspect, none are provably
    untouched. Recorded here plainly rather than fabricating a finer number
    the cache does not support."""
    n = _cache_entry_count(cache_path or K2_CACHE_PATH)
    return {
        "stage": "K2", "cached_conversations": n, "claims_untouched": 0,
        "detail": (f"changing K2's model invalidates all {n} cached conversation "
                   f"extraction(s) and everything derived from them -- the cache "
                   "carries no per-entry model attribution, so none can be "
                   "shown as provably untouched.")
                  if n else "no cached extractions on disk -- nothing to invalidate.",
    }


def k4_model_change_impact(cache_path: Path | None = None,
                            claims_path: Path | None = None) -> dict:
    """K4's confirm cache is separate from K2's claims: changing K4's model
    invalidates cached verdicts only; the claims themselves (K2's output,
    read from claims.json) are untouched -- exactly the split the brief's
    example number states."""
    n_verdicts = _cache_entry_count(cache_path or K4_CACHE_PATH)
    cpath = claims_path or K2_CLAIMS_PATH
    n_claims = 0
    if cpath.is_file():
        try:
            data = json.loads(cpath.read_text(encoding="utf-8"))
            n_claims = int(data.get("claims_extracted") or 0)
        except (OSError, ValueError):
            n_claims = 0
    return {
        "stage": "K4", "cached_verdicts": n_verdicts, "claims_untouched": n_claims,
        "detail": (f"this invalidates {n_verdicts} cached verdict(s); "
                   f"{n_claims} claim(s) are untouched."),
    }


# ---------------------------------------------------------------------------
# The lock -- a real file, not a disabled button. COWORK_BRIEF_conductor_
# governor.md Task 5': "the lock must survive a multi-hour hold" -- the
# original O_CREAT|O_EXCL scheme (an unreadable lock counts as locked,
# correct for a five-minute stage) is a trap for an overnight run killed by
# a crash or reboot, with nothing to ever tell it apart from one still
# genuinely running. A pid + a heartbeat give a caller enough to make that
# call themselves -- staleness is REPORTED here, never acted on
# automatically; breaking a lock is always `break_lock`, called explicitly.
# ---------------------------------------------------------------------------

#: No heartbeat update in this long -> the lock is reported stale. A live
#: `execute_with_lock` run heartbeats far more often than this (every
#: streamed line -- seconds, not minutes) so a genuinely running stage never
#: approaches it; only a crashed/killed process leaves a heartbeat this old.
STALE_HEARTBEAT_SECONDS = 120.0


def _pid_alive(pid: int | None) -> bool | None:
    """Best-effort, cross-platform liveness check. ``True``/``False`` when
    it can tell, ``None`` when it genuinely cannot (no pid recorded, or a
    platform/permission situation that makes the question unanswerable) --
    staleness never depends SOLELY on this, because ``None`` must never be
    silently treated as either alive or dead."""
    if pid is None:
        return None
    try:
        if sys.platform == "win32":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, just not ours to signal -- definitely alive
    except OSError:
        return None


def lock_status(lock_path: Path | None = None, *, stale_after: float = STALE_HEARTBEAT_SECONDS,
                 now: float | None = None) -> dict:
    """Reports what's held and whether it looks stale -- never breaks
    anything itself (0031's discipline applied to the lock: an observation,
    not a verdict acted on automatically)."""
    p = lock_path or LOCK_PATH
    if not p.is_file():
        return {"locked": False}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"locked": True, "stage": None, "started_at": None, "pid": None,
                "heartbeat_at": None, "heartbeat_age_seconds": None, "stale": True,
                "stale_reasons": ["lock file present but unreadable"]}
    now = now if now is not None else time.time()
    heartbeat_at = data.get("heartbeat_at")
    hb_age = (now - heartbeat_at) if isinstance(heartbeat_at, (int, float)) else None
    pid = data.get("pid")
    alive = _pid_alive(pid)
    reasons: list[str] = []
    if hb_age is not None and hb_age > stale_after:
        reasons.append(f"no heartbeat in {hb_age:.0f}s (limit {stale_after:.0f}s)")
    if alive is False:
        reasons.append(f"pid {pid} is not running")
    return {"locked": True, "stage": data.get("stage"), "started_at": data.get("started_at"),
            "pid": pid, "heartbeat_at": heartbeat_at, "heartbeat_age_seconds": hb_age,
            "stale": bool(reasons), "stale_reasons": reasons}


def acquire_lock(stage: str, lock_path: Path | None = None) -> dict:
    """Real single-run lock: an exclusive file create (`O_CREAT|O_EXCL`), not
    a disabled button and not an in-memory flag another worker process
    wouldn't see. A second request while one is held is refused with what is
    running and when it started -- never queued, never silently dropped, and
    NEVER auto-broken here even if `lock_status` would call it stale --
    staleness is only ever acted on via the explicit `break_lock`."""
    p = lock_path or LOCK_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    now = time.time()
    payload = json.dumps({
        "stage": stage, "started_at": started_at, "pid": os.getpid(), "heartbeat_at": now,
    }, indent=2).encode("utf-8")
    try:
        fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return {"acquired": False, **lock_status(p)}
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return {"acquired": True, "stage": stage}


def heartbeat(lock_path: Path | None = None, *, now: float | None = None) -> bool:
    """Update the held lock's `heartbeat_at`, preserving every other field --
    read-modify-write, never a blind rewrite. Never CREATES a lock; returns
    False (does nothing) if none is held or the file is unreadable, so a
    caller that races a `release_lock` fails safe rather than resurrecting
    a lock nobody holds."""
    p = lock_path or LOCK_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    data["heartbeat_at"] = now if now is not None else time.time()
    try:
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def release_lock(lock_path: Path | None = None) -> None:
    p = lock_path or LOCK_PATH
    try:
        p.unlink()
    except FileNotFoundError:
        pass


def break_lock(reason: str, lock_path: Path | None = None) -> dict:
    """The ONLY sanctioned way a stale lock is ever cleared -- an explicit
    operator action that names what it is breaking, never an automatic
    silent reclaim (COWORK_BRIEF_conductor_governor.md Task 5', a stop
    condition in its own right). `reason` is mandatory: a break with no
    reason is refused outright, so there is always something to point at
    later for "why was this lock cleared." Breaking a lock that isn't
    actually stale is still permitted (an operator's call, not this
    function's to second-guess) -- but the caller is expected to have read
    `lock_status` first; this does not check staleness itself."""
    if not reason or not reason.strip():
        raise ValueError("break_lock requires a non-empty reason -- this is a "
                          "deliberate operator action, never a silent reclaim.")
    p = lock_path or LOCK_PATH
    status = lock_status(p)
    if not status["locked"]:
        return {"broken": False, "reason": reason, "detail": "no lock was held"}
    release_lock(lock_path=p)
    return {"broken": True, "reason": reason, "was": status}


# ---------------------------------------------------------------------------
# Execution -- the hard allowlist, a fixed argv, three-state outcome
# ---------------------------------------------------------------------------

class ExecutionRefused(ValueError):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass
class StageOutcome:
    stage: str
    state: str  # "success" | "failed" | "skipped" | "blocked" -- FOUR states, never a fifth
    detail: str
    returncode: int | None = None
    stdout_tail: str = ""
    #: Cancellation is conductor/orchestration state layered ALONGSIDE the
    #: four existing states, never a fifth one of its own -- a cancelled
    #: run still lands on "blocked" (queued, never started) or "failed"
    #: (in-flight, terminated); this flag is what tells that apart from an
    #: ordinary blocked precondition or a real failure.
    cancelled: bool = False


def classify_outcome(returncode: int | None, stdout: str, stderr: str) -> tuple[str, str]:
    """Map a subprocess result to one of three visually/textually distinct
    states -- never a fourth, never a blend. Mirrors run_pipeline.py's own
    contract for the ingest chain: a clean skip is not a failure, and a
    failure is never rendered as a skip."""
    text = (stdout + "\n" + stderr).lower()
    if returncode is None:
        return "blocked", "did not run (blocked precondition)"
    if returncode == 0 and "skip" in text:
        return "skipped", "no input available"
    if returncode == 0:
        return "success", "completed"
    return "failed", f"exit {returncode}"


class CancelToken:
    """One-shot, thread-safe cancellation flag. Atomic test-and-clear
    (``ForgeEngine._consume_cancel``'s pattern, re-derived -- COWORK_BRIEF_
    conductor_governor.md Addendum's Task 5'), so a cancellation cannot fire
    twice. The SAME token distinguishes queued vs in-flight by nothing more
    than WHEN it's read: ``consume()`` (test-and-clear) before a step ever
    starts means "skip it, it was still queued"; ``is_set()`` (non-consuming
    peek) checked WHILE a step is streaming means "stop it now, it was
    in-flight" -- two different operator intents, the same primitive,
    exactly the distinction an overnight run needs between "stop after this
    step" and "stop right now."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled = False

    def request(self) -> None:
        with self._lock:
            self._cancelled = True

    def consume(self) -> bool:
        with self._lock:
            if self._cancelled:
                self._cancelled = False
                return True
            return False

    def is_set(self) -> bool:
        with self._lock:
            return self._cancelled


# TIMING/TIMING_WINDOW/TIMING_CLAIM lines, exactly as extract_claims.py's/
# match_claims.py's make_*_timing_reporter() write them to stderr.
_TIMING_KIND_RE = re.compile(r"^(TIMING_WINDOW|TIMING_CLAIM|TIMING)\b")
_TIMING_KIND_NAMES = {"TIMING_WINDOW": "window", "TIMING_CLAIM": "claim", "TIMING": "conversation"}
_MS_PER_TOKEN_RE = re.compile(r"generation_ms_per_token=(\S+)")


def _classify_timing_line(line: str) -> str | None:
    m = _TIMING_KIND_RE.match(line)
    return _TIMING_KIND_NAMES[m.group(1)] if m else None


def _parse_ms_per_token(line: str) -> float | None:
    """The line's `generation_ms_per_token` figure, or `None` -- either the
    line marked it literally "unavailable" (Addendum 2's own discipline:
    absent, never estimated) or this isn't a window/claim line at all."""
    m = _MS_PER_TOKEN_RE.search(line)
    if not m or m.group(1) in ("unavailable", "None"):
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _default_popen(argv: list[str], *, cwd: str):
    """stderr merged into stdout (`STDOUT`) -- K2/K4 write their TIMING*
    lines to stderr; merging keeps them in real arrival order against
    stdout on a single stream, which is what makes reading ONE pipe (rather
    than juggling two, with the deadlock risk that brings) safe here."""
    return subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, bufsize=1)


def run_stage(stage: str, *, host: str | None = None, cache_root: Path | None = None,
              project_id: str | None = None, popen_factory=None, on_timing_line=None,
              cancel_token: "CancelToken | None" = None, heartbeat_fn=None) -> StageOutcome:
    """Run exactly one allowlisted stage. ``stage`` is the ONLY thing this
    function accepts that named the work to do -- there is no argv, path, or
    flag parameter here a caller could use to run something else. Model
    stages (K2/K4) resolve their model from ``config/local.json`` themselves;
    a stage with no selection recorded is BLOCKED, never run with a guessed
    default (a model stage's `--model` has no default anywhere in this
    codebase, deliberately -- COWORK_BRIEF_curator_tab.md, "Grounding").

    **Streaming, not buffered to exit.** `subprocess.run(capture_output=True)`
    used to sit here -- it blocks until the process exits and returns
    everything at once, so a multi-hour stage showed nothing until it
    finished: no timings, no progress, no way to tell "paused" from "stuck."
    This spawns via ``popen_factory`` (defaults to `_default_popen`, a thin
    `subprocess.Popen` wrapper) and reads its output line by line AS IT
    ARRIVES -- this is what makes a live governor
    (`chronicler.pipeline.governor`) possible at all, not a UI nicety
    (COWORK_BRIEF_conductor_governor.md Task 5', its own words).

    ``on_timing_line(kind, ms_per_token, line)`` fires for every
    TIMING/TIMING_WINDOW/TIMING_CLAIM line K2/K4 write -- ``kind`` is
    ``"conversation"``/``"window"``/``"claim"``, ``ms_per_token`` is the
    parsed `generation_ms_per_token` figure (`None` if the line marked it
    unavailable). Never fired for any other line. Purely observational --
    whether the caller feeds it into a `governor.GovernorState` or ignores
    it entirely is not this function's concern; it has no notion of
    pausing.

    ``cancel_token``, if given, is checked after every line -- if set
    (`is_set()`, a non-consuming peek), the subprocess is terminated
    (`Popen.terminate()`, cross-platform) and the outcome is marked
    `cancelled=True`. This is the IN-FLIGHT half of cancellation; the
    QUEUED half (skipping a step that hasn't started yet) lives in
    `execute_with_lock`.

    ``heartbeat_fn``, if given, is called after every line -- `execute_with_
    lock` binds this to the held lock's `heartbeat()` automatically, so a
    long-running stage's lock never goes stale while it's genuinely
    streaming output.

    ``project_id``, if given AND ``stage`` is in :data:`PROJECT_SCOPED_STAGES`
    (K2/K4 -- the two that ship their own `--project` flag), is appended as
    `--project {project_id}`, scoping this invocation to that one project
    exactly as the conductor's plan steps mean it to be scoped. Given for
    any other stage, it is silently NOT applied -- K0/K1/K3/K5's own CLI
    parsers have no `--project` flag to accept it, and inventing one here
    would be exactly the kind of caller-supplied-argv path 0037 clause 1
    forbids for this codebase."""
    if stage not in EXECUTION_ALLOWLIST:
        raise ExecutionRefused(
            "not_allowlisted",
            f"{stage!r} is not on the execution allowlist "
            f"({sorted(EXECUTION_ALLOWLIST)}). Refused.")

    spec = STAGE_TABLE[stage]
    cfg = get_curator_models(host)
    argv_extra = spec["argv"](cfg)
    if argv_extra is None:
        return StageOutcome(stage=stage, state="blocked",
                             detail=f"no model selected for {stage} -- set one before running "
                                    "(no default is ever assumed).")
    if stage in MAP_SCOPED_STAGES:
        declared_estate = l5gn_config.machine(host).get("estate")
        try:
            map_path = ratified_map_path_for_estate(declared_estate)
        except ValueError as exc:
            return StageOutcome(stage=stage, state="blocked", detail=str(exc))
        argv_extra = [*argv_extra, "--map", str(map_path)]
    if project_id and stage in PROJECT_SCOPED_STAGES:
        argv_extra = [*argv_extra, "--project", project_id]

    script_path = _PIPE / spec["script"]
    if not script_path.is_file():
        return StageOutcome(stage=stage, state="blocked",
                             detail=f"{spec['script']} not found under {_PIPE}")

    spawn = popen_factory or _default_popen
    proc = spawn([sys.executable, str(script_path), *argv_extra], cwd=str(_PIPE.parent.parent))

    lines: list[str] = []
    cancelled = False
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        lines.append(line)
        kind = _classify_timing_line(line)
        if kind is not None and on_timing_line:
            on_timing_line(kind, _parse_ms_per_token(line), line)
        if heartbeat_fn:
            heartbeat_fn()
        if cancel_token is not None and cancel_token.is_set():
            proc.terminate()
            cancelled = True
            break

    returncode = proc.wait()
    stdout_text = "\n".join(lines)
    if cancelled:
        state, detail = "failed", "cancelled by operator request (in-flight)"
    else:
        state, detail = classify_outcome(returncode, stdout_text, "")
    tail = "\n".join(lines[-10:])
    return StageOutcome(stage=stage, state=state, detail=detail,
                         returncode=returncode, stdout_tail=tail, cancelled=cancelled)


def execute_with_lock(stage: str, lock_path: Path | None = None, *,
                       cancel_token: "CancelToken | None" = None, **kwargs) -> StageOutcome:
    """Acquire the lock, run, always release -- the single entry point
    app.py's execute route calls. A refusal (lock already held) raises
    rather than silently queuing or dropping the request.

    ``lock_path`` defaults to :data:`LOCK_PATH` (the real, repo-relative
    lock) but is a parameter precisely so a tester can point it at a temp
    file and never touch the real ``data/knowledge_curator/`` directory --
    the allowlist check happens before the lock is even touched, so a bad
    stage key never acquires anything to begin with.

    ``cancel_token``, if given, is consumed (test-and-clear) IMMEDIATELY
    after the lock is acquired but BEFORE `run_stage` is ever called -- a
    token already set at that point means this step was still queued when
    cancellation was requested, so it is skipped entirely (`state="blocked"`,
    `cancelled=True`) rather than started and then stopped. The SAME token
    is then handed to `run_stage` for the in-flight half: if nothing
    consumed it here, a request arriving WHILE this step streams is caught
    there instead. A token can therefore only ever cancel a step once,
    either as a skip or as a stop, never both.

    ``heartbeat_fn`` is bound to this lock automatically unless the caller
    overrides it via ``kwargs`` -- a caller-supplied ``on_timing_line``,
    ``popen_factory``, or ``project_id`` in ``kwargs`` passes straight
    through to `run_stage` unchanged (no special handling needed here --
    this function's whole job is the lock, not the argv)."""
    if stage not in EXECUTION_ALLOWLIST:
        raise ExecutionRefused(
            "not_allowlisted",
            f"{stage!r} is not on the execution allowlist "
            f"({sorted(EXECUTION_ALLOWLIST)}). Refused.")
    got = acquire_lock(stage, lock_path=lock_path)
    if not got["acquired"]:
        raise ExecutionRefused(
            "already_running",
            f"a run is already in progress: stage={got.get('stage')} "
            f"started_at={got.get('started_at')}. Refused -- never queued.")
    try:
        if cancel_token is not None and cancel_token.consume():
            return StageOutcome(stage=stage, state="blocked",
                                 detail="cancelled before it started (queued cancellation)",
                                 cancelled=True)
        kwargs.setdefault("heartbeat_fn", lambda: heartbeat(lock_path=lock_path))
        return run_stage(stage, cancel_token=cancel_token, **kwargs)
    finally:
        release_lock(lock_path=lock_path)
