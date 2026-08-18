<!-- uat: commit=5a1bad9 dirty=true host=LucasGoonPC walked=2026-08-18 -->

# Results log — curator correction (walked 2026-08-18, LucasGoonPC)

Partner to `docs/UAT_curator_correction.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## Machine-verified

_No witness artefact found at `data/witness/curator_correction.json` for this sheet. The machine-verified section below has no witness observations to cite -- reported here, not silently omitted._

- **i1** On a machine configured `"estate": "personal"`, the Curator tab renders (not an absence message) and `/api/curator/header` returns `available` reflecting real on-disk state, not a gap.
  [no witness observation] not present in the cited witness artefact for this item id

## Human ruling

- **Ratify a row twice on purpose** — once as a normal ratification, once more attempting to re-ratify the same `session_id` with no status tag. The second attempt is refused as a no-op, exactly as it is today.
  [BLOCKED] Buttons in the "Ratified map (raw)" section don't appear to work -- couldn't attempt the re-ratification through the UI to confirm the no-op refusal.

- **Correct a ratification.** Ratify a row, then submit a correction with a different `project_id`. The resolved view (K1's join) reflects only the corrected `project_id`. The raw view (the tab's new "Ratified map (raw)" sub-tab) shows both rows, the corrected one marked, and it's legible without reading the TSV by hand.
  [BLOCKED] Same underlying issue -- the "Ratified map (raw)" section's controls don't work, so a correction with a different project_id couldn't be submitted through the UI to check.

- **Capture a folder from `unmapped_local_folders` through the UI.** Pick a folder K0 never proposed a candidate for, type a `project_id`, submit, and confirm the appended row carries `[provenance:hand-mapped:no-candidate]` and is staged (`git diff --staged` shows it) but not committed.
  [BLOCKED] Clicked "Capture & ratify" on local_c643dd90-4dcb-4370-ad5e-3539d4655f87 with project_id Test_conversation -- button doesn't appear to do anything, no row appended, no staged change. Server log shows POST /api/curator/k0/ratify returned 200 OK during this session, so the backend call succeeded but the UI did not reflect it.

- **Read the raw map view as a human deciding whether to trust it.** Does a superseded row read as "this was corrected, here's what it says now" or does it read as noise/a duplicate?
  [BLOCKED] Can't form a judgement on legibility of corrected rows since no correction is visible in the raw view -- the ratify POST returns 200 but the UI doesn't show the result, so there is nothing on screen to read as "corrected" vs "noise."

---

## Not walked, and why

- **Ratify a row twice on purpose** [BLOCKED] — once as a normal ratification, once more attempting to re-ratify the same `session_id` with no status tag. The second attempt is refused as a no-op, exactly as it is today. — Buttons in the "Ratified map (raw)" section don't appear to work -- couldn't attempt the re-ratification through the UI to confirm the no-op refusal.
- **Correct a ratification.** [BLOCKED] Ratify a row, then submit a correction with a different `project_id`. The resolved view (K1's join) reflects only the corrected `project_id`. The raw view (the tab's new "Ratified map (raw)" sub-tab) shows both rows, the corrected one marked, and it's legible without reading the TSV by hand. — Same underlying issue -- the "Ratified map (raw)" section's controls don't work, so a correction with a different project_id couldn't be submitted through the UI to check.
- **Capture a folder from `unmapped_local_folders` through the UI.** [BLOCKED] Pick a folder K0 never proposed a candidate for, type a `project_id`, submit, and confirm the appended row carries `[provenance:hand-mapped:no-candidate]` and is staged (`git diff --staged` shows it) but not committed. — Clicked "Capture & ratify" on local_c643dd90-4dcb-4370-ad5e-3539d4655f87 with project_id Test_conversation -- button doesn't appear to do anything, no row appended, no staged change. Server log shows POST /api/curator/k0/ratify returned 200 OK during this session, so the backend call succeeded but the UI did not reflect it.
- **Read the raw map view as a human deciding whether to trust it.** [BLOCKED] Does a superseded row read as "this was corrected, here's what it says now" or does it read as noise/a duplicate? — Can't form a judgement on legibility of corrected rows since no correction is visible in the raw view -- the ratify POST returns 200 but the UI doesn't show the result, so there is nothing on screen to read as "corrected" vs "noise."
