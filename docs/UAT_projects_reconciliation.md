# UAT — projects reconciliation

**Pairs with:** `docs/COWORK_REPORT_projects_reconciliation.md` ·
`docs/COWORK_BRIEF_projects_reconciliation.md`

Every item below is **ready to walk**, never "passed". Only Tim walking it passes
it. `verify.py` green proves the code works; it cannot prove the identities are
right — that is what this sheet is for.

**Before you start.** `verify.py` was GREEN in the build session (6 auditors, 24
testers) and no code was changed, so re-running it is a formality rather than a
gate here. Items A, F and G need nothing but reading and one ssh session. Items C
and B-2 write to the live vault and are gated on a backup.

**When you write the results log:** name it `docs/UAT_projects_reconciliation_results.md`
and give it a uat stamp on line 1, or `auditor_uat_stamp` refuses the commit:

```
<!-- uat: commit=<sha> dirty=<bool> host=l5gn-castle-worker walked=2026-07-21 gate=6a/24t -->
```

---

## A — the list (the substantive item; everything else is mechanical)

**Command:** none. Read the reconciliation table in
`docs/COWORK_REPORT_projects_reconciliation.md` § *Task A*.

**Passing looks like:** you recognise your actual projects, their groupings and
their aliases. Nothing you own is missing; nothing appears twice. Concretely, four
questions only you can answer:

1. **Is `smelt-gateway` an incarnation of Citadel MicroIDE, or of `L5GN-Castle`?**
   The deposited git facts say `smelt-gateway` and `L5GN-Castle` share a first
   commit, a last commit and a commit count to the second, and that `L5GN-Armory`
   shares none of it. 117 threads — the largest cluster in the vault — hang on
   this. Settle it on the knight:

   ```bash
   git -C <path>/smelt-gateway log --format=%H --reverse | head -1
   git -C <path>/L5GN-Castle  log --format=%H --reverse | head -1
   git -C <path>/smelt-gateway remote -v
   ```

   Same root SHA ⇒ one repo under two names ⇒ the registry's placement of
   `smelt-gateway` under Citadel MicroIDE is wrong and must move **before** the
   reset, not after.
2. **Are the four estate repos one project?** `L5GN-Castle`, `L5GN-Archive`,
   `L5GN-server-hub-iso`, `L5GN_Managed_Workspace` are proposed as repos of a new
   `l5gn-estate-infrastructure`. Accept, or split them back out.
3. **Is `L5GN-Continuous-Ingestion-Daemon` a repo of the 2026 Chronicler?**
   Proposed on dates (52 commits ending 3 days before the L5GN-Tools work) and on
   function.
4. **What is `BuildItYourself`?** Found only in two thread titles, in no registry
   and no deposit. If it is an early name for something already listed, say which
   and it becomes an alias instead of an entry.

**Also check the aliases added this pass** (report §Task A, bolded): every rename
you can remember should be present. `DungeonsAndDesktops`, `L5GNOS`, `Smelter`,
`L5GN_TOWER_Chronicler`, `Watchtower`, `DiT` were all mined from your own thread
titles and matched nothing before.

**Failing looks like:** a project you own that appears nowhere; two entries you
know are one thing; an alias you would never use.

---

## B — the counts (agree to numbers, not a hand-wave)

**Command:** re-run the two census queries on the knight and confirm they still
match the report. They were measured at 2026-07-21T10:50:07Z.

```bash
ssh l5gn-castle
VAULT=$HOME/vault/chronicler.db
sqlite3 -readonly $VAULT "SELECT COUNT(*) FROM threads WHERE project_link IS NOT NULL;"
sqlite3 -readonly $VAULT "SELECT project_confidence, COUNT(*) FROM threads
  WHERE project_confidence IS NOT NULL GROUP BY 1;"
```

**Passing:** `226` links; confidence census `evidence 213`, `manual 13`,
`none 44`.

**The one you are actually agreeing to:** **13 manual rulings will be
destroyed.** Ten of them point at `l5gn-os` — an id that has since become the
program id, so they were ruled against a meaning that no longer exists. Two look
mis-ruled on their own titles ("Building a MicroIDE with local LLM support" filed
under `l5gn-mesh-network`; "Building a terminal-based D&D world for Discord" filed
under `l5gn-tools-chronicler`). They are listed in full in the report §Task B.
Read that table before you say yes.

**Failing:** the counts have moved since the bundle was taken — someone has ruled
threads in the meantime, and the list you are agreeing to is stale. Re-take it.

---

## C — the reset (writes to the live vault)

**Not run in the build session** — no knight access. The statements are in the
report §Task C, and they are unexecuted.

### C.0 — backup first. No backup, no reset.

```bash
cd ~/L5GN-Tools && .venv/bin/python run.py backup
```

**Passing:** a `chronicler-<UTC>.db` filename is printed. **Record it in the
results log.** If this fails, stop — everything below is irreversible.

### C.1 — ship the registry (do this before anything else)

The knight has never had the three-tier registry; its curated seed is still the
round-2 flat file. Confirm the defect, then fix it:

```bash
# on the knight, BEFORE shipping — this is the bug, visible:
python3 -c "import json;d=json.load(open('$HOME/L5GN/.intel_sync/project_registry.json'));print('programs:',d['programs'])"
# expect: programs: []
```

```powershell
# on the gaming rig
scp config\project_registry.json l5gn-castle:L5GN-Tools/config/project_registry.json
```

**Passing:** the sha256 on the knight matches
`a8416e0bc4a87d138220bfa14563113c47a828daf945835f45950dccc982e4f5`
(`sha256sum ~/L5GN-Tools/config/project_registry.json`).

### C.2 — the reset itself

Run the three statements from the report §Task C **in order**. Order is not
cosmetic: clearing `threads` before deleting `projects` is what stops the FK
refusing.

**Passing, checked immediately after:**

```sql
SELECT COUNT(*) FROM threads WHERE project_link IS NOT NULL;   -- 0
SELECT COUNT(*) FROM projects;                                 -- 16
SELECT COUNT(*) FROM projects WHERE source_system_id IS NOT NULL;  -- 9
SELECT DISTINCT project FROM link_evidence
  WHERE project NOT IN (SELECT project_id FROM projects);      -- no rows
```

The generation census now returns **two buckets, not three**: 9 Claude uuids and
7 registry ids.

**The third statement is not in the brief and is the one to watch.** Without
re-keying `link_evidence`, 332 of 657 evidence rows still name folder paths, and
the next relink run re-creates the nine rows you just deleted. If you skip it,
expect the census to return to three buckets after C.3 — that failure is the proof
the step is needed.

### C.3 — rebuild and dry-run

```bash
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases
.venv/bin/python chronicler/pipeline/build_registry.py
.venv/bin/python chronicler/pipeline/relink.py            # DRY-RUN, the default
```

**Passing (build):** the report opens with `PROGRAM  l5gn-os` and
`PROGRAM  wizforge-analytics`. If it still says `STANDALONE (no program)` for
everything, the scp did not land. `UNMAPPED Claude project names` should be
shorter than the ten in the last run.

**Passing (dry-run):** every SUGGESTIONS line carries a
`[L5GN OS > Citadel MicroIDE > smelt-gateway]` breadcrumb; ambiguities are few and
genuinely ambiguous; the auto-links look right to you. **This table is the
GO/NO-GO.** Answer one question: *would I trust this?*

### C.4 — STOP

Do **not** run `--apply`. That was skipped last pass and is the whole reason
dry-run is the default.

**Failing at any point:** you have the backup from C.0. Restore it rather than
patching forward.

---

## F — lineage collapse

**Command:**

```bash
sqlite3 -readonly $VAULT "SELECT MIN(created_at), MAX(created_at), COUNT(*)
  FROM review_queue WHERE type='link_ambiguous' AND status='pending';"
sqlite3 -readonly $VAULT "SELECT item_id, created_at, note FROM review_queue
  WHERE type='link_ambiguous' AND note LIKE '%crystal-spire%' LIMIT 5;"
```

**Passing:** the rows predate round 3. That confirms the report's answer — the
review UI renders *stored* `note` text and never recomputes candidates, so the
rivalry you saw in the UAT was frozen debris, not `collapse_lineage` failing.

**If they are recent**, the answer changes and `collapse_lineage` genuinely is not
firing on real data. Either way, the second half of the answer stands on its own:
the knight's registry has `programs: []` and every curated project has no repos,
so there has been no hierarchy for the rule to collapse.

**Consider ruling on this:** if those 212 pending ambiguity rows are stale, the
reset should clear them too. The brief scopes the reset to two columns, so this is
outside it and needs your call.

---

## G — the registry path

**Command:**

```bash
ssh l5gn-castle 'cd ~/L5GN-Tools && echo "$CHRONICLER_REGISTRY_PATH" &&
  .venv/bin/python -c "import sys;sys.path.insert(0,\"chronicler/pipeline\");
  import relink;print(relink.REGISTRY_PATH)"'
```

**Passing** — in the sense of "the defect is confirmed, not fixed": the two paths
printed are **different**.

```
/home/l5gn/vault/project_registry.json                  <- what the review endpoint validates against
/home/l5gn/L5GN/.intel_sync/project_registry.json       <- what relink links against
```

relink and the endpoint disagree about what the registry is. **No fix was built**
(scope was A and B); the proposed one-function fix is in the report §Task G. Until
it lands, a workaround: point `CHRONICLER_REGISTRY_PATH` at
`~/L5GN/.intel_sync/project_registry.json` so both halves read the file relink
actually uses.

---

## D and E — not built

Both were descoped when the session scope was agreed as "A and B, done properly".

**Read the report's Finding 3 before building D.** The briefed invariant — refuse
to apply when `projects` holds a foreign row — would be correct and permanently
red, because relink creates the foreign row it would then refuse. The invariant
belongs one step earlier, at candidate scoring: refuse a candidate whose key is
not a link target. Same loud failure, at the point the bad identity enters.

**E has a clean baseline waiting.** The rewritten registry adds 24 targets and
remaps **zero** ids, so the first `--allow-id-remap` comparison has nothing
spurious to report.
