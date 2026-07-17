"""project_trail: assert per-project trail shape, ordering, and confidence rank
against a temp frozen-shaped vault (reusing tester_vault_reader's builder).

Hermetic: patches the shared vault-path resolver so it never reads this
machine's configured vault."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from l5gntools.scanners import project_trail, vault_reader
from .tester_vault_reader import _make_vault


def _rich_vault(path: Path) -> None:
    """A vault with one repo project carrying substantive + fragment threads
    across every confidence tier, plus a concept project with real activity."""
    c = sqlite3.connect(str(path))
    c.executescript(
        "CREATE TABLE projects(project_id TEXT PRIMARY KEY, name TEXT, repo_folder_path TEXT, source_system_id TEXT);"
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, source TEXT, account TEXT, title TEXT,"
        " created_at TEXT, updated_at TEXT, status TEXT, project_link TEXT, project_confidence TEXT,"
        " review_status TEXT, substantive INTEGER);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT, seq INTEGER, role TEXT, content TEXT);"
        "CREATE TABLE link_evidence(evidence_id INTEGER PRIMARY KEY, thread_id TEXT, project TEXT, signal TEXT, weight REAL);"
        "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);"
    )
    c.execute("INSERT INTO meta VALUES('schema_version','1.0-frozen')")
    c.execute("INSERT INTO projects VALUES('widget','widget','L5GN/widget',NULL)")
    c.execute("INSERT INTO projects VALUES('big','BigIdea',NULL,NULL)")
    c.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
        # (tid, source, account, title, created, updated, status, link, confidence, review, substantive)
        ("w_sub_new", "gemini", "gemini-personal", "s-new", "", "2026-07-10", "open", "widget", "manual", "confirmed", 1),
        ("w_exact",   "gemini", "gemini-personal", "s-exact", "", "2026-07-08", "open", "widget", "exact", "auto", 1),
        ("w_sub_old", "gemini", "gemini-work",     "s-old", "", "2026-07-05", "open", "widget", "evidence", "auto", 1),
        ("w_frag_a",  "claude", "claude-personal", "frag-a", "", "2026-07-06", "open", "widget", "fuzzy", "auto", 0),
        ("w_frag_nl", "claude", "claude-personal", "frag-null", "", "2026-06-01", "open", "widget", None, "auto", 0),
        # a FRAGMENT newer than the newest substantive thread -> exercises latest_activity = newest-of-ANY
        ("w_frag_newest", "claude", "claude-personal", "frag-new", "", "2026-07-12", "open", "widget", "fuzzy", "auto", 0),
        # concept project activity (repo_folder_path NULL)
        ("c1",        "gemini", "gemini-work",     "concept", "", "2026-07-09", "open", "big", "evidence", "auto", 1),
    ])
    c.executemany("INSERT INTO messages VALUES(?,?,?,?,?)", [
        ("m1", "w_sub_new", 0, "user", "a"), ("m2", "w_sub_new", 1, "assistant", "b")])
    c.executemany("INSERT INTO link_evidence VALUES(?,?,?,?,?)", [
        (1, "w_sub_new", "widget", "path_mention", 0.9),
        (2, "w_exact", "widget", "path_mention", 0.9),
        (3, "w_sub_old", "widget", "path_mention", 0.9),
        (4, "w_frag_a", "widget", "title_match", 0.4)])
    c.execute("PRAGMA user_version = 1")
    c.commit()
    c.close()


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "chronicler.db"
        _make_vault(db, user_version=1)

        orig = vault_reader._resolve_vault_path
        vault_reader._resolve_vault_path = lambda: db
        try:
            out = project_trail.scan_estate([])
        finally:
            vault_reader._resolve_vault_path = orig

        if out.get("status") != "ok":
            return [f"project_trail: expected ok, got {out.get('status')!r}"]
        repo = {p["estate_project"]: p for p in out["projects"]}
        if "smelt-gateway" not in repo:
            return ["project_trail: smelt-gateway not surfaced"]
        sg = repo["smelt-gateway"]
        if sg["thread_count"] != 2 or sg["substantive_count"] != 2:
            v.append(f"project_trail: bad counts {sg['thread_count']}/{sg['substantive_count']}")
        if sg["estate"] != "L5GN":
            v.append(f"project_trail: estate wrong {sg['estate']!r}")
        # Both substantive -> newest-first: t2 (2026-07-11) ahead of t1 (2026-07-10).
        order = [t["thread_id"] for t in sg["trail"]]
        if order != ["t2", "t1"]:
            v.append(f"project_trail: trail order wrong {order}")
        # Confidence rank carried: t2 manual(4) > t1 evidence(2).
        ranks = {t["thread_id"]: t["confidence_rank"] for t in sg["trail"]}
        if ranks.get("t2") != 4 or ranks.get("t1") != 2:
            v.append(f"project_trail: confidence ranks wrong {ranks}")
        if sg["dominant_signal"] != "path_mention":
            v.append(f"project_trail: dominant_signal wrong {sg['dominant_signal']!r}")
        # Account wall carried at thread level.
        accts = {t["account"] for t in sg["trail"]}
        if accts != {"gemini-personal", "gemini-work"}:
            v.append(f"project_trail: account wall not carried {accts}")

    # ---- Rich vault: ordering, full confidence-rank map, concept activity ----
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "chronicler.db"
        _rich_vault(db)
        orig = vault_reader._resolve_vault_path
        vault_reader._resolve_vault_path = lambda: db
        try:
            out = project_trail.scan_estate([Path("widget")])
        finally:
            vault_reader._resolve_vault_path = orig

        if out.get("status") != "ok":
            return v + [f"project_trail: rich vault expected ok, got {out.get('status')!r}"]
        w = {p["estate_project"]: p for p in out["projects"]}.get("widget")
        if w is None:
            return v + ["project_trail: widget not surfaced from rich vault"]

        # Substantive-first, then newest-first WITHIN each band. w_sub_old (07-05)
        # must precede the NEWER fragment w_frag_a (07-06) purely because it's substantive.
        order = [t["thread_id"] for t in w["trail"]]
        if order != ["w_sub_new", "w_exact", "w_sub_old", "w_frag_newest", "w_frag_a", "w_frag_nl"]:
            v.append(f"project_trail: substantive-first / newest-first ordering wrong {order}")

        # Full confidence-rank map: none/null(0) < fuzzy(1) < evidence(2) < exact(3) < manual(4).
        rank = {t["thread_id"]: t["confidence_rank"] for t in w["trail"]}
        expect = {"w_sub_new": 4, "w_exact": 3, "w_sub_old": 2,
                  "w_frag_newest": 1, "w_frag_a": 1, "w_frag_nl": 0}
        if rank != expect:
            v.append(f"project_trail: confidence_rank map wrong {rank}")

        if w["substantive_count"] != 3 or w["thread_count"] != 6:
            v.append(f"project_trail: counts wrong {w['substantive_count']}/{w['thread_count']}")
        # latest_activity is the true newest of ANY thread (matches vault_reader): the
        # 07-12 fragment wins over the newest substantive (w_sub_new, 07-10), even though
        # the display order floats it below the substantive band.
        if w["latest_activity"] != "2026-07-12":
            v.append(f"project_trail: latest_activity should be newest-of-any, got {w['latest_activity']!r}")
        # dominant_signal = the most frequent evidence signal (path_mention x3 > title_match x1).
        if w["dominant_signal"] != "path_mention":
            v.append(f"project_trail: dominant_signal wrong {w['dominant_signal']!r}")
        if w["evidence_signals"] != {"path_mention": 3, "title_match": 1}:
            v.append(f"project_trail: evidence_signals wrong {w['evidence_signals']}")
        # projects=[Path('widget')] -> present flag resolves True.
        if w["present_in_estate"] is not True:
            v.append(f"project_trail: present_in_estate should be True when supplied, got {w['present_in_estate']!r}")
        # thread with 2 messages carries its message count.
        msgs = {t["thread_id"]: t["messages"] for t in w["trail"]}
        if msgs.get("w_sub_new") != 2:
            v.append(f"project_trail: message count not carried {msgs.get('w_sub_new')}")

        # Concept project with real activity surfaces in its own channel, not projects[].
        cc = {c["vault_project"]: c for c in out["concept_projects_with_activity"]}
        if "BigIdea" not in cc:
            v.append("project_trail: a concept project with a linked thread should surface")
        else:
            b = cc["BigIdea"]
            if b["thread_count"] != 1 or b["latest_activity"] != "2026-07-09":
                v.append(f"project_trail: concept activity wrong {b['thread_count']}/{b['latest_activity']}")
            if b["accounts"] != ["gemini-work"]:
                v.append(f"project_trail: concept accounts wrong {b['accounts']}")
        if any(p["estate_project"] == "BigIdea" for p in out["projects"]):
            v.append("project_trail: a concept project must not appear among repo projects")
    return v
