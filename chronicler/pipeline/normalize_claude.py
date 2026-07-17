"""
Claude normalizer — build spec item 2.

Reads raw_claude_files/conversations.json + raw_claude_files/projects/*.json
and writes threads / messages / attachments / projects into chronicler.db.

Project-linking: exact title match (conv.name == project.name), else
prompt_template substring match against the first human message of the
thread. Anything else -> project_link=None, project_confidence='none'.

Usage:
    python3 pipeline/normalize_claude.py
"""
import hashlib
import json
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT

PARSER_VERSION = "claude_v1"
RAW_DIR = CHRONICLER_ROOT / "chat_threads" / "raw_claude_files"
CONVERSATIONS_PATH = RAW_DIR / "conversations.json"
PROJECTS_DIR = RAW_DIR / "projects"

# Only one Claude account confirmed so far (users.json has a single entry).
# Section 9.5: account is a free-form string, revisit if/when a second
# Claude account shows up.
ACCOUNT_LABEL = "claude-personal"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def message_text(msg: dict) -> str:
    if msg.get("text"):
        return msg["text"]
    parts = []
    for block in msg.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
            parts.append(block["text"])
    return "\n".join(parts)


def load_projects() -> list:
    projects = []
    if not PROJECTS_DIR.exists():
        return projects
    for p in sorted(PROJECTS_DIR.glob("*.json")):
        with open(p, "r", encoding="utf-8") as f:
            projects.append(json.load(f))
    return projects


def link_project(conv: dict, first_human_text: str, projects: list):
    """Returns (project_id, confidence) or (None, 'none')."""
    name = (conv.get("name") or "").strip()
    for proj in projects:
        if name and proj.get("name") and name == proj["name"].strip():
            return proj["uuid"], "exact"
    for proj in projects:
        template = (proj.get("prompt_template") or "").strip()
        if template and first_human_text and template in first_human_text:
            return proj["uuid"], "exact"
    return None, "none"


def run():
    if not CONVERSATIONS_PATH.exists():
        raise SystemExit(f"Not found: {CONVERSATIONS_PATH}")

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    projects = load_projects()
    rows_new_projects = 0
    for proj in projects:
        cur.execute(
            """INSERT INTO projects (project_id, name, repo_folder_path, source_system_id)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(project_id) DO UPDATE SET
                 name=excluded.name, source_system_id=excluded.source_system_id""",
            (proj["uuid"], proj.get("name"), None, proj["uuid"]),
        )
        rows_new_projects += cur.rowcount

    with open(CONVERSATIONS_PATH, "r", encoding="utf-8") as f:
        conversations = json.load(f)

    rows_new_threads = 0
    rows_new_messages = 0
    rows_new_attachments = 0

    for conv in conversations:
        thread_id = conv["uuid"]
        messages = sorted(
            conv.get("chat_messages", []),
            key=lambda m: m.get("created_at") or "",
        )

        first_human_text = ""
        for m in messages:
            if m.get("sender") == "human":
                first_human_text = message_text(m)
                break

        project_id, confidence = link_project(conv, first_human_text, projects)

        cur.execute(
            """INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,
                                     status, project_link, project_confidence, review_status,
                                     raw_ref, parser_version)
               VALUES (?, 'claude', ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
               ON CONFLICT(thread_id) DO UPDATE SET
                 title=excluded.title, updated_at=excluded.updated_at,
                 project_link=excluded.project_link, project_confidence=excluded.project_confidence,
                 review_status=excluded.review_status""",
            (
                thread_id,
                ACCOUNT_LABEL,
                conv.get("name"),
                conv.get("created_at"),
                conv.get("updated_at"),
                project_id,
                confidence,
                "auto" if project_id else "pending",
                str(CONVERSATIONS_PATH.relative_to(CHRONICLER_ROOT)),
                PARSER_VERSION,
            ),
        )
        rows_new_threads += 1

        for seq, msg in enumerate(messages):
            message_id = msg["uuid"]
            role = "user" if msg.get("sender") == "human" else "assistant"
            cur.execute(
                """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                   VALUES (?, ?, ?, ?, ?, ?, NULL)
                   ON CONFLICT(message_id) DO UPDATE SET
                     content=excluded.content, seq=excluded.seq""",
                (message_id, thread_id, seq, role, message_text(msg), msg.get("created_at")),
            )
            rows_new_messages += 1

            for att in msg.get("attachments") or []:
                attachment_id = hashlib.sha256(
                    f"{message_id}:{att.get('file_name')}:{att.get('file_size')}".encode("utf-8")
                ).hexdigest()[:32]
                cur.execute(
                    """INSERT INTO attachments (attachment_id, message_id, filename, turn_hash,
                                                 file_path, mime, extracted_content)
                       VALUES (?, ?, ?, NULL, NULL, ?, ?)
                       ON CONFLICT(attachment_id) DO UPDATE SET
                         extracted_content=excluded.extracted_content""",
                    (
                        attachment_id,
                        message_id,
                        att.get("file_name"),
                        att.get("file_type") or None,
                        att.get("extracted_content"),
                    ),
                )
                rows_new_attachments += 1

            for fobj in msg.get("files") or []:
                cur.execute(
                    """INSERT INTO attachments (attachment_id, message_id, filename, turn_hash,
                                                 file_path, mime, extracted_content)
                       VALUES (?, ?, ?, NULL, NULL, NULL, NULL)
                       ON CONFLICT(attachment_id) DO NOTHING""",
                    (fobj["file_uuid"], message_id, fobj.get("file_name")),
                )
                rows_new_attachments += 1

    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('claude', ?, ?, datetime('now'), ?, 0, 0, ?)""",
        (ACCOUNT_LABEL, file_hash(CONVERSATIONS_PATH), rows_new_threads, PARSER_VERSION),
    )

    conn.commit()

    linked = cur.execute(
        "SELECT COUNT(*) FROM threads WHERE source='claude' AND project_link IS NOT NULL"
    ).fetchone()[0]
    total_threads = cur.execute("SELECT COUNT(*) FROM threads WHERE source='claude'").fetchone()[0]
    total_messages = cur.execute(
        "SELECT COUNT(*) FROM messages m JOIN threads t ON m.thread_id=t.thread_id WHERE t.source='claude'"
    ).fetchone()[0]
    total_attachments = cur.execute(
        """SELECT COUNT(*) FROM attachments a
           JOIN messages m ON a.message_id=m.message_id
           JOIN threads t ON m.thread_id=t.thread_id WHERE t.source='claude'"""
    ).fetchone()[0]

    conn.close()

    print(f"Projects loaded:        {rows_new_projects}")
    print(f"Threads written:        {total_threads}")
    print(f"  ...project-linked:    {linked}")
    print(f"Messages written:       {total_messages}")
    print(f"Attachments written:    {total_attachments}")


if __name__ == "__main__":
    run()
