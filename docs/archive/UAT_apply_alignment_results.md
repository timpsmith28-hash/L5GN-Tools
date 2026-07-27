<!-- uat: commit=5711962 dirty=false host=l5gn-castle-worker walked=2026-07-27 -->

> **ARCHIVED** 2026-07-27 · completed pair (results) · walked 2026-07-27, ruling "closed for this round"
> Superseded by: nothing — terminal results log of the golden-close-out effort.
> The first, contaminated apply (412 changed, 55 auto-links) is preserved in this file with its own in-body superseded notice — read that notice, not the raw numbers, if skimming. The corrected/final state is the second pass (343 changed, 3 auto-links), the "Task 10 re-verification" section, and the closing walk-sheet cross-reference table.

# Results log — apply alignment (walked 2026-07-27, knight)

Partner to `docs/UAT_apply_alignment.md` / `docs/COWORK_BRIEF_apply_alignment.md`.
This is the golden-close-out list's resumption of the golden apply, unblocked by
the repo-tier producer round (`docs/COWORK_REPORT_repo_tier_producers.md`).

This log records **evidence**, not acceptance beyond what's stated. `verify.py`
GREEN proves the code works; only Tim ruling on each item closes it.

---

## Hard preconditions — checked on the knight, before any write

| # | Precondition | Status | Evidence |
|---|---|---|---|
| 1 | Scorer fixed (A/B/C landed, committed, UAT walked) | **MET** | `52193bd` committed; UAT walked at the table 2026-07-27 — see `docs/UAT_relink_scoring_results.md`. Precondition was unconfirmed going into this session (no results log existed); closed by that document. B's exact decision-table counts deferred to Task 7's live dry-run (named the decisive walk by the original report/brief). |
| 2 | Registry ratified, incl. CID-as-program, `build_registry.py` re-run | **MET (structure confirmed; re-run pending)** | `config/project_registry.json` on the knight carries `programs: [l5gn-os, wizforge-analytics, cid, command-deck]`, three-tier shape (`programs` + `projects`) confirmed present. The **re-run** of `build_registry.py` against the live vault happens in Task 6 (Step 4 apply-brief Task 1) — not yet executed as of this precondition check. |
| 3 | Clean identity base (fresh build, empty `link_evidence` / `project_link`) | **MET** | On the knight: `SELECT COUNT(*) FROM link_evidence` = 0; `SELECT COUNT(*) FROM threads WHERE project_link IS NOT NULL` = 0. Vault at `/home/l5gn/vault/chronicler.db`. |
| 4 | Crystal Spire `first_seen` set | **MET** | `config/project_registry.json` on the knight: `crystal-spire` → `first_seen: 2026-05-16`. |
| 5 | Backup taken and verified off-box | **MET** | `run.py backup` on the knight produced `chronicler-20260727T095312Z.db` (76,419,072 bytes), local at `~/vault/backups/`. The auto-push reported `LOCAL ONLY` (no `backup_target` configured on the knight's own `local.json` entry — the automated push path is not wired up). Verified off-box by manual pull instead: `scp l5gn-castle:/home/l5gn/vault/backups/chronicler-20260727T095312Z.db` to the gaming rig at `C:\Users\timps\Documents\Backups\chronicler_backups\`, confirmed landed, same size (76,419,072 bytes). Both irreplaceable inputs confirmed present on the knight: chat exports (`~/vault/chat_threads/raw_claude_files/{conversations.json,projects/,users.json}`, `raw_gemini_files/Takeout/`) and Gemini scrapes (`~/vault/scraped_gemini/*.json` + `manifest.jsonl`, 70 files). |

**All five preconditions must be met before `--apply` runs anywhere in Task 9.**
All five now MET. Precondition 2's registry **re-run** (not just structural
presence) still happens as part of Task 6, next up.

**Carried-open housekeeping (not a blocker):** the knight's automated off-box
backup push (`backup_target`/`backup_transport` in the knight's own
`config/local.json`, per `docs/KNIGHT_PLAYBOOK.md` §10.2) is not configured —
today's off-box copy was a manual pull from the rig, not the automated push
`run.py backup` is designed to do. Worth wiring up properly in a future round
so every `ingest`'s pre-flight backup is off-box automatically, not just
this session's.

---

---

## Task 1 (apply-alignment) — re-derive evidence LIVE, walked 2026-07-27

Run on the knight (`l5gn-castle-worker`) against the live vault, in order:
`build_registry.py --report-aliases` (inspect) → `build_registry.py` (write, 31
entries) → `build_inventory.py --force` (34 built, 9 concept projects with no
deposit of their own, 15 missing) → `build_activity.py --force` (34 built, 9
concept projects with no window, 15 missing) → `xref_filenames.py` dry-run then
`--apply` (1103 rows / 109 threads) → `extract_path_mentions.py` dry-run then
`--apply` (254 rows / 137 threads).

- [x] **A1.** `L5GN-Crystal-Spire`, `L5GN_Armory_v4`, `smelt-gateway` and the
  estate-infra repos (`L5GN-Castle`, `L5GN-Archive`, `L5GN_Managed_Workspace`)
  all carry a `file_inventory` from this build. **New coverage: 34 built** vs
  the old 10-of-58 baseline — near-complete for folder-backed targets.
- [x] **A2.** Spot-checked: `crystal-spire`, `citadel-microide`,
  `continuous-ingestion-daemon`, `l5gn-estate-infrastructure` and 5 other
  concept projects report `(concept project -- files carried by its repos)` —
  no synthetic inventory. **Observation, not a defect:** 10 single-incarnation
  MCF projects (`mcf-sol-config`, `gemtopairs`, `mcf-tss-to-assets`,
  `mcf-validation-automation`, etc.) have a project canonical_name identical to
  their one repo's canonical_name, so both tiers independently match the same
  real deposit and both carry a genuine (non-synthetic) copy of the same
  inventory. Confirmed this is handled by `relink.py`'s existing
  `collapse_lineage()` (folds same-lineage project+repo candidates into one
  before rivalry is judged, never sums origins) — not a re-introduction of the
  double-count class of bug. Visible directly in the applied `link_evidence`:
  both `mcf-sol-config` and `solconfig-repo` carry evidence for the same files.
- [x] **B1.** No concept project carries a `2026-07-17..27`-shaped window —
  every concept project's `build_activity` line reads `--` (no window). Real
  repos carry real dates (e.g. `L5GN_Armory_v4` 2026-06-17..2026-06-24,
  `VBA-JSON` 2014-09-15..2019-01-28).
- [x] **B2.** No fabricated-window risk observed — Crystal Spire, Citadel/Armory
  and estate-infra repos all carry real commit- or mtime-derived windows, not
  scan-date ranges. (Deep per-thread time-plausibility spot-check deferred to
  Task 10/the golden read-surface check, per the original UAT sheet's ordering.)
- [x] **C1.** `world_graph.json` resolves to `l5gn-crystal-spire` (the repo id,
  52 unique-basename hits), not `crystal-spire` (the concept id) and not any
  canonical_name string.
- [x] **C2.** `SELECT DISTINCT project FROM link_evidence` — all 37 distinct
  values resolve in the registry by id (checked programmatically against
  `project_registry.json`'s project + repo + program ids). **NONE unresolved.**

**S4.1 (apply-alignment Task 1) is complete.** 1357 evidence rows written
(1103 filename_xref + 254 path_mention) across the live vault. Proceeding to
Task 2 (relink dry-run, the GO/NO-GO gate).

---

---

## Task 2 (apply-alignment) — relink DRY-RUN, the GO/NO-GO gate

`relink.py --out data/relink_dryrun.txt` on the knight, live vault, post-S4/S5.

**Decision table:** 725 threads scanned. auto-link 52, suggestion 232,
ambiguous 114, downgrade 0, no-op 327 (reconciles: 52+232+114+0+327=725).

- **Auto-link quality:** sample of 15 (of 52) inspected, every one rests on
  **≥2 independent origins**. The single 0.997-adjusted case
  (`l5gn-crystal-spire`, filename `tui.py` + path token
  `L5GN-Crystal-Spire`) has **2 distinct origins** — genuine corroboration,
  not the old single-sentence 0.997 double-count pattern (which was one
  origin cited twice).
- **No auto-link on a single origin** observed in the sample.
- **Breadcrumbs:** `smelt-gateway` → `[L5GN OS > L5GN Estate Infrastructure >
  smelt-gateway]`, correct parent chain. CID rolls to its program:
  `[Citadel MicroIDE (CID) > Citadel MicroIDE]` (project),
  `[Citadel MicroIDE (CID) > Continuous Ingestion Daemon >
  L5GN-Continuous-Ingestion-Daemon]` (repo). A few entries match the CID
  program directly and render as `[Citadel MicroIDE (CID) > Citadel MicroIDE
  (CID)]` — cosmetically duplicated (ancestor and candidate are the same
  program) but not incorrect.
- **Suggestion + ambiguous volume:** 346/725 threads (48%) — Tim's assessment:
  "feels a bit of a flood but that is only because it's the first baseline...
  manageable for the purposes of this UAT" — with a follow-up idea to revisit
  once more auto-links are locked in, as those may lend corroborating
  credibility to some of the reviewable set on a future pass. A large share of
  the volume is a homogeneous, explainable cluster (generic single-origin
  body-mention aliases like `Smelter`, `DiT` correctly held at `suggest`
  rather than auto-linking — Task B's corroboration floor working as
  intended), plus the known ~14% undated-thread (`time:unknown`) population
  from DECISIONS 0003/0015.

**GO/NO-GO ruling: GO.** Tim's call, given in chat 2026-07-27. Proceeding to
Task 8 (the four-names ruling, decided at the table against this same dry-run
table) before Task 9 (`relink --apply`).

---

---

## Task 8 (apply-alignment) — four unmapped Claude names, ruled 2026-07-27

Tim's ruling on the four Claude-project-container names surfaced as unmapped
by `build_registry.py --report-aliases`:

1. `Crystal Spire` → yes, alias of `crystal-spire`.
2. `UCPSmelter` → yes, alias of `universal-content-pipeline`.
3. `L5GN OS Smelter` → new project, under the `l5gn-os` program (added as
   `l5gn-os-smelter`).
4. `ProjectWizard` → alias of `l5gn-tools` (UAT/end-user-feedback threads for
   the L5GN-Tools project itself).

All four resolved cleanly in `build_registry.py --report-aliases` after the
registry edit (0 unmapped remaining). `l5gn-os-smelter` currently carries no
`link_evidence` — expected and not a defect: a Claude-project-container name
matching an alias only silences the "unmapped" nag (`attach_claude_aliases()`
in `build_registry.py`); it does not itself create evidence. Evidence still
requires the literal alias text to appear in message content.

### Re-run per Task 8 step 3 — first pass (post four-name additions)

`build_inventory.py --force` / `build_activity.py --force` / `xref_filenames.py
--apply` (1103 rows, unchanged) / `extract_path_mentions.py --rescan --apply`
(254 rows, unchanged — the four new alias strings are Claude-project-container
names, not literal text found in unscanned message bodies) / `relink.py
--out data/relink_dryrun.txt`:

**Decision table:** 725 scanned. auto-link 55, suggestion 216, ambiguous 167,
downgrade 0, no-op 287 (55+216+167+0+287=725).

Ambiguous jumped 114 → 167, unexplained by the four additions alone.
Investigated before taking this table to Tim:

- `SELECT` over `link_evidence` grouped by (thread, project, signal, detail) —
  zero duplicate rows. 1357 total = 1103 filename_xref + 254 path_mention
  exactly. Ruled out data corruption.
- Read `relink.py`'s `_matchers_for()` — each registry target compiles its own
  boundary-anchored regex independently; no shared/global pattern. Ruled out
  array-ordering / cross-target bleed.
- Root cause: `l5gn-bridge-repo`'s `Bridge` / `L5GN_Bridge` aliases had no
  `low_signal_body` flag, unlike every other short/common-English-word alias
  already in the registry (`Castle`, `Archive`, `Auditor`, `Chronicler`,
  `Sovereign`). `Bridge` was scoring as a 0.60 body-alias rival across a large
  number of unrelated threads, driving most of the ambiguous growth plus
  general suggestion noise.

Presented to Tim with two options; **Tim chose to add `low_signal_body` now**
rather than leave it. Edited `config/project_registry.json` (rig, gitignored):
added `"low_signal_body": true` to the `l5gn-bridge` project entry, same
precedent as Castle/Archive/Auditor/Chronicler/Sovereign. `relink.py`'s
`load_registry()` (`repo.get("low_signal_body", proj.get("low_signal_body"))`)
makes the repo tier (`l5gn-bridge-repo`) inherit the flag automatically — no
separate repo-level edit needed. Shipped via `scp` (gitignored file — not
committed), knight ran `build_registry.py` to regenerate the live registry,
then `relink.py --out data/relink_dryrun.txt` again. `xref_filenames.py` /
`extract_path_mentions.py` were **not** re-run — `low_signal_body` only
affects `relink.py`'s live scoring, not the stored evidence rows.

### Re-run per Task 8 step 3 — second pass (post Bridge `low_signal_body` fix)

**Decision table:** 725 scanned. auto-link 55, suggestion 236, ambiguous 121,
downgrade 0, no-op 313 (55+236+121+0+313=725).

- Ambiguous: 167 → **121** (-46), landing close to the original pre-four-name
  baseline of 114 (+7 net, consistent with genuine new alias coverage rather
  than noise). Confirms the `low_signal_body` diagnosis was correct.
- No `l5gn-bridge-repo` entries observed anywhere in the ambiguous table in
  this run (previously a frequent rival there).
- `l5gn-bridge-repo` still surfaces correctly on **title** hits, e.g.
  `0.800 ... name_alias:Bridge@title(0.80)` — the fix only demoted body hits
  (0.60→0.15), title-alias weight is untouched.
- Auto-link: 52 (original baseline) → 55, +3 net across both alias rounds —
  small, explainable by the new legitimate alias coverage (Crystal Spire,
  UCPSmelter, ProjectWizard all resolving unambiguously in a few threads).
- No-op: 327 (baseline) → 313; suggestion: 232 (baseline) → 236. Table shape
  is now close to the original baseline plus a modest, explained bump from
  four newly-mapped names — not the runaway noise of the intermediate pass.

**This is the corrected table Task 9's `--apply` ran against.** Per the
brief's own instruction ("the GO decision is made against the table you will
actually apply, not an earlier one"), Tim's earlier GO (given against the
pre-Bridge-fix table) did not carry forward automatically. **Fresh GO/NO-GO
ruling: GO.** Tim's call, given in chat 2026-07-27, against this exact
corrected table (auto-link 55, suggestion 236, ambiguous 121, no-op 313).
Proceeding to Task 9 (`relink.py --apply` on the knight).

---

---

## Task 9 (apply-alignment) — relink APPLY, run 2026-07-27

`relink.py --apply` on the knight, live vault. Same decision table as the
corrected dry-run (auto-link 55, suggestion 236, ambiguous 121, downgrade 0,
no-op 313; 725 total). Output: **"Applied. 412 thread(s) changed / queued."**

- Reconciles exactly against the table run: 55 auto-link + 236 suggestion +
  121 ambiguous = **412** — auto-links get `project_link` set directly;
  suggestion/ambiguous entries get queued as review candidates (human
  decision, not auto-applied); no-op (313) untouched. Confirms the apply
  acted on precisely the table Tim ruled GO on, nothing more, nothing less.
- Evidence winners are now locked (`skipped: evidence` on any future re-run
  for these threads) — re-running `relink.py` will not re-nag already-decided
  threads.

**Task 9 complete.** Proceeding to Task 10 (KNIGHT — verify SQL queries,
`run.py build` / `run.py serve`, golden check, provenance spot-check).

---

---

## Mid-Task-10 finding — seed_aliases regenerated a deliberately-removed alias,
## false-auto-linking 6 threads (found and fixed 2026-07-27)

While doing the golden read-surface check on `l5gn-castle-repo`'s 11 auto-linked
threads, 6 showed evidence resting entirely on a bare `path_mention:Castle(0.9)`
+ `name_alias:Castle@body/title` pair — with **zero other evidence**. The
registry's own curated note said the bare `'Castle'` alias was "DELIBERATELY
REMOVED" (2026-07-25, matches the knight's own hostname
`l5gn-castle-worker` in shell transcripts). Traced the cause to
`build_registry.py`'s `seed_aliases()`: it re-derives a short-name alias from
the canonical name (stripping the `l5gn`/`mcf` prefix token) on **every run**,
regardless of a curated author's deliberate removal — `_merge_alias_lists()`
had no way to honour a removal, only to union curated + seeded. Confirmed
directly on the live generated registry (`/home/l5gn/vault/project_registry.json`):
`l5gn-castle-repo -> ['L5GN-Castle', 'Castle']`, `l5gn-archive-repo ->
['L5GN-Archive', 'Archive']`. Same latent risk on both.

**Fix (commit `b7c2390`):** `_merge_alias_lists()` now takes an optional
`suppress` list; `build_registry.py` reads a new curated field,
`seed_suppress: [...]`, on a repo entry and drops any seeded alias matching it
(normalised comparison), rather than merging it back in. Test coverage added to
`tests/tester_build_registry.py` (3 new assertions: suppression works, curated
aliases alongside a suppressed one survive, comparison is
case/separator-insensitive). `verify.py` GREEN before commit. Curated
`config/project_registry.json` updated with `seed_suppress: ["Castle"]` /
`["Archive"]` on the two repos (gitignored, shipped via `scp`).

**Redo sequence on the knight:**
1. `git pull` (code fix) + `scp` (curated registry fix).
2. Reset the 6 falsely-linked threads: `threads.project_link` /
   `project_confidence` / `link_evidence_ids` / `review_status` cleared to
   NULL — required because `relink.py` treats any `project_confidence='evidence'`
   thread as locked (`skip_evidence`) and never re-scores it; a plain re-run
   alone would not have self-corrected these 6.
3. First cleanup pass, `DELETE FROM link_evidence WHERE detail IN
   ('Castle','Archive')`, missed the persisted `name_alias` rows — those store
   `detail` as `'Castle@title'`/`'Castle@body'` (position suffix baked into the
   string), not bare `'Castle'`. Caught via one surviving thread
   (`451aeb7f...`) still showing `name_alias:Castle@title(0.8)` in the first
   redo dry-run despite the registry itself confirmed already fixed. Corrected
   delete: `WHERE detail IN ('Castle','Archive') OR detail LIKE 'Castle@%' OR
   detail LIKE 'Archive@%'`.
4. `build_registry.py` (registry rebuild, confirmed `l5gn-castle-repo ->
   ['L5GN-Castle']` only) → `extract_path_mentions.py --rescan --apply`
   (`l5gn-archive-repo` no longer appears in the vote table at all — it had
   *zero* genuine path mentions, only the bogus alias; `l5gn-castle-repo`
   dropped from 36 total rows to 15 new votes, matching the legitimate
   `'L5GN-Castle'`-detail count from before the bug was introduced) →
   `relink.py --out data/relink_dryrun.txt`.

**Corrected table:** 725 threads; 676 actively scored + 49 correctly
skipped/locked (the genuine prior auto-links, untouched). auto-link 3,
suggestion 225, ambiguous 115, downgrade 0, no-op 333
(3+225+115+0+333+49=725).

- All 6 reset threads confirmed clean: 4 landed `no-op` (no evidence at all
  once the bogus alias was gone), 2 landed in `ambiguous` on genuine unrelated
  evidence (`deck-backend-ui` vs `crystal-spire`) — none reference Castle.
- Full-table scan: zero bare `'Castle'`/`'Archive'` hits anywhere; every
  remaining Castle-repo match carries the full `'L5GN-Castle'` string.
  `l5gn-archive-repo` does not appear in auto-link or suggestions at all.
- The 3 remaining auto-links (`universal-content-pipeline`/Smelter,
  `sovereign`/Sovereign Architect+Sovereign title, `smelt-gateway`/Smelt+path)
  are all genuine ≥2-origin matches, unrelated to this bug.

**This is now the third dry-run table Tim has been asked to rule on this
round, and materially different from the first two (Task 9's already-applied
55/236/121/0/313 table is now known to have included 6 false positives).**
**Fresh GO/NO-GO ruling: GO.** Tim's call, given in chat 2026-07-27, against
this exact corrected table (3/225/115/0/333, 49 correctly locked). Applied:
**"Applied. 343 thread(s) changed / queued."** — reconciles exactly (3+225+115
= 343). The 6 previously-false-linked threads are corrected as part of this
apply (4 to no-op / cleared, 2 to genuinely-ambiguous review candidates on
unrelated evidence). Task 9 (relink apply) is now complete against the
corrected, seed_suppress-fixed table.

### Task 10 re-verification (walked 2026-07-27, against the corrected apply)

Queries re-run live on the vault via Datasette (`chronicler-serve`):

| check | result | expected | status |
|---|---|---|---|
| `COUNT(*) FROM threads WHERE project_link IS NOT NULL` | 52 | 49 (pre-existing, correctly locked) + 3 (new auto-link) = 52 | match |
| orphan check (`project_link NOT IN projects`) | 0 rows | 0 | match |
| distinct `project_link` values | 14 projects, sums to 52 | -- | consistent |
| `link_ambiguous / pending` | 115 | 115 | exact match |
| `link_upgrade / confirmed` | 52 | 52 | exact match |
| Castle/Archive evidence rows (`detail IN/LIKE`) | 0 rows | 0 | match -- cleanup held |
| duplicate thread_id in `project_link/pending` | 0 rows | 0 | no re-insertion bug |

One open finding: `project_link / pending` = 251, not the 225 the corrected
dry-run predicted. Diagnosed via a date-split query: 10 rows dated
2026-07-26 (the already-known, already-ruled-on pre-session stale rows) +
241 dated 2026-07-27. Of that 241: 225 are the corrected run's live
suggestions; the remaining 16 are leftover rows from the *first*
(contaminated) apply earlier the same day, for threads that were `suggest`
under the bad Castle/Archive evidence but correctly resolved to `no-op`
under the corrected evidence. `clear_pending_relink_rows()` only clears a
thread's queue row when that thread lands in a scored category on the
current run -- a thread landing `no-op` leaves its prior row untouched. No
duplicate thread_ids were found, so this is inert staleness, not a
re-insertion or double-count bug.

**Disposition (Tim, chat 2026-07-27): "Leave for now (recommended)"** --
same call as the original 10, extended to cover all 26 stale
`project_link/pending` rows. Noted for a future dedicated queue-cleanup
pass; does not block closing Task 10.

**Task 10: verified clean.** All structural checks (locked-thread count,
orphan check, ambiguous/confirmed counts, Castle/Archive purge, no
duplicate queue rows) match the corrected, GO'd table. The only variance
(26 stale pending rows) is explained, inert, and left in place per Tim's
call.

---

## Task 11 (deposit/consume + wall check), walked 2026-07-27

**Correction to the run instructions:** `deposit --push` belongs on a
*producer* rig (this rig / any work laptop), never on the knight. The
knight's `config/local.json` is `role: consumer, estate: both` by design,
so it has no `push_target` -- the "no push_target configured" note seen
when this was (mistakenly) run on the knight was expected consumer
behaviour, not an error. No action needed there.

**Real finding, mid-Task-11: vault schema never frozen.** `python3
run.py consume` reported `(vault: schema_mismatch)` and `drift=needs_inputs`
for both estates. Traced through `l5gntools/scanners/{vault_reader,
project_trail}.py`: both gate strictly on `PRAGMA user_version == 1`
(the frozen-schema contract per `chronicler/pipeline/schema_frozen.sql` /
`SCHEMA.md`). Direct query confirmed `PRAGMA user_version` = `0` on the
live vault -- confirmed NOT a stale-deploy issue (`git log` showed the
knight on `b7c2390`, current, clean tree). The vault had simply never had
`chronicler/pipeline/finalize_db.py --apply` (the round-3 "finalize &
freeze" script: P1 leaked-thread-id repair, P2 `'none'`->NULL migration,
P3 `threads.substantive` population, then a schema_version/user_version
stamp) run against it -- `threads.substantive` already existed via a
separate direct migration commit, but the freeze stamp itself was never
applied.

Dry-run (`PYTHONPATH=. python3 chronicler/pipeline/finalize_db.py`, run
from `~/L5GN-Tools`) confirmed this was safe to apply: P1 = 0 invalid
rows, P2 = 0 rows to migrate, P3 recomputed to the *same* 272/453
substantive split already present in the "before" census. The dry-run
census (52 linked/evidence, 115 ambiguous, 52 confirmed, 251
project_link/pending) matched Task 10's verified-clean numbers exactly,
confirming this is the same live database Task 9/10 operated on (just
resolved via a different path than the config example implies -- no
divergent-copy concern).

Applied (`--apply`): backup written
(`chronicler.db.bak-finalize-20260727T160111Z`), before/after census
identical (P1/P2 were no-ops as predicted, P3 re-confirmed existing
values), post-conditions passed (`'none' remaining=0`, `invalid
project_link remaining=0`). Schema stamped `1.0-frozen` / `user_version=1`.
Tim's GO given in chat 2026-07-27 against the dry-run preview before
applying.

**Consume re-run, now unblocked:**
```
consume: swept /home/l5gn/vault/estates  (vault: ok)
  [personal] ingest=ingested verified=True snap=estate-2026-07-25.json | estate_diff=ok
    | drift={'discussed_not_present': 0, 'talked_not_built': 0, 'built_not_discussed': 2}
  [work] ingest=ingested verified=True snap=estate-2026-07-25.json | estate_diff=ok
    | drift={'discussed_not_present': 0, 'talked_not_built': 0, 'built_not_discussed': 4}
```

**Wall check: held.** `personal` and `work` land in separately-namespaced
directories under `/home/l5gn/vault/estates/`, each ingested and manifest-
verified (`verified=True`) independently -- the namespace-enforcement
guard in `deposit.py` (a rig may only deposit into its own declared
estate) is intact. `discussed_not_present=0` and `talked_not_built=0` on
both sides; `built_not_discussed` (2 personal / 4 work) is ordinary
recent-commits-without-linked-chat drift, not a gap of concern.

**Task 11: complete.** Wall verified intact; the vault-freeze gap found
along the way is fixed (safely, zero data change, backed up, verified
before/after) rather than deferred.

---

---

## Task 10 (apply-alignment) — verify alignment landed clean, walked 2026-07-27

> **SUPERSEDED — this section documents the FIRST, contaminated apply
> (412 changed/queued, 55 auto-links).** Mid-verification, the
> `l5gn-castle-repo` "11 threads" and "246 project_link/pending" numbers
> below led to discovering the seed_suppress registry-generator defect
> (see "Mid-Task-10 finding" above this section in file order, though it
> was discovered chronologically *after* this section was first written).
> A full clean redo followed: registry fix, S5 rescan, tainted-thread
> reset, fresh dry-run, fresh GO, re-apply (343 changed/queued, 3
> auto-links). **The corrected, final Task 10 verification is "Task 10
> re-verification (walked 2026-07-27, against the corrected apply)"
> above.** This section is kept, unedited, as the honest record of what
> was actually run and seen at the time — not deleted or quietly
> corrected in place — per the standing rule against laundering a
> superseded count into looking current. Do not cite the numbers below
> (55 auto-links, 11 castle threads, 246 pending) as the final state.

Run on the knight against the live vault (`/home/l5gn/vault/chronicler.db`).

- **`threads.project_link` resolution.** `SELECT COUNT(*) FROM threads WHERE
  project_link IS NOT NULL` = 55, matching the auto-link count exactly (only
  auto-links write `threads.project_link` directly; suggestion/ambiguous land
  in `review_queue` instead). `SELECT DISTINCT project_link ...` = 14 values,
  all confirmed by hand against `config/project_registry.json`: every one a
  real id (project or repo tier) — `chronicler-repo`, `citadel-microide`,
  `crystal-spire`, `desktopsanddungeons-repo`, `l5gn-armory-v4`,
  `l5gn-bridge-repo`, `l5gn-castle-repo`,
  `l5gn-continuous-ingestion-daemon-repo`, `l5gn-crystal-spire`,
  `l5gn-mesh-network`, `smelt-gateway`, `sovereign`,
  `universal-content-pipeline`, `vertex-3`. **No legacy title-case or
  folder-name string found.**
- **DB-native orphan check** (stronger than the manual registry-file
  comparison above): `SELECT project_link, COUNT(*) FROM threads WHERE
  project_link IS NOT NULL AND project_link NOT IN (SELECT project_id FROM
  projects) GROUP BY 1` — **0 results.** Every linked project_link resolves
  against the vault's own `projects` table, not just the source registry
  file.
- **Thread-count-per-project plausibility:** top count `l5gn-castle-repo` at
  11, all others ≤7. Nothing implausible (no single project absorbing a
  disproportionate share). `l5gn-castle-repo` flagged for extra scrutiny in
  the golden read since its registry note documents a past false-positive
  class (bare `Castle` alias matching the knight's own hostname in shell
  transcripts) — the bare alias was already removed from the registry before
  this run, so these 11 should rest on other evidence, confirmed at the
  golden read below.
- **`run.py build`** succeeded — `data/estate.json` + `report.html` written,
  5 projects scanned (resume mode).
- **`run.py serve`** required activating the knight's `.venv`
  (`shutil.which("datasette")` looks on `$PATH`, and `.venv/bin` isn't on it
  unless activated — not a real defect, just an environment step). Once
  activated, served the read-only immutable snapshot correctly.
- **`review_queue` breakdown** (`SELECT type, status, COUNT(*) ... GROUP BY
  type, status`): `link_upgrade/confirmed` = 55 (matches auto-link exactly),
  `link_ambiguous/pending` = 121 (matches ambiguous exactly),
  `project_link/pending` = **246**, ten more than the 236 expected from
  today's suggestion count. `close_suggestion`, `thread_grouping`,
  `reconciliation_*` rows (557+502+40+39+5=1143) are a separate subsystem
  (dedup/reconciliation), unrelated to today's relink apply — not
  investigated further here, out of scope for S6.
- **Diagnosed the 246-vs-236 gap:** `SELECT date(created_at), COUNT(*) FROM
  review_queue WHERE type='project_link' AND status='pending' GROUP BY 1` →
  **10 rows dated 2026-07-26** (before this session), **236 rows dated
  2026-07-27** (today, exact match). Root cause: `relink.py`'s
  `apply_decision()` only calls `clear_pending_relink_rows()` for threads
  landing in `auto_link`/`suggest`/`ambiguous`/`downgrade` **this run**; a
  thread that scored `no-op` this run (e.g. because the `low_signal_body`
  fix lowered its score below suggestion threshold) is never touched, so a
  stale pending row from a prior round survives. Precondition 3's
  clean-identity-base check verified `link_evidence` and
  `threads.project_link` were empty but did not check `review_queue` — the
  gap in coverage that let these 10 rows through. **Not a correctness bug in
  today's apply** (proven clean above: 412 = 55+236+121 exactly) — pre-
  existing queue noise from before this session.
- **Tim's ruling on the 10 stale rows: leave for now.** Harmless — will be
  naturally confirmed/rejected during ordinary manual review same as any
  other pending row. No DB write made.

**Golden read-surface check:** Datasette live at the knight
(`100.124.152.18:8001`), `threads` table sorted/filtered by `project_link`.
[Tim's read of `l5gn-castle-repo` and other auto-links, plus the provenance
spot-check, pending below.] **This is the read that found the seed_suppress
defect** — see "Mid-Task-10 finding" above. The corrected golden read
(post-fix) is folded into the "Task 10 re-verification" section's
distinct-`project_link` breakdown (`l5gn-castle-repo` = 5, no bare
Castle/Archive evidence remaining).

---

## Walk-sheet cross-reference (`docs/UAT_apply_alignment.md`), 2026-07-27

Every item below is evidenced by a specific section of this log. Marked
**walked** where Tim has ruled on it in chat; marked **evidenced,
code/data-confirmed** where the log demonstrates it but no separate verbal
ruling was needed beyond the section's own GO; marked **deferred** where
explicitly not closed this session.

| Item | Status | Evidence |
|---|---|---|
| P1–P5 (preconditions) | **walked** | "Hard preconditions" table above; P2 noted MET-structure-confirmed with the re-run itself landing in Task 1 |
| T0.1–T0.2 (backup, irreplaceables) | **walked** | Precondition 5's evidence row (same table) |
| T1.1–T1.2 (re-derive live, id-keyed) | **walked** | "Task 1 (apply-alignment) — re-derive evidence LIVE" |
| T2.1–T2.5 (dry-run GO/NO-GO) | **walked** | "Task 2" (first pass) + "Task 8" re-runs; final GO given against the corrected 3/225/115/0/333 table, not a stale one — see "Fresh GO/NO-GO ruling: GO" |
| T3.1–T3.2 (apply on GO only) | **walked** | "Task 9" (412, superseded) and the corrected apply (343, reconciles 3+225+115) recorded under the GO ruling |
| T4.1–T4.5 (verify landed clean) | **walked** | "Task 10 re-verification" — orphan check 0, review_queue counts exact match (115/52), stale-row gap diagnosed and explained, not dismissed |
| F1–F4 (seed_suppress finding) | **walked** | "Mid-Task-10 finding" section in full: root cause traced in code, fix shipped with `tester_build_registry` coverage, all 6 tainted threads identified by direct evidence cross-reference and confirmed clean post-redo, full clean redo (not a patch) |
| T5.1–T5.4 (deposit/consume, wall) | **walked** | "Task 11" section: deposit-on-knight correction, schema_mismatch root-caused to an unrun `finalize_db.py` freeze (pre-existing, unrelated to this round's code), fixed safely (0-row P1/P2, dry-run-verified before apply), consume re-run `vault: ok`, wall confirmed via independent per-estate `verified=True` |
| Golden | **walked** | Corrected distinct-`project_link` breakdown (Task 10 re-verification, item 3) |
| Provenance | **evidenced, code-confirmed** | The 6 tainted threads' evidence rows were inspected directly (2 Castle-derived rows each, nothing else) before reset — the provenance check that *caught* the defect. A broader spot-check of the 3 new auto-links' own evidence beyond the tainted-thread investigation was not separately walked this session. |
| No over-count | **walked (inherited)** | `MIN_AUTOLINK_ORIGINS = 2` is `relink_scoring`'s fix, already UAT-walked in that round; this round's dry-run tables did not surface a regression |
| Identity | **walked** | T4.1–T4.2 |
| Wall | **walked** | T5.3 |
| No laundering | **walked** | This log documents the contaminated first pass in place (superseded, not deleted) and the corrected second pass separately, per the notice at the top of the old "Task 10" section |

**Overall ruling: apply alignment is closed for this round.** The golden
apply landed on the corrected, seed_suppress-fixed registry; verification
is clean; the deposit/consume wall held; a pre-existing vault-freeze gap
found along the way is fixed. Work-estate (MCF) threads remain
deliberately unaligned (no full export) — expected, not a gap.

---
