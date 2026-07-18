"""tester_backup: the off-box VACUUM INTO snapshot engine (Task C).

Hermetic: builds a throwaway sqlite vault in a temp dir and exercises the pure
backup helpers -- no live vault, no network. Neutralises CHRONICLER_* env vars
for the duration so path resolution is driven only by the supplied machine dict.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from l5gntools import backup


def _make_vault(path: Path, rows: int = 25) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE threads(thread_id TEXT PRIMARY KEY, title TEXT)")
    conn.executemany("INSERT INTO threads VALUES(?, ?)",
                     [(f"t{i}", f"title {i}") for i in range(rows)])
    conn.commit()
    conn.close()


def run() -> list[str]:
    v: list[str] = []
    saved = {k: os.environ.pop(k, None) for k in ("CHRONICLER_HOME", "CHRONICLER_DB_PATH")}
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            home = td / "vault"
            home.mkdir()
            src = home / "chronicler.db"
            _make_vault(src, rows=25)
            machine = {"vault": str(src), "chronicler_home": str(home)}

            # --- vacuum_into: produces a valid, openable, complete copy ---
            dest = td / "snap.db"
            backup.vacuum_into(src, dest)
            if not dest.exists():
                v.append("backup: vacuum_into produced no file")
            else:
                # close the handle before temp cleanup, else Windows WinError 32
                c = sqlite3.connect(str(dest))
                try:
                    n = c.execute("SELECT count(*) FROM threads").fetchone()[0]
                finally:
                    c.close()
                if n != 25:
                    v.append(f"backup: snapshot row count wrong ({n} != 25)")
            # source must be untouched (opened mode=ro)
            if not src.exists():
                v.append("backup: source DB vanished after snapshot")

            # refuses an existing target (VACUUM INTO can't overwrite)
            try:
                backup.vacuum_into(src, dest)
                v.append("backup: vacuum_into should refuse an existing target")
            except FileExistsError:
                pass
            # refuses a missing source, loudly
            try:
                backup.vacuum_into(td / "nope.db", td / "x.db")
                v.append("backup: vacuum_into should refuse a missing source")
            except FileNotFoundError:
                pass

            # --- snapshot_name: dated + lexically sortable == chronological ---
            n1 = backup.snapshot_name(datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
            n2 = backup.snapshot_name(datetime(2026, 1, 2, 3, 4, 6, tzinfo=timezone.utc))
            if n1 != "chronicler-20260102T030405Z.db":
                v.append(f"backup: snapshot_name format wrong: {n1}")
            if not (n1 < n2):
                v.append("backup: snapshot names not chronologically sortable")

            # --- prune_snapshots: keep-last-N, never below 1 ---
            bdir = td / "backups"
            bdir.mkdir()
            names = [f"chronicler-2026010{i}T000000Z.db" for i in range(1, 8)]  # 7 dated
            for nm in names:
                (bdir / nm).write_bytes(b"x")
            doomed = backup.prune_snapshots(bdir, keep=3)
            kept = [p.name for p in backup.list_snapshots(bdir)]
            if kept != names[-3:]:
                v.append(f"backup: prune kept wrong set: {kept}")
            if [p.name for p in doomed] != names[:4]:
                v.append(f"backup: prune deleted wrong set: {[p.name for p in doomed]}")
            # keep floored at 1
            backup.prune_snapshots(bdir, keep=0)
            if len(backup.list_snapshots(bdir)) != 1:
                v.append("backup: keep=0 should floor to 1, not wipe all snapshots")

            # --- path resolution: never hardcoded ---
            if backup.resolve_db_path(machine) != Path(str(src)):
                v.append("backup: resolve_db_path did not honour machine 'vault'")
            if backup.resolve_backup_dir(machine) != home / "backups":
                v.append("backup: resolve_backup_dir not under CHRONICLER_HOME")
            os.environ["CHRONICLER_DB_PATH"] = str(td / "envdb.db")
            if backup.resolve_db_path(machine) != td / "envdb.db":
                v.append("backup: CHRONICLER_DB_PATH env should win over machine 'vault'")
            del os.environ["CHRONICLER_DB_PATH"]

            # --- push_command shapes ---
            scp = backup.push_command(dest, "l5gn-castle:vault/Chronicler_Backup", "scp")
            if scp[0] != "scp" or not scp[-1].endswith("Chronicler_Backup/"):
                v.append(f"backup: scp push_command wrong: {scp}")
            rs = backup.push_command(dest, "host:dir/", "rsync")
            if rs[0] != "rsync" or "-az" not in rs:
                v.append(f"backup: rsync push_command wrong: {rs}")

            # --- make_backup end to end: no target -> local only, push skipped ---
            home2 = td / "vault2"
            home2.mkdir()
            src2 = home2 / "chronicler.db"
            _make_vault(src2, rows=3)
            m2 = {"vault": str(src2), "chronicler_home": str(home2)}
            r = backup.make_backup(machine=m2, push=True)  # no backup_target set
            if not Path(r["snapshot"]).exists():
                v.append("backup: make_backup did not create a snapshot")
            if r["backup_target"] is not None or r["pushed"]:
                v.append("backup: make_backup should not push without a backup_target")
            if len(r["kept"]) != 1:
                v.append(f"backup: make_backup 'kept' wrong: {r['kept']}")

            # target set but push staged (push=False) -> command built, not run
            m3 = dict(m2, backup_target="l5gn-castle:vault/Chronicler_Backup",
                      backup_transport="scp")
            r3 = backup.make_backup(machine=m3, push=False)
            if not r3["push_command"] or r3["pushed"] or r3["push_error"]:
                v.append(f"backup: staged push wrong: {r3}")
    finally:
        for k, val in saved.items():
            if val is not None:
                os.environ[k] = val
    return v
