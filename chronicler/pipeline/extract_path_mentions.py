"""
S5 - Path-mention extraction (evidence producer).

Scans `messages.content` for filesystem paths and, when a path contains a folder
segment that matches a project's canonical name or an alias, emits a
`path_mention` evidence row for that thread->project pair (weight 0.9 - a path
that literally names the repo folder is a strong automatic signal, second only to
a unique filename hit).

Normalisation (spec S5.2) - the whole point of this producer:
  * A path is split into SEGMENTS on any run of `/`, `\\` or `:` separators.
  * Each segment - and each adjacent (previous, current) PAIR of segments - is
    compact-normalised (lower-cased, every `-`, `_`, space and separator
    stripped) and tested against the same compact-normalised registry keys.
  * Matching is therefore case-insensitive AND separator-insensitive, so
    `Crystal-Spire`, `crystal_spire` and `Crystal Spire` all collapse to
    `crystalspire`, and the two-segment folder pair `...\\L5GN\\Crystal-Spire\\`
    collapses to `l5gncrystalspire`, matching the canonical `L5GN-Crystal-Spire`.
  * EVERYTHING LEFT OF THE MATCH IS IGNORED - a foreign username, a different
    drive, or an unrelated parent directory never suppresses or produces a hit.
    So `C:\\Users\\someone-else\\Github\\L5GN\\Crystal-Spire\\tui.py` still votes
    for Crystal-Spire, and `C:\\Python314\\Lib\\...` votes for nothing (no
    segment matches a project; `lib`/`python314` are infrastructure noise).

This skill ONLY writes `link_evidence` rows - relink.py (S6) is the sole consumer
that turns evidence into link decisions.

Idempotency / caching (spec S5.3):
  * A `path_scan_log` watermark records the highest `messages.rowid` scanned, so
    normal runs only tokenise NEW messages (the messages table is large; a full
    re-scan every pipeline run is wasteful). New votes are appended, skipping any
    (thread, project, detail) triple already present, so re-runs never duplicate.
  * `--rescan` deletes this producer's own `path_mention` rows, resets the
    watermark and re-scans every message from scratch (full idempotent rebuild).
    It never touches rows from other signals.

Standing rules: UTF-8, UTC ISO-8601, loud failure (a broken registry stops the
run rather than writing partial evidence), single-transaction writes (all rows
land or none do), --apply gates every write (default is a dry-run preview).

Usage:
    python3 pipeline/extract_path_mentions.py            # dry-run (incremental): report only
    python3 pipeline/extract_path_mentions.py --apply    # append new path_mention evidence
    python3 pipeline/extract_path_mentions.py --rescan --apply   # full rebuild from rowid 0
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection
from build_inventory import REGISTRY_PATH

PRODUCER_VERSION = "extract_path_mentions/1.0"
SIGNAL = "path_mention"
EVIDENCE_WEIGHT = 0.9          # a path naming the repo folder is a strong signal
MIN_KEY_LEN = 4               # compact keys shorter than this are too collision-
                              # prone to trust as a lone path segment (drops 'CID',
                              # 'sol', 'cli' style aliases from path matching)

# Infrastructure / system path segments that must NEVER be treated as a project
# match, even if some alias unluckily compacts to the same string. Belt-and-braces
# on top of the curated registry keys - guarantees the C:\Python314\Lib acceptance
# case (and Users/Github/AppData scaffolding) produces zero hits.
PATH_NOISE = {
    "users", "user", "github", "gitlab", "documents", "document", "downloads",
    "desktop", "appdata", "roaming", "local", "locallow", "windows", "system32",
    "syswow64", "programfiles", "programfilesx86", "program", "temp", "tmp",
    "cache", "onedrive", "dropbox", "googledrive", "lib", "libs", "bin", "sbin",
    "usr", "etc", "var", "opt", "home", "root", "mnt", "media", "sitepackages",
    "nodemodules", "dist", "vendor", "venv", "python", "python3", "python310",
    "python311", "python312", "python313", "python314", "scripts", "include",
    "share", "public", "private", "srv", "proc", "dev", "http", "https", "www",
    "com", "org", "net", "github.com", "githubcom",
}

# A path-ish token: a run of path characters that must contain at least one
# separator (/ or \). Colon is included so a Windows drive prefix stays attached
# to its path (and URL schemes stay in one token, so a repo named inside a github
# URL is still found). We split into real segments afterwards.
_PATH_CHAR = r"[A-Za-z0-9_.\-~/\\:]"
_PATH_TOKEN_RE = re.compile(_PATH_CHAR + r"*[\\/]" + _PATH_CHAR + r"*")
_SEG_SPLIT_RE = re.compile(r"[\\/:]+")
_COMPACT_RE = re.compile(r"[-_\s./]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact(s: str) -> str:
    """Lower-case and strip every separator so name variants collapse to one key.
    'L5GN-Crystal-Spire' / 'Crystal Spire' / 'crystal_spire' -> 'crystalspire'
    (spaces, -, _, ., and stray path separators all removed)."""
    return _COMPACT_RE.sub("", s).replace("\\", "").lower()


def load_project_keys(registry_path: Path):
    """Build compact_key -> set(project). Keys come from every entry's
    canonical_name + aliases. Returns (keymap, detail_of) where detail_of maps a
    compact key to a human-readable source label for the evidence `detail`."""
    if not registry_path.is_file():
        raise SystemExit(f"[extract_path_mentions] registry missing: {registry_path}")
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    keymap = defaultdict(set)
    detail_of = {}
    for entry in registry["projects"]:
        canon = entry["canonical_name"]
        sources = [canon] + list(entry.get("aliases", []))
        for src in sources:
            key = compact(src)
            if len(key) < MIN_KEY_LEN or key in PATH_NOISE:
                continue
            keymap[key].add(canon)
            detail_of.setdefault(key, src)   # first source label wins for display
    if not keymap:
        raise SystemExit("[extract_path_mentions] no usable project keys in registry.")
    return keymap, detail_of


def extract_paths(text: str):
    """Every path-ish token (contains a separator) in a message body."""
    return _PATH_TOKEN_RE.findall(text)


def match_path(path: str, keymap):
    """Given one path token, yield (project, compact_key) for every project whose
    name/alias matches a segment OR an adjacent (prev, cur) segment pair. Segments
    in PATH_NOISE are never counted. De-dupes within the single path."""
    segs = [s for s in _SEG_SPLIT_RE.split(path) if s]
    hits = set()
    prev_key = None
    for seg in segs:
        key = compact(seg)
        if len(key) >= MIN_KEY_LEN and key not in PATH_NOISE and key in keymap:
            for project in keymap[key]:
                hits.add((project, key))
        # (previous, current) pair collapses a multi-segment folder name, e.g.
        # .../L5GN/Crystal-Spire/... -> 'l5gncrystalspire' == canonical key.
        if prev_key is not None:
            pair = prev_key + key
            if len(pair) >= MIN_KEY_LEN and pair not in PATH_NOISE and pair in keymap:
                for project in keymap[pair]:
                    hits.add((project, pair))
        prev_key = key
    return hits


def scan_rows(rows, keymap, detail_of):
    """rows: iterable of (thread_id, content). Returns a list of unique
    (thread_id, project, weight, detail) votes (one per thread/project/key)."""
    seen = set()
    votes = []
    for thread_id, content in rows:
        if not content:
            continue
        for path in extract_paths(content):
            for project, key in match_path(path, keymap):
                triple = (thread_id, project, key)
                if triple in seen:
                    continue
                seen.add(triple)
                votes.append((thread_id, project, EVIDENCE_WEIGHT,
                              detail_of.get(key, key)))
    return votes


# ---------------------------------------------------------------------------
# DB plumbing
# ---------------------------------------------------------------------------
LINK_EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,
    signal           TEXT,
    weight           REAL,
    detail           TEXT,
    produced_at      TEXT,
    producer_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);
"""

PATH_SCAN_LOG_DDL = """
CREATE TABLE IF NOT EXISTS path_scan_log (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    scanned_through    INTEGER NOT NULL,   -- highest messages.rowid scanned
    updated_at         TEXT NOT NULL
);
"""


def get_watermark(conn) -> int:
    conn.executescript(PATH_SCAN_LOG_DDL)
    row = conn.execute("SELECT scanned_through FROM path_scan_log WHERE id = 1").fetchone()
    return int(row["scanned_through"]) if row else 0


def set_watermark(conn, rowid: int):
    conn.execute(
        "INSERT INTO path_scan_log (id, scanned_through, updated_at) VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET scanned_through=excluded.scanned_through, "
        "updated_at=excluded.updated_at",
        (rowid, utc_now()),
    )


def load_messages_since(conn, watermark: int):
    """(thread_id, content) for messages with rowid > watermark that resolve to a
    thread. Also returns the max rowid across ALL messages so the watermark can
    advance past thread-less/empty rows we intentionally skip."""
    max_row = conn.execute("SELECT COALESCE(MAX(rowid), 0) AS m FROM messages").fetchone()["m"]
    rows = conn.execute(
        "SELECT thread_id, content FROM messages "
        "WHERE rowid > ? AND thread_id IS NOT NULL "
        "AND content IS NOT NULL AND TRIM(content) <> ''",
        (watermark,),
    ).fetchall()
    return [(r["thread_id"], r["content"]) for r in rows], int(max_row)


def load_existing_triples(conn):
    """Existing (thread_id, project, detail) for THIS signal, so incremental
    appends never duplicate a vote already recorded on an earlier run."""
    conn.executescript(LINK_EVIDENCE_DDL)
    rows = conn.execute(
        "SELECT thread_id, project, detail FROM link_evidence WHERE signal = ?",
        (SIGNAL,),
    ).fetchall()
    return {(r["thread_id"], r["project"], r["detail"]) for r in rows}


def write_evidence(conn, votes, rescan, new_watermark):
    """Single transaction: (optional) clear own rows on rescan, insert new votes,
    advance the watermark. All-or-nothing."""
    now = utc_now()
    # Create BOTH tables before any data mutation. On the --rescan path
    # get_watermark() (the other place PATH_SCAN_LOG_DDL runs) is skipped, so
    # set_watermark() below would otherwise hit a missing table and crash the
    # apply. Both executescripts run before the DELETE/INSERT so the data writes
    # still land as one all-or-nothing transaction committed at the end.
    conn.executescript(LINK_EVIDENCE_DDL)
    conn.executescript(PATH_SCAN_LOG_DDL)
    if rescan:
        conn.execute("DELETE FROM link_evidence WHERE signal = ?", (SIGNAL,))
    conn.executemany(
        "INSERT INTO link_evidence "
        "(thread_id, project, signal, weight, detail, produced_at, producer_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(t, p, SIGNAL, w, d, now, PRODUCER_VERSION) for (t, p, w, d) in votes],
    )
    set_watermark(conn, new_watermark)
    conn.commit()


def report(votes, scanned, watermark, new_watermark, rescan):
    per_project = defaultdict(int)
    for _, p, _, _ in votes:
        per_project[p] += 1
    threads = len({t for t, _, _, _ in votes})
    print("=" * 66)
    print("path_mention evidence" + ("  (full rescan)" if rescan else "  (incremental)"))
    print("=" * 66)
    print(f"scanned {scanned} message(s) with rowid in ({watermark}, {new_watermark}]")
    print(f"{'project':32} {'new votes':>10}")
    for project in sorted(per_project):
        print(f"{project:32} {per_project[project]:>10}")
    print("-" * 66)
    print(f"{len(votes)} new evidence row(s) across {threads} thread(s).")


def run(apply: bool, rescan: bool):
    keymap, detail_of = load_project_keys(REGISTRY_PATH)
    conn = get_connection()
    try:
        watermark = 0 if rescan else get_watermark(conn)
        rows, new_watermark = load_messages_since(conn, watermark)
        votes = scan_rows(rows, keymap, detail_of)
        if not rescan:
            existing = load_existing_triples(conn)
            votes = [v for v in votes if (v[0], v[1], v[3]) not in existing]
        if apply:
            write_evidence(conn, votes, rescan, new_watermark)
    finally:
        conn.close()

    report(votes, len(rows), watermark, new_watermark, rescan)
    if apply:
        print(f"\nWrote {len(votes)} '{SIGNAL}' row(s); watermark now {new_watermark}.")
    else:
        print("\n(dry-run - nothing written. Re-run with --apply to persist.)")
    return votes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Path-mention evidence (S5).")
    ap.add_argument("--apply", action="store_true",
                    help="Write path_mention rows to link_evidence (default dry-run).")
    ap.add_argument("--rescan", action="store_true",
                    help="Delete own rows, reset watermark, re-scan every message.")
    args = ap.parse_args()
    run(args.apply, args.rescan)
