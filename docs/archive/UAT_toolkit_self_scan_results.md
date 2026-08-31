<!-- uat: commit=a202ba0 dirty=false host=LucasGoonPC walked=2026-08-01 -->
<!-- gate-frozen: commit=a202ba0 -->
<!-- This is a results log: §"Gate state" records what `verify.py` PRINTED on
     2026-08-01 at the commit in the uat stamp above. Editing 53 to 54 would
     falsify an observation, which is the one thing a results log exists to
     prevent. Frozen instead, per docs/README.md §3. -->

<!-- Sections A-C were walked 2026-07-29 against a dirty tree at ac7710d/6dd70f1
     and are carried here as recorded, not re-derived. Sections D-F and the stop
     conditions were walked 2026-08-01 against a clean a202ba0 after a
     `run.py build --fresh`, so every D/E figure below is the 2026-08-01
     artefact, not the one the brief and report were written against.
     gate= omitted per the disposition in docs/UAT_solo_playbook_results.md. -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_toolkit_self_scan.md` + `COWORK_REPORT_toolkit_self_scan.md`, walked 2026-08-01
> Superseded by `L5GN-Tools` now being scanned as a normal project (`is_project: true` in the machine config) · Original purpose: close **0020**'s own noted gap — the toolkit could not see its own write-and-execute-heavy code.
> **Asserts the round was tested**, walked 2026-08-01. **Stop trusting** any gate count quoted inside it — the live gate is **12 auditors + 81 testers**.

# Results log — the toolkit sees itself (`LucasGoonPC`, walked 2026-07-29 / 2026-08-01)

Partner to `docs/UAT_toolkit_self_scan.md`. Report:
`docs/COWORK_REPORT_toolkit_self_scan.md`.

Evidence, not acceptance beyond what is stated. Machine: `LucasGoonPC`, repo at
`C:\Users\timps\Documents\GitHub\L5GN-Tools`, `CHRONICLER_HOME` pointed at the
throwaway dev vault `C:\Users\timps\Documents\chronicler_dev`. No `--apply`, no
`relink.py`, nothing committed, nothing pushed.

---

## Headline

**Walked to completion. The toolkit can see itself, and what it sees is broadly
accurate.** The registry collision predicted at C5 is closed, the linking payoff
is real and was measured, and the disclosure check found no leaked configuration
content.

Three things the walk-sheet got wrong, all found by walking it:

1. **F0 names the wrong path.** The generated registry does not live under
   `Documents\GitHub\L5GN\`. It followed `CHRONICLER_HOME` to
   `C:\Users\timps\L5GN\.intel_sync\project_registry.json`.
2. **F3 tests the wrong thing.** `verify.py`, `relink.py`, `DECISIONS.md` and
   `SOLO_PLAYBOOK.md` are all in the basename index — three of them sole-owned —
   and none of them matched, because `xref_filenames` votes on *attachments*, not
   on inventory membership.
3. **D1 and D5 are written more absolutely than the data supports**, in both
   cases because the sheet did not anticipate the channel (git history for D1,
   `outliers[]` for D5).

One new disclosure item was opened that the sheet did not contemplate at all:
the work rig's hostname reaching the estate bundle through authored prose.

---

## Gate state

`python verify.py` on 2026-08-01: **GREEN**, **6 auditors + 53 testers**, exactly
the count the walk-sheet predicted. `tester_project_root` present and OK.
`auditor_stdlib` OK, which is the half of E8 that needed a live gate.

The artefact walked for D-F is `data/estate.json`,
`generated_at 2026-08-01T09:19:23+01:00`, `toolkit_commit a202ba0`,
`toolkit_dirty false`, `producer_host LucasGoonPC`, 9 projects. It was produced
by `python run.py build --fresh`, which also regenerated `report.html`,
`data/estate_status.json` and `data/duplicate_finder.json`.

---

## A / B / C — carried from 2026-07-29

Recorded as walked on 2026-07-29; not re-derived on 2026-08-01 except where the
`--fresh` rebuild touched them.

- **A1-A5** passed as recorded. Both roots present, 9 projects, no mis-scoped
  sibling, work rig and knight untouched.
- **B1-B3** passed as recorded. The repo-tier diff was applied to
  `config/project_registry.json` on 2026-07-29 *after* the C5 collision fired;
  `l5gn-tools` retains `low_signal_body: true`.
- **C1 / C1a** passed. The unkeyed estate-cache defect was real and is written up
  in the report. Confirmed still correct on 2026-08-01:
  `estate_status.project_count` is **9** with an `L5GN-Tools` row.
- **C2 / C3** passed, with the numbers moved by two commits of work:
  `working_set` is now **253 files** (was 246), `total_files` **37,450** (was
  37,396). Both remain in the predicted shape — the ~37k figure is the real
  `.venv` being counted, as expected.
- **C4** deposit staged 2026-07-29T00:10:56, 9 projects. **Not refreshed on
  2026-08-01** — see "What was deliberately not done".
- **C5 re-run: PASS.** Exactly one `l5gn-tools`, `provenance: manual`, repo
  `l5gn-tools-repo` **present**, `first_seen=2026-07-10`. No `provenance: auto`
  twin, no `duplicate registry id` abort. B2 closed the collision.
- **C6: PASS.** Bare `Tools` appears as a live alias nowhere in the full
  `--report-aliases` dump. `L5GN-Tools` and `L5GN Tools` both present, on the
  project and the repo. `seed_suppress: ["Tools"]` on the repo did its job.

---

## D — the disclosure check

**D1 — filename only, but not "nowhere else". Expectation corrected.**
`project_registry.json` occurs exactly once, in `env_scanner.config_files`.
`local.json` occurs there too, and *additionally* in `file_census.files[]` as
`config/local.json.example` (tracked, explicitly allowed by D3) and in **three
`git_deep_history` commit subjects**. Filenames only; no contents in any case.
The sheet's "and nowhere else" did not anticipate commit subjects as a channel.

**D2 — no configuration content leaked. One sub-clause fails for an unrelated
reason.** `secret_suspects: []`, `credential_files: []`,
`tracked_suspect_count: 0`. The literal `push_target` value
(`l5gn-castle:vault/estates`) does **not** appear anywhere in `estate.json`. No
value from `config/local.json` or `config/project_registry.json` was ingested.

But the sub-clause "no hostname beyond the producer host" **fails**: `10280L`
appears in two `doc_census` doc titles and one commit subject.
`l5gn-castle-worker` does not appear. This is not scanner scope leakage — it is
authored prose naming the work rig, which the scanner then faithfully indexes.
Spun out as its own item (see Findings F-2).

**D3 — PASS.** All 253 entries in `file_census.files[]` passed through
`git check-ignore`: **zero** ignored. `config/local.json.example` confirmed
tracked.

**D4 / D5 — RULED: accept as disclosure by design.** `outliers[]` holds 20
entries, **all 20 gitignored**, 12 of them full `.venv/…` paths headed by
`torch_cpu.dll` at 305 MB. Tim's ruling: naming the large ignored file is the
purpose of an outlier list, and the disclosure is intentional. D5's literal
wording ("no `.venv/` path in **any** per-file list") is therefore wrong and is
superseded by this ruling; D5's *intent* — that `files[]` stays clean — holds and
is confirmed by D3.

Two corrections to the report while ruling on this: `outliers[]` does **not**
name `report.html`. At 2.20 MB it falls below the 20-entry cutoff, whose smallest
member is 2.90 MB. It names `data/estate.json` and `chronicler/chronicler.db` as
the report claims.

**D6 — RULED: accept as a recorded finding, not a deposit blocker.** The count is
**198**, not the 185 in the report: **193 under `data/`**, 4 under `config/`, 1
`pyproject.toml`. Every one of the 193 is a gitignored scanner output being
classified as a config file. The rise over 185 is the C1a rebuild adding estate
caches. Does not block depositing the toolkit; goes to a later brief.

---

## E — what it says about itself

**E1 — PASS.** `tier: raw-write`, `tier_rank 3`, `hit_count 272`, `by_family`
dominated by `db-writes 204` (then `shell-os 48`, `salesforce-dml 13`, rest
single digits). All five files named in the sheet are present and among the top
hits: `group_fallback.py` 15, `relink.py` 14, `review/core.py` 8,
`pull-report.ps1` 8, `finalize_db.py` 7. The dangerous operations are the ones
flagged — the `DELETE FROM` / `INSERT INTO` / `.commit` triples in
`build_vocabulary.py`, `bulk_review.py` and `backfill_candidate_project.py` are
all caught. **Nothing important is missing.**

Two observations recorded while confirming:

- only **33 of 272 hits are `guarded`**;
- `tests/tester_review.py` (15) and `tests/tester_blast_radius.py` (14) are among
  the highest-hit files in the whole project — the scanner is scoring its own
  test fixtures, the same reflexivity E5 records for markers;
- `hit_cap` is **300** against a count of 272. `truncated` is `false` today, with
  28 of headroom.

**E2 — RULED: a saturated tier ladder is acceptable for now.** Confirmed: all
nine projects read `raw-write` / rank 3. Separation is purely `hit_count` —
**272 vs 29** (Castle), then 22, 14, 14, 12, 8, 3, 3. Tim's ruling: acceptable,
and the work-laptop estate will be scanned as a cross-check to widen the sample
before deciding whether the ladder needs more rungs.

**E3 — reproduced 2026-07-29; root cause identified; not observable on
2026-08-01.** On the 29 Jul artefact `uncommitted_critical` held
`l5gntools/common.py` with `git_state: "untracked"`, while `git ls-files`
confirmed the file **tracked**. On the current clean tree
`uncommitted_critical` is `[]`, so the artefact no longer demonstrates it.

The defect is in `l5gntools/scanners/blast_radius.py:205-209`. Line 205 filters
to `uncommitted = (changed is None) or (p in changed)` and `continue`s otherwise;
line 208-209 then re-tests the same condition,
`"untracked" if p in changed else "dirty"`. At that point `p in changed` is
always true, so the `"dirty"` branch is structurally unreachable and every
tracked-and-modified file is labelled `"untracked"`. Left as-is; the fix is out
of scope for this walk.

**E4 — PASS, exactly.** `decisions_count 28`, `adr_count 0`, and `DECISIONS.md`
carries 28 headings `## 0001` … `## 0028` with no gaps. `decision_tiers` now
reads **`{accepted: 28}`** — the `{accepted: 27, other: 1}` recorded in the
report resolved between the two builds. Note these fields live in
`todo_adr_scanner`, not `doc_census`, which the sheet's wording implies.

**E5 — RULED: mark for later follow-up.** `marker_count` is **33**, not the 28 in
the report, `{TODO: 31, XXX: 1, FIXME: 1}`. The reflexivity is more extreme than
the report claimed: **exactly one marker is a genuine actionable TODO** —
`chronicler/scrape_gemini_share.py:104`, "normalize to ISO 8601 UTC". The other
32 are the scanner's own regex and docstrings (4), its testers' fixture strings
(6), `l5gntools/report.py`'s UI heading "TODO / ADR / Decisions" (1), and
documentation *about* markers (21), now including the self-scan report itself (5).
So **32 of 33 reflexive**, against the report's "~26 of 28". No disposition yet.

**E6 — RULED: ratified, with a Live/Archived split as follow-up.** `doc_count`
**106**, `authored_count` **105**, `classified_pct` **87.6**. `docs/archive` (45)
and `docs/investigation` (5) are counted; top-level `docs/` is 56.

Tim's ruling: counting them is correct and stays, but `doc_census` should report
the split rather than a single total — **Live 56** (not archive, not
investigation) and **Archived 50** (archive + investigation). The rationale is
that the two numbers answer different questions: the archive describes the full
body of work, the live count describes how much is in flight. Recorded as a
follow-up brief, not a change made here.

**E7 — RULED: switch to `authored_count` and trial it.** Confirmed as the sheet
describes, with the toolkit's count updated: median **27**, threshold **81.0**,
flagged 4 of 9 — CID 358, Armory_v4 288, **L5GN-Tools 106**, Crystal-Spire 97.

Modelled on this estate, the switch **reorders the population** rather than
merely rescaling it:

```
A) doc_count (today)   median 27   threshold 81   flagged 4/9
     CID 358 | Armory_v4 288 | L5GN-Tools 106 | Crystal-Spire 97
B) authored_count      median  6   threshold 18   flagged 3/9
     L5GN-Tools 105 | Crystal-Spire 44 | Castle 19
```

CID drops out (358 docs but only **17 authored** — 341 are generated) and so does
Armory_v4 (288 docs, **2 authored**); Castle enters. The metric becomes a measure
of human documentation effort rather than generator sprawl, which is the
intended discrimination.

**Recorded for the brief:** the switch does *not* get the toolkit out of
`out_of_band` — at 105 against a threshold of 18 it becomes the most extreme
outlier in the estate, 5.8x over. The E6 Live/Archived split is the change that
would (Live 56 is under the current 81 threshold). **The two follow-ups pull in
opposite directions and must be designed together, not separately.**

**E8 — PASS.** `import_scanner.third_party` lists **27** names, of which exactly
**6** are genuinely third-party: `yaml`, `playwright`, `sentence_transformers`,
`uvicorn`, `fastapi`, `pydantic`. The other 21 are `chronicler/pipeline` siblings
imported by bare name, led by `db` at 27 occurrences. `auditor_stdlib` is **OK**
in the same run — the wall is intact and the scanner is wrong, exactly as the
report argues.

**E9 — PASS.** `bloat_audit`: 253 tracked files, `tracked_bloat_paths 0`,
`large_tracked_files []`, `flags []`. `env_scanner` reports no committed secret.
`git_deep_history`: `total_commits 78` (was 76 at the report), `commits_by_author
{"L5GN": 78}`, `author_aliasing {"timpsmith28-hash": "L5GN"}` — folds cleanly.

---

## F — the linking payoff

**F0 — the file now exists, at a different path than the sheet states.**
`python chronicler\pipeline\build_registry.py` (no `--report-aliases`) wrote
**31 entries** to **`C:\Users\timps\L5GN\.intel_sync\project_registry.json`**.
`Documents\GitHub\L5GN\.intel_sync\` does not exist and was never written.

Cause identified: `CHRONICLER_HOME=C:\Users\timps\Documents\chronicler_dev`.
`db.resolve_registry_path()` derives `CHRONICLER_ROOT.parent.parent / "L5GN" /
".intel_sync"`, so `Documents\chronicler_dev` → `C:\Users\timps` →
`C:\Users\timps\L5GN\.intel_sync`. Writer and readers still agree — that is what
`tester_registry_path` guarantees, and it is green — so this is not a
correctness failure. It is a coupling finding: a knob documented as a *DB
location* escape hatch also relocates the *canonical join file*. See Findings
F-1.

31 project entries reconciles against the curated layer: 9 + 10 + 2 + 2 + 8
across the four programs and standalone.

**F1 — PASS, exactly on prediction.** `python chronicler\pipeline\build_inventory.py`
reported `L5GN-Tools 246 / 246 / +0`. From the written registry,
`l5gn-tools-repo.file_inventory` carries `file_count 246`, 246 `paths`,
`truncated false`, `extra_basenames 0`, `source: deposit`,
`source_commit ac7710d`, and **237 distinct basenames** — the sheet predicted
"246 and ~237".

The arithmetic reconciles: only two basenames repeat, `__init__.py` x6 and
`README.md` x5, giving 5 + 4 = 9 collisions, 246 − 9 = **237**. Nine repos
received inventories in total. Scan scope did not move.

**F2 — PASS, dry-run, and the "structurally zero" claim is now proven.**
Baseline before the run: `link_evidence` **165 rows, all `name_alias`**, and
**zero `filename_xref` rows for any project**. So the count was not merely low,
it was structurally zero, as the sheet asserted.

`python chronicler\pipeline\xref_filenames.py` (default dry-run, `--apply` is
`store_true` and was not passed) produced **2,018 evidence rows across 308
threads**, of which `l5gn-tools-repo` receives **31 — 6 `unique(1.0)` and 25
`multi(<1)`**. All 31 were impossible before this walk. Closing line confirmed:
`(dry-run - nothing written. Re-run with --apply to persist.)`. The run also
reports excluding **262 export-artifact basenames** from the project-owned index
(fix C).

The 31 rows come from **9 distinct basenames**:

| basename | weight | owners |
|---|---|---|
| `docs/archive/chronicler_investigation_2026-07-18.md` | 1.0 | 1 |
| `docs/archive/chronicler_system_design.md` | 1.0 | 1 |
| `chronicler/CLOSEOUT_PROMPT.md` | 1.0 | 1 |
| `docs/archive/COWORK_BRIEF_build_round_2.md` | 1.0 | 1 |
| `docs/archive/COWORK_ROUND_2_REPORT.md` | 1.0 | 1 |
| `docs/archive/cowork_tasks_cleanup_and_qol.md` | 1.0 | 1 |
| `parse_gemini_export.py` | 0.5 | 2 |
| `registry.py` | 0.3333 | 3 |
| `workspace_scanner.py` | 0.1667 | 6 |

Every unique hit is a document that was physically uploaded into a session. The
shared ones degrade by owner count as designed.

**F3 — the prediction is wrong; the scanner is right.** None of `verify.py`,
`relink.py`, `DECISIONS.md` or `SOLO_PLAYBOOK.md` are among the matched
basenames. Corrected for the index's lowercasing, all four **are** in the index,
three of them sole-owned by `l5gn-tools-repo`:

```
verify.py         owners = [cid-repo, l5gn-tools-repo]   would vote 0.5
relink.py         owners = [l5gn-tools-repo]             would vote 1.0
DECISIONS.md      owners = [l5gn-tools-repo]             would vote 1.0
SOLO_PLAYBOOK.md  owners = [l5gn-tools-repo]             would vote 1.0
run.py            owners = [l5gn-tools-repo]             SUPPRESSED
```

They did not match because **no thread ever attached a file with those
basenames**. `xref_filenames` votes on rows in `attachments`, not on inventory
membership or on mentions in message text. F3 conflated the two. The signal
behaved correctly; the walk-sheet's expectation was built on the wrong model of
what the scanner does.

`run.py` is **not** matched, as F3 predicts — but the reason is worth recording.
It is in `GENERIC_BASENAMES`, a hardcoded denylist, while on this estate it is
**sole-owned by `l5gn-tools-repo`** and therefore completely unambiguous. The
denylist is estate-blind. See Findings F-3.

**F4 — PASS.** After F2 and F3, `link_evidence` still reads **165 rows, all
`name_alias`, `filename_xref` `(none)`**. No `--apply` ran. `relink.py` was never
invoked. Row count unchanged from before the walk.

**F5 — recorded.** From the 2026-08-01 `--fresh` rebuild with 9 projects:
`identical_content_groups` **25** (baseline 25 — unchanged),
`shared_filename_groups` **41** (baseline 39 — **+2**),
`shared_filename_divergent` 29.

The rise is modest rather than a jump. L5GN-Tools appears in **zero**
identical-content groups — it shares no byte-identical file with any other
project — and in **4** shared-filename groups, all `content: divergent`:

| filename | projects |
|---|---|
| `workspace_scanner.py` | Archive, Armory, Armory_v2, Castle, **Tools**, Armory_v4 |
| `registry.py` | Castle, **Tools**, Armory_v4 |
| `verify.py` | CID, **Tools** |
| `parse_gemini_export.py` | **Tools**, Armory_v4 |

These are the same basenames `xref_filenames` degraded by owner count, which is a
useful cross-validation: the two scanners agree on which names are shared and on
how widely. `verify.py` appears here but produced no xref vote, consistent with
F3 — shared name, never attached.

---

## Stop conditions

- **S1 — PASS.** Exactly one `l5gn-tools` project id and one `l5gn-tools-repo`
  repo id in the written registry. 31 ids, no duplicates at either tier.
- **S2 — PASS.** No gitignored path in scan output other than the known
  `env_scanner` case (D1/D6) and the labelled `file_census` `mass[]` / `outliers[]`
  (D3/D4, ruled disclosure by design).
- **S3 — PASS.** 9 projects, exactly the expected set. No `L5GN`, no
  `l5gn-mesh-vertex-3_prod`, nothing called `docs`, `config` or `l5gntools`.
- **S4 — PASS.** Nothing committed (`git status` clean at `a202ba0`), nothing
  applied, no link changed (`link_evidence` 165, unchanged). The only writes
  outside the repo were the generated registry at F0 and the nine
  `file_inventory` blocks at F1, both of which the walk-sheet requires.

---

## Findings opened by this walk

| id | finding | disposition |
|---|---|---|
| **F-1** | `CHRONICLER_HOME` relocates the shared `project_registry.json`, not just the DB. Documented as a DB escape hatch; actually moves the canonical join file to `<HOME>/../../L5GN/.intel_sync/`. | Record. Not a correctness bug — all consumers resolve through one function and `tester_registry_path` is green — but the coupling is undocumented and surprising. |
| **F-2** | Work rig hostname `10280L` reaches the estate bundle through authored doc titles and a commit subject, not through config scope. | **Own item.** Near-term mitigation: substitute rig aliases (`work rig` / `game rig` / `knight`) in authored prose. Hard to police — neither doc titles nor commit subjects are scanner-controlled, and commit subjects are immutable once written. |
| **F-3** | `GENERIC_BASENAMES` is estate-blind. `run.py` is sole-owned by `l5gn-tools-repo` across the whole estate yet is suppressed unconditionally, costing a weight-1.0 signal. | Follow-up brief: suppress on *observed* owner count rather than a hardcoded denylist. |
| **F-4** | `env_scanner.config_files` classifies 193 gitignored `data/` scanner outputs as configuration. | Accepted as a recorded finding (D6). Later brief. |
| **F-5** | `blast_radius` labels every tracked-and-modified critical file `"untracked"`; the `"dirty"` branch is unreachable. `blast_radius.py:205-209`. | Recorded (E3). Fix out of scope here. |
| **F-6** | 32 of 33 TODO/FIXME markers are reflexive — the scanner's own regex, its fixtures, and docs about markers. | Deferred (E5). No disposition yet. |
| **F-7** | `import_scanner.third_party` reports 27 names of which 6 are third-party; the rest are bare-name sibling imports. | Recorded (E8). Scanner is wrong, wall is intact. |
| **F-8** | Two Claude project names matched nothing in any deposit: `'How to use Claude'` and `'L5GN Tools Mobile'`. The latter looks like it belongs to `l5gn-tools`. | Needs an alias decision. |
| **F-9** | `blast_radius.hit_cap` is 300 against a live count of 272 for L5GN-Tools. | Watch. 28 of headroom before the project's own hits truncate. |

## Follow-up briefs proposed

1. **`doc_census` Live/Archived split** (E6) — report Live 56 / Archived 50
   instead of a single 106. Archive size describes the body of work; live size
   describes what is in flight.
2. **`out_of_band` scores `authored_count`** (E7) — trial it. **Must be designed
   alongside (1)**: the split would drop the toolkit out of the flag, the
   `authored_count` switch would make it the most extreme member. Together they
   need one coherent definition of what the flag is for.
3. **Estate-aware basename suppression** (F-3).
4. **Rig-alias substitution in authored prose** (F-2).
5. **Cross-check the tier ladder against the work estate** (E2) — scan
   `10280L` and re-examine whether `raw-write` saturation is a property of this
   estate or of the scanner.

## What was deliberately not done

- **No `--apply` on `xref_filenames`.** The 2,018 rows, including the toolkit's
  31, remain uncommitted evidence.
- **`relink.py` was never invoked.**
- **The deposit was not refreshed.** `build_registry` and `build_inventory` read
  the 2026-07-29T00:10:56 deposit (246 files), not the 2026-08-01 `--fresh`
  build (253 files). Chosen deliberately so F1's 246 / 237 prediction stayed a
  live test rather than a moving target. **A re-deposit is the natural next
  action** and will move the inventory to 253.
- **The `work` estate is absent.** All ten `mcf-*` projects have no deposit, so
  F2's cross-reference saw only the personal half of the estate.
- **Nothing was committed or pushed.**

Two throwaway read-only helper scripts were written to the gitignored `data/`
directory during F2-F4 (`_uat_link_evidence.py`, `_uat_f3_basenames.py`) to read
`link_evidence` counts and the matched basenames the summary table hides. Both
open the DB `mode=ro` and neither reaches `write_evidence()`. Delete when done.
