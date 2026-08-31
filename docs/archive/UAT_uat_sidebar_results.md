<!-- uat: commit=b9fae8d dirty=true host=LucasGoonPC walked=2026-08-03 -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_uat_sidebar.md` + `COWORK_REPORT_uat_sidebar.md`, walked 2026-08-03
> Superseded by the sidebar being live, and by `CONVENTION_docs.md` §4's uat-stamp rules · Original purpose: slice 2 of two — give the *built, not walked* column a real action, so walking a sheet emits a stamped results log that advances the card itself.
> **Asserts the round was tested**, walked 2026-08-03. **Stop trusting** any gate count quoted inside it — the live gate is **12 auditors + 81 testers**.

# Results log — uat sidebar (walked 2026-08-03, LucasGoonPC)

Partner to `docs/UAT_uat_sidebar.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## A · reading a sheet (Task 1)

- **A1** Open a real walk-sheet from `docs/` by stem (not this one — pick
  [EVIDENCE] ←[32mINFO←[0m:     127.0.0.1:61581 - "←[1mGET /api/uat/sheet?stem=uat_sidebar HTTP/1.1←[0m" ←[32m200 OK←[0m

- **A2** Open `doc_provenance_coverage` or `repo_tier_producers` (the two
  [EVIDENCE]
  ```
  ←[32mINFO←[0m:     127.0.0.1:61636 - "←[1mGET /api/uat/sheet?stem=UAT_repo_tier_producers.md HTTP/1.1←[0m" ←[31m404 Not Found←[0m
  ←[32mINFO←[0m:     127.0.0.1:61636 - "←[1mGET /api/uat/sheet?stem=UAT_repo_tier_producers HTTP/1.1←[0m" ←[31m404 Not Found←[0m
  ←[32mINFO←[0m:     127.0.0.1:61637 - "←[1mGET /api/uat/sheet?stem=repo_tier_producers HTTP/1.1←[0m" ←[32m200 OK←[0m
  ```

## B · recording a verdict and evidence (Task 2)

- **B3** Set an item's verdict to **deferred** and leave the evidence box
  [DEFERRED] added deferred for this box - I was blocked when trying to emit

- **B4** Same as B3, for **blocked**.
  [BLOCKED] added block for this box - I was blocked when trying to emit without a comment

---

## Not walked, and why

- **B3** [DEFERRED] Set an item's verdict to **deferred** and leave the evidence box — added deferred for this box - I was blocked when trying to emit
- **B4** [BLOCKED] Same as B3, for **blocked**. — added block for this box - I was blocked when trying to emit without a comment

---

## Additional walk — 2026-08-15, LucasGoonPC (<!-- uat: commit=174e57e dirty=true host=LucasGoonPC walked=2026-08-15 -->)

Partner to `docs/UAT_uat_sidebar.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## Machine-verified

Machine-verified items below are cited from a witness run: `data/witness/uat_sidebar.json`, fixture `tests/witness/fixtures/uat_sidebar`, commit `174e57e`, ran 2026-08-15T11:08:51+01:00 on `LucasGoonPC`. Re-run the witness at that commit against that fixture to re-derive these observations.

- **B1** Pick one deterministic-shaped item (a command, an exit code, a
  [matched] — textarea round-trip of 3 pasted lines survived verbatim=True

- **B7** Press **Resume** on that banner. Confirm previously recorded
  [matched] — resume_banner_present=True resumed_verdict_populated=True

- **C1** With B1/B2 given real verdicts, emit. Open the emitted
  [no witness observation] not present in the cited witness artefact for this item id

- **C2** Check the stamp comment on the first line: `commit=` matches
  [no witness observation] not present in the cited witness artefact for this item id

- **B3** Set an item's verdict to **deferred** and leave the evidence box
  [matched] — item=W2 flagged=True message_visible=True message="W2: 'deferred' requires a reason recorded in the evidence box -- the useful line in every existing log is the one saying why, not just that."

- **B4** Same as B3, for **blocked**. *(Witness-covered.)*
  [matched] — item=W3 flagged=True message_visible=True message="W3: 'blocked' requires a reason recorded in the evidence box -- the useful line in every existing log is the one saying why, not just that."

- **B6** Open a sheet whose results log already exists (this one, after
  [matched] — 'already recorded' badge present on W4=True

## Human ruling

- **B2** Pick one judgement-shaped item (a "does this feel right" call).
  [EVIDENCE]

---

## Not walked, and why

Everything recorded on this walk carries a `[EVIDENCE]` verdict or a witness observation.
