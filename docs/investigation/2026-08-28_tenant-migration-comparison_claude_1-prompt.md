# Prompt — the tenant migration, measured before and after

**Written:** 2026-08-28 on `LucasGoonPC`, ahead of the round it opens.
**Not yet handed to anyone.** Captured under `CONVENTION_docs.md` §5 so the
prompt exists as an artefact before the response does — the same pairing as
`2026-08-27_intent-coverage-remeasure_claude_1-prompt.md`.

**Precondition, and it is hard: this round cannot run until the post-migration
snapshot exists.** The operator is running a full week of real work through the
new work tenant so that the *after* sample is representative rather than a
first-day artefact. Opening this round before that week has elapsed and been
captured measures nothing and burns the comparison. **Check the snapshot's date
range before Task 1 and stop if it is short.**

---

You're working in `C:\Users\timps\Documents\GitHub\L5GN-Tools` on host
`LucasGoonPC`.

Read `CLAUDE.md` first — it is the map and it carries the environment hazards,
including the two that will bite this round specifically: never run plain git
against this repo from a sandbox, and a sandbox mount serves stale byte-truncated
content deterministically and without error. Then `docs/DECISIONS.md` **0038**
(conversation, session and thread are three distinct things), **0039** (a run is
scoped to the machine's declared estate), **0040** (where a source carries a
stable native conversation id, a curated map is the join of record) and **0051**
(the work-estate corpus is bounded by construction). Then
`docs/investigation/2026-08-27_intent-coverage-remeasure_claude_2-response.md`,
which is the method this round copies and the baseline it measures against.

**The job:** work out how the two Claude tenants differ as *sources*, so the
estate can decide how to handle them — not to produce a headline number.

## Why this round exists

The work account migrated to a new Claude tenant. The estate now holds, or will
hold, two captures of the same kind of material either side of that line. That is
a rare thing: **a controlled before/after on a source, with the work held
roughly constant by design.** Every other measurement in this estate compares two
different corpora and has to argue that the difference is not the cause.

Three questions, in this order, and the third is the one worth the round.

## 1. Do the two tenants behave the same as sources?

Mechanical, and it is the precondition for everything after it.

- **Conversation identity.** Does the new tenant carry a stable native
  conversation id, in the same id space and the same format as the old? 0040
  clause 1 turns on exactly this, and clause 1 also says a key that can be
  reissued is not a key. **If the id space changed, say so before anything else** —
  it decides whether the curated map carries across the boundary or has to be
  rebuilt, and that is a bigger finding than any coverage number.
- **Export shape.** Same fields, same nesting, same timestamp format and
  timezone? A silently changed field is how `ingest_local_transcripts` came to
  declare a join impossible that was merely underived (0040's Context).
- **`userSelectedFolders`, or whatever replaced it.** `data/decisions_draft/0058_proposed.md`
  measured the Cowork sidecar at 35 agree / 0 disagree / 14 empty on the old
  tenant. Re-run that comparison on the new one. **A mechanism that silently
  stopped populating would look exactly like a mechanism with nothing to say**, and
  0058 exists because that distinction has to be recorded rather than inferred.

## 2. The cloud-share question

The operator's expectation is that the new tenant does **not** have the
share-link problem, and wants that confirmed rather than assumed.

State plainly what "the problem" was on the old tenant before testing for it on
the new one — from the artefacts, not from anyone's memory of it. **If you cannot
find the old behaviour written down anywhere, that is the finding**: the estate
believed something about a source and never recorded it, which is the class
`CONVENTION_design_thread_restart.md` §2 exists to catch.

Then test the new tenant's behaviour directly and report it as measured, with the
commands that produced it.

## 3. Does linking work better or worse against the new tenant?

The interesting one, and the reason this round is worth a full budget.

The re-measure of 2026-08-27 left the estate with a per-account split that has
never been explained:

| account | threads | substantive | +ev | coverage |
|---|---:|---:|---:|---:|
| `claude-personal` | 39 | 32 | 6 | **18.8%** |
| `claude-local-personal` | 97 | 71 | 11 | **15.5%** |
| `gemini-personal` | 1,194 | 233 | 18 | **7.7%** |

**Nobody knows whether that spread is about the sources or about the linker.** A
new tenant is a third Claude-shaped source arriving with the work held constant,
which is the closest this estate will get to separating those two causes.

- Measure coverage on the new tenant on **INTENT §2's own definition**, stated
  before the number is taken, exactly as the 2026-08-27 round did. A different
  definition makes the comparison worthless.
- Split the delta into **corpus** and **linker**, and if you cannot, say so. The
  2026-08-27 round's headline finding was that most of a rise was a month of
  un-ingested material landing rather than the linking improving, and it only
  found that because it looked.
- **Arm the linker before measuring, and say that you did.** `relink` is skipped
  by default on this rig when `CHRONICLER_REGISTRY_PATH` is unset — the chain
  still finishes green. See `RUNBOOK_chronicler_refresh.md` Step 0 and
  `AGENDA_running_order_2026-08-28.md` Card B. **A coverage figure taken with the
  linker disarmed is not a measurement of linking**, and this round would be the
  second to nearly make that mistake.
- Report the **`exact` versus `evidence` split** separately. The 2026-08-27 round
  found 4 substantive threads on `exact` and 18 non-substantive ones — the exact
  join landing where INTENT's metric structurally cannot see it. If the new
  tenant changes that ratio, the metric is what moved, not the linking.

## Stop conditions

- **The post-migration snapshot covers less than a working week** → stop. The
  sample is the whole point.
- **The new tenant's id space differs from the old** → report that and stop
  before the coverage work. It changes what 0040 clause 1 means across the
  boundary, and a coverage number computed over a broken join is worse than none.
- **You cannot arm the linker** → report the coverage figures as **unknown**
  (0050), not as measured. Do not publish a number taken with `relink` skipped.
- **Any comparison would require reading work-estate content** → stop. 0051 binds
  this round. Counts of work-estate artefacts cross; their contents do not, in
  either direction.
- **You find yourself explaining the per-account spread from the sources' names
  rather than from measurement** → stop. That spread is the thing to measure, and
  a plausible story about it is worth less than nothing.

## Containment

0051 and 0039. The two estates are not co-rendered and not co-measured in one
run or one output. Where the work tenant is described, it is described by
**shape** — id format, field set, counts, coverage — never by what any
conversation is about. That line is the same one
`Work_Bridge/to-work/2026-08-27_REQUEST_harness_frame.md` drew and can be held to.

## What lands

One response file in `docs/investigation/`, paired to this prompt by name
(`..._claude_2-response.md`), per `CONVENTION_docs.md` §5.

If it produces a ruling, that ruling is **drafted `proposed`** and ratified on a
different day by the operator (0033). Two candidates are foreseeable and should
not be pre-empted here: whether the curated map survives the tenant boundary, and
whether INTENT's coverage figure should be scoped per-source rather than
per-estate — the second was raised and explicitly not drafted by the 2026-08-27
round (§7).

## What may not happen

- **No edit to `INTENT.md` or `ARCHITECTURE.md`.** §7 of the 2026-08-27 response
  holds a drafted §2 replacement that is still unapplied, and ARCHITECTURE §7's
  figure goes stale in the same act. Both move together, on the operator's call.
- **No ratification.**
- **No write to the vault.** Read-only, `mode=ro`, INTENT §5.
- **No git commit.** Draft to `data/git_warden/` and hand back the command.
- **No number without its definition stated first.** The 2026-08-27 round's one
  structural lesson.
