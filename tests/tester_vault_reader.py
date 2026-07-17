"""vault_reader: build a tiny frozen-shaped vault in a temp dir and assert the
rollup shape, the schema-version guard, and the account dimension.

Hermetic: patches vault_reader's path resolver so it never depends on this
machine's configured vault (a real vault on the knight would otherwise win)."""
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


def _scan(db: Path) -> dict:
    """Run vault_reader against exactly ``db``, ignoring machine config/env."""
    orig = vault_reader._resolve_vault_path
    vault_reader._resolve_vault_path = lambda: db
    try:
        return vault_reader.scan_estate([])
    finally:
        vault_reader._resolve_vault_path = orig


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "chronicler.db"
        _make_vault(good, user_version=1)
        out = _scan(good)

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
        concept = {p["vault_project"]: p for p in out["vault_projects_without_repo"]}
        if "L5GN Crystal Spire" not in concept:
            v.append("vault_reader: concept project (no repo) not surfaced separately")
        else:
            cp = concept["L5GN Crystal Spire"]
            # A concept row carries NO repo/estate mapping and drops the repo-only
            # confidence + evidence fields (keeps the two project kinds distinct).
            for absent in ("estate", "estate_project", "repo_folder_path",
                           "present_in_estate", "by_confidence", "evidence_signals"):
                if absent in cp:
                    v.append(f"vault_reader: concept project should not carry {absent!r}")

        # evidence_signals are joined by project name onto the REPO project.
        sg = repo.get("smelt-gateway", {})
        if sg.get("evidence_signals") != {"path_mention": 1}:
            v.append(f"vault_reader: evidence_signals not joined onto repo project: {sg.get('evidence_signals')}")
        # confidence histogram carried per repo project (t1 evidence, t2 manual).
        if sg.get("by_confidence") != {"evidence": 1, "manual": 1}:
            v.append(f"vault_reader: by_confidence histogram wrong: {sg.get('by_confidence')}")

        if out["unlinked"]["threads"] != 1:
            v.append(f"vault_reader: unlinked count wrong: {out['unlinked']}")
        # The unlinked bucket is itself account-walled: t3 is claude-personal.
        uba = out["unlinked"]["by_account"]
        if set(uba) != {"claude-personal"} or uba["claude-personal"]["threads"] != 1:
            v.append(f"vault_reader: unlinked bucket not carried per account: {uba}")
        # Unlinked threads never leak into a project rollup's account wall.
        if "claude-personal" in sg.get("by_account", {}):
            v.append("vault_reader: an unlinked account must not appear in a project's by_account")

        # Schema guard: a wrong user_version must refuse, not interpret.
        bad = Path(td) / "bad.db"
        _make_vault(bad, user_version=99)
        out2 = _scan(bad)
        if out2.get("status") != "schema_mismatch":
            v.append(f"vault_reader: expected schema_mismatch on user_version 99, got {out2.get('status')!r}")
        if out2.get("found_user_version") != 99:
            v.append("vault_reader: schema_mismatch should report the found user_version")

        # No vault anywhere -> a clean no_vault status, never a crash.
        orig = vault_reader._resolve_vault_path
        vault_reader._resolve_vault_path = lambda: None
        try:
            nov = vault_reader.scan_estate([])
        finally:
            vault_reader._resolve_vault_path = orig
        if nov.get("status") != "no_vault":
            v.append(f"vault_reader: absent vault should yield no_vault, got {nov.get('status')!r}")
    return v
