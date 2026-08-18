<!-- actioned: (none yet) -->

# Quartermaster — a clean-slate reimagining of L5GN-Tools

**Date:** 2026-08-17 · **Model:** Fable (design thread) · **Prompt:** not
retained; the estate's own documents were the input.

*A vision document, written cold, on purpose. It describes the tool your estate has
been circling, not the code that exists. A short appendix at the end checks what
survives from the repo — but nothing before that point is constrained by it.*

Investigation, per `docs/README.md` §4. **Born frozen.** Nothing here is a
ruling; DECISIONS 0048 and 0049 are the two proposals drawn from it and are
`Status: proposed` until ratified. The `actioned:` block above is the one part
of this file that may gain lines later.

---

## 1. The premise: you've been building an allocator without naming it

Read the estate's own documents in one sitting and a pattern emerges that none of
them states. The Chronicler recovers *why* decisions were made. The deck queues
things for *ruling*. The Conductor turns a *budget* into a plan. The Wizard puts
*runnable* things one click away. The DECISIONS log makes rulings durable. Every
component, independently grown, is a fragment of the same machine: a system for
**allocating three scarce resources against a portfolio of work**.

The three resources, in order of scarcity:

1. **Your attention.** You are one person. Every hour spent assembling context,
   remembering which script rebuilds which report, or re-deriving a decision you
   already made once, is the binding constraint on everything else.
2. **Frontier tokens.** Metered, rationed, shrinking for consumers on a budget.
   The most capable compute you have access to, and the only one you can't scale.
3. **Machine time.** Local GPUs, local scripts, overnight windows. Cheap but slow,
   thermally bounded, and only useful if something routes work to it.

The current toolkit is framed as an *observability* system — "one honest picture
of the estate." That framing is true and insufficient. A picture is only worth
building if it changes what happens next. The reimagining is one move:

> **Stop building a picture that you consult. Build an allocator that consults
> the picture — and brings you only the decisions.**

I'll call it **Quartermaster**, because that's the job: the officer who doesn't
fight, doesn't command, but decides what scarce supply goes where, keeps the
ledger, and makes sure the front line never waits on the depot. It also sits
comfortably beside your knight and your castle.

---

## 2. The unit of throughput is a decision

Here is the systems-engineering reframe that everything else falls out of.

In the current toolkit, the unit of work is an *artifact*: a scan, a report, a
linked thread, a rebuilt dashboard. Artifacts are what the system produces, so
artifacts are what the surfaces show. But artifacts are not why the system
exists. You said it yourself in one line: *"help decisions get made quicker and
more efficiently."*

So Quartermaster's unit of throughput is the **decision** — and everything else
in the system exists to do one of three things to decisions:

- **Reduce their cost.** A decision is expensive when you must assemble its
  context yourself. It is cheap when it arrives pre-assembled: the question, the
  evidence for each side, what each option costs, and a stated default.
- **Reduce their number.** Most things that feel like decisions are actually
  policies you haven't written down yet. The tenth time you decide "refresh data
  before rebuilding the report," that's not a decision, it's a rule — and a rule,
  once ratified, is a decision the system makes for you forever after, citing
  the ruling.
- **Make them durable.** A decision that can't be recovered gets made again,
  badly, by someone who's forgotten the reasoning — usually future-you. This is
  the Chronicler's thesis, and it's correct; it just isn't the *centre* of the
  system. It's the memory of the decision engine.

This gives you a real, measurable definition of "decision velocity": the time
from *a decision becoming necessary* to *a ruling landing in the ledger* —
minus everything the system did to shrink it. That number can go on a surface.
The current toolkit cannot state it, because decisions have no first-class
existence between "queued row" and "DECISIONS.md entry."

---

## 3. The shape: five parts

```
                       ┌──────────────────────────────┐
                       │        DECISION DESK         │  ← the only surface
                       │  cards in, rulings out       │     that asks for you
                       └──────────▲───────┬───────────┘
                                  │       │ rulings
                         decisions│       ▼
 ┌───────────┐  facts   ┌─────────┴───────────────────┐   plans   ┌────────────┐
 │  SENSORS   │────────▶│           LEDGER            │◀─────────│ DISPATCHER │
 │ (read-only)│         │  one queryable substrate:   │──────────▶│ (economic  │
 └───────────┘          │  facts · rulings · runs ·   │  work +   │  router)   │
                        │  costs · provenance         │  budgets  └─────┬──────┘
                        └─────────────────────────────┘                 │
                                                              executes via
                                                                        ▼
                                                          ┌─────────────────────┐
                                                          │      CONTRACTS      │
                                                          │ each project's      │
                                                          │ declared capabilities│
                                                          └─────────────────────┘
```

### 3.1 The Ledger — one substrate, not four stores

Everything the system knows lives in one queryable place, as **events with
provenance**: this fact was observed by that sensor at this commit; this ruling
was made by the operator on this date citing that evidence; this run consumed
this much time and these many tokens and produced that artifact.

The current estate keeps four disjoint stores — `estate.json`, `chronicler.db`,
`DECISIONS.md`, scattered run markers — and the seams between them are where
the 8% linking problem lives. In Quartermaster there is one event log and many
*derived views* (the estate picture, the chat trail, the decision log, the run
history are all queries, all rebuildable, all disposable). The standing
constraint you already wrote holds perfectly here: **the data is irreplaceable;
the derived is free.** One writer. Frozen, versioned schema. Readers open
read-only and refuse what they don't recognise.

The crucial addition is that **rulings, runs, and costs are ledger events too**
— not markdown, not sidecar files. When a ruling is an event, "cite the ruling"
is a foreign key, not a convention. When a run is an event with a cost, the
economics of §5 stop being philosophy and become a `GROUP BY`.

### 3.2 Sensors — honest, read-only, boring

Unchanged in spirit from your scanners, and deliberately so: read-only,
structurally incapable of harm, zero-setup, run anywhere. They observe code,
documents, chat corpora, run outputs, and hardware, and emit facts into the
ledger. The one upgrade: sensors emit **deltas against the last observation**,
not snapshots — because the Desk (§3.3) is driven by *what changed*, and diffing
snapshots after the fact is the expensive way to know.

### 3.3 The Decision Desk — the only surface that spends your attention

The Desk replaces "an app with nine tabs" as the front door. It shows exactly
one kind of object: a **decision card**. A card has a fixed anatomy:

- **The question**, in one sentence.
- **The trigger** — what changed to make this decision necessary now (a sensor
  delta, a completed run, an expired assumption).
- **The evidence**, pre-assembled from the ledger, each item carrying its
  provenance. Not "here are the tabs where you could look" — the looking has
  been done.
- **The options**, each with a stated cost in the three currencies (your time,
  frontier tokens, machine time) where the system can estimate it — and per
  your own rule, no estimate where there is no measurement.
- **A default and an expiry.** What happens if you don't rule, and when. Some
  cards decay harmlessly ("stale report — rebuild next idle window unless
  vetoed"). Some block plans and say so. Silence is itself an input, and it is
  always explicit what silence does.

Ruling on a card writes a ledger event. Ruling the *same shape of card* three
times prompts the second-order card: **"promote this to a policy?"** — which,
if ratified, becomes a standing rule the Dispatcher applies automatically, with
the policy itself carrying provenance back to the three rulings that spawned
it. This is the mechanism that *reduces the number of decisions*, and it is the
piece nothing in the current toolkit does: your DECISIONS log records rulings
beautifully, but nothing executes them.

Everything that is not a decision card — dashboards, browsers, transcripts,
Datasette-style free query — still exists, but as the **reference room**, one
level down, reached from a card's evidence links. You go there because a card
sent you, not to patrol.

### 3.4 The Dispatcher — the economic router

The Conductor, grown up. Its inputs are the ledger (what work exists, what it
has cost before), the contracts (§3.5, what each project can run), the budgets
(frontier envelope, thermal profile, time window), and the policies (ratified
standing rules). Its output is the same thing your 0037 already demands:
**a plan, proposed, shown with stated provenance, approved before it runs.**

What makes it a *router* rather than a scheduler is the capability ladder. Every
plannable task carries a declared **minimum capable tier**:

```
T0  deterministic script      (free, instant, always preferred)
T1  local small model         (cheap, fast, good enough for routing/classify)
T2  local large model         (K2-class extraction, thermally budgeted)
T3  frontier                  (metered; spent only per §5)
```

The Dispatcher always plans at the lowest capable tier, escalates only on
evidence (a T2 run that failed its own acceptance check is evidence; a hunch is
not), and **every escalation is itself a ledger event with a cost** — so over
time you get the one report that governs the whole budget question: *what did
each tier actually deliver per pound and per hour?* Calibration before
estimation, measurement before planning, spread not just mean — your Conductor
brief already got all of this exactly right. Quartermaster just widens it from
"GPU minutes" to all three currencies.

### 3.5 Contracts — every project declares what it can do

Your `wizforge.manifest.json` instinct, promoted to the universal joint of the
system. Every participating repo — personal or work — carries a committed,
versioned, validated manifest declaring its runnable stages: fixed argv, no
parameter slots, declared outputs, declared freshness source, declared
dependencies. The toolkit executes only what a manifest declares, only from an
allowlisted root, only under lock, streaming, with four outcomes and no fifth.

This is also, not incidentally, **the work-transferable pattern**. At work, the
frontier can never touch the systems — but a manifest is just JSON, the runner
is just local Python, and the Desk pattern ("cards with evidence and defaults,
rulings with provenance") is a way of *working*, not an AI integration. The
whole left half of the diagram ships anywhere; only T3 in the ladder is
personal.

---

## 4. One piece of work, end to end

To make it concrete — the pricing report, in Quartermaster:

A sensor notices the upstream data changed (delta event). A ratified policy —
promoted from your third identical ruling weeks ago — says stale data on this
project triggers a refresh-then-rebuild plan at the next idle window. The
Dispatcher drafts the plan: two T0 stages from the repo's contract, estimated
at four minutes from the last nine measured runs, spread stated. Because the
policy is ratified, no card is raised; the plan runs in the overnight window,
under lock, streamed, logged as ledger events with costs.

One stage fails its acceptance check. *Now* a card is raised: the question
("rebuild failed — output row count dropped 40%"), the trigger, the evidence
(the diff, the stage log, the last three green runs), the options ("accept the
new output — upstream really shrank", "hold and investigate", "escalate the
diff summary to T2 for an explanation, est. 6 GPU-min"), and the default
("hold; nothing downstream consumes this until ruled"). You rule in ninety
seconds over morning coffee, on your phone, because the assembly work was the
expensive part and the system did it.

Your attention was spent exactly once, at the one point a human was worth more
than a policy. That is decision velocity — not deciding faster, but **deciding
only where deciding pays.**

---

## 5. The frontier economy: tokens are capital, not fuel

The budget-efficiency thesis, stated as a rule the Dispatcher can enforce:

> **Frontier tokens may only be spent on two things: rulings that unblock
> plans, and artifacts that permanently lower the cost of future work.**

The first is the escalation path in §4 — a T3 call whose output is *judgment*,
attached to a card, feeding a ruling. Expensive, rare, and worth it, because it
unblocks machine-time work that was stalled on ambiguity.

The second is the one that compounds, and it deserves a name: the
**distillation loop**. When T3 does something well — writes the extraction
rubric, produces the few-shot examples, designs the prompt that makes K2-class
extraction reliable — that output is committed as an artifact (a prompt, a
rubric, an eval set) that *raises the ceiling of the local tiers*. Frontier
spend that only produces an answer is fuel: burned once, gone. Frontier spend
that produces a reusable artifact is capital: it moves work permanently down
the ladder. The ledger can literally measure this — "T2's acceptance rate on
extraction rose from 61% to 84% after rubric v3, retiring an estimated N
frontier calls/month" — and that measurement is the whole game for a consumer
on a tight budget.

Concretely, the frontier envelope becomes a first-class budget object like your
thermal profiles: a weekly allowance, drawn down by logged spend events,
visible on the Desk, with the Dispatcher refusing (not clamping — your rule) a
plan that would exceed it. Where usage caps are opaque, treat the envelope as
what it really is: your best current estimate, stated as such.

---

## 6. What survives from the repo — the honest audit

Almost everything, which is the reassuring part: this is a re-centring, not a
rewrite. The estate has been building Quartermaster's organs; what's missing is
its circulatory system (one ledger) and its head (the Desk).

| Exists today | Becomes | Verdict |
|---|---|---|
| Scanners + read-only/stdlib contract + auditors | Sensors, near-unchanged; add delta emission | **Keep** — this layer is already right |
| Chronicler pipeline + vault | One ingest adapter feeding the ledger; the vault schema is a strong starting substrate | **Keep, absorb** — its frozen-schema discipline generalises to the whole ledger |
| Command Deck / module registry | The reference room; the registry pattern already proved a new surface is "one registration + one view" | **Keep as chassis** — the Desk becomes the tenth module, then the first |
| Review queue + rulings | Decision cards, minus the assembly and defaults they don't yet have | **Grow** — the card anatomy is the upgrade |
| DECISIONS.md + 0033 propose/ratify/execute | The policy engine's input format; rulings become ledger events that *execute* | **Grow** — from record to mechanism |
| Conductor (planner, ledger, governor, 0037) | The Dispatcher's T2 lane, and the template for every other lane | **Generalise** — the calibration-before-estimation discipline is the crown jewel |
| Project Wizard + manifest + 0042 | Contracts, verbatim; `depends_on` and `kind` were future-proofed for exactly this | **Promote** — from side-panel to universal joint |
| verify.py gate, INTENT, the wall | Unchanged | **Keep** — the governance is the part a seasoned engineer would *not* redesign |
| Mesh mode | Still mothballed; the ledger being one substrate makes an eventual sync *simpler*, not urgent | **Leave parked** |

And the two hard truths the clean slate can't dissolve:

**The 8% problem doesn't go away — it gets reframed.** Evidence-assembly on
cards is only as good as the linking underneath it. But the Desk changes the
economics of fixing it: instead of "link 332 threads" as an abstract backlog,
every card that surfaces with thin evidence is a *specific, motivated* linking
task — and a T1/T2 job the Dispatcher can schedule into idle windows. Linking
stops being a project and becomes a standing maintenance lane whose value is
visible every time a card arrives well-armed.

**INTENT failure mode #1 is watching.** A system built to detect
talked-not-built, elaborately reimagined in a vision document, is a joke that
writes itself. The mitigation is the same one your briefs already practise:
the first build slice must be small enough to ratify in one round and useful on
day one. My candidate: **the card, alone** — one decision type (failed-run
triage or stale-report), assembled from what the ledger-of-today can already
answer, with a default and an expiry, landing as one module in the existing
deck. No new substrate, no router, no economy. If living with ten real cards
for two weeks doesn't visibly move your decision latency, the rest of this
document doesn't deserve to be built — and that finding would be cheap.

---

## 7. What this is not

Not a product; one operator, same as INTENT §4. Not automated judgment — the
Desk *narrows* what reaches you, but nothing rules except you, and promoted
policies are rulings you made, executing with citation. Not a frontier
integration for work — the work-shaped subset is manifests, local runners, and
a way of structuring decisions. And not a rewrite: every guarantee the estate
bled for — structural not behavioural, fail loud, one writer, read-only until
proven otherwise, measurement before estimation — is load-bearing here. The
clean slate kept your constraints and discarded only your framing.


# Quartermaster — the build plan

*From the vision (VISION_quartermaster.md) and Tim's four rulings of
2026-08-17: chronicler as substrate with the Knowledge Curator as the linking
engine; ledger-first rulings with DECISIONS.md rendered; stale-output triage as
the first card; the vision landing as an INTENT append with decision points
carried in this plan. Each phase below is sized to become one COWORK_BRIEF.
Decision points are lettered D-A…D-F; numbers get assigned in DECISIONS.md at
ratification, in whatever order the phases actually ratify them.*

---

## The shape of the whole plan in one paragraph

Five phases, each independently valuable, each falsifiable before the next
starts. Phase 1 proves the card mechanic against today's stores with no new
substrate. Phase 2 makes chronicler.db the ledger by governed migration and
inverts DECISIONS.md to a render. Phase 3 fixes linking by making the Curator's
claim engine the linking engine, with ratification flowing through cards.
Phase 4 grows the Conductor into the Dispatcher — tiers, policies, the
frontier envelope. Phase 5 closes the loop: distillation artifacts and the
work-transferable extraction. If Phase 1 fails its two-week test, everything
after it is cancelled and the estate has lost one small module.

---

## Phase 0 — ratify the frame

Append the INTENT §8 draft (separate file, edited by you — the tension notes
tell you where it must be reconciled with §4). Ratify:

**D-A — The unit of throughput is a decision; the Desk is the front door.**
A decision card's anatomy is fixed: question, trigger, evidence-with-
provenance, costed options, default, expiry. A surface that wants the
operator's attention raises a card; everything else is reference. Silence is
an input and its consequence is always stated on the card. *Consequence:* new
surfaces are justified by the decisions they move, not the facts they show.

**D-B — Frontier tokens buy rulings or durable cost reductions, nothing
else.** The two legitimate purchases: judgment attached to a card, and
artifacts (prompts, rubrics, eval sets) that measurably move work down-tier.
Spend is logged as events with stated purpose; the envelope is self-reported
and says so. *Consequence:* "just ask the frontier" becomes a plannable,
budgeted act rather than an ambient habit.

Phase 0 is a documentation round: the INTENT append, D-A and D-B entered as
proposed, ratified after a re-read. No code. **Exit:** both entries accepted;
the INTENT tension with §4 resolved in writing, not left as a note.

---

## Phase 1 — the first card: stale-output triage

**One brief, one module, two weeks of live use, then a verdict.**

Builds directly on what exists: the Project Wizard already knows per-stage
freshness (self mtime or delegated), the module registry already makes a new
tab one registration plus one view, and `docs_board`'s derive-never-store is
the rendering discipline.

- A `desk` module in the existing deck. On every render it derives cards
  fresh: for each wizard-known stage whose declared inputs are newer than its
  declared output (or whose delegated freshness says stale), raise one card.
- Card anatomy per D-A, with the honest v1 reductions stated on the card:
  evidence is what today's stores can answer (freshness facts, last run
  outcome, the manifest's declaration, latest relevant thread *if* a link
  exists); options are `rebuild now` (runs the existing wizard stage, same
  lock, same streaming, same four outcomes), `snooze until <event/date>`, and
  `dismiss with reason`; the default is `hold — nothing runs`, because in v1
  **no policy engine exists and no expiry may act**. Expiry in v1 only
  re-raises with an "aged" marker.
- Rulings append to `data/desk/rulings.jsonl` — deliberately a sidecar, not a
  chronicler table, because Phase 2 owns the schema question. Each event:
  card fingerprint, ruling, reason, timestamp, evidence refs. The file is the
  seed corpus Phase 2 migrates into the ledger, and Phase 4's promotion
  detector reads it ("three identical rulings on this card shape").
- Instrument the one number: time from card first raised to ruling landed.

**Exit test (the falsifier):** after two weeks of real use — did cards reach
you with the evidence you actually needed, and is decision latency on stale
outputs visibly better than patrol-and-remember? If no: stop, write the
report, keep the wizard, cancel Phases 2–5. If yes: Phase 2 is justified by
lived data, not by this plan.

---

## Phase 2 — the ledger: chronicler.db grows up, DECISIONS.md inverts

The substrate ruling made real, without endangering the vault.

**D-C — The ledger is chronicler.db, extended by governed migration; the
vault contract survives by version, not by freeze.** New tables (`events`:
facts, rulings, runs, costs, spend — append-only, provenance columns
mandatory) land via a migration that bumps `user_version`; every reader's
version guard is updated in the same round, so the fail-loud contract does
exactly its job. The irreplaceable tables (`threads`, `messages`,
`attachments`) are untouched by the migration and stay owned by the pipeline;
the single-writer rule extends by column/table scope exactly as the review
endpoint already proved. *Consequence:* "frozen" was always a means to
"never misread"; versioned-and-guarded achieves the same end and permits
growth. A backup (`VACUUM INTO`, off-box) is a precondition of the migration
running at all — this is also the moment to land the standing backup fix.

**D-D — Rulings are ledger events; DECISIONS.md is a render.** The append-only
markdown log becomes DB→file output, one-directional, same as every other
render in the estate (the discipline that already survived the estate's one
data-loss incident points this way). A one-time parse walks the existing
0001–004x entries into ruling events, human-verified entry by entry — the
history is too valuable to trust to a parser unreviewed. Authoring moves to a
small entry form or CLI that writes the event; the render regenerates the file
the auditors and readers already know. *Consequence:* "cites 0037" becomes a
foreign key; Phase 4's policies can execute with real provenance.

Phase 1's `rulings.jsonl` migrates in; run/cost events start flowing from the
wizard and conductor runners (they already know outcome, duration, and stage —
they just don't write it anywhere durable).

**Exit:** gate green with updated version guards; a ruling authored through
the new path renders into DECISIONS.md byte-stable; the walked proof that a
reader with the old guard refuses loudly.

---

## Phase 3 — linking through the Curator: the 8% problem gets an engine

Your ruling: the Curator is the better route for linking, and the fix belongs
somewhere definite. This phase is that somewhere.

The insight the Curator already proved: **claims are the right granularity.**
`relink.py` links whole threads on thin signals; K2 extracts quoted,
verbatim-anchored claims and K4 confirms matches in two stages. A thread whose
claims match a project's code and knowledge corpus is linked *by evidence you
can read* — which is the only kind of link INTENT allows you to trust.

**D-E — Thread↔project linking is derived from Curator claims and ratified
through cards; the Curator's read-only rule is preserved by writing through
the ledger, not by the Curator.** The Curator stages stay read-only exactly as
SPEC'd. A new match target joins their pass: claims are matched not only
against KNOWLEDGE files but against project identity signals (paths, names,
the estate registry). Confirmed matches become *link-proposal events* in the
ledger. The Desk raises the second card type — thin-evidence linking cards:
the claim, the quoted source, the proposed project, confidence per the
existing order. A ratified card writes `link_evidence` + `project_link`
through the same narrow ruling path the review endpoint established.
`relink.py` demotes to a fallback for corpora with no extracted claims yet.
*Consequence:* linking becomes a standing lane — the Dispatcher-of-today
(the Conductor) can schedule K2/K4 into idle thermal windows, and every
Curator run now compounds into coverage, not just reports.

**Exit:** the substantive-thread linking coverage number, re-derived, moves —
that is the whole test. INTENT's scoreboard, not a new one.

---

## Phase 4 — the Dispatcher: the Conductor learns the ladder

The Conductor generalised, keeping every discipline 0037 established
(ratified plans, declared parameter schemas, measurement before estimation,
refuse-don't-clamp).

- **The tier ladder declared in the stage table:** every runnable stage —
  wizard stages, K-stages, future T3 calls — carries its tier (T0 script /
  T1 small local / T2 large local / T3 frontier) and its acceptance check.
  Plans state their tier mix and total cost in all three currencies.
- **Escalation on evidence:** a stage failing its acceptance check may
  propose (never auto-run) the next tier up, as a card, with the failure
  evidence attached and the cost stated. This is D-B's first purchase route
  made mechanical.
- **Policy execution:** the promotion detector reads ruling events; three
  matching rulings raise the "promote to policy?" card; a ratified policy
  (itself a ruling event, citing its parents) lets the Dispatcher plan and
  run that card shape without raising it — with revocation as one act, per
  the INTENT append.
- **The frontier envelope:** a budget object beside the thermal profiles;
  spend events drawn against it, self-reported and labelled as such; a plan
  that would exceed it refuses.

**D-F — (carrier decision for the above, drafted at brief time):** the tier
ladder and escalation rules as a widening of 0037/0042's execution posture —
this one needs the code in front of it to be drafted honestly, so the plan
only reserves its slot.

**Exit:** one real week where an overnight window was planned across tiers by
policy, and the estimate-versus-actual (0037's own best number) held.

---

## Phase 5 — the compounding loop, and the work extraction

- **Distillation artifacts as first-class:** a T3 purchase that produces a
  rubric/prompt/eval-set lands as a versioned artifact with a spend event;
  the ledger reports acceptance-rate movement at the tier it was meant to
  lift, and therefore whether the capital purchase paid. No movement, no
  more purchases of that shape — the metric per the INTENT append's third
  failure mode.
- **The work-transferable subset extracted:** contracts + runner + desk
  pattern as a package with no vault, no frontier tier, no personal data —
  the import direction (package never imports estate) enforced the same way
  `auditor_dependency_direction` already polices the app tier. This is where
  the "patterns reusable at work" goal is cashed, deliberately last, because
  extracting a pattern before it has survived personal use ships a guess.

**Exit:** the toolkit's own answer to D-B, from the ledger: what did frontier
spend retire this quarter?

---

## Standing risks, named once

1. **Phase 2 touches the vault's neighbourhood.** The migration precondition
   (off-box backup, walked restore) is not ceremony; it is the one phase with
   an irreversible failure mode. Everything else in this plan loses only time.
2. **Card flood is the Desk's failure mode, not card famine.** Phase 1
   deliberately picks a card type that fires steadily; if it floods, the
   dedupe/aging rules get designed against real noise — the Curator's K6
   "seen before, still open" instinct, applied earlier.
3. **The 2am test governs Phase 4's ceiling.** Policies executing overnight
   plans is the most system this plan asks you to own alone. If Phase 4's
   brief can't be debugged from its own surfaces, it ships smaller.
4. **INTENT failure #1 watches every phase.** Each exit test above is a
   permission slip for the next phase, not a milestone to celebrate past.


*— drafted 2026-08-17, from a cold read of the estate at `174e57e`.*