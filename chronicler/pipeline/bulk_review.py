"""
Bulk-accept for high-confidence review items — QoL build B1.

Problem this solves: the layered grouping fallback leaves a large pile of
`thread_grouping` rows in `review_queue`, most at high confidence. Confirming
those one-by-one in Obsidian frontmatter is pointless toil — confidence tiers
existed precisely to enable a bulk sweep of the safe ones.

Scope (deliberately narrow):
  Only `thread_grouping` rows are eligible. `reconciliation_gap`,
  `reconciliation_fuzzy_match`, `reconciliation_order_conflict`,
  `reopen_candidate`, and `close_suggestion` rows are individually meaningful
  and stay manual — this tool never touches them.

Safety model:
  * --dry-run is the DEFAULT. Nothing is written unless you pass --apply.
  * The override rule is absolute: a row already confirmed/rejected/reassigned
    by hand is never touched, regardless of --min-confidence. We enforce this
    two ways — we only select review_queue rows still `status='pending'`, AND
    we only touch threads whose `review_status` is still 'auto'/'pending'
    (a human who confirmed/reassigned a grouping in Obsidian has already
    flipped review_status via sync-back, so those are skipped).
  * Every bulk run writes exactly ONE audit row to review_queue
    (type='bulk_accept', note = criteria + count). The trail must show that a
    human deliberately ran a bulk-accept with these parameters — not 839 rows
    silently mutating.

Sync-back safety (this is the subtle part):
  render_md.py runs sync_back() BEFORE it re-renders — file wins over DB for
  editable frontmatter fields. review_status IS editable. So if we flipped the
  DB to 'confirmed' and then just ran the standard render, sync_back would read
  the still-'pending' .md files and revert every thread right back to pending
  (and log 839 spurious manual_override rows). To avoid that, once the DB is
  updated we also write review_status: confirmed into the corresponding .md
  frontmatter BEFORE rendering, so file and DB already agree and sync_back is a
  clean no-op. This is legitimate DB->file flow: the CLI invocation carries the
  same human authority as an Obsidian edit (per design 9.1 / 13.3).

Usage:
    # See what would change (default — writes nothing):
    python3 pipeline/bulk_review.py --accept-groupings --min-confidence 0.95

    # Actually commit:
    python3 pipeline/bulk_review.py --accept-groupings --min-confidence 0.95 --apply
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT, DB_PATH

PIPELINE_DIR = Path(__file__).resolve().parent
VAULT_DIR = CHRONICLER_ROOT / "chat_threads" / "vault_staging"
RENDER_SCRIPT = PIPELINE_DIR / "render_md.py"

# review_status values that mean "no human has ruled on this thread yet" and so
# are safe to bulk-confirm. Anything else (confirmed / rejected / reassigned /
# etc.) is a human decision we must not override.
UNTOUCHED_REVIEW_STATUSES = ("auto", "pending")

SAMPLE_SIZE = 10


def select_candidates(cur, min_confidence):
    """Pending thread_grouping rows at/above the confidence floor, restricted
    to threads no human has already ruled on. Returns list of Row."""
    return cur.execute(
        """SELECT rq.item_id, rq.thread_id, rq.confidence, rq.note,
                  t.title, t.review_status
             FROM review_queue rq
             JOIN threads t ON t.thread_id = rq.thread_id
            WHERE rq.type = 'thread_grouping'
              AND rq.status = 'pending'
              AND rq.confidence >= ?
              AND t.review_status IN ({})
            ORDER BY rq.confidence DESC, rq.thread_id""".format(
            ",".join("?" * len(UNTOUCHED_REVIEW_STATUSES))
        ),
        (min_confidence, *UNTOUCHED_REVIEW_STATUSES),
    ).fetchall()


def print_plan(rows, min_confidence):
    n_rows = len(rows)
    thread_ids = {r["thread_id"] for r in rows}
    print(f"Criteria:   type=thread_grouping, status=pending, confidence >= {min_confidence}")
    print(f"            (threads already ruled on by hand are excluded)")
    print(f"Matched:    {n_rows} pending grouping rows across {len(thread_ids)} threads")
    if n_rows:
        print(f"\nSample (up to {SAMPLE_SIZE}):")
        print(f"  {'confidence':>10}  {'thread_id':<34}  title")
        for r in rows[:SAMPLE_SIZE]:
            title = (r["title"] or "")[:48]
            conf = "" if r["confidence"] is None else f"{r['confidence']:.3f}"
            print(f"  {conf:>10}  {r['thread_id']:<34}  {title}")
    return n_rows, len(thread_ids)


def patch_frontmatter_review_status(thread_rows):
    """Set review_status: confirmed in each thread's .md frontmatter, so the
    follow-up render's sync_back sees file == DB (no revert, no spurious
    override rows). Skips threads with no rendered file yet — render will
    create those fresh from the DB. Returns count of files patched."""
    fm_re = re.compile(r"^(review_status:).*$", re.MULTILINE)
    patched = 0
    for tr in thread_rows:
        md_path = VAULT_DIR / tr["source"] / tr["account"] / f"{tr['thread_id']}.md"
        if not md_path.exists():
            continue
        text = md_path.read_text(encoding="utf-8")
        # Only rewrite within the leading frontmatter block.
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end == -1:
            continue
        head, rest = text[: end + 1], text[end + 1 :]
        new_head, n = fm_re.subn(r"\1 confirmed", head, count=1)
        if n and new_head != head:
            md_path.write_text(new_head + rest, encoding="utf-8")
            patched += 1
    return patched


def run_render():
    """Invoke the standard renderer as its own process so it picks up the same
    CHRONICLER_DB_PATH we're using. Returns (returncode, stdout, override_count)."""
    if not RENDER_SCRIPT.exists():
        print("  [render skipped] render_md.py not found next to this script.")
        return 0, "", None
    proc = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT)],
        cwd=str(PIPELINE_DIR),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    override_count = None
    m = re.search(r"Sync-back overrides applied:\s*(\d+)", out)
    if m:
        override_count = int(m.group(1))
    return proc.returncode, out, override_count


def apply_changes(conn, rows, min_confidence):
    cur = conn.cursor()
    item_ids = [r["item_id"] for r in rows]
    thread_ids = sorted({r["thread_id"] for r in rows})

    # 1. Resolve the matched pending grouping rows.
    cur.executemany(
        "UPDATE review_queue SET status='confirmed', resolved_at=datetime('now') WHERE item_id=?",
        [(i,) for i in item_ids],
    )
    # 2. Flip the threads to confirmed.
    cur.executemany(
        "UPDATE threads SET review_status='confirmed' WHERE thread_id=?",
        [(t,) for t in thread_ids],
    )
    # 3. ONE audit row for the whole sweep.
    note = (
        f"bulk_accept: --accept-groupings --min-confidence {min_confidence} -> "
        f"confirmed {len(item_ids)} thread_grouping rows across {len(thread_ids)} threads"
    )
    cur.execute(
        """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at, resolved_at)
           VALUES ('bulk_accept', NULL, ?, 'confirmed', ?, datetime('now'), datetime('now'))""",
        (min_confidence, note),
    )
    conn.commit()

    # 4. Fetch source/account for file paths, patch frontmatter, then render.
    thread_rows = cur.execute(
        "SELECT thread_id, source, account FROM threads WHERE thread_id IN ({})".format(
            ",".join("?" * len(thread_ids))
        ),
        thread_ids,
    ).fetchall()
    patched = patch_frontmatter_review_status(thread_rows)
    print(f"\nApplied:")
    print(f"  grouping rows confirmed:      {len(item_ids)}")
    print(f"  threads set review=confirmed: {len(thread_ids)}")
    print(f"  audit rows written:           1 (type=bulk_accept)")
    print(f"  .md frontmatter pre-synced:   {patched}")
    return note


def run(min_confidence, apply):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    print(f"DB: {DB_PATH}\n")
    rows = select_candidates(cur, min_confidence)
    n_rows, n_threads = print_plan(rows, min_confidence)

    if not apply:
        print("\n[DRY RUN] Nothing written. Re-run with --apply to commit.")
        conn.close()
        return

    if n_rows == 0:
        print("\nNothing to accept — clean no-op.")
        conn.close()
        return

    apply_changes(conn, rows, min_confidence)
    conn.close()

    print("\nRendering so frontmatter reflects the new review_status values...")
    rc, out, overrides = run_render()
    for line in out.strip().splitlines():
        print(f"  | {line}")
    if rc != 0:
        raise SystemExit(f"Render failed (exit {rc}) — see output above.")
    if overrides not in (0, None):
        print(
            f"\nWARNING: render reported {overrides} sync-back overrides — expected 0. "
            "Investigate before trusting this run."
        )
    else:
        print("\nSync-back conflicts: 0 (as expected). Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk-accept high-confidence review items.")
    parser.add_argument(
        "--accept-groupings", action="store_true",
        help="Accept pending thread_grouping rows (the only supported bulk action).",
    )
    parser.add_argument("--min-confidence", type=float, default=0.95)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write changes. Omit for a dry run (the default).",
    )
    args = parser.parse_args()

    if not args.accept_groupings:
        raise SystemExit(
            "Nothing to do. Pass --accept-groupings (the only supported bulk action).\n"
            "Example: python3 pipeline/bulk_review.py --accept-groupings --min-confidence 0.95 --apply"
        )
    run(args.min_confidence, args.apply)
