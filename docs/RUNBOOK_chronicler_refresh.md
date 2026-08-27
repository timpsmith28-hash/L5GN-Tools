# Runbook — refresh the Chronicler vault on the gaming rig

**Scope: `LucasGoonPC`, the personal estate, the dev vault at
`C:\Users\timps\Documents\chronicler_dev\chronicler.db`.** This is *not* the
cross-machine pass — that is `RUNBOOK_refresh_and_deposit.md`, which rebuilds the
vault **on the knight** from shipped inputs. This one refreshes the vault this rig
declares as its own, which is the one every scanner on this rig reads.

**Written 2026-08-27** from the measurement in
`docs/investigation/2026-08-27_intent-coverage-remeasure_claude_2-response.md`.
Every path and flag below was read out of the code, not remembered. Nothing here
was executed: the sandbox this was drafted in resolves `socket.gethostname()` to
`claude`, which is in neither `machines.json` nor `local.json`, so
`python run.py config` reports `NOT CONFIGURED` and the toolkit correctly refuses
to run there. **Every command below runs in PowerShell on `LucasGoonPC`.**

---

## What is actually wrong, in one paragraph

The vault's newest row is `2026-07-27T23:52:14Z`. Three separate things stalled,
and they need different fixes:

1. **`relink` last ran at `2026-07-27T21:48:20Z`. The local transcripts were
   ingested at `2026-07-28 00:36`.** The linker has therefore **never seen** the
   71 local-transcript threads — they were written into the vault about three
   hours after the last link pass. This is why they sit at 0.0% coverage and why
   there is no `L5GN-Tools` row in `projects`: `relink.upsert_project()` mints
   that row on demand when a thread wins a link to a registry id, and no thread
   has ever won one. **The registry is not the problem** — both
   `config/project_registry.json` and the generated
   `chronicler_dev/project_registry.json` already carry `id: l5gn-tools` with its
   aliases. Nothing has run since.
2. **The Claude export is stale.** `conversations.json` is dated 2026-07-27 and
   its newest conversation is 2026-07-17. Only a fresh export from the account
   fixes that, and nothing in this estate can trigger or notice it.
3. **The local transcript store stopped growing on 2026-08-14**, because the work
   moved to remote Cowork sessions that write no local transcript. Steps 4 and 5
   recover what is still on disk; nothing recovers what was never written there.
   That gap is a decision, not a command — see §8.

**The ordering rule, and it is the opposite of the obvious one.** Ingesting new
local transcripts *without* a link pass makes the coverage figure worse, because
every local thread lands unlinkable. **Ingest, then link, in the same sitting.**
Never stop between steps 5 and 6.

---

## Step 0 — Preconditions. Two checks, both must pass before anything writes

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py config
```

**Expect:** host `LucasGoonPC`, `role: producer`, `estate: personal`,
`vault: C:/Users/timps/Documents/chronicler_dev/chronicler.db`. Anything else and
stop — a wrong host resolution is how a run writes into the wrong estate.

Then the one that will bite silently if you skip it. **PowerShell has no
heredoc**, so the probes are committed as scripts under `data/` (gitignored
wholesale) rather than pasted inline:

```powershell
python data\_vault_status.py
```

**Section 2 prints the resolved default registry path and whether it exists.**
On `LucasGoonPC` it exists **and is a trap** -- see the amendment below. `resolve_registry_path()`
defaults to
`CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"`,
which from `Documents\chronicler_dev` resolves to
`C:\Users\timps\L5GN\.intel_sync\project_registry.json` — **a path that does not
exist on this rig.** This is the fourth instance of the folder-walk defect that
`COWORK_REPORT_intent_evidence.md` Task B flagged and that is still open.

It matters because `run_pipeline.py`'s `has_registry()` gates the relink stage on
that file existing. If it is absent the stage prints
`[relink] skipped (no input available)` and the chain **carries on green having
done no linking at all.** That is the silent no-op this whole round has been
chasing. So set the path explicitly, for this shell, before anything else:

```powershell
$env:CHRONICLER_HOME     = "C:\Users\timps\Documents\chronicler_dev"
$env:CHRONICLER_DB_PATH  = "C:\Users\timps\Documents\chronicler_dev\chronicler.db"
$env:CHRONICLER_REGISTRY_PATH = "C:\Users\timps\Documents\chronicler_dev\project_registry.json"
```

Setting `CHRONICLER_REGISTRY_PATH` is what `db.py`'s own docstring says the knob
is for — *"the knob to set on a deploy target so the writer (build_registry) and
every reader point at one file deterministically."* Use it here for the same
reason. **Keep this one shell open for the whole run**; the variables do not
persist.

### The phantom registry — check before every run

**Amended 2026-08-27, second finding.** `resolve_registry_path()` defaults to
`CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"`,
which from `Documents\chronicler_dev` resolves to
`C:\Users\timps\L5GN\.intel_sync\project_registry.json`. That file **exists on
this rig**, 521,208 bytes, dated **2026-08-01** — created by an earlier
`build_registry` run whose `write_json_atomic` did `mkdir(parents=True)` at the
wrong resolution, exactly as `COWORK_REPORT_intent_evidence.md` Task B predicted.

It is a **silently-preferred stale fork**. Any pipeline run on this rig without
`CHRONICLER_REGISTRY_PATH` set reads a 26-day-old registry and links against it
with full confidence. That is worse than the absent-registry case, which at least
makes `has_registry()` false and prints a visible `[relink] skipped`.

Nothing has consumed it: the vault's `link_evidence` is stamped
`2026-07-27T21:48:20Z`, before the file existed, and no `run.py ingest` has run
since. **Move it aside rather than deleting it** — it is evidence of what a run
would have used — and confirm the default no longer resolves:

```powershell
Move-Item C:\Users\timps\L5GN C:\Users\timps\L5GN_stale_phantom_20260827
Test-Path C:\Users\timps\L5GN\.intel_sync        # must now be False
```

This does not make the default *correct*, only *loud*: a future run without the
env var now skips relink visibly instead of linking against stale data. The real
fix is `resolve_registry_path()` itself and is still not done here.

---

### The gate must be run in a *different* shell

**`verify.py` is not hermetic against the `CHRONICLER_*` environment.** Measured
2026-08-27: with the three variables above set, `tester_census` reports 7 issues
and `tester_review_preflight` 3, in both cases because a fixture's injected
machine dict is overridden by the real `CHRONICLER_DB_PATH` / `CHRONICLER_HOME`.
`tester_census` pops `CHRONICLER_HOME` but not `CHRONICLER_DB_PATH`, and the pop
does not cover every assertion. Both testers' docstrings claim hermeticity
("*No real machine config is read and nothing outside the temp dir is touched*")
and both are wrong about it. Reproduced identically on a second machine with the
same variables exported, so it is the environment and not this rig.

**So: run the refresh in the Step 0 shell, and run `verify.py` in a fresh one
with none of the three set.** The same applies to committing — `.githooks/pre-commit`
runs `verify.py`, so a commit made from the Step 0 shell goes red for reasons
that have nothing to do with the commit.

This cuts the other way too and that is the worse half: an exported
`CHRONICLER_DB_PATH` could equally make a fixture-based tester *pass* against
the real vault. Nothing has been shown to do that; nothing checks that it
cannot. Fixing it is a small change to two testers and is **not** done by this
runbook.

---

---

## Step 1 — Back up the vault, and read what it says about off-box

```powershell
python run.py backup
```

**Expect:** `backup: snapshot -> ...\chronicler_dev\backups\chronicler-<UTC>.db`,
then a `kept (N)` line. It is a `VACUUM INTO` snapshot, safe on a live DB.

**Read the last line carefully.** `config/local.json` for this host has a
`pull_backup` block but **no `backup_target`**, so this will print
`off-box: no 'backup_target' configured ... snapshot is LOCAL ONLY.` That is
honest and it is also the state DECISIONS 0005/0006 exist about. Before running
anything that writes, either accept a local-only snapshot or copy it somewhere
off this disk by hand. **Do not proceed on a failed backup** — `run.py ingest`
would abort on the same condition anyway, deliberately.

---

## Step 2 — Fresh Claude export  *(manual; the long pole)*

Nothing automates this. Request the export from the Claude account, wait for the
mail, download the zip, then place its `conversations.json` where
`normalize_claude.py` looks — `RAW_DIR / "conversations.json"`, which under this
rig's `CHRONICLER_HOME` is:

```
C:\Users\timps\Documents\chronicler_dev\chat_threads\raw_claude_files\conversations.json
```

Move the current one aside first rather than overwriting it — the 2026-07-27 file
is the only copy of that capture:

```powershell
$raw = "C:\Users\timps\Documents\chronicler_dev\chat_threads\raw_claude_files"
Move-Item "$raw\conversations.json" "$raw\conversations-20260727.json"
# then drop the new conversations.json (and its projects\ folder) into $raw
```

**Verify before ingesting:**

```powershell
python data\_export_check.py
```

It reports both sources and says, per source, whether what is on disk is
actually newer than what the vault holds. **Expect `>> newer than the vault`**
for Claude. If it prints `>> NOT NEWER. This is the same export.` you have
re-downloaded the 2026-07-27 capture — stop; the rest of the run will do nothing
new on the Claude side. (It compares `updated_at` against the vault's newest
`updated_at` of 2026-07-20, same field both sides.)

**If you skip this step**, everything below still works and still helps — it just
cannot recover the Claude-account half of the August gap.

---

## Step 3 — Fresh Gemini Takeout  *(manual, optional this round)*

Same shape: a new Takeout drops into the pipeline's takeout input
(`normalize_gemini_personal.DEFAULT_INPUT`, under
`chat_threads\raw_gemini_files\Takeout`). Gemini-personal is 1,062 threads at 8.1%
and 844 of them are two-message fragments; refreshing it adds material but does
not fix anything measured this round. **Reasonable to skip and do on its own.**

---

> **Amended 2026-08-27, after the first real run.** Step 4 failed with
> `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.
> `ingest_local_transcripts` wrote `threads.project_link` for a CLI session
> whose `cwd` matched the registry without creating the `projects` row it
> references. It had never fired before because the registry could not be
> resolved on this rig; Step 0's `CHRONICLER_REGISTRY_PATH` is what enabled the
> attribution path for the first time. Fixed by mirroring
> `relink.upsert_project()`, with the tester's fixture strengthened to carry the
> `projects` table, the real foreign key and `foreign_keys=ON` so it can fail on
> this class at all. **Run `python verify.py` once before Step 4.** Draft:
> `data/git_warden/ingest_fk_projects_row-1.msg`.

## Step 4 — Re-ingest the local transcripts: dry run first

`ingest_local_transcripts.py` is **not** a `run_pipeline.py` stage — it is a
separate program and must be run by hand, before the chain.

**Run every pipeline script from the repo root, not by `cd`-ing into
`chronicler/pipeline`.** Python puts the *script's own* directory on `sys.path[0]`
either way, and no pipeline script reads the working directory, so both work --
but `--out` and any other relative argument are resolved against the shell's cwd,
and the `cd ..\..` dance is the thing that goes wrong at 11pm. Verified
2026-08-27: no pipeline module resolves a path from `Path(".")` or `os.getcwd()`.

```powershell
python chronicler\pipeline\ingest_local_transcripts.py
```

Dry-run is its default; `--apply` is what writes. **Expect** it to report roughly
**23 sessions the vault does not hold** (17 of them from August), forming about 19
conversations. That figure is measured from the `2026-08-27_164914` snapshot in
`C:\Users\timps\backups\claude_migration`; the live store should match or slightly
exceed it.

**Stop if** it reports zero new sessions — that means it is reading a different
store than the one the backup captures, and the path in `local.json`'s
`cowork_transcripts_home` needs checking before anything is written.

---

## Step 5 — Apply the ingest

```powershell
python chronicler\pipeline\ingest_local_transcripts.py --apply
```

**Verify:**

```powershell
python data\_vault_status.py
```

**Expect** the local thread count to rise from **71** toward **94**, and the
newest `created_at` to move from 2026-07-27 into August.

> **Do not stop here.** At this point the figure is at its worst — new
> unlinkable threads in the denominator, no new links. Steps 6 and 7 are the
> other half of the same act.

---

## Step 6 — Rebuild the registry, then dry-run the linker

```powershell
python chronicler\pipeline\build_registry.py --report-aliases   # inspect; writes nothing
python chronicler\pipeline\build_registry.py                    # write it
```

**Verify** it wrote to the path you set in Step 0, not to a freshly-created
`C:\Users\timps\L5GN\.intel_sync\` — `write_json_atomic` does
`mkdir(parents=True)`, so a wrong resolution *creates* a plausible-looking folder
rather than failing. Check with `Test-Path`:

```powershell
Test-Path C:\Users\timps\L5GN\.intel_sync   # must be False
(Get-Item $env:CHRONICLER_REGISTRY_PATH).LastWriteTime   # must be just now
```

Then the linker, dry, with its output kept:

```powershell
python chronicler\pipeline\relink.py --out data\relink_dryrun_20260827.txt
```

`--apply` is what writes; dry-run is the default. **Read that file before going
on.** What to look for:

- Does any candidate resolve to **`l5gn-tools`**? That is the question this whole
  round turns on. If yes, the missing `projects` row mints itself on apply and
  the estate's own build threads become linkable for the first time.
- The registry flags `l5gn-tools` as **`low_signal_body: true`**, which demotes a
  body-only alias hit from 0.60 to 0.15. **Title matches are unaffected.** So
  expect threads *titled* "L5GN Tools ..." to win and threads that merely mention
  the toolkit in passing to lose — which is the flag working as designed, not a
  failure.
- Watch `time_plausibility`. `relink` computes `adjusted = score ×
  time_plausibility` and hard-zeroes any thread more than 14 days before a
  project's first commit. Anything whose registry `first_seen` is later than its
  conversations will score zero regardless of evidence.

---

## Step 7 — Run the chain (this is where relink applies)

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py ingest --skip-intake
```

`--skip-intake` because mesh mode is stood down (**0036**); without it the run
prints a skip notice and continues anyway. The chain is
`claude → takeout → md-transcript → reconcile → group → suggest-close →
substantive → relink (--apply) → render`, and `run.py ingest` takes its own
pre-flight backup first.

**Two stages matter most here:**

- **`[set_substantive]`** — this clears the finding that `threads.substantive` is
  `NULL` for all 71 local rows. After this the column and the message counts agree
  again.
- **`[relink]`** — must **not** print `skipped (no input available)`. If it does,
  `CHRONICLER_REGISTRY_PATH` did not survive into the subprocess; go back to
  Step 0. A green chain with a skipped relink is the exact silent failure this
  runbook exists to prevent.

**Stop if** any stage prints `FAILED (exit N). Stopping the chain.` — the chain
halts by design; do not re-run past it without reading the tail it prints.

---

## Step 8 — Re-measure, and compare against a real baseline

The whole point. Same probe as Step 0, same definition as the 2026-08-27
measurement, so the numbers are directly comparable — it carries the baseline
inline and prints the delta:

```powershell
python data\_vault_status.py
```

**Report both ratios.** `INTENT figure` is §2's own definition and the one
comparable to 7.85%. `any project link` is the honest picture of what the vault
can actually address, and it will move first. Section 5 of the probe answers the
question this round turned on: whether an `L5GN-Tools` row exists yet.

**A worse number here is a result, not a failure of the run** — INTENT §6. Write
down what it says either way.

---

## What this runbook cannot fix, named rather than hidden

1. **The 62 Cowork conversations carry an exact project id that nothing reads.**
   Each `local_<uuid>.json` sidecar holds `userSelectedFolders`; 44 of 62 name a
   specific project directory and 37 name `L5GN-Tools`.
   `ingest_local_transcripts` ruling 2 correctly observes that the *session's*
   `cwd` is just its outputs dir, and wrongly concludes no signal exists — the
   *conversation's* sidecar one level up names the repo. That is **0038**'s
   distinction and **0040**'s "join of record", and reading it is a **code
   change**, not a command. It would take substantive threads with a project link
   from 27 to roughly 65 — at `exact` confidence, which INTENT's numerator does
   not count, so the headline figure would not move. **That is a brief, and it
   should probably be the next one.**
2. **Nothing after 2026-08-14 exists locally in any form.** Remote Cowork sessions
   write no local transcript. No command recovers them. Whether that material is
   worth capturing at all, and how, is a decision — and if the answer is "no",
   then INTENT §2's thesis is being measured against a corpus that structurally
   cannot include most of the estate's current work, which is worth saying out
   loud before any more effort goes into coverage.
3. **The staleness is not detected.** Nothing in the estate goes red when a store
   stops growing. **0050** already rules how a source declares its own freshness;
   the Claude export and the local store are two sources that declare nothing.
   That is a small feed, not a feature — and INTENT §6 is explicit that none of
   this is a reason to add features.
5. **The two probes this runbook depends on are not tracked.**
   `data/_vault_status.py` and `data/_export_check.py` live under `data/`, which
   `CLAUDE.md` says is *"gitignored wholesale; never source"* — so this runbook
   cites two scripts that do not travel with the repo and will not exist after a
   fresh clone. That is a defect introduced by this round, named rather than
   quietly fixed: they are diagnostics, so either they move to a tracked path
   (`tests/` is the nearest existing home for hermetic read-only checks) or the
   runbook inlines their queries. Choosing between those is a small decision and
   is not made here.

4. **`resolve_registry_path()` still resolves wrong on this rig.** Step 0 works
   around it with an env var every time. The fix is one line and belongs with the
   other three folder-walk instances `COWORK_REPORT_intent_evidence.md` Task B
   left open.

---

## Order at a glance

```
0. config + set CHRONICLER_HOME / _DB_PATH / _REGISTRY_PATH   (one shell, keep it)
1. run.py backup                       -- read the off-box line
2. fresh conversations.json            -- manual, optional, the long pole
3. fresh Takeout                       -- manual, optional, skippable
4. ingest_local_transcripts.py         -- dry run, expect ~23 new sessions
5. ingest_local_transcripts.py --apply -- do NOT stop here
6. build_registry.py, then relink.py --out <file>   -- read the dry run
7. run.py ingest --skip-intake         -- [relink] must not say "skipped"
8. re-measure, report both ratios
```
