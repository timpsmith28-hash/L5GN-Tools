<!-- uat: commit=a17fda8 dirty=true host=LucasGoonPC walked=2026-08-28 -->

# Results log — the conductor, Task 1 (walked 2026-08-28, LucasGoonPC) — INTERIM, one check open

Partner to `docs/UAT_conductor.md`. Walked against
`docs/COWORK_REPORT_conductor.md` at `a17fda8`, by Tim, with the `[G]` checks
verified from the tree by the walking thread.

**Declared `INTERIM` at first writing**, under `CONVENTION_docs.md` §4's four
conditions — not retrofitted when a revision turned out to be wanted:

1. It says so here, in the title, on the day it was first written.
2. **What it waits for, concretely:** the `[W]` below needs *a long run with a
   short TTL on hardware that has a GPU and LM Studio*, and a statement of
   whether memory stayed healthy without manual reloads. That is a run, not a
   judgement, and a reader can tell whether it has happened.
3. Every re-walk re-cuts the stamp above to the commit it ran against.
4. A superseded verdict is marked superseded and left standing, never deleted.

This log records a verdict and its evidence per item — never a computed pass.
`[EVIDENCE]` walked, with evidence · `[DEFERRED]` deferred, with a reason ·
`[UNCONFIRMED]` could not be verified by this thread, and what would confirm it.

---

## The checks

- **`[H]` 0037 is ratified and committed before any code lands.** — **[EVIDENCE]**
  Tim's answer, verbatim: *"yes you can tick that"*.

  What the thread could verify: `docs/DECISIONS.md` shows 0037 with
  `**Status:** accepted`, read directly from the log this session.
  **[UNCONFIRMED]** the commit the sheet cites, `8687d25` — git does not run
  from a Cowork sandbox against this repo (`CLAUDE.md`, environment hazards), so
  the SHA was not resolved. `git log 8687d25` on Windows would confirm it. Tim
  was told the SHA was unresolved before he ticked it, and ticked it knowing so.

- **`[G]` `--cool-down 0` and no `--model-ttl` reproduce today's behaviour
  exactly.** — **[EVIDENCE]** Read from the testers, not from the sheet's
  summary of them. `tests/tester_extract_claims.py:610` asserts *"call_lmstudio
  with no ttl given must not send a `ttl` field at all"*; `:641` asserts
  *"cool_down=0.0 (the default) must never sleep -- reproduces today's…"*.
  Mirrored for K4 at `tests/tester_match_claims.py:378` and `:421` against
  `call_lmstudio_generic`.

- **`[G]` `--cool-down N` pauses between conversations, never inside one; a
  conversation's windows stay contiguous and the cache is unchanged.** —
  **[EVIDENCE]** `tester_extract_claims.py:631` — three conversations at
  `cool_down=5.0` must sleep **exactly twice**, never after the last.
  `tester_match_claims.py:413` — two claims sharing `c-tl1` plus one in `c-tl2`
  at `cool_down=7.0` must sleep **exactly once**, between the conversations and
  not between the two claims. The cache-warm variants the sheet claims exist do
  exist: `tester_extract_claims.py:652` (`cool_down=9.0`) and
  `tester_match_claims.py:449` (`cool_down=3.0`).

- **`[W]` The TTL question is answered with evidence — a long run with a short
  TTL, and a statement of whether memory stayed healthy without manual
  reloads.** — **[DEFERRED]**, and it stays deferred deliberately.

  Tim's testimony, verbatim: *"the TTL question did help a bit in some of the
  extended runs I think but fine to leave it still open - we're planning some
  more llm work so we can hopefully cover it off there."*

  **That testimony is recorded and is explicitly not this check's evidence.**
  The check asks for a long run with a stated outcome; the answer is a hedged
  impression (*"a bit"*, *"I think"*) offered as such, and reading it as a pass
  would be the failure `UAT_desk_stale_card_results.md` D9 recorded one week
  earlier in the same estate: a deferral wearing the wrong reason.

  What *is* verified: `--model-ttl SECONDS` places LM Studio's documented `ttl`
  field on the wire with the right value — `tester_extract_claims.py:613`
  (`ttl=120.0`) and `tester_match_claims.py:382` (`ttl=90.0`). The wire format
  works; the operational question does not follow from it.

  **What clears it:** one long run with a short TTL on a rig with a GPU and LM
  Studio. Named as coming with the planned LLM work.

- **`[G]` Per-conversation timings are emitted and land in the ledger.** —
  **[EVIDENCE]**, with the scope reduction the sheet already declares. "Land in
  the ledger" is Task 2 and no ledger exists yet; what Task 1 owns is emission.
  `tester_extract_claims.py:793-801` — `make_timing_reporter` writes a `TIMING`
  line carrying `conversation_id` and `wall_clock_seconds` to the stream, and
  creates the JSONL file when `jsonl_path` is given. `tester_match_claims.py:466-473`
  — the same, carrying `claim_count`, which K4 reports in place of a message
  count.

## Defects the walk found in the walk-sheet, not in the repo

- **The sheet ticked four of five items at build time**, including one `[H]`.
  `CONVENTION_briefs.md` §6 makes walking a human act, so a pre-ticked `[H]` is
  a claim awaiting an operator rather than a walked check. The sheet was honest
  about this — it wrote *"worth a `git log` glance, not a rubber stamp"* — but
  the tick was already present before the glance happened. **A pre-ticked box is
  indistinguishable from a walked one to every reader and every tool.**
  Recorded here rather than fixed; the sheet is frozen.

- **The `[G]` evidence in the sheet was written from the tests, and it holds.**
  Every claim re-derived above matched. Noted because a sheet whose evidence
  survives independent re-derivation is the case this estate has least data on.

## Not walked

- The `[W]`, above, with its clearing condition named.
- Everything belonging to Tasks 2-6 — planner ordering, governor loop state,
  lock staleness, surface behaviour, real-hardware walks, estimate-vs-actual —
  is out of this round's scope and absent from the sheet by design, not skipped.

**The card is walked and not closed.** It re-walks when the TTL run happens.

---

## Correction, 2026-09-02 — `gate=` removed from the stamp

**No verdict above is changed.** The stamp's `gate=12a/81t` field was removed;
`commit=` and `walked=` stand, and they are what `auditor_uat_stamp` requires.

**Why.** Registering a thirteenth auditor on 2026-09-02 turned this log red.
`auditor_uat_stamp` compares `gate=` — a fact about the moment of the walk —
against `verify.py`'s count at HEAD. That comparison has two stable outcomes
over time: the gate goes red whenever gate composition changes, or historical
stamps get re-cut to match. **The second is laundering a number into a document
to satisfy a check, which is the incident that auditor's own docstring says it
was built to catch.**

`gate=` is optional in that auditor, and it duplicates something `commit=`
already fixes — check out that commit and count the lists. Removing a
denormalised copy is not losing provenance; keeping one beside its source is how
the two drift.

**The auditor is not fixed by this edit and should be.** Resolving `gate=`
against the census *at the stamped commit* would make the field meaningful
again. That is a code change, it is outside the round that found this, and it
wants its own card. Recorded here rather than done in passing.
