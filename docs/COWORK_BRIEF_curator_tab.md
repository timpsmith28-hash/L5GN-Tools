# Cowork brief — the Knowledge Curator tab: ratification first, findings second

**Origin:** design thread, 2026-08-08.
**Depends on:** DECISIONS **0025** (a solo box reads its own estate on loopback),
**0027** (a local surface reads the source at render time), **0031** (a check
surface reports findings, never a verdict), **0032** (the Curator is
local-transcript, MCF-scoped, recency-ordered), and the Curator K0–K5 build
recorded in `docs/COWORK_REPORT_knowledge_curator.md`.
**Deliverable:** a **tab in the existing review app** that ratifies the K0
conversation map, controls the Curator's stages, and renders its findings.

The Curator's brief said, explicitly: *"A UI, scheduling, or coupling into the
ingest pipeline"* is out of scope, and *"the report is a markdown file, read like
any other investigation doc."* That was right for the build round and it is worth
saying why this round overturns it, because "we built it so now it needs a screen"
is not a reason.

Three things a rendered surface does that `report_<date>.md` cannot:

1. **K0's ratification is a per-row judgement over evidence**, and the evidence is
   two blocks of text with a matched prefix in them. A TSV column saying
   `pass-1, 112, 1` asks you to trust the matcher. The same match, with the
   overlapping span highlighted in both texts, asks you to *look*. The walk-sheet
   already tells you to read the evidence column, not the answers — this is that
   instruction made possible.
2. **The map is header-only, so K1–K5 are all blocked.** Nothing downstream has
   ever produced real output. The one screen that matters right now is the one
   that unblocks the rest, and it is a screen, not a file.
3. **Model selection now has consequences that must be shown before they are
   accepted** — see Task 3.

Everything else in this brief exists to make those three honest.

---

## Where it lives, and the wariness that was withdrawn

**In `chronicler/review/`, as a tab in the existing app.** This was argued the
other way first — a runner has a wider remit than a reader, so isolate the
process — and then settled the other way deliberately.

The reason is slice 2's rule, which has not stopped being true: *two
implementations of a security boundary is one more than can be kept correct.* The
review app already resolves the machine's declared estate, already refuses to
serve threads when the estate cannot be named, already enforces the loopback rule
structurally for a non-personal estate, and already degrades per-route rather
than all-or-nothing. A second service re-derives every one of those, and the
second copy is the one that rots.

So: same app, same process, same bind, new tab. **The extra remit is real and is
handled by naming it** — Task 3's execution allowlist and Task 2's staging
allowlist — not by moving it to a different port.

---

## Precondition ▸ DECISIONS 0033 must be ratified before any code

Task 2 stages `config/mcf_conversation_map.tsv` into the working tree. **0028
does not authorise that**, and reading it as if it did would be the kind of
quiet stretch this estate keeps a decision log to prevent.

0028's clause (1) confines a staged change to `docs/`, as a `git mv` into
`docs/archive/` plus a stamp prepended above the title, **never a body edit**.
The Curator's map is in `config/`, is not a move, and its body is the entire
change. All three conditions fail.

What does *not* fail is the property 0028 exists to protect. Draft the entry
below, get it ratified and committed, and only then build. If it is ruled
against, Task 2 becomes read-only — it renders the candidate map and you edit the
TSV by hand — and the rest of the brief stands unchanged.

> ## 0033 — Staging is confined by a code-declared path allowlist, not by directory; 0028's `docs/`-only clause is widened once, by name
>
> **Date:** 2026-08-08 · **Status:** proposed · **Amends:** 0028 (does not
> supersede it) · **Builds on:** 0025, 0027, 0032 · **Source:** design thread
>
> **Context.** 0028 permits a local surface to stage a working-tree change and
> forbids it to commit. Its clause (1) confines the change to `docs/`, to a
> `git mv` into `docs/archive/`, and to a prepended stamp — never a body edit.
> That confinement was written around the one action then in view: the docs
> board archiving a completed pair.
>
> The Curator's K0 ratification is a different shape of the same act. It writes
> `config/mcf_conversation_map.tsv` — a curated join surface, one row per
> conversation, each row ratified individually by the operator reading the
> evidence for that row. It is in `config/`, it is not a move, and the body is
> the change.
>
> But the property 0028 was actually protecting is not the directory, and is not
> the `git mv`. It is clause (3): **the human reads `git diff --staged` and
> performs the commit**, so the gate runs on a human act and no unreviewed
> change can enter history. That property is untouched here.
>
> **Decision.** 0028's clause (1) is replaced by:
>
> 1. The change is confined to a **path allowlist declared in code**, not in
>    config, each entry carrying a declared shape. Two entries at this ruling:
>    - `docs/**` → `git mv` into `docs/archive/` plus a prepended stamp, never a
>      body edit (0028's original clause, unchanged in substance);
>    - `config/mcf_conversation_map.tsv` → **append a row**, never edit or
>      remove an existing one.
>
> Clauses (2) and (3) stand **unchanged and unweakened**: per-item ratification
> given in that session, never in bulk, never inferred from a green gate; and
> **never `git commit`**.
>
> Additionally, and specific to the map: **every staged row records how it was
> arrived at** — machine-matched by which pass, or human-picked from a refused
> collision, or hand-mapped with no machine candidate. A row resting on the
> operator's memory rather than on a match must say so, permanently, in the
> file. This is the registry's `alias_sources` pattern (S1), for the same
> reason: a curated identity whose provenance is lost becomes indistinguishable
> from a derived one, and 0011 and 0017 spent two rounds cleaning up the
> consequences of that.
>
> **Consequences.** There is now an allowlist where there was a directory
> constant — a knob where 0028 had none. Accepted deliberately, and bounded two
> ways: it is **declared in code**, so widening it is a commit that the gate
> sees and a reviewer reads, not a config edit; and the never-commit rule is
> what actually makes staging safe, and it is not being touched. The worst case
> remains a working tree the operator must clean up.

---

## Working rules

- **Extend the review app. Do not add a service, a port, or a bind.** FastAPI and
  uvicorn are already its optional extra (`pip install -e .[review]`); add no new
  dependency beyond what is installed.
- **Reuse, do not reimplement.** The Curator's stage modules already exist and
  already own their logic: `bootstrap_conversation_map.py` (K0),
  `knowledge_index.py` (K1), `extract_claims.py` (K2), `corpus_index.py` (K3),
  `match_claims.py` (K4), `compile_report.py` (K5). The tab reads their outputs
  under `data/knowledge_curator/` and invokes their entry points. **It
  reimplements no stage logic and computes no finding of its own.**
- **Gate GREEN before commit. All logic in testable functions, not route
  handlers** — the standing rule, and it matters more here than usual because
  three of this round's requirements (containment, the execution allowlist, the
  staging shape) are security boundaries that must be tester-proven.
- **Read-only except for the two named write paths**: staging the map (Task 2)
  and invoking a stage (Task 3). Nothing else writes.
- **Findings, never verdicts** (0031). No ticks, no "pass", no green summary, no
  aggregate score. The tab cannot mark anything done.
- UTF-8 explicit, UTC ISO-8601, in line with the Curator's own rules.

---

## Grounding — what exists, and the three obstacles worth naming up front

**What is already there and should be leaned on:**

- `run.py review`'s **preflight is already split by what each route needs**
  (slice 1). A machine with a vault and no estate build serves, and so does the
  reverse; a missing half degrades that half and says so. The curator tab is a
  third half and joins the same pattern.
- `create_app()` already takes optional `estate=` and `index=` and a
  `vault_unavailable=` reason, and already documents that any half may be absent
  and the surface **says what it hasn't got rather than refusing to start**. Add
  a `curator=` in that shape and nothing new is invented.
- The estate wall is resolved **once** in `run.py` and passed down; `app.py` and
  `core.py` never read config themselves. Keep that property.
- Every model-calling stage already takes `--endpoint`, `--model` (**required**,
  with no default — so provenance cannot be omitted by accident) and
  `--temperature`. Per-stage model selection maps onto flags that already exist.

**Obstacle 1 — the tab must be absent on the wrong machine, and say why.**
0032 scopes the Curator to the work/MCF estate. The review app already refuses to
serve threads when the declared estate cannot be named, and already renders
non-estate-labelled surfaces regardless. The curator tab is **estate-labelled by
construction**: it reads MCF transcripts. So it must be available only where the
declared estate is the work/MCF one, and on any other machine it renders a stated
absence — the same shape as the Chronicler stages being shown as unavailable on
the work rig. **Present and explained beats hidden**, in both directions.

**Obstacle 2 — the transcript store is not an estate root.**
Task 4 renders a conversation at render time, which is 0027, but 0027's condition
(3) is "within the configured estate roots and vault home". The Cowork local
transcript store is neither. This is a genuine widening of what the surface can
reach and it is the reason Task 4 is specified the way it is: the store's home
must be added as a **declared, allowlisted read root**, the identifier must remain
opaque, and slice 1's containment check must be called against it rather than a
second resolver being written.

**Obstacle 3 — `auditor_readonly` does not cover this, and that is worth
recording rather than relying on.**
It walks the `SCANNERS` registry and audits scanner sources for filesystem-
mutating calls. `chronicler/review/` is not in that set, so nothing in this round
trips it. **Say so in the report, explicitly.** A write path that passes the gate
because no auditor was looking at it is a fact the next reader needs, not a
clean bill of health.

---

## Task 1 ▸ the curator data layer and the tab shell

A read-only module (suggested `chronicler/review/curator_data.py`) that loads
what exists under `data/knowledge_curator/` and reports what does not.

- Load `knowledge_index.json`, `claims.json`, `corpus_index.json`,
  `matches.json`, `candidate_map.tsv` and the ratified
  `config/mcf_conversation_map.tsv` if present. **Every one of them may be
  absent**, and absent is the current true state of most of them.
- Expose per-stage state derived from what is on disk: whether the stage's output
  exists, its `generated_at`, and **what it is blocked on**. "K2 blocked: the map
  is header-only" is the answer the operator needs; "K2: no data" is not.
- Surface the run provenance every artefact carries — model id, endpoint,
  temperature, run timestamp — because 0032's honesty argument rests on it.
- **Staleness is per-artefact, not global.** A corpus index from yesterday beside
  claims from last week is the normal state of a partially-run pipeline, and the
  header must be able to say that rather than picking one timestamp.

Wire it into `create_app()` as an optional half in the existing shape, and into
`run.py review`'s preflight as a third route family. **State in the report which
routes now require what** — the same sentence slice 1 was asked for, because the
preflight table is now three rows and nobody will re-derive it from the code.

## Task 2 ▸ K0 ratification — the screen that unblocks the rest

**Build this first.** Until the map is ratified nothing downstream has real data,
so a findings view built first would be a view of nothing.

- Render `candidate_map.tsv` as one card per candidate, grouped by outcome, with
  **all six K0 counts printed including the zeroes** — matched-by-pass-1,
  matched-by-pass-2, ambiguous-same-project, ambiguous-different-project,
  unmatched-sheet-rows, unmapped-`local_*`-folders-on-disk.
- **The evidence is the point of the card.** Show the normalised sheet opener and
  the conversation's normalised first user message with **the matched span
  visually marked in both**, above the machine-readable evidence line (which
  pass, matched length, candidate count). The operator is being asked to ratify a
  claim about text; show them the text.
- **Per-row actions only. No bulk accept, and no "accept all matched by pass 1".**
  0028's clause (2) survives 0033 unchanged and this is where it bites. A round
  of 48 individual clicks is the cost of the thing being permanent.
- **Honour K0's own rules in the UI, do not re-litigate them.** A same-project
  collision offers "ratify pair, split by date". A **different-project collision
  offers no ratify button at all** — only pick-one-by-hand or leave unmatched. A
  sheet row below the 60-character floor says it never reached pass 2 and why.
- **Ratification appends a row and stages it.** Provenance per row per 0033.
  Never edit or remove an existing row. Never `git commit`.
- Show the **staged diff** in the tab — the rows that will be committed, with
  human-provenance rows visually distinct — so `git diff --staged` in a terminal
  is a confirmation rather than the first sight of it.
- The **unmapped `local_*` folders** (~16 expected, against ~64 on disk and 48
  curated rows) get their own section with date and message count per folder,
  framed as the finding the Curator's brief says it is:
  if these are conversations deleted in the Cowork UI, then deleting a
  conversation does not delete its transcript, which is a data-retention fact
  about the work estate. **Do not let this render as a tidy-up list.**

## Task 3 ▸ the control strip — preconditions, per-stage models, invocation

**Preconditions are probed and displayed before anything offers to run.** LM
Studio reachable or not, with the endpoint and the round-trip; the loaded model
list from `/v1/models`; whether the map is ratified; which stage outputs exist.
Discovering three minutes into a run that the endpoint is down is the failure this
prevents.

**Model selection is per stage, and only for stages that call a model.**

- K2 (extraction) and K4's confirm step each get their own selection, defaulting
  to a single default with overrides marked as overrides.
- **K0, K1, K3 and K5 get no selector.** They are deterministic. A dropdown beside
  a stage that calls no model implies a choice that does not exist.
- **K4's shortlist step is a capability display, not a selector.** Report what it
  actually does in the code today; if there is no embedding path, the UI states
  the method in use rather than offering a model for it. Same discipline as slice
  1's FTS5 capability check: probe, degrade, and say so visibly.
- **Selections are machine config**, in `config/local.json` keyed by hostname
  alongside the machine's declared estate — never in anything that travels. The
  loaded models differ per machine, so a repo-level default would be wrong
  everywhere but one rig.

**The cache consequence must be stated in real numbers before the change is
accepted, not after.** The caches are separate: changing K2's model invalidates
the cached claims and everything derived from them; changing K4's confirm model
invalidates the cached verdicts and leaves the claims intact. So the UI says
*"this invalidates 1,204 cached verdicts; 312 claims are untouched"* — the actual
counts read from the cache files — and offers re-extract or keep-and-record-both
as an explicit choice. **A report spanning two models is not automatically
wrong, but it is not reproducible testimony unless it says so**, which is why the
choice is surfaced rather than defaulted.

**Invocation, and its two hard requirements:**

- **The route takes a stage key from a fixed allowlist derived from the Curator's
  own stage table. It never accepts a command, an argument string, a path, or a
  flag from the caller.** This is slice 2's opaque-identifier rule applied to
  execution rather than to file reads, and it is the whole security story of this
  task.
- **One run at a time, enforced by a real lock**, not by disabling a button. A
  second request while a run is in flight is refused with *what is running and
  when it started* — never queued, never silently dropped. Two browser tabs and a
  double-click are the normal case, not the edge case.

**Render skipped, failed and blocked as three different things.** `run_pipeline`'s
existing contract is precise — a missing input is a clean skip with a note, a
non-zero exit for any other reason stops the chain — and the Curator's own
standing rule is that a stage which cannot complete says so and produces no
partial output. A UI that colours all three the same teaches the operator to
ignore all three.

**Progress is stage-count, never a percentage.** "Stage 3 of 6, conversation 21 of
45" is honest. A percentage bar over a run whose duration nobody has measured is
a fabricated window, and this estate has a name for those.

**Chronicler's stages appear in the strip and are unavailable, with the reason
named.** No vault on the work rig, so the ingest stages have nothing to run
against. They are shown so the absence reads as a stated fact rather than a
missing feature — and, more importantly, so that a populated Chronicler strip
never appears beside a populated Curator strip. **That co-render is the case 0023
gates and the gate does not exist**; the preflight split is what keeps this round
away from it.

## Task 4 ▸ the findings views

Five sections, in the order `compile_report.py` already emits them: gaps, no
knowledge file yet, cross-project, superseded, captured. The tab renders the same
material; it does not recompute it.

- **Run health above the findings, always.** Conversations excluded for an
  unresolvable timestamp, the unmapped folders, the projects with no knowledge
  file, and the quote-rejection rate. The Curator's own stated failure mode is a
  thin run reading as a clean bill of health; putting the caveats underneath the
  findings is how that happens.
- **Per project, never totalled.** Conversation counts run from 1 to 14 and only 4
  of 9 projects have a knowledge file at all. A single headline number over that
  distribution is not a summary, it is an average of incomparable things. A
  project with no knowledge file shows no gap count — a gap against an empty
  corpus is not a finding.
- **Timestamp provenance is shown per conversation**, badged by source (last
  message timestamp / file mtime / folder mtime). Ordering *is* the design under
  0032, so the quality of the ordering is a first-class fact, not a footnote.
- **Every finding shows its negative evidence.** A gap states which corpus was
  searched, how many chunks, the closest shortlist score and the confirm verdict.
  Both halves are already recorded by K4 precisely so that a confirm step which
  never disagrees with its shortlist is visible; the UI is where that becomes
  visible.
- **Superseded is two blocks, both quoted, both dated**, current above
  superseded, with the interval stated — and with it said plainly on the card
  that ordering picked the newer statement and has **not** judged which is better
  reasoned. Offer a way to record that the ordering got it wrong. That path is the
  round's novel claim and its honest weak point, and how often it is exercised is
  a finding about the design.
- **Drill through to the conversation, per 0027 and Obstacle 2.** Opaque
  identifier resolved against the in-memory map; containment checked against the
  declared transcript-store root using slice 1's resolver, **not a second one**;
  a bounded window rather than a whole transcript; an honest refusal for a
  missing, binary or oversized file. Testers for both cases — a resolved path
  outside the root, and a traversal attempt through the identifier — run against
  transcript paths specifically, because a containment test that only ever
  exercised markdown under the estate roots does not cover this.
- **Nothing here writes.** No triage state, no dismissal, no "not useful".

## Task 5 ▸ map and coverage

The K1 reconciliation, rendered: mapped rows resolved by exact session id, mapped
rows absent on disk, folders present but unmapped, the three-state `unresolved`
(no mapping / folder absent / unreadable), and the label sanity-check
disagreements — **reported, never auto-resolved**, with it stated on the surface
that the label is a label and the session id is the join.

---

## Explicitly out of scope

- **Triage state across runs** — marking a gap reviewed or not-worth-writing-up.
  It is a third write path and it is K6's parked dedupe question. **Not in this
  round.**
- **Any write into a `KNOWLEDGE*.md` file, ever.** The tool proposes; Tim edits.
  Proposed wording, if it happens at all, is reviewed in the editing pass and not
  by a button here.
- **`git commit`.** 0033 clause (3), unchanged from 0028.
- **Chronicler stages actually running**, and any populated Chronicler view on
  this machine. Shown unavailable, with reason.
- **Personal-estate content**, per 0032. Not deferred — out.
- **The TOTP gate** (0023). Still unbuilt, still required for any co-rendering or
  network-reachable surface, and this round is deliberately arranged so that it
  is not needed.
- **Scheduling.** K6's cadence question stays parked; no scheduled run, no timer.
- **Any change to what a Curator stage computes.** If a view needs a field a
  stage does not record, **report that rather than adding it** — a stage change
  is a different pair.

---

## Stop conditions

- **A second bind, port, or service appears** → stop. The whole argument for the
  tab is that it inherits one boundary rather than copying it.
- **A route accepts a path, a command, an argument string, or a line number from
  the caller** → stop, in either the read or the execute direction.
- **A second path resolver is written** → stop. Slice 1's is the one.
- **Anything calls `git commit`** → stop.
- **A staged row edits or removes an existing map row**, or is written without
  provenance → stop.
- **A bulk-ratify action exists** in any form → stop.
- **The tab renders on a machine whose declared estate is not the work/MCF one**,
  with data → stop.
- **Chronicler and Curator both render populated on the same surface** → stop;
  that is the ungated co-render.
- **A finding is recomputed in the UI** rather than read from a stage's output →
  stop; two authorities that can disagree about a finding is the defect this
  estate keeps rediscovering.
- **Any view issues a verdict** — passed, green, clean, done → stop (0031).

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[H]` **0033 is ratified and committed before any code lands.**
- `[G]` The tab renders on the work rig and states a clean absence on a machine
  whose declared estate is not work/MCF — with no curator data reachable there.
- `[G]` With the map header-only, K1–K5 each read as **blocked with a named
  cause**, not as empty or broken.
- `[G]` A machine with no vault still serves the curator tab; a machine with no
  estate build still serves it; the preflight table in the report matches the
  behaviour.
- `[H]` **Ratify the map.** Read the highlighted evidence, not the answers. This
  is the one step where a wrong row becomes permanent.
- `[G]` No bulk-accept exists. A different-project collision offers no ratify
  action. A same-project pair ratifies as a pair, split by date.
- `[G]` Ratification appends rows, stages them, and does **not** commit.
  `git diff --staged` shows exactly what the tab showed, provenance column
  included, and a `human-mapped` row is distinguishable from a `pass-1` row in
  the file itself.
- `[G]` Re-ratifying a row already in the map does not duplicate or edit it.
- `[G]` **Kill LM Studio and the tab says so before offering to run**, not three
  minutes into a run.
- `[G]` Changing K4's confirm model reports the verdict count it invalidates and
  leaves the claim count untouched; changing K2's model reports the claims.
- `[G]` K0, K1, K3 and K5 offer no model selector.
- `[G]` Model selections land in `config/local.json` under this hostname and
  nowhere that travels.
- `[G]` **Two runs cannot overlap.** Start a run, request another from a second
  tab, and get a refusal naming what is running and when it started.
- `[G]` A stage that skips for a missing input, a stage that fails, and a stage
  that is blocked are visually and textually three different states.
- `[G]` The execution route rejects a stage key not on the allowlist, and there
  is no route that accepts an argument.
- `[G]` Containment holds against transcript paths — a crafted identifier cannot
  read outside the declared transcript-store root, and a traversal attempt
  through the identifier fails. Tester-proven, plus one manual attempt.
- `[G]` A deleted or oversized transcript gives a stated refusal, not a stack
  trace.
- `[G]` Zeroes print. An empty section reads as a real answer, not as breakage.
- `[H]` **Is run health impossible to miss?** Look at the tab as if you had not
  built it: could you mistake a thin run for a clean one?
- `[H]` **Does the evidence display actually help you ratify?** If you find
  yourself trusting the pass label instead of reading the spans, the display has
  failed at its one job.
- `[H]` **Does anything on the surface read as a verdict?** Any tick, any green,
  any "complete" is a finding against this round.
- `[H]` **Is the tab worth it over the markdown report?** Answered plainly,
  including if the answer is "only for K0."

Results log needs a uat stamp naming the commit; do not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_curator_tab.md`, walk-sheet `docs/UAT_curator_tab.md`,
stamped results after the walk.

Record: the 0033 ratification; the **three-row preflight table** (which route
family now requires what); the execution allowlist as implemented and how the
lock is held; the staging shape, with a real staged diff quoted in full; the
containment tests against transcript paths; what `auditor_readonly` does and
does not cover for this round, stated plainly; and the K0 ratification outcome —
how many rows ratified by which provenance, how many refused, and whether the
unmapped-folder question got an answer.
