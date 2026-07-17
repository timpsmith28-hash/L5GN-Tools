"""
.md renderer + sync-back reader — build spec item 7 (design doc section 13).

Sync-back must fully drain into the DB before any thread's .md is
regenerated in the same pass (13.5) — otherwise a fresh render could
overwrite a human's just-applied Obsidian edit with stale content. This
script therefore always runs sync_back() for every thread before render()
for any thread.

Filename convention (13.1): vault_staging/<source>/<account>/<thread_id>.md
— keyed on thread_id only, never on title, so Obsidian backlinks survive
title changes. The existing 35 vault_staging/*.md files (shatter.py output,
zero frontmatter, old "NNNN_Title.md" naming) are archived once, not
deleted, before the first regeneration pass.

Sync-back safety (the "stale file" hazard, learned the hard way):
    Any non-Obsidian DB write (relink.py --apply, the normalizers, group_fallback)
    makes the on-disk .md frontmatter OLDER than the DB. The original sync-back
    assumed "the file is never staler than the DB" and let the file win
    unconditionally — so running a render straight after a pipeline DB write read
    the stale `project_link: null` values back as if a human had typed them and
    clobbered fresh links (this wiped 133 evidence links once and logged 359
    bogus manual_override rows). Two guards now prevent that:

      (a) --no-syncback: skip file->DB entirely. run_pipeline uses this for the
          render that follows a pipeline write (DB->file only). Explicit and
          simple.
      (b) render_log 3-way merge: a frontmatter field is treated as a human
          override ONLY when it differs from the value we last rendered into that
          file (the "base"). A field equal to its last-rendered value is a stale
          default, not an edit, and is ignored no matter what the DB now says.
          The base is recorded per thread in the `render_log` table each render.

    (a) is the belt; (b) is the suspenders — even a hand-run `render_md.py` with
    sync-back ON will no longer mistake stale defaults for edits.

Usage:
    python3 pipeline/render_md.py                 # sync-back ON (honors real Obsidian edits)
    python3 pipeline/render_md.py --no-syncback   # DB->file only (use right after a pipeline DB write)
"""
import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT

try:
    import yaml
except ImportError as e:
    raise SystemExit(
        "pyyaml is required for render_md.py.\n"
        "Install with: pip install pyyaml --break-system-packages"
    ) from e

VAULT_DIR = CHRONICLER_ROOT / "chat_threads" / "vault_staging"
ARCHIVE_DIR = VAULT_DIR / "_archive"
MIGRATION_MARKER = VAULT_DIR / "._archived_pre_frontmatter"
OLD_FORMAT_RE = re.compile(r"^\d{4}_")

# 9.1 frontmatter contract — order matters (matches the design-doc sample).
FRONTMATTER_FIELD_ORDER = [
    "thread_id", "source", "account", "title", "status",
    "project_link", "project_confidence", "review_status",
    "review_note", "suggested_close", "tags",
]
READONLY_FIELDS = {"thread_id", "source", "account"}
EDITABLE_FIELDS = [
    "status", "project_link", "project_confidence",
    "review_status", "review_note", "suggested_close", "tags",
]

# Per-thread record of the editable-field values we LAST rendered into the .md.
# sync_back consults this "base" so a frontmatter field that still equals what we
# wrote is recognised as a stale default (not a human edit) and left alone.
# Self-contained CREATE IF NOT EXISTS so render works before/after any migration.
RENDER_LOG_DDL = """
CREATE TABLE IF NOT EXISTS render_log (
    thread_id       TEXT PRIMARY KEY,
    rendered_fields TEXT,        -- JSON: {field: last-rendered value}, editable fields only
    rendered_at     TEXT         -- UTC ISO-8601
);
"""

# Sentinel: this thread has no render_log base yet (never rendered by this code).
_NO_BASE = object()


def _normalize_field(field, value):
    """Canonical comparison form for one editable field, so file / DB / base all
    compare apples-to-apples."""
    if field == "tags":
        return normalize_tags(value)
    if field == "suggested_close":
        return bool(value)
    return value if value not in ("", None) else None


def load_render_bases(conn):
    """thread_id -> {field: last-rendered value} from render_log (empty if none)."""
    conn.execute(RENDER_LOG_DDL)
    bases = {}
    for r in conn.execute("SELECT thread_id, rendered_fields FROM render_log"):
        try:
            bases[r["thread_id"]] = json.loads(r["rendered_fields"]) if r["rendered_fields"] else {}
        except (json.JSONDecodeError, TypeError):
            bases[r["thread_id"]] = {}
    return bases


def record_render_base(cur, thread_row):
    """Store the editable-field snapshot we are about to write to this thread's
    .md, so a later sync_back can tell a real edit from a stale default."""
    snapshot = {f: _normalize_field(f, thread_row[f]) for f in EDITABLE_FIELDS}
    cur.execute(
        """INSERT INTO render_log (thread_id, rendered_fields, rendered_at)
           VALUES (?, ?, ?)
           ON CONFLICT(thread_id) DO UPDATE SET
             rendered_fields=excluded.rendered_fields,
             rendered_at=excluded.rendered_at""",
        (thread_row["thread_id"], json.dumps(snapshot),
         datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
    )


def archive_old_format_files():
    """13.1 — one-time migration, guarded by a marker file. Old shatter.py
    output has no frontmatter and uses NNNN_Title.md naming; move it aside
    rather than delete it or silently overwrite it."""
    if MIGRATION_MARKER.exists():
        return 0
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    moved = 0
    for path in VAULT_DIR.glob("*.md"):
        if OLD_FORMAT_RE.match(path.name):
            dest = ARCHIVE_DIR / f"{ts}__{path.name}"
            shutil.move(str(path), str(dest))
            moved += 1
    MIGRATION_MARKER.write_text(
        f"Old pre-frontmatter vault_staging files archived to _archive/ on {ts} UTC.\n"
        "This marker prevents re-archiving on every run — delete it only if you "
        "intentionally want the migration to run again.\n"
    )
    return moved


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    raw_fm = text[4:end]
    body = text[end + 5:]
    try:
        fm = yaml.safe_load(raw_fm) or {}
    except yaml.YAMLError:
        return None, text
    return fm, body


def normalize_tags(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [value]
        except json.JSONDecodeError:
            return [value] if value else []
    return []


def find_existing_md_files():
    if not VAULT_DIR.exists():
        return []
    return [p for p in VAULT_DIR.rglob("*.md") if ARCHIVE_DIR not in p.parents]


def sync_back(conn):
    """13.3 — file wins for editable fields a human genuinely edited; read-only
    fields are never accepted from the file; absent fields are 'no opinion'.

    "Genuinely edited" is the fix: a file field is only an override when it
    differs from the value we LAST rendered into that file (its render_log base).
    A field still equal to the last-rendered value is a stale default — ignored,
    even if the DB has since moved on (relink, normalizers, etc.). Without a base
    (thread never rendered by this code) we conservatively decline to override,
    so a stale pre-existing file can never clobber a fresh DB write."""
    cur = conn.cursor()
    bases = load_render_bases(conn)
    applied = 0

    for path in find_existing_md_files():
        fm, _ = parse_frontmatter(path)
        if not fm or "thread_id" not in fm:
            continue
        thread_id = fm["thread_id"]
        db_row = cur.execute("SELECT * FROM threads WHERE thread_id=?", (thread_id,)).fetchone()
        if db_row is None:
            continue  # file references a thread that no longer exists in the DB
        base = bases.get(thread_id)  # None => no render_log row yet

        for field in EDITABLE_FIELDS:
            if field not in fm:
                continue  # absent = no opinion, per 13.3 — never inferred as "clear this field"

            file_value = fm[field]
            db_value = db_row[field]
            file_norm = _normalize_field(field, file_value)
            db_norm = _normalize_field(field, db_value)
            if file_norm == db_norm:
                continue  # file already agrees with the DB — nothing to do

            # 3-way guard: is this a real human edit, or a stale default?
            # base missing entirely -> can't prove an edit -> decline (DB wins).
            if base is None:
                continue
            base_norm = _normalize_field(field, base[field]) if field in base else _NO_BASE
            if base_norm is _NO_BASE:
                continue  # field not in this thread's base snapshot -> can't prove edit
            if file_norm == base_norm:
                continue  # file unchanged since we wrote it -> stale default, not an edit

            # Genuine edit: file differs from both the DB and the last render.
            if field == "tags":
                new_db_value = json.dumps(file_norm)
                old_db_value = db_value
            elif field == "suggested_close":
                new_db_value = int(file_norm)
                old_db_value = db_value
            else:
                new_db_value = file_value
                old_db_value = db_value

            # A human genuinely edited this field in the file — file wins.
            if field == "project_link":
                cur.execute(
                    "UPDATE threads SET project_link=?, project_confidence='manual' WHERE thread_id=?",
                    (new_db_value, thread_id),
                )
            else:
                cur.execute(
                    f"UPDATE threads SET {field}=? WHERE thread_id=?",
                    (new_db_value, thread_id),
                )

            cur.execute(
                """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at, resolved_at)
                   VALUES ('manual_override', ?, NULL, 'confirmed', ?, datetime('now'), datetime('now'))""",
                (thread_id, f"{field}: {old_db_value!r} -> {new_db_value!r}"),
            )
            applied += 1

    conn.commit()
    return applied


def render_body(cur, thread_id):
    msgs = cur.execute(
        """SELECT role, content FROM messages WHERE thread_id=? ORDER BY seq ASC""",
        (thread_id,),
    ).fetchall()
    lines = []
    for m in msgs:
        heading = {"user": "User", "assistant": "Assistant"}.get(m["role"], m["role"].title())
        lines.append(f"### {heading}\n\n{m['content'] or ''}\n")
    return "\n".join(lines)


def render_thread(cur, thread_row):
    fm = {
        "thread_id": thread_row["thread_id"],
        "source": thread_row["source"],
        "account": thread_row["account"],
        "title": thread_row["title"] or "Untitled",
        "status": thread_row["status"],
        "project_link": thread_row["project_link"],
        "project_confidence": thread_row["project_confidence"],
        "review_status": thread_row["review_status"],
        "review_note": thread_row["review_note"],
        "suggested_close": bool(thread_row["suggested_close"]),
        "tags": normalize_tags(thread_row["tags"]),
    }
    fm_ordered = {k: fm[k] for k in FRONTMATTER_FIELD_ORDER}
    fm_yaml = yaml.safe_dump(fm_ordered, sort_keys=False, allow_unicode=True).strip()

    body = render_body(cur, thread_row["thread_id"])
    content = f"---\n{fm_yaml}\n---\n\n# {fm['title']}\n\n{body}"

    out_dir = VAULT_DIR / thread_row["source"] / thread_row["account"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{thread_row['thread_id']}.md"
    out_path.write_text(content, encoding="utf-8")
    # Record exactly what we wrote, so a future sync_back can distinguish a real
    # human edit from a stale default (the 3-way base).
    record_render_base(cur, thread_row)
    return out_path


def run(no_syncback=False):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # Ensure render_log exists on EVERY path: with --no-syncback we skip
    # sync_back() (the other place the DDL runs), but render_thread still
    # writes a base row, so the table must exist regardless.
    conn.execute(RENDER_LOG_DDL)

    moved = archive_old_format_files()
    print(f"Archived old-format files: {moved}")

    if no_syncback:
        # DB->file only. Use right after a pipeline DB write, when the on-disk
        # frontmatter is older than the DB and must not be read back.
        print("Sync-back: suppressed (--no-syncback) — DB is authoritative this pass.")
    else:
        applied = sync_back(conn)
        print(f"Sync-back overrides applied: {applied}")

    threads = cur.execute("SELECT thread_id FROM threads").fetchall()
    rendered = 0
    for t in threads:
        # Re-read fresh per 13.5 — sync-back for this thread has already
        # been fully drained above, so this row reflects any edit just applied.
        fresh = cur.execute("SELECT * FROM threads WHERE thread_id=?", (t["thread_id"],)).fetchone()
        render_thread(cur, fresh)
        rendered += 1

    conn.commit()  # persist render_log bases written during this pass
    conn.close()
    print(f"Threads rendered: {rendered}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render threads to .md (with optional sync-back).")
    ap.add_argument("--no-syncback", action="store_true",
                    help="Skip file->DB sync-back; render DB->file only. Use immediately "
                         "after a pipeline DB write (relink, normalizers) so stale "
                         "frontmatter can't clobber fresh DB values.")
    args = ap.parse_args()
    run(no_syncback=args.no_syncback)
