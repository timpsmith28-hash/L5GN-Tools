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

    # 5. The SECOND resolver, and the invariant that was only ever a comment.
    #
    # `chronicler/review/core.py` carries its own resolve_registry_path because
    # that module is deliberately independent of `pipeline.db` -- an invariant
    # its own docstring states ("the same way this module stays independent of
    # pipeline.db"). So the duplication is a design decision, not an oversight,
    # and merging the two would break a property something else relies on.
    #
    # What was NOT written down anywhere executable is that the two must derive
    # the SAME location. core.py says "Mirror relink.REGISTRY_PATH" in a code
    # comment (line ~266) and computes the formula a second time by hand. A
    # comment is not a mechanism: change db's formula and core drifts silently,
    # after which the review endpoint validates ids against a different registry
    # than the pipeline linked with, and nothing anywhere reports which was used.
    #
    # This asserts the agreement the comment has been standing in for. It does
    # not couple the modules -- tests/ may import both tiers (auditor_dependency
    # _direction's APP_TIER includes `tests`, and forbids only l5gntools/ from
    # reaching upward), so the check lives here rather than in either module.
    #
    # NOT asserted: that the two return the same path outright. They legitimately
    # differ when the derived location is absent, because core has a third step
    # (the repo authoring copy) that db deliberately refuses to have. That
    # divergence is real, live on LucasGoonPC as of 2026-08-31, and recorded as
    # a seed instance for the conformance round rather than papered over here --
    # the file core falls back to is `config/project_registry.json`, which 0055
    # rules is corpus rather than config and whose migration is undone.
    from chronicler.review import core as _review_core

    saved_env = os.environ.get("CHRONICLER_REGISTRY_PATH")
    try:
        # a. Both honour the explicit knob identically.
        os.environ["CHRONICLER_REGISTRY_PATH"] = "/tmp/agreed/registry.json"
        if db.resolve_registry_path() != _review_core.resolve_registry_path():
            v.append(f"F: the two resolvers disagree under an explicit "
                     f"CHRONICLER_REGISTRY_PATH -- db="
                     f"{db.resolve_registry_path()} core="
                     f"{_review_core.resolve_registry_path()}")

        # b. The derived formulas agree. Compared as formulas, not as answers:
        #    core only RETURNS its derived path when the file exists, so this
        #    reads the location it would compute rather than the branch it took.
        del os.environ["CHRONICLER_REGISTRY_PATH"]
        db_derived = db.CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"
        core_derived = (_review_core._PIPELINE_DIR.parent.parent.parent
                        / "L5GN" / ".intel_sync" / "project_registry.json")
        if db_derived != core_derived:
            v.append(f"F: the two registry derivations have drifted apart. "
                     f"db={db_derived} core={core_derived}. They are duplicated "
                     f"by hand because review/core.py is deliberately "
                     f"independent of pipeline.db; that independence is fine, "
                     f"the silent drift is not -- fix the formula, or rule that "
                     f"they may differ and say what depends on which.")
    finally:
        if saved_env is None:
            os.environ.pop("CHRONICLER_REGISTRY_PATH", None)
        else:
            os.environ["CHRONICLER_REGISTRY_PATH"] = saved_env

    return v
