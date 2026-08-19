<!-- uat: commit=a79bcc9 dirty=true host=LucasGoonPC walked=YYYY-MM-DD -->

# UAT — Phase 0: the Quartermaster frame

Walk against `docs/COWORK_BRIEF_quartermaster_frame.md`'s acceptance checks.
Mark each `[G]`/`[W]`/`[H]` per 0031 as you go — `[G]` gate-checked by
`verify.py`, `[W]` a deterministic non-gating check, `[H]` needs your
judgement. Fill in `walked=` above with the date you actually do this.

**This sheet is unusual: it walks a ruling, not a build.** Nothing here runs.
Every `[H]` item is a re-read against something real, and a *no* on any of them
is cheap now and expensive after Phase 4. `dirty=true` above is honest — the
`accepted` status flip and this pair's report were uncommitted when the sheet
was written.

---

- [ ] **Q1. `[H]` The §4 reconciliation, read cold: does it convince?**
  Read `docs/INTENT.md` §4's *"Not automated judgment"* bullet and then §8's
  *"What a standing ruling is, and what it costs"* — in that order, in one
  sitting, without reading this sheet's summary of them first.

  The question is not whether the reasoning is well-put. It is whether **you
  would defend the narrowing** — *a human* becoming *a human ruling*, standing
  rather than per-instance — knowing that it gives up per-instance review for
  that shape of decision, and that the tenth application of a policy is not
  something you looked at.

  **If it does not convince, promotion is cut from the frame here**, 0048
  clause 5 goes with it, and Phase 4 shrinks accordingly. That is the cheap
  version of this decision; the expensive version is cutting it out of built
  code.

- [ ] **Q2. `[H]` Read 0048's card anatomy against a real recent decision.**
  Pick any decision you actually made in the last fortnight — the silent-week
  removal, the config-difference call on the bench, the 0050 draft, anything.
  Now lay it against the six required fields: question, trigger, evidence with
  provenance, options with costs where measured, default, expiry.

  **Would that decision have fitted?** Specifically: was there a trigger you
  could point at, and evidence that existed *before* you decided rather than
  assembled afterwards to justify it?

  If it would not have fitted, the anatomy is wrong **now**, before a surface
  hard-codes it — and `desk.py` has already hard-coded it once.

- [ ] **Q3. `[H]` Read 0049 against your last three frontier spends.**
  The check most likely to refuse this entry, so do it properly. For each of
  the last three: which of the two legitimate purchases was it — judgment that
  unblocked stalled work, or an artifact that permanently moved work down-tier?

  **If any was neither**, answer honestly which way it cuts: is the rule right
  and the spend wrong, or the rule wrong? 0049 only earns its ratification if
  you would accept it binding you.

  *(The Fable session that produced this entire frame is itself a candidate
  for this check.)*

- [x] **Q4. `[G]` The mechanical checks.** *Answered in
  `docs/COWORK_REPORT_quartermaster_frame.md` and re-verifiable from the tree:*

  - DECISIONS numbering is sequential — 0044 → 0050, no gaps, no reuse.
  - Both entries carry Source lines naming the vision thread and their draft
    letters (`D-A`, `D-B`).
  - INTENT holds no facts after the append: §8 carries no counts, no paths, no
    module names, no "currently implemented as".

---

## Blocking items, not acceptance checks

Named here rather than in the results log so the walk is not marked complete
while they stand. Neither is a judgement call.

- [ ] **Q5. The `accepted` flip must be committed.** Both entries read
  `Status: accepted` in the working tree and `proposed` in committed history at
  `d6d75da`, while `d4f1c54`, `a79bcc9` and draft 0050 already cite 0048. The
  pair cannot close on a ratification that only exists on one disk.

- [ ] **Q6. Add a `Ratified:` date to 0048 and 0049.** The brief made
  same-sitting ratification a stop condition. It was honoured, but both entries
  carry only `Date: 2026-08-18` — the drafting date — so nothing in the log
  evidences the rule. The field also gives 0048 clause 5's sunset an anchor:
  a policy cannot expire from a date the log does not hold.

- [ ] **Q7. Run 0049's own homework before anything else cites clause 3.**
  `docs/investigation/2026-08-19_downtier_recurrence_probe.py` is written and
  untracked, scoped as `COWORK_BRIEF_curator_linking.md`'s Task 0. 0049's own
  *What would show this wrong* says the corpus test should be run **before
  anything is built on it**. Until then the entry is accepted on argument.
