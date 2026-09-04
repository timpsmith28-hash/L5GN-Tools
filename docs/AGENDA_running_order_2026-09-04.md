# Agenda — the running order, 2026-09-04

The planning act that follows `AGENDA_restart_2026-09-03.md` and the Cards C/D
brief-writing thread of 2026-09-04. Frozen at its date. It names rounds and
their sequence; it writes no brief and no code, and it **ratifies nothing**.

**Host:** `LucasGoonPC`. **HEAD at writing:** `ba883af`, plus this thread's two
doc commits still uncommitted (`data/git_warden/card_completeness-1.msg`,
`promotion_step-2.msg`). Every figure below was read out of the tree on
2026-09-04 and is cited with its file.

> **This supersedes §1 of `AGENDA_running_order_2026-08-31.md`**, whose five
> sessions are spent. That file stands as written and as evidence; §0 below says
> what of it landed and what did not. It does not amend
> `AGENDA_running_order_2026-08-28.md`, which declared its third amendment its
> last.

**Written for a week split across two work Claudes.** The constraint being
planned against is not session budget, it is **context-switch cost** — so the
order is cheapest-first, every session ends on a commit, and §4 tells a cold
reader where to start.

> **Amended 2026-09-04, same day, before S1 opened. §0's fourth row and §1's S1
> are wrong and are corrected here rather than rewritten in place.**
>
> **The claim:** that 0054 clause 6 is *"still live"* — `authors` present in both
> `config/machines.json` and `config/local.json` — and therefore that *"a built
> card is now standing on a live contradiction."* The same claim is in commit
> `d694e59`'s body, which stays as written (**0029**: kept intact, never
> doctored).
>
> **What is true.** 0054 clause 6 was **closed on 2026-08-31**, by ruling, by
> config and by code. `config/local.json`'s `LucasGoonPC` section carries no
> `authors` key — it carries `_authors_moved`, a comment recording the move and
> stating that re-adding it there *"would be inert, not an override."*
> `config/machines.json` carries a real `LucasGoonPC` section holding `authors`
> and nothing else, with an `_authorship_exception_comment` narrating the whole
> collision and its resolution. `l5gntools/config.py`'s `_tracked_entry` is
> `machine()`'s layer stack **with `local.json` removed**, so an untracked
> declaration is not outranked — it is unreadable. Card B's prerequisite cleared
> before Card B shipped.
>
> **How the error was made, because the mechanism matters more than the fact.**
> `grep -l "authors" config/machines.json config/local.json` returned both files
> and the two hits were reported as two declarations. One of them was a
> substring inside a comment key. **That is a claim over a substituted subject —
> 0060 clause 3's own shape — made by the thread that had spent the session on
> the conformance round, in the commit body reporting it.** The evidence
> contradicting it was inside the file that was grepped.
>
> **Two things the correction turned up that are worth more than it:**
>
> - **`AGENDA_running_order_2026-08-31.md`'s own S1 instruction pointed at the
>   wrong file.** It said to check `tests/tester_authors.py` first. That tester
>   is about **git commit author aliasing** — `config.author_aliases`,
>   `config/authors.json`, folding two git identities in the census — and has
>   nothing to do with 0054 clause 6's per-artefact `authors`. **Two unrelated
>   things in this repo are called `authors`**, and an order written four days
>   earlier had already tripped on it.
> - **There is a real residual, and it is not the one claimed.** Clause 6 is
>   satisfied and **declares no reader**: nothing in the gate reads the actual
>   `config/machines.json` (`tester_config` and `tester_pin` both swap
>   `config._MACHINES` for a temp fixture, and `machines.json`'s own comment says
>   so). And the code makes `authors` in `local.json` **inert rather than
>   refused**, so adding it there produces silence — which is unrecognised
>   configuration failing quietly, against **0054 clause 8**'s fail-loudly rule.
>
> **S1 is replaced.** See §1a below. §0's row and §1's S1 stand as written and as
> evidence of the error.

---

## 0. What the 08-31 order actually landed

Read from the tree, not from that file's own claims.

**S3, S4 and S5 landed in full.** **0060** accepted 2026-09-01;
`docs/CONVENTION_conformance.md` written; `auditors/auditor_rule_subjects.py`
built and registered — **the gate is now 13 auditors and 82 testers**, up from
12; `docs/_conformance_map.md` generated; the round walked 2026-09-02 and
stamped at `8a61aec`.

**S2 — Card B — landed, and better than briefed.** All three relink defects are
closed in `chronicler/pipeline/run_pipeline.py`: `SKIPPED -- NOT CONFIGURED`
distinguishes an unconfigured stage from an absent source (line 301); `RAN,
OUTCOME UNREPORTED` replaces the vacuous *"no new rows"* and cites 0048 clause 4
by number (line 350); `encoding="utf-8"` is on the capture (line 273).

**S1 landed one item of four, and one of the misses matters.**

| 08-31 S1 item | state today | evidence |
|---|---|---|
| 0056 gap 1 — pattern-driven pin check | **closed** | `auditor_conversation_map_pin.py` now drives off `PATTERN`, not a module-level path |
| **0054 clause 6 — the `authors` contradiction** | **still live** | `authors` present in **both** `config/machines.json` (tracked) and `config/local.json` (untracked) |
| the two registry resolvers | **both still exist** | `chronicler/pipeline/db.py:52` and `chronicler/review/core.py:247`; whether they still disagree on step count was **not confirmed by this reading** |
| adoption-header pass | **not confirmed** | the conformance map now reports the same class differently; nobody has re-counted |

## 0a. The two numbers that did not move

The 08-31 order named the pattern in its own §1: *"the pattern that produced 10
unbuilt briefs and 8 unwalked reports is that planning is cheap and building is
not, so rounds ended in a brief."*

Counted from the tree today, across 27 brief slugs in `docs/`:

| | 08-31 | today |
|---|---|---|
| fully closed — brief, report, sheet, stamped results | — | **7** |
| **built and reported, never walked** | 8 | **8** |
| **briefed, never built** | 10 | **12** |

**Neither improved, and one got worse by this thread's own hand.** The two
briefs written on 2026-09-04 are the +2. That is not an argument against writing
them — Card D's brief was the round's contractual first act — but it is the
reason this order front-loads closing over opening.

**`round-closer` exists for exactly the eight**, and its own description says so:
*"find which cards are built but not walked."* It has never been pointed at
them, across three consecutive running orders. **That is now a pattern rather
than an oversight**, and §3 asks the operator to rule on it rather than letting
a fourth order carry it silently.

---

## 1. The order

**Sequenced so that stopping after any session leaves something committed.**
S0 is minutes; S1 is small; S2 and S3 are the week.

### S0 — the three cheapest open items in the estate

Do these first. Together they are under an hour and they remove three pieces of
ambient noise that make every later session harder to start cold.

1. **Sweep `data/git_warden/`.** Four drafts, all dated 2026-09-02, none
   confirmed spent: `conformance_report-1`, `conformance_walk-1`,
   `ratify_0058_0059-1`, `restart_2026-09-02-1`. **This cannot be done from a
   sandbox** — it is a `git log` question against a mounted Windows repo, which
   is the standing hazard. One PowerShell pass on the rig settles it. Note
   `conformance_walk-1.msg`'s first line is *"docs(uat): walk the conformance
   reader -- two checks fail, and both say why"* while the commit subject
   recorded in `AGENDA_restart_2026-09-03.md` is the shorter *"docs(uat): walk
   the conformance reader"* — **an exact match is the test**, and a near-miss
   means the draft was edited after the commit, which is worth seeing.
2. **Close the INTERIM conformance walk.** `docs/UAT_conformance_reader_results.md`
   declares itself INTERIM under `CONVENTION_docs.md` §4 and names what it waits
   for: A2's second half — *one person reading `docs/CONVENTION_conformance.md`
   end to end against its own §9 table, to confirm the table omits no
   imperative.* **The log itself calls this "a ten-minute job."** It has been
   open since 2026-09-02.
3. **Commit the two briefs from the 09-04 thread.** Drafts are written; the
   commands are in that thread. Two commits, doc-only, gate pre-checked green on
   the three auditors that could have caught them.

**Ends on:** `data/git_warden/` holding only live work, one results log no longer
INTERIM, two commits, a green gate.
**Does not end on:** anything new opened.

### S1 — 0054 clause 6, the contradiction that has outlived two orders

It was 08-31 S1 item 1, it is Card B's named prerequisite, and Card B shipped
anyway — so the prerequisite is now a live contradiction with a built card
standing on it.

The accepted clause says `authors` *"is estate policy and lives in the tracked
file only"*. `authors` is in `config/machines.json` (tracked) **and**
`config/local.json` (untracked).

**Check `tests/tester_authors.py` first.** The 08-31 order's own instruction, and
it still holds: a reader may already exist and be reading the wrong file, which
makes this a conformance instance rather than a config fix — and a fresh worked
instance is worth more to `CONVENTION_conformance.md` than a tidy config.

**Ends on:** the contradiction resolved one way, a commit, a green gate.

### S1a — what replaces S1 *(added by the 2026-09-04 amendment)*

Two items, in this order. Both are small, both end on a commit, and the second
is the real residual the correction found.

1. **Fix `CONVENTION_conformance.md` §9's table.** The follow-up recorded by S0's
   A2 re-walk, on the operator's call: rename the third column from
   `0060 clause` to `clause` and add the two rows from that walk's defect 6 —
   §0's superseding-entry rule (0052 cl.3, inverted) and §7's
   *"a reader that cannot go red is worse than no reader"* (0048 cl.4). **Widen
   the table rather than narrow the preamble**, so the table matches the subject
   §9 already claims. Minutes, and it finishes S0 properly.

2. **Give 0054 clause 6 a reader, and make clause 8 true of it.** Two halves,
   and the second is the one with teeth:
   - **Nothing in the gate reads the real `config/machines.json`.** Clause 6 is
     enforced by `config._tracked_entry`'s structure and by nothing that can go
     red. Under **0060** clause 4 it declares no reader.
   - **`authors` in `local.json` is inert, not refused.** Someone adding it there
     gets silence — unrecognised configuration failing quietly, which **0054
     clause 8** forbids. The remedy is a loud refusal at load, not a comment.

   **Blast radius, named before it is hit:** anything registered in `verify.py`
   moves the gate census, which `auditor_doc_claims` reads and
   `auditor_architecture_current` guards. `docs/_architecture_shape.md`
   regenerates **in the same commit** (`python run.py render-architecture`,
   0030, `CONVENTION_commits.md` §6), and any live doc asserting the old count
   is corrected in that commit or carries `gate-frozen`. **The one live claim is
   `docs/COWORK_REPORT_conformance_reader.md`'s gate-count line** — the
   thirteen-and-eighty-two figure, in the compound form the auditor matches. It
   is frozen testimony about 2026-09-02, so it takes the marker rather than an
   edit. This file's own §0 count survives untouched, because §0 joins the two
   numbers with *and* and the auditor's pattern wants a `+`.

   **And a finding, from writing this paragraph:** the first draft of it quoted
   the report's line verbatim and **turned the gate red on the quotation**.
   `auditor_doc_claims` cannot tell an assertion from a citation of one — its
   docstring says it exempts *past-tense narrative mentions*, and a present-tense
   quotation is neither past tense nor a claim. Not a defect worth code: the
   mechanical narrowness is the reason the auditor is trustworthy, and
   `gate-frozen` exists for the case where a doc really is testimony. **But
   nothing anywhere records it**, so it is recorded here: **to write about a
   gate-count claim, describe it rather than quote it.**

   **Scope guard:** this is one narrow reader in `auditor_doc_claims`' pattern —
   one claim class, one authoritative source. It is not a config conformance
   engine, and if it starts reading a second rule it has become one → stop.

**Ends on:** two commits, a green gate, and a second worked instance for
`CONVENTION_conformance.md`, which currently has one.

### S2 — `card_completeness`, in its own thread

Briefed 2026-09-04. **The operator has said this runs in a separate thread before
Card C**, which is what makes it a session rather than a preamble.

Two things about its shape, both in the brief and repeated here because they
change how the session opens:

- **Task 1 is a ratify-before-code ruling and nothing builds until it binds.**
  0050 clause 5 and 0059 clauses 1/3 collide on `condition_first_observable`,
  the only field any code path refuses on. `decision-scribe` drafts; **the
  re-read is on a later day than the drafting** (0033), so this session
  genuinely spans two sittings and the second one is short.
- **Its own falsifier may fire during the walk.** On today's two triggers every
  card fills all six fields, so the completeness display may have nothing to say
  until Card C lands. Task 6 makes that a recorded outcome rather than a
  discovery.

**Ends on:** a ratified ruling, a built anatomy change, a walked sheet, a stamped
results log. **This is the first round in three orders scheduled to end walked
rather than reported.**

### S3 — `staleness_feeds` (Card C), the week's expensive item

Seven tasks, and its own brief instructs that **the rewrite is sized before it
is opened**. Both hard preconditions are clear and have been since 2026-08-28
(the `desk_stale_card` trial closed) and 2026-08-20 (0050 accepted).

**This card has slipped from two consecutive orders.** 08-28 §4 scheduled it;
08-31 §0b deferred it explicitly and named the cost. If it slips a third time,
that is information about the plan and not about the week — see §3.

**Open it only with S2 closed**, since Card C's Task 3 restructures the
`_make_card` that S2 changes.

### S4 — `promotion_step` (Card D), only if C closed

Briefed 2026-09-04, with two ratify-before-code items of its own and a hard
precondition of C closing. **If S3 runs long, this does not start** — its brief
is written and that was the round's first act; it loses nothing by waiting.

---

## 2. Not in this order, and why

- **The eight unwalked reports.** `estate_restructure`, `file_census`,
  `gap_closure`, `intent_evidence`, `knowledge_curator`,
  `local_deck_docs_and_time`, `project_wizard`, `quartermaster_frame`. All have a
  report and a walk-sheet and no stamped results. **Not scheduled here either**,
  and that is the third order in a row — §3 asks for a ruling instead.
- **`hermetic_gate`.** Briefed 2026-08-24, walk-sheet written, unblocked by 0053
  since 2026-08-28. **Its slot has been "an open call nobody has made" in three
  consecutive running orders.** It is the only item here that is briefed, sheeted,
  unblocked and unscheduled at once.
- **The 71 undeclared rule-bearing documents.** `docs/_conformance_map.md`
  reports **1 declared-and-checked of 72**; the other 71 sit inside 0060 clause
  8's carve-out. The carve-out is doing all the work and **there is no sweep and
  no expiry on it.** Clause 8 says entries acquire declared subjects "when
  something next touches them" — nothing is scheduled to touch them.
- **Card B has no card files.** No `COWORK_BRIEF_relink*`, no report, no
  walk-sheet, for work that shipped. `CONVENTION_briefs.md` §1 makes a card's
  state a function of which of the four files exist, so Card B is invisible to
  the doc lifecycle and to `docs-archivist`. Retroactive files would violate §0's
  frozen-at-the-moment-of-asking rule; naming it as deliberately uncarded is the
  honest alternative. **Not decided here.**
- **Card E (Governor's route)** — still cannot precede C and D. Untouched.
- **Card F (copy currency)** — unblocked by 0057, unscheduled.
- **0051 clause 2's containment auditor**, **0055's registry migration**, **the
  tenant migration investigation** (hard precondition: the post-migration
  snapshot covers a full working week — check the date range before opening),
  and **`INTENT.md` §2 / `ARCHITECTURE.md` §7's stale ~8% against a measured
  10.42%** — all unchanged from 08-31 §2 and all still unscheduled.

---

## 3. Four calls this order does not make, and cannot

Each has now survived more than one order. Leaving them unmade is itself a
choice, so they are named here rather than carried silently.

1. **Are the eight unwalked reports a debt or a decision?** If a round that is
   built and reported is finished in practice, then `CONVENTION_briefs.md` §6's
   *"walking is a human act"* is describing a step the estate does not take, and
   the convention should say so. If they are a debt, one `round-closer` session
   clears the cheapest of them.
2. **Where does `hermetic_gate` go?** Three orders have deferred to the operator
   on this. S4 added to the gate; gate hygiene is now more relevant, not less.
3. **Does 0060 clause 8's carve-out expire?** 71 of 72 documents rely on it. A
   carve-out with no sweep behind it is indistinguishable from a rule nobody
   intends to apply.
4. **Is Card B uncarded deliberately?** See §2.

---

## 4. Coming back cold — where to start reading

For a thread, or a person, opening this week without the 09-04 context.

1. **`CLAUDE.md`** — the map, and where the environment hazards live. The
   sandbox-git hazard binds every session below.
2. **This file, §1** — the order.
3. **Then only what the session you are on needs:**
   - S0 → `docs/UAT_conformance_reader_results.md` (its INTERIM block names the
     job exactly).
   - S1 → `docs/DECISIONS.md` 0054, then `tests/tester_authors.py`.
   - S2 → `docs/COWORK_BRIEF_card_completeness.md`, then 0059 and 0050 clause 5.
   - S3 → `docs/COWORK_BRIEF_staleness_feeds.md` in full, including its
     draft-status header, which demands re-verification against the tree as the
     round's first act.
   - S4 → `docs/COWORK_BRIEF_promotion_step.md`, then 0060.

**Do not read the previous running orders to get oriented.** They are frozen at
their dates and two of them defer items this file schedules. §0 above is what
they contain that still matters.

---

## 5. What would show this order wrong

- **A month from now the Desk still has one real card type.** Unchanged from
  08-28 §7 and 08-31 §4, **and this is its third consecutive appearance
  unanswered.** S2, S3 and S4 are the first order that schedules the evidence
  rather than postponing it. If the Desk is still single-card-type at the end of
  this order, the three cards were never the constraint and something else is.
- **S0 does not happen.** If the three cheapest items in the estate — under an
  hour together, all named with their exact remedy — are still open next week,
  then the constraint is not budget and not sizing, and every session estimate in
  every order here is measuring the wrong thing.
- **S3 slips a third time.** Then `staleness_feeds` is not a card that keeps
  losing to more urgent work; it is a card nobody wants to open, and the honest
  move is to say why in a report rather than reschedule it a fourth time.
- **The briefed-never-built count rises again.** It went 10 → 12 this week.
  A running order whose own output is more briefs is the failure the 08-31 order
  named and did not escape.
- **§3's four calls survive this order too.** Then they are not calls awaiting a
  decision; they are things the estate has decided not to do, and they belong in
  `CLAUDE.md`'s Debts rather than in a fifth agenda.
