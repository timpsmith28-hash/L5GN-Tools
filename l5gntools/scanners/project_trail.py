"""project_trail -- per estate-project discussion trail from the chat vault (S7).

Reverse-enrichment: for each estate project, list the threads that discuss it,
newest-first (substantive threads ahead of fragments), each tagged with its link
confidence and authority rank. This is the feed that keeps an Intent/Contents-
style nav honest -- built from real chat linkage in the frozen vault rather than
an LLM's guess. Read-only; reuses vault_reader's path resolution + schema guard,
so the two stay in lockstep on where the vault is and what version is expected.

Estate tool, excluded from build (SKIP_IN_BUILD) -- part of the knight's
interpret sweep, not the producer's code snapshot.
"""
from __future__ import annotations

import sqlite3

from . import vault_reader
from ..contract import SAFE

NAME = "project_trail"
DESCRIPTION = "Per-project chat discussion trail (S7), newest-first, from the vault."
ESTATE_LEVEL = True
SAFETY = SAFE
SKIP_IN_BUILD = True

# Authority order per the freeze contract: none/NULL < fuzzy < evidence < exact
# (source-native) < manual (human). Used for display/ranking, not for sorting the
# trail (which is chronological, substantive-first).
_CONF_RANK = {None: 0, "null": 0, "none": 0, "fuzzy": 1, "evidence": 2,
              "exact": 3, "manual": 4}


def scan_estate(projects: list) -> dict:
    vault = vault_reader._resolve_vault_path()
    if vault is None:
        return {"status": "no_vault",
                "note": "No Chronicler vault found (config 'vault', CHRONICLER_DB_PATH, "
                        "or sibling Chronicler/chronicler.db)."}
    try:
        conn = vault_reader._connect_ro(vault)
    except sqlite3.Error as exc:
        return {"status": "error", "vault_path": str(vault), "error": str(exc)}
    try:
        return _read(conn, vault, projects)
    finally:
        conn.close()


def _read(conn: sqlite3.Connection, vault, projects: list) -> dict:
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    if user_version != vault_reader.EXPECTED_USER_VERSION:
        return {"status": "schema_mismatch", "vault_path": str(vault),
                "found_user_version": user_version,
                "expected_user_version": vault_reader.EXPECTED_USER_VERSION,
                "note": "Vault schema differs from expected; refusing to interpret."}
    meta: dict = {}
    try:
        meta = {k: v for k, v in conn.execute("SELECT key, value FROM meta")}
    except sqlite3.Error:
        pass

    repo = {pid: (name, rfp) for pid, name, rfp in conn.execute(
        "SELECT project_id, name, repo_folder_path FROM projects "
        "WHERE repo_folder_path IS NOT NULL")}
    concept = {pid: name for pid, name in conn.execute(
        "SELECT project_id, name FROM projects WHERE repo_folder_path IS NULL")}

    msg_by_thread = dict(conn.execute(
        "SELECT thread_id, count(*) FROM messages GROUP BY thread_id"))
    ev_by_name: dict = {}
    for name, sig, n in conn.execute(
        "SELECT project, signal, count(*) FROM link_evidence GROUP BY project, signal"):
        ev_by_name.setdefault(name, {})[sig] = n

    trails: dict = {}
    concept_activity: dict = {}
    for tid, title, source, account, updated, conf, review, sub, pid in conn.execute(
        "SELECT thread_id, title, source, account, updated_at, project_confidence, "
        "review_status, substantive, project_link FROM threads "
        "WHERE project_link IS NOT NULL"):
        rec = {"thread_id": tid, "title": title, "source": source, "account": account,
               "updated_at": updated, "project_confidence": conf,
               "confidence_rank": _CONF_RANK.get(conf, 0), "review_status": review,
               "substantive": bool(sub), "messages": msg_by_thread.get(tid, 0)}
        if pid in repo:
            trails.setdefault(pid, []).append(rec)
        elif pid in concept:
            concept_activity.setdefault(pid, []).append(rec)

    estate_names = {p.name for p in projects} if projects else None

    out_projects: list = []
    for pid, (name, rfp) in repo.items():
        trail = trails.get(pid, [])
        trail.sort(key=lambda t: (t["updated_at"] or ""), reverse=True)
        trail.sort(key=lambda t: 0 if t["substantive"] else 1)   # substantive first, stable
        estate, _, tail = rfp.replace("\\", "/").partition("/")
        estate_project = tail or name
        sigs = ev_by_name.get(name, {})
        out_projects.append({
            "estate_project": estate_project,
            "estate": estate,
            "vault_project": name,
            "present_in_estate": (estate_project in estate_names)
                                 if estate_names is not None else None,
            "thread_count": len(trail),
            "substantive_count": sum(1 for t in trail if t["substantive"]),
            "latest_activity": trail[0]["updated_at"] if trail else None,
            "dominant_signal": max(sigs, key=sigs.get) if sigs else None,
            "evidence_signals": sigs,
            "trail": trail,
        })
    out_projects.sort(key=lambda p: (p["latest_activity"] or ""), reverse=True)

    concept_out: list = []
    for pid, recs in concept_activity.items():
        recs.sort(key=lambda t: (t["updated_at"] or ""), reverse=True)
        concept_out.append({
            "vault_project": concept[pid],
            "thread_count": len(recs),
            "latest_activity": recs[0]["updated_at"] if recs else None,
            "accounts": sorted({r["account"] for r in recs}),
            "trail": recs,
        })
    concept_out.sort(key=lambda p: (p["latest_activity"] or ""), reverse=True)

    return {
        "status": "ok",
        "vault_path": str(vault),
        "schema_version": meta.get("schema_version"),
        "projects": out_projects,
        "concept_projects_with_activity": concept_out,
    }
