# Cowork report — projects reconciliation: one identity per project

**Date:** 2026-07-21 · **Pairs with:** `COWORK_BRIEF_projects_reconciliation.md`
**Gate:** `python verify.py` — **GREEN** (6 auditors, 24 testers), before and after.
**Nothing committed.** Everything staged for Tim's review.

**Evidence base.** The session had no route to the knight (no DNS for
`l5gn-castle`, no keys). Rather than reason from the brief's figures, a read-only
collection runbook (`docs/RUNBOOK_collect_reconciliation_evidence.md`) was written
and **Tim ran it on the knight**; the bundle
(`reconcile_evidence_20260721T105006Z.txt`, 3,066 lines, host
`l5gn-castle-worker`, `git=1f260ed dirty=true`) is the source for every number
below. Nothing here is simulated. Where a claim could not be proved from that
bundle it is marked **UNPROVEN** and the query that would settle it is given.

---

## Done vs pending

| Task | State | Note |
|---|---|---|
| A — the definitive project list | **done** | table below; `config/project_registry.json` rewritten, 28 → 52 link targets |
| B — the reset, counted | **done** | 270 rows updated, 9 rows deleted, **13 manual rulings lost** |
| F — does `collapse_lineage` fire? | **done** | answered: it fires, but on a hierarchy that is empty on the knight; the UI was never running it |
| G — registry path derivation | **done** | answered: **relink and the review endpoint read two different files today** |
| C — execute the reset | **runbook only** | no knight access; exact statements below, unrun |
| D — foreign-row invariant | **not built** | scope agreed as "A and B, done properly"; and see §Finding 3 — the invariant as briefed would be a permanent block, not a guard |
| E — id-remap guard | **not built** | same; the new registry was authored to *satisfy* its rule (zero id remaps) so the guard has a clean baseline when built |

---

## Three findings that change the brief

The brief's diagnosis is right about the disease. The bundle shows the cause is
one layer deeper, and that the reset as specified will not hold.

### Finding 1 — the knight has never had a three-tier registry

`config/project_registry.json` is gitignored and ships by scp. **That scp never
happened after round 3.** The knight's curated seed is still the round-2 flat
file, and the proof is in its own output:

```
curated_source: /home/l5gn/L5GN-Tools/config/project_registry.json
programs: []                      <- the rig's seed has two
```

Every entry in the knight's generated registry carries `"group": "L5GN"|"MCF"` —
the round-2 field — and none carries `program`. `citadel-microide`,
`l5gn-os-program` and `sovereign` do not exist there at all; `l5gn-os` is still a
*project*; `vertex-3` is still a *project*. Every `low_signal_body` is `false`,
including on `l5gn-os`, so the D.4 flags the round-3 report showed working have
never been live.

So round 3's Task D was built, tested and reported — and then not deployed. Everything
downstream of it on the knight has been running on round-2 data.

**The guard that should have caught this did not, and the reason is a one-word bug.**
`relink.load_registry` refuses a flat registry with:

```python
if "programs" not in registry:      # relink.py:168
    raise SystemExit(...)
```

`build_registry` always *emits* a `programs` key — empty when the seed has no
programs. So the check tests for the key, not for content, and a registry with
`"programs": []` sails through the guard written to stop exactly it. One
character fixes it: `if not registry.get("programs")`.

### Finding 2 — the rename in the docs is the wrong rename

Round-3 D.3 and the brief both cite `L5GN-Armory` → `smelt-gateway` as "a rename
this estate has performed". The deposited git facts disagree:

| Repo | Estate | First commit | Latest | Commits |
|---|---|---|---|---|
| `L5GN-Castle` | personal | 2026-05-29T12:04:58+01:00 | 2026-06-04T11:48:34+01:00 | 12 |
| `smelt-gateway` | work | **2026-05-29T12:04:58+01:00** | **2026-06-04T11:48:34+01:00** | **12** |
| `L5GN-Armory` | personal | 2026-06-13T10:54:25+01:00 | 2026-06-14T21:38:23+01:00 | 6 |

`smelt-gateway` and `L5GN-Castle` share a first commit to the second, a last
commit to the second, and a commit count. `L5GN-Armory` shares none of it and
starts two weeks later. On the evidence, **`smelt-gateway` is an incarnation of
`L5GN-Castle`, not of `L5GN-Armory`** — and 117 threads, the largest single
cluster in the vault, hang on which of those is true.

**UNPROVEN, and it matters.** Identical git dates are strong but not conclusive
(a clone-then-rename and a fork produce the same signature). The query that
settles it, on the knight:

```bash
git -C ~/…/smelt-gateway log --format=%H --reverse | head -1
git -C ~/…/L5GN-Castle  log --format=%H --reverse | head -1   # same SHA => same repo
git -C ~/…/smelt-gateway remote -v
```

Same root commit SHA means one repo under two names, and the curated registry's
placement of `smelt-gateway` under Citadel MicroIDE is wrong. **This is flagged
for your ruling and the registry has been left as-is pending it** — moving 117
threads on a hunch is precisely the kind of unauditable merge this brief exists to
avoid.

### Finding 3 — the reset is not idempotent; relink will rebuild the legacy rows

This is the important one. `relink.score_thread` builds its candidate set from two
places: registry entries keyed by **id**, and `link_evidence` rows keyed by
whatever string sits in `link_evidence.project`. Those strings are folder names
written by a pre-id-scheme producer:

| `link_evidence.project` | rows | is it a registry id? |
|---|---|---|
| `smelt-gateway` | 319 | yes |
| `L5GN_Armory_v4` | 120 | **no** (`l5gn-armory-v4`) |
| `L5GN-Crystal-Spire` | 79 | **no** (`l5gn-crystal-spire`) |
| `v1 proto` | 64 | **no** (`citadel-v1-proto`) |
| `Chronicler` | 28 | **no** |
| `SolConfig` | 24 | **no** (`mcf-sol-config`) |
| `DesktopsAndDungeons` | 10 | **no** |
| `l5gn-castle-repo` | 6 | yes |
| `GemToPairs` | 5 | **no** (`gemtopairs`) |
| `L5GN OS` | 2 | **no** |

**332 of 657 evidence rows (50.5%) are keyed to names that are not link targets.**
A candidate carrying one of those keys can win, and `relink.upsert_project` then
does `INSERT INTO projects (project_id…) VALUES (<that raw string>…)` with
`registry.get(target_id, {})` returning `{}`. That is not a historical accident —
it is a live code path that **re-creates a legacy `projects` row on every run**.

The nine rows Task B deletes are the nine names in that column. Run the reset
exactly as briefed and the first `relink.py --apply` afterwards puts them back.

**Consequence for Task C.** The reset needs a fourth step the brief does not have:
either re-key `link_evidence.project` onto ids, or make relink ignore evidence
whose project is not a link target. Re-keying is a 9-row `UPDATE … CASE` and is
recommended — it preserves all 657 rows of evidence, which is the thing that makes
re-earning the 226 links cheap. Discarding it would make the reset far more
expensive than the ruling assumed. Statements are in §Task C.

**Consequence for Task D.** The briefed invariant — refuse to apply when
`projects` holds a foreign row — would be correct *and permanently red*, because
relink itself creates the foreign row it would then refuse. The invariant belongs
one step earlier: refuse to *score* a candidate whose key is not a link target.
Same loud failure, at the point where the bad identity actually enters.

---

## Task A — the definitive project list

### The generation census, done properly

The brief's `project_id GLOB '*[A-Z ]*'` heuristic is replaced by the sound test:
membership in the current registry's id set.

| Generation | Rows | Threads |
|---|---|---|
| Claude project uuids (`source_system_id` set) | 9 | 0 |
| Current registry ids | 7 | 133 |
| Legacy — neither | **9** | **93** |
| **Total** | **25** | **226** |

This reconciles the brief's three buckets exactly (93 legacy + 117 `smelt-gateway`
+ 16 "current") — `smelt-gateway` and `l5gn-os` are *both* current registry ids,
which is why the heuristic split them out.

### The reconciliation table

`ev` = which of the brief's six sources attest: **1** curated seed · **2** generated
registry · **3** deposits · **4** `projects` table · **5** Claude uuids · **6** thread titles.
`thr` = threads linked today. Deposits: **P** personal, **W** work.

#### Program: L5GN OS (`l5gn-os`, low_signal_body)

| id | tier | canonical_name | aliases added this pass | scope | present | thr | ev |
|---|---|---|---|---|---|---|---|
| `citadel-microide` | project | Citadel MicroIDE | Citadel Castle, CitadelMicroIDE, CitadelMicroIDE v4, CID v4.1, CID v5.0, Citadel L5GN MicroIDE, Micro IDE | l5gn | via repos | — | 1,5,6 |
| ` citadel-v1-proto` | repo | v1 proto | — | l5gn | W | 10 | 1,2,3,4,6 |
| ` l5gn-armory` | repo | L5GN-Armory | — | l5gn | P | 0 | 1,2,3 |
| ` l5gn-armory-v2` | repo | L5GN-Armory_v2 | — | l5gn | P | 0 | 1,2,3 |
| ` l5gn-armory-v4` | repo | L5GN_Armory_v4 | — | l5gn | P+W | 51 | 1,2,3,4 |
| ` smelt-gateway` | repo | smelt-gateway | — | l5gn | W | **117** | 1,2,3,4,6 |
| `crystal-spire` | project | Crystal Spire | **DungeonsAndDesktops**, Dungeons and Desktops, **DiT** | l5gn | via repos | 0 | 1,2,4,5,6 |
| ` l5gn-crystal-spire` | repo | L5GN-Crystal-Spire | — | l5gn | P+W | 6 | 1,2,3,4 |
| ` desktopsanddungeons-repo` | repo | DesktopsAndDungeons | **NEW repo tier** | l5gn | W | 4 | 2,3,4,6 |
| `universal-content-pipeline` | project | L5GN Journal / UCP | **Smelter, Master Smelter, UCP Master Smelter, UCP Personal Smelter** | l5gn | no | 1 | 1,2,4,5,6 |
| `l5gn-mesh-network` | project | L5GN Mesh Network | — | l5gn | via repo | 1 | 1,2,4,5 |
| ` vertex-3` | repo | l5gn-mesh-vertex-3_prod | — | l5gn | P | 0 | 1,2,3 |
| `chancellor` | project | Chancellor | — | l5gn | no | 0 | 1,2 |
| `chronicler-gas` | project | Chronicler (GAS-era) | **L5GN_TOWER_Chronicler, Chronicler Tower, L5GN Tower, L5GN_TOWER, ConViewer, L5GN_ConViewer** | l5gn | no | 0 | 1,2,6 |
| `auditor-arbiter` | project | Auditor | **Watchtower, The Watchtower** | l5gn | no | 0 | 1,2,6 |
| `l5gn-os-program` | project | L5GN OS (program-level) | **L5GNOS, L5GN_TOWER_L5GNOS** | l5gn | no | 0 | 1,6 |
| `l5gn-estate-infrastructure` | project | **NEW** — L5GN Estate Infrastructure | Estate Infrastructure | l5gn | via repos | — | 2,3,6 |
| ` l5gn-castle-repo` | repo | L5GN-Castle | *'Castle' **removed*** | l5gn | P | 3 | 2,3,4,6 |
| ` l5gn-archive-repo` | repo | L5GN-Archive | *'Archive' **removed*** | l5gn | P | 0 | 2,3,6 |
| ` l5gn-server-hub-iso-repo` | repo | L5GN-server-hub-iso | — | l5gn | P | 0 | 2,3 |
| ` l5gn-managed-workspace-repo` | repo | L5GN_Managed_Workspace | — | l5gn | P | 0 | 2,3 |
| `gemtopairs` | project | **NEW** — GemToPairs | GemToPairs, Gem To Pairs | l5gn | W | 0 | 2,3 |

#### Program: WizForgeAnalytics (`wizforge-analytics`, low_signal_body)

| id | tier | canonical_name | scope | present | thr | ev |
|---|---|---|---|---|---|---|
| `mcf-sol-config` | project | SolConfig | mcf | W | 6 | 1,2,3,4,5 |
| ` solconfig-repo` | repo | SolConfig | mcf | W | — | 2,3 |
| `mcf-activity-statements` (+repo) | project | ActivityStatements | mcf | W | 0 | 1,2,3,6 |
| `mcf-churn-level-indicator` (+repo) | project | ChurnLevellIndictor | mcf | W | 0 | 1,2,3 |
| `mcf-pricing-modelisation` (+repo) | project | PricingModelisation | mcf | W | 0 | 1,2,3,6 |
| `mcf-data-access-layer` | project | DataAccessLayer | mcf | no | 0 | 1,2 |
| `mcf-tss-to-assets` (+repo) | project | TSsToAssets | mcf | W | 0 | 1,2,3 |
| `mcf-validation-automation` (+repo) | project | ValidationAutomation | mcf | W | 0 | 1,2,3 |
| `mcf-gulam-data-export` (+repo) | project | **NEW** — GulamDataExport | mcf | W | 0 | 2,3 |
| `mcf-source-data` (+repo) | project | **NEW** — Source_data (low_signal) | mcf | W | 0 | 2,3 |
| `mcf-unified-intelligence-source` (+repo) | project | **NEW** — UnifedIntelligenceSource | mcf | W | 0 | 2,3 |
| `mcf-wizforge-analytics` (+repo) | project | **NEW** — WizForgeAnalytics (repo) | mcf | W | 0 | 2,3 |

#### Standalone (no program)

| id | tier | canonical_name | low_signal | present | thr | ev |
|---|---|---|---|---|---|---|
| `l5gn-tools-chronicler` | project | Chronicler (2026, Python/SQLite) | yes | P+W | 1 | 1,2,3,4 |
| ` l5gn-continuous-ingestion-daemon-repo` | repo | L5GN-Continuous-Ingestion-Daemon **(proposed)** | — | P | 0 | 2,3 |
| `l5gn-tools` | project | L5GN Tools | yes | no | 0 | 1,2 |
| `learning-ai-and-computers` | project | Learning about AI and computers | yes | no | 0 | 1,2 |
| `sovereign` | project | Sovereign | yes | no | 0 | 1,2,6 |
| `build-it-yourself` | project | **NEW** — BuildItYourself | no | no | 0 | **6 only** |

#### Claude project uuids — kept untouched, 0 links, the reconciliation axis

| uuid | Claude project name | proposed target |
|---|---|---|
| `019e6a8b-…` | UCP Personal Smelter | `universal-content-pipeline` |
| `019ec1d0-…` | CitadelMicroIDE | `citadel-microide` |
| `019edceb-…` | CitadelMicroIDE v4 | `l5gn-armory-v4` |
| `019ee1d2-…` | CID v4.1 | `citadel-microide` — **the round-3 UAT proposed `churnlevelindicator`, which is an MCF BI project and cannot be right; "CID" is Citadel** |
| `019ee23d-…` | How to use Claude | none — meta |
| `019f008e-…` | Solution Configurator | `mcf-sol-config` |
| `019f0d6d-…` | CID v5.0 | `citadel-microide` |
| `019f4273-…` | L5GN Crystal Spire | `crystal-spire` |
| `019f710e-…` | L5GN Tools Mobile | `l5gn-tools` |

### The explicit call-outs the brief asked for

**Renames.** Three found, none previously recorded as aliases:

1. `L5GN-Castle` ↔ `smelt-gateway` — identical git history (Finding 2). **UNPROVEN, flagged.**
2. `DesktopsAndDungeons` ↔ `DungeonsAndDesktops` — the halves swapped. Two threads use the reversed form ("Hi DiT! Restarting our Thread on DungeonsAndDesktops"). A pure alias miss; now recorded.
3. `L5GN OS` ↔ `L5GNOS` ↔ `L5GN_TOWER_L5GNOS` — the unspaced and TOWER-prefixed forms appear in six titles and matched nothing. Now aliases of `l5gn-os-program`.

**The Armory generations — proposal: separate repos of one project, as
DECISIONS 0012 already ruled.** The bundle supports it: `l5gn-armory` (6 commits,
Jun 13-14), `l5gn-armory-v2` (10, Jun 15-16), `l5gn-armory-v4` (80, Jun 17-24)
are strictly sequential with no overlap — a lineage, not rivals. `v1 proto` sits
in the work deposit with no git history at all. What the bundle does **not**
support is `smelt-gateway`'s membership (Finding 2); its dates precede
`l5gn-armory` by two weeks and match `L5GN-Castle` exactly. **168 threads hang on
this and it is flagged for your ruling, not decided here.**

**`SolConfig` vs `MCF Solution Configurator` vs `mcf-solution-configurator` — one
project, three identities.** Evidence: one repo in the work deposit
(`MCF/SolConfig`, 2 commits), one Claude project uuid (`019f008e`, "Solution
Configurator"), and three `projects` rows for it (`SolConfig` 6 threads,
`MCF Solution Configurator` 4, `mcf-solution-configurator` 0). Nothing anywhere
suggests two efforts. Kept as `mcf-sol-config` — *not* renamed to
`mcf-solution-configurator`, because renaming an id to fix an identity problem is
the exact move that created the `l5gn-os` collision. The other two names are now
aliases.

**The five unfiled auto projects.** Four are one project, not four:
`L5GN-Castle`, `L5GN-Archive`, `L5GN-server-hub-iso` and `L5GN_Managed_Workspace`
are the physical incarnations of *running the estate* — proposed as
`l5gn-estate-infrastructure` under L5GN OS, with those four as repos. The fifth,
`L5GN-Continuous-Ingestion-Daemon` (52 commits, Jun 26 – Jul 3), is proposed as a
repo of `l5gn-tools-chronicler`: continuous ingestion is what that Chronicler
does, and the dates sit immediately before the L5GN-Tools work began. **All five
flagged for your ruling.**

**A false-positive class, proven mechanically.** `l5gn-castle-repo`'s alias
`Castle` was matching the knight's **hostname**. relink's boundary regex is
`(?<![A-Za-z0-9])Castle(?![A-Za-z0-9])`; the hyphens in `l5gn-castle-worker` are
non-alphanumeric, so the boundary holds and the alias fires. Two of that row's
three links are shell transcripts (`l5gn@l5gn-castle-worker:~/L5GN-Tools$ python
run.py backup`). A third title reads *"We are building 'Citadel Castle'"* — which
is Citadel MicroIDE. The bare `Castle` and `Archive` shortnames are removed.

**In a deposit, claimed by nobody** (now claimed): `GemToPairs`,
`GulamDataExport`, `Source_data`, `UnifedIntelligenceSource`, `WizForgeAnalytics`
(the folder, as distinct from the program).
**In the registry, in no deposit:** `chancellor`, `chronicler-gas`,
`auditor-arbiter`, `l5gn-os-program`, `l5gn-tools`, `learning-ai-and-computers`,
`sovereign`, `mcf-data-access-layer`, `build-it-yourself`, and
`universal-content-pipeline` — ten link targets with no code behind them. That is
legitimate (they are conversation-only efforts) but it means `present=false` is
the norm, not an alarm.

### The file

`config/project_registry.json` rewritten in place. Gitignored — **ship by scp**.

- **28 → 52 link targets.** 24 added, **0 removed, 0 re-tiered, 0 ids remapped.**
- Aliases added to 8 existing entries (listed above); 2 removed (`Castle`, `Archive`).
- **sha256:** `a8416e0bc4a87d138220bfa14563113c47a828daf945835f45950dccc982e4f5`
- The zero-remap property is deliberate: it gives Task E's id-remap check a clean
  baseline to be built against, and means shipping this file cannot orphan a
  ruling.

---

## Task B — the reset, counted before it runs

Measured on the live vault at 2026-07-21T10:50:07Z.

### What clearing the links costs

| | rows |
|---|---|
| threads with `project_link IS NOT NULL` | **226** |
| of those, `project_confidence='evidence'` | 213 |
| of those, **`project_confidence='manual'`** | **13** |
| threads with the legacy string `'none'` in `project_confidence` (link NULL) | 44 |
| **rows the UPDATE touches** | **270** |

**The 13 manual rulings, in full** — this is the number you are agreeing to, not a
hand-wave. Ten of them point at `l5gn-os`, which is now the *program* id: they were
ruled when `l5gn-os` still meant the project. Read as a group they are almost all
Citadel MicroIDE:

| target | n | titles |
|---|---|---|
| `l5gn-os` | 10 | "Building the agentic loop for Citadel L5GN MicroIDE", "Citadel MicroIDE T5 chunking policy implementation", "Refactoring Citadel's event-driven architecture", "Prompt engineer IDE codebase audit and consolidation", "Vault documentation service refactoring", "Project restart and phase 3 handoff", "Repository updates and next development steps", + 3 Gemini opener threads |
| `l5gn-mesh-network` | 1 | "Building a MicroIDE with local LLM support" — *looks mis-ruled; it is a MicroIDE thread* |
| `l5gn-tools-chronicler` | 1 | "Building a terminal-based D&D world for Discord" — *looks mis-ruled; that is Crystal Spire* |
| `universal-content-pipeline` | 1 | "AI Persona Pipeline Image Creation" |

Two of the thirteen appear mis-ruled on their titles, and ten were ruled against
an id that has since changed meaning. That is an argument *for* the reset, and
worth stating: the rulings being discarded are not thirteen good answers.

**A bonus the brief did not ask for.** `SCHEMA.md` convention 1 states the legacy
string `'none'` "has been migrated to SQL `NULL`; do not test for `'none'`". The
live vault has **44 rows still carrying it**. The reset clears them, bringing the
vault into line with its own documented contract.

### What deleting the rows costs

Nine rows are neither a Claude uuid nor a current registry id:

| project_id | name | repo_folder_path | threads |
|---|---|---|---|
| `L5GN_Armory_v4` | L5GN_Armory_v4 | L5GN/L5GN_Armory_v4 | 51 |
| `Chronicler` | Chronicler | L5GN/Chronicler | 10 |
| `v1 proto` | v1 proto | L5GN/v1 proto | 10 |
| `L5GN-Crystal-Spire` | L5GN-Crystal-Spire | L5GN/L5GN-Crystal-Spire | 6 |
| `SolConfig` | SolConfig | MCF/SolConfig | 6 |
| `DesktopsAndDungeons` | DesktopsAndDungeons | L5GN/DesktopsAndDungeons | 4 |
| `MCF Solution Configurator` | MCF Solution Configurator | — | 4 |
| `L5GN OS` | L5GN OS | — | 2 |
| `mcf-solution-configurator` | MCF Solution Configurator | — | 0 |
| | | **total** | **93** |

Seven rows survive as current registry ids (`smelt-gateway` 117, `l5gn-os` 10,
`l5gn-castle-repo` 3, `l5gn-mesh-network` 1, `l5gn-tools-chronicler` 1,
`universal-content-pipeline` 1, `crystal-spire` 0) and nine as Claude uuids.
**25 rows → 16.** The census then returns two buckets, not three.

**Orphans: zero**, confirmed — the S6 check returned no rows.

---

## Task C — the exact reset (NOT RUN — no knight access)

Order matters: clear `threads` before deleting `projects`, or the FK refuses.
Step 0 is not optional (DECISIONS 0005/0006).

```bash
ssh l5gn-castle
cd ~/L5GN-Tools
.venv/bin/python run.py backup          # report the snapshot filename in the results log
```

```sql
-- 1. clear every link and confidence value.  Expect: 270 rows.
UPDATE threads
   SET project_link = NULL, project_confidence = NULL
 WHERE project_link IS NOT NULL OR project_confidence IS NOT NULL;

-- 2. delete the nine legacy rows.  Expect: 9 rows.
DELETE FROM projects WHERE project_id IN (
  'L5GN_Armory_v4','Chronicler','v1 proto','L5GN-Crystal-Spire','SolConfig',
  'DesktopsAndDungeons','MCF Solution Configurator','L5GN OS',
  'mcf-solution-configurator');

-- 3. RE-KEY THE EVIDENCE.  Not in the brief; see Finding 3.  Expect: 332 rows.
--    Without this, step 2 is undone by the next relink run.
UPDATE link_evidence SET project = CASE project
    WHEN 'L5GN_Armory_v4'     THEN 'l5gn-armory-v4'
    WHEN 'L5GN-Crystal-Spire' THEN 'l5gn-crystal-spire'
    WHEN 'v1 proto'           THEN 'citadel-v1-proto'
    WHEN 'Chronicler'         THEN 'l5gn-tools-chronicler'
    WHEN 'SolConfig'          THEN 'mcf-sol-config'
    WHEN 'DesktopsAndDungeons' THEN 'desktopsanddungeons-repo'
    WHEN 'GemToPairs'         THEN 'gemtopairs'
    WHEN 'L5GN OS'            THEN 'l5gn-os-program'
  END
 WHERE project IN ('L5GN_Armory_v4','L5GN-Crystal-Spire','v1 proto','Chronicler',
                   'SolConfig','DesktopsAndDungeons','GemToPairs','L5GN OS');

-- verification: must return no rows
SELECT DISTINCT project FROM link_evidence
 WHERE project NOT IN (<the 52 ids from the new registry>);
```

Step 3 maps `'Chronicler'` → `l5gn-tools-chronicler`, not `chronicler-gas`: its 28
evidence rows are `path_mention` and `filename_xref` hits on
`L5GN/Chronicler`, a Python folder, and the GAS-era Chronicler was a spreadsheet.
**Confirm that reading before running it.**

Then:

```bash
scp config/project_registry.json l5gn-castle:L5GN-Tools/config/project_registry.json   # Finding 1
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases   # expect programs, NOT "STANDALONE"
.venv/bin/python chronicler/pipeline/build_registry.py                    # write it
.venv/bin/python chronicler/pipeline/relink.py                            # DRY-RUN. Stop here.
```

**Stop before `--apply`.** The dry-run table is the GO/NO-GO. There is no dry-run
decision table in this report because the dry-run has not been run — reporting one
would be simulating a result, which the brief forbids.

---

## Task F — does `collapse_lineage` fire on the knight?

**Both round-3 claims are true; they are about different things, and neither is
about the knight's real data.**

1. **The UI was never running it.** `collapse_lineage` lives inside
   `relink.decide()` — it runs at *write* time. The review UI does not compute
   candidates at all: `core.pending_items()` selects `review_queue` rows and
   renders the stored `q.note` string, and `app.py` offers *every* registry entry
   in the assignment picker, sorted by breadcrumb. So the "conflicting candidate
   matches" the UAT observed are **frozen note text from earlier relink runs**
   (212 `link_ambiguous` rows are pending) plus a full-registry picker. Nothing
   recomputes them, so no amount of lineage collapse would change that screen.
2. **On the knight there is almost no lineage to collapse.** Per Finding 1 the
   generated registry has `programs: []` and every curated project has
   `repos: []`. The only parent links that exist are the 25 auto `project → *-repo`
   pairs. `citadel-microide`, and therefore the whole Armory lineage, does not
   exist there — so the sibling roll-up the round-3 report demonstrated has never
   had a hierarchy to work on.
3. **The round-3 dry-run was a fixture.** It ran "against a synthetic five-thread
   vault" (its own words) using the rig's three-tier seed. A rule proven only
   against a fixture has not been proven — the brief's phrasing, and it is correct
   here.

`smelt-gateway` vs `Chronicler`, the other pair the UAT saw, is a genuinely
unrelated rivalry and `collapse_lineage` is right not to fold it.

**UNPROVEN:** that the specific `L5GN-Crystal-Spire` / `l5gn-crystal-spire-repo`
row predates the collapse_lineage change. One query settles it:

```sql
SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM review_queue
 WHERE type='link_ambiguous' AND status='pending';
SELECT item_id, created_at, note FROM review_queue
 WHERE type='link_ambiguous' AND note LIKE '%crystal-spire%' LIMIT 5;
```

If those rows predate round 3, they are stale queue debris and the reset should
clear them too — worth your ruling, since the brief scopes the reset to
`project_link`/`project_confidence` only.

---

## Task G — the registry path derivation

**relink and the review endpoint do not read the same file today. Proven:**

```
CHRONICLER_HOME            = (unset)
CHRONICLER_REGISTRY_PATH   = /home/l5gn/vault/project_registry.json
relink.REGISTRY_PATH       = /home/l5gn/L5GN/.intel_sync/project_registry.json   exists=True
review.resolve_registry_path() = /home/l5gn/vault/project_registry.json          exists=True
```

Two different files, both present, both real. relink links against one; the
endpoint validates human rulings against the other. A ruling can therefore be
accepted for an id relink has never heard of, or refused for one it just wrote.

Two further facts worth having:

- **`CHRONICLER_HOME` is unset on the knight**, contrary to the brief's premise.
  relink's path does not come from it at all: `CHRONICLER_ROOT` resolves from the
  *repo location* (`~/L5GN-Tools/chronicler`), so `.parent.parent` = `/home/l5gn`
  and the registry lands in `~/L5GN/.intel_sync/`. The brief's "works by accident
  of arithmetic" is right, but the accident is that the repo happens to sit two
  levels below `$HOME` — move or rename the checkout and the path moves with it.
- `~/L5GN/.intel_sync/` contains exactly one file. There is no Github root there;
  the directory exists only because `build_registry` created it.

**Answers.**

*Where should it live on a consumer?* Under `CHRONICLER_HOME` — it is machine
state derived from deposits, the same class as the DB and the snapshots, and it
has no business inside a Github-root-shaped path on a box with no Github root.

*Is `CHRONICLER_REGISTRY_PATH` the right knob?* Yes, and it is already set and
already honoured by `review.resolve_registry_path`. The defect is that **relink
does not consult it** — `REGISTRY_PATH` is a module constant computed at import.

*Proposed fix — small and obviously right.* Give relink the same three-step
resolution the endpoint already has, with the env knob first:

```python
def resolve_registry_path():
    env = os.environ.get("CHRONICLER_REGISTRY_PATH")
    if env:
        return Path(env)
    return GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
REGISTRY_PATH = resolve_registry_path()
```

Four other modules (`build_registry`, `build_activity`, `build_inventory`,
`xref_filenames`) duplicate the same derivation, so the honest fix is one shared
resolver they all import. **Not built this session** — it touches five files and
the agreed scope was A and B. It is the single highest-value small build left,
because until it lands the two halves of the system disagree about what the
registry *is*.

---

## Drafted DECISIONS 0017 — for ratification, not appended

> Draft only. `DECISIONS.md` is Tim's log; nothing has been written to it.

---

### 0017 — The `projects` table is reset and rebuilt, not migrated; 0011's debt is paid

**Date:** 2026-07-21 · **Status:** proposed · **Executes:** 0011 · **Source:**
`COWORK_BRIEF_projects_reconciliation.md`; live census 2026-07-21T10:50Z

**Context.** 0011 ruled in round 2 that existing `project_link` values are noise
from early auto-accept testing and should be reset rather than trusted. The
runbook was written; no knight access existed to run it. Every relink and ruling
since has layered onto a table the repo had already decided not to trust. The
result, measured: 25 `projects` rows in three generations — 9 Claude uuids, 7
current registry ids, 9 legacy — carrying 226 links across five duplicate
identity clusters, with zero orphans. The FK held throughout; the problem is
duplication, not breakage.

Two things found while measuring change what "reset" has to mean. First,
`config/project_registry.json` was never shipped to the knight after round 3, so
the three-tier registry (0012) has never existed there and the guard meant to
refuse a flat registry tests for a `programs` *key* that the generator always
emits. Second — and the reason this entry is not simply "run 0011's runbook" —
`relink.score_thread` keys candidates by the raw `link_evidence.project` string,
and `upsert_project` will insert whatever that string says. 332 of 657 evidence
rows are keyed to folder names rather than ids, so a reset that does not re-key
the evidence is undone by the next relink run.

**Decision.** Reset and rebuild; do not migrate. Clear `project_link` and
`project_confidence` on every thread (270 rows), delete the 9 `projects` rows
that are neither a Claude uuid nor a current registry id (93 links), **re-key the
332 legacy `link_evidence.project` values onto registry ids**, ship the rewritten
curated registry, regenerate, and re-earn the links through relink and Tim's
rulings.

Not migrating is the smaller cost: a careful merge of 226 links across five
identity clusters would produce a result nobody could audit, and the manual
tagging at risk is 13 rulings — of which 10 point at an id (`l5gn-os`) that has
since changed meaning and 2 look mis-ruled on their own titles.

**Consequences.** 226 links discarded, 13 of them human rulings — that is the bad
part and it is accepted deliberately. What survives: the 9 Claude uuid rows (they
are Claude's own entities and hold no links), every thread and message, all 657
evidence rows, and every alias Tim has authored. The re-key step (`link_evidence`)
extends the reset beyond the two columns the brief scoped, and is what makes the
result stable rather than momentary. `l5gn-os` keeps its program meaning; the 10
threads ruled against its old project meaning are re-earned, most likely onto
`citadel-microide`. Two follow-ups this commits us to: relink's flat-registry
guard must test content not key presence, and the candidate-scoring path must
refuse a key that is not a link target — otherwise the third generation grows
back the same way the second did.

---

## UAT — acceptance checks

Full walk-sheet: **`docs/UAT_projects_reconciliation.md`**. Every item marked
*ready to walk*; none marked passed. The results log you produce must carry a uat
stamp (`docs/README.md` §3) or `auditor_uat_stamp` refuses the commit.

## Files changed

- **New:** `docs/RUNBOOK_collect_reconciliation_evidence.md`,
  `docs/COWORK_REPORT_projects_reconciliation.md`,
  `docs/UAT_projects_reconciliation.md`.
- **Changed, gitignored, ship by scp:** `config/project_registry.json`
  (sha256 `a8416e0b…82e4f5`).
- **No code changed.** `verify.py` GREEN before and after.

Nothing committed. Nothing written to the live vault.
