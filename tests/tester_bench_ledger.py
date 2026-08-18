"""tester_bench_ledger: Task 2's widened bench ledger --
`chronicler.pipeline.bench_ledger`. Mirrors `tester_ledger.py`'s shape
(parse -> record -> summarize -> feed from a real timing line) but proves
the WIDENED row: prompt_fingerprint, config_fingerprint, host,
position_in_session, and the discarded numerics parsed straight off a real
TIMING_WINDOW/TIMING_CLAIM line -- plus that it is structurally incapable of
writing `ledger.DEFAULT_LEDGER_PATH` (no bench-side default path exists at
all).

Hermetic. Every test writes to a temp path.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from chronicler.pipeline import bench_ledger as bl
from chronicler.pipeline import ledger


def run() -> list[str]:
    v: list[str] = []

    # --- there is no accidental path collision with production -------------
    if bl.DEFAULT_BENCH_LEDGER_PATH == ledger.DEFAULT_LEDGER_PATH:
        v.append("bench_ledger's default path must never equal the production "
                 "calibration_ledger.jsonl path")
    if "calibration_ledger" in str(bl.DEFAULT_BENCH_LEDGER_PATH):
        v.append("bench_ledger's default path must not live under the same "
                 "filename as the production ledger")

    # --- parse_timing_line: a real TIMING_WINDOW line, every field typed ---
    window_line = (
        "TIMING_WINDOW conversation_id=c1 project_id=proj window_index=1 "
        "windows_total=3 token_count=512 model_id=gemma-4 "
        "cool_down_preceded=False usage_available=True prompt_tokens=400 "
        "completion_tokens=80 generation_ms_per_token=12.50 "
        "wall_clock_seconds=1.234"
    )
    parsed = bl.parse_timing_line(window_line)
    if parsed.get("window_index") != 1 or not isinstance(parsed["window_index"], int):
        v.append(f"parse_timing_line should coerce window_index to int: {parsed}")
    if parsed.get("cool_down_preceded") is not False:
        v.append(f"parse_timing_line should coerce cool_down_preceded to bool: {parsed}")
    if parsed.get("generation_ms_per_token") != 12.5:
        v.append(f"parse_timing_line should coerce generation_ms_per_token to float: {parsed}")
    if parsed.get("token_count") != 512:
        v.append(f"parse_timing_line should carry token_count (a discarded numeric "
                 f"Task 2 wants recovered): {parsed}")

    # a TIMING_CLAIM line never carries token_count/window_index -- absent,
    # never guessed or defaulted to 0/None-as-a-value-in-the-dict
    claim_line = (
        "TIMING_CLAIM conversation_id=c1 project_id=proj model_id=qwen-32b "
        "cool_down_preceded=True usage_available=True prompt_tokens=80 "
        "completion_tokens=20 generation_ms_per_token=33.30 "
        "wall_clock_seconds=0.700"
    )
    parsed_claim = bl.parse_timing_line(claim_line)
    if "token_count" in parsed_claim or "window_index" in parsed_claim:
        v.append(f"a TIMING_CLAIM line carries no token_count/window_index -- "
                 f"parse_timing_line must not invent them: {parsed_claim}")

    # "unavailable"/"None" values parse to None, never a string or a fabricated 0
    unavailable_line = window_line.replace(
        "generation_ms_per_token=12.50", "generation_ms_per_token=unavailable")
    parsed_unavail = bl.parse_timing_line(unavailable_line)
    if parsed_unavail.get("generation_ms_per_token") is not None:
        v.append(f"an 'unavailable' figure must parse to None, not a fabricated "
                 f"number or the literal string: {parsed_unavail}")

    # --- build_config_fingerprint: deterministic, sensitive to every key ---
    settings_a = {"context_length": 8192, "gpu_offload_layers": 30, "quantisation": "q4_0"}
    settings_b = dict(settings_a, gpu_offload_layers=31)
    fp_a1 = bl.build_config_fingerprint(settings_a)
    fp_a2 = bl.build_config_fingerprint(dict(settings_a))  # different dict, same content
    fp_b = bl.build_config_fingerprint(settings_b)
    if fp_a1 != fp_a2:
        v.append("build_config_fingerprint should be deterministic for identical settings")
    if fp_a1 == fp_b:
        v.append("build_config_fingerprint must change when a single setting (here "
                 "gpu_offload_layers) changes -- a config fingerprint that can't tell "
                 "30 offload layers from 31 defeats Task 2 item 2's whole point")

    # --- make_bench_ledger_feeder: on_timing_line-shaped, widened row ------
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bench.jsonl"
        feed = bl.make_bench_ledger_feeder(
            p, stage="K2", host="LucasGoonPC", config_fingerprint=fp_a1,
            position_in_session=2, prompt_fingerprint="deadbeef")
        feed("window", 12.5, window_line)
        feed(None, None, "matching: 2/5 done")  # non-timing line: no-op
        feed("window", None, unavailable_line)  # no measurement: no-op (absence in, absence out)
        entries = bl.load_entries(p)
        if len(entries) != 1:
            v.append(f"make_bench_ledger_feeder should append exactly 1 entry (the one "
                     f"real measurement): {entries}")
        else:
            e = entries[0]
            for field, expected in (
                ("model_id", "gemma-4"), ("stage", "K2"), ("cool_down_preceded", False),
                ("generation_ms_per_token", 12.5), ("prompt_fingerprint", "deadbeef"),
                ("config_fingerprint", fp_a1), ("host", "LucasGoonPC"),
                ("position_in_session", 2), ("kind", "window"),
                ("token_count", 512), ("wall_clock_seconds", 1.234),
                ("prompt_tokens", 400), ("completion_tokens", 80),
                ("conversation_id", "c1"), ("project_id", "proj"),
                ("time_to_first_token_ms", None),
            ):
                if e.get(field) != expected:
                    v.append(f"fed entry field {field!r} should be {expected!r}, got "
                             f"{e.get(field)!r}: {e}")
            if "timestamp" not in e:
                v.append(f"a fed entry should carry a timestamp: {e}")

        # a fresh feeder for a DIFFERENT config -- rows must not blend
        feed2 = bl.make_bench_ledger_feeder(
            p, stage="K2", host="LucasGoonPC", config_fingerprint=fp_b,
            position_in_session=1, prompt_fingerprint="deadbeef")
        feed2("window", 20.0, window_line.replace("model_id=gemma-4", "model_id=gemma-4"))
        entries2 = bl.load_entries(p)
        if len(entries2) != 2:
            v.append(f"a second feeder call should APPEND, not replace: {entries2}")
        configs_seen = {e["config_fingerprint"] for e in entries2}
        if len(configs_seen) != 2:
            v.append(f"two feeders built with different config_fingerprint values must "
                     f"produce rows with two DISTINCT config_fingerprint values, not "
                     f"blended: {configs_seen}")

    # --- append_entry: required-field enforcement, no silent default path --
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "b2.jsonl"
        complete = {
            "model_id": "m1", "stage": "K2", "cool_down_preceded": False,
            "generation_ms_per_token": 10.0, "prompt_fingerprint": "pf",
            "config_fingerprint": "cf", "host": "h", "position_in_session": 0,
        }
        bl.append_entry(complete, p)
        try:
            bl.append_entry({"model_id": "m1"}, p)
            v.append("append_entry accepted an entry missing required fields")
        except ValueError:
            pass
        try:
            bl.append_entry(complete)  # type: ignore[call-arg]
            v.append("append_entry must require `path` explicitly -- no optional "
                     "fallback that could coincide with the production ledger's path")
        except TypeError:
            pass

    # --- summarize: partitioned on (model, stage, cool_down, config, prompt) -
    entries = [
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
         "config_fingerprint": "cfA", "prompt_fingerprint": "pf1",
         "generation_ms_per_token": 40.0, "wall_clock_seconds": 4.0},
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
         "config_fingerprint": "cfA", "prompt_fingerprint": "pf1",
         "generation_ms_per_token": 60.0, "wall_clock_seconds": 6.0},
        # same model/stage/cool-down, DIFFERENT config -- must not blend
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
         "config_fingerprint": "cfB", "prompt_fingerprint": "pf1",
         "generation_ms_per_token": 9999.0, "wall_clock_seconds": 999.0},
        # same everything except prompt_fingerprint -- must not blend either
        {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
         "config_fingerprint": "cfA", "prompt_fingerprint": "pf2",
         "generation_ms_per_token": 5.0, "wall_clock_seconds": 0.5},
    ]
    clean = bl.summarize(entries, model_id="m1", stage="K2", cool_down_preceded=False,
                          config_fingerprint="cfA", prompt_fingerprint="pf1")
    if clean is None or clean.n != 2 or clean.median_ms_per_token != 50.0:
        v.append(f"summarize should find exactly the 2 (m1,K2,False,cfA,pf1) entries, "
                 f"median 50.0: {clean}")
    if clean is not None and clean.median_wall_clock_seconds != 5.0:
        v.append(f"summarize should also report median wall-clock, per Task 2 item 3 "
                 f"('keep both'): {clean}")

    mismatched_config = bl.summarize(entries, model_id="m1", stage="K2",
                                      cool_down_preceded=False, config_fingerprint="cfZ",
                                      prompt_fingerprint="pf1")
    if mismatched_config is not None:
        v.append(f"a config_fingerprint with no matching entries should summarize to "
                 f"None, never borrow another config's figures: {mismatched_config}")

    mismatched_prompt = bl.summarize(entries, model_id="m1", stage="K2",
                                      cool_down_preceded=False, config_fingerprint="cfA",
                                      prompt_fingerprint="pfZ")
    if mismatched_prompt is not None:
        v.append(f"a prompt_fingerprint with no matching entries should summarize to "
                 f"None, never borrow another prompt version's figures: {mismatched_prompt}")

    if clean is not None and mismatched_config is None:
        pass  # the cfB entry (9999.0) must never leak into clean's median -- already
              # implied by clean.median_ms_per_token == 50.0 above, checked explicitly:
    if clean is not None and 9999.0 in (clean.min_ms_per_token, clean.max_ms_per_token):
        v.append("a different config_fingerprint's measurement leaked into this "
                 "summary's min/max")

    # --- known_configurations: distinct (model, config, prompt) triples ----
    triples = bl.known_configurations(entries)
    if len(triples) != 3:
        v.append(f"known_configurations should list 3 distinct (model, config, prompt) "
                 f"triples across the 4 entries above (cfA/pf1, cfB/pf1, cfA/pf2): {triples}")

    return v
