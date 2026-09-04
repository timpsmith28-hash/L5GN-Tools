# UAT walk-sheet — `promotion_step`

**Brief:** `docs/COWORK_BRIEF_promotion_step.md`. This sheet is the brief's
acceptance section, extracted so it can be walked and stamped
(`CONVENTION_briefs.md` §2). They were written together, before the build.

**Checks: 18 — 15 `[G]`, 3 `[H]`.** The `[H]` count is deliberate and its
justification is in the brief's acceptance section: one asks whether assembled
evidence was actually enough, one is a cold-read judgement that only time and a
person can supply, and one asks whether a mechanical answer dissolved a felt
problem. None is standing in for a property that could have been mechanised.

**Walking is a human act** (`CONVENTION_briefs.md` §6). This sheet is not
stamped by the thread that did the build, and a passing test is not a walk.

**Before walking, confirm the round's own preconditions held:** both *Ratify
before code* rulings are `accepted`, not `proposed`; `card_completeness` and
`staleness_feeds` are both closed with stamped results; dispatcher Task 3 is
struck. If any is false, the walk stops here.

---

## The round's falsifier

*Does anything ever get promoted?*

At the N ratified in Task 1, and **one month after this round closes**: if
nothing has been promoted and nothing has been *refused* promotion either, then
INTENT §8's *"a decision made three times is a policy not yet written down"* has
no instance in this estate's actual traffic.

**Consequence, written before the answer is known:** the promotion step is
furniture and is **deleted**, not left dormant — and 0048 clause 5's sunset
clause loses its only mechanism and is re-argued rather than kept as intent.

This is not answered by this walk. Record the date one month out in the results
log, and record Task 1's corpus counts as the baseline it will be judged
against.

Baseline (fill from Task 1, not from the brief's stale 2026-09-04 figures):

- total ruling events: ______
- distinct fingerprints: ______
- fingerprints meeting N: ______
- N as ratified: ______
- date to re-check: ______

---

## `[G]` — a machine or an unambiguous procedure decides

- [ ] `[G]` Task 1's corpus report, re-run on an unchanged
      `data/desk/events.jsonl`, produces identical counts twice.

- [ ] `[G]` The report names every `finding`-annotated fingerprint with the
      finding's text **verbatim**, and the count for that fingerprint is **not
      reduced**.

- [ ] `[G]` `promotion_candidates()` and `latency_summary()` agree on occurrence
      counts per fingerprint — a diff of the two occurrence sets is empty — and
      the round's diff contains **no second occurrence replay** beside
      `_reconstruct_occurrences`.

- [ ] `[G]` `latency_summary()`'s five figures — `cards_raised`, `cards_ruled`,
      `cards_resolved_without_ruling`, `median_latency_hours`,
      `oldest_open_days` — are unchanged against the pre-round event log. Record
      both sets.

- [ ] `[G]` A fingerprint at N−1 raises no promotion card; the same fingerprint
      at N raises exactly one; ruling it `refuse` and then reaching N+1 does not
      raise a second at the same count.

- [ ] `[G]` The promotion card names, **in words on the rendered board**, what
      the fingerprint is — read from the opening sighting's `card_summary`, not
      from the hash.

- [ ] `[G]` A `promote` ruling writes exactly one appended row, and the file's
      prior bytes are unchanged — verified by hashing the prefix before and
      after, not by a visual diff.

- [ ] `[G]` A second `promote` on the same fingerprint returns an
      already-promoted refusal and **writes nothing**.

- [ ] `[G]` The written row carries: what was promoted; a declared subject; a
      declared reader **or** an explicit `none`; a sunset date; parent
      occurrences resolvable back to `events.jsonl` by fingerprint and timestamp
      **by reading the row alone**; and the contamination notes that were on the
      card when it was ruled.

- [ ] `[G]` Revocation appends. The revoked row is still present and reads as
      revoked; nothing earlier in the file was rewritten (hash the prefix before
      and after).

- [ ] `[G]` Nothing in the round commits. After a promotion, `git status` **on
      Windows** shows the file modified or staged, never committed.

- [ ] `[G]` Task 6's answer is visible in the tree — **one of exactly two**:
      - a new reader runs in the gate and reports standing rulings with no
        declared subject or no declared reader; **or**
      - the file's own header states the class `unenforceable` in 0060 clause
        2's terms.

      Which: ______________

- [ ] `[G]` No standing ruling authorises, plans or executes anything. A search
      of the round's diff for an execution path reading the standing-rulings
      file finds none.

- [ ] `[G]` Task 7's answer is recorded: the count of `insufficient` rulings and
      their named items at round-open, and **either** a detector built over a
      set large enough to detect on, **or** a statement that 0059's third
      falsifier is not yet answerable.

      Count: ______   Built / not answerable: ______________

- [ ] `[G]` `python verify.py` → GREEN.

## `[H]` — a human judgement is genuinely required

- [ ] `[H]` **Promote one real thing.** Rule a promotion card on a repetition
      you actually recognise. Was the evidence enough to promote on, or did you
      go and read `data/desk/events.jsonl` yourself? Going hunting is the
      finding — and it is a finding about the join in Task 3, not about you.

      Answer, in your words:

- [ ] `[H]` **Read the standing ruling back a week later, cold.** Does it say
      what it binds and who reads it — or does it read as a note to yourself?
      This is 0060 clause 1's test applied to the first rule this estate
      *generated* rather than wrote, and it is the check most likely to fail.

      Date read back: ______   Answer, in your words:

- [ ] `[H]` **The naming question, answered by the mechanism rather than by
      re-labelling.** `AGENDA_running_order_2026-08-28.md` §2a claimed building
      this dissolves the *"Decision Desk names the rarest of the three"* worry.
      Does it? Or does the Desk still feel like the wrong name — in which case
      §2a's mechanical answer failed and renaming is back on the table as its
      own round.

      Answer, in your words:

---

## Stamping

Results go to `docs/UAT_promotion_step_results.md`, whose first line is the uat
stamp:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> -->
```

`gate=` is optional (`CONVENTION_briefs.md` §6). Omit it rather than assert a
count you did not observe; if you include it, it is checked against the
registered counts by `auditor_uat_stamp`.

Record every `[H]` answer in the operator's own words, not paraphrased
(`CONVENTION_briefs.md` §5), name every stop condition that tripped, and record
the earliest sunset date written during the round — it has no renewal mechanism
until the next round opens, and the report is required to say so.
