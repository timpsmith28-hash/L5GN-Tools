"""tester_docs_board: the docs board's derivation and its containment anchor.

Two halves, and the split matters.

**Derivation is tested against a fixture tree**, not against the real ``docs/``.
A tester that asserted "`toolkit_self_scan` is in Walked" would go red the day
somebody legitimately archived it -- it would be testing the estate's current
state and calling it a code defect. The rules are what is stable, so the rules
are what is tested: build a tree with one of every shape, assert each lands in
the column ``docs/README.md`` §3 says it should.

**Containment is tested against the real anchor**, because that is the claim
worth making: the board must render this repository's own ``docs/`` on a
machine where the toolkit sits outside every configured estate root. Slice 1's
resolver is anchored to ``config.estate_roots()``, and the toolkit only
*happens* to sit inside one on the gaming rig -- so the tester proves the board
does not depend on that coincidence, and that widening the anchor did not
widen it to everything.

Hermetic and stdlib-only. No server is bound, no config is read, nothing is
written outside a temp dir.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from chronicler.review import docs_board, estate_data

_UAT_STAMP = "<!-- uat: commit=abc1234 dirty=false host=rig walked=2026-07-30 -->\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(root: Path) -> None:
    """One of every shape the real ``docs/`` contains."""
    docs = root / "docs"
    arch = docs / "archive"

    # in flight: a brief and nothing else
    _write(docs / "COWORK_BRIEF_inflight.md", "# brief\n")

    # built, not walked: brief + report + sheet, no results log
    _write(docs / "COWORK_BRIEF_built.md", "# brief\n")
    _write(docs / "COWORK_REPORT_built.md", "# report\n")
    _write(docs / "UAT_built.md", "# uat\n- [ ] a\n- [ ] b\n- [x] c\n")

    # walked, ticked on the sheet: the convention applied as written
    _write(docs / "COWORK_BRIEF_ticked.md", "# brief\n")
    _write(docs / "COWORK_REPORT_ticked.md", "# report\n")
    _write(docs / "UAT_ticked.md", "# uat\n- [x] a\n- [~] b\n- [ ] c\n")
    _write(docs / "UAT_ticked_results.md", _UAT_STAMP + "# results\n- [x] a\n")

    # walked, evidence in the results log: the finding, reproduced
    _write(docs / "COWORK_BRIEF_evidence.md", "# brief\n")
    _write(docs / "COWORK_REPORT_evidence.md", "# report\n")
    _write(docs / "UAT_evidence.md", "# uat\n- [ ] a\n- [ ] b\n")
    _write(docs / "UAT_evidence_results.md", _UAT_STAMP + "# results\n- [x] a\n- [x] b\n")

    # a walk-sheet with no brief -- legitimate, not a broken pair
    _write(docs / "UAT_solo.md", "# uat\n- [ ] a\n")
    _write(docs / "UAT_solo_results.md", _UAT_STAMP + "# results\n- [x] a\n")

    # built, not walked -- the post-0031 backticked checkbox form, which must
    # count exactly like the plain form (correctness sweep, finding 5/2:
    # UAT_knowledge_curator.md and UAT_project_wizard.md read 0/0 on the real
    # board before this fix, a confident zero on 38 real open items)
    _write(docs / "COWORK_BRIEF_backticked.md", "# brief\n")
    _write(docs / "COWORK_REPORT_backticked.md", "# report\n")
    _write(docs / "UAT_backticked.md",
           "# uat\n- `[ ]` a\n- `[ ]` b\n- `[x]` c\n- `[~]` d\n")

    # off-board: maintained, not finished
    _write(docs / "DECISIONS.md", "# decisions\n")
    _write(docs / "RUNBOOK_thing.md", "# runbook\n")

    # archive: a clean pair
    _write(arch / "COWORK_BRIEF_done.md",
           "> **ARCHIVED** 2026-07-27 · completed pair · report\n\n# brief\n")
    _write(arch / "COWORK_REPORT_done.md",
           "> **ARCHIVED** 2026-07-27 · completed pair · brief\n\n# report\n")

    # archive: pre-convention names that will not pair (the ROUND_N case)
    _write(arch / "COWORK_BRIEF_build_round_9.md",
           "> **ARCHIVED** 2026-07-20 · completed pair · COWORK_ROUND_9_REPORT.md\n\n# b\n")
    _write(arch / "COWORK_ROUND_9_REPORT.md",
           "> **ARCHIVED** 2026-07-20 · completed pair · the round 9 brief\n\n# r\n")

    # archive: a singleton retired by class, pairing with nothing
    _write(arch / "HANDOFF_final.md",
           "> **ARCHIVED** 2026-07-20 · retired · no report — retired by class\n\n# h\n")

    # archive: a stamp whose disposition elaborates beyond the vocabulary
    _write(arch / "old_plan.md",
           "> **ARCHIVED** 2026-07-20 · SUPERSEDED — do NOT run as a task list · none\n\n# p\n")

    # archive: the stamp sits BELOW a multi-line uat comment (two real files do)
    _write(arch / "UAT_late_results.md",
           _UAT_STAMP + "<!-- gate= omitted\n     on purpose -->\n\n"
           "> **ARCHIVED** 2026-07-25 · completed pair · the round sheet\n\n# r\n")

    # archive: NO stamp at all -- a finding, and NOT the same as unmatched
    _write(arch / "naked.md", "# never stamped\n")


#: Set by :func:`_route_checks` so a reader can tell "the routes passed" from
#: "the routes were never driven". Absence of the optional extra is a fact
#: about the machine, not a pass.
route_coverage: str = "not run"


def _route_checks() -> list[str]:
    """Drive the two board routes through a real client, if one is available."""
    global route_coverage
    from chronicler.review import app as review_app
    if not review_app.available():
        route_coverage = "skipped -- fastapi/uvicorn not installed (optional extra)"
        return []
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        route_coverage = "skipped -- no test client available"
        return []

    v: list[str] = []
    # The machine shape this slice exists to support: no vault, and an estate
    # label that does not resolve to a clause. The board must still serve.
    app = review_app.create_app(None, {}, None, estate=None, index=None)
    client = TestClient(app)

    res = client.get("/api/docs/board")
    if res.status_code != 200:
        v.append(f"route: /api/docs/board returned {res.status_code} on a "
                 f"machine with no vault and no resolvable estate -- the board "
                 f"depends on neither")
        route_coverage = "driven -- failed"
        return v
    body = res.json()
    if not any(c["count"] for c in body["columns"]):
        v.append("route: the board served no cards at all")

    # Thread routes must be off on this shape -- degraded, never open.
    for path in ("/api/pending", "/api/registry", "/api/queue/projects"):
        code = client.get(path).status_code
        if code != 503:
            v.append(f"route: {path} returned {code}, expected 503 -- a machine "
                     f"that cannot name one estate must serve no thread")

    # A card body renders by digest...
    member = next(m for col in body["columns"] for c in col["cards"]
                  for m in c["members"])
    got = client.get("/api/docs/document", params={"doc_id": member["id"]})
    if got.status_code != 200:
        v.append(f"route: a listed card document returned {got.status_code}")

    # ...and a path is not a digest, on the wire as well as in the module.
    for bad in ("../../etc/passwd", "docs/DECISIONS.md", "/etc/passwd"):
        bad_res = client.get("/api/docs/document", params={"doc_id": bad})
        if bad_res.status_code != 404:
            v.append(f"route: {bad!r} returned {bad_res.status_code}, expected "
                     f"404 -- the route takes a digest, never a path")

    # The guard that makes the wall structural rather than argued.
    try:
        review_app.create_app(Path("nonexistent.db"), {}, None)
        v.append("route: create_app served vault routes with no estate clause")
    except ValueError:
        pass

    route_coverage = "driven -- passed"
    return v


def _cards(board: dict) -> dict:
    out = {}
    for col in board["columns"]:
        for card in col["cards"]:
            out[card["key"]] = card
    return out


def _column(board: dict, key: str) -> dict:
    return next(c for c in board["columns"] if c["key"] == key)


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _fixture(root)
        b = docs_board.board(repo_root=root)
        cards = _cards(b)

        # --- columns are a function of which files exist --------------------
        expected = {
            "inflight": "in_flight",
            "built": "built_not_walked",
            "ticked": "walked",
            "evidence": "walked",
            "solo": "walked",
            "done": "archived",
            "build_round_9": "archived",
            "ROUND_9": "archived",
            "HANDOFF_final.md": "archived",
            "old_plan.md": "archived",
            "late": "archived",
            "naked.md": "archived",
        }
        for key, col in expected.items():
            card = cards.get(key)
            if card is None:
                v.append(f"board: no card for {key!r} -- it was dropped, not placed")
            elif card["column"] != col:
                v.append(f"board: {key!r} landed in {card['column']!r}, expected {col!r}")

        # --- `archivable` is not a column. It is not derivable. -------------
        if any(c["key"] == "archivable" for c in b["columns"]):
            v.append("board: invented an `archivable` column -- it requires a "
                     "human ruling the filesystem cannot supply")

        # --- open items counted, not interpreted ----------------------------
        if cards.get("built", {}).get("open_items") != 2:
            v.append("board: `- [ ]` count wrong on the built card")
        if cards.get("built", {}).get("done_items") != 1:
            v.append("board: `- [x]` count wrong on the built card")
        if cards.get("ticked", {}).get("done_items") != 2:
            v.append("board: `- [~]` must count as done (walked with a caveat)")

        # --- the backticked checkbox form counts identically to the plain one
        bt = cards.get("backticked", {})
        if bt.get("open_items") != 2:
            v.append("board: `` - `[ ]` `` must count as open, same as `- [ ]` "
                     f"-- got {bt.get('open_items')!r} (a confident zero here is "
                     f"exactly the bug this tester exists to catch)")
        if bt.get("done_items") != 2:
            v.append("board: `` - `[x]` `` / `` - `[~]` `` must count as done, "
                     f"same as the plain form -- got {bt.get('done_items')!r}")

        # --- the checkbox finding is SURFACED, never normalised -------------
        ev = cards.get("evidence", {})
        if docs_board.FINDING_EVIDENCE_IN_RESULTS not in ev.get("flags", []):
            v.append("board: a walked card with an unticked sheet and a ticked "
                     "results log must be flagged")
        if ev.get("done_items") != 0:
            v.append("board: the evidence-in-results-log card must still read 0 "
                     "done on its sheet -- normalising it destroys the finding")
        if not any(f["kind"] == docs_board.FINDING_EVIDENCE_IN_RESULTS
                   for f in b["findings"]):
            v.append("board: the checkbox finding must reach the findings list, "
                     "not only the card")
        tk = cards.get("ticked", {})
        if docs_board.FINDING_EVIDENCE_IN_RESULTS in tk.get("flags", []):
            v.append("board: a properly ticked sheet must NOT be flagged -- the "
                     "flag would then mean nothing")

        # --- a walk-sheet with no brief is a shape, not a broken pair -------
        solo = cards.get("solo", {})
        if solo.get("kind") != "walk_only":
            v.append(f"board: a walk-sheet with no brief must be `walk_only`, "
                     f"got {solo.get('kind')!r}")
        if solo.get("has", {}).get("brief"):
            v.append("board: walk_only card claims a brief it does not have")

        # --- unmatched: a card kind, never a drop ---------------------------
        for key in ("build_round_9", "ROUND_9", "HANDOFF_final.md", "old_plan.md",
                    "late"):
            if cards.get(key, {}).get("kind") != "unmatched":
                v.append(f"board: {key!r} should be `unmatched` -- it anchors no "
                         f"brief+report pair by filename")
        if cards.get("done", {}).get("kind") != "pair":
            v.append("board: an archived brief+report by stem is a pair")

        arch_col = _column(b, "archived")
        # The five asserted above plus `naked.md`, which is unclassified and
        # pairs with nothing. The count is published on the column so a pairing
        # regression cannot hide in the pot: it is a number that should move
        # only when archive/ moves.
        if arch_col.get("unmatched_count") != 6:
            v.append(f"board: archived column unmatched_count is "
                     f"{arch_col.get('unmatched_count')}, expected 6")
        if arch_col.get("file_count") != 8:
            v.append(f"board: archived column must account for every file in "
                     f"archive/ -- got {arch_col.get('file_count')} of 8")

        # --- disposition comes from the STAMP, not the filename -------------
        if cards.get("HANDOFF_final.md", {}).get("disposition") != "retired":
            v.append("board: disposition must be read from the stamp")
        if cards.get("build_round_9", {}).get("disposition") != "completed pair":
            v.append("board: a stamp saying `completed pair` must be reported as "
                     "such even when the card pairs as unmatched -- the stamp is "
                     "the archivist's judgement, the kind is what names carry")
        if cards.get("old_plan.md", {}).get("disposition") != "superseded":
            v.append("board: a disposition that elaborates beyond the vocabulary "
                     "must still classify by its leading term")
        if cards.get("late", {}).get("disposition") != "completed pair":
            v.append("board: a stamp below a multi-line uat comment must still "
                     "be found -- two real archived files are shaped that way")

        # --- unstamped is a FINDING, not a card kind ------------------------
        naked = cards.get("naked.md", {})
        if "naked.md" not in naked.get("unstamped", []):
            v.append("board: an archive file with no stamp must be reported "
                     "unstamped")
        if naked.get("disposition") is not None:
            v.append("board: an unstamped file must not be given a disposition")
        if not any(f["kind"] == docs_board.FINDING_UNSTAMPED for f in b["findings"]):
            v.append("board: unstamped must reach `findings` -- it is a breach of "
                     "§3, not a naming quirk like unmatched")
        if naked.get("kind") == "unstamped":
            v.append("board: `unstamped` must not be a card kind -- it is "
                     "orthogonal to whether the file pairs")

        # --- off-board is declared, not silent ------------------------------
        off = {o["name"] for o in b["off_board"]}
        for name in ("DECISIONS.md", "RUNBOOK_thing.md"):
            if name not in off:
                v.append(f"board: {name} must be listed as deliberately off the "
                         f"board with a reason, not silently skipped")
        if any(k in cards for k in ("DECISIONS.md", "RUNBOOK_thing.md")):
            v.append("board: a maintained doc must not be given a column")

        # --- nothing is persisted -------------------------------------------
        before = {p.name for p in root.rglob("*")}
        docs_board.board(repo_root=root)
        after = {p.name for p in root.rglob("*")}
        if before != after:
            v.append(f"board: deriving the board created files: {after - before}")
        if b.get("persisted") is not False:
            v.append("board: must report persisted=false as a first-class field")
        if b.get("actions_enabled") is not False:
            v.append("board: this slice is read-only; actions_enabled must be false")

        # --- reading a card body: check one, the identifier ------------------
        brief = cards["built"]["members"][0]
        got = docs_board.read_card_document(brief["id"], repo_root=root)
        if "# brief" not in got["text"]:
            v.append("board: a listed card document must render")
        for bogus in ("../../etc/passwd", "docs/DECISIONS.md", "", "0" * 16):
            try:
                docs_board.read_card_document(bogus, repo_root=root)
                v.append(f"board: read {bogus!r} -- the route takes a digest, "
                         f"never a path, and an unknown digest must refuse")
            except estate_data.DocumentRefused as exc:
                if exc.reason != "unknown_document":
                    v.append(f"board: {bogus!r} refused as {exc.reason!r}, "
                             f"expected unknown_document")

    # --- check two: containment, against the REAL anchor ---------------------
    # The claim under test is the reason this slice exists: the board renders
    # the toolkit's own docs/ without depending on the toolkit sitting inside a
    # configured estate root. So this half uses REPO_ROOT itself.
    repo = estate_data.REPO_ROOT
    if not (repo / "docs" / "README.md").is_file():
        v.append(f"board: REPO_ROOT ({repo}) does not look like this repository "
                 "-- the anchor is derived from __file__ and must land on the "
                 "checkout root")

    live = docs_board.board()
    live_cards = _cards(live)
    if not live_cards:
        v.append("board: derived no cards from the real docs/")
    readme = None
    for card in live_cards.values():
        for m in card["members"]:
            if m["rel"].startswith("docs/"):
                readme = m
                break
        if readme:
            break
    if readme is None:
        v.append("board: no real card member resolved under docs/")
    else:
        try:
            docs_board.read_card_document(readme["id"])
        except estate_data.DocumentRefused as exc:
            v.append(f"board: refused to read its own {readme['rel']} "
                     f"({exc.reason}) -- the repo anchor is not doing its job")

    # The anchor must be a boundary, not a formality: a path outside the repo
    # is refused even though the gate is being called directly.
    outside = Path(tempfile.gettempdir()) / "definitely-not-in-the-repo.md"
    try:
        estate_data.resolve_contained(outside, (repo,),
                                      outside_reason="outside_repo_root")
        v.append("board: the repo anchor admitted a path outside the repo")
    except estate_data.DocumentRefused as exc:
        if exc.reason != "outside_repo_root":
            v.append(f"board: wrong refusal tag {exc.reason!r} for an outside path")

    # A sibling directory sharing the repo's name prefix must not be admitted --
    # this is the `/estate-evil` vs `/estate` case, on the new anchor.
    try:
        estate_data.resolve_contained(Path(str(repo) + "-evil") / "x.md", (repo,),
                                      outside_reason="outside_repo_root")
        v.append("board: `<repo>-evil` was read as being inside `<repo>` -- the "
                 "os.sep guard is not holding on the repo anchor")
    except estate_data.DocumentRefused:
        pass

    # An empty anchor set refuses everything. "No boundary configured" must
    # never degrade into "no boundary applies".
    try:
        estate_data.resolve_contained(repo / "docs" / "README.md", ())
        v.append("board: an empty anchor set admitted a path")
    except estate_data.DocumentRefused as exc:
        if exc.reason != "no_configured_roots":
            v.append(f"board: empty anchors refused as {exc.reason!r}")

    # --- the routes, driven end-to-end when the extra is installed -----------
    # Slice 1 shipped a defect that every unit-level tester passed: the search
    # index was built on the main thread and queried from uvicorn's threadpool,
    # which `sqlite3` refuses. It surfaced only under a real client. So the
    # board's routes are driven through one here.
    #
    # FastAPI is an optional extra (`pip install -e .[review]`), deliberately
    # out of the stdlib-only core, so this half is conditional. It is NOT a
    # silent skip: absence is reported by `route_coverage` below, and a machine
    # that has the extra -- which is any machine that can actually run the
    # surface -- gets the coverage.
    v.extend(_route_checks())

    # --- the estate resolver is unchanged by the extraction ------------------
    # resolve_document_path now delegates to the shared gate; its refusal tags
    # are load-bearing for the surface and must not have drifted.
    empty = estate_data.EstateData(None, [], Path("nowhere"), reason="estate_missing")
    try:
        empty.resolve_document_path("deadbeefdeadbeef")
        v.append("board: the estate resolver stopped refusing an unknown id")
    except estate_data.DocumentRefused as exc:
        if exc.reason != "unknown_document":
            v.append(f"board: estate resolver refusal drifted to {exc.reason!r}")

    return v
