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
        cov = c.coverage()
        if cov["present_not_mapped"] != ["local_zzz"]:
            v.append("curator_data: coverage() must pass K1's "
                     "present_not_mapped through unchanged")

    return v
