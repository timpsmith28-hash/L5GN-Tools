"""tester_ledger: Task 2's calibration ledger -- recording, partitioning on
cool_down_preceded, spread-not-mean summaries, and "no measurements -> no
estimate."

Hermetic. Every test writes to a temp path, never the real
data/knowledge_curator/calibration_ledger.jsonl.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from chronicler.pipeline import ledger


def run() -> list[str]:
    v: list[str] = []

    # --- record_from_timing: absence in, absence out -- never estimated ----
    present = ledger.record_from_timing(
        {"model_id": "m1", "cool_down_preceded": False, "generation_ms_per_token": 42.5},
        stage="K2")
    if present != {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
                    "generation_ms_per_token": 42.5}:
        v.append(f"record_from_timing did not shape a present measurement correctly: {present}")

    absent = ledger.record_from_timing(
        {"model_id": "m1", "cool_down_preceded": False, "generation_ms_per_token": None},
        stage="K2")
    if absent is not None:
        v.append(f"record_from_timing should return None when generation_ms_per_token is "
                 f"None, never a fabricated entry: {absent}")

    missing_field = ledger.record_from_timing({"generation_ms_per_token": 10.0}, stage="K2")
    if missing_field is not None:
        v.append("record_from_timing should return None when model_id/cool_down_preceded "
                 "are missing, not guess them")

    # --- append_entry: real file, one JSON line, timestamp stamped,
    #     required fields enforced ------------------------------------------
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ledger.jsonl"
        ledger.append_entry(present, path=p)
        raw_lines = p.read_text(encoding="utf-8").splitlines()
        if len(raw_lines) != 1:
            v.append(f"append_entry should write exactly one line: {raw_lines}")
        parsed = json.loads(raw_lines[0])
        if "timestamp" not in parsed:
            v.append(f"an appended entry should carry a timestamp: {parsed}")
        for field in ("model_id", "stage", "cool_down_preceded", "generation_ms_per_token"):
            if parsed.get(field) != present[field]:
                v.append(f"appended entry field {field!r} did not round-trip: {parsed}")

        try:
            ledger.append_entry({"model_id": "m1"}, path=p)
            v.append("append_entry accepted an entry missing required fields")
        except ValueError:
            pass

        # a second append is a genuine APPEND, not an overwrite
        ledger.append_entry(
            {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
             "generation_ms_per_token": 50.0}, path=p)
        if len(p.read_text(encoding="utf-8").splitlines()) != 2:
            v.append("a second append_entry call should ADD a line, not replace the file")

    # --- load_entries: absent file -> [], corrupt lines skipped not fatal --
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "nope.jsonl"
        if ledger.load_entries(p) != []:
            v.append("load_entries on a never-created ledger should return [], not raise")

        p2 = Path(td) / "corrupt.jsonl"
        ledger.append_entry(present, path=p2)
        with p2.open("a", encoding="utf-8") as f:
            f.write("not valid json at all\n")
        ledger.append_entry(
            {"model_id": "m2", "stage": "K2", "cool_down_preceded": False,
             "generation_ms_per_token": 10.0}, path=p2)
        entries = ledger.load_entries(p2)
        if len(entries) != 2:
            v.append(f"a corrupt line should be skipped, not crash the whole read, and the "
                     f"valid lines on either side should still load: got {len(entries)}")

    # --- summarize: partitioned by (model_id, stage, cool_down_preceded);
    #     reports SPREAD, not just a mean; None when nothing matches --------
    entries = [
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 40.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 50.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 60.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 45.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 55.0},
        # a post-cool-down population that reads much slower -- must NOT
        # blend into the above and inflate/deflate its spread
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": True, "generation_ms_per_token": 200.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": True, "generation_ms_per_token": 210.0},
        # a different model entirely -- must never blend into m1's figures
        {"model_id": "m2", "stage": "K2", "cool_down_preceded": False, "generation_ms_per_token": 9999.0},
    ]

    clean = ledger.summarize(entries, model_id="m1", stage="K2", cool_down_preceded=False)
    if clean is None or clean.n != 5 or clean.median_ms_per_token != 50.0:
        v.append(f"summarize should find exactly the 5 clean m1/K2/not-preceded entries, "
                 f"median 50.0: {clean}")
    if clean.min_ms_per_token != 40.0 or clean.max_ms_per_token != 60.0:
        v.append(f"summarize should report min/max as part of the spread, not just a mean: {clean}")
    if clean.p25_ms_per_token >= clean.median_ms_per_token or clean.p75_ms_per_token <= clean.median_ms_per_token:
        v.append(f"p25 should be below the median and p75 above it: {clean}")

    preceded = ledger.summarize(entries, model_id="m1", stage="K2", cool_down_preceded=True)
    if preceded is None or preceded.n != 2 or preceded.median_ms_per_token != 205.0:
        v.append(f"the cool_down_preceded partition should be reported SEPARATELY, not "
                 f"blended into the clean population: {preceded}")

    # never blend across models
    m2 = ledger.summarize(entries, model_id="m2", stage="K2", cool_down_preceded=False)
    if m2 is None or m2.n != 1:
        v.append(f"a different model_id must never contribute to another model's summary: {m2}")
    if clean.median_ms_per_token == m2.median_ms_per_token:
        v.append("m1 and m2's summaries should be independent, not coincidentally identical "
                 "in a way that suggests they got mixed")

    # no measurements for this exact filter -> None, plainly, never a guess
    nothing = ledger.summarize(entries, model_id="m1", stage="K4", cool_down_preceded=False)
    if nothing is not None:
        v.append(f"summarize should return None when nothing matches the filter (K4 was "
                 f"never recorded for m1 here), not fabricate a figure: {nothing}")

    # --- known_models: distinct model_ids only, sorted, deterministic -----
    if ledger.known_models(entries) != ["m1", "m2"]:
        v.append(f"known_models should list every distinct model_id, sorted: "
                 f"{ledger.known_models(entries)}")
    if ledger.known_models([]) != []:
        v.append("known_models on an empty ledger should return [], not raise")

    # --- make_ledger_feeder: on_timing_line-shaped, wires straight into a
    #     real TIMING_WINDOW/TIMING_CLAIM line, ignores everything else -----
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "fed.jsonl"
        feed = ledger.make_ledger_feeder(p, stage="K4")
        claim_line = ("TIMING_CLAIM conversation_id=c1 project_id=proj claim_index=0 "
                      "model_id=qwen-32b cool_down_preceded=False usage_available=True "
                      "prompt_tokens=80 completion_tokens=20 generation_ms_per_token=33.30 "
                      "wall_clock_seconds=0.700")
        feed("claim", 33.3, claim_line)
        feed(None, None, "matching: 2/5 done")       # non-timing line: no-op
        feed("claim", None, claim_line.replace("generation_ms_per_token=33.30",
                                                 "generation_ms_per_token=unavailable"))  # no measurement: no-op
        fed_entries = ledger.load_entries(p)
        if len(fed_entries) != 1:
            v.append(f"make_ledger_feeder should append exactly 1 entry (the one real "
                     f"measurement), ignoring the non-timing and unmeasured lines: "
                     f"{fed_entries}")
        elif (fed_entries[0]["model_id"] != "qwen-32b" or fed_entries[0]["stage"] != "K4"
              or fed_entries[0]["cool_down_preceded"] is not False
              or fed_entries[0]["generation_ms_per_token"] != 33.3):
            v.append(f"the fed entry's fields did not extract correctly from the real "
                     f"TIMING_CLAIM line: {fed_entries[0]}")

    return v
