# Cowork report — Phase 1: the Decision Desk's first card — stale-output triage

Built against `docs/COWORK_BRIEF_desk_stale_card.md`, Tasks 0–3, plus both
of its dated addenda, on `LucasGoonPC`. Commit series below; current HEAD
`fb6fa5c`.

**This report is written ahead of the brief's own schedule, at Tim's
explicit direction on 2026-08-19, and updated 2026-08-20.** The brief's
Reporting section says this document gets written "after the trial, not
after the build — the trial is the round," on an open-ended trial that
runs until ten real cards are ruled. As of the 2026-08-20 update the trial
has produced four ruled cards, all on the `uat-decisions-fixture` fixture
stood up 2026-08-19. The call to write now rather than wait:
enough real adaptation has already happened mid-build — a structural flaw
found and cut before the trial started, a measurement bug found and fixed
one day in, a UI ordering bug found and fixed live during UAT — that the
history is worth capturing while it's fresh, rather than reconstructed
after the fact. Unlike the reports this repo normally produces, **this one
is not frozen testimony.** It has no `gate-frozen` marker, and it will be
revised and re-issued as the trial continues toward ten ruled cards and the
falsifier gets its real answer. Where a claim below is provisional because
the trial isn't done, it says so plainly rather than reading as more
finished than it is.

## What changed, in the order it actually happened

**1 — the build itself (`d6fa9b7`, later folded into `c6c1d4a`).** New
`chronicler/review/desk.py` derives stale-output cards fresh on every
render from `project_wizard`'s manifests, freshness answers, and run
markers — nothing about a card is stored; only the events describing what
happened to it are. Registered as a tenth deck module (`modules.py`, order
5, front of the strip) with its own `static/views/desk.js` pane, on the
`project_wizard` precedent: no `app.py` changes, one registration plus one
view file. `wizforge.manifest.json` gained `build`'s `depends_on: [verify]`
(Trigger B's data) and a new `estate_freshness` stage giving Trigger A a
real delegated source via `estate_freshness_check.py`.

**2 — the silent week cut before the trial started (`d4f1c54`).**
Reviewed against the live build rather than the brief in the abstract: the
planned silent first week could produce at most one data point on this
fixture's single fingerprint, and the brief's own "no tuning mid-trial"
stop condition would have locked that N=1 in for the week's full length.
It was building a zero-point baseline to compare week two's number
against — the exact memory-comparison failure mode the brief named as the
reason a baseline was needed in the first place. Decided in the design
thread the same day: drop it, run visible from the first render. In its
place `desk.py` gained a `resolution` event — a fingerprint the log
believes is open that goes missing from a fresh derivation is now recorded
as `{kind: "resolution", fingerprint, ts, previous_render_ts,
detected_by: "absence"}`. The falsifier moved from a comparative claim
against patrol-and-remember (deferred to Phase 2, where more than one card
type makes an N worth measuring) to "did cards reach you with the evidence
you actually needed, and did you rule on them rather than scroll past?"
Trial length became open-ended — ten real cards ruled, not a calendar
bound. Full reasoning is recorded as a dated addendum at the end of the
brief.

**3 — the `estate_freshness` "Rebuild now" no-op (`a79bcc9`).** Found via
live testing on the real fixture, not by review: the stage's own `command`
re-ran `estate_freshness_check.py` — the freshness *question* — instead of
rebuilding `data/estate.json`, the freshness *answer*'s subject. Every
click executed, ruled, and re-derived correctly; the underlying staleness
never actually changed, so the card kept coming back. Fixed by pointing the
stage's `command` at `run.py build`, same as the `build` stage;
`freshness_source` stays delegated to `estate_freshness_check.py` for the
verdict, unchanged.

**4 — the occurrence-model rewrite (Addendum (b), folded into `c6c1d4a`).**
Found by reading the live `events.jsonl` one day into the trial, not by
reasoning about the code: a fingerprint that recurs only ever wrote **one**
sighting, because sighting/resolution logic checked a fingerprint's entire
history rather than what had happened since it was last resolved. A
resolved-then-reopened fingerprint could never sight or resolve again, and
every ruling against it inflated `latency_summary` against a
`condition_first_observable` unrelated to the ruling in front of it — three
rulings on one visit recorded three near-identical multi-day latencies
instead of one, and "rule ten real cards" was unreachable on a fixture with
exactly one recurring fingerprint. Root cause: the fingerprint (a standing
*kind* of problem) was being treated as the unit of measurement, when the
unit is actually an *occurrence* of it — opened by a sighting, closed by a
resolution, capable of recurring any number of times.

The fix: `_reconstruct_occurrences()` replays a fingerprint's
sighting/resolution events in order to answer "is there currently an open
occurrence, and when did it open" — the same question `_sync_events` needs
to decide whether a derived card opens a new occurrence or continues one,
and the same question `rule()` needs to stamp `occurrence_started_at` on
every ruling, explicitly, rather than leaving a reader to re-infer it from
timestamp ordering. `latency_summary()` groups rulings by occurrence, not
fingerprint: one latency figure per occurrence, from that occurrence's own
`condition_first_observable` to its first ruling; `cards_ruled` counts
occurrences ruled. The five pre-fix events on fingerprint
`57860823ba56c2c7` were disqualified as a button test, not trial data, via
a `finding` event logged through the existing `append_finding()` — nothing
on disk was rewritten; the log stays append-only and the pre-fix rulings
are still readable through a legacy-replay fallback that matches them to a
reconstructed occurrence window rather than needing the field. Verified
against four isolated unit-test scripts before ever touching the real
device, the last of which (`run_test_legacy.py`) replays the exact five
real historical events and asserts the code reproduces the real ~93.5h
figure precisely.

`data/desk/trial_state.json`, dead since the silent-week state was removed
in change 2, was deleted directly by Tim rather than through this round's
own tooling (the device bridge used elsewhere in this build cannot delete
files) — noted here per the addendum's instruction not to leave it
unexplained.

**5 — the "Rebuild now" ruling-refusal race (`fb6fa5c`, found and fixed
live during UAT, 2026-08-19).** Not in the brief or either addendum —
found by Tim clicking the button during the live walk. `desk.js`'s
"rebuild" action executed the wizard stage first, then tried to record the
ruling — but a successful rebuild is exactly what makes a card stop being
derived, and `POST /api/desk/rule` refuses any fingerprint that isn't
currently derived. Every successful rebuild was guaranteed to refuse its
own ruling; the error read `'<fingerprint>' is not a currently-derived
card. Refused -- rulings only land against a fingerprint the board can see
right now.` Fixed by swapping the order: the ruling is now recorded
*before* the stage executes, which also better matches what's actually
being measured — the moment of the human decision, not the moment the
command finished. If the mechanical rebuild then fails, the error message
now says so explicitly while crediting that the ruling still landed. No
change to `desk.py`; the fix is entirely in the client's call order.

**6 — the UAT fixture, `uat_decisions_fixture` (2026-08-19, not committed
into `L5GN-Tools`'s own history — see below).** A dedicated, hand-editable
repo at `C:\Users\timps\Documents\GitHub\uat_decisions_fixture`, separate
from `l5gn-tools-fixture`, built so the trial has a second source of real
triggers under direct manual control rather than waiting on
`L5GN-Tools`'s own estate-build cadence. Three stages: `source` and
`derived` (Trigger B — `derived` depends on `source`; both driven by
rebuild scripts per Tim's explicit choice over hand-touching mtimes), and
`state_freshness` (Trigger A — delegated to `uat_freshness_check.py`, a
1-hour staleness threshold, faster than `L5GN-Tools`'s real 24-hour one, so
the fixture can be exercised in one sitting). `config/project_wizard.allow.json`
gained a second `LucasGoonPC` repo entry, `uat-decisions-fixture`, alongside
the existing `l5gn-tools-fixture` — a fixture, not a pilot, same posture as
the entry it sits next to. **As of `9c1e221` (2026-08-19, after this entry
was added), that file is no longer committed at all** — Tim narrowed
DECISIONS 0042 clause 2 the same day, moving the allowlist into
`.gitignore` alongside `local.json` and `project_registry.json`: per-host
absolute paths that on the work rig mean employer repo paths, authored on
the machine and shipped by hand, never committed. `load_allowlist` still
fails closed on a fresh clone (an absent file merges to an empty map, not
"everything"), so nothing about execution safety changed — but this
round's own `uat-decisions-fixture` entry is the very case that surfaced
the need for the rule, and now lives only on `LucasGoonPC`'s disk, correct
per that ruling.

The fixture folder itself is a plain directory, not a git repository — it
also already contained a `DECISIONS.md`, `README.md`, and `decisions_feed.py`
predating this round's eight delivered files (`state.json`,
`uat_freshness_check.py`, `rebuild_state.py`, `source.json`, `derived.json`,
`rebuild_source.py`, `rebuild_derived.py`, `wizforge.manifest.json`); those
three files are unrelated to the Desk brief and not described further here.

## The card anatomy, against D-A, field by field

- **Question** — one sentence, naming the stage and repo:
  `"<repo> / <stage.label> looks stale -- rebuild it?"`, built in
  `_make_card()`.
- **Trigger** — Trigger A (delegated) or Trigger B (dependency), carrying
  the verbatim delegated answer or both compared timestamps; visible on the
  card face as a labelled tag (`delegated` / `dependency`).
- **Evidence** — the freshness line, the last run marker, the manifest's
  own declaration, and (where a `project_link` exists for the repo) the
  latest linked thread's title and date read `mode=ro`, or stated absent
  otherwise (`_linked_thread_evidence()`, wrapped in a broad try/except so
  a lookup failure degrades to "absent" rather than a 500). Every fixture
  card this session showed `linked thread: absent (no_project_link)`,
  correctly, since neither fixture repo has a vault link.
- **Options** — `rebuild` / `snooze` / `dismiss`, each without a cost
  estimate (`_base_options()`) — "no measurement, no estimate," per 0037
  clause 4; the run marker's last wall-clock is the only honestly available
  figure, and it isn't shown as a cost because it isn't one.
- **Default** — `hold`, stated on the card face; nothing runs until a
  click, and this round adds no policy engine that could override that.
- **Expiry** — re-raises the card with an `aged: true` marker after
  `AGED_AFTER_DAYS = 3.0`, a constant in the module, not config, per the
  brief's instruction to wait for a second card type before generalising
  it.
- **A card without assembled evidence is not raised** — `_make_card()`
  returns `None` whenever `condition_epoch` can't be established; this held
  throughout the session with no bare or evidence-free card ever observed.

## The `depends_on` widening, as landed

Trigger B reads `StageSpec.depends_on` for the first time — to ask whether
A ran more recently than B's output, never to run anything. The Desk has no
code path from card derivation to `run_stage` that doesn't pass through an
explicit operator click on the wizard's own existing execute route; this
held live, confirmed by the server logs throughout the session showing
`POST /api/project_wizard/execute` only ever following a click, never a
render.

## 2026-08-20 update — verification pass against Addendum (b), no code change needed

Tim picked the addendum (b) breakage back up explicitly on 2026-08-20,
asking for the occurrence model, `occurrence_started_at`, the
one-figure-per-occurrence `latency_summary`, append-only preservation, the
disqualifying finding, and `trial_state.json`'s removal to be built and
verified against the addendum's text. All six were already in place from
the 2026-08-19 work described above — this was a line-by-line audit of the
live `chronicler/review/desk.py` (confirmed byte-identical to what's on
`LucasGoonPC`) against each of the addendum's six numbered requirements,
not a rebuild. Every requirement checked out: `_sync_events` computes the
open occurrence set first and scopes the aged-transition check to sightings
since the occurrence's own opening, not the fingerprint's whole history;
`rule()` stamps `occurrence_started_at` from a fresh
`_reconstruct_occurrences` replay at ruling time; `latency_summary` groups
by `(fingerprint, opened_at)` and takes only the first ruling per group;
nothing in `_read_events`/`_append_event` rewrites history; the
disqualifying finding on `57860823ba56c2c7` is present in the log; and
`data/desk/trial_state.json` is gone (deleted by Tim directly, as recorded
above). No new commit was needed for the module itself.

Two things did change today, both outside `desk.py`'s code:

- **A second finding was logged**, per Tim's instruction to carry it:
  `chronicler/review/project_wizard.py` has no registered tester in
  `verify.py`. It spawns subprocesses under a pid+heartbeat lock and
  resolves stage-cwd containment (0042) with zero automated coverage, and
  the concrete, current instance of that gap is `write_run_marker`'s new
  `duration_seconds` field (see below) — it shipped into this same
  untested module. Recorded as a `finding` event, `refs: ["chronicler/review/project_wizard.py"]`,
  timestamped `2026-08-20T13:55:44Z`. `tester_project_wizard.py` is real,
  separate work — not scoped to this brief, not started here.
- **`docs/UAT_desk_stale_card.md` and its results log were already carrying
  the four addendum (b) `[G]` checks** (D10–D13) from the 2026-08-19 round;
  today's audit re-walked them against the live log rather than assuming
  yesterday's evidence still held, and found a second, independently-timed
  reinforcement: fingerprint `652d40c4fd26...` recurred a third time this
  morning (`2026-08-20T11:37:39Z`), sighted and ruled 32 seconds later, with
  `occurrence_started_at` correctly pointing at its own opening sighting
  rather than either of the two earlier occurrences. See
  `docs/UAT_desk_stale_card_results.md` for the full re-walk, dated
  2026-08-20.

**`write_run_marker`'s new `duration_seconds` field — flagged, not
implemented.** `project_wizard.write_run_marker` now records a real
`duration_seconds` (`None` when no command ran, never a misleading `0.0`).
Once stages run again on either fixture, `desk._base_options` could show
that as a real per-option cost instead of "no measurement recorded for this
stage yet" — closer to what 0037 clause 4 actually wants. **This is a
card-content change mid-trial**, and the brief's own stop condition is
explicit that thresholds don't move mid-trial; whether a *new, previously
absent* field showing up on the card counts as the same class of change is
Tim's call, not mine to make unilaterally. Not implemented in this pass.
If it's wanted, the natural time is either after the ten-card mark (clean
break, no mid-trial contamination question at all) or immediately, named
and dated as a deliberate exception the same way Addendum (b) named its own
mid-trial fix — but that's a decision for the next round, not this one.

**`docs/COWORK_BRIEF_staleness_feeds.md` — confirmed untouched.** 0050 is
ratified, but its 1b precondition (the trial's falsifier answered) isn't
met, and nothing from that brief — the feed, the options extension, the
health line — was read into this build or this report.

## The trial's numbers, as of this writing — provisional

Recomputed directly from `data/desk/events.jsonl` via `desk.latency_summary()`
itself, not by hand, as of 2026-08-20: **`cards_raised: 5`, `cards_ruled: 4`,
`cards_resolved_without_ruling: 1`, `median_latency_hours: ≈11.34`** (up
from `≈1.09` on 2026-08-19, as same-session fixture-testing rulings start
getting diluted by real time gaps between occurrences). Six cards short of
the trial's ten. The median is still not a believable decision-latency
figure — four points, three of them from one day's fixture testing — the
same "button test, not trial data" caveat Addendum (b) named for the
pre-fix events. The one new finding logged today is about the instrument's
own test coverage, not about a card's evidence being insufficient; no
"hunt" findings against a card have been logged yet. The sample remains
entirely on `uat-decisions-fixture`, not yet on `l5gn-tools-fixture`'s real
`estate_freshness` stage.

## The falsifier — not yet answered

*Did cards reach you with the evidence you actually needed, and did you
rule on them rather than scroll past?* Deliberately left open here. Seven
ruled cards short of the point the brief asks this question at; answering
it now, on three cards from one day's fixture testing, would be exactly the
premature-conclusion failure mode the silent-week cut and the
occurrence-model fix both existed to avoid.

## What wasn't exercised

- **D5 (kill the deck mid-ruling)** and **D6 (empty-allowlist honest empty
  state)** — not walked live this session; see
  `docs/UAT_desk_stale_card_results.md` for the deferral reasons. D6 is
  covered by earlier route-level `TestClient` tests from the original
  build; D5 has no coverage beyond `_read_events()`'s general tolerance for
  a trailing corrupt line.
- **The server-side empty-dismiss-reason refusal** — exercised only by the
  automated test suite; the client's own validation blocks an empty
  dismiss before it ever reaches the API, so the live UI never hit
  `DeskRefused("empty_dismiss_reason", ...)` this session.
- **Snooze and dismiss as suppression mechanisms** — deliberately don't
  exist. The brief is explicit: "no policy engine exists in this round…
  nothing acts on silence." Both were walked live and confirmed to behave
  exactly as specified — the card re-derives on every render regardless of
  what it was last ruled, because ruling never feeds back into derivation.
  Tim observed this directly (both snooze and dismiss "left it in the
  list") and confirmed it as expected rather than a defect; noted here so a
  future reader doesn't mistake it for one either.

## Commit series

```
d6fa9b7 Add the Desk module -- Phase 1 stale-output triage (Tasks 0-3)
d4f1c54 Drop the Desk's silent week; add a resolution event, open-ended trial
a79bcc9 Fix estate_freshness stage: Rebuild now was a no-op
c6c1d4a Add the Desk module -- Phase 1 stale-output triage (Tasks 0-3)
        [tree at this point already carries the occurrence-model rewrite
        and both addenda's text; folded in during a local rebase alongside
        unrelated Quartermaster-frame ratification commits — described
        narratively above rather than commit-by-commit for that reason]
fb6fa5c Fix Desk "Rebuild now": record the ruling before executing, not after
0345e72 chore(architecture-census): regenerate the shape after the Desk module
44dee3d docs(desk): Phase 1 report, walk-sheet and interim results
9c1e221 chore(config): ignore the Project Wizard allowlist, and record why
06c7ae6 docs: the commit convention  [untracks config/project_wizard.allow.json,
        reasoning recorded properly in 9c1e221 by forward reference]
4747741 chore: added a duration to write_run_marker  [outside this brief --
        see "flagged, not implemented" above]
```

`config/project_wizard.allow.json` itself is now permanently outside this
commit series — see the fixture paragraph above. As of this update, `git
status` on the desk-related paths (`chronicler/review/`,
`wizforge.manifest.json`, `docs/COWORK_BRIEF_desk_stale_card.md`,
`docs/COWORK_REPORT_desk_stale_card.md`, `docs/UAT_desk_stale_card*.md`) is
clean; the working tree still carries unrelated,
`bench_load_cost.py`, several other briefs' docs) — not part of this round,
not described further here.

## UAT

Walk-sheet: `docs/UAT_desk_stale_card.md`. Results so far:
`docs/UAT_desk_stale_card_results.md`, walked 2026-08-19, explicitly marked
interim. Of the thirteen acceptance items (nine original, four added by
Addendum (b)): seven carry full live evidence, one (the dismiss-reason
refusal) carries partial evidence with the gap named, and five are
deliberately deferred with a stated reason — none silently skipped. The
three `[H]` items among those five — ten cards ruled, the latency footer,
the falsifier — remain open by design until the trial reaches its own
stated end. This report and both UAT documents will be revised together
when it does.
