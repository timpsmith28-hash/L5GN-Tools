"""
Single pipeline runner — QoL build B2.

Replaces the five-invocations-in-the-right-order periodic loop with one
command. Pure orchestration: ordering, per-stage summaries, stop-on-failure,
and treating "no new input for this source" as a skip rather than an error.
Each underlying script is already idempotent; this adds nothing clever.

Stage order (design 4 / 9.2):
    normalize_claude -> normalize_gemini_personal -> normalize_md_transcript
    -> reconcile_gemini -> group_fallback -> suggest_close -> set_substantive
    -> relink -> render_md

relink (S6) is folded in just before render so fresh threads are linked to
projects in the same pass that ingests them (ARCHITECTURE §7 standing fix); it is
gated on the project registry existing. **If that gate fires the run is DEGRADED
and exits 2** — see CONFIG_GATED. This docstring claimed "skips cleanly + loudly"
from the day the stage was added until 2026-08-31, during which the skip printed
the same line as an absent Takeout export and the chain finished green.

normalize_gemini_work is deliberately NOT in the chain: the work account is a
closed, historical corpus (design 9.2), ingested once and never revisited.

Behaviour:
  * Missing input (e.g. no new Takeout since last run, empty scraped_gemini/)
    => that stage is SKIPPED with a note. The common case is "re-run
    everything, only some sources have new data", so this must not fail.
  * A stage that actually FAILS (non-zero exit for any other reason) STOPS the
    whole chain immediately — we never run reconcile/group/render on top of a
    half-finished normalize (loud-failure principle, design 1).
  * Per stage: one line. Most stages record their work in ingestion_log and are
    summarised from it. `relink` and `render` do not write that table and carry
    their own summariser (STAGES' sixth field), because "reads ingestion_log"
    and "has no summariser" were the same value until 2026-08-31 and a stage
    that logged nothing was reported as having done nothing.
  * A stage that ran but produced no line its summariser recognises reports
    OUTCOME UNREPORTED and degrades the run. Unknown is not empty.

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
from normalize_md_transcript import RAW_DIR as MD_TRANSCRIPT_DIR
# relink (S6) is stdlib-only; imported as a module so its REGISTRY_PATH is looked
# up live (the stage's input-gate), not frozen at import time.
import relink as _relink

PIPELINE_DIR = Path(__file__).resolve().parent


def has_takeout():
    return TAKEOUT_INPUT.exists()


def has_claude():
    return CONVERSATIONS_PATH.exists()


def has_scraped():
    return DEFAULT_SCRAPED_DIR.exists() and any(DEFAULT_SCRAPED_DIR.glob("*.json"))


def has_md_transcripts():
    return MD_TRANSCRIPT_DIR.exists() and any(MD_TRANSCRIPT_DIR.glob("*.md"))


def has_registry():
    """relink's input is the project registry (built by build_registry.py).

    **Absent is NOT the same fact as the gates above.** `has_takeout` and
    friends answer "is there new source data" -- absence there is the ordinary
    case the runner was built for. This one answers "is this machine configured
    to link at all", and absence is a configuration defect wearing an absent
    source's clothes. Until 2026-08-31 both printed the same line and this
    function's own docstring claimed the skip was "clean and loud"; it was
    neither, and `relink.py`'s loud SystemExit was never reached because the
    gate fired first. See CONFIG_GATED below for how the two are now told apart.
    """
    return _relink.REGISTRY_PATH.is_file()


#: Stage keys whose input_check answers a CONFIGURATION question rather than a
#: "is there new data" question. Skipping one is a degraded run, not a normal
#: one: the chain completed without doing the thing it was run to do, and
#: anything measured from it is measuring something else. A stage listed here
#: that skips makes the whole run exit non-zero.
#:
#: 0048 clause 4 is the reason this is not merely a louder print. A warning
#: nobody has to act on is a check that cannot fail, and two rounds nearly
#: published a coverage figure taken from a chain whose linking stage never ran.
CONFIG_GATED = {"relink"}


def skip_note(key: str) -> str:
    """The loud block for a config-gated stage that could not run.

    Names the path that was looked at, says the absence is configuration rather
    than missing data, and states the consequence in the terms someone reading
    the log actually cares about -- that no figure from this run describes
    linking. INTENT §5 refuses a rule that survives on the operator's memory;
    this is the line that stops it having to.
    """
    if key != "relink":
        return ""
    return (
        f"\n    !! relink DID NOT RUN. This is a configuration fault, not an "
        f"absent source.\n"
        f"       Looked for the project registry at:\n"
        f"         {_relink.REGISTRY_PATH}\n"
        f"       Nothing on this run linked a thread to a project. Any coverage\n"
        f"       figure taken from this run measures the corpus, NOT the linking\n"
        f"       -- do not publish one (DECISIONS 0048 clause 4).\n"
        f"       Fix: build the registry (`build_registry.py`), or point\n"
        f"       CHRONICLER_REGISTRY_PATH at the file the pipeline should read.\n"
        f"       `--skip-relink` silences this deliberately and exits 0.\n")


# Each stage: key (for --skip-<key>), label, script filename, argv, and an
# input_check (None => DB-only stage, always runs).
#
# The sixth field is the stage's SUMMARISER: a callable taking the child's
# stdout, or None meaning "this stage records its work in ingestion_log, read it
# from there". Added 2026-08-31, because `None` had been doing two jobs -- most
# stages genuinely log, and relink genuinely does not, and the runner could not
# tell the difference so it reported relink's outcome as "no new rows" forever.
STAGES = [
    ("claude",        "normalize_claude",          "normalize_claude.py",          [], has_claude,        None),
    ("takeout",       "normalize_gemini_personal", "normalize_gemini_personal.py", [], has_takeout,       None),
    ("md-transcript", "normalize_md_transcript",   "normalize_md_transcript.py",   [], has_md_transcripts, None),
    ("reconcile",     "reconcile_gemini",          "reconcile_gemini.py",          [], has_scraped,       None),
    ("group",         "group_fallback",            "group_fallback.py",            [], None,              None),
    ("suggest-close", "suggest_close",             "suggest_close.py",             [], None,              None),
    ("substantive",   "set_substantive",           "set_substantive.py",           [], None,              None),
    # relink (S6): links freshly-ingested threads to projects. Runs AFTER the
    # normalizers/reconcile have landed threads and set_substantive has flagged
    # them, and BEFORE render so the rendered .md reflects the new links. Runs
    # with --apply (dry-run is relink's own default). Idempotent and safe every
    # pass: winners become 'evidence' (locked, skipped next run) and human-ruled
    # threads are never re-touched. Gated on the registry file existing.
    ("relink",        "relink",                    "relink.py",                    ["--apply"], has_registry, lambda out: summarize_relink(out)),
    ("render",        "render_md",                 "render_md.py",                 [], None,              lambda out: summarize_render(out)),
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


def summarize_relink(out):
    """relink's own account of what it did, parsed from its report.

    relink writes **no `ingestion_log` rows at all** -- verified, not assumed:
    the module contains zero references to that table. It was nonetheless
    registered as a log-summarised stage, so `summarize_from_log` found nothing
    and the runner printed `[relink] ok -- no new rows` after every run,
    whatever relink had done. Not merely vacuous: wrong in the reassuring
    direction, and the stage is the one the estate's coverage thesis rests on.

    `ingestion_log` is the wrong home for it rather than a missing feature.
    Its columns are rows_new / rows_changed / rows_skipped -- an ingestion's
    units. relink's units are auto_link, suggest, ambiguous and downgrade, and
    flattening four link decisions into "changed" would report a number that is
    true and answers nobody's question.

    So relink joins render as a stage that reports through its own output.
    Returns None when the expected line is absent, and the caller says so out
    loud rather than substituting a reassuring default -- a summariser that
    silently degrades to "nothing happened" is the defect this replaces.
    """
    applied = re.search(r"Applied\.\s*(\d+)\s*thread\(s\) changed / queued", out)
    if applied:
        n = int(applied.group(1))
        return (f"{n} thread(s) linked / queued" if n
                else "0 threads changed (every thread already locked or ruled)")
    if "[DRY RUN]" in out:
        # The stage is wired with --apply, so this means the flag was lost.
        # Degrading, not merely narrating: nothing was linked, which is the
        # same outcome as the stage not running, and it must not exit 0.
        return ("DRY RUN -- nothing was written. The stage is configured with "
                "--apply, so this is a wiring fault, not a no-op.", False)
    return None


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
    # utf-8 on BOTH sides of the pipe, deliberately.
    #
    # Without `encoding=`, `text=True` decodes the child with
    # locale.getpreferredencoding() -- cp1252 on Windows. relink prints thread
    # titles and this estate's titles carry emoji, so this fired on a real stage
    # on 2026-08-27.
    #
    # It fails in TWO modes, and the quiet one is the worse one. Measured:
    #
    #   U+1F601  bytes f0 9f 98 81  -> UnicodeDecodeError. 0x81 is one of
    #                                  cp1252's five undefined slots (81 8D 8F
    #                                  90 9D). The capture is LOST.
    #   U+1F600  bytes f0 9f 98 80  -> no error; decodes to four mojibake
    #                                  characters. The tail survives, wrong.
    #   U+2018   bytes e2 80 98     -> no error; three mojibake characters.
    #
    # So which emoji a thread title happens to carry decides whether the chain
    # loses the diagnostic or silently garbles it. run() prints a failing
    # stage's diagnostic as the tail of (err or out), so mode one reports an
    # exit code with no tail at all -- the chain's single diagnostic surface --
    # and mode two hands back a plausible wrong answer, which INTENT section 5
    # calls the worst thing this system can produce.
    #
    # errors="replace" is the deliberate half: a diagnostic that survives
    # slightly mangled beats one that does not survive. PYTHONIOENCODING makes
    # the child emit utf-8 rather than whatever its locale offers, so the parent
    # is not left guessing.
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / script), *argv],
        cwd=str(PIPELINE_DIR),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
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
    degraded = []          # config-gated stages that could not run (0048 cl.4)
    for key, label, script, argv, input_check, summarizer in STAGES:
        prefix = f"[{label}]"
        if key not in active_keys:
            print(f"{prefix} skipped (--skip-{key} / not in this run)")
            skipped += 1
            continue
        if input_check is not None and not input_check():
            if key in CONFIG_GATED:
                # Not "no input available". The distinction is the whole card:
                # an absent source is the ordinary case, an unconfigured stage
                # is a run that completed without doing its job.
                print(f"{prefix} SKIPPED -- NOT CONFIGURED")
                print(skip_note(key))
                degraded.append(label)
            else:
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
        stage_ok = True
        if summarizer is not None:
            summary = summarizer(out)
            # A summariser may return `(text, ok)` to say "I understood the
            # output, and it says this stage did not do its job". A plain string
            # means ok. Without this, a relink that silently lost its --apply
            # flag reported a clear diagnosis on a run that still exited 0 --
            # a correct sentence nobody downstream could act on.
            if isinstance(summary, tuple):
                summary, stage_ok = summary
                if not stage_ok:
                    degraded.append(f"{label} ({summary.split(' --')[0].strip()})")
            if summary is None:
                # A stage that reports through its own output and did not say
                # anything recognisable has an UNKNOWN outcome, not an empty
                # one. Substituting "no new rows" here is exactly the bug this
                # field was added to remove, and it would hide a changed child.
                #
                # Not printed as "ok" either. The exit code was zero and that is
                # all that is known; asserting "ok" alongside "outcome unknown"
                # in one line is the sentence a skimmer reads as success.
                print(f"{prefix} RAN, OUTCOME UNREPORTED -- {label} exited 0 but "
                      f"produced no line this runner recognises. What it did is "
                      f"unknown. This is not 'nothing happened' (DECISIONS 0048 "
                      f"clause 4).")
                degraded.append(f"{label} (unreported)")
                ran += 1
                continue
        else:
            summary = summarize_from_log(cur, before) or "no new rows"
        # "ok" is an assertion, so it is only printed where one can be made.
        # A stage that ran and did not do its job gets a different word, for
        # the same reason OUTCOME UNREPORTED does: the line a skimmer reads
        # must not say the opposite of the line beneath it.
        print(f"{prefix} {'ok —' if stage_ok else 'RAN, DID NOT APPLY —'} {summary}")
        ran += 1

    conn.close()
    print("-" * 68)
    print(f"Done. {ran} stage(s) ran, {skipped} skipped.")
    if degraded:
        # Exit non-zero. A chain that completed without linking is a degraded
        # run and must not read as success to anything downstream -- a script,
        # a scheduled task, or a person skimming for the last line.
        print()
        print(f"DEGRADED RUN: {', '.join(degraded)}. "
              f"The chain completed; it did not do everything it was run to do.")
        raise SystemExit(2)


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
    parser.add_argument("--skip-md-transcript", action="store_true")
    parser.add_argument("--skip-reconcile", action="store_true")
    parser.add_argument("--skip-group", action="store_true")
    parser.add_argument("--skip-suggest-close", action="store_true")
    parser.add_argument("--skip-substantive", action="store_true")
    parser.add_argument("--skip-relink", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()
    # sync-back file->DB is wanted ONLY when re-rendering to absorb Obsidian edits.
    run(resolve_active_keys(args), render_syncback=args.render_only)
