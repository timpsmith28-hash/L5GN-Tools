"""tester_estate_data: the local deck's read-only estate layer (slice 1).

Hermetic and stdlib-only. Builds a throwaway estate on disk -- two projects
inside a root, one hostile project outside it -- and drives the real code
against it. No FastAPI, no uvicorn, no server bind, and nothing touches the
real ``data/estate.json``.

**The path-safety cases are the point of this file.** DECISIONS 0027 permits a
render-time file read only inside the configured estate roots, and the brief
makes that "two independent checks, both required, with a tester for each":

  * check one -- the route takes an opaque identifier, so an identifier that is
    not in the catalogue resolves to nothing. Proven by ``../`` traversal
    attempts, absolute paths and a plausible-looking forged digest.
  * check two -- the resolved path is re-verified inside the roots immediately
    before opening. Proven by a project whose ``path`` sits outside the roots
    entirely, and by a symlink that escapes them.

The second case matters precisely because check one passes for it: the document
IS in the catalogue, the identifier IS genuine, and it must still be refused.
That is the case a single check would miss.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from chronicler.review import doc_search, estate_data, estate_time


def _doc(path: str, title: str, provenance: str = "authored",
         doc_type: str = "unclassified", words: int = 10) -> dict:
    return {"path": path, "title": title, "headings": 1, "words": words,
            "bytes": 100, "doc_type": doc_type, "provenance": provenance}


def _snapshot(root: Path, outside: Path) -> dict:
    """A structurally-real estate: one documented git project, one project with
    no git at all, and one whose path is outside the configured roots."""
    return {
        "generated_at": "2026-07-28T22:20:48+01:00",
        "toolkit_version": "0.1.0",
        "toolkit_commit": "abc1234",
        "toolkit_dirty": True,
        "estate_name": "personal",
        "estate_root": str(root),
        "producer_host": "fixture",
        "roots": [{"path": str(root), "scope": "test"}],
        "projects": [
            {
                "name": "Documented", "path": str(root / "Documented"), "scope": "test",
                "git_summary": {"is_git": True, "branch": "main",
                                "latest_hash": "ddd4444",
                                "latest_date": "2026-07-20T10:00:00+00:00",
                                "latest_author": "timpsmith28-hash",
                                "latest_subject": "a commit",
                                "commit_count": 12, "dirty_files": 0,
                                "first_commit_date": "2026-06-01T10:00:00+00:00"},
                "git_deep_history": {"is_git": True, "total_commits": 12,
                                     "truncated": False,
                                     "commits_by_author": {"timpsmith28-hash": 9,
                                                           "Someone Else": 3},
                                     "commits_by_day": {"2026-06-01": 9, "2026-07-20": 3}},
                "doc_census": {"doc_count": 4, "authored_count": 3, "generated_count": 1,
                               "docs": [
                                   _doc("PROJECT_knowledge.md", "The knowledge doc",
                                        doc_type="knowledge", words=40),
                                   _doc("README.md", "Readme", doc_type="readme"),
                                   _doc("docs/DECISIONS.md", "Decisions",
                                        doc_type="decisions"),
                                   _doc("AutoFiles/machine.md", "Generated",
                                        provenance="generated", doc_type="report"),
                               ]},
            },
            {
                "name": "NoGit", "path": str(root / "NoGit"), "scope": "test",
                "git_summary": {"is_git": False},
                "git_deep_history": {"is_git": False},
                "doc_census": {"doc_count": 1, "authored_count": 1, "generated_count": 0,
                               "docs": [_doc("NOTES.md", "Notes")]},
            },
            {
                # The hostile case: a genuine catalogue entry whose path is
                # outside the configured roots. Check one passes for it.
                "name": "Outside", "path": str(outside / "Outside"), "scope": "test",
                "git_summary": {"is_git": False},
                "doc_census": {"doc_count": 1, "authored_count": 1, "generated_count": 0,
                               "docs": [_doc("SECRET.md", "Not yours")]},
            },
        ],
    }


def _write_tree(root: Path, outside: Path) -> None:
    doc = root / "Documented"
    (doc / "docs").mkdir(parents=True)
    (doc / "AutoFiles").mkdir(parents=True)
    (doc / "PROJECT_knowledge.md").write_text(
        "# Knowledge\n\nThe reconciliation cadence is weekly, and the "
        "peculiar marker word is zarquon.\n", encoding="utf-8")
    (doc / "README.md").write_text("# Readme\n\nOrdinary prose.\n", encoding="utf-8")
    (doc / "docs" / "DECISIONS.md").write_text(
        "# Decisions\n\n0001 -- something about zarquon too.\n", encoding="utf-8")
    (doc / "AutoFiles" / "machine.md").write_text(
        "generated output mentioning zarquon\n", encoding="utf-8")
    nogit = root / "NoGit"
    nogit.mkdir(parents=True)
    (nogit / "NOTES.md").write_text("# Notes\n\nnothing special\n", encoding="utf-8")
    out = outside / "Outside"
    out.mkdir(parents=True)
    (out / "SECRET.md").write_text("the crown jewels\n", encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root, outside = base / "estate", base / "elsewhere"
        _write_tree(root, outside)
        estate_path = base / "estate.json"
        estate_path.write_text(json.dumps(_snapshot(root, outside)), encoding="utf-8")

        # Roots are passed explicitly: the tester must never depend on, or be
        # affected by, the running machine's real config.
        est = estate_data.EstateData.load(estate_path, roots=[root])

        # --- Task 1: the layer loads and states its provenance ---------------
        if not est.available:
            v.append(f"EstateData: fixture snapshot failed to load ({est.reason})")
            return v
        head = est.header()
        for field in ("generated_at", "toolkit_commit", "toolkit_dirty"):
            if head.get(field) in (None, ""):
                v.append(f"header: {field} missing -- staleness must be visible")
        if head["toolkit_dirty"] is not True:
            v.append("header: toolkit_dirty not carried through from the snapshot")
        if head["age_seconds"] is None or head["age_seconds"] <= 0:
            v.append("header: age_seconds not computed from generated_at")

        # --- absent estate degrades cleanly, it does not raise ---------------
        missing = estate_data.EstateData.load(base / "nope.json", roots=[root])
        if missing.available or missing.reason != "estate_missing":
            v.append("EstateData: a missing estate.json must report cleanly, "
                     f"got available={missing.available} reason={missing.reason}")
        if missing.projects() or missing.documents:
            v.append("EstateData: an unavailable estate must expose no projects/docs")
        if missing.header().get("available") is not False:
            v.append("header: an unavailable estate must say so in its header")

        # --- Task 2: generated documents are not offered ---------------------
        paths = {d["path"] for d in est.documents}
        if "AutoFiles/machine.md" in paths:
            v.append("catalogue: a generated document entered the catalogue -- "
                     "this slice reads authored documents only")
        if len(est.documents) != 5:
            v.append(f"catalogue: expected 5 authored documents, got {len(est.documents)}")

        # --- knowledge sorts first in the nav --------------------------------
        groups = est.documents_for("Documented")
        if not groups or groups[0]["doc_type"] != "knowledge":
            v.append(f"documents_for: knowledge must lead the groups, got "
                     f"{[g['doc_type'] for g in groups]}")
        if any(g["doc_type"] == "report" for g in groups):
            v.append("documents_for: the generated report leaked into the groups")

        # --- the document renders, and matches the file on disk --------------
        know = next(d for d in est.documents
                    if d["project"] == "Documented" and d["doc_type"] == "knowledge")
        rendered = est.read_document(know["id"])
        on_disk = (root / "Documented" / "PROJECT_knowledge.md").read_text(encoding="utf-8")
        if rendered["text"] != on_disk:
            v.append("read_document: rendered text does not match the file on disk")

        # --- PATH SAFETY, CHECK ONE: the identifier is opaque ----------------
        # None of these is a digest in the catalogue, so none of them resolves.
        # This is why the route takes an id and not a path.
        forged = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\win.ini",
            str(root / "Documented" / "README.md"),
            "/etc/passwd",
            "Documented/PROJECT_knowledge.md",
            "0" * 16,                      # right shape, not in the catalogue
            "",
        ]
        for attempt in forged:
            try:
                est.read_document(attempt)
                v.append(f"PATH SAFETY (check one): identifier {attempt!r} was "
                         "accepted -- a non-catalogue identifier must be refused")
            except estate_data.DocumentRefused as exc:
                if exc.reason != "unknown_document":
                    v.append(f"PATH SAFETY: {attempt!r} refused for the wrong "
                             f"reason ({exc.reason}); expected unknown_document")

        # A traversal smuggled into the *snapshot* is dropped at catalogue-build
        # time, so it never gets an identifier at all.
        poisoned = json.loads(estate_path.read_text(encoding="utf-8"))
        poisoned["projects"][0]["doc_census"]["docs"].append(
            _doc("../../../../etc/passwd", "traversal"))
        poison_path = base / "poisoned.json"
        poison_path.write_text(json.dumps(poisoned), encoding="utf-8")
        poisoned_est = estate_data.EstateData.load(poison_path, roots=[root])
        if any(".." in d["path"] for d in poisoned_est.documents):
            v.append("PATH SAFETY: a '..' path from the snapshot entered the catalogue")
        if not poisoned_est.warnings:
            v.append("PATH SAFETY: dropping a traversal path must be reported, "
                     "not done silently")

        # --- PATH SAFETY, CHECK TWO: containment, independently -------------
        # This document IS in the catalogue and its identifier IS genuine --
        # check one passes. Check two must still refuse it.
        secret = next(d for d in est.documents if d["project"] == "Outside")
        try:
            est.read_document(secret["id"])
            v.append("PATH SAFETY (check two): a catalogued document outside the "
                     "configured roots was READ -- this is the file-disclosure case")
        except estate_data.DocumentRefused as exc:
            if exc.reason != "outside_estate_roots":
                v.append(f"PATH SAFETY (check two): wrong refusal reason {exc.reason!r}")

        # The predicate itself, directly: a sibling directory whose name merely
        # starts with the root's name must not count as inside it.
        near_miss = Path(str(root) + "-evil") / "x.md"
        if estate_data.path_within_roots(near_miss, [root]):
            v.append("path_within_roots: prefix collision -- "
                     f"{near_miss} counted as inside {root}")
        if not estate_data.path_within_roots(root / "Documented" / "README.md", [root]):
            v.append("path_within_roots: a genuine in-root path was refused")
        if estate_data.path_within_roots(root / "Documented" / "README.md", []):
            v.append("path_within_roots: with no roots configured, nothing is "
                     "inside the boundary -- must refuse")

        # A symlink escaping the roots is caught because containment is checked
        # after realpath, not on the joined path.
        if hasattr(os, "symlink"):
            link = root / "Documented" / "escape.md"
            try:
                os.symlink(str(outside / "Outside" / "SECRET.md"), str(link))
            except (OSError, NotImplementedError):
                pass  # unprivileged Windows: skip, the direct case above stands
            else:
                if estate_data.path_within_roots(link, [root]):
                    v.append("PATH SAFETY: a symlink out of the estate was "
                             "counted as inside it -- realpath not applied")

        # --- no configured roots means no reads at all ------------------------
        rootless = estate_data.EstateData.load(estate_path, roots=[])
        entry = rootless.documents[0]
        try:
            rootless.read_document(entry["id"])
            v.append("PATH SAFETY: with no configured roots, a read succeeded -- "
                     "there is no boundary to be inside of")
        except estate_data.DocumentRefused as exc:
            if exc.reason != "no_configured_roots":
                v.append(f"PATH SAFETY: rootless refusal reason was {exc.reason!r}")

        # --- Task 3: search --------------------------------------------------
        if not doc_search.fts5_available():
            v.append("NOTE: FTS5 unavailable in this interpreter -- the fts5 "
                     "path below is untested here (substring path still is)")
        index = doc_search.DocumentIndex(est)
        try:
            # 5 authored documents in the catalogue, but only 4 are indexable:
            # the one outside the configured roots is refused by the containment
            # check at index time, exactly as it would be at render time.
            if index.indexed != 4:
                v.append(f"index: expected 4 indexable documents (5 authored, "
                         f"1 outside the roots), got {index.indexed}")
            if index.status()["persisted"] is not False:
                v.append("index: must report that it persists nothing")
            # The document outside the roots is refused by the SAME containment
            # check at index time, so it is not searchable either.
            skipped_projects = {s["project"] for s in index.skipped}
            if "Outside" not in skipped_projects:
                v.append("index: the out-of-roots document was indexed -- search "
                         "must be subject to the same containment check as render")

            hits = index.search("zarquon")
            got = {(h["project"], h["path"]) for h in hits["results"]}
            if ("Documented", "PROJECT_knowledge.md") not in got:
                v.append(f"search: the knowledge document did not surface for a "
                         f"term it contains; got {sorted(got)}")
            if ("Documented", "AutoFiles/machine.md") in got:
                v.append("search: a generated document was searchable")
            if hits["results"] and not hits["results"][0]["is_knowledge"]:
                v.append("search: a knowledge document must be surfaced ahead of "
                         "an equally-relevant ordinary one (0026)")
            if not any("\x02" in h["snippet"] for h in hits["results"]):
                v.append("search: results carry no marked snippet")

            scoped = index.search("zarquon", project="NoGit")
            if scoped["results"]:
                v.append("search: project scoping did not restrict the results")

            if index.search("")["results"]:
                v.append("search: an empty query must return nothing, not everything")

            # Substring mode is the degradation path and must give the same
            # answer, minus ranking -- exercised explicitly so a machine without
            # FTS5 is not the first place it ever runs.
            plain = doc_search.DocumentIndex(est, force_substring=True)
            try:
                if plain.engine != "substring" or not plain.notice:
                    v.append("index: forced substring mode must say so in `notice`")
                plain_hits = {(h["project"], h["path"])
                              for h in plain.search("zarquon")["results"]}
                if plain_hits != got:
                    v.append(f"search: substring mode found {sorted(plain_hits)}, "
                             f"fts5 found {sorted(got)} -- the corpus must match")
            finally:
                plain.close()

            # A malformed FTS5 expression is a typo, not a crash.
            broken = index.search('"unbalanced')
            if broken.get("results") is None:
                v.append("search: a malformed query returned no result structure")

            # REGRESSION: the index is built on one thread and queried from
            # uvicorn's threadpool, which is a different thread per request.
            # sqlite3 refuses cross-thread use by default, and the failure is
            # invisible to a single-threaded tester -- it only appeared under
            # the real server. Query from a worker thread so it stays fixed.
            import threading
            cross: list = []

            def _query():
                try:
                    cross.append(index.search("zarquon")["count"])
                except Exception as exc:  # noqa: BLE001 -- the defect is any raise
                    cross.append(exc)

            worker = threading.Thread(target=_query)
            worker.start()
            worker.join(timeout=30)
            if not cross:
                v.append("search: a query from a worker thread never returned")
            elif isinstance(cross[0], Exception):
                v.append(f"search: querying from another thread raised {cross[0]!r} "
                         "-- the index must be usable from uvicorn's threadpool")
            elif cross[0] != hits["count"]:
                v.append(f"search: cross-thread query gave {cross[0]} results, "
                         f"main thread gave {hits['count']}")
        finally:
            index.close()

        # --- Task 4: time, and the honesty rule ------------------------------
        aliases = {"timpsmith28-hash": "L5GN", "l5gn": "L5GN"}
        snapshot = est.snapshot
        documented = snapshot["projects"][0]
        span = estate_time.project_span(documented, aliases)
        if not span["has_history"]:
            v.append("project_span: a git project with dates reported no history")
        if span["span_days"] != 49.0:
            v.append(f"project_span: expected a 49-day span, got {span['span_days']}")
        authors = {c["author"] for c in span["contributors"]}
        if "L5GN" not in authors or "timpsmith28-hash" in authors:
            v.append(f"project_span: authors not folded through the alias map; "
                     f"got {sorted(authors)}")
        if span["contributors"][0]["author"] != "L5GN":
            v.append("project_span: contributors must be ordered by commit count")

        nogit = estate_time.project_span(snapshot["projects"][1], aliases)
        if nogit["has_history"] or "not a git repository" not in nogit["reason"]:
            v.append("project_span: a non-git project must say it has no history, "
                     "never be given an invented span")
        for forbidden in ("first_commit", "last_commit", "span_days"):
            if forbidden in nogit:
                v.append(f"project_span: a non-git project carries {forbidden} -- "
                         "that is the fabricated-window defect")

        empty_repo = estate_time.project_span(
            {"name": "Empty", "git_summary": {"is_git": True}}, aliases)
        if empty_repo["has_history"]:
            v.append("project_span: a git repo with no commit dates must report "
                     "no history rather than a zero-length span")

        timeline = estate_time.estate_timeline(snapshot)
        if not timeline["has_axis"]:
            v.append("estate_timeline: no axis built from a snapshot with history")
        else:
            names = [p["project"] for p in timeline["projects"]]
            if names != ["Documented"]:
                v.append(f"estate_timeline: unexpected projects on the axis: {names}")
            for p in timeline["projects"]:
                if not (0.0 <= p["offset"] <= 1.0 and 0.0 <= p["width"] <= 1.0):
                    v.append(f"estate_timeline: {p['project']} offset/width outside "
                             f"0..1 ({p['offset']}, {p['width']})")
            absent_names = {p["project"] for p in timeline["without_history"]}
            if absent_names != {"NoGit", "Outside"}:
                v.append(f"estate_timeline: projects without history must still be "
                         f"listed; got {sorted(absent_names)}")

        # A single-instant estate must not be drawn as a full-width bar.
        instant = {"projects": [{
            "name": "Instant",
            "git_summary": {"is_git": True, "commit_count": 1,
                            "first_commit_date": "2026-07-01T00:00:00+00:00",
                            "latest_date": "2026-07-01T00:00:00+00:00"}}]}
        inst_tl = estate_time.estate_timeline(instant)
        if inst_tl["projects"][0]["width"] != 0.0:
            v.append("estate_timeline: a zero-length estate span must give width 0, "
                     f"got {inst_tl['projects'][0]['width']}")

        # --- the build delta names both sides --------------------------------
        history = base / "history"
        history.mkdir()
        (history / "estate-2026-07-27.json").write_text(
            json.dumps({"generated_at": "2026-07-27T10:00:00+01:00",
                        "toolkit_commit": "0000aaa", "toolkit_dirty": False,
                        "projects": [snapshot["projects"][0]]}), encoding="utf-8")
        (history / "estate-2026-07-28.json").write_text(
            json.dumps({"generated_at": "2026-07-28T22:20:48+01:00",
                        "toolkit_commit": "abc1234", "toolkit_dirty": True,
                        "projects": snapshot["projects"][:2]}), encoding="utf-8")
        delta = estate_time.build_delta(history)
        if delta.get("status") != "ok":
            v.append(f"build_delta: expected a comparison, got {delta.get('status')}")
        else:
            if delta["from_build"]["toolkit_commit"] != "0000aaa" or \
               delta["to_build"]["toolkit_commit"] != "abc1234":
                v.append("build_delta: both builds must be named by commit, "
                         "not just by filename")
            if delta["projects_added"] != ["NoGit"]:
                v.append(f"build_delta: expected NoGit to appear, got "
                         f"{delta['projects_added']}")

        thin = estate_time.build_delta(base / "no-history-here")
        if thin.get("status") != "insufficient_history":
            v.append("build_delta: with fewer than two snapshots the honest "
                     f"answer is insufficient_history, got {thin.get('status')}")

        # --- nothing was persisted -------------------------------------------
        # The strongest form of 0027's condition (1): after loading, indexing,
        # searching and rendering, the fixture tree is byte-identical.
        strays = [p for p in base.rglob("*")
                  if p.is_file() and p.name.endswith((".db", ".sqlite", ".idx", ".cache"))]
        if strays:
            v.append(f"PERSISTENCE: the slice left files behind: {strays}")

    return v
