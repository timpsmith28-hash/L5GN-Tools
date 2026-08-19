"""tester_bench_failures: Task 3's failure taxonomy --
`chronicler.pipeline.bench_failures`. Proves classification against real
shapes this repo already produces (`curator_control.StageOutcome`, K2's own
`--out` report conversation entries) and that a failure can never be
recorded without a valid `kind` (the brief's own stop condition).

Hermetic. Every test writes to a temp path.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.pipeline import bench_failures as bf
from chronicler.review import curator_control as cc


def run() -> list[str]:
    v: list[str] = []

    # --- classify_window_by_size: proactive, never guesses a missing figure
    if bf.classify_window_by_size(9000, 8192) != "context_overflow":
        v.append("a window bigger than context_length (plus reserve) should "
                 "classify as context_overflow")
    if bf.classify_window_by_size(1000, 8192) is not None:
        v.append("a window well within context_length should not classify as "
                 "context_overflow")
    if bf.classify_window_by_size(None, 8192) is not None:
        v.append("an unknown token_count must never be guessed into a verdict")
    if bf.classify_window_by_size(9000, None) is not None:
        v.append("an unknown context_length must never be guessed into a verdict")

    # --- classify_crash_text: exception-class-name signatures, not
    #     server-specific wording -----------------------------------------
    cases = {
        "Traceback (most recent call last):\n  ...\nTimeoutError: timed out": "timeout",
        ("Traceback (most recent call last):\n  ...\nurllib.error.URLError: "
         "<urlopen error [Errno 111] Connection refused>"): "transport_error",
        "Traceback (most recent call last):\n  ...\nurllib.error.HTTPError: HTTP Error 400: Bad Request":
            "transport_error",
        ("Traceback (most recent call last):\n  ...\nurllib.error.HTTPError: HTTP Error 400: "
         "the request exceeds the model context length"): "context_overflow",
        "Traceback (most recent call last):\n  ...\nKeyError: 'choices'": "unknown",
        # Real-run evidence (2026-08-18/19, gemma-4-e4b, work rig): llama.cpp's
        # ACTUAL wording, previously unmatched by any marker -- 25 real crashes
        # were misclassified transport_error before this marker was added.
        ("Traceback (most recent call last):\n  ...\nurllib.error.HTTPError: HTTP Error 400: "
         "Bad Request\nsend_error: task id = 66732, error: request (79115 tokens) exceeds "
         "the available context size (32768 tokens), try increasing it"): "context_overflow",
    }
    for text, expected in cases.items():
        got = bf.classify_crash_text(text)
        if got != expected:
            v.append(f"classify_crash_text({text!r}) should be {expected!r}, got {got!r}")

    # a context-overflow marker inside an HTTPError body must win over the
    # generic transport-error match -- the more specific classification,
    # not the first one found
    mixed = ("urllib.error.HTTPError: HTTP Error 400: prompt is too long for "
             "this model's context window")
    if bf.classify_crash_text(mixed) != "context_overflow":
        v.append("a context-overflow marker inside an HTTPError body must take "
                 "priority over the generic transport_error match")

    # --- classify_stage_outcome: real StageOutcome, duck-typed -------------
    failed = cc.StageOutcome(stage="K2", state="failed", detail="exit 1",
                              returncode=1, stdout_tail="TimeoutError: timed out")
    success = cc.StageOutcome(stage="K2", state="success", detail="completed", returncode=0)
    blocked = cc.StageOutcome(stage="K2", state="blocked", detail="no model selected")
    skipped = cc.StageOutcome(stage="K2", state="skipped", detail="no input", returncode=0)

    if bf.classify_stage_outcome(failed) != "timeout":
        v.append("a failed StageOutcome should classify from its stdout_tail")
    if bf.classify_stage_outcome(success) is not None:
        v.append("a success StageOutcome is not a failure -- must classify to None")
    if bf.classify_stage_outcome(blocked) is not None:
        v.append("a blocked StageOutcome never reached the model -- must classify to None, "
                 "not be mistaken for a model capability limit")
    if bf.classify_stage_outcome(skipped) is not None:
        v.append("a skipped StageOutcome (no input) is not a failure -- must classify to None")

    # --- classify_conversation_result: real K2 report shape ----------------
    clean_zero = {"conversation_id": "c1", "parse_failed": False,
                  "scanned_with_zero": True, "windows_parse_failed": 0, "windows_total": 1}
    if bf.classify_conversation_result(clean_zero) is not None:
        v.append("scanned_with_zero WITHOUT parse_failed is a correct result "
                 "(nothing worth extracting), not a failure -- must classify to None")

    genuinely_failed = {"conversation_id": "c2", "parse_failed": True,
                        "scanned_with_zero": True, "windows_parse_failed": 2, "windows_total": 2}
    if bf.classify_conversation_result(genuinely_failed) != "schema_violation_or_refusal":
        v.append("a parse_failed conversation with no context-length evidence should "
                 "fall back to the combined schema_violation_or_refusal bucket")
    if bf.classify_conversation_result(genuinely_failed, token_count=9000,
                                        context_length=8192) != "context_overflow":
        v.append("a parse_failed conversation whose window token_count exceeds the "
                 "candidate's context_length should classify as context_overflow, "
                 "not fall through to the combined bucket")

    # --- record_failure: kind enforcement is the stop condition made
    #     structural, not a convention --------------------------------------
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "fail.jsonl"
        complete = {
            "kind": "timeout", "model_id": "m1", "stage": "K2", "host": "h",
            "config_fingerprint": "cf", "prompt_fingerprint": "pf",
            "position_in_session": 1, "conversation_id": "c1",
        }
        bf.record_failure(complete, p)

        try:
            bf.record_failure({**complete, "kind": "made_up_kind"}, p)
            v.append("record_failure accepted a kind not in FAILURE_KINDS -- this is "
                     "exactly the stop condition ('a failure recorded without its kind') "
                     "it must refuse")
        except ValueError:
            pass

        try:
            bf.record_failure({"kind": "timeout"}, p)
            v.append("record_failure accepted an entry missing required fields")
        except ValueError:
            pass

        entries = bf.load_failures(p)
        if len(entries) != 1:
            v.append(f"exactly the one valid record_failure call should have written a "
                     f"line -- both invalid calls above must have been refused: {entries}")
        elif entries[0].get("kind") != "timeout":
            v.append(f"the recorded entry's kind did not round-trip: {entries[0]}")

        # a second, different-kind failure -- counts_by_kind must not blend
        bf.record_failure({**complete, "kind": "context_overflow", "conversation_id": "c2"}, p)
        # a failure for a DIFFERENT config -- must not contribute to this unit's counts
        bf.record_failure({**complete, "kind": "transport_error",
                            "config_fingerprint": "cf-other"}, p)
        entries = bf.load_failures(p)
        counts = bf.counts_by_kind(entries, model_id="m1", stage="K2",
                                    config_fingerprint="cf", prompt_fingerprint="pf")
        if counts.get("timeout") != 1 or counts.get("context_overflow") != 1:
            v.append(f"counts_by_kind should find exactly 1 timeout and 1 "
                     f"context_overflow for this (model,stage,config,prompt): {counts}")
        if counts.get("transport_error") != 0:
            v.append(f"a failure recorded under a DIFFERENT config_fingerprint must not "
                     f"be counted against this unit: {counts}")
        if set(counts) != set(bf.FAILURE_KINDS):
            v.append(f"counts_by_kind should report every kind in FAILURE_KINDS, even "
                     f"ones seen zero times, so absence reads as 0 not 'unknown key': "
                     f"{sorted(counts)}")

    return v
