"""
Single pipeline runner — QoL build B2.

Replaces the five-invocations-in-the-right-order periodic loop with one
command. Pure orchestration: ordering, per-stage summaries, stop-on-failure,
and treating "no new input for this source" as a skip rather than an error.
Each underlying script is already idempotent; this adds nothing clever.

Stage order (design 4 / 9.2):
    normalize_claude -> normalize_gemini_personal -> reconcile_gemini
    -> group_fallback -> suggest_close -> render_md

normalize_gemini_work is deliberately NOT in the chain: the work account is a
closed, historical corpus (design 9.2), ingested once and never revisited.

Behaviour:
  * Missing input (e.g. no new Takeout since last run, empty scraped_gemini/)
    => that stage is SKIPPED with a note. The common case is "re-run
    everything, only some sources have new data", so this must not fail.
  * A stage that actually FAILS (non-zero exit for any other reason) STOPS the
    whole chain immediately — we never run reconcile/group/render on top of a
    half-finished normalize (loud-failure principle, design 1).
  * Per stage: one line of new/changed/skipped, taken from the same
    ingestion_log numbers each script already records.

Sync-back ordering (data-integrity rule):
    Every stage in the full chain WRITES the DB, so by the time render runs the
    on-disk .md frontmatter is older than the DB. render is therefore run
    DB->file only (`--no-syncback`) in the full chain — reading stale frontmatter
    back would clobber fresh links (this once wiped 133 evidence links). The ONE
    time file->DB sync-back is wanted is `--render-only`, i.e. re-rendering to
    absorb genuine Obsidian edits; only that mode runs render with sync-back ON.

Usage:
    python3 pipeline/run_pipeline.py                 # full loop (render DB->file only)
    python3 pipeline/run_pipeline.py --render-only    # re-render WITH sync-back (after Obsidian edits)
    python3 pipeline/run_pipeline.py --skip-takeout --skip-reconcile
    python3 pipeline/run_pipeline.py --skip-claude --skip-takeout --skip-reconcile --skip-group --skip-suggest-close
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT

# Canonical input paths, imported from the scripts themselves so there is one
# source of truth (these imports don't execute anything — run() is __main__-gated).
from normalize_claude import CONVERSATIONS_PATH
from normalize_gemini_personal import DEFAULT_INPUT as TAKEOUT_INPUT
from reconcile_gemini import DEFAULT_SCRAPED_DIR

PIPELINE_DIR = Path(__file__).resolve().parent


def has_takeout():
    return TAKEOUT_INPUT.exists()


def has_claude():
    return CONVERSATIONS_PATH.exists()


def has_scraped():
    return DEFAULT_SCRAPED_DIR.exists() and any(DEFAULT_SCRAPED_DIR.glob("*.json"))


# Each stage: key (for --skip-<key>), label, script filename, argv, and an
# input_check (None => DB-only stage, always runs).
STAGES = [
    ("claude",        "normalize_claude",          "normalize_claude.py",          [], has_claude),
    ("takeout",       "normalize_gemini_personal", "normalize_gemini_personal.py", [], has_takeout),
    ("reconcile",     "reconcile_gemini",          "reconcile_gemini.py",          [], has_scraped),
    ("group",         "group_fallback",            "group_fallback.py",            [], None),
    ("suggest-close", "suggest_close",             "suggest_close.py",             [], None),
    ("render",        "render_md",                 "render_md.py",                 [], None),
]


def max_batch_id(cur):
    row = cur.execute("SELECT COALESCE(MAX(batch_id), 0) AS m FROM ingestion_log").fetchone()
    return row["m"]


def summarize_from_log(cur, since_batch_id):
    """Sum the ingestion_log rows this stage just wrote (there may be several,
    e.g. reconcile writes one per skeleton). Returns a one-line summary or None
    if the stage wrote no log rows."""
    rows = cur.execute(
        "SELECT rows_new, rows_changed, rows_skipped FROM ingestion_log WHERE batch_id > ?",
        (since_batch_id,),
    ).fetchall()
    if not rows:
        return None
    new = sum(r["rows_new"] or 0 for r in rows)
    changed = sum(r["rows_changed"] or 0 for r in rows)
    skipped = sum(r["rows_skipped"] or 0 for r in rows)
    batches = f" across {len(rows)} batches" if len(rows) > 1 else ""
    return f"+{new} new / {changed} changed / {skipped} skipped{batches}"


def summarize_render(out):
    rendered = re.search(r"Threads rendered:\s*(\d+)", out)
    overrides = re.search(r"Sync-back overrides applied:\s*(\d+)", out)
    parts = []
    if rendered:
        parts.append(f"{rendered.group(1)} threads rendered")
    if overrides:
        parts.append(f"{overrides.group(1)} sync-back overrides")
    return ", ".join(parts) if parts else "(see output)"


def run_stage(script, argv):
    proc = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / script), *argv],
        cwd=str(PIPELINE_DIR),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout or ""), (proc.stderr or "")


def run(active_keys, render_syncback=False):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 68)
    print("Chronicler pipeline runner")
    print("=" * 68)

    ran = skipped = 0
    for key, label, script, argv, input_check in STAGES:
        prefix = f"[{label}]"
        if key not in active_keys:
            print(f"{prefix} skipped (--skip-{key} / not in this run)")
            skipped += 1
            continue
        if input_check is not None and not input_check():
            print(f"{prefix} skipped (no input available)")
            skipped += 1
            continue

        # The full chain wrote the DB, so render must go DB->file only. Only a
        # --render-only pass (render_syncback=True) reads Obsidian edits back.
        if key == "render" and not render_syncback:
            argv = [*argv, "--no-syncback"]

        before = max_batch_id(cur)
        rc, out, err = run_stage(script, argv)

        if rc != 0:
            print(f"{prefix} FAILED (exit {rc}). Stopping the chain.")
            tail = (err or out).strip().splitlines()[-15:]
            for line in tail:
                print(f"    | {line}")
            conn.close()
            raise SystemExit(
                f"\nPipeline halted at '{label}' — nothing downstream was run. "
                "Fix the cause and re-run (earlier stages are idempotent)."
            )

        # Fresh connection view of the log rows the child just committed.
        summary = (
            summarize_render(out) if key == "render"
            else summarize_from_log(cur, before)
        )
        print(f"{prefix} ok — {summary or 'no new rows'}")
        ran += 1

    conn.close()
    print("-" * 68)
    print(f"Done. {ran} stage(s) ran, {skipped} skipped.")


def resolve_active_keys(args):
    all_keys = [s[0] for s in STAGES]
    if args.render_only:
        return {"render"}
    skipped = {k for k in all_keys if getattr(args, f"skip_{k.replace('-', '_')}")}
    return set(all_keys) - skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Chronicler pipeline end to end.")
    parser.add_argument("--render-only", action="store_true",
                        help="Skip everything except the final render (use after Obsidian edits).")
    parser.add_argument("--skip-claude", action="store_true")
    parser.add_argument("--skip-takeout", action="store_true")
    parser.add_argument("--skip-reconcile", action="store_true")
    parser.add_argument("--skip-group", action="store_true")
    parser.add_argument("--skip-suggest-close", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    # sync-back file->DB is wanted ONLY when re-rendering to absorb Obsidian edits.
    run(resolve_active_keys(args), render_syncback=args.render_only)
