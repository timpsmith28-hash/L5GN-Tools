# Agenda — the running order, 2026-08-28

The planning act that follows `AGENDA_restart_2026-08-28.md`. Frozen at its date.
It names rounds and their gating; it writes no brief and no code, and it ratifies
nothing.

**Host:** `LucasGoonPC`. Every claim below was read out of the tree on this
reading and is cited with its file. Where a source could not be reached the
restart note says so and this file does not paper over it.

> **Amended once, 2026-08-28, later the same day**, on three readings taken on
> the rig after §0 was written: the Desk's trial has reached ten, the linker is
> disarmed by default, and the operator put a naming problem to this thread that
> changes what one card is. §0's finding stands unchanged; §4's order is
> rewritten and the original is not preserved, because an order nobody will
> follow is not evidence of anything. **§2a is new and it is the operator's
> observation, not this thread's.**
>
> **Amended again, same day**, after the `data/git_warden/` sweep: **Card B is
> widened from one defect to three.** The sweep found a commit message for a fix
> that was never made, and the fix it describes is the third of three
> independent ways the relink stage reports nothing true.

---

## 0. The finding that reorganised this document

**A running order already exists in the tree, it is more complete than anything
this thread would have produced, and it is gated shut.**

`docs/investigation/2026-08-17_quartermaster_fable_2-response.md` carries, from
its line 328, a document titled *"Quartermaster — the build plan"*: Phases 0
through 5, with exit tests. It is not filed as a plan, it is not named in
`CLAUDE.md`, and it is encoded in the wild across the brief headers that cite it.
Five of the ten unbuilt briefs are its phases:

| phase | brief | state |
|---|---|---|
| 0 — ratify the frame | `quartermaster_frame` | built; **report never walked** |
| 1 — the first card | `desk_stale_card` | built and walked |
| 1b — staleness as a feed | `staleness_feeds` | briefed 2026-08-19, unbuilt |
| 2 — the ledger | `ledger_migration` | briefed, unbuilt |
| 3 — linking through the Curator | `curator_linking` | briefed, unbuilt |
| 4 — the Dispatcher | `dispatcher` | briefed, unbuilt |
| 5 — the compounding loop | `distillation_extraction` | briefed, unbuilt |

**And the gate on all of it is open, stalled, and eight days cold.**

The plan's own words: *"If Phase 1 fails its two-week test, everything after it
is cancelled and the estate has lost one small module."*
`COWORK_BRIEF_ledger_migration.md` makes it a hard precondition — *"Phase 1's
falsifier answered **yes** in its stamped results."*

`UAT_desk_stale_card_results.md`, read on this reading:

> **D9** The falsifier, answered in one paragraph, yes or no.
> **[DEFERRED]** Cannot be answered honestly before the trial has real signal.

> **D7** … **`cards_raised: 5, cards_ruled: 4`** as of this walk (2026-08-20).
> Six to go.

**Four of ten, last data point 2026-08-20.** Phases 2, 3, 4 and 5 are blocked by
construction on a trial that stopped producing signal eight days ago.

**[AMENDED] The trial has since reached ten.** The Deck's own footer, read on
the rig: `10 cards raised · 9 ruled · 1 resolved without a ruling · median
21.6h`. **D7's condition is met and D9 is answerable today** — which turns Card
A from "decide whether the trial is alive" into "answer the falsifier", a
different and much cheaper act.

Two qualifications the operator supplied, and they belong in the answer rather
than beside it: **a chunk of the ten are fixture tests**, and the trial ran on
**one card type, on one rig**. So D9's honest answer is not a clean yes. It is
closer to *yes, and the trial proved less than the number makes it look like* —
which is still an answer, still unblocks Phase 2, and is worth more than a
clean one because Phase 2's precondition then inherits the qualification instead
of laundering it.

## 1. Why the vision looked too fuzzy to sequence — and why it is not

It is not fuzzy. **It is doubled.** The estate holds two orders, written ten days
apart, and nobody has retired either or mapped one onto the other:

- **The Quartermaster build plan**, 2026-08-17. Five phases, exit tests, encoded
  in briefs. Gated shut at Phase 1.
- **The harness frame**, 2026-08-27. Eight staff, a support framework, a build
  order — `Work_Bridge/to-work/2026-08-27_REQUEST_harness_frame.md` §4 — and its
  shake-down in the matching `REPLY`. Encoded in the bridge, in no brief.

Planning past that would have produced a third order. The reconciliation is the
job, and there is exactly one point where the two touch:

**The harness frame's thin slice is a Quartermaster card type.** The `REPLY` §1
lean — *one rule read by Warden, routed to the Desk, ratified there, and the
ratification leaving a dated artefact in the tree* — is, mechanically, a new card
type on the Desk built in Phase 1. A new card type raises real cards. Real cards
are exactly what D7 has run out of. **The frame's first move and the plan's
blocked gate are the same act**, and neither document noticed, because one lives
in `docs/investigation/` and the other in another repository.

That is the whole reconciliation. Everything below follows from it.

## 2. The judgment on twenty cards in flight

The stop condition was: if twenty in flight starts looking like *finish
something*, follow it. It does, but not where it appeared to.

**The ten unbuilt briefs are not ten unbuilt rounds.** Six of them declare in
their own opening lines that they expect to be rewritten before they are built —
`dispatcher` (*"the most speculative brief in the set"*), `distillation_extraction`
(*"four phases ahead… the furthest horizon"*), `wizard_tiers` (*"written
deliberately early and expected to sit"*), `curator_linking`, `validation_ratify`
(*"without sight of the source it describes"*), `staleness_feeds`. A brief that
says it is a placeholder is not talked-not-built; it is a placeholder doing its
job. **Reading them as a backlog is the error, and it is the error that made the
board look like the problem.**

**The board is not the problem. It is the measurement.** Twenty cards accumulated
because the docs board *displays* and obliges nobody — which is precisely the
`REPLY` §5 finding turned on the repo itself: *the route that works is not
"appears on a surface", it is "produces an obligation with a named owner and a
reply owed."* Twenty in flight is the evidence for that claim, sitting in this
repo, uncounted.

**So: finish something, and the something is the Desk trial** — not ten walks by
hand. Ten hand-walks spend the scarcest of `INTENT.md` §8's three resources on the
one activity that moves neither the thesis nor the gate.

## 2a. "Decision" is the wrong name, and the fix is a mechanism not a taxonomy

**The operator's observation, recorded as his:** *decision* has a very broad
meaning; it scales by how important or far-reaching a thing is, all the way down
to *the data is stale, should we refresh?* — **and sometimes you cannot know the
scale up front.**

The last clause is the load-bearing one, and it rules out the obvious fix. Any
scheme that asks a card to declare its own importance at the moment it is raised
is asking for a judgement nobody has yet. That is `INTENT.md` §4's *"confidence
scores route attention; they don't rule"* arriving as a grading problem.

**The axis that does separate them is not importance. It is whether the answer
outlives its occasion.**

| | *should we refresh the estate report?* | *is the registry corpus or config?* (0055) |
|---|---|---|
| what the answer binds | this instance only | every future instance |
| cost of being wrong | run it again tomorrow | later work cites it and inherits it |
| where it is recorded | an **event** in `events.jsonl` | a **clause** in `DECISIONS.md` |
| how often | daily | rarely |

**And you do not have to grade it up front, because repetition grades it for
you.** The same fingerprint, ruled the same way, N times, is an answer that has
outlived its occasion — measured after the fact, from data the Desk already
keeps. `INTENT.md` §8 already states this exactly: *"a decision made three times
is a policy not yet written down. The system should notice repetition and offer
promotion."*

**So the estate's vocabulary is already correct and only the surface's name is
wrong.** 0048 says *a surface that wants attention raises a card*; `desk.py`
writes `ruling` events; §8 says *standing ruling*. Card, ruling, standing ruling
— three words, correctly used. **"Decision Desk" names the rarest of the three**,
and most of what crosses the Desk is an occasion whose answer expires with it.
Renaming the surface is not worth a round on its own; **building the promotion
step is**, because it dissolves the worry mechanically instead of by
re-labelling, and it is §8's own stated want with no new concept in it.

**The immediate promotion candidate is the operator's own complaint.** The
refresh card fires *"only on a 1 day timer — not on a 'something has changed
should we update?'"*. That is one card type, ruled repeatedly, almost certainly
the same way. Both available fixes are the same insight from opposite ends:
promote the repeated ruling to standing, or trigger on change instead of age.

**And the second of those is already briefed.**
`COWORK_BRIEF_staleness_feeds.md` is titled *"Phase 1b: staleness becomes a
declared feed, not a trigger type"*. The complaint has a brief waiting for it,
written 2026-08-19, unbuilt.

## 3. The thin slice, sized rather than guessed

You asked not to guess at this. Measured on this reading:

| the slice needs | what exists today | lines |
|---|---|---|
| a Desk that raises derived cards with a fixed anatomy, an append-only event store, `ruling` and `resolution` events, hold-by-default, and no execution path | **`chronicler/review/desk.py`** | 725 |
| ratification that is per-row, refuses bulk-accept *"because there is nowhere to put one"*, appends bytes and never rewrites, carries a permanent `[provenance:…]` tag and `[status:corrected]`/`[status:revoked]`, stages and never commits | **`chronicler/review/curator_ratify.py`** | 515 |
| a conformance reader over documents, running in the gate | **`auditors/auditor_doc_claims.py`**, **`auditors/auditor_uat_stamp.py`** | 2 of 12 auditors |

**The slice is not three builds. It is one new card type on a built Desk, one new
rule source, and one artefact writer modelled on `append_ratified_row`.** The
`REPLY`'s worry — *"a Desk shipped first is correct, proven, and empty"* — does
not apply, because the Desk was shipped in Phase 1 and its emptiness is a
measured fact (`cards_raised: 5`), not a risk.

**The rule to read first: `CONVENTION_docs.md` §2's filename-prefix contract.**
It is a rule this repo owns; it is checkable from filenames alone with no corpus
read and no wall crossing; `CONVENTION_docs.md` §8 already names prefix
discipline as the estate's single point of failure; and the `REPLY` §5 names the
knowledge-base viewer as *"pure liability with no output"* precisely because it
can break this contract. One rule, load-bearing, mechanical.

## 4. The order

**Card A — answer D9. CLOSED 2026-08-28.** Answered **yes, at a stated n=2**, in
`UAT_desk_stale_card_results.md`, re-walked and re-stamped at `d4d65c4`.

Two things it turned up that the card did not anticipate. **D9's second limb was
never answerable** — the patrol-and-remember baseline was cancelled on
2026-08-19 and reaching ten was never going to supply it; the yes rests on limb 1
plus judgement, and Phase 2 inherits that sentence rather than a clean pass.
**And the trial's headline median is a fixture artefact**: 21.6h overall splits
into 10.05h across six hand-edited fixture occurrences and 24.36h / 85.34h across
the two clean real ones, against a 24h staleness threshold.

**Phases 2-5 are unblocked, and what they are unblocked by is a qualified yes on
two data points.** That is a weaker permission than the plan assumed it was
granting, and any round that opens on it should cite this line rather than the
word "yes".

**Card B — the relink stage learns to report.** Independent of A; does not
contend with it. **Widened 2026-08-28** from "arm the linker" after the
`data/git_warden/` sweep, which found a commit message describing a fix that was
never made.

**Not one defect — three, and they compound.** The stage the thesis depends on
has no trustworthy report in *any* of its three outcomes:

| outcome | what it reports | why |
|---|---|---|
| **skipped** | nothing; chain green | `CHRONICLER_REGISTRY_PATH` unset resolves under a `GitHub/L5GN` directory that does not exist, so `has_registry()` is False and the stage is skipped before `relink.py`'s own loud `SystemExit` can fire |
| **ran** | `[relink] ok -- no new rows` | `summarize_from_log` reads `ingestion_log`, and **`relink.py` contains zero references to it** (verified, not inferred). The line is vacuous whatever relink did |
| **failed** | exit code, no tail | `run_stage` captures with `capture_output=True, text=True` and **no `encoding=`**, so a non-cp1252 byte destroys the capture. relink prints thread titles; this estate's titles carry emoji |

**The third one has a commit message and no commit.**
`data/git_warden/pipeline_stage_encoding-1.msg` reads *"Fixed on both sides of
the pipe"* in the past tense and names the remedy — `encoding='utf-8',
errors='replace'` on the parent, `PYTHONIOENCODING=utf-8` in the child env.
`run_pipeline.py` lines 150-151 carry neither, and the tree is clean. **The
message is the only artefact of the fix.** It is also, on its own, an instance of
the copy-currency class Card F is about, arriving inside the `git_warden`
mechanism rather than across a machine boundary.

**So the card is "make the stage answerable", not "set the env var."** The skip
must be loud or the default must be right (`INTENT.md` §5 forbids the rule that
survives on the operator's memory; 0048 clause 4 forbids the check that cannot
fail); the success line must say something relink actually did, or say nothing;
and the failure tail must survive a byte the locale cannot decode.

**Sequencing note, and it is the point of widening this card:** arming the
linker *without* fixing the report means the run cannot tell you whether arming
it worked. Scope against 0053 (**proposed**), which already rules on what belongs
in the gate and what belongs beside it.

**Card C — `staleness_feeds`, Phase 1b.** Briefed 2026-08-19; re-verify against
the tree at round-open per its own header. It is the operator's own timer
complaint, already scoped (§2a). It is also the **reader → Desk** half of the
join the work rig asked not to be deferred: a declared feed, read, routed to a
card. *Depends on* **0050** (accepted); touches **0053** (**proposed** — stated
as a dependency, not assumed).

**Card D — the promotion step: a repeated ruling becomes a standing one, and
says so in a dated file.** The **Desk → artefact** half of the same join, and
§2a's mechanical answer to the naming problem. Needs no new rule source: the
fingerprints, occurrences and per-occurrence ruling history are already in
`data/desk/events.jsonl` and already summarised by `desk.latency_summary()`.
Delivers the artefact **both estates found missing independently** — this repo's
*"ratification produces no artefact"* (`CLAUDE.md`, Debts) and the work rig's
`CONVENTION_decisions.md` §10 *"the different-day rule is unobservable"*. Check
overlap with `COWORK_BRIEF_validation_ratify.md` at round-open.

**C and D together are the thin slice**, and they are better than the bespoke one
§3 sized, because both halves already have briefs or data rather than needing a
round invented for them.

**Card E — Governor's route, or Governor is declared furniture.** The `REPLY` §5
calls this *"the strongest single thing we found in your list"*: pacing, cooling
and decay detection are **built**, and where *decay detected* goes is named
nowhere. **The stop condition fires here and this card is the route, not the
component.** It cannot be ordered before C and D, because those are what
establish that a route is a card with an owner and an expiry. E is that route's
first test on something that is not a document.

**Card F — copy currency: the hash manifest.** The class with five recorded
instances and no owner (`REPLY` §6), and the only card here that discharges a
named ask from the other side of the bridge (`REPLY` §0.2). *Depends on* **0057**
(**proposed**). Sharpened by a fact from the rig: **the Deck runs on the gaming
rig only**, so every card type built above has an audience of one machine until
this is answered.

**The conformance card is not first any more.** Reading one convention rule and
routing it to the Desk (§3's sizing still holds) is the natural card after D — it
is the same shape with a new rule source. Putting it second is a **deliberate
deferral of the work rig's §1 request** that the join not be deferred, and the
reason is that C and D test both halves of that join with briefs and data that
already exist, where the conformance card needs a new reader first.

**The order still stops at F.** Phases 2-5 are no longer *gated* — Card A closed
them out — but they are not thereby *ordered*. What they now hold is a qualified
yes on two data points, and the thing that would make them orderable is more real
card types, which is Cards C and D. **Ordering Phase 2 today would be reading the
word "yes" and ignoring the paragraph under it**, which is the failure `INTENT.md`
§5 names as a plausible wrong answer.

### Not in the order, and why

- **`hermetic_gate`** — briefed 2026-08-24 from live diagnosis and current. It is
  gate hygiene gated on **0053** (proposed), not a program card. Run it whenever
  0053 is ratified; it does not belong in this sequence.
- **`conversation_grain`** — briefed with its walk-sheet. Its ruling, **0058**, is
  not in the log at all. Its first mechanical act is appending that draft as
  `proposed` from `data/decisions_draft/0058_proposed.md`.
- **`wizard_tiers`, `model_bench`, `dispatcher`, `distillation_extraction`,
  `curator_linking`, `ledger_migration`** — placeholders or blocked phases, per §2
  and §0.
- **The ten unwalked reports** — not a burn-down. Cards C and D are what should
  raise them, with owners and expiries. If they cannot, that is those cards'
  falsifier and worth more than ten hand-walks.

## 5. Owed a reply, across the bridge

**One correction, and it strengthens their case rather than ours.**
`2026-08-27_REPLY_harness_frame` §1 withdraws the `.gitignore` evidence on the
ground that it *"says nothing about whether a reader would have stopped it,
**because no reader has ever run in either estate**."* That is false for this
repo. `auditors/auditor_doc_claims.py` and `auditors/auditor_uat_stamp.py` run in
the gate today, and the second's own docstring records the incident that produced
it — a stale *"18 testers"* recovered from an archived HANDOFF and laundered back
into a live results log, which nothing could adjudicate because the document
carried no commit.

**That is evidence of the remedy**, which is the exact thing their §1 says neither
side has. It also carries their §0.1 warning intact: `auditor_doc_claims` checks
one claim class on purpose, *"a small auditor that always runs beats a large one
that rots."* A reply is owed and this is its content.

Also unanswered on this side, and named rather than left as ambience: their §0.2
question of whether **0057**'s branch mechanism reaches the work rig or amends
the bridge's third exclusion. Card F touches it; it does not settle it.

## 5a. The 0040 finding, checked — and it lands the other way up

Carried into this thread as: *derived linking ran against a source an accepted
clause excludes it for, it produced the estate's headline improvement, nothing
reported it, and the reason nothing reported it is that the schema records how
confident a link is and not how it was reached.* Checked rather than taken.

**The first half holds.** 0040 clause 1 is `accepted` and reads *"Where a source
carries a stable native conversation id, a curated map keyed on that id is the
join of record. Fuzzy or derived linking is not used for that source."* The
investigation §6b records the eleven `claude-local-personal` auto-links at
0.92–0.96 on title+body alias pairs, *"through the ordinary evidence pipeline
rather than through the exact join"*, and they are most of the 7.85% → 10.42%
rise. `chronicler/pipeline/relink.py` contains **no source predicate of any
kind** — no reference to 0040, to a native id, or to an excluded source. It
cannot honour the clause, and does not try to.

**The second half does not.** The record *can* express the violation.
`link_evidence` carries a `signal` column enumerated
`name_alias|vocabulary|filename_xref|path_mention|time_window`; `threads` carries
`source` with an index on `(source, account)`; and `project_confidence`
separates `exact`, `evidence` and `manual`. **The query that finds every
violation of clause 1 can be written today against the schema as it stands.**

**So the defect is not a rule whose subject the record cannot express. It is a
rule with no reader** — the same shape as `CLAUDE.md`'s own Debt, *"nothing
checks any convention in this file."* That is a better finding than the one it
replaces, because it moves the card from *migrate the schema* to *write the
check* — the conformance card's second rule rather than a round of its own.

**And 0058 already rules on the general case** — a link records the mechanism
that produced it, as a closed value refused at write, on a different axis from
confidence. It is drafted, it is not in the log, and it is the reason
`data/decisions_draft/0058_proposed.md` being unappended is not a filing detail.

**Not settled here:** whether 0056's adjacent shape — a pattern rule enforced by
an enumeration, whose own Consequences admit *"an unknown quantity of latent
non-conformance and no list of it"* — has the same answer. Same question, and it
wants the same reader.

## 6. What this plan assumes, stated so it cannot assume it quietly

- **Five of the seven proposed rulings are load-bearing here** — 0050 is accepted,
  but 0053 gates `hermetic_gate` and scopes Card B, 0057 gates Card F, and
  0051/0052/0054/0055/0056 bound what any of these rounds may touch. **None is
  ratified and this plan does not assume ratification.** Each is a dependency;
  where a card cannot start without one, that is said above.
- **0056's own Consequences admit it creates** *"an unknown quantity of latent
  non-conformance and no list of it."* Producing that list is a real card and it
  is the conformance card's natural second rule. Not ordered here.
- **[AMENDED] The 10.42% figure has now been read on the rig** and holds exactly
  (restart note, gaps §2). It carries one qualification this plan uses:
  `gemini-personal` is 1,194 of 1,330 threads and links at **7.7%**, against
  18.8% and 15.5% for the two Claude sources. **The headline figure is mostly a
  statement about Takeout.** Any card justified by *"does it move the thesis"*
  should say which corpus it moves, because moving the Claude sources moves the
  record the thesis is actually about and barely moves the number.

## 7. What would show this plan wrong

- **[RESOLVED] "The ten were mostly fixtures."** They were: seven of ten
  occurrences, two of three fingerprints. Phase 1's exit test **was** unwalkable
  as written — one card type on one rig could not produce ten independent data
  points, and its second limb lost its instrument six days before the trial
  ended. Answered yes anyway, knowingly. The falsifier fired and the plan
  proceeded with the failure written into its permission slip, which is the
  honest version of proceeding.
- **Cards C and D raise the ten unwalked reports and the operator ignores them.**
  Then a card is not an obligation after all, the `REPLY` §5 finding is wrong,
  and the Desk is furniture with better manners.
- **Card B lands and 10.42% does not move within a month of a refresh.** Then the
  linker was not the constraint, the coverage figure is bounded by the corpus
  rather than by the linking, and Phase 3 (`curator_linking`) is aimed at the
  wrong half. The account table in §6 already hints at this.
- **A month from now the Desk still has one real card type.** Then this plan
  spent its rounds feeding a trial nobody was running, which is `INTENT.md` §6
  failure mode 1 arriving through the instrument built to detect it.
