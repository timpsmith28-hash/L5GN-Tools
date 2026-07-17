"""
One-time bootstrap helper — NOT part of the regular pipeline.

Context: item 10 (suggest_close.py) is being activated for the first time
against a vault that was already fully rendered under item 7 before item 10
existed. Every existing .md file therefore has `suggested_close: false`
baked in from that earlier render, which is not a deliberate human edit —
it's just the default that existed before this feature did.

Per design doc 13.3, render_md.py's sync-back treats *any* file/DB mismatch
identically regardless of cause ("file wins, unconditionally — even if the
DB value also changed since the last render, e.g. an automated pass just
touched it"). Run render_md.py as-is right now and it will faithfully do
its job: read the stale `false` out of every file and stomp the fresh `true`
suggest_close.py just computed, back to false. That's not a bug in
render_md.py — it's exactly what 13.3 says should happen for a genuine
file/DB disagreement. The problem is only that these particular files don't
represent a disagreement at all; they predate the DB value that would have
made them agree.

This script closes that gap once: for every thread where the DB's
suggested_close is true but the on-disk file still says false, patch just
that one field in place (reusing render_md.py's own parse_frontmatter /
yaml.safe_dump round-trip, so formatting matches exactly what render_md.py
itself would produce). After this, file and DB agree, so the next normal
render_md.py run will see zero sync-back conflicts and every future human
edit to suggested_close will be honored exactly as 13.3 intends.

Usage:
    python3 pipeline/_presync_suggested_close.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

from db import get_connection, init_db
from render_md import (
    FRONTMATTER_FIELD_ORDER,
    find_existing_md_files,
    normalize_tags,
    parse_frontmatter,
)


def run():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    patched = 0
    checked = 0
    for path in find_existing_md_files():
        fm, body = parse_frontmatter(path)
        if not fm or "thread_id" not in fm:
            continue
        checked += 1
        thread_id = fm["thread_id"]
        db_row = cur.execute(
            "SELECT suggested_close FROM threads WHERE thread_id=?", (thread_id,)
        ).fetchone()
        if db_row is None:
            continue

        db_value = bool(db_row["suggested_close"])
        file_value = bool(fm.get("suggested_close"))
        if db_value == file_value:
            continue  # already agrees — nothing to bootstrap here

        fm["suggested_close"] = db_value
        # normalize tags the same way render_thread does, so re-dump is stable
        if "tags" in fm:
            fm["tags"] = normalize_tags(fm["tags"])
        fm_ordered = {k: fm[k] for k in FRONTMATTER_FIELD_ORDER if k in fm}
        fm_yaml = yaml.safe_dump(fm_ordered, sort_keys=False, allow_unicode=True).strip()
        new_text = f"---\n{fm_yaml}\n---\n{body}"
        path.write_text(new_text, encoding="utf-8")
        patched += 1

    conn.close()
    print(f"Files checked: {checked}")
    print(f"Files patched (bootstrapped suggested_close to match DB): {patched}")


if __name__ == "__main__":
    run()
