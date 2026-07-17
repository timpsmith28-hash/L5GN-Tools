"""
S4 step 2 - Filename cross-reference (evidence producer).

Joins Chronicler's `attachments` table against the per-project `file_inventory`
blocks in the registry (built by build_inventory.py). An exact basename match
is the strongest *automatic* link signal available.

Vote rules (spec S4.2):
  * unique hit  (exactly one project owns that basename)  -> weight 1.0
  * multi-hit   (n projects share it), not stoplisted      -> weight 1/n each
  * generic basename (main.py, README.md, ...)             -> no signal
  * no hit                                                  -> no signal
    (absence is NOT negative evidence - attachments legitimately include
     non-repo files)

This skill ONLY produces evidence rows in `link_evidence`; it never writes a
link. S6 (relink.py) is the sole consumer that turns evidence into decisions.

`link_evidence` is created here with CREATE TABLE IF NOT EXISTS using exactly
the columns S6 specifies, so S4 is independently runnable before S6's migration
lands (the migration uses the same IF NOT EXISTS DDL - idempotent either way).

Idempotency: a run first deletes this producer's own `filename_xref` rows, then
re-inserts, so re-running yields the same table (never accumulating dupes). It
never touches rows from other signals.

Standing rules: UTF-8, UTC ISO-8601, loud failure (a broken registry/inventory
stops the run rather than writing partial evidence). DB writes are wrapped in a
single transaction - all rows land or none do.

Usage:
    python3 pipeline/xref_filenames.py             # dry-run (default): report only
    python3 pipeline/xref_filenames.py --apply     # write evidence rows
"""
import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, CHRONICLER_ROOT

GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"

PRODUCER_VERSION = "xref_filenames/1.1"   # 1.1: export-artifact exclusion (fix C)
SIGNAL = "filename_xref"

# Generic basenames that carry no project-distinctiveness. A basename here never
# produces evidence, whether it is a unique hit or a multi-hit (a unique hit on
# a generic name is not real evidence - it just means the other repos happen not
# to contain that boilerplate file). Extend freely; this is the one knob.
GENERIC_BASENAMES = {
    "main.py", "readme.md", "readme", "requirements.txt", "__init__.py",
    "setup.py", "setup.cfg", "pyproject.toml", "index.html", "index.js",
    "index.ts", "package.json", "package-lock.json", "yarn.lock",
    ".gitignore", ".gitattributes", "dockerfile", "docker-compose.yml",
    "makefile", "license", "license.md", "license.txt", "config.py",
    "config.json", "settings.py", "utils.py", "test.py", "tests.py",
    "conftest.py", "app.py", "run.py", "cli.py", ".env", ".env.example",
    "tsconfig.json", "style.css", "styles.css", "notes.md", "todo.md",
    "changelog.md", "manifest.json",
}

# Fix C: conversation-export data artifacts are NOT project source. A Gemini/
# Claude export dump can carry a basename that happens to live in a project's
# inventory (e.g. GemToPairs archives its own `[gemini conversation] ...` files),
# which then falsely links any thread that attaches that dump. Such basenames
# are excluded from the project-owned index entirely. We exclude ONLY the data
# artifacts - never scripts: `parse_gemini_export.py` is legitimate GemToPairs
# source and must still count.
#   * `[gemini conversation] ...` / `[claude conversation] ...` export files
#   * date-stamped `.json` conversation dumps (a `_YYYYMMDD_` segment)
_EXPORT_PREFIX_RE = re.compile(r"^\[(?:gemini|claude) conversation\]", re.IGNORECASE)
_EXPORT_JSON_DUMP_RE = re.compile(r"_\d{8}[_-].*\.json$", re.IGNORECASE)


def is_export_artifact(basename_lower: str) -> bool:
    """True for conversation-export DATA artifacts (never for .py scripts)."""
    if basename_lower.endswith(".py"):
        return False
    if _EXPORT_PREFIX_RE.match(basename_lower):
        return True
    if _EXPORT_JSON_DUMP_RE.search(basename_lower):
        return True
    return False

# link_evidence schema - EXACTLY the columns S6 specifies (spec S6 evidence
# model). CREATE IF NOT EXISTS so this is safe to run before or after S6.
LINK_EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,      -- canonical_name from the registry
    signal           TEXT,      -- name_alias|vocabulary|filename_xref|path_mention|time_window
    weight           REAL,      -- 0..1
    detail           TEXT,      -- e.g. the matched basename
    produced_at      TEXT,      -- UTC ISO-8601
    producer_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_basename_index(registry_path: Path):
    """basename(lower) -> set(canonical_name) from every entry's file_inventory."""
    if not registry_path.is_file():
        raise SystemExit(f"[xref_filenames] registry missing: {registry_path}")
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    index = defaultdict(set)
    have_inv = 0
    excluded = 0
    for entry in registry["projects"]:
        inv = entry.get("file_inventory")
        if not inv:
            continue
        have_inv += 1
        canon = entry["canonical_name"]
        for rel in inv.get("paths", []):
            base = rel.split("/")[-1].lower()
            if not base:
                continue
            if is_export_artifact(base):
                excluded += 1          # Fix C: not project-owned source
                continue
            index[base].add(canon)
    if have_inv == 0:
        raise SystemExit("[xref_filenames] no file_inventory in registry - "
                         "run build_inventory.py first.")
    if excluded:
        print(f"[xref_filenames] excluded {excluded} export-artifact basename(s) "
              "from the project-owned index (fix C).")
    return index


def load_attachments(conn):
    """(thread_id, basename_lower) for every attachment that resolves to a
    thread. Attachments whose message has no thread yet are skipped (no thread
    to vote for)."""
    rows = conn.execute("""
        SELECT m.thread_id AS thread_id, a.filename AS filename
        FROM attachments a
        JOIN messages m ON m.message_id = a.message_id
        WHERE m.thread_id IS NOT NULL
          AND a.filename IS NOT NULL
          AND TRIM(a.filename) <> ''
    """).fetchall()
    out = []
    for r in rows:
        base = os.path.basename(r["filename"].strip()).lower()
        if base:
            out.append((r["thread_id"], base))
    return out


def compute_votes(attachments, index):
    """Yield (thread_id, project, weight, detail). One row per (attachment,
    project) hit. De-dupes identical (thread, project, basename) triples so a
    thread that attaches the same file five times votes once."""
    seen = set()
    votes = []
    for thread_id, base in attachments:
        if base in GENERIC_BASENAMES:
            continue
        owners = index.get(base)
        if not owners:
            continue
        n = len(owners)
        weight = 1.0 if n == 1 else round(1.0 / n, 4)
        for project in sorted(owners):
            key = (thread_id, project, base)
            if key in seen:
                continue
            seen.add(key)
            votes.append((thread_id, project, weight, base))
    return votes


def write_evidence(conn, votes):
    now = utc_now()
    conn.executescript(LINK_EVIDENCE_DDL)
    # idempotent: clear only this producer's own signal rows, then re-insert.
    conn.execute("DELETE FROM link_evidence WHERE signal = ?", (SIGNAL,))
    conn.executemany(
        "INSERT INTO link_evidence "
        "(thread_id, project, signal, weight, detail, produced_at, producer_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(t, p, SIGNAL, w, d, now, PRODUCER_VERSION) for (t, p, w, d) in votes],
    )
    conn.commit()


def report(votes):
    per_project = defaultdict(lambda: [0, 0])  # project -> [unique, multi]
    for _, project, weight, _ in votes:
        per_project[project][0 if weight == 1.0 else 1] += 1
    threads = len({t for t, _, _, _ in votes})
    print("=" * 62)
    print("filename_xref evidence")
    print("=" * 62)
    print(f"{'project':30} {'unique(1.0)':>12} {'multi(<1)':>10}")
    for project in sorted(per_project):
        u, m = per_project[project]
        print(f"{project:30} {u:>12} {m:>10}")
    print("-" * 62)
    print(f"{len(votes)} evidence rows across {threads} threads.")


def run(apply: bool):
    index = load_basename_index(REGISTRY_PATH)
    conn = get_connection()
    try:
        attachments = load_attachments(conn)
        votes = compute_votes(attachments, index)
        if apply:
            write_evidence(conn, votes)
    finally:
        conn.close()

    report(votes)
    if apply:
        print(f"\nWrote {len(votes)} '{SIGNAL}' rows to link_evidence.")
    else:
        print("\n(dry-run - nothing written. Re-run with --apply to persist.)")
    return votes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Filename cross-reference evidence (S4.2).")
    ap.add_argument("--apply", action="store_true",
                    help="Write evidence rows (default is dry-run, report only).")
    args = ap.parse_args()
    run(args.apply)
