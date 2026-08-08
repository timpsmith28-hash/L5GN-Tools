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
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from l5gntools import config as l5gn_config

from .curator_data import CURATOR_DATA_DIR, RATIFIED_MAP_PATH, ratified_row_count

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

#: Stages that get a model selector at all (Task 3: "only for stages that
#: call a model"). K0/K1/K3/K5 are deterministic and get none.
MODEL_SELECTABLE_STAGES: tuple[str, ...] = ("K2", "K4")

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
# The lock -- a real file, not a disabled button
# ---------------------------------------------------------------------------

def lock_status(lock_path: Path | None = None) -> dict:
    p = lock_path or LOCK_PATH
    if not p.is_file():
        return {"locked": False}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"locked": True, "stage": None, "started_at": None,
                "detail": "lock file present but unreadable -- treated as locked"}
    return {"locked": True, "stage": data.get("stage"), "started_at": data.get("started_at"),
            "pid": data.get("pid")}


def acquire_lock(stage: str, lock_path: Path | None = None) -> dict:
    """Real single-run lock: an exclusive file create (`O_CREAT|O_EXCL`), not
    a disabled button and not an in-memory flag another worker process
    wouldn't see. A second request while one is held is refused with what is
    running and when it started -- never queued, never silently dropped."""
    p = lock_path or LOCK_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "stage": stage, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": os.getpid(),
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


def release_lock(lock_path: Path | None = None) -> None:
    p = lock_path or LOCK_PATH
    try:
        p.unlink()
    except FileNotFoundError:
        pass


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
    state: str  # "success" | "failed" | "skipped" | "blocked"
    detail: str
    returncode: int | None = None
    stdout_tail: str = ""


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


def run_stage(stage: str, *, host: str | None = None, cache_root: Path | None = None,
              runner=None) -> StageOutcome:
    """Run exactly one allowlisted stage. ``stage`` is the ONLY thing this
    function accepts that named the work to do -- there is no argv, path, or
    flag parameter here a caller could use to run something else. Model
    stages (K2/K4) resolve their model from ``config/local.json`` themselves;
    a stage with no selection recorded is BLOCKED, never run with a guessed
    default (a model stage's `--model` has no default anywhere in this
    codebase, deliberately -- COWORK_BRIEF_curator_tab.md, "Grounding").

    ``runner`` is injectable (defaults to `subprocess.run`) so testers exercise
    the allowlist/lock/classification logic without ever spawning a real
    process."""
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

    script_path = _PIPE / spec["script"]
    if not script_path.is_file():
        return StageOutcome(stage=stage, state="blocked",
                             detail=f"{spec['script']} not found under {_PIPE}")

    run = runner or subprocess.run
    proc = run([sys.executable, str(script_path), *argv_extra],
               cwd=str(_PIPE.parent.parent), capture_output=True, text=True)
    state, detail = classify_outcome(proc.returncode, proc.stdout or "", proc.stderr or "")
    tail = "\n".join((proc.stdout or "").splitlines()[-10:])
    return StageOutcome(stage=stage, state=state, detail=detail,
                         returncode=proc.returncode, stdout_tail=tail)


def execute_with_lock(stage: str, lock_path: Path | None = None, **kwargs) -> StageOutcome:
    """Acquire the lock, run, always release -- the single entry point
    app.py's execute route calls. A refusal (lock already held) raises
    rather than silently queuing or dropping the request.

    ``lock_path`` defaults to :data:`LOCK_PATH` (the real, repo-relative
    lock) but is a parameter precisely so a tester can point it at a temp
    file and never touch the real ``data/knowledge_curator/`` directory --
    the allowlist check happens before the lock is even touched, so a bad
    stage key never acquires anything to begin with."""
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
        return run_stage(stage, **kwargs)
    finally:
        release_lock(lock_path=lock_path)
