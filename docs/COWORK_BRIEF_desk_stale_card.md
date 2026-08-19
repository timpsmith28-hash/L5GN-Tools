# Cowork brief — Phase 1: the Decision Desk's first card — stale-output triage

**Origin:** vision thread, 2026-08-17 (`docs/investigation/2026-08-17_quartermaster_fable_2-response.md`
(vision and plan, consolidated) Phase 1); Tim's ruling that stale-output triage is the
first card type.
**Precondition:** Phase 0 closed — the INTENT §8 append landed and D-A/D-B
ratified with real numbers. This brief cites D-A throughout; it may not be
built while D-A is `proposed`.
**Depends on — this repo's rulings:** **0031** (findings, never verdicts — a
card is a finding with a question attached), **0033** (propose, ratify,
execute — a ruling on a card is the ratify step), **0037** (execution
parameters derive server-side; the execute route accepts an identifier, never
argv), **0042** (stages run only from validated manifests under the committed
allowlist), **0047** (there is one process; the Desk is a module in it, not a
second surface).
**Deliverable:** a `desk` module in the existing deck — one registration in
`chronicler/review/modules.py` plus one view in `static/views/desk.js`, per
the registry's own proven claim — that derives stale-output cards fresh on
every render, takes rulings, appends them as events to a sidecar log, and
measures one number: **time from the staleness becoming observable to the
ruling landing** — derived from the triggering timestamps, never from when the
tab was opened. **Two
weeks of live use, then the falsifier: if cards did not visibly beat
patrol-and-remember, Phases 2–5 are cancelled and this report says so.**

---

## What already exists — verified against the code, 2026-08-17

Build on these; do not reimplement them.

- **`project_wizard.load_manifests()`** returns per-repo results with
  validation errors accumulated, and **`stage_freshness(manifest, stage)`**
  already answers self-mtime or delegated freshness per stage. The card's
  trigger data is one call away.
- **`project_wizard.read_run_marker(repo_key, stage_key)`** already holds the
  last run's outcome and timestamp.
- **`project_wizard.execute_with_lock` / `run_stage`** already run a stage
  under the pid+heartbeat lock, streaming, with `classify_outcome`'s four
  states. The card's `rebuild now` option is a call to the **existing**
  execute route with the **existing** `(repo_key, stage_key)` body — the Desk
  adds no execution path of its own.
- **`project_wizard.WizardPlanSpec` / `WizardPlanStep`** — the Task-4 seam,
  serialisable and validated. Not used in this round; named so nobody builds
  a rival shape.
- **`modules.ModuleDescriptor` + `STATUS_REGISTRY`** — a new module is one
  registration plus one view file; `project_wizard`'s own entry (order 55,
  `requires=()`) is the precedent for a module whose data is reachable by
  construction.
- **`StageSpec.depends_on`** is recorded on every manifest stage and read by
  nothing (COWORK_BRIEF_project_wizard.md Task 4: "recorded, never acted on").

## The one deliberate widening, named

This round **reads** `depends_on` for the first time — to *ask*, never to
*run*. A card may be raised because stage B's `depends_on` names stage A and
A ran more recently than B's output; no stage is ever executed because of it.
The wizard brief's "read by nothing yet" line becomes "read by the Desk, to
raise a question" — a widening taken knowingly, recorded in this brief and in
the round's report, and structurally bounded: the Desk module has no code
path from card derivation to `run_stage` that does not pass through an
explicit operator click on the existing execute route. Chaining stays
forbidden (the wizard brief's non-negotiable), because raising a question is
not running a stage.

## Working rules

- **Cards are derived, never stored** — `docs_board.py`'s discipline. Every
  render recomputes the card set from manifests, freshness, and run markers.
  What *is* stored is events: sightings and rulings (below), because an event
  is a fact about the past, not board state.
- **The Desk executes nothing.** Its `rebuild now` posts to the existing
  wizard execute route, same body, same allowlist, same lock, same four
  outcomes. No new subprocess path, no new argv surface (0037, 0042).
- **No policy engine exists in this round.** The default on every card is
  `hold — nothing runs`; expiry only re-raises the card with an `aged`
  marker. Nothing acts on silence. (D-A permits stated defaults that act
  only under a ratified policy; there are none yet, so none act.)
- **No writes to `chronicler.db`.** The sidecar log is the ledger's seed
  corpus, deliberately outside the vault until Phase 2 owns the schema
  question.
- **A card without assembled evidence is not raised.** If the Desk cannot
  say *why* it believes a stage is stale (which freshness source, which
  timestamps, which dependency), it shows nothing rather than a bare
  accusation — a plausible wrong card is this surface's worst output, same
  reasoning as INTENT §5's fail-loud rule.
- Findings, never verdicts (0031): a card proposes; the operator rules.
- UTF-8 explicit, UTC ISO-8601, same as everywhere else.

## Task 0 ▸ give the triggers something to fire on

**Verified 2026-08-18: as things stand this module would render empty forever.**
`config/project_wizard.allow.json` grants `LucasGoonPC` one repo
(`l5gn-tools-fixture` → this checkout) and `10280L` none. Its two stages declare
`freshness_source: self` and `depends_on: []`, and `stage_freshness` with `self`
returns a *timestamp*, not a verdict. So **Trigger A has no delegated stage to
read and Trigger B has no dependency to compare** — the trial would produce zero
cards and the falsifier would return "no" for a reason unrelated to whether cards
work.

Fix it in this repo's own manifest, reviewed and committed like any other
manifest edit (0042 clause 2):

- Declare `build`'s `depends_on: [verify]` — a real ordering, not a fabricated
  one, and Trigger B's data.
- Add one stage whose `freshness_source` is `delegated`, pointed at something
  that already answers staleness honestly. The estate header computes
  *"44.5 h old — STALE"* today; a delegated command that reports the same is
  Trigger A's data, quoted verbatim per 0042 clause 7.

**This is a fixture, not a pilot** — the same posture the allowlist's own comment
takes about `l5gn-tools-fixture`. It buys the trial real triggers on the machine
where development happens; it is not a precedent for widening, and the work rig's
manifests remain Task 5 of the wizard brief, undone.

## Task 1 ▸ the card derivation — `chronicler/review/desk.py`

`desk.cards(allowlist=None)` derives the card set fresh:

- **Trigger A — delegated staleness:** a stage whose `freshness_source` is
  `delegated` and whose command's answer reports stale. Shown verbatim, per
  the wizard's no-second-freshness-engine rule (0042 clause 7).
- **Trigger B — dependency staleness:** stage B declares `depends_on: [A]`,
  and A's run marker (or A's `output_glob` newest mtime) is newer than B's
  `output_glob` newest mtime. Both timestamps shown on the card.
- **Card anatomy per D-A**, every field present or the card is not raised:
  the question (one sentence, named stage, named repo); the trigger (A or B,
  with the timestamps/answer that fired it); the evidence (freshness line,
  last run marker, the manifest's own declaration, and — where a
  `project_link` exists in the vault for this repo — the latest linked
  thread's title and date, read `mode=ro`, absent otherwise and *stated* as
  absent); the options (below) with what each costs where known (the run
  marker's last wall-clock is the only honest estimate available; no
  measurement, no estimate, per 0037 clause 4); the default (`hold`); the
  expiry (re-raise aged after N days, N in the module, not config, until a
  second card type exists to justify generalising).
- **Card fingerprint:** a stable hash of `(repo_key, stage_key, trigger
  kind)` — deliberately excluding timestamps, so the same standing staleness
  is one card that ages, not a new card per render.

## Task 2 ▸ the event log — sightings and rulings

`data/desk/events.jsonl`, append-only, one JSON object per line:

- **Sighting:** first time a fingerprint is seen (and again when it
  re-raises aged): `{kind: "sighting", fingerprint, card_summary, ts}`.
  Written on render only when the fingerprint is new or newly aged — a
  render that changes nothing writes nothing.
- **Finding:** `{kind: "finding", text, source: "human", ts, refs}` — entered
  by the operator, not derived. Findings are ledger events by ruling
  (2026-08-18); this round gives them their first home so the answer does not
  wait on Phase 2's migration. The seed corpus is real: the fix list from the
  2026-08-15..17 Grand Walk. In practice the *derived* source of a finding is a
  conversation like this one, and human entry serves that case unchanged. This
  is the one write path the Desk gains beyond rulings, and it is deliberate.

- **Ruling:** `{kind: "ruling", fingerprint, ruling: rebuild|snooze|dismiss,
  reason, evidence_refs, ts}`. `snooze` carries its until-condition;
  `dismiss` requires a non-empty reason — a dismissal without a reason is
  the un-promotable decision, and promotion detection (Phase 4) feeds on
  reasons.
- This file is the **decision-latency instrument**, and its anchor is the
  correction that makes it mean anything: latency runs from
  **`condition_first_observable`** — the triggering mtime/answer that made the
  stage stale, which the card already knows — to the ruling. **Not** from first
  sighting. Anchored to sighting, the number would measure *time from Tim
  noticing to Tim ruling*, excluding the entire patrol delay this module exists
  to remove: a stage going stale on Monday, seen Friday, ruled in a minute would
  record one minute. Sightings are still logged (they say when the surface was
  visited), but they are not the clock. `desk.py` computes it on render for the
  module's own small footer ("7 cards ruled, median 26h, oldest open 4d").
- The deviation from derive-never-store is confined to this file and named
  in the module docstring: events are the ledger's seed (Phase 2 migrates
  them), not board state — the board still derives.

## Task 3 ▸ the module — registration and view

- One `ModuleDescriptor` in `modules.py`: `id="desk"`, `status=
  STATUS_REGISTRY`, `requires=()` on the `project_wizard` precedent (its
  inputs are this checkout's manifests and sidecar — reachable by
  construction; an empty allowlist is an honest empty desk, not a degraded
  tab). Order: front of strip (below 10) — the Desk is the front door
  aspiration made literal, and the spaced-by-ten scheme absorbs it without
  renumbering.
- Routes via the module's own `router(ctx)`, wizard-style: `GET
  /api/desk/cards`, `POST /api/desk/rule` (fingerprint + ruling + reason,
  nothing else), `GET /api/desk/latency`. **No route accepts a repo path, an
  argv, or anything execution-shaped** — `rebuild now` in the view calls the
  wizard's existing execute route directly.
- The view renders cards as cards — question first, evidence expandable,
  options as buttons, default and expiry stated on the face. The reference
  room is one link away (the wizard tab, the docs board), reached from
  evidence, per the vision.

## Task 4 ▸ the two-week trial — designed in, not bolted on

- **The first week runs silent.** Cards are derived and their sightings and
  `condition_first_observable` timestamps logged, but nothing is shown. That
  week is the **baseline**: it measures how long staleness stood unruled while
  the operator was patrolling as usual. Without it, "visibly better than
  patrol-and-remember" is a memory comparison, which this estate rejects
  everywhere else. Cards become visible at the start of week two.
- **The trial runs on `LucasGoonPC`**, against the fixture manifest of Task 0.
  The work rig has no allowlisted repos, and its cold-start defect is a separate
  finding.
- The trial's start is the commit date of the round's last task; its end is
  a calendar entry, not a feeling.
- During the trial, **no fixes beyond breakage**: tuning card thresholds
  mid-trial contaminates the latency number. Findings accumulate in the walk
  sheet.
- The falsifier, verbatim from the plan: *did cards reach you with the
  evidence you actually needed, and is decision latency on stale outputs
  visibly better than patrol-and-remember?* The report answers with the
  events file's numbers and Tim's testimony, and a **no** cancels Phases
  2–5 in writing.

## Explicitly out of scope

- Any second card type (failed-run triage, linking cards) — one type is the
  experiment's control.
- Any policy engine, promotion detection, or default that acts. Phase 4.
- Any write to `chronicler.db`, any schema work. Phase 2.
- Any change to `project_wizard.py`'s execution path, lock, or outcome
  states. The Desk is a caller.
- Any notification, scheduler, or push. The Desk is visited, in v1.

## Stop conditions

- The Desk gains any execution path other than the existing wizard execute
  route → stop (0037, 0042).
- A card is raised without its full D-A anatomy (missing trigger evidence,
  missing default, missing expiry) → stop.
- An expiry or default *acts* — anything runs without a click → stop
  (INTENT §4; there are no ratified policies).
- Anything writes to `chronicler.db` → stop (Phase 2 owns that door).
- Board state is stored (anything beyond the two event kinds in the sidecar)
  → stop; derive it instead.
- The module lands with routes inline in `app.py` rather than via its own
  `router(ctx)` → stop — nine modules prove the registry; a tenth going
  around it is regression, not pragmatism.
- Card thresholds are tuned mid-trial → stop; note the urge in the walk
  sheet instead.
- `classify_outcome` gains a fifth state → stop (standing).

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[H]` per 0031.

- `[G]` A repo with a delegated-freshness stage reporting stale raises
  exactly one card, whose trigger quotes the delegated answer verbatim.
- `[G]` A `depends_on` pair where A ran after B's output raises a card with
  both timestamps shown; running B through the card's button clears it on
  next render — because the *facts* changed, not because the card was
  marked done.
- `[G]` The same standing staleness across many renders is one fingerprint,
  one sighting event, aging — never a duplicate card per render.
- `[G]` `POST /api/desk/rule` refuses an unknown fingerprint and an empty
  dismiss-reason; no desk route accepts a path or argv.
- `[G]` Kill the deck mid-ruling: the events file is valid JSONL (append-only
  survives), and the board re-derives identically.
- `[G]` With an empty allowlist the Desk renders an honest empty state, not
  an error.
- `[H]` **Rule ten real cards over the trial.** Was the evidence on the card
  enough, or did you leave the Desk to go hunting? Every hunt is a finding
  naming what was missing.
- `[H]` **The latency footer at trial's end: is the number believable**, and
  did it move against your own memory of patrol-and-remember?
- `[H]` **The falsifier, answered in one paragraph, yes or no.** A no is a
  successful experiment and a cancelled programme; say which this was.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Reporting

`docs/COWORK_REPORT_desk_stale_card.md`, walk-sheet
`docs/UAT_desk_stale_card.md`, stamped results after the trial (not after
the build — the trial is the round).

Record: the card anatomy as implemented against D-A field by field; the
`depends_on` widening as landed; the events file's final trial numbers
(cards raised, ruled, median latency, oldest open); every hunt the trial
logged; and the falsifier's answer, plainly, with its consequence for
Phases 2–5.

---

## Addendum, 2026-08-19 — the silent week cut before the trial started

Reviewed against the live build (one fixture repo, one delegated-freshness
stage) rather than against the brief in the abstract. Findings, not a
re-litigation of Task 4's intent:

- `latency_summary` derives entirely from `ruling` events. The silent
  week's own view has no ruling button — rulings cannot happen while it
  runs. Through the whole silent week the footer would read
  `cards_ruled: 0, median_latency_hours: None`, every time.
- The fixture allowlist (`l5gn-tools-fixture` only, one delegated stage)
  yields at most one fingerprint. A week of silence could produce at most
  one observation, and only if a rebuild happened to land inside it.
- The brief's own stop condition — "card thresholds tuned mid-trial → stop"
  — locks that N=1 in for the silent week's full length, since nothing
  about the trigger set can be widened to get more signal without
  violating it.
- Net: the silent week was building a baseline of zero data points to
  compare week two's number against — the memory-comparison failure mode
  this brief itself named as the reason a baseline week was needed in the
  first place. The instrument could not do the job it was built for.

**Decision, taken in the design thread and implemented same day:** drop the
silent week; run visible from the first render. In its place, `desk.py`
gained a `resolution` event — a fingerprint the log believes is still open
that goes missing from a fresh derivation is now recorded as
`{kind: "resolution", fingerprint, ts, previous_render_ts,
detected_by: "absence"}`, `ts` stated as an upper bound (the Desk only
learns a card vanished when someone loads the tab). This closes the gap the
silent week's absence of a ruling path would otherwise have hidden — a card
fixed by hand, or by something else, no longer disappears without a trace.

**The falsifier changes accordingly.** The original comparative claim —
"is decision latency on stale outputs visibly better than
patrol-and-remember" — is deferred to Phase 2, where a real ledger, more
than one card type, and the work rig's manifests make an N worth measuring
exist. This round's falsifier, answered in `COWORK_REPORT_desk_stale_card
.md`: **did cards reach you with the evidence you actually needed, and did
you rule on them rather than scroll past?** Still a no/yes with a
consequence for Phases 2–5, just not a comparative one.

**Trial length, also decided in the design thread:** open-ended rather
than a fixed two weeks — it runs until ten real cards have been ruled (the
UAT line already asked for this), on the same N=1 reasoning above: a
calendar bound doesn't guarantee enough signal to trust the anatomy on one
fixture stage, and there is no reason to stop early just because a
fortnight passed.

Implementation: `chronicler/review/desk.py` (silent-week state removed,
`resolution` event added, `latency_summary` reports
`cards_resolved_without_ruling` alongside the existing fields) and
`chronicler/review/static/views/desk.js` (trial messaging removed, cards
render from the first load). Full account goes in
`COWORK_REPORT_desk_stale_card.md` per the Reporting section above.
