"""Write-endpoint core -- stdlib only, no server, independently testable.

Everything that touches the DB or the registry lives here so the hermetic gate
(tests/tester_review.py) can exercise the real write path with plain sqlite3, no
FastAPI, no uvicorn. app.py is a thin HTTP shell over these functions.

The load-bearing invariant, asserted by the tester: `apply_ruling` mutates ONLY
`threads.project_link` and `threads.project_confidence` (plus an idempotent
registry-identity row in `projects`, required for the FK). It never touches
`link_evidence`, `review_queue`, message content, or any other pipeline-owned
column -- that column boundary is the single-writer guarantee (DECISIONS 0007).
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Confidence value a human ruling stamps. In relink's authority ladder
# (none < fuzzy < evidence < manual) this is the top, and PROTECTED there -- so
# once the endpoint writes it, the nightly relink pass skips the thread
# (skip_manual) and can never overwrite a human's decision. That is the whole
# point: the write is also the lock, structurally.
MANUAL_CONFIDENCE = "manual"

# review_queue row types this round's endpoint surfaces (round-2 brief, Task C).
QUEUE_TYPES = ("project_link", "link_ambiguous", "link_downgrade")

_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db_path: Path) -> sqlite3.Connection:
    """The endpoint's connection to the LIVE vault (DECISIONS 0014).

    Routed through the shared pragma helper so the write endpoint opens the file
    with exactly the settings every other writer uses -- WAL and a busy_timeout,
    which is what lets it write while Datasette reads without either seeing a
    torn state. Deliberately the live DB, not a snapshot: `serve` moved to a
    snapshot under 0013, but review must see live state or it would re-serve
    threads that have already been ruled.
    """
    from l5gntools.dbsafe import connect as _connect
    return _connect(db_path)


# ---------------------------------------------------------------------------
# Path resolution -- config-driven, never hardcoded (DECISIONS 0007, round-2 C.4)
# ---------------------------------------------------------------------------
def resolve_db_path(machine: dict | None = None) -> Path:
    """The live vault path, resolved EXACTLY like `serve`/`backup`.

    Delegates to l5gntools.backup.resolve_db_path so there is one path-resolution
    rule across every runtime command (CHRONICLER_DB_PATH env -> machine 'vault'
    -> CHRONICLER_HOME/chronicler.db). Never hardcoded (the vertex-3 mistake).
    """
    from l5gntools.backup import resolve_db_path as _resolve
    return _resolve(machine)


def resolve_registry_path(machine: dict | None = None) -> Path:
    """Where to read `project_registry.json` for id validation.

    Order, most-explicit first:
      1. CHRONICLER_REGISTRY_PATH env -- the recommended knob on the knight. It
         sidesteps relink's REGISTRY_PATH derivation fragility entirely (that
         path moves with CHRONICLER_HOME; see the round-2 report). Set this and
         the endpoint and relink can be pointed at the same file deterministically.
      2. relink's derived location: <github_root>/L5GN/.intel_sync/project_registry.json,
         computed the same way relink.py computes REGISTRY_PATH, so absent an env
         override the endpoint validates against the same registry relink linked.
      3. the repo authoring copy config/project_registry.json (dev / fallback).
    Raises FileNotFoundError loudly if none exists -- never validates against a
    silently-missing registry (that would let every id look 'unknown').
    """
    env = os.environ.get("CHRONICLER_REGISTRY_PATH")
    if env:
        return Path(env)

    # Mirror relink.REGISTRY_PATH: CHRONICLER_ROOT.parent.parent / L5GN / .intel_sync
    home = os.environ.get("CHRONICLER_HOME")
    if home is None and machine:
        home = machine.get("chronicler_home")
    chronicler_root = Path(home) if home else _PIPELINE_DIR.parent
    derived = chronicler_root.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"
    if derived.is_file():
        return derived

    repo_copy = _REPO_ROOT / "config" / "project_registry.json"
    if repo_copy.is_file():
        return repo_copy

    raise FileNotFoundError(
        "cannot locate project_registry.json -- set CHRONICLER_REGISTRY_PATH, or "
        f"ship it to {derived}, or keep the authoring copy at {repo_copy}.")


# ---------------------------------------------------------------------------
# Registry -- the set of ids a ruling is allowed to assign
# ---------------------------------------------------------------------------
def load_registry(source) -> dict:
    """Return ``{id: {...}}`` for every link-target the endpoint accepts, across
    all three tiers (DECISIONS 0012).

    `source` is a path (str/Path) or an already-parsed dict.

    **A ruling may be made at any tier.** A thread may genuinely be about a whole
    program ("how should L5GN OS handle config?"), a project ("Citadel's plugin
    lifecycle"), or one specific incarnation ("the smelt-gateway rewrite"), and
    forcing the human to pick a tier the evidence does not support is how you get
    junk rulings. Each entry carries `tier`, `program`, `project` and a
    `hierarchy` breadcrumb so the UI can show the context around whatever is
    being ruled on.

    Every target is keyed by **id**, the single identifier scheme -- the same one
    relink writes (round-3 D.3). Before that decision, this endpoint wrote ids
    and relink wrote canonical_names into the same `threads.project_link` column.

    Legacy flat registries (no `programs` key) still load, with every project
    reported at the project tier and no hierarchy. That keeps a stale registry
    usable read-only rather than taking the review surface down, but
    build_registry should be re-run to regenerate the tiers.
    """
    if isinstance(source, dict):
        data = source
    else:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

    scope_to_root = {"l5gn": "L5GN", "mcf": "MCF"}
    out: dict[str, dict] = {}
    programs = {p["id"]: p for p in data.get("programs", []) if p.get("id")}

    def _add(entry: dict, tier: str, program: str | None, project: str | None):
        pid = entry.get("id")
        if not pid:
            return
        root = scope_to_root.get(entry.get("scope"))
        canon = entry.get("canonical_name") or entry.get("name") or pid
        crumbs = []
        if program and program in programs:
            crumbs.append(programs[program].get("name", program))
        if project and project != pid and project in out:
            crumbs.append(out[project]["canonical_name"])
        crumbs.append(canon)
        out[pid] = {
            "id": pid,
            "canonical_name": canon,
            "tier": tier,
            "program": program,
            "project": project,
            "hierarchy": " > ".join(crumbs),
            "repo_folder_path": (f"{root}/{canon}" if root else None),
            "account_scope": entry.get("account_scope") or [],
            "estate": entry.get("estate"),
            # Retained for the existing UI sort: repo-tier entries are the
            # "finer" targets the flat schema called sub-projects.
            "is_sub": tier == "repo",
        }

    for prog in data.get("programs", []):
        _add(prog, "program", prog.get("id"), None)

    for p in data.get("projects", []):
        _add(p, "project", p.get("program"), p.get("id"))
        for repo in p.get("repos") or []:
            if isinstance(repo, dict):
                repo.setdefault("scope", p.get("scope"))
                _add(repo, "repo", p.get("program"), p.get("id"))
        # Legacy flat shape: dict-shaped sub_projects were the old finer targets.
        for sp in p.get("sub_projects") or []:
            if isinstance(sp, dict):
                _add(sp, "repo", p.get("program"), p.get("id"))
    return out


def valid_project_ids(registry: dict) -> set[str]:
    return set(registry.keys())


# ---------------------------------------------------------------------------
# Read side -- pending rulings with enough context to decide (round-2 C.1)
# ---------------------------------------------------------------------------
def pending_rulings(conn: sqlite3.Connection) -> list[dict]:
    """Pending project-link queue rows joined with thread context.

    Estate/account-agnostic (DECISIONS 0010): no filtering or grouping by estate
    or account -- but the thread's `account` IS surfaced per row, informationally.
    Rows whose thread is already `project_confidence='manual'` are excluded, so a
    completed ruling drops off the list WITHOUT the endpoint ever writing
    review_queue -- the queue row stays pending (pipeline-owned) and the manual
    confidence is the real signal. That is deliberate column-scope discipline.
    """
    rows = conn.execute(
        """
        SELECT q.item_id, q.type, q.thread_id, q.confidence, q.status, q.note,
               q.created_at AS queued_at,
               t.title, t.account, t.source, t.created_at AS thread_created_at,
               t.project_link, t.project_confidence,
               (SELECT m.content FROM messages m
                 WHERE m.thread_id = t.thread_id
                 ORDER BY m.seq ASC LIMIT 1) AS first_message
          FROM review_queue q
          LEFT JOIN threads t ON t.thread_id = q.thread_id
         WHERE q.status = 'pending'
           AND q.type IN ('project_link', 'link_ambiguous', 'link_downgrade')
           AND COALESCE(t.project_confidence, '') <> 'manual'
         ORDER BY q.confidence DESC NULLS LAST, q.item_id ASC
        """
    ).fetchall()

    out = []
    for r in rows:
        snippet = (r["first_message"] or "")
        snippet = snippet.replace("\n", " ").strip()
        if len(snippet) > 240:
            snippet = snippet[:240] + "…"
        out.append({
            "item_id": r["item_id"],
            "type": r["type"],
            "thread_id": r["thread_id"],
            "title": r["title"],
            "account": r["account"],
            "source": r["source"],
            "thread_created_at": r["thread_created_at"],
            "confidence": r["confidence"],
            "note": r["note"],
            "current_link": r["project_link"],
            "current_confidence": r["project_confidence"],
            "snippet": snippet,
        })
    return out


# ---------------------------------------------------------------------------
# Write side -- the whole point. Two columns, validated, or nothing. (C.2, C.6)
# ---------------------------------------------------------------------------
def _upsert_project(conn: sqlite3.Connection, entry: dict) -> None:
    """Ensure a projects row keyed by the registry id exists, so the
    threads.project_link FK holds. Idempotent (ON CONFLICT COALESCE) and derived
    purely from registry identity -- safe for both writers to run."""
    conn.execute(
        """INSERT INTO projects (project_id, name, repo_folder_path, source_system_id)
           VALUES (?, ?, ?, NULL)
           ON CONFLICT(project_id) DO UPDATE SET
             repo_folder_path = COALESCE(projects.repo_folder_path, excluded.repo_folder_path)""",
        (entry["id"], entry["canonical_name"], entry["repo_folder_path"]),
    )


def apply_ruling(conn: sqlite3.Connection, thread_id: str, project_id: str,
                 registry: dict) -> dict:
    """Apply one human project-link ruling. Writes ONLY threads.project_link and
    threads.project_confidence='manual'. Validates loudly; commits atomically.

    Raises ValueError (nothing written) if the thread is unknown or the
    project_id is not present in the shipped registry -- never silently writes an
    id the registry can't explain (round-2 C.6; INTENT 5 "fail loud, never
    silently wrong").
    """
    if project_id not in registry:
        raise ValueError(
            f"unknown project id {project_id!r}: not in the shipped registry "
            f"({len(registry)} known ids). Refusing to write garbage.")

    row = conn.execute(
        "SELECT project_link, project_confidence FROM threads WHERE thread_id=?",
        (thread_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown thread id {thread_id!r}: not in threads.")

    prev_link = row["project_link"]
    prev_conf = row["project_confidence"]
    entry = registry[project_id]

    # projects identity row first (FK target), then the two-column ruling.
    _upsert_project(conn, entry)
    conn.execute(
        "UPDATE threads SET project_link=?, project_confidence=? WHERE thread_id=?",
        (project_id, MANUAL_CONFIDENCE, thread_id),
    )
    conn.commit()

    return {
        "thread_id": thread_id,
        "project_id": project_id,
        "canonical_name": entry["canonical_name"],
        "project_confidence": MANUAL_CONFIDENCE,
        "previous_link": prev_link,
        "previous_confidence": prev_conf,
    }


def thread_columns(conn: sqlite3.Connection, thread_id: str) -> dict:
    """Full column snapshot of one thread row -- used by the hermetic tester to
    prove no column other than the two ruling columns ever changes."""
    row = conn.execute("SELECT * FROM threads WHERE thread_id=?", (thread_id,)).fetchone()
    return dict(row) if row is not None else {}
