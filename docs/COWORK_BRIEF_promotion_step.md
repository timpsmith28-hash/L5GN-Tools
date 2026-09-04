# Cowork brief — Card D: a repeated ruling becomes a standing one, and says so in a tracked file

**Where you are:** `C:\Users\timps\Documents\GitHub\L5GN-Tools`, host
`LucasGoonPC`.

**Read before Task 1, in this order:** `CLAUDE.md` at the repo root — it is the
map and it is where the environment hazards live; then `docs/INTENT.md` §8,
which is this round's origin in one sentence; then **0048** (clauses 1 and 5),
**0050** (clause 8), **0059** (clause 4 and its falsifiers) and **0060**
(clauses 1, 2, 4 and 8) in `docs/DECISIONS.md`; then
`docs/AGENDA_running_order_2026-08-28.md` §2a and §4, which is where this card
was framed; then `docs/COWORK_REPORT_staleness_feeds.md`, because this round's
hard precondition is what that report says landed; then this brief in full;
then `docs/UAT_promotion_step.md`, which is the walk-sheet of record and is not
a summary of what follows.

**Draft-status:** written 2026-09-04, **ahead of both cards it depends on**.
`card_completeness` and `staleness_feeds` are unbuilt at drafting, and both
change the ground this round stands on: `card_completeness` adds a fourth ruling
verb; `staleness_feeds` opens the ruling vocabulary per-card and its UAT fixture
writes into the same `data/desk/events.jsonl` this round reads. **Every count in
this brief was taken on 2026-09-04 and will be wrong by round-open** — they are
here to show the shape of the corpus and to give the falsifier a baseline, not
to be trusted. Re-counting is Task 1, not a formality.

**Origin:** `docs/AGENDA_running_order_2026-08-28.md` §2a and §4, and behind it
`docs/INTENT.md` §8: *"a decision made three times is a policy not yet written
down. The system should notice repetition and offer promotion."* §2a's finding
is the reason this is a build rather than a rename: the estate's vocabulary —
card, ruling, standing ruling — is already correct, and *"Decision Desk names
the rarest of the three."* Building the promotion step dissolves that worry
mechanically instead of by re-labelling, with no new concept in it.

It is also the **Desk → artefact** half of the join the work rig asked not to be
deferred, `staleness_feeds` being the **reader → Desk** half.

**Precondition — hard, each checkable:**

- **`card_completeness` closed**, with stamped results at
  `docs/UAT_card_completeness_results.md`. `insufficient` exists in the
  vocabulary this round reads, and the completeness block exists for the
  promotion card to fill like any other.
- **`staleness_feeds` (Card C) closed**, with stamped results at
  `docs/UAT_staleness_feeds_results.md`. Card C makes the ruling vocabulary
  per-card; a detector built against a closed set before C would be rebuilt by
  C. Check: `grep -n "VALID_RULINGS" chronicler/review/desk.py` returns nothing,
  or returns it only as a default option set rather than as the validation
  authority.
- **`COWORK_BRIEF_dispatcher.md` Task 3 is struck**, dated, in that file.
  Check: `grep -n "Struck, Card D" docs/COWORK_BRIEF_dispatcher.md`. Without the
  strike, two live briefs specify the same mechanism and the second one built
  wins by accident.
- **`data/desk/events.jsonl` exists and is readable**, and the counts in Task 1
  can be reproduced twice on an unchanged file.
- **`python verify.py` is GREEN** before the first edit.

**Depends on — this repo's rulings:**

- **0048** — clause 1 (the unit of throughput is a decision; a surface that
  wants attention raises a card — so promotion is offered as a card, never
  applied), clause 5 (**a standing ruling carries a sunset**; a policy expires
  unless renewed, and renewal is itself a card carrying that policy's own firing
  record as evidence), clause 4 (a check that cannot fail trains the eye past
  it; a field identical on every card for months does the same).
- **0050** — clause 8 (the ruling vocabulary belongs to the card, and promotion
  detection reads ruling verbs *and reasons*; recording a refusal as `dismiss`
  would erase exactly the distinction promotion detection is built to read).
  **This round can only half-honour it, and says so** — see *Working rules*.
- **0059** — clause 4 (`insufficient` is a ruling and carries what is missing),
  and its own third falsifier: *"read the `insufficient` rulings' named items
  after a month. If the same item is named three times, the assembling machinery
  has a fixable gap and did not notice — which is 0048 clause 5's promotion test
  arriving from the evidence side."* **0059 named this round's second detector
  before this round existed**, and it is in scope below.
- **0060** — clause 1 (a rule declares the subject it binds, in a form something
  can enumerate; a subject recoverable only from prose is not a declared
  subject), clause 2 (a rule whose subject cannot be enumerated is recorded as
  **unenforceable**, which is a permitted outcome; what is refused is the third
  state, a rule treated as enforced against a substituted subject), clause 4 (a
  rule declares its reader, or declares that it has none), clause 8 (this binds
  rules made from today). **A promoted standing ruling is a rule made after
  0060.** This is the constraint nobody had named on this card, and it shapes
  the artefact's *format*, not merely its location. See *Ratify before code*.
- **0031** — a non-gating surface reports findings, never verdicts.
- **0037** clause 4 — no estimate where no measurement exists. This is why the
  repetition threshold is not in this brief.
- **0045** — report, never repair.
- **0046** clauses 1, 3 and 5 — undo is an append; the last row for a key wins;
  a superseding row says so. Revocation of a standing ruling is an appended row.
- **0030** — an authored file carries rationale, a generated file carries shape,
  and a generated file is never hand-edited.
- **0028** clause 3 — a commit is a human act; a local surface may stage, never
  commit.
- **0033** — propose, ratify, execute; the re-read happens on a different day
  than the drafting.
- **0036** — the mesh stands down; no cross-machine read, write or call.
- **0051** — work-estate rulings are unread by construction.

**Ratify before code — two rulings, and no code lands before both bind.**

**(i) The standing-rulings file's prefix.** `CONVENTION_docs.md` §2 is a
filename-prefix contract, and `docs/` has no prefix for a machine-appended
standing-ruling log. Adding one is a convention amendment, not a file-naming
choice — `docs-archivist`, `auditor_doc_claims` and the doc census all read that
contract. Name the prefix and amend §2 before the writer lands.

**(ii) Whether a promoted standing ruling is a rule in 0060's sense.** It is a
rule made after 0060, so clause 8 puts it in the live subject set — which means
clause 1 requires it to declare an enumerable subject and clause 4 requires it
to declare a reader or declare that it has none.

**And there is a hole here that this brief found rather than inherited.**
`auditor_rule_subjects` prints its own scope on every run:

> `0060 cl.8 carve-out in force -- DECISIONS 0001-0060 and 11 conventions
> predating 0060 classify as undeclared WITHOUT going red. Live subject:
> entries 0061+ and conventions added since.`

A standing ruling in a new `docs/` file is **neither a DECISIONS entry nor a
convention**, so on today's gate it is not a live subject and not a carved-out
one — it is invisible. **The first rules this estate generates rather than
writes would be the first rules with no reader by construction**, which is 0060
clause 4's failure arriving through the mechanism built to answer 0048 clause 5.
The ruling must say which it is: a live subject the auditor is extended to see,
or an explicitly `unenforceable` class under clause 2. **Silence is the third
state clause 2 refuses**, and Task 6 exists to make sure the round cannot end in
it.

Tasks 4, 5 and 6 depend on both rulings. Task 1 (the corpus count) may proceed
before them — it is a read.

**Deliverable:** a repetition detector over `data/desk/events.jsonl` reporting,
per occurrence-grouped fingerprint, how many times it was ruled and with which
verbs, naming every `finding` event that annotates it and excluding nothing; a
`promote?` card raised through the Desk's existing card path, carrying that
occurrence history as its evidence; and, on a `promote` ruling, exactly one
appended row in a tracked, machine-written standing-rulings file naming what was
promoted, its parent occurrences by fingerprint and timestamp, its declared
subject and its declared reader (0060 clauses 1 and 4), and its sunset date
(0048 clause 5). Nothing acts on a standing ruling in this round. **The round is
finished when a standing ruling exists in a tracked file, its parent rulings can
be listed back out of `events.jsonl` by reading that file alone, revocation has
been walked as an append, and `verify.py` is green.**

---

## What the corpus actually holds, counted 2026-09-04

Read directly from `data/desk/events.jsonl`. **These numbers will have moved by
round-open** — Card C's UAT fixture writes into this same file — and Task 1
re-counts. They are here because the round's falsifier needs a baseline and
because three of them change the design.

**39 events: 14 `ruling`, 12 `sighting`, 11 `resolution`, 2 `finding`.**

| | |
|---|---|
| rulings by verb | `rebuild` × 12, `snooze` × 2 |
| rulings by fingerprint | `57860823ba56c2c7` × 6, `652d40c4fd26e2a9` × 5, `78a5d9f55fb2dcca` × 3 |
| annotated as not-real | `57860823ba56c2c7` — a `finding` event records it as *"a button test from fixing the estate_freshness stage command… not real trial data"* |

**Three consequences, and each of them is a design decision this brief takes
rather than discovers mid-build.**

**1. A naive detector's first promotion is a button test.** Six of the fourteen
rulings sit on a fingerprint a `finding` event explicitly disowns. This round
**counts it anyway and reports the contamination** (0031: findings, never
verdicts) — the operator rules on a card that names the annotation verbatim
rather than on a number that quietly excluded it. The alternative, excluding by
annotation, gives a `finding`'s prose authority over a count, which is a new
power for that event kind and not one this round grants.

**2. A `ruling` event cannot say what it is about.** Its keys are
`fingerprint`, `ruling`, `reason`, `ts`, `occurrence_started_at`, `until`,
`evidence_refs`. **No `repo_key`, no `stage_key`, no card text** — the
fingerprint is a one-way hash of `(repo_key, stage_key, trigger_kind)`
(`desk.py:420`). The only human-readable description of what a fingerprint *is*
lives on the opening `sighting`'s `card_summary`, as prose. So the promotion
card's evidence must join ruling → occurrence → opening sighting, and that join
is this round's one hard dependency on data that already exists. If it does not
hold, the card renders an opaque hash and there is nothing to rule on.

**3. The reasons carry no operator signal.** Every one of the fourteen reads
`"rebuilt via card"`, `"snoozed via card"` or `"rebuilt via card: success"` —
written by the run path, not typed by anyone. 0050 clause 8 says promotion
detection reads verbs *and* reasons. In this corpus the reasons are boilerplate.
**This round therefore detects on verbs, and states that as a limit rather than
pretending otherwise.** Making `reason` operator-supplied is named out of scope
below, and the report is required to say whether verb-only was enough in
practice.

## Working rules

- **The detector reports; it does not judge.** It counts, and it names
  contamination. It does not exclude, weight, rank or grade (0031). The operator
  rules.
- **N is not in this brief.** Task 1 counts the corpus and *proposes* a
  repetition threshold with the count in front of it; the number is ratified,
  not coded from a guess. Setting a threshold finer than the corpus can support
  is 0037 clause 4's fabricated distinction, and this corpus is small enough
  that the temptation is real.
- **Evidence is verb-only, stated rather than silent.** See the count above.
- **The standing-rulings file is machine-written and never hand-edited**
  (0030). Every correction is an append; the last row for a key wins and a
  superseding row says so (0046).
- **The writer stages; it never commits** (0028 clause 3).
  `curator_ratify.append_ratified_row` is the model to copy, not a pattern to
  reinvent: pure append with no code path that can rewrite a byte already on
  disk, a refusal on duplicate rather than a silent overwrite, and staging
  without committing. **Copy its shape and cite it.**
- **A promoted ruling has no execution path.** Nothing in this round plans,
  authorises or runs anything. The standing ruling is a record that a decision
  has outlived its occasion — acting on it is a later round.
- **One occurrence replay.** `_reconstruct_occurrences` and
  `_occurrence_key_for_ruling` already exist and `latency_summary()` already
  uses them, for the reason `_reconstruct_occurrences`'s own docstring gives —
  *"all see the same replay rather than three."* A second replay beside them is
  a stop condition.
- UTF-8 explicit, UTC ISO-8601.

## Tasks

1. **Count the corpus, then propose N.** A read-only report over
   `data/desk/events.jsonl`: occurrences per fingerprint, rulings per
   occurrence, verb distribution, and **which fingerprints carry a `finding`
   event referencing them**, with the finding's text verbatim. Propose the
   repetition threshold with those numbers visible, and ratify it before the
   detector is written (0037 clause 4, 0033). Record the numbers in the report
   whatever N turns out to be — they are the falsifier's baseline.

2. **The detector.** `desk.promotion_candidates()`, over the same occurrence
   reconstruction `latency_summary()` uses. Returns, per fingerprint:
   occurrence count, ruling verbs in order with their timestamps, whether it
   meets N, and a `contamination` list naming every `finding` event that
   references it, verbatim. **Counts everything; excludes nothing.**

3. **The `promote?` card.** Raised through the existing card path and filling
   0048 clause 2's anatomy as amended by 0059 — question; trigger (*"this
   fingerprint has been ruled `<verb>` N times across N occurrences"*); evidence
   = the occurrence history, the contamination notes, and **the opening
   sighting's `card_summary`, so the card says in words what the fingerprint
   is**; options `promote` / `refuse` / `insufficient`; default `hold`; expiry.
   Its completeness block derives like any other card's. A fingerprint that
   meets N and is ruled `refuse` does not re-raise on the next render at the
   same count.

4. **The standing-rulings writer.** One appended row per `promote` ruling,
   modelled on `append_ratified_row`. The row carries: what was promoted; the
   parent occurrences (fingerprint, `opened_at`, and each ruling's `ts`), so the
   parents are resolvable back out of `events.jsonl` **by reading the row
   alone**; the declared subject in an enumerable form and the declared reader
   or an explicit `none` (0060 clauses 1 and 4); the sunset date (0048
   clause 5); and the contamination notes that were on the card when it was
   ruled — because a promotion made over a known-contaminated count should say
   so on its own face rather than in a report nobody re-reads.

5. **Revocation as an append.** One act (the dispatcher brief's own standing
   requirement), appended, never an edit (0046). A revoked standing ruling stays
   present in the file and reads as revoked; it is never absent from it.

6. **Answer the reader question explicitly, in one of exactly two ways.**
   Either a gate reader that enumerates standing rulings and reports those with
   no declared subject or no declared reader — 0060 clause 2's permitted
   `unenforceable` outcome, reported never repaired (0045) — **or** a recorded
   statement, in the file's own header and in the report, that this round
   declares the class unenforceable and why. **Not silence.** Silence is the
   third state 0060 clause 2 refuses, and it is the default outcome if this task
   is skipped, which is why it is a task and not a note.

7. **The `insufficient`-item detector, if there is anything to detect.** 0059's
   third falsifier is the same repetition test arriving from the evidence side:
   the same missing item named three times means the assembling machinery has a
   fixable gap. Run the same counter over `insufficient` rulings' named items.
   **If `card_completeness` produced too few to count, that is the answer** —
   record the count, build nothing, and say the falsifier is not yet answerable.
   Do not build a detector for an empty set.

## Explicitly out of scope

- **The renewal card.** 0048 clause 5 requires a standing ruling to be renewed
  by a card carrying its own firing record as evidence. That is the **next
  round**, deliberately sequenced after this one so the two mechanisms are built
  and walked separately. **Named consequence, not absorbed:** the standing
  rulings this round writes carry a sunset date that nothing acts on — an inert
  field of exactly the kind 0048 clause 4 warns trains the eye past it. Accepted
  for one round. **If the renewal round has not opened before the first sunset
  date falls, that is a finding and the report's reader should be told to expect
  it.**
- **Anything that acts on a standing ruling** — planning, authorising,
  executing, a policy consulted when drafting. `COWORK_BRIEF_dispatcher.md`
  Tasks 1, 2 and 4.
- **The ledger (Phase 2).** Dispatcher Task 3 wanted the policy as a *ledger
  event*; there is no ledger. See the deliberate widening below.
- **Making `reason` operator-supplied** on `rule()`. Related and measured above,
  but it is a change to the ruling path that Card C also touches, and folding it
  in here means this round's own corpus changes shape mid-round.
- **Excluding fixture, annotated or contaminated rulings from the count.** The
  detector names them; it does not remove them.
- **Any change to fingerprints, to `latency_summary()`'s five figures, or to
  Triggers A and B.**
- **Reading work-rig rulings** (0051), or any cross-machine read, write or call
  (0036).
- **A promotion that writes to `DECISIONS.md`.** The standing-rulings file is
  not the decisions log and does not become one in this round.

## The one deliberate widening, named

**`COWORK_BRIEF_dispatcher.md` Task 3 specified promotion as *"the policy as a
ledger event with parent citations."* This round writes a tracked file
instead.**

Why: the ledger is Phase 2 and does not exist. Waiting for it means the artefact
**both estates independently recorded as missing** — this repo's *"ratification
produces no artefact"* (`CLAUDE.md`, Debts) and the work rig's
`CONVENTION_decisions.md` §10 *"the different-day rule is unobservable"* — stays
missing through two more phases, having already been named on two rigs.

**What still bounds it:** the row's shape is the ledger row's shape — parent
citations by fingerprint and timestamp, appended, never edited, staged never
committed — so Phase 2's migration is a reader change and not a redesign. And
the carve-out is made visible from both directions: **dispatcher Task 3 is
struck in that file, dated 2026-09-04**, following the 0049 precedent already in
it, so a reader of either brief finds the other.

**A second, smaller widening, named because it will be inherited:** this round
creates *rules* by machine, which no mechanism in this estate has done before.
0060 clause 8 binds them. That is not a licence taken quietly — it is the whole
subject of *Ratify before code* (ii) and of Task 6.

## Stop conditions

- Any code lands before both *Ratify before code* rulings bind → stop.
- The detector excludes, weights, ranks or grades any fingerprint → stop
  (0031). It counts and it names.
- N is coded before it is ratified against an actual count → stop (0037
  clause 4).
- A second occurrence replay appears beside `_reconstruct_occurrences` → stop.
- The standing-rulings file is hand-edited, or any byte already written is
  rewritten → stop (0030, 0046).
- Anything in this round runs `git commit` rather than staging → stop (0028
  clause 3).
- A standing ruling authorises, plans, or runs anything → stop; nothing acts in
  this round.
- A standing ruling is written with no declared subject **and** no declared
  reader **and** no explicit `unenforceable` → stop; that is 0060 clause 2's
  refused third state, and it is what happens by default if nobody notices.
- The promotion card's evidence cannot name what a candidate fingerprint *is* —
  the join through the opening sighting's `card_summary` fails → stop and fix
  the join. A card rendering an opaque hash is not a card the operator can rule.
- `latency_summary()`'s five figures move against the pre-round event log →
  stop; Phase 1's corpus is the trial's whole output.
- The standing-rulings file acquires a query interface, an index, or a second
  writer → stop; it has become the ledger, out of order, and the widening above
  is bounded precisely by its not doing that.
- Task 7 builds a detector over an empty or near-empty set → stop; that is a
  check that cannot fail (0048 clause 4).

## UAT — acceptance checks (Tim walks these)

**Falsifier for this round:** *does anything ever get promoted?*

Measured 2026-09-04, the corpus holds eight real rulings across two real
fingerprints, and twelve of fourteen verbs are `rebuild`. If, at the N ratified
in Task 1 and **one month after this round closes**, nothing has been promoted
and nothing has been *refused* promotion either, then INTENT §8's *"a decision
made three times is a policy not yet written down"* has no instance in this
estate's actual traffic. **The consequence, written before the answer:** the
promotion step is furniture and is **deleted**, not left dormant — and 0048
clause 5's sunset clause loses its only mechanism and is re-argued rather than
kept as intent.

- `[G]` Task 1's corpus report, re-run on an unchanged `events.jsonl`, produces
  identical counts twice.
- `[G]` The report names every `finding`-annotated fingerprint with the
  finding's text verbatim, and **the count for that fingerprint is not
  reduced.**
- `[G]` `promotion_candidates()` and `latency_summary()` agree on occurrence
  counts per fingerprint — a diff of the two occurrence sets is empty — and the
  round's diff contains no second occurrence replay.
- `[G]` `latency_summary()`'s five figures are unchanged against the pre-round
  event log.
- `[G]` A fingerprint at N−1 raises no promotion card; the same fingerprint at N
  raises exactly one; ruling it `refuse` and then reaching N+1 does not raise a
  second at the same count.
- `[G]` The promotion card names, **in words on the rendered board**, what the
  fingerprint is — read from the opening sighting's `card_summary`, not from the
  hash.
- `[G]` A `promote` ruling writes exactly one appended row, and the file's prior
  bytes are unchanged — compare a hash of the prefix, not a visual diff.
- `[G]` A second `promote` on the same fingerprint returns an already-promoted
  refusal and **writes nothing**.
- `[G]` The written row carries a declared subject, a declared reader or an
  explicit `none`, a sunset date, parent occurrences resolvable back to
  `events.jsonl` by fingerprint and timestamp **by reading the row alone**, and
  the contamination notes that were on the card when it was ruled.
- `[G]` Revocation appends; the revoked row is still present and reads as
  revoked; nothing earlier in the file was rewritten (hash the prefix before and
  after).
- `[G]` Nothing in the round commits. After a promotion, `git status` on Windows
  shows the file modified or staged, never committed.
- `[G]` Task 6's answer is visible in the tree: **either** a new reader runs in
  the gate and reports standing rulings with no declared subject or reader,
  **or** the file's own header states the class `unenforceable` in 0060
  clause 2's terms. Not neither.
- `[G]` No standing ruling authorises, plans or executes anything — a search of
  the round's diff for an execution path reading the standing-rulings file finds
  none.
- `[G]` Task 7's answer is recorded: the count of `insufficient` rulings and
  their named items at round-open, and either a detector built over a set large
  enough to detect on, or a statement that 0059's third falsifier is not yet
  answerable.
- `[G]` `python verify.py` → GREEN.
- `[H]` **Promote one real thing.** Rule a promotion card on a repetition you
  actually recognise. Was the evidence enough to promote on, or did you go and
  read `events.jsonl` yourself? **Going hunting is the finding**, and it is a
  finding about the join in Task 3, not about you.
- `[H]` **Read the standing ruling back a week later, cold.** Does it say what
  it binds and who reads it — or does it read as a note to yourself? This is
  0060 clause 1's test applied to the first rule this estate *generated* rather
  than wrote, and it is the check most likely to fail.
- `[H]` **The naming question, answered by the mechanism rather than by
  re-labelling.** `AGENDA_running_order_2026-08-28.md` §2a claimed that building
  this dissolves the *"Decision Desk names the rarest of the three"* worry. Does
  it? Or does the Desk still feel like the wrong name — in which case §2a's
  mechanical answer failed and renaming is back on the table as its own round.

**`[H]` count: 3.** Each asks about the operator's experience rather than the
code's behaviour. The first cannot be mechanised because "was the evidence
enough" is the question the whole card anatomy exists to serve and no assertion
can answer it. The second is a cold-read judgement that only time and a person
can supply. The third is a judgement about whether a mechanical answer actually
dissolved a felt problem, which is by construction not mechanical.

## Reporting

`docs/COWORK_REPORT_promotion_step.md`, walk-sheet
`docs/UAT_promotion_step.md`, stamped results
`docs/UAT_promotion_step_results.md`.

Record, specifically:

- **Both *Ratify before code* rulings as ratified**, what the re-reads changed,
  and — for (ii) — which of 0060 clause 2's two permitted outcomes the standing
  rulings class landed in.
- **N, and the count it was set against**, with Task 1's full corpus numbers at
  round-open, so the round's falsifier has a baseline that is not this brief's
  stale 2026-09-04 figures.
- **Whether the sighting join held for every candidate**, and for any it did not,
  what the card showed instead.
- **The standing-rulings row, field by field**, and whether declaring an
  enumerable subject (0060 clause 1) turned out to be possible for a rule
  derived from repetition — **this is the part most likely to have been harder
  than the brief assumed**, and the report should say so plainly if it was.
- **Whether verb-only evidence was sufficient in practice**, in the operator's
  words. If it was not, that is the argument for making `reason`
  operator-supplied, and it belongs in the report as a finding rather than being
  fixed quietly.
- Every `[H]` answer in the operator's words rather than paraphrased.
- **Named rather than absorbed:** that the sunset dates written this round have
  no renewal mechanism until the next round opens, and the date of the earliest
  one.
- Every stop condition that tripped, and anything this brief asked for that
  turned out to be wrong. A report that contradicts its brief is the round
  working correctly (`CONVENTION_briefs.md` §5).
