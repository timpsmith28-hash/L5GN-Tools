"""tester_review: the write endpoint's core (DECISIONS 0007 stage 2, round-2 C.6).

Hermetic and stdlib-only -- exercises the real write path against a throwaway
sqlite DB, no FastAPI, no uvicorn, no server bind. Two load-bearing guarantees:

  1. A ruling mutates ONLY threads.project_link + threads.project_confidence.
     Every other threads column, and every link_evidence / review_queue row, is
     byte-for-byte unchanged (this is the single-writer column-scope guarantee).
  2. project_link only accepts ids present in the shipped registry: an unknown id
     (or unknown thread) raises loudly and writes NOTHING.
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from chronicler.review import core

_SCHEMA = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline" / "schema.sql"

# A minimal but structurally-real registry (dict source, both shapes of sub_project).
_REGISTRY_DOC = {
    "projects": [
        {"id": "l5gn-os", "canonical_name": "L5GN OS", "scope": "l5gn",
         "account_scope": ["gemini-work"], "estate": "work",
         "sub_projects": [
             {"id": "chancellor", "canonical_name": "Chancellor"},   # dict -> a target
         ]},
        {"id": "crystal-spire", "canonical_name": "Crystal Spire",
         "account_scope": ["claude-personal"], "estate": "personal",
         "sub_projects": ["Smelt Gateway", "Bare Name"]},            # strings -> NOT targets
    ]
}


def _seed(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    # A thread carrying a pre-existing (untrusted) fuzzy link + non-default values
    # in every other column, so any stray write shows up as a diff.
    conn.execute(
        """INSERT INTO threads
           (thread_id, source, account, title, created_at, updated_at, gem_name,
            is_custom_gem, status, closed_at, project_link, project_confidence,
            review_status, raw_ref, parser_version, review_note, suggested_close,
            tags, link_evidence_ids)
           VALUES ('T1','gemini','gemini-work','Sovereign Engine planning',
                   '2026-06-01T00:00:00Z','2026-06-02T00:00:00Z','Gemmy',
                   1,'open',NULL,NULL,'fuzzy',
                   'pending','raw/T1.json','p/1.0','look at me',1,
                   '["keep","these"]','[11,22]')""")
    conn.execute("INSERT INTO messages (message_id, thread_id, seq, role, content, created_at) "
                 "VALUES ('M1','T1',0,'user','First message body','2026-06-01T00:00:00Z')")
    conn.execute("INSERT INTO link_evidence (thread_id, project, signal, weight, detail, "
                 "produced_at, producer_version) VALUES ('T1','L5GN OS','filename_xref',0.7,"
                 "'engine.py','2026-06-01T00:00:00Z','s4/1.0')")
    conn.execute("INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at) "
                 "VALUES ('project_link','T1',0.72,'pending','suggest -> L5GN OS','2026-06-01T00:00:00Z')")
    conn.commit()


def _snapshot(conn: sqlite3.Connection) -> dict:
    return {
        "thread": core.thread_columns(conn, "T1"),
        "evidence": [dict(r) for r in conn.execute(
            "SELECT * FROM link_evidence ORDER BY evidence_id")],
        "queue": [dict(r) for r in conn.execute(
            "SELECT * FROM review_queue ORDER BY item_id")],
    }


def run() -> list[str]:
    v: list[str] = []
    registry = core.load_registry(_REGISTRY_DOC)

    # --- registry loading: ids, sub-project shapes ---
    ids = core.valid_project_ids(registry)
    if ids != {"l5gn-os", "chancellor", "crystal-spire"}:
        v.append(f"registry: wrong id set {sorted(ids)} "
                 "(dict sub_project should count, string sub_projects should not)")
    if registry.get("l5gn-os", {}).get("repo_folder_path") != "L5GN/L5GN OS":
        v.append("registry: scope->repo_folder_path derivation wrong for l5gn-os")

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        _seed(conn)

        before = _snapshot(conn)

        # --- read side surfaces the pending row (with account, informationally) ---
        pend = core.pending_rulings(conn)
        if len(pend) != 1 or pend[0]["thread_id"] != "T1":
            v.append(f"pending_rulings: expected 1 row for T1, got {pend}")
        elif pend[0]["account"] != "gemini-work":
            v.append("pending_rulings: account not surfaced per-thread (0010)")

        # --- unknown id: raise, write nothing ---
        try:
            core.apply_ruling(conn, "T1", "no-such-project", registry)
            v.append("apply_ruling: unknown project id was NOT rejected")
        except ValueError:
            if _snapshot(conn) != before:
                v.append("apply_ruling: unknown id rejected but DB was mutated")

        # --- unknown thread: raise, write nothing ---
        try:
            core.apply_ruling(conn, "GHOST", "l5gn-os", registry)
            v.append("apply_ruling: unknown thread id was NOT rejected")
        except ValueError:
            if _snapshot(conn) != before:
                v.append("apply_ruling: unknown thread rejected but DB was mutated")

        # --- valid ruling: exactly two columns change ---
        res = core.apply_ruling(conn, "T1", "chancellor", registry)
        if res["previous_confidence"] != "fuzzy" or res["canonical_name"] != "Chancellor":
            v.append(f"apply_ruling: return payload wrong: {res}")

        after = _snapshot(conn)
        tb, ta = before["thread"], after["thread"]
        changed = {k for k in tb if tb[k] != ta.get(k)}
        if changed != {"project_link", "project_confidence"}:
            v.append(f"apply_ruling: changed columns {sorted(changed)} "
                     "-- MUST be exactly {'project_link','project_confidence'}")
        if ta.get("project_link") != "chancellor":
            v.append(f"apply_ruling: project_link={ta.get('project_link')!r}, want 'chancellor'")
        if ta.get("project_confidence") != "manual":
            v.append(f"apply_ruling: project_confidence={ta.get('project_confidence')!r}, want 'manual'")

        # --- pipeline-owned tables untouched ---
        if before["evidence"] != after["evidence"]:
            v.append("apply_ruling: link_evidence was modified (must never be touched)")
        if before["queue"] != after["queue"]:
            v.append("apply_ruling: review_queue was modified (must never be touched)")

        # --- projects identity row created for the FK, keyed by id ---
        prow = conn.execute("SELECT project_id, name FROM projects WHERE project_id='chancellor'").fetchone()
        if prow is None or prow["name"] != "Chancellor":
            v.append("apply_ruling: projects identity row not upserted for the FK")

        # --- ruled thread drops off the pending list (via manual conf, not a queue write) ---
        if any(p["thread_id"] == "T1" for p in core.pending_rulings(conn)):
            v.append("pending_rulings: ruled (manual) thread still appears in the queue")

        conn.close()

    # --- registry path resolution honours the explicit env override ---
    import os
    saved = os.environ.pop("CHRONICLER_REGISTRY_PATH", None)
    try:
        os.environ["CHRONICLER_REGISTRY_PATH"] = "/tmp/whatever/registry.json"
        if core.resolve_registry_path() != Path("/tmp/whatever/registry.json"):
            v.append("resolve_registry_path: CHRONICLER_REGISTRY_PATH override not honoured")
    finally:
        os.environ.pop("CHRONICLER_REGISTRY_PATH", None)
        if saved is not None:
            os.environ["CHRONICLER_REGISTRY_PATH"] = saved

    return v
