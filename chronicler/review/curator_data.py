"""curator_data.py -- Task 1, COWORK_BRIEF_curator_tab.md.

Read-only data layer for the Knowledge Curator tab. Loads whatever exists
under ``data/knowledge_curator/`` (K0's ``candidate_map.tsv``, K1's
``knowledge_index.json``, K2's ``claims.json``, K3's ``corpus_index.json``,
K4's ``matches.json``) and the ratified join surface,
``config/mcf_conversation_map.tsv``, and reports **what is on disk and what
is not** -- it recomputes no finding and reimplements no stage's logic.

Every one of the six artefacts this module reads may be absent, and absent
is a normal state, not an error: this machine may never have run the
pipeline at all (`data/knowledge_curator/` does not exist here), or may have
run some stages and not others (a partially-run pipeline is the normal
mid-flight state, not a defect).

**Staleness is per-artefact.** There is deliberately no single "as of"
timestamp for the whole tab -- a corpus index from yesterday beside claims
from last week is the ordinary state of a pipeline nobody runs in lockstep,
and collapsing that to one timestamp would hide exactly the fact an operator
needs (which half is stale).

Blocked reasoning is derived from what is actually on disk, not assumed: the
ratified map may be header-only, or may already carry rows and simply not
have had K1 run against it yet -- both are real states this module has to
tell apart, because the operator's next action differs.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from l5gntools.common import DATA_DIR

from .estate_data import REPO_ROOT, parse_timestamp

#: Where every Curator stage output lives on this machine.
CURATOR_DATA_DIR: Path = DATA_DIR / "knowledge_curator"

#: The ratified join surface (K0's human-checked output). Never derived --
#: this is the one file Task 2 is permitted to append to (DECISIONS 0033).
RATIFIED_MAP_PATH: Path = REPO_ROOT / "config" / "mcf_conversation_map.tsv"

#: K0's own candidate output -- NOT ratified, offered for review only.
CANDIDATE_MAP_PATH: Path = CURATOR_DATA_DIR / "candidate_map.tsv"

K1_INDEX_PATH: Path = CURATOR_DATA_DIR / "knowledge_index.json"
K2_CLAIMS_PATH: Path = CURATOR_DATA_DIR / "claims.json"
K3_CORPUS_PATH: Path = CURATOR_DATA_DIR / "corpus_index.json"
K4_MATCHES_PATH: Path = CURATOR_DATA_DIR / "matches.json"

STAGE_KEYS: tuple[str, ...] = ("K0", "K1", "K2", "K3", "K4", "K5")

RATIFIED_MAP_HEADER: tuple[str, ...] = (
    "session_id", "local_folder", "project_id", "conversation_name", "notes")
CANDIDATE_MAP_HEADER: tuple[str, ...] = (
    "session_id", "local_folder", "project_id", "conversation_name",
    "match_pass", "matched_length", "candidate_count", "status", "note")


@dataclass
class ArtefactState:
    """One stage's on-disk state -- exists or not, and why not, never a
    recomputed finding. ``raw`` carries the parsed body for the route to
    hand to a Task-4/5 renderer; the API layer decides what subset to expose."""
    stage: str
    path: str
    exists: bool
    row_count: int | None = None
    generated_at: str | None = None
    generated_at_source: str | None = None  # "field" | "file_mtime" | None
    model_id: str | None = None
    endpoint: str | None = None
    temperature: float | None = None
    blocked: bool = False
    blocked_reason: str | None = None
    raw: object = None

    def summary(self) -> dict:
        """The header-safe view -- everything except ``raw``, which is large
        and stage-specific and is fetched separately by the views that need it."""
        return {
            "stage": self.stage, "path": self.path, "exists": self.exists,
            "row_count": self.row_count, "generated_at": self.generated_at,
            "generated_at_source": self.generated_at_source,
            "model_id": self.model_id, "endpoint": self.endpoint,
            "temperature": self.temperature, "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
        }


def _file_mtime_iso(path: Path) -> str | None:
    try:
        import datetime as _dt
        ts = path.stat().st_mtime
        return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_tsv_rows(path: Path) -> list[dict]:
    """Every row of a Curator TSV, in file order, as dicts. Never raises --
    an absent or unreadable file is an empty list, and the caller (which
    already checked ``exists``) reports the absence itself."""
    if not path.is_file():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            return [dict(rec) for rec in reader]
    except OSError:
        return []


# ---------------------------------------------------------------------------
# The ratified map (K0's human-checked output)
# ---------------------------------------------------------------------------

def ratified_map_rows(path: Path | None = None) -> list[dict]:
    """Every row in ``config/mcf_conversation_map.tsv``, ratified or not --
    a header-only file returns ``[]``. This does not filter on session_id
    being non-blank because every real row in this file already carries one;
    a blank one would itself be a finding, not something to hide by filtering."""
    return _load_tsv_rows(path or RATIFIED_MAP_PATH)


def ratified_row_count(path: Path | None = None) -> int:
    return len(ratified_map_rows(path))


# ---------------------------------------------------------------------------
# K0 -- candidate_map.tsv (the un-ratified candidate output)
# ---------------------------------------------------------------------------

def k0_state(candidate_path: Path | None = None,
             ratified_path: Path | None = None) -> ArtefactState:
    cpath = candidate_path or CANDIDATE_MAP_PATH
    rpath = ratified_path or RATIFIED_MAP_PATH
    rows = _load_tsv_rows(cpath)
    ratified_count = ratified_row_count(rpath)
    exists = cpath.is_file()
    blocked = not exists
    blocked_reason = None
    if blocked:
        blocked_reason = (
            "K0 has not been run on this machine -- no candidate_map.tsv "
            f"under {CURATOR_DATA_DIR}. Run bootstrap_conversation_map.py "
            "against the curated sheet to produce one.")
    return ArtefactState(
        stage="K0", path=str(cpath), exists=exists,
        row_count=(len(rows) if exists else None),
        generated_at=_file_mtime_iso(cpath) if exists else None,
        generated_at_source=("file_mtime" if exists else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw={"candidate_rows": rows, "ratified_row_count": ratified_count},
    )


# ---------------------------------------------------------------------------
# K1 -- knowledge_index.json
# ---------------------------------------------------------------------------

def k1_state(index_path: Path | None = None,
             ratified_path: Path | None = None) -> ArtefactState:
    ipath = index_path or K1_INDEX_PATH
    data = _load_json(ipath)
    ratified_count = ratified_row_count(ratified_path or RATIFIED_MAP_PATH)
    exists = data is not None

    blocked = not exists
    blocked_reason = None
    if blocked:
        if ratified_count == 0:
            blocked_reason = (
                "K1 blocked: the ratified map is header-only (0 rows in "
                f"{RATIFIED_MAP_PATH.name}). Ratify at least one row before "
                "K1 has anything to join against.")
        else:
            blocked_reason = (
                f"K1 has not been run yet, though the map is ratified "
                f"({ratified_count} row(s)). Run knowledge_index.py.")

    # knowledge_index.json carries no generated_at field of its own (K1's
    # writer does not stamp one) -- file mtime is the only honest answer.
    return ArtefactState(
        stage="K1", path=str(ipath), exists=exists,
        row_count=(len(data.get("projects", [])) if data else None),
        generated_at=_file_mtime_iso(ipath) if exists else None,
        generated_at_source=("file_mtime" if exists else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw=data,
    )


# ---------------------------------------------------------------------------
# K2 -- claims.json
# ---------------------------------------------------------------------------

def k2_state(claims_path: Path | None = None,
             ratified_path: Path | None = None) -> ArtefactState:
    cpath = claims_path or K2_CLAIMS_PATH
    data = _load_json(cpath)
    ratified_count = ratified_row_count(ratified_path or RATIFIED_MAP_PATH)
    exists = data is not None

    blocked = not exists
    blocked_reason = None
    if blocked:
        if ratified_count == 0:
            blocked_reason = (
                "K2 blocked: the ratified map is header-only -- there are no "
                "mapped conversations to extract claims from.")
        else:
            blocked_reason = (
                f"K2 has not been run yet, though the map is ratified "
                f"({ratified_count} row(s)). Run extract_claims.py "
                "-- requires LM Studio reachable and a --model.")

    return ArtefactState(
        stage="K2", path=str(cpath), exists=exists,
        row_count=(data.get("claims_extracted") if data else None),
        generated_at=(data.get("run_timestamp") if data else None),
        generated_at_source=("field" if (data and data.get("run_timestamp")) else None),
        model_id=(data.get("model_id") if data else None),
        endpoint=(data.get("endpoint") if data else None),
        temperature=(data.get("temperature") if data else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw=data,
    )


# ---------------------------------------------------------------------------
# K3 -- corpus_index.json (deterministic, no model)
# ---------------------------------------------------------------------------

def k3_state(corpus_path: Path | None = None,
             index_path: Path | None = None) -> ArtefactState:
    cpath = corpus_path or K3_CORPUS_PATH
    data = _load_json(cpath)
    k1_exists = (index_path or K1_INDEX_PATH).is_file()
    exists = data is not None

    blocked = not exists
    blocked_reason = None
    if blocked:
        blocked_reason = (
            "K3 blocked: K1's knowledge_index.json is absent -- there is no "
            "mapped project to chunk KNOWLEDGE*.md files for."
            if not k1_exists else
            "K3 has not been run yet. Run corpus_index.py.")

    total_chunks = None
    if data:
        total_chunks = sum(
            f.get("chunk_count", 0)
            for p in data.get("projects", []) for f in p.get("files", []))

    return ArtefactState(
        stage="K3", path=str(cpath), exists=exists,
        row_count=total_chunks,
        generated_at=_file_mtime_iso(cpath) if exists else None,
        generated_at_source=("file_mtime" if exists else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw=data,
    )


# ---------------------------------------------------------------------------
# K4 -- matches.json
# ---------------------------------------------------------------------------

def k4_state(matches_path: Path | None = None,
             claims_path: Path | None = None,
             corpus_path: Path | None = None) -> ArtefactState:
    mpath = matches_path or K4_MATCHES_PATH
    data = _load_json(mpath)
    k2_exists = (claims_path or K2_CLAIMS_PATH).is_file()
    k3_exists = (corpus_path or K3_CORPUS_PATH).is_file()
    exists = data is not None

    blocked = not exists
    blocked_reason = None
    if blocked:
        missing = [n for n, ok in (("K2 claims", k2_exists), ("K3 corpus index", k3_exists))
                   if not ok]
        if missing:
            blocked_reason = f"K4 blocked: missing input(s): {', '.join(missing)}."
        else:
            blocked_reason = (
                "K4 has not been run yet. Run match_claims.py -- requires "
                "LM Studio reachable and a --model for the confirm step.")

    return ArtefactState(
        stage="K4", path=str(mpath), exists=exists,
        row_count=(len(data.get("claims", [])) if data else None),
        generated_at=(data.get("run_timestamp") if data else None),
        generated_at_source=("field" if (data and data.get("run_timestamp")) else None),
        model_id=(data.get("model_id") if data else None),
        endpoint=(data.get("endpoint") if data else None),
        temperature=(data.get("temperature") if data else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw=data,
    )


# ---------------------------------------------------------------------------
# K5 -- report_<date>.md (found by glob; the compiled report is not JSON)
# ---------------------------------------------------------------------------

def k5_state(data_dir: Path | None = None,
             claims_path: Path | None = None,
             matches_path: Path | None = None) -> ArtefactState:
    ddir = data_dir or CURATOR_DATA_DIR
    reports = sorted(ddir.glob("report_*.md")) if ddir.is_dir() else []
    latest = reports[-1] if reports else None
    exists = latest is not None
    k2_exists = (claims_path or K2_CLAIMS_PATH).is_file()
    m_exists = (matches_path or K4_MATCHES_PATH).is_file()

    blocked = not exists
    blocked_reason = None
    if blocked:
        missing = [n for n, ok in (("K2 claims", k2_exists), ("K4 matches", m_exists))
                   if not ok]
        if missing:
            blocked_reason = f"K5 blocked: missing input(s): {', '.join(missing)}."
        else:
            blocked_reason = "K5 has not been run yet. Run compile_report.py."

    return ArtefactState(
        stage="K5", path=(str(latest) if latest else str(ddir / "report_<date>.md")),
        exists=exists, row_count=(len(reports) if reports else None),
        generated_at=_file_mtime_iso(latest) if latest else None,
        generated_at_source=("file_mtime" if latest else None),
        blocked=blocked, blocked_reason=blocked_reason,
        raw={"reports": [str(p) for p in reports]},
    )


# ---------------------------------------------------------------------------
# Curator -- the loaded whole, the tab's one entry point
# ---------------------------------------------------------------------------

class Curator:
    """Everything the tab needs, loaded once per request the same way
    ``EstateData`` is loaded once per process -- except the Curator's own
    rule (0027-style: a local surface reads its source at render time) means
    each accessor re-reads its file rather than caching, so a stage that just
    finished writing shows up on the next request without a restart.

    ``available`` mirrors the estate half's shape: True iff
    ``data/knowledge_curator/`` exists at all, so the header can say plainly
    "nothing has run here yet" rather than enumerating six absences.
    """

    def __init__(self, data_dir: Path | None = None, ratified_map_path: Path | None = None):
        self.data_dir: Path = data_dir or CURATOR_DATA_DIR
        self.ratified_map_path: Path = ratified_map_path or RATIFIED_MAP_PATH

    @property
    def available(self) -> bool:
        return self.data_dir.is_dir()

    def stage_states(self) -> dict[str, ArtefactState]:
        candidate = self.data_dir / "candidate_map.tsv"
        index = self.data_dir / "knowledge_index.json"
        claims = self.data_dir / "claims.json"
        corpus = self.data_dir / "corpus_index.json"
        matches = self.data_dir / "matches.json"
        return {
            "K0": k0_state(candidate, self.ratified_map_path),
            "K1": k1_state(index, self.ratified_map_path),
            "K2": k2_state(claims, self.ratified_map_path),
            "K3": k3_state(corpus, index),
            "K4": k4_state(matches, claims, corpus),
            "K5": k5_state(self.data_dir, claims, matches),
        }

    def header(self) -> dict:
        """Per-artefact state, never one collapsed timestamp (per-artefact
        staleness is load-bearing, see module docstring)."""
        states = self.stage_states()
        return {
            "available": self.available,
            "data_dir": str(self.data_dir),
            "ratified_map_path": str(self.ratified_map_path),
            "ratified_row_count": ratified_row_count(self.ratified_map_path),
            "stages": {k: v.summary() for k, v in states.items()},
        }

    # --- Task 5: map/coverage, straight from K1's own reconciliation -------
    def coverage(self) -> dict:
        """K1's reconciliation, reported and never resolved (Task 5). Every
        field here is copied from ``knowledge_index.json`` -- nothing is
        recomputed. If K1 has not run, every list is empty and ``available``
        says so; an empty list here must never be read as "fully resolved"."""
        k1 = k1_state(self.data_dir / "knowledge_index.json", self.ratified_map_path)
        data = k1.raw or {}
        return {
            "available": k1.exists,
            "blocked_reason": k1.blocked_reason,
            "generated_at": k1.generated_at,
            "projects": data.get("projects", []),
            "unresolved": data.get("unresolved", []),
            "label_disagreements": data.get("label_disagreements", []),
            "mapped_but_absent_on_disk": data.get("mapped_but_absent_on_disk", []),
            "present_not_mapped": data.get("present_not_mapped", []),
            "note": ("The label (conversation_name) is a label; session_id is "
                     "the join. Reported, never auto-resolved."),
        }
