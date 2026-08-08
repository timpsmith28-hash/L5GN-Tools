"""tester_curator_ratify: Task 2's K0 ratification engine.

Hermetic, against a throwaway ``git init`` repo -- never the real
``config/mcf_conversation_map.tsv``, which already carries unrelated
uncommitted work in this checkout that this build must not touch (see
COWORK_REPORT_curator_tab.md). This is also the ONLY safe way to test
staging: a real `git add` against the live file would stage someone else's
WIP alongside the test row.

Covers the load-bearing rules, each asserted directly rather than inferred:
  * append-only -- a second ratify never edits or removes the first row's
    bytes;
  * provenance is mandatory and drawn from the 0033 vocabulary only;
  * re-ratifying an already-present session_id is a no-op, not a duplicate;
  * a different-project collision is never offered a ratify action;
  * a same-project collision offers exactly a pair action;
  * six counts print including the zeroes;
  * `stage_ratified_map` stages ONLY the map path, and the staged diff shown
    would match a terminal `git diff --staged`.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from chronicler.review import curator_ratify as ratify

HEADER = "session_id\tlocal_folder\tproject_id\tconversation_name\tnotes\n"
EXISTING_ROW = ("local_existing\tMCF/Foo\tFoo\tFoo - existing thread\t"
                "[provenance:machine-matched:pass-1] pre-existing row\n")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                           capture_output=True, text=True)


def _init_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "test")
    cfg = root / "config"
    cfg.mkdir(exist_ok=True)
    mapfile = cfg / "mcf_conversation_map.tsv"
    mapfile.write_text(HEADER + EXISTING_ROW, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    return mapfile


def run() -> list[str]:
    v: list[str] = []

    # --- evidence spans: pass1 (prefix) and pass2 (substring) --------------
    ev = ratify.evidence_spans("Hello world, this is the opener",
                                "Hello world, this is the opener plus more text",
                                "pass1", 12)
    if ev["sheet"]["span"] != [0, 12] or ev["conversation"]["span"] != [0, 12]:
        v.append(f"curator_ratify: pass1 span wrong: {ev}")

    ev2 = ratify.evidence_spans("a specific phrase that recurs",
                                "some preamble text a specific phrase that recurs and more",
                                "pass2", None)
    if ev2["conversation"]["span"] is None:
        v.append("curator_ratify: pass2 substring span not located")

    ev3 = ratify.evidence_spans(None, "conversation text", "pass1", 5)
    if ev3["sheet"]["span"] is not None or ev3["conversation"]["span"] is not None:
        v.append("curator_ratify: a missing sheet side must not fabricate a span")

    # --- six counts, including the zeroes -----------------------------------
    rows = [
        {"session_id": "s1", "status": "matched", "match_pass": "pass1"},
        {"session_id": "s2", "status": "matched", "match_pass": "pass2"},
        {"session_id": "", "status": "ambiguous-different-project", "match_pass": "pass1"},
    ]
    counts = ratify.six_counts(rows, unmapped_folder_count=0)
    for key in ratify.SIX_COUNT_KEYS:
        if key not in counts:
            v.append(f"curator_ratify: six_counts missing key {key!r}")
    if counts["ambiguous_same_project"] != 0:
        v.append("curator_ratify: a zero count must print as 0, not be absent")
    if counts["matched_by_pass1"] != 1 or counts["matched_by_pass2"] != 1:
        v.append(f"curator_ratify: six_counts miscounted matches: {counts}")

    # --- K0's own rules honoured, not re-litigated --------------------------
    diff = ratify.row_action({"status": ratify.STATUS_AMBIG_DIFF})
    if diff["action"] != "hand_map_or_leave":
        v.append("curator_ratify: a different-project collision must offer NO "
                 f"ratify action; got {diff}")
    same = ratify.row_action({"status": ratify.STATUS_AMBIG_SAME})
    if same["action"] != "ratify_pair":
        v.append(f"curator_ratify: a same-project collision must offer ratify_pair; got {same}")
    short = ratify.row_action({"status": ratify.STATUS_UNMATCHED,
                               "note": "only 13 normalised chars (<60); never reaches pass 2"})
    if short["action"] != "hand_map_only" or "60" not in short["reason"]:
        v.append(f"curator_ratify: a below-floor row must say why it never "
                 f"reached pass 2; got {short}")

    # --- provenance is mandatory and from the 0033 vocabulary --------------
    try:
        ratify.build_row(session_id="x", local_folder="MCF/X", project_id="X",
                         conversation_name="X - t", provenance="just trust me")
        v.append("curator_ratify: build_row accepted an unrecognised provenance tag")
    except ratify.RatifyError:
        pass

    # --- append-only: a real staged diff, against a throwaway repo ---------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        mapfile = _init_repo(root)
        before = mapfile.read_text(encoding="utf-8")

        new_row = ratify.build_row(
            session_id="local_new", local_folder="MCF/Bar", project_id="Bar",
            conversation_name="Bar - thread", provenance=ratify.PROV_PASS1,
            note="matched_length=112")
        result = ratify.append_ratified_row(new_row, path=mapfile)
        if result["status"] != "appended":
            v.append(f"curator_ratify: expected 'appended', got {result}")

        after = mapfile.read_text(encoding="utf-8")
        if not after.startswith(before):
            v.append("curator_ratify: append rewrote bytes that already existed "
                     "on disk -- this must be a pure append")
        if EXISTING_ROW.strip() not in after:
            v.append("curator_ratify: the pre-existing row was altered or dropped")

        # re-ratify the SAME session_id: must be a no-op, not a duplicate
        again = ratify.append_ratified_row(new_row, path=mapfile)
        if again["status"] != "already_ratified":
            v.append(f"curator_ratify: re-ratifying must no-op; got {again}")
        if after.count("local_new") != (mapfile.read_text(encoding="utf-8").count("local_new")):
            v.append("curator_ratify: re-ratifying duplicated the row")

        # stage ONLY the map path
        staged_path = ratify.stage_ratified_map(root)
        if staged_path != "config/mcf_conversation_map.tsv":
            v.append(f"curator_ratify: staged an unexpected path: {staged_path}")
        status = _git(root, "diff", "--staged", "--name-only").stdout.strip().splitlines()
        if status != ["config/mcf_conversation_map.tsv"]:
            v.append(f"curator_ratify: git diff --staged touched more than the "
                     f"map: {status}")
        diff_text = ratify.staged_diff(root)
        added_lines = [l for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed_lines = [l for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---")]
        if not any("local_new" in l for l in added_lines):
            v.append("curator_ratify: staged diff must show the new row as an addition")
        if removed_lines:
            v.append(f"curator_ratify: staged diff must never show a removal "
                     f"(append-only): {removed_lines}")
        if any("local_existing" in l for l in added_lines):
            v.append("curator_ratify: the pre-existing row must not appear as "
                     "an addition in the staged diff")
        # This exact diff is quoted in COWORK_REPORT_curator_tab.md as the
        # real staged-diff demonstration the brief requires.

        # --- pair ratification: exactly two rows, both explicit -------------
        row_a = ratify.build_row(session_id="local_pair_a", local_folder="MCF/Baz",
                                 project_id="Baz", conversation_name="Baz - a",
                                 provenance=ratify.PROV_PASS1, note="paired by date")
        row_b = ratify.build_row(session_id="local_pair_b", local_folder="MCF/Baz",
                                 project_id="Baz", conversation_name="Baz - b",
                                 provenance=ratify.PROV_PASS1, note="paired by date")
        pair_results = ratify.append_ratified_pair(row_a, row_b, path=mapfile)
        if len(pair_results) != 2 or any(r["status"] != "appended" for r in pair_results):
            v.append(f"curator_ratify: pair ratify did not append both rows: {pair_results}")

    return v
