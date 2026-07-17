"""normalize_md_transcript.py -- ingest markdown conversation transcripts.

For sources you can't export via API (e.g. admin-gated work-account Claude), close
the thread out with the close-out prompt (see chronicler/README.md) to have the
model emit a transcript in the convention below, drop the .md into
CHRONICLER_HOME/chat_threads/raw_md_transcripts/, and ingest picks it up here.
It's a best-effort self-report, not a byte-exact export.

Convention:
    ---
    source: claude
    account: claude-work-manual
    title: Some Title
    created_at: 2026-07-17          # optional
    thread_id: <optional; else synthesised from the filename>
    ---
    **User:**
    ...message...

    **Assistant:**
    ...message...

Stdlib-only. Idempotent by thread_id (re-running skips ingested files unless
--force). Ingested files move to raw_md_transcripts/_ingested/.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from db import CHRONICLER_ROOT, get_connection, init_db

RAW_DIR = CHRONICLER_ROOT / "chat_threads" / "raw_md_transcripts"
PARSER_VERSION = "md_transcript_v1"
SUBSTANTIVE_MIN_MESSAGES = 4

_ROLE = {"user": "user", "human": "user", "assistant": "assistant", "claude": "assistant"}
# Matches **User:**, **User**:, **User** and the Human/Claude aliases -- colon
# inside or outside the bold, in any case.
_MARKER = re.compile(r"^\s*\*\*\s*(User|Human|Assistant|Claude)\s*:?\s*\*\*\s*:?\s*$",
                     re.IGNORECASE)


def _parse_frontmatter(lines: list[str]):
    """Return (meta dict, body_start_index). Optional leading '---' … '---' block
    of simple `key: value` lines."""
    meta: dict = {}
    if not lines or lines[0].strip() != "---":
        return meta, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return meta, i + 1
        if ":" in lines[i]:
            key, _, val = lines[i].partition(":")
            meta[key.strip().lower()] = val.strip()
    return {}, 0  # no closing fence -> treat as no frontmatter


def _parse_turns(body_lines: list[str]):
    """Split body into (role, content) turns on **User:** / **Assistant:** markers."""
    turns = []
    role = None
    buf: list[str] = []
    for line in body_lines:
        m = _MARKER.match(line)
        if m:
            if role is not None:
                turns.append((role, "\n".join(buf).strip()))
            role = _ROLE[m.group(1).lower()]
            buf = []
        elif role is not None:
            buf.append(line)
    if role is not None:
        turns.append((role, "\n".join(buf).strip()))
    return [(r, c) for r, c in turns if c]


def _synth_thread_id(path: Path) -> str:
    return "mdmanual-" + hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:12]


def ingest_file(conn, path: Path, force: bool = False) -> dict:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    meta, start = _parse_frontmatter(lines)
    turns = _parse_turns(lines[start:])
    if not turns:
        return {"file": path.name, "status": "empty", "messages": 0}

    tid = meta.get("thread_id") or _synth_thread_id(path)
    cur = conn.cursor()
    exists = cur.execute("SELECT 1 FROM threads WHERE thread_id=?", (tid,)).fetchone()
    if exists and not force:
        return {"file": path.name, "status": "skipped (exists)", "thread_id": tid, "messages": 0}
    if exists:
        cur.execute("DELETE FROM messages WHERE thread_id=?", (tid,))
        cur.execute("DELETE FROM threads WHERE thread_id=?", (tid,))

    source = meta.get("source", "claude")
    account = meta.get("account", "claude-work-manual")
    title = meta.get("title") or path.stem
    created = meta.get("created_at") or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    substantive = 1 if len(turns) >= SUBSTANTIVE_MIN_MESSAGES else 0

    cur.execute(
        "INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,"
        " status, project_link, project_confidence, review_status, raw_ref, parser_version,"
        " substantive) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tid, source, account, title, created, created, "open", None, None, "pending",
         f"raw_md_transcripts/{path.name}", PARSER_VERSION, substantive),
    )
    for seq, (role, content) in enumerate(turns):
        cur.execute(
            "INSERT INTO messages (message_id, thread_id, seq, role, content, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (f"{tid}-{seq}", tid, seq, role, content, created),
        )
    conn.commit()
    return {"file": path.name, "status": "ingested", "thread_id": tid,
            "account": account, "messages": len(turns)}


def run(raw_dir: Path = RAW_DIR, force: bool = False) -> list[dict]:
    if not raw_dir.exists():
        print(f"normalize_md_transcript: no drop dir at {raw_dir}")
        return []
    init_db()
    conn = get_connection()
    archive = raw_dir / "_ingested"
    results = []
    try:
        for path in sorted(raw_dir.glob("*.md")):
            rec = ingest_file(conn, path, force=force)
            results.append(rec)
            if rec["status"] == "ingested":
                archive.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(archive / path.name))
    finally:
        conn.close()
    new = sum(1 for r in results if r["status"] == "ingested")
    msgs = sum(r["messages"] for r in results)
    print(f"normalize_md_transcript: {new} transcript(s) ingested, {msgs} messages "
          f"({len(results)} file(s) seen)")
    return results


def main():
    ap = argparse.ArgumentParser(description="Ingest markdown conversation transcripts.")
    ap.add_argument("--force", action="store_true", help="re-ingest even if the thread exists")
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = ap.parse_args()
    run(args.raw_dir, force=args.force)


if __name__ == "__main__":
    main()
