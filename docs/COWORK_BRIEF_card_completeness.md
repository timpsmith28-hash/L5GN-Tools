# Cowork brief — a card declares its completeness; the refusal 0059 struck comes out of `desk.py` before a second surface copies it

**Where you are:** `C:\Users\timps\Documents\GitHub\L5GN-Tools`, host
`LucasGoonPC`.

**Read before Task 1, in this order:** `CLAUDE.md` at the repo root — it is the
map and it is where the environment hazards live; then **0059** and **0048** in
`docs/DECISIONS.md`, in that order, because 0059 amends 0048 and the amendment
is the round; then **0050** clause 5, which is the collision Task 1 exists to
resolve; then this brief in full; then `docs/UAT_card_completeness.md`, which is
the walk-sheet of record and is not a summary of what follows.

**Draft-status:** written 2026-09-04, in the design thread that opened Cards C
and D. It is written to be built in its own thread, **before**
`COWORK_BRIEF_staleness_feeds.md` opens. Every "already exists" claim below was
checked against the tree while drafting, with the file and line named so the
check can be re-run rather than trusted. **Re-verify them anyway as the round's
first act** — and in particular re-check that nothing from `staleness_feeds` has
been built, because if it has, this card is out of order and the collision it
resolves has already been resolved by accident.

**Origin:** design thread, 2026-09-04, sizing Cards C and D from
`docs/AGENDA_restart_2026-09-03.md`. **0059** was accepted 2026-09-02, five
days after `COWORK_BRIEF_staleness_feeds.md`'s own preconditions cleared and
fifteen days after that brief was written. It puts real work —
completeness derived and shown, incomplete cards raised, a fourth ruling kind —
inside the scope of that brief's Task 3, which restructures `_make_card` into
*"the single place a card is assembled."* A brief is frozen at the moment of
asking (`CONVENTION_briefs.md` §0), so the choice was where the 0059 work goes,
not whether the frozen brief could be corrected. **It goes here, in its own
card, landing first**, so that Card C restructures a `_make_card` that already
obeys 0059 rather than propagating a withdrawn refusal into a provider loop.

0059's own Consequences argued for exactly this ordering before this brief
existed: *"`desk.py` has hard-coded the anatomy once already, and Q2's own
wording warns that this is the moment to change it — before a second surface
copies it."*

**Precondition — hard, each checkable:**

- **0059 is accepted.** `awk '/^## 0059/,/^\*\*Context/' docs/DECISIONS.md | grep Status`
  → `accepted 2026-09-02`. A `proposed` 0059 is not authority
  (`CONVENTION_decisions.md` §3) and this round does not open.
- **Nothing from `COWORK_BRIEF_staleness_feeds.md` is built.**
  `grep -n "MANIFEST_SCHEMA_VERSION" chronicler/review/project_wizard.py` → `= 1`;
  `grep -n "VALID_RULINGS" chronicler/review/desk.py` → line 123, three kinds;
  `cards()` has no provider loop. If any of the three has moved, Card C has
  started and this brief is out of order — **stop and re-sequence**, do not
  build around it.
- **`python verify.py` is GREEN** before the first edit, so a red gate at the
  end is this round's and not inherited.

**Depends on — this repo's rulings:**

- **0059** — the entry this round builds. Clause 1 (0048 clause 2's field list
  stands, its refusal does not), clause 2 (a card declares its own completeness,
  derived and never typed; a surface reports it and does not grade the card),
  clause 3 (an incomplete card is raised, marked incomplete), clause 4
  (`insufficient` is a ruling and carries what is missing; ruled with no named
  item it is refused at write), clause 5 (completeness is not a threshold and
  never gates).
- **0048** — clause 1 (the unit of throughput is a decision), clause 2 (the six
  fields, whose *list* survives 0059 and whose *refusal* does not), clause 3
  (silence is an input and its consequence is stated on the card), clause 4
  (`default` and `expiry` are declared now and inert until a policy engine
  exists — and a check that cannot fail trains the eye past it, which is this
  round's own falsifier), clause 5 (a standing ruling carries a sunset —
  cited because 0059's Consequences names clause 4 remaining true as a
  dependency, not because this round touches promotion).
- **0050** — clause 5 (an item claiming staleness without stating when it became
  observable has no latency clock and no expiry, so it is not raised, and the
  reason appears on the health line rather than nowhere). **This is the
  collision.** See *Ratify before code*.
- **0031** — a non-gating surface reports findings, never verdicts. 0059
  clause 2's *"a surface reports this; it does not grade the card or withhold
  it"* is 0031 applied to the card's own anatomy.
- **0037** clause 4 — no estimate where no measurement exists. The reason every
  option's `cost` is `None` today, and the precedent this round's completeness
  derivation generalises.
- **0045** — report, never repair.
- **0058** — a mechanism that cannot answer abstains explicitly, and the
  abstention is counted. 0059 clause 4 cites it for the
  `insufficient`-with-no-named-item refusal.
- **0028** clause 3 — a commit is a human act; a local surface may stage, never
  commit. Unchanged by this round and restated because the round touches a
  write path.

**Ratify before code — one ruling, and the round does not build until it binds.**

**0050 clause 5 and 0059 clauses 1/3 cannot both hold on the same field, and
that field is the only one `desk.py` refuses on today.**

- 0050 clause 5: an item with no `observable_since` *"is not raised — and the
  reason appears on the health line rather than nowhere."*
- 0059 clause 1 strikes 0048 clause 2's *"a card missing any field is not
  raised"* outright; clause 3 says an incomplete card is raised, marked
  incomplete.
- 0059 lists 0050 under **Builds on**, glossing only its clause 4 (a source that
  cannot be reached reads as unknown). Clause 5 is not named as amended, and
  was very likely not in view.

Verified in the tree: `chronicler/review/desk.py:468`, `_make_card`, returns
`None` at line 474 when `condition_epoch is None`, with the docstring *"a card without
assembled evidence is not raised (Task 1; DECISIONS 0048 clause 2)"* — a
citation pointing at struck text. `condition_first_observable` is **the only
field any code path refuses on.** So this is not a corner case; it is the whole
refusal.

Two readings, and the operator's re-read picks one:

- **(a) 0050 clause 5 survives as a narrower carve-out.** No clock → still not
  raised, but the reason becomes *visible* (Task 5) instead of a silent `None`.
  Everything else → raised, marked incomplete. The argument: a card with no
  clock cannot age, cannot expire, and contributes nothing to
  `latency_summary()`; raising it puts a permanent unrulable item on a board
  whose whole instrument is the latency clock.
- **(b) 0059 supersedes it.** Raised, marked incomplete on the clock field,
  contributing no latency. The argument: 0059 clause 1's case is that refusing
  moves the attention cost from the operator to nobody, and a clock is not
  special.

**This brief's reading is (a)**, and it is stated so that the operator's act is
a re-read rather than an archaeology. **The reading is not authority until it is
ratified**, drafted by `decision-scribe` and re-read on a different day than
drafting (**0033**). Tasks 2, 3 and 5 all depend on it: under (a) `_make_card`
keeps one `return None` and Task 5 must render its reason; under (b) that
`return None` is deleted and Task 5 renders no clock case at all. **Nothing in
this round is built while that ruling is `proposed`**, and the report says which
reading bound.

**Deliverable:** every derived card carries a `completeness` block naming each of
0048 clause 2's six fields as `present`, `absent` or `not_applicable` with a
reason on anything not `present` — derived in `_make_card`, never typed, never
counted, never gating; cards that today are silently withheld are raised marked
incomplete or, where Task 1's ruling preserves a refusal, refused *visibly*
through a `refusals` list on `GET /api/desk/cards` that Card C's feed-health
line will later fill; and `insufficient` joins the ruling vocabulary, refused at
write when it names no missing item. **The round is finished when a card exists
on the board whose completeness block reads something other than complete, an
`insufficient` ruling with a named item is in `events.jsonl`, `latency_summary()`'s
five figures are unchanged against the pre-round event log, and `verify.py` is
green.**

---

## The thing this round exists to prevent

`_make_card` is under forty lines (`desk.py:468-503`) and it is where the card
anatomy lives. Card C's Task 3
makes it *"the single place a card is assembled"* for both the manifest provider
and every future declared feed. Whatever refusal it holds on the day of that
restructure becomes the refusal every feed inherits.

Today it holds a refusal whose authority was withdrawn on 2026-09-02, and cites
the withdrawn clause by number in its own docstring. Left in place through Card
C, the estate ends with one assembly point enforcing struck text against an
open set of sources, and the correction becomes a change to a feed contract
rather than a change to forty lines.

**That is the whole argument for this being its own card and going first.** It
is small, it is entirely inside one function and one ruling, and it is the last
moment at which it is small.

## What is already true, verified rather than remembered

Checked in the tree on 2026-09-04. Each line names where, so the round's first
act can re-run it:

| claim | where | state |
|---|---|---|
| The six fields are assembled in one place | `desk.py:468` `_make_card` | `question`, `trigger`, `evidence{freshness,last_run,manifest_declaration,linked_thread}`, `options`, `default: "hold"`, `expiry` |
| The only refusal-to-raise | `desk.py:473-474` | `if condition_epoch is None: return None`, silent, docstring citing 0048 cl.2 |
| The ruling vocabulary | `desk.py:123` | `VALID_RULINGS = frozenset({"rebuild", "snooze", "dismiss"})` |
| Per-verb refusals | `desk.py:360-372` | unknown verb, unknown fingerprint, `dismiss` with empty reason, `snooze` with no `until` |
| The request body | `desk.py` `RuleBody` | `fingerprint`, `ruling`, `reason`, `evidence_refs`, `until` — no field for a named missing item |
| The render path | `static/views/desk.js`, 220 lines | renders trigger pill, `aged` pill, evidence block, default line |
| The event log | `data/desk/events.jsonl` | 39 events: 14 `ruling`, 12 `sighting`, 11 `resolution`, 2 `finding` |

**And one measured fact that decides Task 6.** On today's two triggers every
derived card fills all six fields by construction. Two sub-fields are already
absent-and-correct — `evidence.linked_thread` reads
`{"available": false, "reason": "no_vault_on_this_machine"}` on this rig, and
every option's `cost` is `None` with a `cost_note` citing 0037 clause 4. Neither
is a gap; both are `not_applicable`. **So a completeness block built and walked
against today's population would say the same thing on every card, forever** —
which is precisely 0048 clause 4's failure, built deliberately. Task 6 is the
answer to that, and it is allowed to fail.

## Working rules

- **Completeness is derived, never typed.** No manifest field, no feed field, no
  hand-set flag, no override. If a completeness value can be authored anywhere,
  the round has built the thing 0059 clause 2 forbids.
- **Completeness never gates.** No count, no score, no minimum, no automatic
  escalation, no sort order that hides an incomplete card (0059 clause 5). A
  surface reports it (0031).
- **`absent` and `not_applicable` are different answers and the difference is
  the point.** Absent means a gap in the assembling machinery. Not-applicable
  means the field correctly has nothing — no measurement, no vault, no
  dependency — and the reason says which. Collapsing them produces a number that
  reads like a defect count and is not one.
- **The existing three verbs do not change.** Same names, same refusals, same
  fingerprints. The trial's rulings must stay comparable across this round, for
  the same reason `COWORK_BRIEF_staleness_feeds.md` holds that line.
- **`default` and `expiry` stay inert** (0048 clause 4). This round makes them
  *legible*, not live.
- **No restructure.** `cards()` is not touched beyond what Tasks 3 and 5
  require. Providers, feeds and schema v2 are Card C.
- UTF-8 explicit, UTC ISO-8601.

## Tasks

1. **Ratify the 0050 clause 5 / 0059 clauses 1–3 collision.** `decision-scribe`
   drafts; re-read on a different day than drafting (0033). The entry names
   which reading binds and what happens to a card with no
   `condition_first_observable`. **No code in this round lands before it binds.**
   If it goes to reading (b), Tasks 2, 3 and 5 change as described above — say
   so in the report rather than silently building the other one.

2. **The completeness derivation.** A `completeness` block on every card dict,
   built in `_make_card`: one entry per 0048 clause 2 field
   (`question`, `trigger`, `evidence`, `options`, `default`, `expiry`), each
   `present` / `absent` / `not_applicable`, each non-`present` carrying a
   one-line reason. **The precedent to follow already exists**:
   `_base_options()`'s `cost_note` states *why* a cost is absent, citing 0037
   clause 4. This is that shape, generalised to six fields. No score, no total,
   no percentage — a count is a threshold waiting to be compared against
   something.

3. **Incomplete cards are raised, marked.** `_make_card` stops returning `None`
   except where Task 1's ruling preserves it; `desk.js` renders the completeness
   block so an incomplete card is distinguishable from a complete one *on the
   page*, naming which field and why. The docstring's 0048 clause 2 citation is
   replaced with the 0059 citation that now governs it — a citation pointing at
   struck text is the defect this round is here to remove, and leaving it in the
   function it rewrites would be comic.

4. **`insufficient` as a fourth ruling.** `VALID_RULINGS` gains it. `rule()`
   refuses an `insufficient` carrying no named missing item (0059 clause 4, on
   0058's abstain-explicitly principle), by the same accumulate-and-refuse shape
   the `dismiss`/`snooze` refusals already use. `RuleBody` gains the field that
   carries it. **The named item is written onto the event**, because 0059's own
   falsifier is *"read the `insufficient` rulings' named items after a month"*
   and a ruling that does not persist the item answers nothing.
   `rebuild` / `snooze` / `dismiss` keep their exact current verbs and refusals.

5. **The refusals socket.** `GET /api/desk/cards` returns `refusals` alongside
   `cards`: what was not raised, and why, each entry naming the repo and stage
   it would have described. Rendered where an empty board would otherwise read
   as all-clear. **This is deliberately the socket Card C's Task 6 feed-health
   line fills** — named here so C extends one mechanism rather than building a
   second beside it. Under Task 1's reading (b) this list may be empty on this
   rig, and it is still built, because C needs it.

6. **Find out whether the display can ever say anything, and record the answer
   either way.** Construct a fixture that yields a card with a genuine gap in a
   field **other than the clock**, using only Triggers A and B and a manifest in
   `config/project_wizard.allow.json`. If one can be built, name the
   arrangement in the report and walk it. **If no arrangement of today's two
   triggers can produce a non-clock gap, that is the finding** — it means this
   round's central display is provably inert until Card C lands, it is recorded
   as such in the report, and the `[H]` check below is what decides whether the
   block ships anyway. Do not manufacture the case by special-casing the
   fixture inside `desk.py`.

## Explicitly out of scope

Named because each is a step away and will feel like tidying:

- **Everything in `COWORK_BRIEF_staleness_feeds.md`**: `staleness_feed` as a
  manifest section, `MANIFEST_SCHEMA_VERSION = 2`, the provider loop in
  `cards()`, source-declared `options`, per-option `requires`, the workcycle
  feed, the full feed-health line, the `feed_error` event, the second
  allowlisted fixture repo. This round touches `_make_card`, `rule()`,
  `RuleBody`, one API response field and `desk.js`. It does not restructure
  `cards()`.
- **Opening the ruling vocabulary.** `VALID_RULINGS` gains a fourth member and
  stays a closed module-level set. Making the vocabulary per-card is Card C's
  Task 4 and doing it here builds C's hardest task out of order.
- **Promotion, repetition detection, standing rulings** —
  `COWORK_BRIEF_promotion_step.md`.
- **Making `default` or `expiry` act.** They stay inert (0048 clause 4).
- **Any completeness score, threshold, sort, filter or escalation** (0059
  clause 5).
- **Making `reason` operator-supplied** on the existing three verbs. Related —
  the promotion round names it as a measured limit — but not this round's
  change.
- **A `desk/` package.** This is edits inside one 725-line module.

## The one deliberate widening, named

**`insufficient` lands in `VALID_RULINGS`, a module-level list that 0050
clause 8 says the vocabulary should not live in.** 0050 clause 8 is accepted
authority and says the ruling vocabulary belongs to the card, validated against
the options that card actually offered. This round widens the closed set instead
of opening it.

Why: opening it is Card C's Task 4, it is coupled to the manifest schema and the
feed contract, and doing it here means building the harder half of C without C's
brief, its preconditions or its walk-sheet. **What still bounds it:** the set
stays closed and module-level, the refusals stay per-verb in `rule()`, nothing
in this round reads a per-card option list, and Card C replaces the whole
mechanism rather than extending it. If this round finds itself generalising the
vocabulary, it has become Card C — see the stop conditions.

## Stop conditions

- Any code lands before Task 1's ruling binds → stop.
- A completeness value can be set from a manifest, a request, or by hand → stop
  (0059 clause 2).
- A completeness count, score, percentage or threshold appears, or completeness
  gates, sorts, filters, hides, blocks or escalates anything → stop (0059
  clause 5).
- `absent` and `not_applicable` collapse into one state → stop; the difference
  is the deliverable.
- `cards()` grows a provider loop, a feed reader, or a schema v2 branch → stop;
  that is Card C.
- The per-card option list, `requires`, or per-option validation appears → stop;
  that is Card C's Task 4 and this round's named widening says so.
- `rebuild`, `snooze` or `dismiss` change verb, refusal, payload or fingerprint
  → stop; the trial's rulings must stay comparable.
- An `insufficient` ruling is written with no named item, or with the item
  discarded rather than persisted → stop (0059 clause 4).
- `refusals` acquires a second, competing home for feed health → stop; it is one
  socket and Card C fills it.
- `latency_summary()`'s figures move against the pre-round event log → stop;
  Phase 1's corpus is the trial's whole output.
- Task 6 finds no constructible non-clock gap, and the round ships the display
  without recording that → stop; a check that cannot fail, shipped silently, is
  0048 clause 4 exactly.

## UAT — acceptance checks (Tim walks these)

**Falsifier for this round:** *after this round, does the completeness block
ever say anything other than complete?* If, one month on, no card has been
raised marked incomplete and no `insufficient` ruling exists in
`events.jsonl`, then 0048 clause 2's refusal was withholding nothing and 0059
clause 3 has added furniture. **The consequence, written before the answer:**
0059 clause 4 is struck by its own falsifier, and the completeness block is
**deleted** rather than left as a field the eye has learned to skip.

- `[G]` Every currently-derived card carries a `completeness` block naming all
  six of 0048 clause 2's fields, each `present` / `absent` / `not_applicable`,
  and every non-`present` entry carries a non-empty reason string.
- `[G]` On this rig `evidence.linked_thread` reports `not_applicable` with
  `no_vault_on_this_machine` as its reason, and every option's `cost` reports
  `not_applicable` citing 0037 clause 4. **Neither is reported as a gap** — the
  round's own test that `absent` and `not_applicable` did not collapse.
- `[G]` The fixture's no-clock stage behaves exactly as Task 1's ruling says.
  Reading (a): no card, and the reason appears in `refusals` on
  `GET /api/desk/cards` **and on the rendered board**. Reading (b): one card,
  marked incomplete on the clock field, contributing no latency to
  `latency_summary()`. The walked check names which reading bound.
- `[G]` `latency_summary()`'s five figures — `cards_raised`, `cards_ruled`,
  `cards_resolved_without_ruling`, `median_latency_hours`, `oldest_open_days` —
  are identical before and after the round against the unchanged pre-round
  `events.jsonl`.
- `[G]` `rule(fp, "insufficient", …)` with a named missing item appends one
  event carrying that item, readable back from `events.jsonl`. The same call
  with no named item raises `DeskRefused` **and writes nothing** — verified by
  the file's byte length being unchanged, not by the absence of a visible
  error.
- `[G]` `dismiss` with an empty reason, and `snooze` with no `until`, refuse
  exactly as they do today; `rebuild` still requires neither; an unknown verb is
  still refused, now against a four-member set.
- `[G]` A card marked incomplete is distinguishable from a complete one **on the
  rendered page**, and names which field is missing and why — read from the
  board, not from the JSON.
- `[G]` Task 6's answer is recorded: either a non-clock gap was constructible
  from Triggers A and B, with the fixture arrangement named and walked, or it
  was not and the report says the display is inert until Card C.
- `[G]` `python verify.py` → GREEN.
- `[H]` **Was the completeness block information, or furniture?** You have now
  looked at a board where most cards read complete on six fields. Did the block
  tell you anything, or did your eye go past it? This is 0048 clause 4's own
  test, asked of the thing this round built.
- `[H]` **Rule one real card `insufficient`, and name the thing you actually
  wanted.** Was `insufficient` the ruling you reached for, or did you reach for
  `snooze` and then remember it existed? 0059's own falsifier is a count of
  these after a month; this is its first data point, and a reluctant one counts.
- `[H]` **Would you defend striking 0048 clause 2's refusal, on re-read?** 0059
  clause 1 states in its own text that its reading of your Q2 answer is an
  inference you have not confirmed. This round is what makes that inference
  expensive to reverse. Say now if it was wrong.

**`[H]` count: 3.** Each asks about the operator's experience rather than the
code's behaviour, which is the shape `CONVENTION_briefs.md` §4 says earns the
cost. None is standing in for a property that could have been mechanised: the
first two are judgements about attention that no assertion can make, and the
third is a ratification question that only the author of the original answer can
settle.

## Reporting

`docs/COWORK_REPORT_card_completeness.md`, walk-sheet
`docs/UAT_card_completeness.md`, stamped results
`docs/UAT_card_completeness_results.md`.

Record, specifically:

- **Task 1's ruling as ratified**, which reading bound, and what the re-read
  changed from this brief's stated preference.
- **The completeness block field by field**, and for each of the six, whether
  any real card in the round ever reported it as anything but `present` or
  `not_applicable`.
- **Task 6's answer**, and if no non-clock gap was constructible, that this
  round's central display is inert until Card C lands — **stated as a finding,
  not absorbed into a passing check.**
- `latency_summary()`'s five figures before and after, side by side.
- Every `[H]` answer in the operator's words rather than paraphrased.
- **Whether the `refusals` socket is a shape Card C's Task 6 can fill, or a
  thing C will have to replace** — the honest answer matters more than the
  convenient one, because C's brief is frozen and cannot be told.
- Anything this brief asked for that turned out to be wrong. A report that
  contradicts its brief is the round working correctly
  (`CONVENTION_briefs.md` §5).
