"""tester_bench_report: Task 5's comparison -- `chronicler.pipeline.
bench_report`. Proves row assembly, the "indistinguishable, never tie-
broken" comparison rule, the detectable-difference floor, and markdown
rendering against hand-built entries in the exact shapes Tasks 2-4 and K2's
own `_build_report` already produce.

Hermetic -- no I/O, no network.
"""
from __future__ import annotations

from chronicler.pipeline import bench_ledger as bl
from chronicler.pipeline import bench_report as br


_CF = bl.build_config_fingerprint({"context_length": 8192})
_PF = "promptfp"


def _entries(model_id, values, *, config_fingerprint=_CF, prompt_fingerprint=_PF,
             cool_down_preceded=False):
    return [
        {"model_id": model_id, "stage": "K2", "cool_down_preceded": cool_down_preceded,
         "config_fingerprint": config_fingerprint, "prompt_fingerprint": prompt_fingerprint,
         "generation_ms_per_token": v, "wall_clock_seconds": v / 10}
        for v in values
    ]


def run() -> list[str]:
    v: list[str] = []

    # --- quality_from_k2_report: reads K2's real field names, never
    #     fabricates a rate from an empty denominator ----------------------
    acc, corr = br.quality_from_k2_report(
        {"claims_extracted": 90, "claims_rejected": 10, "quote_rejection_rate": 0.1})
    if acc != 0.9:
        v.append(f"acceptance_rate should be 1 - quote_rejection_rate = 0.9: {acc}")
    if corr is not None:
        v.append(f"correctness_rate must be None this round (no Level 2 ground truth): {corr}")
    acc_empty, _ = br.quality_from_k2_report(
        {"claims_extracted": 0, "claims_rejected": 0, "quote_rejection_rate": 0.0})
    if acc_empty is not None:
        v.append("a K2 report that offered zero claims (nothing scanned) should not "
                 "fabricate an acceptance_rate of 1.0")

    # --- build_row (bench): throughput, quality, reliability, load cost
    #     assembled correctly, cool_down partition respected ---------------
    bench_entries = _entries("gemma-4", [40.0, 42.0, 45.0, 41.0])
    bench_entries += _entries("gemma-4", [200.0], cool_down_preceded=True)  # must be excluded
    failure_entries = [
        {"kind": "timeout", "model_id": "gemma-4", "stage": "K2", "host": "h",
         "config_fingerprint": _CF, "prompt_fingerprint": _PF, "position_in_session": 1},
    ]
    load_cost_entries = [
        {"kind": "cold_start", "host": "h", "config_fingerprint": _CF,
         "model_id": "gemma-4", "cold_start_tax_seconds": 3.5},
        {"kind": "switch", "host": "h", "config_fingerprint": _CF,
         "model_id": "candidate-x", "to_model_id": "gemma-4", "switch_tax_seconds": 5.1},
        {"kind": "residency", "host": "h", "config_fingerprint": _CF,
         "model_id": "gemma-4", "to_model_id": "candidate-x", "both_resident": False},
    ]
    k2_report = {"claims_extracted": 90, "claims_rejected": 10, "quote_rejection_rate": 0.1}

    row = br.build_row(source="bench", host="h", model_id="gemma-4", stage="K2",
                        cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                        bench_entries=bench_entries, failure_entries=failure_entries,
                        load_cost_entries=load_cost_entries, k2_report=k2_report)
    if row.n != 4:
        v.append(f"the cool_down_preceded=True entry must not be pooled into this row's n: {row.n}")
    if row.acceptance_rate != 0.9:
        v.append(f"row.acceptance_rate should come straight from the K2 report: {row.acceptance_rate}")
    if row.failure_counts.get("timeout") != 1:
        v.append(f"row.failure_counts should reflect the one recorded timeout: {row.failure_counts}")
    if row.failure_rate != 1 / 5:
        v.append(f"row.failure_rate should be failures/(failures+successes) = 1/5: {row.failure_rate}")
    if row.cold_start_tax_seconds != 3.5 or row.switch_tax_seconds != 5.1 or row.both_resident is not False:
        v.append(f"row's load-cost fields did not assemble correctly: {row}")

    # --- build_row (production): labelled distinctly, no fingerprints,
    #     no load-cost/reliability fabricated for a source that never
    #     carries them ------------------------------------------------------
    prod_entries = [
        {"model_id": "gemma-4", "stage": "K2", "cool_down_preceded": False,
         "generation_ms_per_token": x} for x in (38.0, 39.0)
    ]
    prod_row = br.build_row(source="production", host="10280L", model_id="gemma-4", stage="K2",
                             cool_down_preceded=False, config_fingerprint=None, prompt_fingerprint=None,
                             ledger_entries=prod_entries,
                             caveats=("not taken over the evaluation set; carries no config fingerprint",))
    if prod_row.n != 2 or prod_row.config_fingerprint is not None:
        v.append(f"production row should summarize the production ledger with no config "
                 f"fingerprint: {prod_row}")
    if prod_row.failure_rate is not None or prod_row.cold_start_tax_seconds is not None:
        v.append(f"a production row must not fabricate reliability/load-cost figures it "
                 f"never actually carries: {prod_row}")
    if not prod_row.caveats:
        v.append("a production row must carry its caveat explicitly, not rely on the reader "
                 "to infer it from the source label alone")

    # --- build_row with zero evidence: every figure absent, never guessed -
    empty_row = br.build_row(source="bench", host="h", model_id="nope", stage="K2",
                              cool_down_preceded=False, config_fingerprint=_CF,
                              prompt_fingerprint=_PF, bench_entries=[])
    if (empty_row.n != 0 or empty_row.median_ms_per_token is not None
            or empty_row.failure_rate is not None):
        v.append(f"a unit with zero entries anywhere should report absence, not zeros or "
                 f"guesses: {empty_row}")

    # --- compare_medians: clearly separated, overlapping, and
    #     insufficient-data cases -------------------------------------------
    fast = br.build_row(source="bench", host="h", model_id="fast-model", stage="K2",
                         cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                         bench_entries=_entries("fast-model", [10.0, 11.0, 9.5, 10.5]))
    slow = br.build_row(source="bench", host="h", model_id="slow-model", stage="K2",
                         cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                         bench_entries=_entries("slow-model", [40.0, 42.0, 45.0, 41.0]))
    if br.compare_medians(fast, slow) != "a_faster":
        v.append(f"clearly-separated IQRs should name a direction: "
                 f"{br.compare_medians(fast, slow)}")

    close_a = br.build_row(source="bench", host="h", model_id="m1", stage="K2",
                            cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                            bench_entries=_entries("m1", [40.0, 41.0, 39.0, 40.5]))
    close_b = br.build_row(source="bench", host="h", model_id="m2", stage="K2",
                            cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                            bench_entries=_entries("m2", [40.2, 40.8, 39.5, 40.9]))
    if br.compare_medians(close_a, close_b) != "indistinguishable":
        v.append(f"overlapping IQRs must report indistinguishable, never tie-broken by "
                 f"preference (e.g. picking the lower median anyway): "
                 f"{br.compare_medians(close_a, close_b)}")

    single = br.build_row(source="bench", host="h", model_id="m3", stage="K2",
                           cool_down_preceded=False, config_fingerprint=_CF, prompt_fingerprint=_PF,
                           bench_entries=_entries("m3", [40.0]))
    if br.compare_medians(single, fast) != "insufficient_data":
        v.append(f"a single-repeat row must refuse ANY verdict, including "
                 f"'indistinguishable' -- a single run cannot carry a claim against a "
                 f"spread it never measured: {br.compare_medians(single, fast)}")

    # --- detectable_difference_floor: real spread -> a positive fraction;
    #     no data -> None, never a default -----------------------------------
    floor = br.detectable_difference_floor(row)
    if floor is None or floor <= 0:
        v.append(f"a row with real spread should yield a positive detectable-difference "
                 f"floor: {floor}")
    if br.detectable_difference_floor(empty_row) is not None:
        v.append("a row with no throughput measurements must not yield a floor -- there is "
                 "no spread to derive one from")

    # --- render_markdown_table: every row present, absence as an em-dash,
    #     caveats surfaced ---------------------------------------------------
    table = br.render_markdown_table([row, prod_row, empty_row])
    if table.count("\n|") < 3:  # header + separator + at least the data rows
        v.append(f"render_markdown_table should emit one table row per ComparisonRow: {table!r}")
    if "not taken over the evaluation set" not in table:
        v.append("render_markdown_table should surface a row's caveats, not silently drop them")
    if "nope" not in table:
        v.append("a row with zero evidence should still appear in the table (as absence), "
                 "not be dropped from it")

    return v
