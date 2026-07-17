"""vault_reader -- read-only view of the Chronicler chat vault, mapped to the estate.

Consumes the frozen ``chronicler.db`` (SQLite, source of truth for chat history)
and emits per-project rollups that line up with estate.json project names, so the
knight can join "what was discussed" against "what the code did". Strictly
read-only: opens the DB with ``mode=ro`` and issues SELECTs only -- it can never
mutate Chronicler's truth. ``sqlite3`` is stdlib, so this honours the toolkit's
stdlib-only + read-only contract natively.

Vault path resolution (first hit wins):
    1. this machine's config ``vault`` key (set on the knight)
    2. ``CHRONICLER_DB_PATH`` env var (matches Chronicler's own override)
    3. a sibling ``Chronicler/chronicler.db`` under the estate root (local dev)
Absent all three -> ``status: no_vault`` (the normal case on a producer rig).

The account dimension (claude-personal / gemini-personal / gemini-work) is carried
explicitly on every rollup and never merged into a single work+personal figure --
that is the work/personal wall, enforced in the data shape rather than by trust.

Estate tool, excluded from ``build`` (``SKIP_IN_BUILD``) -- it reads an external
DB, not the live repos, and belongs to the knight's interpret sweep.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from ..common import ESTATE_ROOT
from ..contract import SAFE

NAME = "vault_reader"
DESCRIPTION = "Read-only rollup of the Chronicler chat vault, joined to estate projects."
ESTATE_LEVEL = True
SAFETY = SAFE
SKIP_IN_BUILD = True

EXPECTED_USER_VERSION = 1


def _resolve_vault_path() -> Path | None:
    from .. import config
    for cand in (config.machine().get("vault"), os.environ.get("CHRONICLER_DB_PATH")):
        if cand and Path(cand).exists():
            return Path(cand)
    sibling = ESTATE_ROOT / "Chronicler" / "chronicler.db"
    return sibling if sibling.exists() else None


def _connect_ro(path: Path) -> sqlite3.Connection:
    # as_uri() yields a correct file URI on every platform; mode=ro guarantees
    # we cannot create a journal or write a single byte into the vault.
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


def scan_estate(projects: list[Path]) -> dict:
    vault = _resolve_vault_path()
    if vault is None:
        return {"status": "no_vault",
                "note": "No Chronicler vault found (config 'vault', CHRONICLER_DB_PATH, "
                        "or sibling Chronicler/chronicler.db)."}
    try:
        conn = _connect_ro(vault)
    except sqlite3.Error as exc:
        return {"status": "error", "vault_path": str(vault), "error": str(exc)}
    try:
        return _read(conn, vault, projects)
    finally:
        conn.close()


def _read(conn: sqlite3.Connection, vault: Path, projects: list[Path]) -> dict:
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    meta: dict = {}
    try:
        meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    except sqlite3.Error:
        pass

    if user_version != EXPECTED_USER_VERSION:
        return {"status": "schema_mismatch", "vault_path": str(vault),
                "found_user_version": user_version,
                "expected_user_version": EXPECTED_USER_VERSION, "meta": meta,
                "note": "Vault schema differs from what vault_reader expects; refusing "
                        "to interpret. Re-run finalize on the vault or bump the reader."}

    total_threads = conn.execute("SELECT count(*) FROM threads").fetchone()[0]
    total_messages = conn.execute("SELECT count(*) FROM messages").fetchone()[0]
    substantive_threads = conn.execute(
        "SELECT count(*) FROM threads WHERE substantive = 1").fetchone()[0]
    linked_threads = conn.execute(
        "SELECT count(*) FROM threads WHERE project_link IS NOT NULL").fetchone()[0]

    by_account = {a: {"threads": t, "substantive": s or 0} for a, t, s in conn.execute(
        "SELECT account, count(*), sum(substantive) FROM threads GROUP BY account")}
    by_source = dict(conn.execute(
        "SELECT source, count(*) FROM threads GROUP BY source"))

    # Per-project aggregates, keyed by projects.project_id.
    thr_rows = {pid: (name, rfp, thr, sub or 0, latest)
                for pid, name, rfp, thr, sub, latest in conn.execute(
        "SELECT p.project_id, p.name, p.repo_folder_path, count(t.thread_id), "
        "sum(t.substantive), max(t.updated_at) "
        "FROM projects p LEFT JOIN threads t ON t.project_link = p.project_id "
        "GROUP BY p.project_id")}
    msg_by_pid = dict(conn.execute(
        "SELECT t.project_link, count(m.message_id) FROM messages m "
        "JOIN threads t ON m.thread_id = t.thread_id "
        "WHERE t.project_link IS NOT NULL GROUP BY t.project_link"))
    acct_by_pid: dict = {}
    for pid, acct, n in conn.execute(
        "SELECT project_link, account, count(*) FROM threads "
        "WHERE project_link IS NOT NULL GROUP BY project_link, account"):
        acct_by_pid.setdefault(pid, {})[acct] = n
    conf_by_pid: dict = {}
    for pid, conf, n in conn.execute(
        "SELECT project_link, project_confidence, count(*) FROM threads "
        "WHERE project_link IS NOT NULL GROUP BY project_link, project_confidence"):
        conf_by_pid.setdefault(pid, {})[conf or "null"] = n
    ev_by_name: dict = {}
    for name, sig, n in conn.execute(
        "SELECT project, signal, count(*) FROM link_evidence GROUP BY project, signal"):
        ev_by_name.setdefault(name, {})[sig] = n

    estate_names = {p.name for p in projects} if projects else None
    repo_projects: list[dict] = []
    concept_projects: list[dict] = []
    for pid, (name, rfp, thr, sub, latest) in thr_rows.items():
        row = {"vault_project": name, "project_id": pid, "threads": thr,
               "substantive_threads": sub, "messages": msg_by_pid.get(pid, 0),
               "latest_activity": latest, "by_account": acct_by_pid.get(pid, {}),
               "by_confidence": conf_by_pid.get(pid, {}),
               "evidence_signals": ev_by_name.get(name, {})}
        if rfp:
            estate, _, tail = rfp.replace("\\", "/").partition("/")
            row["repo_folder_path"] = rfp
            row["estate"] = estate
            row["estate_project"] = tail or name
            row["present_in_estate"] = (
                (tail or name) in estate_names if estate_names is not None else None)
            repo_projects.append(row)
        else:
            row.pop("by_confidence", None)
            row.pop("evidence_signals", None)
            concept_projects.append(row)

    repo_projects.sort(key=lambda x: x["vault_project"].lower())
    concept_projects.sort(key=lambda x: x["vault_project"].lower())

    unlinked_by_account = {a: {"threads": t, "substantive": s or 0}
                           for a, t, s in conn.execute(
        "SELECT account, count(*), sum(substantive) FROM threads "
        "WHERE project_link IS NULL GROUP BY account")}

    return {
        "status": "ok",
        "vault_path": str(vault),
        "schema_version": meta.get("schema_version"),
        "user_version": user_version,
        "totals": {
            "threads": total_threads,
            "messages": total_messages,
            "substantive_threads": substantive_threads,
            "linked_threads": linked_threads,
            "unlinked_threads": total_threads - linked_threads,
            "by_account": by_account,
            "by_source": by_source,
        },
        "projects": repo_projects,
        "vault_projects_without_repo": concept_projects,
        "unlinked": {"threads": total_threads - linked_threads,
                     "by_account": unlinked_by_account},
    }
