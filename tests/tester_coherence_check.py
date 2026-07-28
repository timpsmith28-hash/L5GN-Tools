"""coherence_check: Phase 3 measurement of local-store threads against the
personal Claude export, both already in the dev vault
(COWORK_BRIEF_local_transcript_intake.md).

Hermetic: primes sys.path for the vendored pipeline, builds a throwaway
sqlite DB with synthetic `claude-local` and `claude` threads exercising every
outcome the matcher and differ need to get right, and drives `run()`
directly against it via a monkeypatched `get_connection`. Read-only by
design (the module itself never writes), so there's nothing to prove idempotent
here -- the coverage is about matching and diffing correctness.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _schema(conn) -> None:
    conn.executescript(
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, source TEXT, account TEXT, title TEXT,"
        " created_at TEXT, updated_at TEXT);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT, seq INTEGER,"
        " role TEXT, content TEXT, created_at TEXT);"
    )


def _thread(conn, tid, source, account, title, created="2026-01-01T00:00:00Z"):
    conn.execute(
        "INSERT INTO threads (thread_id, source, account, title, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?)", (tid, source, account, title, created, created),
    )


def _msg(conn, mid, tid, seq, role, content):
    conn.execute(
        "INSERT INTO messages (message_id, thread_id, seq, role, content, created_at) "
        "VALUES (?,?,?,?,?,?)", (mid, tid, seq, role, content, "2026-01-01T00:00:00Z"),
    )


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import coherence_check as cc

    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "vault.db"
        conn = sqlite3.connect(str(db_path))
        _schema(conn)

        # 1. Exact title match, identical content -- should diff clean.
        _thread(conn, "L1", "claude-local", "claude-local-personal", "Fix the login bug")
        _msg(conn, "L1-0", "L1", 0, "user", "why does login fail")
        _msg(conn, "L1-1", "L1", 1, "assistant", "because of a stale token")
        _thread(conn, "E1", "claude", "claude-personal", "Fix the login bug")
        _msg(conn, "E1-0", "E1", 0, "user", "why does login fail")
        _msg(conn, "E1-1", "E1", 1, "assistant", "because of a stale token")

        # 2. Exact title match (case/whitespace-insensitive), DIFFERENT content
        #    -- must still match (title-based) but the diff must flag it.
        _thread(conn, "L2", "claude-local", "claude-local-personal", "  Refactor Auth Module  ")
        _msg(conn, "L2-0", "L2", 0, "user", "refactor the auth module please")
        _thread(conn, "E2", "claude", "claude-personal", "refactor auth module")
        _msg(conn, "E2-0", "E2", 0, "user", "refactor the auth module please")
        _msg(conn, "E2-1", "E2", 1, "assistant", "done, see the diff")
        _msg(conn, "E2-2", "E2", 2, "user", "thanks, one more thing")

        # 3. Near-title match (shares most words, not exact) -- must NOT be
        #    counted as an exact match, must appear in near_pairs, must NOT
        #    appear in local_only/export_only.
        _thread(conn, "L3", "claude-local", "claude-local-personal", "Debug the payment flow")
        _msg(conn, "L3-0", "L3", 0, "user", "payments are broken")
        _thread(conn, "E3", "claude", "claude-personal", "Debug payment flow issue")
        _msg(conn, "E3-0", "E3", 0, "user", "payments are broken")

        # 4. Local-only -- unique title, no export counterpart.
        _thread(conn, "L4", "claude-local", "claude-local-personal", "Census the transcript store")
        _msg(conn, "L4-0", "L4", 0, "user", "let's census the local transcript store")

        # 5. Export-only -- unique title, no local counterpart.
        _thread(conn, "E5", "claude", "claude-personal", "Plan the birthday trip")
        _msg(conn, "E5-0", "E5", 0, "user", "where should we go")

        # 6. A claude-local thread on a DIFFERENT account (e.g. work estate)
        #    -- must be excluded when local_account is scoped to personal.
        _thread(conn, "L6", "claude-local", "claude-local-work", "Fix the login bug")
        _msg(conn, "L6-0", "L6", 0, "user", "unrelated work session")

        conn.commit()
        conn.close()

        real_get_connection = cc.get_connection

        def _get_connection():
            c = sqlite3.connect(str(db_path))
            c.row_factory = sqlite3.Row
            return c

        cc.get_connection = _get_connection
        try:
            r = cc.run(export_account="claude-personal", local_account="claude-local-personal", sample=10)
        finally:
            cc.get_connection = real_get_connection

        if r["local_total"] != 4:  # L1, L2, L3, L4 -- L6 excluded by account scope
            v.append(f"local_total wrong (account scoping broken?): {r['local_total']}")
        if r["export_total"] != 4:  # E1, E2, E3, E5 (no E4 in this fixture)
            v.append(f"export_total wrong: {r['export_total']}")
        if r["exact_matches"] != 2:  # L1/E1, L2/E2
            v.append(f"exact_matches wrong: {r['exact_matches']}")
        if r["near_matches"] != 1:  # L3/E3
            v.append(f"near_matches wrong: {r['near_matches']}")
        if r["local_only"] != 1:  # L4
            v.append(f"local_only wrong: {r['local_only']}")
        if r["local_only_messages"] != 1:
            v.append(f"local_only_messages wrong: {r['local_only_messages']}")
        if r["export_only"] != 1:  # E5
            v.append(f"export_only wrong: {r['export_only']}")

        diffs = {d["local_thread_id"]: d for d in r["diffs_sampled"]}
        if "L1" not in diffs or not diffs["L1"]["same_message_count"] or not diffs["L1"]["same_role_sequence"]:
            v.append(f"L1/E1 should diff clean: {diffs.get('L1')}")
        if diffs["L1"]["content_similarity_ratio"] < 0.99:
            v.append(f"L1/E1 identical content should have ~1.0 similarity: {diffs['L1']}")

        if "L2" not in diffs or diffs["L2"]["same_message_count"]:
            v.append(f"L2/E2 should be flagged as differing message counts: {diffs.get('L2')}")

        near_titles = {(p["local_title"].strip(), p["export_title"]) for p in r["near_pairs_sample"]}
        if ("Debug the payment flow", "Debug payment flow issue") not in near_titles:
            v.append(f"near-title pair not surfaced correctly: {r['near_pairs_sample']}")

        # normalize_title / normalize_text / jaccard -- direct unit checks.
        if cc.normalize_title("  Hello   World ") != "hello world":
            v.append("normalize_title should collapse whitespace and lower-case")
        if cc.normalize_text("Line one\n\n  Line two") != "line one line two":
            v.append("normalize_text should collapse whitespace across lines")
        if cc.jaccard(set(), {"a"}) != 0.0:
            v.append("jaccard of an empty set should be 0.0, not a division error")

        # unscoped local_account -- should include every claude-local-* account.
        cc.get_connection = _get_connection
        try:
            r_all = cc.run(export_account="claude-personal", local_account=None, sample=10)
        finally:
            cc.get_connection = real_get_connection
        if r_all["local_total"] != 5:  # L1..L4 + L6
            v.append(f"unscoped local_account should include every account, got {r_all['local_total']}")

    return v
