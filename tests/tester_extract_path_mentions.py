"""tester_extract_path_mentions: S5 path-mention extraction, id-keyed, repo-aware.

Round 3, Tasks A+D: same repo-tier gap as `xref_filenames` (Task C) -- the
project-key map only read `registry["projects"]` directly, so a path segment
naming a repo folder (`L5GN-Crystal-Spire`) never matched when the repo lived
only inside its concept project's `repos` list, and a hit that DID match wrote
`link_evidence.project` as the canonical_name instead of the id relink's
scorer resolves by (the standing Finding-3 defect). This is the first
hermetic tester for this producer; none existed before this round.

Also guards Task D's specific fold-in: the `origin` a path mention stamps must
be derived from the PATH'S OWN trailing segment, not from the matched alias --
so a message naming `...\\L5GN-Crystal-Spire\\world_graph.json` collapses with
an S4 `filename_xref` hit on the same `world_graph.json` file (both signals
citing the SAME origin is what makes relink's co-origin collapse treat them as
one piece of evidence instead of double-counting).

Hermetic: an on-disk sqlite fixture built from the real `schema.sql` (in a
temp dir) + an in-memory registry dict. No live vault, no network, no git.
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
                 "file_inventory": {"paths": ["world_graph.json"]}},
            ],
        },
    ],
}


def _fresh_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _seed(db_path: Path, messages: list[tuple[str, str, str]],
          attachments: list[tuple[str, str, str]] = ()) -> None:
    """messages: [(thread_id, message_id, content), ...]"""
    conn = _fresh_conn(db_path)
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    seen_threads = set()
    for tid, mid, content in messages:
        if tid not in seen_threads:
            conn.execute(
                "INSERT INTO threads (thread_id, source, account, title) "
                "VALUES (?, 'claude', 'personal', 'x')", (tid,))
            seen_threads.add(tid)
        conn.execute(
            "INSERT INTO messages (message_id, thread_id, seq, role, content) "
            "VALUES (?, ?, 1, 'user', ?)", (mid, tid, content))
    for aid, mid, fname in attachments:
        conn.execute(
            "INSERT INTO attachments (attachment_id, message_id, filename) "
            "VALUES (?, ?, ?)", (aid, mid, fname))
    conn.commit()
    conn.close()


def run() -> list[str]:
    v: list[str] = []
    ep = _load_module("extract_path_mentions")
    xf = _load_module("xref_filenames")
    dbmod = _load_module("db")
    # Both modules are cached (importlib/sys.modules) and shared with every
    # other tester in this process -- restore what we monkeypatch, or a later
    # tester (tester_registry_path checks xref_filenames.REGISTRY_PATH; this
    # file also drives xref_filenames for the co-origin check) fails for a
    # reason that has nothing to do with its own gate.
    saved = {
        "ep.REGISTRY_PATH": ep.REGISTRY_PATH, "ep.get_connection": ep.get_connection,
        "xf.REGISTRY_PATH": xf.REGISTRY_PATH, "xf.get_connection": xf.get_connection,
    }
    try:
        v.extend(_run_body(ep, xf, dbmod))
    finally:
        ep.REGISTRY_PATH = saved["ep.REGISTRY_PATH"]
        ep.get_connection = saved["ep.get_connection"]
        xf.REGISTRY_PATH = saved["xf.REGISTRY_PATH"]
        xf.get_connection = saved["xf.get_connection"]
    return v


def _run_body(ep, xf, dbmod) -> list[str]:
    v: list[str] = []
    PATH_MSG = ("t1", "m1",
                r"See C:\Users\tim\Github\L5GN\L5GN-Crystal-Spire\world_graph.json "
                "for the schema.")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        registry_path = td / "project_registry.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        db_path = td / "chronicler.db"
        _seed(db_path, [PATH_MSG], attachments=[("a1", "m1", "world_graph.json")])

        ep.REGISTRY_PATH = registry_path
        ep.get_connection = lambda: _fresh_conn(db_path)
        xf.REGISTRY_PATH = registry_path
        xf.get_connection = lambda: _fresh_conn(db_path)

        votes = ep.run(apply=True, rescan=True)

        by_project = {}
        for t, project, weight, detail, _origin_tok in votes:
            by_project.setdefault(project, []).append((t, weight, detail))

        # --- id-keyed, repo-tier: the REPO id, not its canonical_name -------
        if "l5gn-crystal-spire" not in by_project:
            v.append("extract_path_mentions: no vote for the repo id "
                     "'l5gn-crystal-spire' -- repo-tier keys are not being "
                     "indexed")
        if "L5GN-Crystal-Spire" in by_project or "Crystal Spire" in by_project:
            v.append("extract_path_mentions: a vote is keyed by "
                     "canonical_name, not id -- the Finding-3 defect has "
                     "regressed")

        got = by_project.get("l5gn-crystal-spire", [])
        if got and got[0][1] != 0.9:
            v.append(f"extract_path_mentions: weight was {got[0][1]!r}, "
                     "expected 0.9")

        # --- origin derived from the trailing segment, matching S4 ----------
        conn = _fresh_conn(db_path)
        try:
            pm_row = conn.execute(
                "SELECT origin FROM link_evidence WHERE signal='path_mention' "
                "AND project=?", ("l5gn-crystal-spire",)).fetchone()
        finally:
            conn.close()
        if pm_row is None:
            v.append("extract_path_mentions: no path_mention row was written "
                     "to link_evidence")
        else:
            expected = dbmod.origin_for("path_mention", "world_graph.json")
            if pm_row["origin"] != expected:
                v.append(f"extract_path_mentions: origin={pm_row['origin']!r}, "
                         f"expected {expected!r} derived from the path's "
                         "trailing segment 'world_graph.json', not the "
                         "matched alias 'L5GN-Crystal-Spire'")

        # --- Task D's acceptance case: collapses with the S4 row on the SAME
        # basename -- both signals, same registry id, same origin.
        xf_votes = xf.run(apply=True)
        conn = _fresh_conn(db_path)
        try:
            xf_row = conn.execute(
                "SELECT project, origin FROM link_evidence WHERE "
                "signal='filename_xref' AND detail='world_graph.json'"
            ).fetchone()
            pm_row2 = conn.execute(
                "SELECT project, origin FROM link_evidence WHERE "
                "signal='path_mention' AND project=?",
                ("l5gn-crystal-spire",)).fetchone()
        finally:
            conn.close()
        if xf_row is None or pm_row2 is None:
            v.append("extract_path_mentions: could not find both an S4 and S5 "
                     "row to compare for the co-origin collapse check")
        else:
            if xf_row["project"] != pm_row2["project"]:
                v.append(f"extract_path_mentions: S4 keyed "
                         f"{xf_row['project']!r} but S5 keyed "
                         f"{pm_row2['project']!r} for the same file -- they "
                         "would not roll up to the same registry entry")
            if xf_row["origin"] != pm_row2["origin"]:
                v.append(f"extract_path_mentions: S4 origin "
                         f"{xf_row['origin']!r} != S5 origin "
                         f"{pm_row2['origin']!r} -- relink's co-origin "
                         "collapse would treat these as independent evidence "
                         "instead of one file cited twice")

        # --- noise-only path produces nothing --------------------------------
        conn = _fresh_conn(db_path)
        conn.execute(
            "INSERT INTO messages (message_id, thread_id, seq, role, content) "
            "VALUES ('m2', 't1', 2, 'user', "
            "'C:\\Python314\\Lib\\site-packages\\foo.py has nothing to do "
            "with any project')")
        conn.commit()
        conn.close()
        more_votes = ep.run(apply=False, rescan=True)
        if any(d == "foo.py" or "python314" in (d or "").lower()
               for *_, d, _o in more_votes):
            v.append("extract_path_mentions: a noise-only system path "
                     "produced a vote")

    # --- dry-run (no --apply) writes nothing --------------------------------
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        registry_path = td / "project_registry.json"
        registry_path.write_text(json.dumps(REGISTRY), encoding="utf-8")
        db_path = td / "chronicler.db"
        _seed(db_path, [PATH_MSG])
        ep.REGISTRY_PATH = registry_path
        ep.get_connection = lambda: _fresh_conn(db_path)

        ep.run(apply=False, rescan=True)
        conn = _fresh_conn(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(link_evidence)")}
        count = (conn.execute("SELECT COUNT(*) AS c FROM link_evidence").fetchone()["c"]
                 if cols else 0)
        conn.close()
        if count:
            v.append(f"extract_path_mentions: a dry-run wrote {count} row(s) "
                     "to link_evidence")

    return v
