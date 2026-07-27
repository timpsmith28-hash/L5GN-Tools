"""tester_relink_apply: relink.apply_decision writes the structured
candidate_project / rival_project columns (Command Deck prototype, Task 1).

Hermetic: seeds a throwaway sqlite DB with the real schema.sql, drives
relink.apply_decision directly with synthetic decision dicts (no scoring, no
registry file on disk), and asserts what landed in review_queue -- both the
note text (unchanged shape) and the new structured columns.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
_SCHEMA = _PIPE / "schema.sql"

_REGISTRY = {
    "l5gn-os": {"id": "l5gn-os", "tier": "project", "canonical_name": "L5GN OS",
                "project": None, "program_name": None},
    "chancellor": {"id": "chancellor", "tier": "repo", "canonical_name": "Chancellor",
                   "project": "l5gn-os", "program_name": None},
    "crystal-spire": {"id": "crystal-spire", "tier": "project",
                       "canonical_name": "Crystal Spire", "project": None,
                       "program_name": None},
}


def _cand(project, adjusted=0.75, summary="evidence summary"):
    return {"project": project, "adjusted": adjusted, "summary": summary}


def _seed(conn):
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    for tid in ("T1", "T2", "T3"):
        conn.execute(
            "INSERT INTO threads (thread_id, source, account, title, created_at, "
            "project_link, project_confidence) VALUES (?, 'claude', 'claude-personal', "
            "'thread', '2026-06-01T00:00:00Z', NULL, NULL)", (tid,))
    conn.commit()


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import relink

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        _seed(conn)
        now = "2026-07-27T00:00:00Z"

        # --- suggest: candidate_project set, rival_project NULL ---
        thread = conn.execute("SELECT * FROM threads WHERE thread_id='T1'").fetchone()
        dec = {"category": "suggest", "best": _cand("chancellor")}
        relink.apply_decision(conn, thread, dec, _REGISTRY, now)
        conn.commit()
        row = conn.execute(
            "SELECT candidate_project, rival_project, note FROM review_queue "
            "WHERE thread_id='T1' AND type='project_link'").fetchone()
        if row is None:
            v.append("suggest: no review_queue row written")
        else:
            if row["candidate_project"] != "chancellor":
                v.append(f"suggest: candidate_project={row['candidate_project']!r}, want 'chancellor'")
            if row["rival_project"] is not None:
                v.append(f"suggest: rival_project={row['rival_project']!r}, want NULL")
            if "suggest -> chancellor (" not in row["note"]:
                v.append(f"suggest: note shape changed, id not parseable: {row['note']!r}")

        # --- ambiguous: both candidate_project and rival_project set ---
        thread = conn.execute("SELECT * FROM threads WHERE thread_id='T2'").fetchone()
        dec = {"category": "ambiguous", "best": _cand("l5gn-os", 0.70),
               "second": _cand("crystal-spire", 0.65)}
        relink.apply_decision(conn, thread, dec, _REGISTRY, now)
        conn.commit()
        row = conn.execute(
            "SELECT candidate_project, rival_project, note FROM review_queue "
            "WHERE thread_id='T2' AND type='link_ambiguous'").fetchone()
        if row is None:
            v.append("ambiguous: no review_queue row written")
        else:
            if row["candidate_project"] != "l5gn-os":
                v.append(f"ambiguous: candidate_project={row['candidate_project']!r}, want 'l5gn-os'")
            if row["rival_project"] != "crystal-spire":
                v.append(f"ambiguous: rival_project={row['rival_project']!r}, want 'crystal-spire'")
            if "VS crystal-spire (" not in row["note"]:
                v.append(f"ambiguous: note shape changed, rival id not parseable: {row['note']!r}")

        # --- downgrade: candidate_project set, rival_project NULL ---
        thread = conn.execute("SELECT * FROM threads WHERE thread_id='T3'").fetchone()
        dec = {"category": "downgrade", "best": _cand("crystal-spire"), "cur_name": "Old Fuzzy Name"}
        relink.apply_decision(conn, thread, dec, _REGISTRY, now)
        conn.commit()
        row = conn.execute(
            "SELECT candidate_project, rival_project, note FROM review_queue "
            "WHERE thread_id='T3' AND type='link_downgrade'").fetchone()
        if row is None:
            v.append("downgrade: no review_queue row written")
        else:
            if row["candidate_project"] != "crystal-spire":
                v.append(f"downgrade: candidate_project={row['candidate_project']!r}, want 'crystal-spire'")
            if row["rival_project"] is not None:
                v.append(f"downgrade: rival_project={row['rival_project']!r}, want NULL")

        conn.close()

    return v
