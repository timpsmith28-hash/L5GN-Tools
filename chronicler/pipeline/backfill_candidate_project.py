"""backfill_candidate_project.py -- Command Deck prototype, Task 1 step 3.

Populates `review_queue.candidate_project` / `.rival_project` on the ~500
pending rows that predate those columns (COWORK_BRIEF_command_deck_proto.md).

WHY A BACKFILL, NOT A RELINK RE-RUN
------------------------------------
`relink.apply_decision` now writes both columns going forward (this brief's
Task 1 step 2). Re-running `relink.py --apply` would also re-score every
thread against current evidence and could change *which* rows are queued --
a much bigger blast radius on a vault that was just aligned. This script
instead re-derives the id that was ALREADY decided, from the row's own
`note` text.

WHY THE NOTE IS TRUSTWORTHY
----------------------------
`relink.apply_decision`'s `lbl(pid)` helper writes notes in the exact shape
`f"{pid} ({rollup_label(registry, pid)})"` -- the registry id appears
verbatim, immediately followed by " (" opening the breadcrumb. This is not a
display-label fuzzy-match problem; it is a fixed-format parse:

    project_link    "suggest -> <id> (<breadcrumb>) (adjusted=...); ..."
    link_ambiguous  "ambiguous: <id> (<breadcrumb>) (adjusted=...; ...) VS
                      <id> (<breadcrumb>) (adjusted=...; ...)"
    link_downgrade  "downgrade: ...; new evidence points to <id> (<breadcrumb>)
                      (adjusted=...); ..."

Every parsed id is still validated against the live registry before being
written -- an id the note names but the registry no longer carries a real
answer is reported UNRESOLVED, never guessed (brief: "Unresolvable rows must
be reported, never guessed").

Standing rules: dry-run is the default; --apply required to write. Only rows
with `candidate_project IS NULL` are touched, so a second run is a no-op on
already-backfilled rows (re-runnable, idempotent). UTF-8, UTC ISO-8601,
single write transaction.

Usage:
    python3 pipeline/backfill_candidate_project.py            # dry-run: report only
    python3 pipeline/backfill_candidate_project.py --apply    # write resolved rows
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from db import get_connection, resolve_registry_path

_PIPE = Path(__file__).resolve().parent
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

import relink  # noqa: E402  (load_registry, used for id validation)

# Row types the S6 relink pass queues with a candidate project in the note.
CANDIDATE_TYPES = ("project_link", "link_ambiguous", "link_downgrade")

# Anchored on `lbl()`'s exact shape: the id sits immediately before " (".
_SUGGEST_RE = re.compile(r"^suggest -> (\S+) \(")
_AMBIG_BEST_RE = re.compile(r"^ambiguous: (\S+) \(")
_AMBIG_RIVAL_RE = re.compile(r"VS (\S+) \(")
_DOWNGRADE_RE = re.compile(r"points to (\S+) \(")


def parse_note(row_type: str, note: str) -> tuple[str | None, str | None, str | None]:
    """Return (candidate_id, rival_id, reason_if_unresolved).

    reason is None on success; a short string explaining why nothing could be
    parsed/resolved otherwise. Never guesses -- an unmatched pattern is
    reported, not silently skipped.
    """
    note = note or ""
    if row_type == "project_link":
        m = _SUGGEST_RE.search(note)
        if not m:
            return None, None, "note does not match the 'suggest -> <id> (' shape"
        return m.group(1), None, None

    if row_type == "link_ambiguous":
        mb = _AMBIG_BEST_RE.search(note)
        mr = _AMBIG_RIVAL_RE.search(note)
        if not mb or not mr:
            return None, None, "note does not match the 'ambiguous: <id> ( ... VS <id> (' shape"
        return mb.group(1), mr.group(1), None

    if row_type == "link_downgrade":
        m = _DOWNGRADE_RE.search(note)
        if not m:
            return None, None, "note does not match the '... points to <id> (' shape"
        return m.group(1), None, None

    return None, None, f"unhandled row type {row_type!r}"


def find_backfillable(conn) -> list:
    placeholders = ",".join("?" for _ in CANDIDATE_TYPES)
    return conn.execute(
        f"SELECT item_id, type, note FROM review_queue "
        f"WHERE candidate_project IS NULL AND type IN ({placeholders})",
        CANDIDATE_TYPES,
    ).fetchall()


def run(apply: bool) -> int:
    conn = get_connection()
    try:
        # relink.load_registry() reads the module-level relink.REGISTRY_PATH;
        # point it at the same path db.resolve_registry_path() resolves so this
        # backfill validates against the same registry relink used.
        relink.REGISTRY_PATH = resolve_registry_path()
        registry = relink.load_registry()

        rows = find_backfillable(conn)
        resolved, unresolved = [], []

        for row in rows:
            cand, rival, reason = parse_note(row["type"], row["note"])
            if reason is not None:
                unresolved.append((row["item_id"], row["type"], reason))
                continue
            if cand not in registry:
                unresolved.append(
                    (row["item_id"], row["type"],
                     f"parsed candidate id {cand!r} not in current registry"))
                continue
            if rival is not None and rival not in registry:
                unresolved.append(
                    (row["item_id"], row["type"],
                     f"parsed rival id {rival!r} not in current registry"))
                continue
            resolved.append((row["item_id"], cand, rival))

        print("=" * 68)
        print(f"backfill_candidate_project  ({'APPLY' if apply else 'DRY-RUN'})")
        print("=" * 68)
        print(f"pending rows missing candidate_project: {len(rows)}")
        print(f"  resolved:   {len(resolved)}")
        print(f"  unresolved: {len(unresolved)}")
        if unresolved:
            print("\nUNRESOLVED (reported, never guessed):")
            for item_id, rtype, reason in unresolved:
                print(f"  item_id={item_id:<6} type={rtype:<14} {reason}")

        if not apply:
            print("\n(dry-run -- nothing written. Re-run with --apply to persist.)")
            return len(unresolved)

        conn.execute("BEGIN")
        for item_id, cand, rival in resolved:
            conn.execute(
                "UPDATE review_queue SET candidate_project=?, rival_project=? "
                "WHERE item_id=?",
                (cand, rival, item_id),
            )
        conn.commit()
        print(f"\napplied: {len(resolved)} row(s) backfilled.")
        if unresolved:
            print(f"{len(unresolved)} row(s) left unresolved -- see list above; "
                  "re-run after fixing the cause (e.g. a stale registry).")
        return len(unresolved)
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Backfill review_queue.candidate_project/rival_project from "
                     "existing note text (Command Deck prototype, Task 1).")
    ap.add_argument("--apply", action="store_true",
                    help="Write resolved rows (default is dry-run, report only).")
    args = ap.parse_args()
    run(args.apply)
