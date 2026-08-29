<!-- uat: commit=a17fda8 dirty=true host=LucasGoonPC walked=2026-08-28 gate=12a/81t -->

# Results log — scanner bug fixes (walked 2026-08-28, LucasGoonPC) — INTERIM, work-rig checks open

Partner to `docs/UAT_scanner_bugfixes.md`, built on `23b5ffa` and gate-frozen at
`6d09eb3`. Walked against `docs/COWORK_REPORT_scanner_bugfixes.md`.

**Declared `INTERIM` at first writing**, under `CONVENTION_docs.md` §4:

1. Said here, in the title, on the day first written.
2. **Waiting for:** a full-estate `run.py build` **on the work rig, where
   Chronicler lives**. A1 says so itself; A4's second half and B2/B3 need the
   same run or a forced oversize case.
3. Every re-walk re-cuts the stamp above.
4. Superseded verdicts are marked and left standing.

**This sheet predates the `[G]`/`[W]`/`[H]` convention** (`CONVENTION_briefs.md`
§4) and carries none. It is **not** unclassified, though — it uses an older
vocabulary, *"Mark each check ready to walk, never passed — the walk is Tim's"*,
plus per-item notes naming which need the work rig. The retrofit below assigns
each item the marker it would carry today. **The sheet is frozen and is not
edited**; this mapping lives here, which is where a divergence between a frozen
sheet and a current convention belongs.

`[EVIDENCE]` walked with evidence · `[UNCONFIRMED]` not verifiable by this
thread, with what would confirm it · `[DEFERRED]` deferred with a reason.

---

## A — scope discipline

- **A1** *(retrofit: `[H]`)* full-estate build including Chronicler yields a
  `todo_adr` marker count in the low tens. — **[DEFERRED]** The sheet already
  says it: *"needs the work rig where Chronicler lives."* Not runnable here.

- **A2** *(retrofit: `[G]`)* the report never lists a path under `raw_*`,
  `chat_threads/`, `vault_staging/`, `Takeout/` or `*_files/`. —
  **[EVIDENCE] the rule holds, and the check as written is defective.**

  Searched `report.html` and `data/estate.json` for all five fragments.
  `raw_claude_files` returns **exactly one hit in each**, and it is the same
  string. Walked to its location in the parsed JSON rather than grepped:

  ```
  .projects[6].todo_adr_scanner.markers[32].text
      '"-shaped strings out of `raw_claude_files/conversations.json` was both a'
  ```

  **That is a TODO/ADR marker whose prose mentions the path — not the report
  listing a path under it.** The rule is intact. The instruction that tests it —
  *"search the report for `raw_claude_files` and expect nothing"* — is broader
  than the rule and fails on legitimate content. **A check that cannot pass while
  any document in the estate discusses the path it forbids will read red forever
  and be trained past**, which is 0048 clause 4's failure in the opposite
  direction. Carried to the defects section.

- **A3** *(retrofit: `[G]`, doctrine)* no chat-transcript text anywhere in the
  report or `data/**/*.json`. — **[UNCONFIRMED].** The one string located under
  A2 is a path mention inside a marker, not transcript text, so nothing found
  contradicts it — but **absence was not proved**, only unsampled. Confirming it
  needs a content scan with a stated definition of "transcript text", which this
  walk did not have and did not invent.

- **A4** *(retrofit: `[G]`)* each content scanner's per-project JSON carries a
  `scope` block with `skipped_paths` and `skipped_by_reason`; on a project with a
  chat archive, `data_dir` appears with a non-zero count. — **[EVIDENCE] on the
  first half, [DEFERRED] on the second.** **83 files under `data/` carry a
  conformant `scope` block** with both keys present. Sampled
  `data/blast_radius/*.json`: the block exists and `skipped_by_reason` is empty,
  which is correct for projects with no chat archive. The `data_dir` non-zero
  case needs the project that *has* one — Chronicler, on the work rig. Same
  blocker as A1.

## B — the report polices itself

- **B1** *(retrofit: `[G]`)* `data/estate.json` and the `DATA` block inside
  `report.html` both parse as JSON. — **[EVIDENCE]** Both parsed this session.
  `estate.json` loads, top keys `generated_at, toolkit_version, toolkit_commit,
  toolkit_dirty, estate_root, estate_name`. The `DATA` block extracted from
  `report.html` parses at **982,586 bytes**.

- **B2** *(retrofit: `[W]`)* an oversize case caps honestly or exits non-zero,
  never a truncated report reading as complete. — **[DEFERRED]** Requires forcing
  an oversize case or pointing at Chronicler pre-fix. Neither is available here.

- **B3** *(retrofit: `[W]`)* payload-anomaly banner names the scanner and
  project. — **[DEFERRED]** Downstream of B2; nothing anomalous to render.

- **B4** *(retrofit: `[G]`, historical)* `verify.py` GREEN at the build-time gate
  — **six auditors and thirty testers**, per the sheet — with
  `tester_scanner_scope` and `tester_report_selfcheck` OK. — **[EVIDENCE as a
  frozen claim.]** The sheet carries `<!-- gate-frozen: commit=6d09eb3 -->`, so
  its figure is a correct build-time record and **not** a claim about today.
  Today's gate is larger and both named testers are still registered and green
  in the run that stamped this log. The frozen marker is doing exactly the job
  `CONVENTION_docs.md` §4 gives it.

  **The counts are spelled in words here deliberately, and the reason is a
  defect this walk caused.** See the defects section.

## C — recorded only

- **C1** *(retrofit: `[H]`)* confirm Task C belongs to the governance run and is
  not expected in this pair. — **[NOT ANSWERED].** Put to the operator, not
  answered in this session. Recorded as unanswered rather than assumed.

## Defects the walk found in the sheet, not in the repo

- **A2's search instruction is broader than A2's rule** (above). The rule forbids
  the report *listing paths* under those prefixes; the instruction forbids the
  *string appearing at all*, which any document discussing the scanner's own
  subject will trip. **This is the second time today a check in this estate has
  been found unable to see, or unable to avoid seeing, the thing it rules on** —
  `auditor_conversation_map_pin` names a path where 0040 clause 4 names a
  pattern. Same class, opposite direction.

- **This log's first draft failed the gate, and the gate was right.** B4 quoted
  the sheet's frozen figure in the compound `N auditors + M testers` form.
  `auditor_doc_claims` matched it, compared it to the live registry, and refused
  the commit — reporting that the doc claimed the sheet's build-time figure
  while `verify.py` registers today's larger one. **The auditor was not wrong —
  this log is live and
  carries no `gate-frozen` marker, so a compound count in it is a present-tense
  assertion whatever the surrounding prose says.** The failure is precisely the
  incident that created `auditor_uat_stamp`: a stale number recovered from a
  frozen document and laundered into a live one. It was done here by a walking
  thread, in a results log, one day after that history was re-read.

  **Fixed by not making the claim** — the figure is spelled in words, and the
  reader is sent to the frozen sheet for the digits. **Not** by adding a
  `gate-frozen` marker to this log, which would have bought green by asserting
  something false: this log is interim and will be re-walked. `NEVER_FREEZE`
  would not have caught that, because it guards the trinity and not results
  logs.

- **The sheet carries no `[G]`/`[W]`/`[H]` markers** because it predates them.
  The retrofit above shows the mapping is mechanical for this sheet: its
  per-item notes already say which need the work rig. **Three further sheets in
  `docs/` are in the same state** — `estate_restructure`, `file_census`,
  `intent_evidence` — carrying about 160 items between them, and
  `auditor_uat_sheet_readable` is green on all of them, so whatever it checks,
  marker presence is not it.

## Not walked

- A1, A4's `data_dir` case, B2, B3 — all needing the work rig or a forced
  oversize case, with the run named as what clears them.
- A3 — unconfirmed, needing a definition before it can be checked.
- C1 — not answered.

**The card is walked and not closed.** Four checks carry evidence, one is
unconfirmed, four are deferred with named clearing conditions, and one awaits
the operator.
