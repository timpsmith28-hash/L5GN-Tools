"""
Gemini-personal normalizer — build spec item 3.

Reads Google Takeout's My Activity.json (Gemini Apps) and writes messages
(thread_id left NULL — unresolved, pending the reconciliation join in item 5)
plus attachments into chronicler.db.

Confirmed schema (surveyed this session, 3507 records):
  Each record = one turn-pair.
    title           -> user prompt, always prefixed "Prompted " for real chat turns
    safeHtmlItem[0]["html"] -> assistant response (HTML), if present
    time            -> ISO8601 UTC, e.g. 2026-07-11T17:30:26.464Z
    attachedFiles / imageFile / subtitles[].url -> attachment filenames,
        each ending in a 16-hex-char hash suffix shared across a turn
        (e.g. "tui-c1db7ec5fc7d115e.py", "image_eb8878-a2d19aa6df2337cc.png")
  Non-"Prompted" titles ("Created ...", "Used ...", "Gave feedback...") are
  activity-log entries, not real turns -> stored as role='activity_log'.

Takeout drop convention (confirmed with Tim 2026-07-15): ongoing Google
Takeout exports live permanently at
  chat_threads/raw_gemini_files/Takeout/My Activity/Gemini Apps/My Activity.json
DEFAULT_INPUT below points there. (This replaced the earlier one-off
"raw_gemini_files_test_refresh" test folder.) For a one-off run against a
different drop, pass --input on the CLI rather than editing this script.

Usage:
    python3 pipeline/normalize_gemini_personal.py [--input PATH_TO_My_Activity.json]
"""
import argparse
import hashlib
import html
import json
import re
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT

PARSER_VERSION = "gemini_personal_v1"
ACCOUNT_LABEL = "gemini-personal"

DEFAULT_INPUT = (
    CHRONICLER_ROOT
    / "chat_threads"
    / "raw_gemini_files"
    / "Takeout"
    / "My Activity"
    / "Gemini Apps"
    / "My Activity.json"
)

HASH_RE = re.compile(r"-([0-9a-f]{16})\.[A-Za-z0-9]+$")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def html_to_text(raw_html: str) -> str:
    text = raw_html
    text = re.sub(r"<pre>\s*<code[^>]*>", "\n```\n", text)
    text = re.sub(r"</code>\s*</pre>", "\n```\n", text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def extract_hash(filenames) -> str | None:
    for name in filenames or []:
        m = HASH_RE.search(name)
        if m:
            return m.group(1)
    return None


def synth_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]


def run(input_path: Path):
    if not input_path.exists():
        raise SystemExit(f"Not found: {input_path}")

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    with open(input_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    rows_messages = 0
    rows_attachments = 0
    rows_skipped = 0

    for record in records:
        title = record.get("title") or ""
        time_ = record.get("time")
        attach_names = list(record.get("attachedFiles") or [])
        if record.get("imageFile") and record["imageFile"] not in attach_names:
            attach_names.append(record["imageFile"])
        turn_hash = extract_hash(attach_names)

        if not title.startswith(("Prompted ", "Created ", "Used ", "Gave ")):
            rows_skipped += 1
            continue

        if title.startswith("Prompted "):
            user_text = title[len("Prompted "):]
            user_msg_id = synth_id("gemini-personal", time_, "user", title[:80])
            cur.execute(
                """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                   VALUES (?, NULL, NULL, 'user', ?, ?, ?)
                   ON CONFLICT(message_id) DO UPDATE SET content=excluded.content""",
                (user_msg_id, user_text, time_, turn_hash),
            )
            rows_messages += 1

            html_items = record.get("safeHtmlItem") or []
            if html_items and html_items[0].get("html"):
                assistant_text = html_to_text(html_items[0]["html"])
                assistant_msg_id = synth_id("gemini-personal", time_, "assistant", title[:80])
                cur.execute(
                    """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                       VALUES (?, NULL, NULL, 'assistant', ?, ?, ?)
                       ON CONFLICT(message_id) DO UPDATE SET content=excluded.content""",
                    (assistant_msg_id, assistant_text, time_, turn_hash),
                )
                rows_messages += 1

            for name in attach_names:
                attachment_id = synth_id("gemini-personal-attachment", name)
                # Reconstruct a readable filename: strip the "-<16hex>" before the extension,
                # e.g. "tui-c1db7ec5fc7d115e.py" -> "tui.py".
                clean_filename = re.sub(r"-[0-9a-f]{16}(\.[A-Za-z0-9]+)$", r"\1", name)
                cur.execute(
                    """INSERT INTO attachments (attachment_id, message_id, filename, turn_hash, file_path, mime, extracted_content)
                       VALUES (?, ?, ?, ?, ?, NULL, NULL)
                       ON CONFLICT(attachment_id) DO NOTHING""",
                    (attachment_id, user_msg_id, clean_filename, turn_hash, name),
                )
                rows_attachments += 1
        else:
            # Created / Used / Gave — activity-log entries, no response, kept for completeness.
            msg_id = synth_id("gemini-personal", time_, "log", title[:80])
            cur.execute(
                """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                   VALUES (?, NULL, NULL, 'activity_log', ?, ?, ?)
                   ON CONFLICT(message_id) DO UPDATE SET content=excluded.content""",
                (msg_id, title, time_, turn_hash),
            )
            rows_messages += 1

    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('gemini', ?, ?, datetime('now'), ?, 0, ?, ?)""",
        (ACCOUNT_LABEL, file_hash(input_path), rows_messages, rows_skipped, PARSER_VERSION),
    )

    conn.commit()

    total_unresolved = cur.execute(
        "SELECT COUNT(*) FROM messages WHERE thread_id IS NULL"
    ).fetchone()[0]
    by_role = cur.execute(
        "SELECT role, COUNT(*) FROM messages WHERE thread_id IS NULL GROUP BY role"
    ).fetchall()
    total_attachments = cur.execute(
        "SELECT COUNT(*) FROM attachments WHERE turn_hash IS NOT NULL"
    ).fetchone()[0]

    conn.close()

    print(f"Records read:              {len(records)}")
    print(f"Skipped (unrecognized):    {rows_skipped}")
    print(f"Messages written (unresolved, awaiting reconciliation): {total_unresolved}")
    for row in by_role:
        print(f"  role={row[0]:<14} {row[1]}")
    print(f"Attachments written:       {total_attachments}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    run(args.input)
