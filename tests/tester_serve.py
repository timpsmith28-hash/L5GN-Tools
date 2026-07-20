"""tester_serve: the Datasette read-surface wiring (DECISIONS 0007 + 0013).

Hermetic: checks the argv the `serve` command builds, its config-driven path
resolution, and -- since 0013 -- that what it serves is a *snapshot* rather than
the live vault. Datasette itself is an optional extra and is NOT required to run
this test; only the dep-absent skip path, the command shape, and the snapshot
mechanics are asserted.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
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

    v.extend(_check_snapshot())
    return v


def _check_snapshot() -> list[str]:
    """DECISIONS 0013: serve must target a frozen copy, never the live vault.

    Builds a real little vault in a temp dir, takes the serving snapshot the way
    `run.py serve` does, and asserts the properties that make the false-malformed
    class impossible: the snapshot is a distinct file, it carries the data, it is
    NOT in the backup rotation, it is overwritten rather than accumulated, and the
    staleness note names the snapshot time.
    """
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        home = Path(td)
        db = home / "chronicler.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE threads (id TEXT PRIMARY KEY, project_link TEXT);")
        conn.execute("INSERT INTO threads VALUES ('t1', 'crystal-spire');")
        conn.commit()
        conn.close()

        m = {"chronicler_home": str(home), "vault": str(db)}
        saved = {k: os.environ.pop(k, None)
                 for k in ("CHRONICLER_HOME", "CHRONICLER_DB_PATH")}
        try:
            snap = viewer.make_serve_snapshot(m)
            snap_path = Path(snap["snapshot"])

            if not snap_path.exists():
                v.append("serve: make_serve_snapshot did not produce a file")
                return v
            if snap_path == db:
                v.append("serve: the snapshot IS the live DB -- 0013 requires a copy")

            # the snapshot must carry the data (it is a real VACUUM INTO, not a stub)
            c = sqlite3.connect(f"file:{snap_path.as_posix()}?mode=ro", uri=True)
            try:
                rows = c.execute("SELECT COUNT(*) FROM threads;").fetchone()[0]
            finally:
                c.close()
            if rows != 1:
                v.append(f"serve: snapshot holds {rows} thread row(s), expected the "
                         "live vault's one -- the copy is not faithful")

            # it must NOT land in the backup rotation (0013: don't pollute backups)
            from l5gntools import backup
            backup_dir = backup.resolve_backup_dir(m)
            if snap_path.parent == backup_dir:
                v.append("serve: the serving snapshot was written into the backup "
                         "directory -- it would age a real off-box generation out of "
                         "keep-last-N")
            if backup.list_snapshots(backup_dir):
                v.append("serve: taking a serving snapshot created backup-rotation "
                         "snapshots -- the two must stay separate")

            # relaunch overwrites rather than accumulating
            again = viewer.make_serve_snapshot(m)
            if Path(again["snapshot"]) != snap_path:
                v.append("serve: a second launch wrote a new snapshot filename -- the "
                         "serving copy is scratch and must be overwritten in place")
            leftovers = list(snap_path.parent.glob("*.db"))
            if len(leftovers) != 1:
                v.append(f"serve: {len(leftovers)} snapshot files accumulated in the "
                         "serve-snapshot dir, expected exactly one")

            # the staleness surface: note names the time, metadata carries the note
            note = viewer.staleness_note(again["taken_at"])
            if again["taken_at"] not in note:
                v.append("serve: staleness note does not state the snapshot time")
            meta_path = viewer.write_metadata(again["dir"], again["taken_at"])
            meta_text = Path(meta_path).read_text(encoding="utf-8")
            if again["taken_at"] not in meta_text:
                v.append("serve: Datasette metadata does not carry the snapshot time, "
                         "so the UI banner cannot state it")

            # and the argv must point --immutable at the snapshot, not the vault
            argv = viewer.datasette_argv(snap_path, metadata=meta_path)
            if argv[argv.index("--immutable") + 1] != str(snap_path):
                v.append("serve: --immutable is not pointed at the snapshot")
            if str(db) in argv:
                v.append("serve: the live vault path appears in the Datasette argv -- "
                         "serve must never open the live file (0013)")
            if "--metadata" not in argv:
                v.append("serve: metadata (the staleness banner) not passed to Datasette")
        finally:
            for k, val in saved.items():
                if val is not None:
                    os.environ[k] = val
    return v
