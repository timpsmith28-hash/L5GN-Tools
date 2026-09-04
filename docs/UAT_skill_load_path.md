# UAT walk-sheet — `skill_load_path`

**Brief:** `docs/COWORK_BRIEF_skill_load_path.md`. This sheet is the brief's
acceptance section, extracted so it can be walked and stamped
(`CONVENTION_briefs.md` §2). They were written together, before the build.

**Checks: 9 — 7 `[G]`, 2 `[H]`.** The `[H]` count is deliberate: one asks
whether the defect is perceptible in use, which no assertion can answer; the
other asks whether a mechanism is one the operator would rely on, which is a
judgement about reliance rather than about behaviour.

**Walking is a human act** (`CONVENTION_briefs.md` §6). This sheet is not
stamped by the thread that did the build, and a passing test is not a walk.

**Task 1 must be walked from a fresh Cowork thread**, not from the one that
built the round and not from this brief's own table. The table is the thing
under test.

---

## The round's falsifier

*Did the refresh hold?*

If a fresh Cowork thread — today, and again a week from now — loads any of the
four skills with its pre-2026-08-31 text, then `save_skill` is not the
mechanism and the fix is upstream of this repo.

**Consequence, written before the answer is known:** this round produces a
recorded `subject-not-enumerable` and a `CLAUDE.md` correction, and nothing
else. No checker, no sync, no habit. The estate would then know it cannot
guarantee what its own skills say when they run — a finding worth having
plainly rather than a gap worth papering.

Date of the first fresh-thread check: ______
Date of the one-week re-check: ______

---

## `[G]` — a machine or an unambiguous procedure decides

- [ ] `[G]` In a **fresh** Cowork thread, each of the four skills reports the
      tracked authority line. Record each verbatim, one line each:

      - `docs-archivist` → expects `docs/CONVENTION_docs.md` §4
        got: ______________
      - `brief-scribe` → expects `docs/CONVENTION_briefs.md`
        got: ______________
      - `decision-scribe` → expects `docs/CONVENTION_decisions.md`
        got: ______________
      - `round-closer` → expects its 2026-08-28 publication note
        got: ______________

- [ ] `[G]` The line-ending-normalised comparison between the tracked copies and
      the deployment is re-run (0057 cl.8) and its result recorded, whichever way
      it falls. Not "unchanged" — the counts.

- [ ] `[G]` Task 2's answer exists in the tree as **one of exactly two things**:
      a reader that can go red on more than one machine, **or** a recorded
      `subject-not-enumerable` naming why (0060 cl.2). Not silence.

      Which: ______________

- [ ] `[G]` `CLAUDE.md`'s Skills row no longer asserts an identity that is false
      in Cowork, and its discharged-markers paragraph no longer asserts a
      present-tense fact about what loads.

- [ ] `[G]` `docs/CONVENTION_skills.md` either carries the
      source-versus-deployment rule, or the report says why it does not.

- [ ] `[G]` No rule introduced by this round exists only in a skill file — grep
      the four skills for any sentence not present in a convention (0052 cl.3).

- [ ] `[G]` `python verify.py` → GREEN.

## `[H]` — a human judgement is genuinely required

- [ ] `[H]` **Had you noticed?** Two stale skills fired at you on 2026-09-04 and
      neither was caught as a pattern until the third. Reading the four
      refreshed ones now — is the difference visible to you in use, or only in a
      diff? If only in a diff, this class of defect is invisible at the point it
      does harm, and that is the argument for whatever Task 2 concludes.

      Answer, in your words:

- [ ] `[H]` **Is `save_skill` a mechanism you would rely on?** It restored four
      deployments in one session, from a Cowork thread, with no record in the
      repo that it happened except the brief. Would you rather it left a tracked
      artefact — and if so, that is a card, not a line here.

      Answer, in your words:

---

## Stamping

Results go to `docs/UAT_skill_load_path_results.md`, whose first line is the uat
stamp:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> -->
```

`gate=` is optional (`CONVENTION_briefs.md` §6). Omit it rather than assert a
count you did not observe.

Record every `[H]` answer in the operator's own words, not paraphrased
(`CONVENTION_briefs.md` §5), name every stop condition that tripped, and record
the date set for the one-week re-check — the falsifier is not answered by this
walk alone.
