"""project_wizard.py -- Tasks 1-4, COWORK_BRIEF_project_wizard.md.

Project Wizard: one control surface over every allowlisted repo's declared,
runnable stages -- data-refresh and report-build alike. It reads a committed
manifest of runnable stages from each of a small, allowlisted set of project
repos, shows what exists and whether it looks fresh, and lets an operator
trigger one stage at a time by hand. Nothing chains automatically in v1
(DECISIONS 0042; the brief's own working rule).

Built on DECISIONS 0042, which authorises the one genuinely new thing here:
this is the first surface asked to reach *outside* this checkout on purpose.
Every clause below is that ruling, applied:

  * **Clause (1) -- the manifest is data, never code.** A repo declares its
    own runnable stages in a committed ``wizforge.manifest.json`` at its own
    root. This module never imports another repo's Python.
  * **Clause (2) -- one repo allowlist, committed, reviewed-to-widen.**
    :func:`load_allowlist` reads ``config/project_wizard.allow.json``, keyed
    per host exactly as ``l5gntools.config.machine()`` is. A repo absent from
    it is never read, listed, or executed -- even if a manifest physically
    exists there (:func:`load_manifests` only ever looks at allowlisted
    paths).
  * **Clause (3) -- the execution allowlist is derived from validated
    manifests at board-build time.** :func:`board` builds it fresh on every
    call; :func:`execute_with_lock` accepts a ``(repo_key, stage_key)`` pair
    and nothing else.
  * **Clause (4) -- a manifest's ``command`` is a fixed, literal argv list,
    with no parameter slot.** :func:`parse_manifest` enforces this at
    validation time; there is no field anywhere in this module a caller
    could use to append to it.
  * **Clause (5) -- containment runs through the existing
    ``estate_data.resolve_contained``, never a second implementation.**
    :func:`resolve_stage_cwd` is the one place a manifest's ``cwd`` is turned
    into a path, and it is the one path every execution and every freshness
    read is required to go through.
  * **Clause (6) -- the toolkit never widens what a consumer repo can do.**
    This module only ever shells to a command a repo already declared for
    itself; there is no privilege-escalation path here for it to grant.
  * **Clause (7) -- where a consumer repo answers a question about itself,
    ask it.** :func:`stage_freshness`'s ``"delegated"`` source runs the
    manifest's own freshness command and shows its answer verbatim, rather
    than re-deriving staleness from file mtimes over data this module does
    not understand.

**Derived, never stored** -- ``docs_board.py``'s rule, carried over
unchanged. :func:`board` walks every allowlisted manifest fresh on every
call; nothing about the board itself is cached. The one thing this module
does write is the run marker (state after an explicit run) and the lock file
-- both records of what *happened*, not projections of what the manifests
currently say, and both live under :data:`WIZARD_DATA_DIR`, gitignored the
same way ``data/knowledge_curator/`` is.

**The lock and outcome contract are reused, not reinvented.** Every
execution goes through a pid+heartbeat file lock
(``curator_control.acquire_lock``/``release_lock``/``heartbeat``/
``lock_status``/``break_lock``, imported directly -- Task 3 left "import or
lift" for build time, and importing is what this module does, since nothing
about those primitives is Curator-specific) and ``curator_control
.classify_outcome``'s existing four states (success/failed/skipped/blocked;
**no fifth state**, a stop condition in its own right).
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from l5gntools import config as l5gn_config
from l5gntools.common import DATA_DIR

from .curator_control import (
    ExecutionRefused,
    StageOutcome,
    acquire_lock,
    break_lock,
    classify_outcome,
    heartbeat,
    lock_status,
    release_lock,
)
from .estate_data import DocumentRefused, resolve_contained

#: The committed, per-repo declaration file -- Task 1. Never authored by this
#: module; only ever read.
MANIFEST_FILENAME = "wizforge.manifest.json"

#: Bumped when a field is added or a shape changes -- a documented step, not
#: a silent one (mirrors the Conductor's ``PlanSpec`` versioning under 0037,
#: and ``l5gn.plan.v1``'s own schema string below).
MANIFEST_SCHEMA_VERSION = 1

#: The committed, per-host repo allowlist -- Task 2. Widening it is a
#: reviewed, committed edit; nothing in this module can widen it from a
#: request.
ALLOWLIST_PATH: Path = l5gn_config.CONFIG_DIR / "project_wizard.allow.json"

#: Where Project Wizard's own records live -- run markers (state after an
#: explicit run) and per-stage lock files. Neither is a manifest cache: both
#: are records of what this module DID, never a copy of what a manifest says
#: exists (that is re-read fresh on every board() call).
WIZARD_DATA_DIR: Path = DATA_DIR / "project_wizard"
RUN_MARKERS_DIR: Path = WIZARD_DATA_DIR / "run_markers"
LOCKS_DIR: Path = WIZARD_DATA_DIR / "locks"

#: Task 1's closed vocabulary for ``kind``. Not enforced behaviourally in v1
#: (every kind runs the same way) -- recorded because Task 4's future
#: planner needs to reason about "refresh, then build."
VALID_KINDS: frozenset[str] = frozenset({"data_refresh", "report_build", "other"})


class ManifestValidationError(ValueError):
    """Raised with EVERY violation found in one manifest, never just the
    first -- the ``chain_registry._validate_stage`` / ``PlanSpec.validate``
    pattern this brief asks for explicitly (Task 1: "Validation accumulates,
    then refuses")."""


# ---------------------------------------------------------------------------
# The allowlist -- Task 2. Config, not code, deliberately (0042's own
# consequence paragraph: a step down from 0033's posture, taken knowingly,
# because per-host paths are exactly what machines.json exists for).
# ---------------------------------------------------------------------------

def _read_json_object(path: Path) -> dict:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_allowlist(host: str | None = None, path: Path | None = None) -> dict[str, Path]:
    """This host's ``{repo_key: Path}`` allowlist.

    Falls back to the ``"default"`` entry exactly the way
    ``l5gntools.config.machine()`` layers ``machines.json``'s ``default`` ->
    host entries -- same precedence, same shape, a second file rather than a
    second mechanism. A host with no entry and no ``"default"`` gets an empty
    allowlist, never every repo on disk: "no boundary configured" must read
    as "nothing is allowlisted", the same discipline
    ``estate_data.resolve_contained`` applies to an empty anchor set.
    """
    host = host or l5gn_config.hostname()
    data = _read_json_object(path or ALLOWLIST_PATH)
    merged: dict[str, str] = {}
    merged.update((data.get("default") or {}).get("repos") or {})
    merged.update((data.get(host) or {}).get("repos") or {})
    return {str(k): Path(v) for k, v in merged.items()}


# ---------------------------------------------------------------------------
# The manifest -- Task 1. Data, never code; validated with every problem
# accumulated before anything is refused.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StageSpec:
    key: str
    label: str
    kind: str
    #: A fixed, literal argv list. 0042 clause (4): there is no parameter
    #: slot in this schema at all, on purpose.
    command: tuple[str, ...]
    #: Relative to the manifest's own location; resolved and verified
    #: contained within the repo's allowlisted root before every use
    #: (:func:`resolve_stage_cwd`, 0042 clause 5).
    cwd: str
    output_glob: str | None = None
    #: ``{"type": "self"}`` (the default) or
    #: ``{"type": "delegated", "command": [...]}``.
    freshness_source: dict = dataclasses.field(default_factory=lambda: {"type": "self"})
    #: Recorded, never acted on in v1 -- Task 4's seam.
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepoManifest:
    repo_key: str
    repo_root: Path
    schema_version: int
    repo_name: str
    stages: tuple  # tuple[StageSpec, ...]


def _validate_freshness_source(raw: Any, prefix: str, errors: list[str]) -> dict | None:
    if raw in (None, "self"):
        return {"type": "self"}
    if isinstance(raw, dict) and raw.get("type") == "delegated":
        command = raw.get("command")
        if (isinstance(command, list) and command
                and all(isinstance(c, str) and c for c in command)):
            return {"type": "delegated", "command": list(command)}
        errors.append(f"{prefix}: freshness_source.command must be a non-empty list of "
                      "non-empty strings.")
        return None
    errors.append(f"{prefix}: freshness_source must be \"self\" or "
                  "{\"type\": \"delegated\", \"command\": [...]}.")
    return None


def parse_manifest(repo_key: str, repo_root: Path, raw: Any) -> RepoManifest:
    """Parse and validate one manifest. Raises :class:`ManifestValidationError`
    naming EVERY problem at once (Task 1) -- never the first one only. A
    manifest that fails to parse or fails validation blocks that repo's card
    only; the caller (:func:`load_manifests`) is what isolates that per repo,
    the same per-item isolation ``estate refresh`` gives ``sf-data-service``'s
    own requirement batch.
    """
    errors: list[str] = []
    if not isinstance(raw, dict):
        raise ManifestValidationError(f"{repo_key}: manifest root must be a JSON object.")

    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, int):
        errors.append("schema_version must be an integer.")
    elif schema_version != MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version {schema_version} is not the known version "
                      f"{MANIFEST_SCHEMA_VERSION}.")

    repo_name = raw.get("repo_name")
    if not isinstance(repo_name, str) or not repo_name.strip():
        errors.append("repo_name must be a non-empty string.")

    raw_stages = raw.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        errors.append("stages must be a non-empty list.")
        raw_stages = []

    seen_keys: set[str] = set()
    stages: list[StageSpec] = []
    for i, raw_stage in enumerate(raw_stages):
        prefix = f"stages[{i}]"
        if not isinstance(raw_stage, dict):
            errors.append(f"{prefix}: must be a JSON object.")
            continue

        key = raw_stage.get("key")
        if not isinstance(key, str) or not key.strip():
            errors.append(f"{prefix}: key must be a non-empty string.")
            key = None
        elif key in seen_keys:
            errors.append(f"{prefix}: key {key!r} is not unique within this manifest.")
            key = None  # do not admit a colliding stage
        else:
            seen_keys.add(key)
        tag = key or f"{prefix}"

        label = raw_stage.get("label")
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{tag}: label must be a non-empty string.")
            label = None

        kind = raw_stage.get("kind")
        if kind not in VALID_KINDS:
            errors.append(f"{tag}: kind {kind!r} not in {sorted(VALID_KINDS)}.")
            kind = None

        command = raw_stage.get("command")
        if (not isinstance(command, list) or not command
                or not all(isinstance(c, str) and c for c in command)):
            errors.append(f"{tag}: command must be a non-empty list of non-empty strings "
                          "-- a fixed, literal argv (0042 clause 4).")
            command = None

        cwd = raw_stage.get("cwd")
        if not isinstance(cwd, str) or not cwd.strip():
            errors.append(f"{tag}: cwd must be a non-empty string, relative to the "
                          "manifest's own location.")
            cwd = None

        output_glob = raw_stage.get("output_glob")
        if output_glob is not None and not isinstance(output_glob, str):
            errors.append(f"{tag}: output_glob must be a string if given.")
            output_glob = None

        freshness = _validate_freshness_source(
            raw_stage.get("freshness_source", "self"), tag, errors)

        depends_on = raw_stage.get("depends_on")
        if depends_on is None:
            depends_on = []
        if not isinstance(depends_on, list) or not all(isinstance(d, str) for d in depends_on):
            errors.append(f"{tag}: depends_on must be a list of strings.")
            depends_on = []

        if None in (key, label, kind, command, cwd, freshness):
            continue  # already recorded above; do not admit a partial stage
        stages.append(StageSpec(
            key=key, label=label, kind=kind, command=tuple(command), cwd=cwd,
            output_glob=output_glob, freshness_source=freshness,
            depends_on=tuple(depends_on)))

    if errors:
        raise ManifestValidationError(
            f"{repo_key}: manifest invalid ({len(errors)} problem(s)): " + " | ".join(errors))

    return RepoManifest(repo_key=repo_key, repo_root=Path(repo_root),
                        schema_version=schema_version, repo_name=repo_name,
                        stages=tuple(stages))


@dataclass
class RepoLoadResult:
    repo_key: str
    repo_root: Path
    manifest: RepoManifest | None
    error: str | None


def load_manifests(allowlist: dict[str, Path] | None = None) -> list[RepoLoadResult]:
    """Every allowlisted repo's manifest, parsed and validated -- or the
    reason it wasn't. 0042 clause (2): only paths in ``allowlist`` are ever
    looked at; a manifest sitting at an unlisted path is never opened by
    this function, let alone read.
    """
    allowlist = allowlist if allowlist is not None else load_allowlist()
    out: list[RepoLoadResult] = []
    for repo_key, repo_root in sorted(allowlist.items()):
        repo_root = Path(repo_root)
        manifest_path = repo_root / MANIFEST_FILENAME
        if not manifest_path.is_file():
            out.append(RepoLoadResult(repo_key, repo_root, None,
                                      f"no {MANIFEST_FILENAME} at {repo_root}"))
            continue
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            out.append(RepoLoadResult(repo_key, repo_root, None,
                                      f"failed to parse {MANIFEST_FILENAME}: {exc}"))
            continue
        try:
            manifest = parse_manifest(repo_key, repo_root, raw)
        except ManifestValidationError as exc:
            out.append(RepoLoadResult(repo_key, repo_root, None, str(exc)))
            continue
        out.append(RepoLoadResult(repo_key, repo_root, manifest, None))
    return out


# ---------------------------------------------------------------------------
# Containment -- 0042 clause (5). One resolver, reused; a new anchor set
# (the allowlisted repo root), never a second implementation.
# ---------------------------------------------------------------------------

def resolve_stage_cwd(manifest: RepoManifest, stage: StageSpec) -> Path:
    """``stage.cwd`` resolved and verified inside ``manifest.repo_root`` --
    the ONLY place a manifest's ``cwd`` becomes a real path. Every execution
    and every self-freshness read goes through this, never a bespoke join.
    """
    candidate = manifest.repo_root.joinpath(*stage.cwd.replace("\\", "/").split("/"))
    return resolve_contained(
        candidate, (manifest.repo_root,),
        outside_reason="cwd_escapes_repo_root",
        no_anchor_reason="no_repo_anchor",
        boundary=f"{manifest.repo_key}'s declared repo root",
        no_anchor_detail="Project Wizard has no containment anchor for this repo, which "
                         "cannot happen for a real run -- repo_root comes from the "
                         "committed allowlist, never from a request.")


# ---------------------------------------------------------------------------
# Freshness -- 0042 clause (7). "self" reads output_glob's newest mtime
# under the verified cwd; "delegated" runs the repo's own answer and shows
# it, never re-deriving a competing number.
# ---------------------------------------------------------------------------

def _newest_mtime(base: Path, pattern: str) -> float | None:
    try:
        matches = [p for p in base.glob(pattern) if p.is_file()]
    except (OSError, ValueError):
        return None
    if not matches:
        return None
    return max(p.stat().st_mtime for p in matches)


def stage_freshness(manifest: RepoManifest, stage: StageSpec) -> dict:
    """One stage's freshness line -- self mtime, or the delegated command's
    own answer. Never both, never a Project-Wizard-derived number layered on
    top of a delegated one (0042 clause 7; UAT: "never a second,
    Project-Wizard-derived staleness number")."""
    fs = stage.freshness_source or {"type": "self"}
    cwd = resolve_stage_cwd(manifest, stage)
    if fs.get("type") == "delegated":
        try:
            proc = subprocess.run(fs["command"], cwd=str(cwd), capture_output=True,
                                  text=True, timeout=30)
            status = (proc.stdout or proc.stderr or "").strip() or None
            return {"source": "delegated", "status": status, "returncode": proc.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"source": "delegated", "status": None, "error": str(exc)}
    if not stage.output_glob:
        return {"source": "self", "last_built": None,
                "detail": "no output_glob declared for this stage."}
    return {"source": "self", "last_built": _newest_mtime(cwd, stage.output_glob)}


# ---------------------------------------------------------------------------
# Run markers -- Task 3: "last-run outcome... written after each run, never
# inferred." A record of what happened, never a cache of manifest state.
# ---------------------------------------------------------------------------

def _marker_path(repo_key: str, stage_key: str) -> Path:
    return RUN_MARKERS_DIR / f"{repo_key}__{stage_key}.json"


def read_run_marker(repo_key: str, stage_key: str) -> dict | None:
    p = _marker_path(repo_key, stage_key)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_run_marker(repo_key: str, stage_key: str, outcome: StageOutcome) -> None:
    RUN_MARKERS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "repo_key": repo_key, "stage_key": stage_key, "state": outcome.state,
        "detail": outcome.detail, "returncode": outcome.returncode,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    p = _marker_path(repo_key, stage_key)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, p)


# ---------------------------------------------------------------------------
# The board -- Task 3. Derived fresh on every call; nothing stored.
# ---------------------------------------------------------------------------

def _lock_path(repo_key: str, stage_key: str) -> Path:
    return LOCKS_DIR / f"{repo_key}__{stage_key}.lock"


def board(allowlist: dict[str, Path] | None = None) -> dict:
    """The whole board, grouped by repo, one card per ``(repo_key,
    stage_key)``. Also returns the execution allowlist derived from this
    exact render -- ``frozenset((repo_key, stage_key) for ...)``, mirroring
    ``curator_control.EXECUTION_ALLOWLIST`` (0042 clause 3). No stored board
    state, no cache: every call re-reads every allowlisted manifest.
    """
    loads = load_manifests(allowlist)
    repos: list[dict] = []
    allowed_pairs: set[tuple[str, str]] = set()
    for result in loads:
        if result.manifest is None:
            repos.append({
                "repo_key": result.repo_key, "repo_root": str(result.repo_root),
                "ok": False, "error": result.error, "stages": [],
            })
            continue
        m = result.manifest
        stage_cards = []
        for stage in m.stages:
            try:
                freshness = stage_freshness(m, stage)
                cwd_ok, cwd_error = True, None
            except DocumentRefused as exc:
                freshness, cwd_ok, cwd_error = None, False, exc.message
            if cwd_ok:
                allowed_pairs.add((result.repo_key, stage.key))
            stage_cards.append({
                "key": stage.key, "label": stage.label, "kind": stage.kind,
                "depends_on": list(stage.depends_on),
                "cwd_ok": cwd_ok, "cwd_error": cwd_error,
                "freshness": freshness,
                "last_run": read_run_marker(result.repo_key, stage.key),
                "lock": lock_status(_lock_path(result.repo_key, stage.key)),
            })
        repos.append({
            "repo_key": result.repo_key, "repo_root": str(m.repo_root),
            "repo_name": m.repo_name, "ok": True, "error": None,
            "stages": stage_cards,
        })
    return {
        "repos": repos,
        "execution_allowlist": sorted(f"{r}::{s}" for r, s in allowed_pairs),
        "persisted": False,
        "actions_enabled": True,
        "note": "Manual only, v1 -- no stage's completion ever triggers another. "
                "Derived fresh from every allowlisted manifest on every call.",
    }


# ---------------------------------------------------------------------------
# Execution -- 0042 clause (3): a (repo_key, stage_key) pair and nothing
# else. The pid+heartbeat lock and the four-state outcome are reused from
# curator_control, not reimplemented (Task 3).
# ---------------------------------------------------------------------------

def _find_stage(repo_key: str, stage_key: str,
                allowlist: dict[str, Path] | None = None) -> tuple[RepoManifest, StageSpec]:
    """The ONLY way a (repo_key, stage_key) pair is resolved to something
    runnable -- re-derives the allowlist from validated manifests at the
    moment of the call, exactly as `board()` does, so a manifest edited or a
    repo removed between page-load and click is honoured immediately."""
    for result in load_manifests(allowlist):
        if result.repo_key != repo_key or result.manifest is None:
            continue
        for stage in result.manifest.stages:
            if stage.key == stage_key:
                return result.manifest, stage
    raise ExecutionRefused(
        "not_allowlisted",
        f"({repo_key!r}, {stage_key!r}) is not on the execution allowlist -- not present "
        "in a validated manifest under the committed repo allowlist. Refused.")


def _default_popen(argv: list[str], *, cwd: str):
    return subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)


def run_stage(repo_key: str, stage_key: str, *, allowlist: dict[str, Path] | None = None,
              popen_factory=None, on_line=None, heartbeat_fn=None) -> StageOutcome:
    """Run exactly one allowlisted stage's fixed argv, streaming stdout+stderr
    line by line (``curator_control.run_stage``'s pattern, re-derived here
    because the argv source is a manifest, not ``STAGE_TABLE``) -- never
    buffered to exit, so a multi-minute report build shows it is alive.
    Writes the run marker unconditionally, including on a blocked precondition,
    so the board's "last-run" line is never stale relative to what this
    function actually did.
    """
    manifest, stage = _find_stage(repo_key, stage_key, allowlist)
    try:
        cwd = resolve_stage_cwd(manifest, stage)
    except DocumentRefused as exc:
        outcome = StageOutcome(stage=stage_key, state="blocked", detail=exc.message)
        write_run_marker(repo_key, stage_key, outcome)
        return outcome

    spawn = popen_factory or _default_popen
    try:
        proc = spawn(list(stage.command), cwd=str(cwd))
    except OSError as exc:
        # The command in a manifest is a fixed, literal argv (0042 clause 4)
        # -- but "fixed" does not mean "resolvable on this machine's PATH".
        # A bare interpreter name (e.g. "python") spawned as a child of a
        # process launched from an unrelated PATH (exactly what "Start
        # Chronicler Deck.bat" documents about itself) fails with
        # FileNotFoundError/WinError2 here, not later. That is a blocked
        # precondition, the same class as a missing script or a bad cwd --
        # never an unhandled exception that turns into a raw 500 the UI has
        # no outcome to show for. The run marker is still written so the
        # board's "last-run" line reflects this immediately.
        outcome = StageOutcome(
            stage=stage_key, state="blocked",
            detail=f"could not start {stage.command[0]!r}: {exc}. The manifest's "
                   "command must resolve on THIS process's PATH, not a terminal's -- "
                   "consider a fully-qualified interpreter path in the manifest if "
                   "the server is launched from an environment where a bare "
                   "interpreter name does not resolve to the right one.")
        write_run_marker(repo_key, stage_key, outcome)
        return outcome
    lines: list[str] = []
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        lines.append(line)
        if on_line:
            on_line(line)
        if heartbeat_fn:
            heartbeat_fn()
    returncode = proc.wait()
    stdout_text = "\n".join(lines)
    # curator_control.classify_outcome's "skipped" branch searches its ENTIRE
    # input text for the substring "skip" -- sound for K0-K5's own terse,
    # single-purpose stdout, unsound for an arbitrary manifest-declared
    # command. `verify.py` alone runs ~90 auditors/testers over several
    # minutes, and it is entirely normal for at least one of them to print
    # something containing "skip" (a benign, expected per-tester skip on a
    # machine with no MCF corpus) as part of an otherwise fully successful,
    # GREEN run -- searching the whole blob mislabelled that GREEN run
    # "skipped". Passing only the last non-empty line keeps the SAME four-
    # state vocabulary and the SAME function (0042/Task 3: no fifth state,
    # reuse classify_outcome) while matching the convention this repo's own
    # scripts already follow -- verify.py's own final line is either
    # "verify: GREEN ..." or "verify: RED ...", never "skip" unless the run
    # genuinely was a no-op end to end.
    last_line = next((l for l in reversed(lines) if l.strip()), "")
    state, detail = classify_outcome(returncode, last_line, "")
    tail = "\n".join(lines[-10:])
    outcome = StageOutcome(stage=stage_key, state=state, detail=detail,
                           returncode=returncode, stdout_tail=tail)
    write_run_marker(repo_key, stage_key, outcome)
    return outcome


def execute_with_lock(repo_key: str, stage_key: str, *,
                      allowlist: dict[str, Path] | None = None, **kwargs) -> StageOutcome:
    """Acquire this stage's own pid+heartbeat lock, run, always release --
    the single entry point the execute route calls. The allowlist check
    (via ``_find_stage``, inside ``run_stage``... run BEFORE the lock is
    touched here too) happens first, so a bad pair never acquires anything.
    A second request while one is held is refused (409, ``already_running``)
    -- never queued, never silently dropped (curator_control's own contract,
    reused verbatim)."""
    _find_stage(repo_key, stage_key, allowlist)  # refuse before touching the lock
    lock_path = _lock_path(repo_key, stage_key)
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    got = acquire_lock(f"{repo_key}::{stage_key}", lock_path=lock_path)
    if not got["acquired"]:
        raise ExecutionRefused(
            "already_running",
            f"a run is already in progress for ({repo_key}, {stage_key}): "
            f"started_at={got.get('started_at')}. Refused -- never queued.")
    try:
        kwargs.setdefault("heartbeat_fn", lambda: heartbeat(lock_path=lock_path))
        return run_stage(repo_key, stage_key, allowlist=allowlist, **kwargs)
    finally:
        release_lock(lock_path=lock_path)


def stage_lock_status(repo_key: str, stage_key: str) -> dict:
    return lock_status(_lock_path(repo_key, stage_key))


def break_stage_lock(repo_key: str, stage_key: str, reason: str) -> dict:
    """The ONLY sanctioned way a stale per-stage lock is ever cleared -- an
    explicit, named operator action, never an automatic reclaim
    (``curator_control.break_lock``, reused directly; a stop condition of
    this brief in its own right)."""
    return break_lock(reason, lock_path=_lock_path(repo_key, stage_key))


# ---------------------------------------------------------------------------
# Task 4 -- the seam for the future orchestrator (WizForgeAnalytics ROADMAP
# R9). Design now, don't wire yet: a schema-versioned, validated,
# serialisable shape for an ordered list of (repo_key, stage_key) steps.
# Nothing here populates or executes one -- there is no planner and no
# automatic chaining anywhere in this module. This is explicitly NOT R9: R9
# is one adaptive process across the whole estate; this is a stub shape a
# future scheduler could emit, exercised trivially (one manual step at a
# time) so it already exists and is not designed blind.
# ---------------------------------------------------------------------------

WIZARD_PLAN_SCHEMA = "wizforge.plan.v1"


@dataclass(frozen=True)
class WizardPlanStep:
    repo_key: str
    stage_key: str


@dataclass(frozen=True)
class WizardPlanSpec:
    """An ordered list of steps -- a shape a future planner could emit, not
    a thing this module ever runs. Every step still requires its own,
    separate, explicit click through :func:`execute_with_lock`; nothing
    reads this class to run anything (Task 4: "design now, don't wire yet
    ")."""
    plan_id: str
    steps: tuple  # tuple[WizardPlanStep, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": WIZARD_PLAN_SCHEMA,
            "plan_id": self.plan_id,
            "steps": [dataclasses.asdict(s) for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "WizardPlanSpec":
        if not isinstance(data, dict):
            raise ManifestValidationError("plan spec must be a JSON object.")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list):
            raise ManifestValidationError("plan spec 'steps' must be a list.")
        steps = tuple(WizardPlanStep(repo_key=s.get("repo_key"), stage_key=s.get("stage_key"))
                      for s in raw_steps)
        return cls(plan_id=str(data.get("plan_id", "")), steps=steps)

    def validate(self, *, known_pairs: frozenset | None = None) -> bool:
        """Accumulate-then-raise (:class:`ManifestValidationError`), the same
        discipline as ``planner.PlanSpec.validate``. ``known_pairs`` -- when
        given -- is a live board's execution allowlist; a step naming a pair
        not on it is invalid. Validating the shape never authorises running
        it -- that is still, and only ever, an explicit
        ``execute_with_lock`` call per step."""
        errors: list[str] = []
        if not self.plan_id or not self.plan_id.strip():
            errors.append("plan_id is empty.")
        for i, step in enumerate(self.steps):
            if not step.repo_key or not step.stage_key:
                errors.append(f"step[{i}]: repo_key and stage_key must both be set.")
            elif known_pairs is not None and (step.repo_key, step.stage_key) not in known_pairs:
                errors.append(f"step[{i}]: ({step.repo_key}, {step.stage_key}) is not on the "
                              "current execution allowlist.")
        if errors:
            raise ManifestValidationError(f"plan {self.plan_id!r} invalid: " + " | ".join(errors))
        return True


# ---------------------------------------------------------------------------
# The request-body models -- MODULE level, not inside `router()`, and the
# reason is written out here because it bit this exact file once already:
# `app.py` (top of file) already carries this warning verbatim -- "a
# closure-local model leaves an unresolved ForwardRef and FastAPI misreads
# it as a query param" -- because this module has `from __future__ import
# annotations`, and FastAPI resolves a route's annotations against the
# route function's MODULE globals at registration time. A Pydantic model
# defined inside `router()` is a local, not a module global, so that
# resolution silently fails and the parameter is treated as a query param
# instead of a request body -- a 422 "field required" that never reaches the
# handler, previously reproduced against a live TestClient before this fix.
#
# Guarded exactly like `app.py`'s own request-body models, so importing this
# module (which `modules.py` does unconditionally) still succeeds on a
# machine with no web stack installed -- `router()` itself is never called
# on such a machine, since nothing calls it before `create_app` has already
# confirmed FastAPI is importable.
# ---------------------------------------------------------------------------
try:
    from pydantic import BaseModel

    class ExecuteBody(BaseModel):
        repo_key: str
        stage_key: str

    class BreakLockBody(BaseModel):
        repo_key: str
        stage_key: str
        reason: str
except ImportError:  # pydantic ships with fastapi; absent == web stack not installed
    ExecuteBody = None  # type: ignore
    BreakLockBody = None  # type: ignore


def router(ctx):
    from fastapi import APIRouter, HTTPException

    api = APIRouter()

    @api.get("/api/project_wizard/board")
    def pw_board_route():
        return board()

    @api.post("/api/project_wizard/execute")
    def pw_execute_route(payload: ExecuteBody):
        try:
            outcome = execute_with_lock(payload.repo_key, payload.stage_key)
            return dataclasses.asdict(outcome)
        except ExecutionRefused as exc:
            status = 409 if exc.reason == "already_running" else 400
            raise HTTPException(status_code=status,
                                detail={"reason": exc.reason, "detail": exc.message})

    @api.get("/api/project_wizard/lock")
    def pw_lock_route(repo_key: str, stage_key: str):
        return stage_lock_status(repo_key, stage_key)

    @api.post("/api/project_wizard/break_lock")
    def pw_break_lock_route(payload: BreakLockBody):
        try:
            return break_stage_lock(payload.repo_key, payload.stage_key, payload.reason)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    return api
