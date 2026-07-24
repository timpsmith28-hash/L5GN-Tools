# UAT — intent evidence

**Brief:** `docs/COWORK_BRIEF_intent_evidence.md`
**Report:** `docs/COWORK_REPORT_intent_evidence.md`
**Built:** 2026-07-21, Cowork on `LucasGoonPC`
**Gate at build time:** `python verify.py` → GREEN (6 auditors + 28 testers)

Every item below is **ready to walk**. None is marked passed — that is Tim's call,
and the result belongs in `docs/UAT_intent_evidence_results.md` with a commit stamp,
or `auditor_uat_stamp` will refuse the commit.

Items are ordered so that a failure stops the walk before it costs anything.

---

## Legend

| Marker | Meaning |
|---|---|
| **RIG** | Walk on a producer (Windows) |
| **KNIGHT** | Walk on the knight |
| **EITHER** | Machine-independent |
| ⚠ | Reads a real vault or rewrites real data — read the note first |

---

## 0 — Crystal Spire's git position ⚠ **RIG**

The only item where work has already been executed against a real repo. Walk it
first; everything else is reversible and this is the one that was not.

### 0.1 The backup exists and opens

```powershell
cd C:\Users\timps\Documents\Backups
dir L5GN-Crystal-Spire_pre-surgery_20260721.tar.gz
```

- [ ] File exists, ~33 MB.
- [ ] Extract it somewhere scratch and confirm it opens.

```powershell
mkdir C:\Users\timps\Documents\Backups\_verify
tar -xzf L5GN-Crystal-Spire_pre-surgery_20260721.tar.gz -C C:\Users\timps\Documents\Backups\_verify
cd C:\Users\timps\Documents\Backups\_verify\L5GN-Crystal-Spire
git log --oneline
```

- [ ] **11 commits**, HEAD `77045a5`.
- [ ] `modules_v3\` contains **1,601** `.md` files.
- [ ] `world_graph.json`, `world2.json`, `canon_index.json` all present.

### 0.2 The old history is independently recoverable

```powershell
cd C:\Users\timps\Documents\Backups\L5GN-Crystal-Spire_history_pre-reset_20260721
git clone L5GN-Crystal-Spire_full.bundle recovered-spire
cd recovered-spire
git log --oneline
```

- [ ] Clones without error and shows the **same 11 commits**.
      *This is the real safety net — the bundle stands alone even if the tarball is lost.*

### 0.3 The three world files are no longer tracked

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Crystal-Spire
git status --short
git ls-files world_graph.json world2.json canon_index.json
```

- [ ] `git status` is **clean** (0 lines).
- [ ] `git ls-files` for the three world files returns **nothing**.
- [ ] All three files are still **on disk** — `dir world_graph.json` finds them.
- [ ] `dir modules_v3\*.md | measure` → **1,601** files on disk, and
      `git ls-files modules_v3\` returns **nothing**.

### 0.4 The ratified option was applied, and the history reads as you expect

```powershell
git log --oneline
git remote -v
```

- [ ] **Six commits**, ending `30cc7e4 docs: HISTORY_RESET.md`.
- [ ] The five stratum commits below it read sensibly and their messages explain
      that this is a reconstruction.
- [ ] **`git remote -v` prints nothing.** No remote. This is the item that must
      never quietly change.
- [ ] `HISTORY_RESET.md` opens and its account matches what you believe happened.

### 0.5 The two open decisions ⚠

Not defects — decisions the session deliberately left to you.

- [ ] **`DRIVE_ID_SCAN.md` and `HYGIENE_SWEEP.md` are tracked and quote all 33
      live IDs verbatim.** They are now the only tracked files carrying live IDs.
      Decide: keep tracked, or move outside the repo?
- [ ] **`modules_v3/` is version-controlled nowhere.** 1,601 files, 8.5 MB, on
      disk and in the 2026-07-21 tape only. Accept, or arrange a second copy?

> **Not in scope and not attempted:** the scrub itself. The real names and live
> Drive IDs are unchanged in every file. Confirm you did not expect otherwise.

---

## A — `file_inventory` exists for every deposited project

### A.1 Prerequisite — regenerate the deposits **RIG**

The `basenames_beyond_cap` field is new; deposits on disk predate it.

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py build --fresh
python run.py deposit --push
```

- [ ] Completes without error and reports **11 projects**.

*(Repeat on the work rig if it is deployed.)*

### A.2 Every deposited project gets an inventory **KNIGHT**

```bash
cd ~/L5GN-Tools
.venv/bin/python chronicler/pipeline/build_registry.py
.venv/bin/python chronicler/pipeline/build_inventory.py --force
```

- [ ] Reports **11 built, 0 missing**.
      *Before this change, all 11 reported MISSING. If you see missing projects,
      stop — the folder-walk defect has not actually been fixed.*
- [ ] `file_count` per project matches the census summary for that project.

### A.3 The non-git projects carry a signature, not an empty block **KNIGHT**

- [ ] `L5GN-Archive` and `L5GN-server-hub-iso` show `signature=…`, not a commit,
      and **not an empty block**.
- [ ] The other nine show a **`source_commit`** matching that repo's HEAD.

> **Correction to the brief:** it expected *four* non-git projects. There are
> **two**. `L5GN-Crystal-Spire` and `test_folder` were misreported as non-git —
> that was the B2 bug — and are now correctly detected as git. Confirm you agree
> two is right, because if you expected four, one of us is wrong.

### A.4 Truncation — the Castle decision is visible in the output **KNIGHT**

The decision was: **carry basenames past the cap** (not raise it, not accept the
blind spot). S4 matches on basename alone, so this costs a few KB and closes the
gap entirely.

- [ ] `L5GN-Castle` shows `files=3805`, `listed=2000`, and **`+names` non-zero**
      (expect ~1805).
- [ ] `L5GN-Castle` **no longer** carries the `<- SHORT` flag.
      *If it still does, A.1 was not re-run and the deposit is stale.*
- [ ] Every other project shows `+names = 0` — none of them are near the cap.

---

## B — the folder-walk audit

Reading, not running. The report has the full table.

- [ ] Two remaining `resolve_fs` instances named with line numbers:
      `build_activity.py:237–241`, `build_vocabulary.py:358`.
- [ ] **Two more the brief did not anticipate**, and you agree they matter:
  - `relink.py:189` writes the dead layout **into the vault** — the `projects`
    table already holds `L5GN/Chronicler`, `MCF/SolConfig`. This is the only
    instance that has written bad data into a durable store.
  - `REGISTRY_PATH` assumes `GitHub/L5GN/.intel_sync/` in **four** modules, and
    that folder does not exist on the rig. Because `write_json_atomic` does
    `mkdir(parents=True)`, `build_registry` would **create** it rather than fail.
- [ ] You accept the recommendation: **fix `REGISTRY_PATH` and `relink.py:189`
      before more `resolve_fs` instances.**
- [ ] You accept that **`build_activity.py` was not refactored** this session —
      judged small and left undone for budget, per the brief's "a second task done
      badly costs more than a first task done well."

### B2 — the `is_git` contradiction **EITHER**

- [ ] You accept the mechanism: `is_git_repo` is a pure `.git` existence check
      and could only fail on a **path that did not exist**. The contradiction and
      the folder-walk defect are **one bug seen from two sides**.
- [ ] `python run.py estate_status` (or `data/estate_status.json`) reports
      **9 git repos**, not 7.
- [ ] Crystal Spire and `test_folder` both report `is_git: true`.
- [ ] No fix was needed — the working tree's existing scanner changes already
      resolved it. Confirm you are content that nothing further was changed here.

---

## C — S4 dry-run ⚠ **KNIGHT**

```bash
.venv/bin/python run.py backup            # BEFORE anything else
.venv/bin/python chronicler/pipeline/xref_filenames.py     # dry-run is the default
```

- [ ] Reports a basename index of roughly **4,816 basenames** (it was empty before
      Task A — an empty index means the producer aborts).
- [ ] Row counts land in the same region as the report's table
      (~2,246 rows / ~321 threads / 11 projects). Exact equality is **not**
      expected — the report's run used a 2026-07-17 snapshot.

### C.1 The spot-check — the item worth most ⚠

> The brief: *"a wrong one is worth more than ten right."*

Pick **three** threads S4 links and open them.

- [ ] Thread 1 — project: ______________ · plausible? **Y / N**
- [ ] Thread 2 — project: ______________ · plausible? **Y / N**
- [ ] Thread 3 — project: ______________ · plausible? **Y / N**

Suggested picks:

- [ ] One **`L5GN-Crystal-Spire`** unique hit. It has 71 unique and **zero**
      multi-hits — the cleanest signal in the estate. If these are wrong, the
      whole join is suspect.
- [ ] One **`L5GN-Archive`** hit. Archive gains evidence for the first time and
      scores **zero** path mentions, so filename evidence is its only route.
- [ ] One **multi-hit** (weight < 1.0), ideally on `handover_schema.py` or
      `citadel_archetypes.json` — see C.2.

### C.2 The stoplist

- [ ] You agree the brief was right: **`handover_schema.py`** (3 owners, 15
      attachments) and **`citadel_archetypes.json`** (5 owners, 16 attachments)
      are **not** stoplisted and should be.
- [ ] You have a view on the finding in the other direction: **`index.html` and
      `style.css` are stoplisted but owned by exactly one project each**, so
      stoplisting them discards a legitimate unique hit. Suppress on *measured*
      owner count rather than a hardcoded name?

### C.3 Apply — only on your GO ⚠

- [ ] Dry-run is clean **and** the three spot-checks are plausible.
- [ ] `run.py backup` has been taken.
- [ ] **GO given.** Then, and only then:
      `.venv/bin/python chronicler/pipeline/xref_filenames.py --apply`

> **Read Correction 1 in the report first.** `link_evidence` already holds 568
> stale `filename_xref` rows from 2026-07-16, naming projects that no longer
> exist (`Chronicler`, `smelt-gateway`, `v1 proto`, …). The producer deletes and
> re-inserts *its own* rows, so applying will clear them — but confirm you expect
> that, and that the DECISIONS 0011 reset is still the plan for the rest.

---

## D — S5 dry-run ⚠ **KNIGHT**

```bash
.venv/bin/python chronicler/pipeline/extract_path_mentions.py
.venv/bin/python chronicler/pipeline/extract_path_mentions.py     # again
```

- [ ] First run reports roughly **104 rows across 84 threads**, 9 projects.
- [ ] **The second run adds nothing — 0 new rows.** The watermark holds.
      *This is the acceptance check the brief names. If the second run adds rows,
      stop and do not apply.*
- [ ] You accept that **`L5GN-Archive` scores zero path mentions** — its name is
      too generic to match safely, so it depends entirely on filename evidence.

### D.1 The double-count finding — read before any `relink` work ⚠

The brief asked whether two evidence rows for one thread/project compound, cap,
or deduplicate, and to flag it if the answer is "compound".

**It is compound.** `relink.combine()` caps counts only for `vocabulary`, then
multiplies everything else.

- [ ] You accept the worked numbers:

  | Evidence | Score | vs. auto-link 0.90 |
  |---|---|---|
  | one `filename_xref` @ 1.0 | **0.970** | **auto-links alone** |
  | one `path_mention` @ 0.9 | 0.900 | at threshold |
  | **both, from one sentence** | **0.997** | far above |
  | three *independent* signals @ 0.6 | 0.936 | **below the pair** |

- [ ] You accept the two aggravating factors: a **lone** unique filename hit
      already auto-links with no corroboration, and **`filename_xref` has no
      count cap**, so N hits in one thread all compound.
- [ ] You accept the recommendation: add both signals to `SIGNAL_COUNT_CAP` and
      treat them as **one evidence family**, since a filename hit and a path
      mention from the same message are not independent observations.
- [ ] **`relink --apply` is not run until this is settled.**

---

## E — the origin query **EITHER**

**Delivered.** The table is in the report. This walks its plausibility, which is
the only part a machine cannot check.

### E.1 The headline claim

- [ ] **Every project's earliest evidenced thread precedes its first commit** —
      by up to 17 days. You accept this as the brief's founding thesis, measured.

### E.2 The two or three you know well — the item that matters

For projects you remember starting, is the named thread plausibly the one?

- [ ] **L5GN-Castle** — 2026-05-20, *"Function GetNeighborContext(currentCoord As
      String)…"*, 9 days before its first commit. Plausible? **Y / N**
- [ ] **L5GN_Armory_v4** — 2026-05-31, *"first batch of 50 is running now. see
      file census attached"*, 17 days before first commit. Plausible? **Y / N**
- [ ] **L5GN-Continuous-Ingestion-Daemon** — 2026-06-18, *"Prompt engineer IDE
      codebase audit and consolidation"*, the only `claude-personal` row.
      Plausible? **Y / N**

### E.3 The row that is wrong — confirm the diagnosis

- [ ] **L5GN-Crystal-Spire**'s earliest evidenced thread is *"when I run
      `docker compose exec gateway mount | grep /data`"* — a Docker question,
      obviously not the origin of a text adventure.
- [ ] You accept the cause: it attaches an **`engine.py`**, and `engine.py` is
      owned by exactly one project in this estate (Crystal Spire's
      `_archive/pipeline_v1/`). Sole ownership ⇒ weight **1.0** ⇒ auto-links.
- [ ] You accept the general lesson: **uniqueness within an 11-project estate is
      not distinctiveness.** `tui.py`, `repl.py` and `world.json` are the same.
      This is the highest-value precision fix available to S4.

### E.4 The caveats are in the output, not buried

- [ ] The report states that **no mtime was used** to establish any origin —
      every date is a chat timestamp; the first-commit column is git.
- [ ] The report states the vault begins **2026-05-02**, and flags that
      L5GN-Castle's 2026-05-20 evidence is close enough to that boundary that its
      **true origin may predate the vault entirely**.
- [ ] The report states an **empty row is ambiguous** — `test_folder` has no
      evidence above the floor but 30 rows below it, and evidence may exist under
      a pre-restructure name.

---

## F — the delve index **EITHER**

Full write-up: `docs/investigation/2026-07-21_crystal-spire-delve-index_2-response.md`

### F.1 The eras are ones you recognise

- [ ] **1,601 floors, 111 delves, 10 eras.** The era names —
      `smeltingthelore`, `thechancellortrials`, `themanifestoreborn`,
      `foundingtheempire`, `chaoticchronotheory`, `modulizingthemass`,
      `chroniclesanddragons`, `obsidianempiremastery`, `thesovereignhandshake`,
      `industrialwizardry` — are yours and match the ten `ERA_DIGEST_*.md` files.
- [ ] The per-era floor and delve counts look right to you.

### F.2 Which side of the mount boundary

- [ ] The report states plainly that **every count was taken sandbox-side**, and
      that this is now safe because the truncation defect no longer reproduces
      (`world_graph.json` → 1,602 zones; `world2.json` → 1,601 floor records,
      both matching your host-side figures).
- [ ] You accept this **contradicts the data-integrity note in `DRIVE_ID_SCAN.md`**.
      Your numbers stand; the constraint that forced them host-side has lifted.

### F.3 The delve → thread join

- [ ] **111 of 111 delves match a vault thread** by title, many at ratio 1.00.
      Spot-check two against threads you remember. Plausible? **Y / N**
- [ ] You accept this settles the brief's caveat: the stitched volumes and the
      vault hold the same conversations.

### F.4 The null result — the item to actually think about

- [ ] Precision **0.000**, recall **0.000**. Zero overlap in both directions.
- [ ] You accept this is **not a producer failure**. Read the two sets:
  - **Linked, not delves:** *building a mobile delve menu browser* · *the fix to
    the attached `tui.py`* · *building a terminal-based d&d world for discord*
  - **Delves, not linked:** *google sheets audit tool development* ·
    *activity statement logic context*
- [ ] You agree the first list is threads **about building** Crystal Spire and
      the second is threads **harvested into** its world — disjoint by
      construction, measuring two different questions.
- [ ] You accept the consequence: **the estate still has no labelled dataset for
      project linkage.** What it has is one for *content provenance*, which the
      schema has nowhere to put. The brief's precision/recall ambition is not
      delivered and cannot be from this dataset.

### F.5 Boundaries held

- [ ] **No floor content in `docs/`** — delve ids, era names, volume names,
      counts and thread titles only. Confirm by reading the investigation doc.
- [ ] **`modules_v3/` was never read** — only its filenames were listed.
- [ ] **No Drive IDs reproduced** anywhere in `docs/`. They were counted, never
      quoted, specifically so Task 0's work is not undone in a second repo.

---

## Extra — `build_activity` and the Crystal Spire time-plausibility trap ⚠ **KNIGHT**

```bash
.venv/bin/python chronicler/pipeline/build_activity.py --force
```

- [ ] Reports **11 built, 0 missing**. *(Before this session: 11 missing.)*
- [ ] `L5GN-Archive` and `L5GN-server-hub-iso` show **mtime** precision; the rest
      show **commit**.
- [ ] Windows look right for projects you know.

### The trap — read before running relink ⚠

- [ ] You accept that **Crystal Spire's window is now a single day** (2026-07-21),
      because the Task 0 reset gave it one day of git history.
- [ ] You accept the consequence: `relink` computes
      `adjusted = score × time_plausibility`, and time-plausibility **hard-zeroes**
      threads more than 14 days before first commit. **All 71 of Crystal Spire's
      filename hits would score 0.**

  | Thread date | `time_plausibility` |
  |---|---:|
  | 2026-06-07 (its earliest evidence) | **0.000** |
  | 2026-07-10 | 0.724 |

- [ ] You accept the **fair account**: the reset did not create this. Pre-reset,
      with a first commit of 2026-07-11, a June thread already scored 0.000.
      Crystal Spire's git history never covered its real lifespan. The reset
      moved the recovery point ten days later.
- [ ] **Decision for you:** record a manual `first_seen` for Crystal Spire in
      `config/project_registry.json` — the curated layer `build_registry` reads
      and never overwrites. A registry data decision, not a code change.

---

## Gate

- [ ] `python verify.py` → **GREEN** (6 auditors + 28 testers).
- [ ] `git status` in **L5GN-Tools** shows the changed files **uncommitted**.
      Nothing in this repo was committed.
- [ ] Results recorded in `docs/UAT_intent_evidence_results.md` **with a commit
      stamp**, or `auditor_uat_stamp` refuses the commit.
