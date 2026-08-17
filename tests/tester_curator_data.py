"""tester_curator_data: Task 1's read-only data layer.

Hermetic and against fixtures only -- never against the real
``data/knowledge_curator/`` (which does not exist on most machines, this one
included, and testing "K1 exists" against a live pipeline run would be
testing today's state and calling it a code defect, the same reasoning
tester_docs_board.py gives for not asserting against real docs/).

Covers: every artefact absent reads as a clean "not run" (never an
exception), blocked-reason text distinguishes "map is header-only" from "map
is ratified but this stage hasn't run", per-artefact staleness (no single
collapsed timestamp), and Task 5's coverage() is a straight passthrough of
K1's own reconciliation fields.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from chronicler.review import curator_data as cd


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []

    # --- everything absent: the current true state of most machines --------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data_dir = root / "data" / "knowledge_curator"  # never created
        ratified = root / "config" / "mcf_conversation_map.tsv"  # never created
        c = cd.Curator(data_dir=data_dir, ratified_map_path=ratified)

        if c.available:
            v.append("curator_data: available=True with no data_dir on disk")
        header = c.header()
        for stage, state in header["stages"].items():
            if state["exists"]:
                v.append(f"curator_data: {stage} reports exists=True with nothing on disk")
            if not state["blocked"]:
                v.append(f"curator_data: {stage} reports blocked=False with nothing on disk")
            if not state["blocked_reason"]:
                v.append(f"curator_data: {stage} has no blocked_reason -- "
                         "'no data' is not the answer the operator needs")
        if "header-only" not in header["stages"]["K1"]["blocked_reason"]:
            v.append("curator_data: K1 with a 0-row ratified map must name the "
                     "map as header-only, not a generic 'not run'")
        cov = c.coverage()
        if cov["available"]:
            v.append("curator_data: coverage() available=True with no K1 output")
        for key in ("projects", "unresolved", "label_disagreements",
                    "mapped_but_absent_on_disk", "present_not_mapped"):
            if cov[key] != []:
                v.append(f"curator_data: coverage()[{key!r}] not empty with no K1 output")

    # --- ratified map has rows, but K1 has not been run --------------------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data_dir = root / "data" / "knowledge_curator"
        ratified = root / "config" / "mcf_conversation_map.tsv"
        _write(ratified, "session_id\tlocal_folder\tproject_id\tconversation_name\tnotes\n"
                          "local_abc\tMCF/Foo\tFoo\tFoo - thread\t[provenance:machine-matched:pass-1]\n")
        c = cd.Curator(data_dir=data_dir, ratified_map_path=ratified)
        k1 = c.stage_states()["K1"]
        if k1.exists:
            v.append("curator_data: K1 reports exists=True with no knowledge_index.json")
        if "header-only" in (k1.blocked_reason or ""):
            v.append("curator_data: K1 blocked-reason wrongly says header-only "
                     "when the map has a real row")
        if "ratified" not in (k1.blocked_reason or ""):
            v.append("curator_data: K1 blocked-reason must say the map IS "
                     "ratified when it has rows but K1 hasn't run")

    # --- a partially-run pipeline: K1/K3 present, K2/K4/K5 absent -----------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data_dir = root / "data" / "knowledge_curator"
        ratified = root / "config" / "mcf_conversation_map.tsv"
        _write(ratified, "session_id\tlocal_folder\tproject_id\tconversation_name\tnotes\n"
                          "local_abc\tMCF/Foo\tFoo\tFoo - thread\t[provenance:machine-matched:pass-1]\n")
        idx = {"projects": [{"project_id": "Foo", "local_folder": "MCF/Foo",
                              "conversations": ["local_abc"], "knowledge_files": []}],
               "unresolved": [], "label_disagreements": [],
               "mapped_but_absent_on_disk": [], "present_not_mapped": ["local_zzz"]}
        _write(data_dir / "knowledge_index.json", json.dumps(idx))
        _write(data_dir / "corpus_index.json", json.dumps({"projects": []}))
        c = cd.Curator(data_dir=data_dir, ratified_map_path=ratified)
        states = c.stage_states()
        if not states["K1"].exists or not states["K3"].exists:
            v.append("curator_data: K1/K3 outputs present but reported absent")
        if states["K2"].exists or states["K4"].exists or states["K5"].exists:
            v.append("curator_data: K2/K4/K5 absent but reported present")
        if states["K1"].generated_at_source != "file_mtime":
            v.append("curator_data: knowledge_index.json carries no "
                     "generated_at field -- must fall back to file_mtime, "
                     "reported as such")
        # per-artefact staleness: K1 and K3 must not be forced onto one clock
        if states["K1"].generated_at is None or states["K3"].generated_at is None:
            v.append("curator_data: an existing artefact must carry a "
                     "generated_at, even a file_mtime-derived one")

    v.extend(_run_estate_gate())
    v.extend(_run_estate_map_path())
    v.extend(_run_resolver())
    return v


def _run_estate_gate() -> list[str]:
    """DECISIONS 0039 clause 2 / 0044 clause 3: the Curator is excluded
    ONLY on a machine declaring 'both', or one with no declared estate at
    all -- never on a fixed allowlist of estate names."""
    v: list[str] = []
    if cd.curator_estate_gap_for("both") is None:
        v.append("curator_estate_gap_for('both') must gate -- it did not")
    if cd.curator_estate_gap_for(None) is None:
        v.append("curator_estate_gap_for(None) must gate -- it did not")
    if cd.curator_estate_gap_for("unknown") is None:
        v.append("curator_estate_gap_for('unknown') must gate -- config."
                 "machine()'s documented default estate is 'unknown' for "
                 "any unconfigured machine, and it must not slip through "
                 "the gate only to crash later resolving a map path")
    for estate in ("work", "personal"):
        if cd.curator_estate_gap_for(estate) is not None:
            v.append(f"curator_estate_gap_for({estate!r}) wrongly gated")
    gap = cd.curator_estate_gap_for("both")
    if "0039" not in gap or "0044" not in gap:
        v.append("curator_estate_gap_for: reason text must cite 0039/0044, "
                 "not the superseded 0032")
    if "0032" in gap:
        v.append("curator_estate_gap_for: reason text still cites the "
                 "superseded DECISIONS 0032")
    return v


def _run_estate_map_path() -> list[str]:
    """0039 clause 1 / 0044 clause 4: never a fixed filename for every
    estate -- each declared estate resolves to its own map."""
    v: list[str] = []
    work_path = cd.ratified_map_path_for_estate("work")
    personal_path = cd.ratified_map_path_for_estate("personal")
    if work_path == personal_path:
        v.append("ratified_map_path_for_estate: work and personal resolved "
                 "to the same path")
    if work_path.name != "mcf_conversation_map.tsv":
        v.append("ratified_map_path_for_estate('work') must keep the "
                 "long-shipped filename -- got " + work_path.name)
    if work_path != cd.RATIFIED_MAP_PATH:
        v.append("ratified_map_path_for_estate('work') must match the "
                 "legacy RATIFIED_MAP_PATH constant exactly")
    try:
        cd.ratified_map_path_for_estate("both")
        v.append("ratified_map_path_for_estate('both') must refuse, not "
                 "return a path -- the Curator never runs on that estate")
    except ValueError:
        pass
    try:
        cd.ratified_map_path_for_estate("unknown-estate")
        v.append("ratified_map_path_for_estate: an undeclared estate name "
                 "must refuse, never guess a filename")
    except ValueError:
        pass
    c = cd.Curator(declared_estate="personal")
    if c.ratified_map_path != personal_path:
        v.append("Curator(declared_estate='personal') did not resolve to "
                 "the personal map path")
    c2 = cd.Curator()
    if c2.ratified_map_path != cd.RATIFIED_MAP_PATH:
        v.append("Curator() with no args must still default to the legacy "
                 "RATIFIED_MAP_PATH -- existing callers rely on this")
    return v


def _run_resolver() -> list[str]:
    """DECISIONS 0046: the last row per key wins, a revoked row drops out
    of the resolved view entirely, and the raw view keeps every row."""
    v: list[str] = []
    header = "session_id\tlocal_folder\tproject_id\tconversation_name\tnotes\n"
    rows_text = (
        header
        + "local_a\tMCF/Foo\tFoo\tFoo thread\t[provenance:machine-matched:pass-1]\n"
        + "local_a\tMCF/Bar\tBar\tFoo thread\t[provenance:hand-mapped:no-candidate] "
          "[status:corrected] wrong project first time\n"
        + "local_b\tMCF/Baz\tBaz\tBaz thread\t[provenance:machine-matched:pass-1]\n"
        + "local_b\tMCF/Baz\tBaz\tBaz thread\t[provenance:hand-mapped:no-candidate] "
          "[status:revoked] should not have been mapped\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "map.tsv"
        _write(path, rows_text)

        raw = cd.ratified_map_rows(path)
        if len(raw) != 4:
            v.append(f"ratified_map_rows: expected 4 raw rows, got {len(raw)}")

        resolved = cd.resolve_map_rows(raw)
        if set(resolved) != {"local_a"}:
            v.append(f"resolve_map_rows: expected only local_a to resolve, "
                     f"got {sorted(resolved)}")
        elif resolved["local_a"]["project_id"] != "Bar":
            v.append("resolve_map_rows: local_a must resolve to the "
                     "correcting row's project_id ('Bar')")

        resolved_rows = cd.resolved_map_rows(path)
        if len(resolved_rows) != 1:
            v.append(f"resolved_map_rows: expected 1 row, got {len(resolved_rows)}")

        annotated = cd.raw_map_rows_annotated(path)
        if len(annotated) != 4:
            v.append(f"raw_map_rows_annotated: expected 4 rows, got {len(annotated)}")
        else:
            current_flags = [a["is_current"] for a in annotated]
            # local_a: row 0 superseded, row 1 current. local_b: row 2
            # superseded, row 3 (revoked) resolves to nothing current.
            if current_flags != [False, True, False, False]:
                v.append(f"raw_map_rows_annotated: is_current flags wrong: "
                         f"{current_flags}")
            if annotated[1]["status"] != "corrected":
                v.append("raw_map_rows_annotated: row 1 must parse status="
                         "'corrected'")
            if annotated[3]["status"] != "revoked":
                v.append("raw_map_rows_annotated: row 3 must parse status="
                         "'revoked'")
            if annotated[0]["status"] is not None:
                v.append("raw_map_rows_annotated: an uncorrected row must "
                         "parse status=None")
    return v
