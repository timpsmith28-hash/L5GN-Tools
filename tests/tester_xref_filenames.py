"""tester_xref_filenames: S4 filename cross-reference, id-keyed, repo-aware.

Round 3, Tasks A+C: `build_inventory` now attaches `file_inventory` to whichever
tier owns the files -- a repo (`L5GN-Crystal-Spire`), not necessarily its
concept project (`crystal-spire`). Before this round, `xref_filenames` only
read `registry["projects"]` directly and wrote `link_evidence.project` as the
**canonical_name** -- so (a) a repo-only inventory was invisible to the basename
index, and (b) even a hit that WAS found pointed relink's id-keyed scorer
(post-`52193bd`) at a key it could never resolve (the standing Finding-3
defect). This is the first hermetic tester for this producer; none existed
before this round.

Hermetic: an on-disk sqlite fixture built from the real `schema.sql` (in a
temp dir) + an in-memory registry dict. No live vault, no network, no git.

Assertions:

  * a unique basename owned by a REPO produces a weight-1.0 row keyed by the
    **repo id**, never the repo's canonical_name
  * a basename shared by two PROJECT-tier entries (no repos of their own --
    the flat/single-repo shape still works) splits 1/n, each row keyed by id
  * a generic basename (README.md) produces no row
  * the stamped `origin` collapses with what a path_mention would stamp for
    the same basename (Task C.3 / D.2's shared contract), asserted directly
    against `db.origin_for`
  * idempotent: re-running with --apply never accumulates duplicate rows
  * --dry-run (the default) writes nothing
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
_SCHEMA = _PIPELINE / "schema.sql"


def _load_module(name: str):
    added = str(_PIPELINE) not in sys.path
    if added:
        sys.path.insert(0, str(_PIPELINE))
    try:
        import importlib
        return importlib.import_module(name)
    finally:
        if added and str(_PIPELINE) in sys.path:
            sys.path.remove(str(_PIPELINE))


REGISTRY = {
    "schema_version": 2,
    "programs": [],
    "projects": [
        {
            "id": "crystal-spire", "canonical_name": "Crystal Spire",
            "scope": "l5gn", "aliases": [],
            "repos": [
                {"id": "l5gn-crystal-spire",
                 "canonical_name": "L5GN-Crystal-Spire", "scope": "l5gn",
                 "aliases": [],
                 "file_inventory": {"paths": ["world_graph.json",
                                              "src/loader.py"]}},
            ],
        },
        {
            "id": "smelt-gateway", "canonical_name": "smelt-gateway",
            "scope": "l5gn", "aliases": [], "repos": [],
            "file_inventory": {"paths": ["shared_util.py"]},
        },
        {
            "id": "l5gn-armory-v4", "canonical_name": "L5GN_Armory_v4",
            "scope": "l5gn", "aliases": [], "repos": [],
            "file_inventory": {"paths": ["shared_util.py"]},
        },
    ],
}


def _fresh_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _seed(db_path: Path) -> None:
    conn = _fresh_conn(db_path)
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    threads = [("t1", "unique hit"), ("t2", "multi hit"), ("t3", "generic only")]
    for tid, title in threads:
        conn.execute(
            "INSERT INTO threads (thread_id, source, account, title) "
            "VALUES (?, 'claude', 'personal', ?)", (tid, title))
    messages = [("m1", "t1"), ("m2", "t2"), ("m3", "t3")]
    for mid, tid in messages:
        conn.execute(
            "INSERT INTO messages (message_id, thread_id, seq, role, content) "
            "VALUES (?, ?, 1, 'user', 'x')", (mid, tid))
    attachments = [
        ("a1", "m1", "world_graph.json"),
        ("a2", "m2", "shared_util.py"),
        ("a3", "m3", "README.md"),
    ]
    for aid, mid, fname in attachments:
        conn.execute(
            "INSERT INTO attachments (attachment_id, message_id, filename) "
            "VALUES (?, ?, ?)", (aid, mid, fname))
    conn.commit()
    conn.close()


def run() -> list[str]:
    v: list[str] = []
    xf = _load_module("xref_filenames")
    dbmod = _load_module("db")
    # xref_filenames is a cached module (importlib/sys.modules) shared with
    # every other tester in this process -- REGISTRY_PATH and get_connection
    # must be restored, or a later tester (tester_registry_path checks
    # xref_filenames.REGISTRY_PATH against the real resolver) sees this
    # fixture's temp path and fails for a reason that has nothing to do with
    # its own gate.
    orig_registry_path = xf.REGISTRY_PATH
    orig_get_connection = xf.get_connection
    try:
        v.extend(_run_body(xf, dbmod))
    finally:
        xf.REGISTRY_PATH = orig_registry_path
        xf.get_connection = orig_get_connection
    return v


def _run_body(xf, dbmod) -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        registry_path = td / "project_registry.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        db_path = td / "chronicler.db"
        _seed(db_path)

        xf.REGISTRY_PATH = registry_path
        xf.get_connection = lambda: _fresh_conn(db_path)

        votes = xf.run(apply=True)

        by_project = {}
        for _, project, weight, detail in votes:
            by_project.setdefault(project, []).append((weight, detail))

        # --- unique hit: the REPO id, not its canonical_name ----------------
        if "l5gn-crystal-spire" not in by_project:
            v.append("xref_filenames: no vote for the repo id "
                     "'l5gn-crystal-spire' -- repo-tier inventories are not "
                     "being indexed")
        elif by_project["l5gn-crystal-spire"] != [(1.0, "world_graph.json")]:
            v.append(f"xref_filenames: unique hit for the repo was "
                     f"{by_project['l5gn-crystal-spire']!r}, expected a single "
                     "weight-1.0 'world_graph.json' vote")
        if "L5GN-Crystal-Spire" in by_project or "Crystal Spire" in by_project:
            v.append("xref_filenames: a vote is keyed by canonical_name, not "
                     "id -- the Finding-3 defect has regressed")

        # --- multi-hit: split 1/n across the two owning ids -----------------
        for pid in ("smelt-gateway", "l5gn-armory-v4"):
            if pid not in by_project:
                v.append(f"xref_filenames: no multi-hit vote for {pid!r}")
            elif by_project[pid] != [(0.5, "shared_util.py")]:
                v.append(f"xref_filenames: multi-hit vote for {pid!r} was "
                         f"{by_project[pid]!r}, expected a single 0.5 vote")

        # --- generic basename produces nothing ------------------------------
        if any(d == "README.md" for votes_ in by_project.values()
               for _, d in votes_):
            v.append("xref_filenames: a generic basename (README.md) produced "
                     "evidence -- it carries no project-distinctiveness")

        # --- origin collapses with what a path_mention would stamp ----------
        conn = _fresh_conn(db_path)
        try:
            row = conn.execute(
                "SELECT origin FROM link_evidence WHERE project=? AND detail=?",
                ("l5gn-crystal-spire", "world_graph.json")).fetchone()
        finally:
            conn.close()
        expected_origin = dbmod.origin_for("filename_xref", "world_graph.json")
        if row is None:
            v.append("xref_filenames: the unique-hit row was not written to "
                     "link_evidence at all")
        elif row["origin"] != expected_origin:
            v.append(f"xref_filenames: origin={row['origin']!r}, expected "
                     f"{expected_origin!r} (db.origin_for) -- a path_mention "
                     "on the same file would not collapse with this row")

        # --- idempotent: re-apply never accumulates duplicates --------------
        conn = _fresh_conn(db_path)
        before = conn.execute(
            "SELECT COUNT(*) AS c FROM link_evidence WHERE signal='filename_xref'"
        ).fetchone()["c"]
        conn.close()
        xf.run(apply=True)
        conn = _fresh_conn(db_path)
        after = conn.execute(
            "SELECT COUNT(*) AS c FROM link_evidence WHERE signal='filename_xref'"
        ).fetchone()["c"]
        conn.close()
        if before != after:
            v.append(f"xref_filenames: re-running --apply changed the row "
                     f"count {before} -> {after}; a re-run must be idempotent")

    # --- a fresh DB never touched by --apply above: dry-run writes nothing --
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        registry_path = td / "project_registry.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        db_path = td / "chronicler.db"
        _seed(db_path)
        xf.REGISTRY_PATH = registry_path
        xf.get_connection = lambda: _fresh_conn(db_path)

        xf.run(apply=False)
        conn = _fresh_conn(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(link_evidence)")}
        count = (conn.execute("SELECT COUNT(*) AS c FROM link_evidence").fetchone()["c"]
                 if cols else 0)
        conn.close()
        if count:
            v.append("xref_filenames: a dry-run (no --apply) wrote "
                     f"{count} row(s) to link_evidence")

    return v
