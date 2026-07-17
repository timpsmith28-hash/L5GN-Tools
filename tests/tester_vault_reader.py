"""vault_reader: build a tiny frozen-shaped vault in a temp dir and assert the
rollup shape, the schema-version guard, and the account dimension."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from l5gntools.scanners import vault_reader


def _make_vault(path: Path, user_version: int = 1) -> None:
    c = sqlite3.connect(str(path))
    c.executescript(
        "CREATE TABLE projects(project_id TEXT PRIMARY KEY, name TEXT, repo_folder_path TEXT, source_system_id TEXT);"
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, source TEXT, account TEXT, title TEXT,"
        " created_at TEXT, updated_at TEXT, status TEXT, project_link TEXT, project_confidence TEXT,"
        " review_status TEXT, substantive INTEGER);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT, seq INTEGER, role TEXT, content TEXT);"
        "CREATE TABLE link_evidence(evidence_id INTEGER PRIMARY KEY, thread_id TEXT, project TEXT, signal TEXT, weight REAL);"
        "CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);"
    )
    c.execute("INSERT INTO meta VALUES('schema_version','1.0-frozen')")
    c.execute("INSERT INTO projects VALUES('smelt-gateway','smelt-gateway','L5GN/smelt-gateway',NULL)")
    c.execute("INSERT INTO projects VALUES('019f','L5GN Crystal Spire',NULL,'019f')")
    c.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
        ("t1", "gemini", "gemini-personal", "a", "", "2026-07-10", "open", "smelt-gateway", "evidence", "auto", 1),
        ("t2", "gemini", "gemini-work", "b", "", "2026-07-11", "open", "smelt-gateway", "manual", "confirmed", 1),
        ("t3", "claude", "claude-personal", "c", "", "2026-07-12", "open", None, None, "auto", 0),
    ])
    c.executemany("INSERT INTO messages VALUES(?,?,?,?,?)", [
        ("m1", "t1", 0, "user", "hi"), ("m2", "t1", 1, "assistant", "yo"), ("m3", "t3", 0, "user", "x")])
    c.execute("INSERT INTO link_evidence VALUES(1,'t1','smelt-gateway','path_mention',0.9)")
    c.execute(f"PRAGMA user_version = {user_version}")
    c.commit()
    c.close()


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "chronicler.db"
        _make_vault(good, user_version=1)

        # Point the reader at our temp vault via the env-var resolution path.
        import os
        os.environ["CHRONICLER_DB_PATH"] = str(good)
        try:
            out = vault_reader.scan_estate([])
        finally:
            os.environ.pop("CHRONICLER_DB_PATH", None)

        if out.get("status") != "ok":
            return [f"vault_reader: expected status ok, got {out.get('status')!r}"]
        if out["totals"]["threads"] != 3 or out["totals"]["linked_threads"] != 2:
            v.append(f"vault_reader: bad totals {out['totals']}")
        if "gemini-work" not in out["totals"]["by_account"]:
            v.append("vault_reader: account dimension missing from totals")
        repo = {p["vault_project"]: p for p in out["projects"]}
        if "smelt-gateway" not in repo:
            v.append("vault_reader: smelt-gateway repo project not surfaced")
        else:
            sg = repo["smelt-gateway"]
            if sg.get("estate") != "L5GN" or sg.get("estate_project") != "smelt-gateway":
                v.append(f"vault_reader: estate mapping wrong: {sg.get('estate')}/{sg.get('estate_project')}")
            if set(sg["by_account"]) != {"gemini-personal", "gemini-work"}:
                v.append(f"vault_reader: account wall not carried per-project: {sg['by_account']}")
        if not any(p["vault_project"] == "L5GN Crystal Spire" for p in out["vault_projects_without_repo"]):
            v.append("vault_reader: concept project (no repo) not surfaced separately")
        if out["unlinked"]["threads"] != 1:
            v.append(f"vault_reader: unlinked count wrong: {out['unlinked']}")

        # Schema guard: a wrong user_version must refuse, not interpret.
        bad = Path(td) / "bad.db"
        _make_vault(bad, user_version=99)
        os.environ["CHRONICLER_DB_PATH"] = str(bad)
        try:
            out2 = vault_reader.scan_estate([])
        finally:
            os.environ.pop("CHRONICLER_DB_PATH", None)
        if out2.get("status") != "schema_mismatch":
            v.append(f"vault_reader: expected schema_mismatch on user_version 99, got {out2.get('status')!r}")
    return v
