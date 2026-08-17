# UAT — curator correction (DECISIONS 0044/0046)

Walk against `docs/COWORK_BRIEF_curator_correction.md`'s acceptance checks. Mark each `[G]`/`[W]`/`[H]` per 0031 as you go.

- [ ] `[G]` On a machine configured `"estate": "personal"`, the Curator tab renders (not an absence message) and `/api/curator/header` returns `available` reflecting real on-disk state, not a gap.
- [ ] `[G]` On a machine configured `"estate": "both"`, the Curator tab shows a stated absence whose text names the `both`-estate exclusion (0039 clause 2), not a stale reference to work/MCF scoping.
- [ ] `[G]` On a machine configured `"estate": "work"`, behaviour is unchanged from before this round — `config/mcf_conversation_map.tsv` is still the map read and written.
- [ ] `[G]` A fresh personal-estate machine with no `config/personal_conversation_map.tsv` on disk shows K0–K5 as correctly blocked (same "header-only" reasoning as the work estate shows today), not an error.
- [ ] `[H]` **Ratify a row twice on purpose** — once as a normal ratification, once more attempting to re-ratify the same `session_id` with no status tag. The second attempt is refused as a no-op, exactly as it is today.
- [ ] `[H]` **Correct a ratification.** Ratify a row, then submit a correction with a different `project_id`. The resolved view (K1's join) reflects only the corrected `project_id`. The raw view (the tab's new "Ratified map (raw)" sub-tab) shows both rows, the corrected one marked, and it's legible without reading the TSV by hand.
- [ ] `[G]` **Revoke a ratification.** The revoked key disappears entirely from the resolved view / K1's join; the raw view still shows the original row and the revocation, neither deleted.
- [ ] `[G]` Attempting a correction with an identical `project_id` to what's already resolved is refused (`no_op_correction`), not silently appended.
- [ ] `[G]` Attempting a correction for a `session_id` never ratified is refused (`unknown_session_id`).
- [ ] `[G]` **Confirm the staged file matches the ratified estate.** On a personal-estate machine, ratify a row and check `git status` (or the tab's staged-diff view) shows `config/personal_conversation_map.tsv` staged — not `mcf_conversation_map.tsv`. (This was a real bug found and fixed mid-build; worth confirming directly rather than trusting the gate alone, since no existing test would have caught the wrong file being staged on a personal machine.)
- [ ] `[H]` **Capture a folder from `unmapped_local_folders` through the UI.** Pick a folder K0 never proposed a candidate for, type a `project_id`, submit, and confirm the appended row carries `[provenance:hand-mapped:no-candidate]` and is staged (`git diff --staged` shows it) but not committed.
- [ ] `[H]` **Read the raw map view as a human deciding whether to trust it.** Does a superseded row read as "this was corrected, here's what it says now" or does it read as noise/a duplicate?
- [ ] `[G]` `knowledge_index.py` run directly (not through the tab) against a personal-estate map produces correct output — confirms the shared resolver, not just the tab's use of it.
- [ ] `[G]` A deposit built (`run.py deposit`, or the equivalent test harness) from a machine with a populated `data/knowledge_curator/` carries nothing under that path in the resulting outbox.
- [ ] `[G]` The new deposit auditor fails loudly if the exclusion is bypassed — already verified independently during the build (a monkeypatched leak past the builder's own check was still caught by the auditor's outbox scan); re-confirm on your own machine if you want a second look.
- [ ] `[W]` `python verify.py` is green (9 auditors + 72 testers at time of writing), and the printed counts match what's claimed in the report.

## Also worth walking, found during the build rather than named in the brief

- [ ] Confirm `run.py app` starts cleanly on a machine with no `config/local.json`/`config/machines.json` entry at all (the real `"unknown"` default) — this used to be an untested path and would have crashed before the `Curator()` construction fix.
- [ ] Confirm `chronicler/review/module_contract.py`'s `capabilities()` output (the app-wide capability surface, not just the Curator tab) also uses the corrected reason string on a `both`-estate machine.
