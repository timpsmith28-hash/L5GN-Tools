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
           VALUES ('T1','gemini','gemini-personal','Sovereign Engine planning',
                   '2026-06-01T00:00:00Z','2026-06-02T00:00:00Z','Gemmy',
                   1,'open',NULL,NULL,'fuzzy',
                   'pending','raw/T1.json','p/1.0','look at me',1,
                   '["keep","these"]','[11,22]')""")
    conn.execute("INSERT INTO messages (message_id, thread_id, seq, role, content, created_at) "
                 "VALUES ('M1','T1',0,'user','First message body','2026-06-01T00:00:00Z')")
    conn.execute("INSERT INTO link_evidence (thread_id, project, signal, weight, detail, "
                 "produced_at, producer_version) VALUES ('T1','L5GN OS','filename_xref',0.7,"
                 "'engine.py','2026-06-01T00:00:00Z','s4/1.0')")
    conn.execute("INSERT INTO review_queue "
                 "(type, thread_id, confidence, status, note, created_at, candidate_project) "
                 "VALUES ('project_link','T1',0.72,'pending','suggest -> l5gn-os','2026-06-01T00:00:00Z',"
                 "'l5gn-os')")

    # T2: a link_ambiguous row with two real candidates -- the Task 2 rival case.
    conn.execute(
        """INSERT INTO threads
           (thread_id, source, account, title, created_at, updated_at, gem_name,
            is_custom_gem, status, closed_at, project_link, project_confidence,
            review_status, raw_ref, parser_version, review_note, suggested_close,
            tags, link_evidence_ids)
           VALUES ('T2','claude','claude-personal','Rival thread',
                   '2026-06-02T00:00:00Z','2026-06-02T00:00:00Z',NULL,
                   0,'open',NULL,NULL,NULL,
                   'pending','raw/T2.json','p/1.0',NULL,0,
                   '[]',NULL)""")
    conn.execute("INSERT INTO review_queue "
                 "(type, thread_id, confidence, status, note, created_at, "
                 "candidate_project, rival_project) "
                 "VALUES ('link_ambiguous','T2',0.68,'pending',"
                 "'ambiguous: l5gn-os (L5GN OS) VS crystal-spire (Crystal Spire)',"
                 "'2026-06-02T00:00:00Z','l5gn-os','crystal-spire')")

    # T3: already ruled manual -- must be excluded from every grouped view too.
    conn.execute(
        """INSERT INTO threads
           (thread_id, source, account, title, created_at, updated_at, gem_name,
            is_custom_gem, status, closed_at, project_link, project_confidence,
            review_status, raw_ref, parser_version, review_note, suggested_close,
            tags, link_evidence_ids)
           VALUES ('T3','claude','claude-personal','Already ruled',
                   '2026-06-03T00:00:00Z','2026-06-03T00:00:00Z',NULL,
                   0,'open',NULL,NULL,'manual',
                   'confirmed','raw/T3.json','p/1.0',NULL,0,
                   '[]',NULL)""")
    conn.execute("INSERT INTO review_queue "
                 "(type, thread_id, confidence, status, note, created_at, candidate_project) "
                 "VALUES ('project_link','T3',0.90,'pending','suggest -> chancellor',"
                 "'2026-06-03T00:00:00Z','chancellor')")
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

        # --- read side surfaces the pending rows (with account, informationally);
        #     T3 (already manual) must be excluded ---
        pend = core.pending_rulings(conn)
        pend_ids = {p["thread_id"] for p in pend}
        if pend_ids != {"T1", "T2"}:
            v.append(f"pending_rulings: expected {{T1,T2}}, got {pend_ids}")
        t1 = next((p for p in pend if p["thread_id"] == "T1"), None)
        if t1 is None or t1["account"] != "gemini-personal":
            v.append("pending_rulings: account not surfaced per-thread (0010)")
        if t1 is not None and t1["candidate_project"] != "l5gn-os":
            v.append(f"pending_rulings: T1 candidate_project={t1 and t1['candidate_project']!r}")

        # --- Task 6 / DECISIONS 0023: the wall. A work-account thread's pending
        #     suggestion must never surface, on either read path -- structurally,
        #     not via a flag the caller could forget to set ---
        conn.execute(
            """INSERT INTO threads
               (thread_id, source, account, title, created_at, project_link,
                project_confidence, review_status)
               VALUES ('TWORK','gemini','gemini-work','Work thread',
                       '2026-06-05T00:00:00Z',NULL,NULL,'pending')""")
        conn.execute(
            "INSERT INTO review_queue "
            "(type, thread_id, confidence, status, note, created_at, candidate_project) "
            "VALUES ('project_link','TWORK',0.80,'pending','suggest -> l5gn-os',"
            "'2026-06-05T00:00:00Z','l5gn-os')")
        conn.commit()
        if any(p["thread_id"] == "TWORK" for p in core.pending_rulings(conn)):
            v.append("wall: work-account thread appeared in unfiltered pending_rulings")
        if any(p["thread_id"] == "TWORK" for p in
               core.pending_rulings(conn, project_id="l5gn-os", registry=registry)):
            v.append("wall: work-account thread appeared in a project-filtered batch")
        wall_by_proj = {e["project_id"]: e for e in core.queue_by_project(conn, registry)}
        # l5gn-os already has T1's suggestion in its count at this point in the
        # run -- confirm TWORK did not add a second one.
        if wall_by_proj.get("l5gn-os", {}).get("counts", {}).get("suggestion", 0) != 1:
            v.append("wall: queue_by_project counted the work-account thread's row")

        # --- Task 2: queue_by_project groups pending rows by candidate,
        #     counting a link_ambiguous row under BOTH candidate and rival ---
        by_proj = {e["project_id"]: e for e in core.queue_by_project(conn, registry)}
        if set(by_proj) != {"l5gn-os", "crystal-spire"}:
            v.append(f"queue_by_project: expected l5gn-os+crystal-spire, got {set(by_proj)} "
                     "(T3's chancellor row is manual and must be excluded)")
        elif by_proj["l5gn-os"]["counts"] != {"suggestion": 1, "ambiguous": 1, "downgrade": 0}:
            v.append(f"queue_by_project: l5gn-os counts wrong: {by_proj['l5gn-os']['counts']}")
        elif by_proj["crystal-spire"]["counts"] != {"suggestion": 0, "ambiguous": 1, "downgrade": 0}:
            v.append(f"queue_by_project: crystal-spire counts wrong: "
                     f"{by_proj['crystal-spire']['counts']}")

        # --- Task 2: pending_rulings(project_id=...) surfaces the rival in BOTH
        #     projects' batches, marked is_rival in the one that isn't its
        #     candidate ---
        l5gn_batch = core.pending_rulings(conn, project_id="l5gn-os", registry=registry)
        cs_batch = core.pending_rulings(conn, project_id="crystal-spire", registry=registry)
        if {p["thread_id"] for p in l5gn_batch} != {"T1", "T2"}:
            v.append(f"pending_rulings(l5gn-os): expected T1+T2, got "
                     f"{[p['thread_id'] for p in l5gn_batch]}")
        if {p["thread_id"] for p in cs_batch} != {"T2"}:
            v.append(f"pending_rulings(crystal-spire): expected T2 only, got "
                     f"{[p['thread_id'] for p in cs_batch]}")
        cs_t2 = next((p for p in cs_batch if p["thread_id"] == "T2"), None)
        if cs_t2 is None or not cs_t2["is_rival"]:
            v.append("pending_rulings(crystal-spire): T2 should be marked is_rival=True there")
        l5gn_t2 = next((p for p in l5gn_batch if p["thread_id"] == "T2"), None)
        if l5gn_t2 is None or l5gn_t2["is_rival"]:
            v.append("pending_rulings(l5gn-os): T2 is the CANDIDATE there, is_rival should be False")

        # Snapshot AFTER all fixture inserts above (T2/T3/TWORK) so the
        # write-path tests below compare against the real steady state, not a
        # snapshot taken before this file's own test fixtures were inserted.
        before = _snapshot(conn)

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

        # --- Task 4: bulk accept -- one write per thread, partial failure visible ---
        before_batch = _snapshot(conn)
        results = core.apply_ruling_batch(
            conn, [("T2", "crystal-spire"), ("T2", "no-such-project")], registry)
        if len(results) != 2:
            v.append(f"apply_ruling_batch: expected 2 results, got {len(results)}")
        else:
            if not results[0]["ok"] or results[0].get("project_id") != "crystal-spire":
                v.append(f"apply_ruling_batch: valid pair should succeed: {results[0]}")
            if results[1]["ok"]:
                v.append("apply_ruling_batch: invalid project id should NOT succeed")
            elif "error" not in results[1]:
                v.append("apply_ruling_batch: failed pair must carry an 'error' message")
        t2_after_batch = conn.execute(
            "SELECT project_link, project_confidence FROM threads WHERE thread_id='T2'"
        ).fetchone()
        if t2_after_batch["project_link"] != "crystal-spire" or t2_after_batch["project_confidence"] != "manual":
            v.append(f"apply_ruling_batch: T2 not ruled despite a valid pair in the batch: "
                     f"{dict(t2_after_batch)}")
        if _snapshot(conn)["queue"] != before_batch["queue"]:
            v.append("apply_ruling_batch: review_queue was modified (must never be touched)")

        # --- DECISIONS 0024: rejection writes ONLY review_rulings ---
        # T3 already carries a pending 'chancellor' suggestion (manual-excluded
        # via T3's own project_confidence in earlier fixtures) -- use a fresh
        # thread/row pair instead so the reject path is exercised cleanly.
        conn.execute(
            """INSERT INTO threads (thread_id, source, account, title, created_at,
               project_link, project_confidence, review_status)
               VALUES ('T4','claude','claude-personal','Reject me',
                       '2026-06-04T00:00:00Z',NULL,NULL,'pending')""")
        conn.execute(
            "INSERT INTO review_queue "
            "(type, thread_id, confidence, status, note, created_at, candidate_project) "
            "VALUES ('project_link','T4',0.65,'pending','suggest -> l5gn-os',"
            "'2026-06-04T00:00:00Z','l5gn-os')")
        conn.commit()

        try:
            core.apply_rejection(conn, "GHOST", "l5gn-os")
            v.append("apply_rejection: unknown thread id was NOT rejected")
        except ValueError:
            pass

        before_reject = _snapshot(conn)
        res = core.apply_rejection(conn, "T4", "l5gn-os")
        if res["verdict"] != "rejected" or res["candidate_project"] != "l5gn-os":
            v.append(f"apply_rejection: return payload wrong: {res}")
        # review_queue and threads must be byte-for-byte unchanged by a rejection.
        if [dict(r) for r in conn.execute("SELECT * FROM review_queue ORDER BY item_id")] != \
           before_reject["queue"]:
            v.append("apply_rejection: review_queue was modified (must never be touched)")
        t4_row = conn.execute("SELECT * FROM threads WHERE thread_id='T4'").fetchone()
        if dict(t4_row)["project_link"] is not None or dict(t4_row)["project_confidence"] is not None:
            v.append("apply_rejection: threads row was modified (must never be touched)")

        # --- rejection clears T4 from l5gn-os's batch and stays cleared on reload ---
        if any(p["thread_id"] == "T4" for p in
               core.pending_rulings(conn, project_id="l5gn-os", registry=registry)):
            v.append("pending_rulings: rejected pair still appears in that project's batch")
        by_proj_after_reject = {e["project_id"]: e for e in core.queue_by_project(conn, registry)}
        l5gn_count = by_proj_after_reject.get("l5gn-os", {}).get("counts", {}).get("suggestion", 0)
        # T1 was already ruled manual earlier in this run, so only T4's suggestion
        # row could have contributed to l5gn-os's suggestion count by this point;
        # after rejection it must be gone.
        if l5gn_count != 0:
            v.append(f"queue_by_project: l5gn-os suggestion count should be 0 after "
                     f"T4's rejection, got {l5gn_count}")

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
