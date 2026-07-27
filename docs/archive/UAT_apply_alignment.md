> **ARCHIVED** 2026-07-27 · completed pair (walk-sheet) · walked; results in `UAT_apply_alignment_results.md`
> Superseded by: nothing — walked clean, all items ruled per the results log's closing walk-sheet cross-reference table.
> Both apply passes (contaminated 412, corrected 343) are accounted for in the results log; this checklist was walked only against the corrected, final state.

# UAT walk-sheet — apply alignment (golden close-out)

**Brief:** `docs/COWORK_BRIEF_apply_alignment.md`
**Report:** `docs/COWORK_REPORT_apply_alignment.md`
**Walked:** 2026-07-27, knight (`l5gn-castle-worker`) + gaming rig (`LucasGoonPC`).
**Gate:** `python verify.py` → 6 auditors + 42 testers, all green (confirmed both
before and after the seed_suppress fix landed mid-run).

Every item below is **ready to walk**, none marked passed — that is Tim's call,
and the result belongs in `docs/UAT_apply_alignment_results.md` with a commit
stamp, or `auditor_uat_stamp` refuses the commit. Items ordered so a failure
stops the walk cheaply. This run executed the apply **twice**: a first pass
that a mid-walk finding proved was built on a registry defect, and a corrected
second pass after the fix. The checklist below is walked against the
**corrected, final state** — the first pass and the defect that invalidated it
are narrated in the report and the results log, not re-litigated here.

---

### P — hard preconditions (brief's gate, refuse to `--apply` unless ALL true)

- [ ] **P1.** Scorer fixed (`COWORK_BRIEF_relink_scoring.md` A/B/C landed,
  committed, UAT walked) — `docs/UAT_relink_scoring_results.md` closes this.
- [ ] **P2.** Registry ratified and `build_registry.py` re-run so the live
  registry is the ratified one.
- [ ] **P3.** Clean identity base (fresh build or 0011 reset + re-key done).
- [ ] **P4.** Crystal Spire `first_seen` set in `config/project_registry.json`.
- [ ] **P5.** Backup taken, verified off-box.

### T0 — backup and the two irreplaceables

- [ ] **T0.1.** `run.py backup` run, verified off-box.
- [ ] **T0.2.** Chat exports and `scraped_gemini/*.json` + `manifest.jsonl`
  confirmed on disk before anything else proceeds.

### T1 — re-derive evidence LIVE

- [ ] **T1.1.** `build_registry.py` / `build_inventory.py` / `xref_filenames.py`
  / `extract_path_mentions.py` all re-run against the **live** vault, not a
  snapshot.
- [ ] **T1.2.** `link_evidence.project` values are registry ids, not folder
  names or canonical_name strings (Finding-3 check).

### T2 — relink dry-run is the GO/NO-GO gate

- [ ] **T2.1.** Dry-run table produced and read together before any `--apply`.
- [ ] **T2.2.** No auto-link rests on a single origin; top auto-links
  spot-checked.
- [ ] **T2.3.** Ambiguous/suggestion volume reviewable, not a flood.
- [ ] **T2.4.** Breadcrumbs correct (project/program rollup).
- [ ] **T2.5.** Fresh GO ruling given in chat, against the table actually
  applied (not a stale earlier table).

### T3 — apply, only on GO

- [ ] **T3.1.** `relink.py --apply` run only after a GO on the matching table.
- [ ] **T3.2.** Applied change count reconciles exactly against the GO'd
  table (auto-link + suggestion + ambiguous + downgrade = applied total).

### T4 — verify the alignment landed clean

- [ ] **T4.1.** `project_link` orphan check returns empty (every linked
  project resolves to a real registry row).
- [ ] **T4.2.** No legacy title-case/folder-name project rows resurrected.
- [ ] **T4.3.** Per-project thread counts plausible; locked-thread total
  matches the GO'd table's auto-link count plus prior locked threads.
- [ ] **T4.4.** `review_queue` category counts (`link_upgrade/confirmed`,
  `link_ambiguous/pending`) match the GO'd table exactly.
- [ ] **T4.5.** Any stale/leftover `review_queue` rows from a superseded
  apply are identified, explained (not just dismissed), and their
  disposition is Tim's explicit call.

### F — registry-generator finding (seed_suppress), mid-run

- [ ] **F1.** The false-auto-link defect (auto-regenerated bare alias
  overriding a curated deliberate removal) is root-caused to
  `build_registry.py`'s `seed_aliases()` / `_merge_alias_lists`, not
  guessed at.
- [ ] **F2.** Fix (`seed_suppress`) ships with hermetic test coverage in
  `tester_build_registry.py`, `verify.py` green before commit.
- [ ] **F3.** All threads false-linked under the defect are identified by
  direct evidence cross-reference (not assumed), and every one is
  confirmed clean (no Castle/Archive-derived evidence remaining) after the
  redo.
- [ ] **F4.** The redo (registry rebuild → S5 rescan → reset tainted
  threads → fresh dry-run → fresh GO → re-apply) is a full clean redo, not
  a manual patch of the contaminated state.

### T5 — deposit / consume, wall check

- [ ] **T5.1.** Deposit run on the correct side (producer rig), not the
  knight.
- [ ] **T5.2.** `consume` ingests both `personal` and `work` estates,
  `verified=True` on each.
- [ ] **T5.3.** Wall held: `personal` and `work` land in separately
  namespaced directories, no cross-contamination.
- [ ] **T5.4.** `drift` computes (not `needs_inputs`) for both estates —
  if blocked, the blocker is root-caused and fixed or explicitly deferred,
  not silently skipped.

---

## UAT — acceptance checks (Tim walks these)

- [ ] **Golden.** Personal-estate chat threads appear aligned to their
  projects and programs on the read surface; breadcrumbs correct.
- [ ] **Provenance.** Spot-check of auto-linked threads — each plausibly
  *about* the project it linked to.
- [ ] **No over-count.** No auto-link rests on a single sentence/origin.
- [ ] **Identity.** T4 queries return the expected empties/matches.
- [ ] **Wall.** Work/MCF threads are not aligned (expected, no export);
  personal/work deposit wall held.
- [ ] **No laundering.** The seed_suppress defect and its 6 falsely-linked
  threads are documented as found-and-fixed, not quietly absorbed into a
  clean-looking final count.

---

Mark each **ready to walk**, never "passed". Record the walk in
`docs/UAT_apply_alignment_results.md` with a uat stamp
(`<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> -->`).
