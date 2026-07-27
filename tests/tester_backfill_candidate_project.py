"""tester_backfill_candidate_project: the Command Deck Task 1 backfill script.

Hermetic: no live vault, no network. Exercises `parse_note` directly against
the exact note shapes `relink.apply_decision`'s `lbl()` writes, then drives
`run()` end-to-end against a throwaway sqlite DB (real schema.sql) with
CHRONICLER_HOME/CHRONICLER_REGISTRY_PATH pointed at a temp registry, asserting
the resolved/unresolved split and that only NULL rows are touched (idempotent
re-run).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
_SCHEMA = _PIPE / "schema.sql"

_REGISTRY_DOC = {
    "programs": [],
    "projects": [
        {"id": "l5gn-os", "canonical_name": "L5GN OS", "scope": "l5gn",
         "repos": [{"id": "chancellor", "canonical_name": "Chancellor"}]},
        {"id": "crystal-spire", "canonical_name": "Crystal Spire", "scope": "l5gn"},
    ],
}


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import backfill_candidate_project as bcp

    # --- parse_note: the three note shapes lbl() actually produces ---
    cand, rival, reason = bcp.parse_note(
        "project_link",
        "suggest -> chancellor (L5GN OS > Chancellor) (adjusted=0.830); evidence: x")
    if (cand, rival, reason) != ("chancellor", None, None):
        v.append(f"parse_note/suggest: got {(cand, rival, reason)}")

    cand, rival, reason = bcp.parse_note(
        "link_ambiguous",
        "ambiguous: l5gn-os (L5GN OS) (adjusted=0.700; e1) VS "
        "crystal-spire (Crystal Spire) (adjusted=0.650; e2)")
    if (cand, rival, reason) != ("l5gn-os", "crystal-spire", None):
        v.append(f"parse_note/ambiguous: got {(cand, rival, reason)}")

    cand, rival, reason = bcp.parse_note(
        "link_downgrade",
        "downgrade: existing fuzzy link -> 'Old Name' now contradicted; new "
        "evidence points to crystal-spire (Crystal Spire) (adjusted=0.800); evidence: x")
    if (cand, rival, reason) != ("crystal-spire", None, None):
        v.append(f"parse_note/downgrade: got {(cand, rival, reason)}")

    # --- unparseable / unresolvable notes are reported, never guessed ---
    cand, rival, reason = bcp.parse_note("project_link", "some unrelated free text")
    if reason is None or cand is not None:
        v.append("parse_note: garbage note should be unresolved, not guessed")

    # --- end-to-end run() against a throwaway DB + registry ---
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        db_path = tdp / "chronicler.db"
        registry_path = tdp / "project_registry.json"
        registry_path.write_text(json.dumps(_REGISTRY_DOC), encoding="utf-8")

        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        for tid in ("T1", "T2", "T3"):
            conn.execute(
                "INSERT INTO threads (thread_id, source, account, title, created_at) "
                "VALUES (?, 'claude', 'claude-personal', 't', '2026-06-01T00:00:00Z')", (tid,))
        # resolvable
        conn.execute(
            "INSERT INTO review_queue (type, thread_id, status, note, created_at) "
            "VALUES ('project_link', 'T1', 'pending', "
            "'suggest -> chancellor (L5GN OS > Chancellor) (adjusted=0.830); evidence: x', "
            "'2026-06-01T00:00:00Z')")
        # unresolvable: id not in this registry
        conn.execute(
            "INSERT INTO review_queue (type, thread_id, status, note, created_at) "
            "VALUES ('project_link', 'T2', 'pending', "
            "'suggest -> ghost-project (Ghost) (adjusted=0.700); evidence: x', "
            "'2026-06-01T00:00:00Z')")
        # already backfilled -- must be left untouched by a re-run
        conn.execute(
            "INSERT INTO review_queue "
            "(type, thread_id, status, note, created_at, candidate_project) "
            "VALUES ('project_link', 'T3', 'pending', "
            "'suggest -> crystal-spire (Crystal Spire) (adjusted=0.900); evidence: x', "
            "'2026-06-01T00:00:00Z', 'crystal-spire')")
        conn.commit()
        conn.close()

        saved_home = os.environ.get("CHRONICLER_HOME")
        saved_db = os.environ.get("CHRONICLER_DB_PATH")
        saved_reg = os.environ.get("CHRONICLER_REGISTRY_PATH")
        os.environ["CHRONICLER_HOME"] = str(tdp)
        os.environ["CHRONICLER_DB_PATH"] = str(db_path)
        os.environ["CHRONICLER_REGISTRY_PATH"] = str(registry_path)
        try:
            # db.py / relink module cache CHRONICLER_ROOT/DB_PATH at import time --
            # reimport fresh so this run picks up the env set just above.
            for mod in ("db", "relink", "backfill_candidate_project"):
                sys.modules.pop(mod, None)
            import backfill_candidate_project as bcp2

            n_unresolved = bcp2.run(apply=False)
            if n_unresolved != 1:
                v.append(f"run(dry-run): expected 1 unresolved (T2), got {n_unresolved}")

            # dry-run must not write
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT candidate_project FROM review_queue WHERE thread_id='T1'").fetchone()
            if row["candidate_project"] is not None:
                v.append("run(dry-run): wrote candidate_project despite no --apply")
            conn.close()

            bcp2.run(apply=True)
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            t1 = conn.execute(
                "SELECT candidate_project, rival_project FROM review_queue "
                "WHERE thread_id='T1'").fetchone()
            if t1["candidate_project"] != "chancellor":
                v.append(f"run(apply): T1 candidate_project={t1['candidate_project']!r}, want 'chancellor'")
            t2 = conn.execute(
                "SELECT candidate_project FROM review_queue WHERE thread_id='T2'").fetchone()
            if t2["candidate_project"] is not None:
                v.append("run(apply): T2 (unresolvable) must stay NULL, never guessed")
            t3 = conn.execute(
                "SELECT candidate_project FROM review_queue WHERE thread_id='T3'").fetchone()
            if t3["candidate_project"] != "crystal-spire":
                v.append("run(apply): T3 (already backfilled) must be left untouched")
            conn.close()
        finally:
            for var, saved in (("CHRONICLER_HOME", saved_home),
                               ("CHRONICLER_DB_PATH", saved_db),
                               ("CHRONICLER_REGISTRY_PATH", saved_reg)):
                if saved is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = saved
            for mod in ("db", "relink", "backfill_candidate_project"):
                sys.modules.pop(mod, None)

    return v
