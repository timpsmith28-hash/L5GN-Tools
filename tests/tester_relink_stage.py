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
    key, label, script, argv, input_check = stage
    if script != "relink.py":
        v.append(f"relink_stage: wrong script {script!r}")
    if "--apply" not in argv:
        v.append("relink_stage: stage must run relink with --apply (else it no-ops)")
    if input_check is not rp.has_registry:
        v.append("relink_stage: stage is not gated on has_registry")

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

    return v
