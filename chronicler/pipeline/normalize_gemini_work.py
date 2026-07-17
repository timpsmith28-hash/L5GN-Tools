"""
Gemini work-account normalizer — build spec item 4b.

Reads every file in raw_gem_files/ (110 files, Gemini "share individual
chat" export, work account — see parse_gemini_export.py for the binary
format this decodes), writes threads/messages into chronicler.db, does
fuzzy project-linking against the existing `projects` table, logs one
ingestion_log batch row, then archives the raw files per the 9.7
convention (move, not copy).

This is a ONE-TIME historical backfill (design doc 8.2/9.2 — work-account
Gemini is closed, no future exports of this kind). Not meant to be re-run
on a schedule; re-running it is still safe (idempotent on thread_id) but
there is nothing new for it to ever pick up after the raw files are moved
into zip_downloads/archive.

Known, deliberate gaps (in scope per the task, not oversights):
  - No timestamps: this export format carries none (confirmed corpus-wide
    in parse_gemini_export.py). threads.created_at/updated_at are left
    NULL for every gemini-work thread. render_md.py's frontmatter contract
    doesn't use these fields, so this doesn't break rendering. It does
    mean these threads are permanently invisible to suggest_close.py's
    30-day staleness check (which requires updated_at IS NOT NULL) — that
    seems like the right outcome for closed, already-historical threads
    rather than a gap worth papering over with a fabricated timestamp.
  - No attachment extraction: field 3.2 in the source format is an opaque
    high-entropy blob, not attachment content, and there is no dedicated
    attachment/filename field elsewhere in the schema. Per the task's
    explicit scope, this is flagged (see parse_gemini_export.py's
    docstring) rather than built.
  - Project-linking: there is no pre-existing Gemini fuzzy-linker to reuse
    (checked — normalize_gemini_personal.py and reconcile_gemini.py don't
    implement one; project_link is left NULL/pending everywhere upstream
    of this script today). The linker below is a new, self-contained
    implementation of the design intent in chronicler_system_design.md
    section 6 (fuzzy match for Gemini): best of (a) whole-string
    difflib.SequenceMatcher ratio between title and project name, (b)
    shared-significant-word overlap ratio against the project name's own
    tokens. FUZZY_THRESHOLD below is a genuinely open tunable (same
    status as reconcile_gemini.py's own fuzzy threshold) — start here,
    retune once Tim has reviewed a batch of real suggestions.

Usage:
    python3 pipeline/normalize_gemini_work.py [--raw-dir PATH] [--dry-run]
"""
import argparse
import difflib
import hashlib
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_connection, init_db, CHRONICLER_ROOT
from parse_gemini_export import parse_export_file, GeminiExportParseError

PARSER_VERSION = "gemini_work_v1"
ACCOUNT_LABEL = "gemini-work"
DEFAULT_RAW_DIR = CHRONICLER_ROOT / "chat_threads" / "raw_gem_files"
ARCHIVE_DIR = CHRONICLER_ROOT / "zip_downloads" / "archive" / "gemini" / ACCOUNT_LABEL

FUZZY_THRESHOLD = 0.45  # open tunable — see module docstring
TOKEN_RE = re.compile(r"[a-z0-9]{4,}")


def synth_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]


def load_projects(cur) -> list:
    return [dict(r) for r in cur.execute("SELECT project_id, name FROM projects").fetchall()]


def link_project(title: str, projects: list):
    """Returns (project_id, confidence, score) — confidence in
    ('exact', 'fuzzy', 'none'), score is the best raw signal (0.0 for
    'none', 1.0 for 'exact')."""
    title_l = (title or "").strip().lower()
    if not title_l or not projects:
        return None, "none", 0.0

    title_tokens = set(TOKEN_RE.findall(title_l))
    best_proj = None
    best_score = 0.0

    for proj in projects:
        name_l = (proj["name"] or "").strip().lower()
        if not name_l:
            continue
        if title_l == name_l:
            return proj["project_id"], "exact", 1.0

        ratio = difflib.SequenceMatcher(None, title_l, name_l).ratio()
        name_tokens = set(TOKEN_RE.findall(name_l))
        token_score = (
            len(title_tokens & name_tokens) / len(name_tokens) if name_tokens else 0.0
        )
        score = max(ratio, token_score)
        if score > best_score:
            best_score = score
            best_proj = proj

    if best_proj and best_score >= FUZZY_THRESHOLD:
        return best_proj["project_id"], "fuzzy", best_score
    return None, "none", 0.0


def run(raw_dir: Path, dry_run: bool):
    if not raw_dir.exists():
        raise SystemExit(f"Not found: {raw_dir}")

    files = sorted(p for p in raw_dir.iterdir() if p.is_file())
    if not files:
        print(f"No files found in {raw_dir} — nothing to do.")
        return

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    projects = load_projects(cur)

    parsed_ok = []
    failures = []
    for path in files:
        try:
            parsed_ok.append((path, parse_export_file(path)))
        except GeminiExportParseError as e:
            failures.append((path, str(e)))
        except Exception as e:
            failures.append((path, f"unexpected {type(e).__name__}: {e}"))

    rows_new_threads = 0
    rows_new_messages = 0
    rows_linked_fuzzy = 0
    rows_linked_exact = 0
    link_report = []

    for path, result in parsed_ok:
        thread_id = result["conversation_id"]
        title = result["title"]
        raw_ref = str(path.relative_to(CHRONICLER_ROOT))

        project_id, confidence, score = link_project(title, projects)
        if confidence == "exact":
            rows_linked_exact += 1
        elif confidence == "fuzzy":
            rows_linked_fuzzy += 1
            link_report.append((title, project_id, score))

        cur.execute(
            """INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,
                                     status, project_link, project_confidence, review_status,
                                     raw_ref, parser_version)
               VALUES (?, 'gemini', ?, ?, NULL, NULL, 'open', ?, ?, ?, ?, ?)
               ON CONFLICT(thread_id) DO UPDATE SET
                 title=excluded.title, project_link=excluded.project_link,
                 project_confidence=excluded.project_confidence,
                 review_status=excluded.review_status, raw_ref=excluded.raw_ref""",
            (
                thread_id, ACCOUNT_LABEL, title,
                project_id, confidence,
                "auto" if project_id else "pending",
                raw_ref, PARSER_VERSION,
            ),
        )
        rows_new_threads += 1

        if confidence == "fuzzy":
            cur.execute(
                """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
                   VALUES ('project_link', ?, ?, 'pending', ?, datetime('now'))""",
                (thread_id, score, f"Suggested project link (fuzzy, score {score:.2f}) for title: {title!r}"),
            )

        seq = 0
        for turn in result["turns"]:
            if turn["user"] is not None:
                message_id = synth_id("gemini-work", thread_id, seq, "user")
                cur.execute(
                    """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                       VALUES (?, ?, ?, 'user', ?, NULL, NULL)
                       ON CONFLICT(message_id) DO UPDATE SET content=excluded.content, seq=excluded.seq""",
                    (message_id, thread_id, seq, turn["user"]),
                )
                rows_new_messages += 1
            seq += 1
            if turn["model"] is not None:
                message_id = synth_id("gemini-work", thread_id, seq, "assistant")
                cur.execute(
                    """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at, source_turn_hash)
                       VALUES (?, ?, ?, 'assistant', ?, NULL, NULL)
                       ON CONFLICT(message_id) DO UPDATE SET content=excluded.content, seq=excluded.seq""",
                    (message_id, thread_id, seq, turn["model"]),
                )
                rows_new_messages += 1
            seq += 1

    for path, reason in failures:
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('gemini_work_parse_failure', NULL, NULL, 'pending', ?, datetime('now'))""",
            (f"{path.name}: {reason}",),
        )

    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('gemini', ?, NULL, datetime('now'), ?, 0, ?, ?)""",
        (ACCOUNT_LABEL, rows_new_threads, len(failures), PARSER_VERSION),
    )

    if dry_run:
        conn.rollback()
        print("DRY RUN — no changes committed, nothing archived.")
    else:
        conn.commit()

    conn.close()

    print(f"Files found:             {len(files)}")
    print(f"Parsed OK:               {len(parsed_ok)}")
    print(f"Parse failures:          {len(failures)}")
    for path, reason in failures:
        print(f"  FAIL: {path.name} -> {reason}")
    print(f"Threads written:         {rows_new_threads}")
    print(f"Messages written:        {rows_new_messages}")
    print(f"Project-linked exact:    {rows_linked_exact}")
    print(f"Project-linked fuzzy:    {rows_linked_fuzzy}")
    for title, project_id, score in link_report:
        print(f"  fuzzy {score:.2f}: {title!r} -> {project_id}")

    if dry_run:
        return

    # Item 5 — archive raw files per 9.7 convention (move, not copy), only
    # for files that were actually ingested successfully. Parse failures
    # are left in place (not archived) so they remain visible for
    # re-investigation rather than quietly vanishing into the archive.
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archived = 0
    for path, _ in parsed_ok:
        dest = ARCHIVE_DIR / f"{timestamp}__{path.name}"
        shutil.move(str(path), str(dest))
        archived += 1
    print(f"Archived to {ARCHIVE_DIR}: {archived} files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.raw_dir, args.dry_run)
