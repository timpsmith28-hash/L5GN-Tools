"""tester_finalize_db: schema_frozen.sql target resolution (solo_playbook round,
sharp edge 8 -- found live 2026-07-27: `finalize_db.py --apply` against a
throwaway dev CHRONICLER_HOME silently overwrote the repo's TRACKED
schema_frozen.sql with the dev vault's shape, caught only by `git status`
before commit).

Hermetic: exercises finalize_db.frozen_schema_target's routing directly. No
DB, no network, no filesystem writes.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import finalize_db as fdb

    saved_root = fdb.CHRONICLER_ROOT
    try:
        # 1. CHRONICLER_HOME unset -> CHRONICLER_ROOT defaults to the repo-relative
        #    location -> safe to write the tracked repo copy.
        fdb.CHRONICLER_ROOT = fdb.PIPELINE_DIR.parent
        target, is_repo = fdb.frozen_schema_target()
        if not is_repo or target != fdb.FROZEN_SQL_PATH:
            v.append(f"F: default CHRONICLER_ROOT should target the repo's tracked "
                     f"file, got {target} is_repo={is_repo}")

        # 2. any non-default CHRONICLER_HOME (dev throwaway OR a real deploy target)
        #    must NEVER silently touch the repo's tracked file.
        dev_root = Path("/tmp/some/throwaway/chronicler_dev")
        fdb.CHRONICLER_ROOT = dev_root
        target, is_repo = fdb.frozen_schema_target()
        if is_repo or target == fdb.FROZEN_SQL_PATH:
            v.append(f"F: non-default CHRONICLER_ROOT silently targeted the repo's "
                     f"tracked file: {target}")
        if target != dev_root / "schema_frozen.sql":
            v.append(f"F: non-default CHRONICLER_ROOT should dump next to its own "
                     f"vault, got {target}")

        # 3. --freeze-repo-schema is the explicit, deliberate override.
        target, is_repo = fdb.frozen_schema_target(force_repo=True)
        if not is_repo or target != fdb.FROZEN_SQL_PATH:
            v.append(f"F: --freeze-repo-schema override did not force the repo "
                     f"target, got {target} is_repo={is_repo}")
    finally:
        fdb.CHRONICLER_ROOT = saved_root

    return v
