"""tester_relink_stage: relink is folded into the pipeline correctly (Task B).

Hermetic: imports the vendored run_pipeline / relink modules and asserts the
STAGES wiring, the --skip-relink flag, and the registry input-gate in BOTH
states (present -> stage runs; absent -> stage skips cleanly). No DB, no network.
"""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import relink
    import run_pipeline as rp

    keys = [s[0] for s in rp.STAGES]
    if "relink" not in keys:
        return v + ["relink_stage: 'relink' not registered in STAGES"]

    # --- position: after set_substantive, before render ---
    if not (keys.index("substantive") < keys.index("relink") < keys.index("render")):
        v.append(f"relink_stage: relink mis-ordered in STAGES: {keys}")

    stage = next(s for s in rp.STAGES if s[0] == "relink")
    key, label, script, argv, input_check, summarizer = stage
    if script != "relink.py":
        v.append(f"relink_stage: wrong script {script!r}")
    if "--apply" not in argv:
        v.append("relink_stage: stage must run relink with --apply (else it no-ops)")
    if input_check is not rp.has_registry:
        v.append("relink_stage: stage is not gated on has_registry")

    # Every stage carries a summariser slot; None means "read ingestion_log".
    # relink writes no ingestion_log rows, so None there is the defect, not a
    # default -- it made the runner print "no new rows" after every run.
    if summarizer is None:
        v.append("relink_stage: relink must carry its own summariser -- it writes "
                 "no ingestion_log rows, so a log-summarised relink reports "
                 "'no new rows' whatever it did")
    if len(stage) != 6:
        v.append(f"relink_stage: STAGES rows should be 6-tuples, got {len(stage)}")

    # --- registry gate: present -> True, absent -> False (skip cleanly) ---
    orig = relink.REGISTRY_PATH
    try:
        with tempfile.TemporaryDirectory() as td:
            present = Path(td) / "project_registry.json"
            present.write_text("{}", encoding="utf-8")
            relink.REGISTRY_PATH = present
            if not rp.has_registry():
                v.append("relink_stage: has_registry() False when registry present")
            relink.REGISTRY_PATH = Path(td) / "missing.json"
            if rp.has_registry():
                v.append("relink_stage: has_registry() True when registry absent")
    finally:
        relink.REGISTRY_PATH = orig

    # --- --skip-relink drops the stage from the active set ---
    def _args(**over):
        base = {f"skip_{k.replace('-', '_')}": False for k in keys}
        base["render_only"] = False
        base.update(over)
        return types.SimpleNamespace(**base)

    if "relink" not in rp.resolve_active_keys(_args()):
        v.append("relink_stage: relink missing from a default run")
    if "relink" in rp.resolve_active_keys(_args(skip_relink=True)):
        v.append("relink_stage: --skip-relink did not drop the stage")

    # --- the skip is LOUD, and the run is degraded -------------------------
    # What this file asserted until 2026-08-31 was that the gate returned False
    # and the stage was dropped -- "skips cleanly", in its own words. It never
    # asserted that anyone would KNOW. The gate's boolean was correct the whole
    # time; the reporting was the defect, and a tester that checks only the
    # boolean will pass over it forever.
    if "relink" not in rp.CONFIG_GATED:
        v.append("relink_stage: relink must be CONFIG_GATED -- a missing registry "
                 "is a configuration fault, not an absent source, and the two "
                 "printed the same line while the chain finished green")

    note = rp.skip_note("relink")
    if not note:
        v.append("relink_stage: a config-gated skip must produce a note")
    else:
        # The note has to carry three things or it is decoration: the path
        # looked at, that nothing linked, and that no coverage figure from this
        # run means anything. The third is the one two rounds nearly got wrong.
        if str(relink.REGISTRY_PATH) not in note:
            v.append("relink_stage: the skip note must name the path it looked "
                     "for, or the reader cannot act on it")
        if "coverage" not in note.lower():
            v.append("relink_stage: the skip note must warn that no coverage "
                     "figure from this run measures linking -- that is the "
                     "mistake the loudness exists to prevent")
        if "--skip-relink" not in note:
            v.append("relink_stage: the skip note must name the deliberate "
                     "opt-out, or the only way to silence it is to stop reading")

    # --- the summariser reports relink's own units, and NEVER a soothing default
    if summarizer("Applied. 7 thread(s) changed / queued.") is None:
        v.append("relink_stage: summariser failed to read relink's own apply line")
    if "7" not in (summarizer("Applied. 7 thread(s) changed / queued.") or ""):
        v.append("relink_stage: summariser dropped the count")
    zero = summarizer("Applied. 0 thread(s) changed / queued.") or ""
    if not zero or "0" not in zero:
        v.append("relink_stage: a genuine zero must be reported as a zero, not "
                 "as an unreported outcome -- they are different facts")
    # Unrecognised output must return None so the runner says UNREPORTED. A
    # summariser that invents a reassuring answer is the original bug wearing
    # a different hat.
    if summarizer("relink fell over in some novel way") is not None:
        v.append("relink_stage: unrecognised output must summarise to None so "
                 "the runner reports the outcome as unknown, never as empty")
    # A dry run from a stage wired with --apply linked nothing, which is the
    # same OUTCOME as the stage not running at all. So it must degrade the run,
    # not merely narrate itself: the summariser returns (text, ok=False).
    dry = summarizer("[DRY RUN] Nothing written. Re-run with --apply to commit.")
    if not isinstance(dry, tuple):
        v.append(f"relink_stage: a dry run from a stage wired with --apply must "
                 f"degrade the run, not just describe itself -- expected "
                 f"(text, ok) got {type(dry).__name__}")
    else:
        dry_text, dry_ok = dry
        if dry_ok:
            v.append("relink_stage: a dry run wired with --apply must not be ok")
        if "DRY RUN" not in dry_text:
            v.append("relink_stage: the dry-run diagnosis must name what it saw")

    # A normal apply must NOT degrade -- the tuple form is for genuine faults,
    # and a guard that fires on the happy path is 0048 clause 4 from the other
    # direction: a check that always fires teaches the eye past it too.
    if isinstance(summarizer("Applied. 3 thread(s) changed / queued."), tuple):
        v.append("relink_stage: a successful apply must not degrade the run")

    return v
