"""tester_uat_sidebar: parsing, verdict validation and stamped emission for the
UAT sidebar (COWORK brief: uat_sidebar, slice 2 of two).

Hermetic and stdlib-only where it can be: parsing, validation and emission are
driven against a fixture tree in a temp dir, never the real `docs/`. The one
place this reaches the real repository is the same two checks
`tester_docs_board` already makes -- containment holds against the real
anchor, and the route exists -- because that is the claim worth making, not a
claim about which sheets currently exist in this checkout.

`emit_results_log`'s `git add` is exercised against the fixture dir, which is
not a git repository -- `run_git` degrades to a no-op there (returns ''), same
as every other caller of it does outside a checkout. That is not tested as a
success; only that emission still produces the right file and content
regardless of whether staging had anything to attach to.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from chronicler.review import docs_board, estate_data, uat_sidebar

_SHEET = """# UAT walk-sheet — fixture

## A · first section

- [ ] **A1** Deterministic check text.
      — sheet note for A1, folded into the item.
- [x] **A2** Already ticked on the sheet.

## B · second section

- [ ] **B1** Needs a judgement call.
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root / "docs" / "UAT_fixture.md", _SHEET)

        # --- Task 1: parse a sheet into items --------------------------------
        parsed = uat_sidebar.parse_sheet(root / "docs" / "UAT_fixture.md")
        if not parsed["readable"]:
            v.append("uat_sidebar: a real sheet must parse as readable")
        secs = {s["label"]: s for s in parsed["sections"]}
        if "A · first section" not in secs:
            v.append("uat_sidebar: section header not captured")
        a_items = {it["id"]: it for it in secs.get("A · first section", {}).get("items", [])}
        if a_items.get("A1", {}).get("state") != "open":
            v.append("uat_sidebar: `- [ ]` must parse as state=open")
        if a_items.get("A2", {}).get("state") != "done":
            v.append("uat_sidebar: `- [x]` must parse as state=done")
        if "sheet note for A1" not in a_items.get("A1", {}).get("sheet_note", ""):
            v.append("uat_sidebar: a continuation line must fold into sheet_note, "
                     "not be dropped -- it is often the most useful line")
        b_items = {it["id"]: it for it in secs.get("B · second section", {}).get("items", [])}
        if "B1" not in b_items:
            v.append("uat_sidebar: item in the second section not captured")

        # --- sheet_view: no results log yet -----------------------------------
        view = uat_sidebar.sheet_view(root, "fixture")
        if view["results_exists"]:
            v.append("uat_sidebar: no results log was written; results_exists must be False")
        if view["evidence_in_results_log"]:
            v.append("uat_sidebar: no results log means no evidence-in-results finding")

        # --- sheet_rel/results_rel are the RESOLVED path, not the typed stem --
        # (correctness sweep, finding 6). A citation built from what the caller
        # typed is not provenance -- these must always agree with the path the
        # code actually resolved and read, not with f"UAT_{stem}...".
        expected_sheet_rel = (root / "docs" / "UAT_fixture.md").relative_to(root).as_posix()
        if view["sheet_rel"] != expected_sheet_rel:
            v.append(f"uat_sidebar: sheet_rel must be the resolved path, got "
                     f"{view['sheet_rel']!r}, expected {expected_sheet_rel!r}")

        # The regression this guards against is Windows-specific: NTFS resolves
        # a mismatched-case request to the real file, so it is the one platform
        # where "built from stem" and "built from the resolved path" can
        # actually disagree and be observed disagreeing. On a case-sensitive
        # filesystem the mismatched request simply refuses (no_sheet) before
        # either path is ever built, so there is nothing to compare -- the
        # win-only guard is the correctness sweep's own diagnosis of the bug,
        # not a weaker test.
        if os.name == "nt":
            mismatched = uat_sidebar.sheet_view(root, "Fixture")  # real stem is "fixture"
            if mismatched["sheet_rel"] != expected_sheet_rel:
                v.append(
                    "uat_sidebar: opening a sheet with mismatched case must cite "
                    f"the path actually resolved ({expected_sheet_rel!r}), got "
                    f"{mismatched['sheet_rel']!r} -- a citation built from the "
                    f"caller's keystrokes, not from provenance")

        # --- an unticked sheet whose results log carries the ticks ------------
        # The board's ruling (UAT_docs_board_results.md, B1/B2): an unticked
        # sheet does not mean unwalked when the evidence is in the results log
        # instead. The sidebar must surface that here too, on the item view.
        _write(root / "docs" / "UAT_evidenced.md", "# uat\n- [ ] a\n- [ ] b\n")
        _write(root / "docs" / "UAT_evidenced_results.md",
              "<!-- uat: commit=abc1234 dirty=false host=rig walked=2026-07-30 -->\n"
              "# results\n- [x] a\n- [x] b\n")
        ev_view = uat_sidebar.sheet_view(root, "evidenced")
        if not ev_view["evidence_in_results_log"]:
            v.append("uat_sidebar: unticked sheet + ticked results log must be flagged")
        if not ev_view["note"]:
            v.append("uat_sidebar: the finding must carry an explanatory note, not "
                     "just a boolean nobody reads")

        # --- Task 4: emitting moves the card on the BOARD, by file existence
        # alone -- docs_board.py is untouched by this slice; the card must
        # move itself because the results log now exists on disk, never
        # because this module told the board anything.
        _write(root / "docs" / "COWORK_BRIEF_loopcheck.md", "# brief\n")
        _write(root / "docs" / "COWORK_REPORT_loopcheck.md", "# report\n")
        _write(root / "docs" / "UAT_loopcheck.md", "# uat\n- [ ] **L1** a check.\n")
        before_board = docs_board.board(repo_root=root)
        before_col = next(c["column"] for col in before_board["columns"]
                          for c in col["cards"] if c["key"] == "loopcheck")
        if before_col != "built_not_walked":
            v.append(f"uat_sidebar: loopcheck card should start built_not_walked, "
                     f"got {before_col!r} -- test fixture is wrong, not the code")
        uat_sidebar.emit_results_log(
            root, "loopcheck", [{"id": "L1", "verdict": "walked", "evidence": "ok"}])
        after_board = docs_board.board(repo_root=root)
        after_col = next(c["column"] for col in after_board["columns"]
                         for c in col["cards"] if c["key"] == "loopcheck")
        if after_col != "walked":
            v.append(f"uat_sidebar: after emit, docs_board must derive column="
                     f"walked from the results log existing on disk, got "
                     f"{after_col!r} -- the loop does not close by itself")

        # --- unknown stem / bad stem: refused, not a crash --------------------
        try:
            uat_sidebar.sheet_view(root, "does_not_exist")
            v.append("uat_sidebar: an unknown stem must refuse")
        except estate_data.DocumentRefused as exc:
            if exc.reason != "no_sheet":
                v.append(f"uat_sidebar: unknown stem refused as {exc.reason!r}, expected no_sheet")
        for bad in ("../../etc/passwd", "a/b", "", "a b"):
            try:
                uat_sidebar.sheet_view(root, bad)
                v.append(f"uat_sidebar: stem {bad!r} must be refused, never resolved to a path")
            except estate_data.DocumentRefused as exc:
                if exc.reason != "bad_stem":
                    v.append(f"uat_sidebar: stem {bad!r} refused as {exc.reason!r}, expected bad_stem")

        # --- Task 2: verdict validation ---------------------------------------
        ok = [{"id": "A1", "verdict": "walked", "evidence": "pasted output"}]
        if uat_sidebar.validate_entries(ok):
            v.append("uat_sidebar: a walked verdict with evidence must validate clean")
        missing_reason = [{"id": "B1", "verdict": "deferred", "evidence": ""}]
        if not uat_sidebar.validate_entries(missing_reason):
            v.append("uat_sidebar: deferred with no reason must be refused, not emitted")
        missing_reason_blocked = [{"id": "B1", "verdict": "blocked", "evidence": "   "}]
        if not uat_sidebar.validate_entries(missing_reason_blocked):
            v.append("uat_sidebar: blocked with only whitespace must still be refused")
        bad_verdict = [{"id": "A1", "verdict": "passed", "evidence": "x"}]
        if not uat_sidebar.validate_entries(bad_verdict):
            v.append("uat_sidebar: an unknown verdict string must be refused")

        # --- Task 3: emit, new -------------------------------------------------
        entries = [
            {"id": "A1", "verdict": "walked", "evidence": "line one\nline two"},
            {"id": "B1", "verdict": "deferred", "evidence": "needs Tim's judgement"},
        ]
        out = uat_sidebar.emit_results_log(root, "fixture", entries)
        if out["status"] != "created":
            v.append(f"uat_sidebar: first emit should be status=created, got {out['status']!r}")
        rp = root / "docs" / "UAT_fixture_results.md"
        if not rp.is_file():
            v.append("uat_sidebar: emit must write the results log to disk")
        text = rp.read_text(encoding="utf-8")

        if "<!-- uat: commit=" not in text.splitlines()[0]:
            v.append("uat_sidebar: the uat stamp must be the first line")
        if "gate=" in text:
            v.append("uat_sidebar: the emitted stamp must never carry a gate= field")
        if "walked=" not in text or "host=" not in text or "dirty=" not in text:
            v.append("uat_sidebar: the stamp must carry walked=, host= and dirty=")
        if "[EVIDENCE]" not in text:
            v.append("uat_sidebar: a walked verdict must emit an [EVIDENCE] tag")
        if "[DEFERRED]" not in text:
            v.append("uat_sidebar: a deferred verdict must emit a [DEFERRED] tag")
        if "line one\nline two" not in text.replace("  line one", "line one").replace("  line two", "line two") \
           and "line one" not in text:
            v.append("uat_sidebar: multi-line evidence (pasted output) must survive verbatim")
        if "Not walked, and why" not in text:
            v.append("uat_sidebar: a 'not walked, and why' section is required")
        if "B1" not in text.split("Not walked, and why", 1)[-1]:
            v.append("uat_sidebar: a deferred item must appear in 'not walked, and why'")
        if "A1" in text.split("Not walked, and why", 1)[-1]:
            v.append("uat_sidebar: a walked item must NOT appear in 'not walked, and why'")

        # --- an item given no verdict at all is simply absent, never invented --
        if "**B2" in text:
            v.append("uat_sidebar: an item never given a verdict must not appear "
                     "in the emitted log")

        # --- resume: a prior emit is parsed back for the sidebar to offer -------
        prior = uat_sidebar.parse_results_log(rp)
        if prior.get("A1", {}).get("verdict") != "walked":
            v.append("uat_sidebar: parse_results_log must recover the walked "
                     "verdict for A1")
        if prior.get("A1", {}).get("evidence") != "line one\nline two":
            v.append("uat_sidebar: parse_results_log must recover multi-line "
                     f"evidence verbatim, got {prior.get('A1', {}).get('evidence')!r}")
        if prior.get("B1", {}).get("verdict") != "deferred":
            v.append("uat_sidebar: parse_results_log must recover the deferred "
                     "verdict for B1")
        if prior.get("B1", {}).get("evidence") != "needs Tim's judgement":
            v.append("uat_sidebar: parse_results_log must recover single-line "
                     "evidence for B1")
        if "B2" in prior:
            v.append("uat_sidebar: an item never emitted must not appear in "
                     "parse_results_log's output")
        # sheet_view surfaces this as prior_entries, matching parse_results_log
        # exactly -- the sidebar's resume button reads from here.
        resumed_view = uat_sidebar.sheet_view(root, "fixture")
        if resumed_view["prior_entries"] != prior:
            v.append("uat_sidebar: sheet_view's prior_entries must match "
                     "parse_results_log's direct output")

        # --- emit again: must refuse to overwrite silently ---------------------
        second = uat_sidebar.emit_results_log(root, "fixture", entries)
        if second["status"] != "exists":
            v.append("uat_sidebar: emitting onto an existing results log without "
                     "mode='append' must report status=exists and write nothing")
        text_after = rp.read_text(encoding="utf-8")
        if text_after != text:
            v.append("uat_sidebar: a refused re-emit must not modify the file on disk")

        # --- append: keeps the original stamp, adds a new dated section --------
        appended = uat_sidebar.emit_results_log(root, "fixture", entries, mode="append")
        if appended["status"] != "appended":
            v.append(f"uat_sidebar: mode='append' should report status=appended, "
                     f"got {appended['status']!r}")
        text3 = rp.read_text(encoding="utf-8")
        if not text3.startswith(text.splitlines()[0]):
            v.append("uat_sidebar: appending must preserve the ORIGINAL stamp line "
                     "-- testimony is not edited")
        if "Additional walk" not in text3:
            v.append("uat_sidebar: an appended emission must be clearly marked as "
                     "an additional walk section")

        # --- resume after append: the LATEST occurrence of an id wins ----------
        # B1 was deferred in the first section and deferred again verbatim in
        # the append above; append once more with B1 now actually walked, and
        # confirm parse_results_log offers the freshest verdict back, not the
        # first one it finds.
        uat_sidebar.emit_results_log(
            root, "fixture",
            [{"id": "B1", "verdict": "walked", "evidence": "resolved on retest"}],
            mode="append")
        prior2 = uat_sidebar.parse_results_log(rp)
        if prior2.get("B1", {}).get("verdict") != "walked":
            v.append("uat_sidebar: parse_results_log must resolve to the LATEST "
                     "recorded verdict for an id walked more than once, got "
                     f"{prior2.get('B1')!r}")

        # --- validation failure refuses the whole emit, writes nothing new -----
        _write(root / "docs" / "UAT_invalid.md", "# uat\n- [ ] **X1** thing\n")
        bad_entries = [{"id": "X1", "verdict": "blocked", "evidence": ""}]
        try:
            uat_sidebar.emit_results_log(root, "invalid", bad_entries)
            v.append("uat_sidebar: emit must refuse when an entry fails validation")
        except ValueError:
            pass
        if (root / "docs" / "UAT_invalid_results.md").exists():
            v.append("uat_sidebar: a refused emit must not create a results log")

        # --- Task 6 (COWORK_BRIEF_ui_witness): [G]/[W]/[H] markers split the
        # emitted log into Machine-verified / Human ruling, cited from a
        # witness artefact, never a human verdict field for machine items.
        _write(root / "docs" / "UAT_layered.md",
              "# uat\n\n"
              "## Sec\n\n"
              "- [ ] [W] **W1** a witness-shaped check.\n"
              "- [ ] [H] **H1** a judgement call.\n")
        # No witness artefact yet: honest absence, not silent omission.
        no_witness_entries = [{"id": "H1", "verdict": "walked", "evidence": "yes, that's right"}]
        out_nw = uat_sidebar.emit_results_log(root, "layered", no_witness_entries)
        text_nw = (root / "docs" / "UAT_layered_results.md").read_text(encoding="utf-8")
        if "Machine-verified" not in text_nw or "Human ruling" not in text_nw:
            v.append("uat_sidebar: a sheet with layer markers must split into "
                     "Machine-verified / Human ruling sections")
        if "No witness artefact found" not in text_nw:
            v.append("uat_sidebar: a missing witness artefact must be reported "
                     "in the log, not silently omitted")
        for forbidden in ("passed", '"ok"', "result="):
            if forbidden in text_nw:
                v.append(f"uat_sidebar: emitted log must never carry {forbidden!r}")

        # Now with a witness artefact present: W1 is cited, not human-verdicted.
        witness_dir = root / "data" / "witness"
        witness_dir.mkdir(parents=True, exist_ok=True)
        import json as _json
        (witness_dir / "layered.json").write_text(_json.dumps({
            "sheet": "layered", "ran_at": "2026-08-03T00:00:00+00:00",
            "host": "fixture", "commit": "deadbee", "dirty": False,
            "fixture": "tests/witness/fixtures/x",
            "items": [{"id": "W1", "outcome": "matched", "detail": "rendered as expected"}],
        }), encoding="utf-8")
        out_w = uat_sidebar.emit_results_log(
            root, "layered",
            [{"id": "H1", "verdict": "walked", "evidence": "still correct"}],
            mode="append")
        text_w = (root / "docs" / "UAT_layered_results.md").read_text(encoding="utf-8")
        if "[matched]" not in text_w:
            v.append("uat_sidebar: a cited witness observation must appear "
                     "inline for its item, using the schema's outcome word")
        if "data/witness/layered.json" not in text_w:
            v.append("uat_sidebar: the citation must name the artefact path, "
                     "as a visible line, not an HTML comment")
        # The citation line itself must not sit inside an HTML comment -- only
        # the leading `<!-- uat: ... -->` stamp comment is allowed to be one.
        body_after_stamp = text_w.split("-->", 1)[-1]
        if "data/witness/layered.json" not in body_after_stamp:
            v.append("uat_sidebar: the citation must appear as visible body "
                     "text after the uat stamp comment, not inside a comment")
        for forbidden in ('"passed"', '"ok"', '"result"'):
            if forbidden in text_w:
                v.append(f"uat_sidebar: emitted log must never carry {forbidden!r}")

        # A legacy sheet with no markers at all must keep the old flat shape.
        legacy_entries = [{"id": "A1", "verdict": "walked", "evidence": "unchanged shape"}]
        uat_sidebar.emit_results_log(root, "fixture", legacy_entries, mode="append")
        text_legacy = rp.read_text(encoding="utf-8")
        if "Machine-verified" in text_legacy.split("Additional walk", 2)[-1]:
            v.append("uat_sidebar: a sheet with no layer markers must keep the "
                     "original flat-by-section shape, not gain a machine split")

    # --- containment holds against the REAL anchor, same shape as the board ---
    repo = estate_data.REPO_ROOT
    outside = Path(tempfile.gettempdir()) / "definitely-not-in-the-repo.md"
    try:
        uat_sidebar._resolve(outside, repo)
        v.append("uat_sidebar: the repo anchor admitted a path outside the repo")
    except estate_data.DocumentRefused as exc:
        if exc.reason != "outside_repo_root":
            v.append(f"uat_sidebar: wrong refusal tag {exc.reason!r} for an outside path")

    # --- the route exists and is well-behaved on this checkout's own docs -----
    from chronicler.review import app as review_app
    if review_app.available():
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            TestClient = None
        if TestClient is not None:
            app = review_app.create_app(None, {}, None, estate=None, index=None)
            client = TestClient(app)
            res = client.get("/api/uat/sheet", params={"stem": "does-not-exist-anywhere"})
            if res.status_code != 404:
                v.append(f"uat_sidebar: route for an unknown stem returned "
                         f"{res.status_code}, expected 404")
            res_bad = client.get("/api/uat/sheet", params={"stem": "../../etc/passwd"})
            if res_bad.status_code != 404:
                v.append(f"uat_sidebar: route for a path-shaped stem returned "
                         f"{res_bad.status_code}, expected 404 -- never resolved as a path")
            # emit with a validation failure must be a 400, and must not touch
            # any real file in this checkout.
            emit_res = client.post("/api/uat/emit", json={
                "stem": "does-not-exist-anywhere",
                "entries": [{"id": "Z1", "verdict": "blocked", "evidence": ""}],
            })
            if emit_res.status_code not in (400, 404):
                v.append(f"uat_sidebar: emit with an invalid entry against an "
                         f"unknown stem returned {emit_res.status_code}, expected "
                         f"400 or 404")

    return v
