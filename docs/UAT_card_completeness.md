# UAT walk-sheet — `card_completeness`

**Brief:** `docs/COWORK_BRIEF_card_completeness.md`. This sheet is the brief's
acceptance section, extracted so it can be walked and stamped
(`CONVENTION_briefs.md` §2). They were written together, before the build.

**Checks: 12 — 9 `[G]`, 3 `[H]`.** The `[H]` count is deliberate and its
justification is in the brief's acceptance section: two are judgements about
attention that no assertion can make, and the third is a ratification question
only the author of the original Q2 answer can settle. None is standing in for a
property that could have been mechanised.

**Walking is a human act** (`CONVENTION_briefs.md` §6). This sheet is not
stamped by the thread that did the build, and a passing test is not a walk.

**Before walking, confirm the round's own precondition held:** Task 1's ruling
is `accepted`, not `proposed`. If it is still `proposed`, nothing in this round
should have been built and the walk stops here.

---

## The round's falsifier

*After this round, does the completeness block ever say anything other than
complete?*

If, one month on, no card has been raised marked incomplete and no
`insufficient` ruling exists in `data/desk/events.jsonl`, then 0048 clause 2's
refusal was withholding nothing and 0059 clause 3 has added furniture.
**Consequence, written before the answer is known:** 0059 clause 4 is struck by
its own falsifier, and the completeness block is **deleted** rather than left as
a field the eye has learned to skip.

This is not answered by this walk. It is answered a month after it, and the date
to check is recorded in the results log.

---

## `[G]` — a machine or an unambiguous procedure decides

- [ ] `[G]` Every currently-derived card carries a `completeness` block naming
      all six of 0048 clause 2's fields — `question`, `trigger`, `evidence`,
      `options`, `default`, `expiry` — each marked `present`, `absent` or
      `not_applicable`, and every non-`present` entry carrying a non-empty
      reason string.

- [ ] `[G]` On this rig `evidence.linked_thread` reports `not_applicable` with
      `no_vault_on_this_machine` as its reason, and every option's `cost`
      reports `not_applicable` citing 0037 clause 4. **Neither is reported as a
      gap.** This is the round's own test that `absent` and `not_applicable` did
      not collapse into one state.

- [ ] `[G]` The fixture's no-clock stage behaves exactly as Task 1's ruling
      says. Record which reading bound before answering:
      - **reading (a)** — no card is raised, and the reason appears both in
        `refusals` on `GET /api/desk/cards` **and** on the rendered board;
      - **reading (b)** — one card is raised, marked incomplete on the clock
        field, contributing no latency to `latency_summary()`.

      Reading that bound: ______________

- [ ] `[G]` `latency_summary()`'s five figures — `cards_raised`, `cards_ruled`,
      `cards_resolved_without_ruling`, `median_latency_hours`,
      `oldest_open_days` — are identical before and after the round, against the
      unchanged pre-round `data/desk/events.jsonl`. Record both sets, not just
      "unchanged".

- [ ] `[G]` `rule(fp, "insufficient", …)` with a named missing item appends
      exactly one event carrying that item, readable back from `events.jsonl`.
      The same call with **no** named item raises `DeskRefused` and **writes
      nothing** — verified by the file's byte length being unchanged, not by the
      absence of a visible error.

- [ ] `[G]` `dismiss` with an empty reason is refused; `snooze` with no `until`
      is refused; `rebuild` requires neither; an unknown verb is refused, now
      against a four-member set. All four behave exactly as they do today.

- [ ] `[G]` A card marked incomplete is distinguishable from a complete one **on
      the rendered page**, and names which field is missing and why. Read from
      the board in a browser, not from the JSON response.

- [ ] `[G]` Task 6's answer is recorded: either a non-clock gap was
      constructible from Triggers A and B — with the fixture arrangement named
      here and walked — or it was not, and the report says the display is inert
      until Card C lands.

      Arrangement, or "not constructible": ______________

- [ ] `[G]` `python verify.py` → GREEN.

## `[H]` — a human judgement is genuinely required

- [ ] `[H]` **Was the completeness block information, or furniture?** You have
      now looked at a board where most cards read complete on six fields. Did
      the block tell you anything, or did your eye go past it? This is 0048
      clause 4's own test, asked of the thing this round built.

      Answer, in your words:

- [ ] `[H]` **Rule one real card `insufficient`, and name the thing you actually
      wanted.** Was `insufficient` the ruling you reached for, or did you reach
      for `snooze` and then remember it existed? 0059's own falsifier is a count
      of these after a month; this is its first data point, and a reluctant one
      counts.

      Answer, in your words:

- [ ] `[H]` **Would you defend striking 0048 clause 2's refusal, on re-read?**
      0059 clause 1 states in its own text that its reading of your Q2 answer is
      an inference you have not confirmed. This round is what makes that
      inference expensive to reverse. Say now if it was wrong.

      Answer, in your words:

---

## Stamping

Results go to `docs/UAT_card_completeness_results.md`, whose first line is the
uat stamp:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> -->
```

`gate=` is optional (`CONVENTION_briefs.md` §6). Omit it rather than assert a
count you did not observe; if you include it, it is checked against the
registered counts by `auditor_uat_stamp`.

Record every `[H]` answer in the operator's own words, not paraphrased
(`CONVENTION_briefs.md` §5), and name every stop condition that tripped.
