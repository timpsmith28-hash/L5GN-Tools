"""tester_serve: the Datasette read-surface wiring (Task A / DECISIONS 0007).

Hermetic: checks the argv the `serve` command builds and its config-driven path
resolution. Datasette itself is an optional extra and is NOT required to run this
test -- only the dep-absent skip path and the command shape are asserted.
"""
from __future__ import annotations

import os
from pathlib import Path

from l5gntools import viewer


def run() -> list[str]:
    v: list[str] = []

    # --- argv: read-only, correct bind, port as string ---
    argv = viewer.datasette_argv("/vault/chronicler.db", host="0.0.0.0", port=8001)
    if argv[:2] != ["datasette", "serve"]:
        v.append(f"serve: not a `datasette serve` invocation: {argv}")
    if "--immutable" not in argv:
        v.append("serve: MUST pass --immutable (read-only == single-writer safe)")
    else:
        # --immutable must be followed by the DB path (it takes PATH as its value)
        if argv[argv.index("--immutable") + 1] != "/vault/chronicler.db":
            v.append("serve: --immutable is not followed by the DB path")
    if "-h" not in argv or argv[argv.index("-h") + 1] != "0.0.0.0":
        v.append("serve: must bind 0.0.0.0 for tailnet + LAN reach (0007)")
    if "-p" not in argv or argv[argv.index("-p") + 1] != "8001":
        v.append("serve: port not passed as a string arg")
    # the DB must never be opened mutable (no bare positional DB alongside -i)
    if str("/vault/chronicler.db") != argv[argv.index("--immutable") + 1] or \
            argv.count("/vault/chronicler.db") != 1:
        v.append("serve: DB should appear exactly once, as the --immutable value")

    # --- dep-absent detection returns a bool (skip-cleanly signal) ---
    if not isinstance(viewer.datasette_available(), bool):
        v.append("serve: datasette_available() must return a bool")

    # --- config-driven DB path (never hardcoded) ---
    saved = {k: os.environ.pop(k, None) for k in ("CHRONICLER_HOME", "CHRONICLER_DB_PATH")}
    try:
        m = {"vault": "/home/l5gn/vault/chronicler.db"}
        if viewer.resolve_db_path(m) != Path("/home/l5gn/vault/chronicler.db"):
            v.append("serve: resolve_db_path did not honour machine 'vault'")
        m2 = {"chronicler_home": "/data/vault"}
        if viewer.resolve_db_path(m2) != Path("/data/vault/chronicler.db"):
            v.append("serve: resolve_db_path did not derive DB from chronicler_home")
    finally:
        for k, val in saved.items():
            if val is not None:
                os.environ[k] = val

    return v
