# Restart — prepared 2026-09-04, for the 2026-09-03 thin-slice round (Cards C, D)

Run against `CONVENTION_design_thread_restart.md`, from a Cowork sandbox on
`LucasGoonPC`'s mounted repo. **It is an agenda, not a report** (§5). Everything
below was read today; nothing is carried from `restart_2026-09-03.md`'s prose
except where it names a file that was then read directly (§2 — read, never
recall, including a restart prompt written on an earlier day).

**One honest gap, closed by the operator during this same sitting.** This
thread has no git access — the environment hazard ("never run plain git
against a mounted Windows repo from a sandbox") holds. The restart prompt's
own Task 1 (`git log --oneline 8a61aec..HEAD`, `git status`) could not be run
from here; the operator ran both on Windows and pasted the output. **Result:
exactly one commit above `8a61aec` — `5b33fd9`, "docs(uat): walk the
conformance reader" — which is precisely the commit the restart prompt itself
named as already known ("plus one commit made immediately after it"). Nothing
above this prompt's own knowledge exists.** `git status`: clean, one commit
ahead of `origin/main`, no untracked files besides this note being drafted.
Every other git fact below still comes from the operator's shell, not this
sandbox — see "What could not be read."

---

## Stage 1 — estate freshness

```
34.9h old (generated_at=2026-09-02T13:06:52+01:00) -- STALE
```

Verbatim. **Stale, so stages 2-4 below are read with that caveat.** No rebuild
was taken from this thread — rebuilding is a decision, not a side effect of
reading (§8), and `run.py build` calls `toolkit_git_info()`, which is git
against the mounted repo. That is the sandbox's own hazard, so the rebuild is
left to the operator, on Windows: `python run.py build`.

## Stages 2 and 3 — pending decisions

**Reported by repo, as every prior restart has.** `docs/DECISIONS.md` carries
no program/project axis; the registry join that would supply it is still
unbuilt (fourth consecutive restart recording this).

Counted directly, not recalled: **60 entries, 0 at `proposed`.** Matches the
restart prompt's claim, verified rather than trusted. `data/decision_drafts/`
holds nothing unappended; `data/decisions_draft/` does not exist. The
two-directory hazard stays resolved.

**Work-estate rulings are unread, by construction** (0051) — named, not
omitted.

## Stage 4 — board

**The program/project board does not exist**, same as every prior restart;
the docs board (documents, not programs) is what was read, and is reported as
that, not substituted for the missing one.

**The gate, counted from `verify.py`, not recalled: 13 auditors (lines
15-29), 82 testers (lines 31-114).** Matches the restart prompt's figure —
verified.

**Card C — `staleness_feeds` — re-verified against the tree, per its own
header's demand:**

- `chronicler/review/project_wizard.py:95` — `MANIFEST_SCHEMA_VERSION = 1`,
  unchanged. The brief's precondition state (schema v1, no
  `staleness_feed` section) still matches the tree.
- `chronicler/review/desk.py` — still two hard-coded triggers in `cards()`
  (no provider loop), `VALID_RULINGS = frozenset({"rebuild", "snooze",
  "dismiss"})` unextended. Nothing in this brief has been built.
- **Hard precondition satisfied, and this is new since the brief was
  written:** `docs/UAT_desk_stale_card_results.md` — the trial reached ten,
  D7/D8/D9 closed 2026-08-28, and its 2026-09-02 correction (removing
  `gate=`) left the "trial is closed" verdict untouched. The brief's own
  gate — *"Nothing in this brief is built while that trial runs"* — is clear.
- **0050 is accepted** (confirmed in the stage-2/3 count above, not assumed),
  so the brief's "Ratify before code" condition is also clear. Both hard
  gates on Card C are open.
- **The rewrite is real and un-sized by this reading.** Seven tasks: schema
  v2 validation, the `cards()` provider restructure, source-declared options
  + per-option `POST /api/desk/rule` validation, the workcycle feed script
  reading `DECISIONS.md`'s own date/status lines, feed health reporting,
  a `feed_error` event, plus a second allowlisted fixture repo for UAT. That
  is a full build round on its own before Card D is touched — the brief's own
  "size the rewrite before starting it" instruction is not yet discharged by
  this reading, only informed by it.

**Card D — the promotion step — has no brief, confirmed** (no
`COWORK_BRIEF_` file matches; `brief-scribe` is the round's first act).
Two checks the restart prompt asked for, both now done:

- **No overlap with `COWORK_BRIEF_validation_ratify.md`.** That brief is a
  work-rig round (its own header: "Runs on: the work rig"), about a pending
  *review-batch* feed with a write-back and a content-digest refusal —
  different subsystem, different rig. Its own hard precondition is Card C
  closing green, which is a dependency in the other direction, not an
  overlap.
- **0059 collides with Card D's subsystem, and this is worth carrying into
  the brief.** 0059 (accepted 2026-09-02) amends 0048 clause 2: a card
  declares completeness rather than being refused for lacking a field, and a
  fourth ruling kind, `insufficient`, joins `rebuild`/`snooze`/`dismiss`.
  `desk.py`'s `VALID_RULINGS` (confirmed above) still has three. Card D reads
  ruling history out of `data/desk/events.jsonl` via `desk.latency_summary()`
  to detect a repeated ruling worth promoting — if it is built against
  today's three-kind vocabulary and 0059 lands mid-round, an `insufficient`
  ruling is either invisible to the promotion logic or breaks it. The brief
  should say which ruling kinds it reads and what an unrecognised kind does,
  rather than assuming the vocabulary is closed.

## Stage 5 — inbound

**Nothing new.** `../WizForge/Work_Bridge/to-personal/` holds the same four
files the 2026-09-02 restart already read (newest dated 2026-08-27); nothing
has arrived since. No context pack channel is reachable from this thread to
apply the §6.1 *open* test to. Nothing is named as owed a reply.

**`data/git_warden/` holds four unswept drafts** (`conformance_report-1`,
`conformance_walk-1`, `ratify_0058_0059-1`, `restart_2026-09-02-1`, all dated
2026-09-02) — not stage-5 inbound, but written down here because it exists
nowhere else in this note: whether they are spent is a `git log` question
this thread cannot answer, named under "what could not be read" below.

## What could not be read, by name

- **`git`, from this sandbox, as a standing hazard** — `log`/`status` were
  supplied by the operator's own Windows shell rather than read directly here
  (above). Whether the four `data/git_warden/` drafts are spent (a commit
  subject matching one) is still unread — the 50-commit log the operator
  pasted does not show a `commit(git):` or similarly named subject for any of
  `conformance_report-1` / `conformance_walk-1` / `ratify_0058_0059-1` /
  `restart_2026-09-02-1`, so at a glance none look spent, but that reading
  needs `commit-scribe`'s own sweep, not eyeballing.
- **The live vault.** Unreachable from a Cowork sandbox; reads as unknown
  (0050).
- **Work-side decision logs.** Behind the wall (0051).

## Decided during the restart, because it existed nowhere else

Nothing. No input this session existed only in memory; everything above came
from a file or a script's own output.

## Agenda for the round that follows

**Task 1 is discharged** — the operator's git log/status confirm nothing
exists above the restart prompt's own knowledge; there is no catch-up to do.
On Card C: size the seven-task rewrite explicitly before opening it, and say
on the day whether the round holds both cards or Card C alone — its own
brief predicts this is where past attempts slipped. On Card D: write the
brief first (`brief-scribe`), naming the ruling-vocabulary question above as
an open design point rather than discovering it mid-build. **Both hard
preconditions on Card C are clear and this reading found nothing that
reopens them.**
