"""
Chronicler DB finalize & freeze (FINAL build session).

Leaves chronicler.db clean, honest and frozen for L5GN-Tools' `vault_reader`
(read-only consumer). Three data-quality repairs + a schema-version stamp, all
re-runnable and gated behind --apply (default is a dry-run preview). A timestamped
backup is taken automatically before any write.

  P1  Repair thread-IDs leaked into threads.project_link.
      Some early fuzzy links stored a thread_id (uuidv7 shape) in project_link
      instead of a project. A VALID project_link must resolve to a real row in
      `projects` (project_id). NOTE ON THE BRIEF'S WORDING: the brief says "must
      be a registry canonical_name", but legitimate Claude `exact` links store the
      Claude project *uuid* (a real projects.project_id) rather than the canonical
      name (see normalize_claude.py). Testing "resolves to a projects row" catches
      the leaked thread-ids (which are NOT in projects) WITHOUT wiping valid
      Claude-uuid or canonical links. Both are surfaced in the dry-run so you can
      confirm. Repaired rows: project_link=NULL, project_confidence=NULL, plus one
      review_queue row (type 'link_repair') each so they re-enter normal review.

  P2  Normalize the two "unlinked" states. project_confidence holds both SQL NULL
      and the string 'none' for the same meaning. Migrate every 'none' -> NULL so
      "unlinked" is unambiguously `project_link IS NULL`. evidence/manual/exact/
      fuzzy are untouched.

  P3  Thin-thread honesty flag. Add threads.substantive (INTEGER): 1 when the
      thread has >= SUBSTANTIVE_MIN_MESSAGES messages, else 0. Lets consumers
      distinguish substantial threads from Takeout-grouping fragments without
      re-counting messages every query. No deletion, no merging.

  FREEZE  Stamp a schema version (a one-row `meta` table AND PRAGMA user_version)
      and dump the live schema to pipeline/schema_frozen.sql with a FROZEN header.

Standing rules: UTF-8, UTC ISO-8601, single-transaction writes (all-or-nothing),
loud failure, backup before mutate, dry-run default.

Usage:
    python3 pipeline/finalize_db.py            # dry-run: report P1-P3 + census
    python3 pipeline/finalize_db.py --apply    # backup, run P1-P3, stamp + freeze
"""
import argparse
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, DB_PATH

try:
    from build_inventory import REGISTRY_PATH, read_json
except Exception:                       # registry helpers optional for reporting
    REGISTRY_PATH = None
    read_json = None

SCHEMA_VERSION = "1.0-frozen"           # bump on any future schema change + migration
SCHEMA_USER_VERSION = 1                 # PRAGMA user_version integer mirror
SUBSTANTIVE_MIN_MESSAGES = 4            # agreed cut: >= 4 messages == substantive
FROZEN_SQL_PATH = Path(__file__).resolve().parent / "schema_frozen.sql"

_UUIDV7_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def registry_canon():
    if not (REGISTRY_PATH and read_json and Path(REGISTRY_PATH).is_file()):
        return set()
    try:
        reg = read_json(REGISTRY_PATH)
        return {e["canonical_name"] for e in reg.get("projects", [])}
    except Exception:
        return set()


def valid_project_ids(conn):
    return {r["project_id"] for r in conn.execute("SELECT project_id FROM projects")}


def census(conn, label):
    print(f"\n----- census: {label} -----")
    print("threads by project_confidence:")
    for r in conn.execute(
        "SELECT COALESCE(project_confidence,'<NULL>') AS c, COUNT(*) AS n "
        "FROM threads GROUP BY project_confidence ORDER BY n DESC"):
        print(f"    {r['c']:12} {r['n']:6}")
    ev = conn.execute(
        "SELECT COUNT(*) AS n FROM threads "
        "WHERE project_link IS NOT NULL AND project_confidence='evidence'").fetchone()["n"]
    linked = conn.execute(
        "SELECT COUNT(*) AS n FROM threads WHERE project_link IS NOT NULL").fetchone()["n"]
    print(f"linked threads (project_link NOT NULL): {linked}   (of which evidence: {ev})")
    if _has_column(conn, "threads", "substantive"):
        sub = conn.execute(
            "SELECT COALESCE(substantive,-1) AS s, COUNT(*) AS n "
            "FROM threads GROUP BY substantive ORDER BY s DESC").fetchall()
        print("substantive flag: " + ", ".join(
            f"{'unset' if r['s']==-1 else r['s']}={r['n']}" for r in sub))
    else:
        print("substantive flag: (column not present yet)")
    print("review_queue by type:")
    for r in conn.execute(
        "SELECT type, COUNT(*) AS n FROM review_queue GROUP BY type ORDER BY n DESC"):
        print(f"    {str(r['type']):20} {r['n']:6}")


def _has_column(conn, table, col):
    return any(r["name"] == col for r in conn.execute(f"PRAGMA table_info({table})"))


# ---------------------------------------------------------------------------
# P1 - repair leaked thread-ids in project_link
# ---------------------------------------------------------------------------
def p1_find_invalid(conn):
    """Threads whose project_link does not resolve to a real projects row."""
    valid = valid_project_ids(conn)
    rows = conn.execute(
        "SELECT thread_id, project_link, project_confidence FROM threads "
        "WHERE project_link IS NOT NULL").fetchall()
    return [(r["thread_id"], r["project_link"], r["project_confidence"])
            for r in rows if r["project_link"] not in valid]


def p1_report(conn):
    invalid = p1_find_invalid(conn)
    print(f"\n[P1] invalid project_link rows (not a real project): {len(invalid)}")
    by_conf, uuidish = {}, 0
    for _, link, conf in invalid:
        by_conf[conf or "<NULL>"] = by_conf.get(conf or "<NULL>", 0) + 1
        if _UUIDV7_RE.match(link or ""):
            uuidish += 1
    for conf, n in sorted(by_conf.items(), key=lambda kv: -kv[1]):
        flag = "  <-- REVIEW: not fuzzy/none!" if conf not in ("fuzzy", "none", "<NULL>") else ""
        print(f"    confidence={conf:10} {n:4}{flag}")
    print(f"    (of these, {uuidish} match the uuidv7 thread-id shape)")
    for tid, link, conf in invalid[:12]:
        print(f"      {tid}  link={link}  conf={conf}")
    if len(invalid) > 12:
        print(f"      ... +{len(invalid) - 12} more")
    return invalid


def p1_apply(conn, invalid):
    now = utc_now()
    for tid, link, conf in invalid:
        conn.execute(
            "UPDATE threads SET project_link=NULL, project_confidence=NULL "
            "WHERE thread_id=?", (tid,))
        conn.execute(
            "INSERT INTO review_queue (type, thread_id, status, note, created_at) "
            "VALUES ('link_repair', ?, 'pending', ?, ?)",
            (tid,
             f"link_repair: reset invalid project_link {link!r} "
             f"(was confidence {conf!r}) - value did not resolve to a known "
             f"project; thread returned to review.",
             now))
    return len(invalid)


# ---------------------------------------------------------------------------
# P2 - normalize 'none' -> NULL
# ---------------------------------------------------------------------------
def p2_count(conn):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM threads WHERE project_confidence='none'").fetchone()["n"]


def p2_apply(conn):
    cur = conn.execute(
        "UPDATE threads SET project_confidence=NULL WHERE project_confidence='none'")
    return cur.rowcount


# ---------------------------------------------------------------------------
# P3 - substantive flag
# ---------------------------------------------------------------------------
def p3_preview(conn):
    sub = conn.execute(
        "SELECT COUNT(*) AS n FROM threads t WHERE "
        "(SELECT COUNT(*) FROM messages m WHERE m.thread_id=t.thread_id) >= ?",
        (SUBSTANTIVE_MIN_MESSAGES,)).fetchone()["n"]
    total = conn.execute("SELECT COUNT(*) AS n FROM threads").fetchone()["n"]
    return sub, total - sub, total


def p3_apply(conn):
    if not _has_column(conn, "threads", "substantive"):
        conn.execute("ALTER TABLE threads ADD COLUMN substantive INTEGER DEFAULT 0")
    conn.execute(
        "UPDATE threads SET substantive = CASE WHEN "
        "(SELECT COUNT(*) FROM messages m WHERE m.thread_id=threads.thread_id) >= ? "
        "THEN 1 ELSE 0 END", (SUBSTANTIVE_MIN_MESSAGES,))


# ---------------------------------------------------------------------------
# Freeze - schema version + schema dump
# ---------------------------------------------------------------------------
def stamp_version(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    for k, v in (("schema_version", SCHEMA_VERSION),
                 ("frozen_at", utc_now()),
                 ("substantive_min_messages", str(SUBSTANTIVE_MIN_MESSAGES))):
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    conn.execute(f"PRAGMA user_version = {SCHEMA_USER_VERSION}")


def dump_frozen_schema(conn):
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY rowid").fetchall()
    header = (
        f"-- Chronicler FROZEN schema  (schema_version {SCHEMA_VERSION}, "
        f"PRAGMA user_version {SCHEMA_USER_VERSION})\n"
        f"-- Frozen {utc_now()} by pipeline/finalize_db.py.\n"
        "-- FROZEN -- L5GN-Tools vault_reader consumes this read-only.\n"
        "-- Any change requires a migration script AND a schema_version bump.\n"
        "-- Load-bearing conventions (see pipeline/SCHEMA.md for the full contract):\n"
        "--   * unlinked  == threads.project_link IS NULL  (never the string 'none')\n"
        "--   * confidence authority: NULL < fuzzy < evidence < manual; 'exact' is\n"
        "--     source-native and, like 'manual', automation never overwrites it.\n"
        "--   * threads.substantive == 1 iff the thread has >= "
        f"{SUBSTANTIVE_MIN_MESSAGES} messages.\n\n")
    body = "\n".join((r["sql"].rstrip() + ";") for r in rows)
    FROZEN_SQL_PATH.write_text(header + body + "\n", encoding="utf-8")
    return FROZEN_SQL_PATH


# ---------------------------------------------------------------------------
def backup_db():
    src = Path(DB_PATH)
    if not src.is_file():
        raise SystemExit(f"[finalize_db] DB not found: {src}")
    dst = src.with_name(src.name + ".bak-finalize-" +
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    shutil.copy2(src, dst)
    return dst


def run(apply: bool):
    conn = get_connection()
    try:
        canon = registry_canon()
        print("=" * 68)
        print(f"Chronicler finalize & freeze  ({'APPLY' if apply else 'DRY-RUN'})")
        print("=" * 68)
        print(f"DB: {DB_PATH}")
        print(f"registry canonical_names known: {len(canon)}")

        census(conn, "before")
        invalid = p1_report(conn)
        none_n = p2_count(conn)
        print(f"\n[P2] project_confidence='none' rows to migrate -> NULL: {none_n}")
        sub, frag, total = p3_preview(conn)
        print(f"\n[P3] substantive: {sub} substantive / {frag} fragment "
              f"(< {SUBSTANTIVE_MIN_MESSAGES} msgs) of {total} threads")

        if not apply:
            print("\n(dry-run - nothing written. Re-run with --apply to persist.)")
            return

        bak = backup_db()
        print(f"\nbackup written: {bak}")
        conn.execute("BEGIN")
        n1 = p1_apply(conn, invalid)
        n2 = p2_apply(conn)
        p3_apply(conn)
        stamp_version(conn)
        conn.commit()
        print(f"P1 repaired {n1} link(s) (+{n1} link_repair review rows).")
        print(f"P2 migrated {n2} 'none' -> NULL.")
        print(f"P3 substantive flag populated (>= {SUBSTANTIVE_MIN_MESSAGES} msgs).")
        print(f"schema_version stamped: {SCHEMA_VERSION} (user_version {SCHEMA_USER_VERSION}).")
        frozen = dump_frozen_schema(conn)
        print(f"frozen schema dumped: {frozen}")

        census(conn, "after")
        # post-conditions
        leftover_none = p2_count(conn)
        leftover_bad = len(p1_find_invalid(conn))
        print(f"\npost-check: 'none' remaining={leftover_none} (want 0), "
              f"invalid project_link remaining={leftover_bad} (want 0)")
        if leftover_none or leftover_bad:
            raise SystemExit("[finalize_db] post-condition FAILED - inspect above.")
        print("post-conditions OK.")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Chronicler DB finalize & freeze (P1-P3 + freeze).")
    ap.add_argument("--apply", action="store_true",
                    help="Backup, then run P1-P3, stamp schema_version, dump schema_frozen.sql.")
    args = ap.parse_args()
    run(args.apply)
