"""tester_registry_path: one config-driven registry path (relink_scoring brief F).

Hermetic: exercises db.resolve_registry_path's resolution order and asserts the
pipeline consumers all resolve THROUGH it (no surviving local literal). No DB, no
network.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import db

    saved = os.environ.get("CHRONICLER_REGISTRY_PATH")
    try:
        # 1. explicit env override wins verbatim (the knight knob).
        os.environ["CHRONICLER_REGISTRY_PATH"] = "/tmp/some/where/registry.json"
        got = db.resolve_registry_path()
        if got != Path("/tmp/some/where/registry.json"):
            v.append(f"F: env override not honoured, got {got}")

        # 2. no silent fallback: a set-but-unusual env is returned, not swapped
        #    for the derived literal.
        os.environ["CHRONICLER_REGISTRY_PATH"] = "/nonexistent/registry.json"
        got = db.resolve_registry_path()
        if got != Path("/nonexistent/registry.json"):
            v.append("F: resolver silently fell back instead of honouring the env path")

        # 3. unset -> deterministic per-host derived location, computed one place.
        del os.environ["CHRONICLER_REGISTRY_PATH"]
        got = db.resolve_registry_path()
        expected = db.CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"
        if got != expected:
            v.append(f"F: derived path wrong, got {got} expected {expected}")
    finally:
        if saved is None:
            os.environ.pop("CHRONICLER_REGISTRY_PATH", None)
        else:
            os.environ["CHRONICLER_REGISTRY_PATH"] = saved

    # 4. the consumers resolve through the one function -- no local literal left.
    import relink
    import xref_filenames
    ref = db.resolve_registry_path()
    if relink.REGISTRY_PATH != ref:
        v.append(f"F: relink.REGISTRY_PATH ({relink.REGISTRY_PATH}) != resolver ({ref})")
    if xref_filenames.REGISTRY_PATH != ref:
        v.append(f"F: xref_filenames.REGISTRY_PATH ({xref_filenames.REGISTRY_PATH}) != resolver ({ref})")

    return v
