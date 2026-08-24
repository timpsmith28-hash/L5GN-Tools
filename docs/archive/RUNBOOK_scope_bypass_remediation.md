# Runbook — remediate the scanner-scope-bypass deposits on the knight

**For:** `COWORK_BRIEF_scanner_scope_bypass.md` Task 3, once the code fix (Task 1:
`file_census` + `workspace_scanner` now consult `Scope`; Task 2: the registry-
iterating tester) has landed and `verify.py` is GREEN on the gaming rig.

**Precondition already met:** DECISIONS **0029** — *"A deposit found to carry
more than its contract is replaced, never edited"* — is ratified (`Status:
accepted`). This runbook executes that ruling; it does not re-argue it.

Every step is marked **▸ GAMING** (`LucasGoonPC`), **▸ WORK** (`10280L`), or
**▸ KNIGHT** (`l5gn-castle`). Rig commands are PowerShell; knight commands are
bash over SSH — same convention as `RUNBOOK_refresh_and_deposit.md`.

**No work-estate path leaves any machine in a report, commit message or chat
thread.** Every measurement below is a *count*, never a path.

---

## What's being fixed, in one line

Two scanners (`file_census`, `workspace_scanner`) never consulted the shared
`Scope` guard, so every deposit taken after the scope-discipline commit
(`6d09eb3`) still carries thousands of paths from inside `raw_claude_files` /
`raw_gemini_files` / similar data directories. Exactly two bundles are affected
— `estates/personal/estate.json` and `estates/work/estate.json`, both from one
commit (`1951cfe`, 2026-07-25) — and neither estate has deposited since. This is
not a long history to clean; it is two files and two history snapshots.

---

## Step 0 ▸ GAMING — confirm the fix is on this machine

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
git log --oneline -1                 # the scanner-scope-bypass fix commit
python verify.py                     # GREEN, tester_scanner_scope included
git push origin main                 # publish, so WORK and KNIGHT can pull it
```

**Verify:** `verify: GREEN`, and the log names `tester_scanner_scope` passing.

---

## Step 1 ▸ KNIGHT — measure the exposure that's already landed (baseline)

Do this **before** touching anything, so you have a real before/after. Counts
only — this prints numbers, never paths.

```bash
ssh l5gn-castle
python3 - <<'EOF'
import json, pathlib

NAMES = ("raw_claude_files", "raw_gemini_files", "chat_threads",
         "vault_staging", "Takeout", "Chronicler_Backup")

for estate in ("personal", "work"):
    base = pathlib.Path.home() / "vault" / "estates" / estate
    for label, p in (("estate.json", base / "estate.json"),):
        if not p.exists():
            print(f"{estate}/{label}: MISSING"); continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        counts = {n: text.count(n) for n in NAMES if text.count(n)}
        print(f"{estate}/{label}: {sum(counts.values())} total  {counts}")
    hist = base / "history"
    if hist.exists():
        for snap in sorted(hist.glob("estate-*.json")):
            text = snap.read_text(encoding="utf-8", errors="ignore")
            counts = {n: text.count(n) for n in NAMES if text.count(n)}
            print(f"{estate}/history/{snap.name}: {sum(counts.values())} total  {counts}")
EOF
```

**Record the numbers** (not the paths) in the results log. They should be in the
same ballpark as the brief's own measurement (9,159 / 2,328 substring matches).
If `Chronicler_Backup` shows a nonzero count that is **not** already nested
under a `raw_*` / `*_files` ancestor segment, flag it in the report as a possible
gap in `DATA_DIR_NAMES` — don't assume the fix covers a name it was never told
about.

---

## Step 2 ▸ GAMING — rebuild the personal estate on the fixed producer

**Use `--fresh`, not a plain `build`.** `run.py build` defaults to
`resume=True`, which reuses each scanner's per-project cache file at
`data/<scanner_name>/<project>.json` **if one already exists on disk** — there
is no check on whether the scanner's code changed since that cache was
written, and the `scanned <name>` log line prints identically whether it
actually re-ran the scanner or just read the stale cache back. A rig with any
prior build will silently keep pre-fix `file_census`/`workspace_scanner`
output unless the cache is bypassed. This is exactly what happened on the
gaming rig during this round's own verification: the first `build` after the
fix looked clean by eye but still carried real data-dir paths from four
projects' stale caches, found by re-running the leak check below.

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py config          # confirm host, role: producer, estate: personal
python run.py build --fresh
```

**Verify locally before depositing anything** — the same substring check, run
against the fresh local `data/estate.json`:

```powershell
python -c "import pathlib; t=pathlib.Path('data/estate.json').read_text(encoding='utf-8'); names=['raw_claude_files','raw_gemini_files','chat_threads','vault_staging','Takeout']; c={n:t.count(n) for n in names if t.count(n)}; print('total', sum(c.values()), c)"
```

**Expect `total 0`.** If it isn't zero, stop — do not deposit a bundle that
fails its own measurement. Re-check `verify.py`, that the build actually
picked up the fixed scanners (`git log --oneline -1` should show the fix
commit), and that `--fresh` was actually passed (a plain `build` will look
identical in its output either way — the cache hit is silent).

For a sharper check than the whole-file substring count — one that only looks
at `file_census`/`workspace_scanner` path fields via `is_data_dir_name`,
rather than counting every mention anywhere (including this toolkit's own
docs/tests, if it's configured as a self-scanned project on this rig) — see
the report's precise leak-check script.

---

## Step 3 ▸ WORK — rebuild the work estate on the fixed producer

```powershell
cd D:\Work\Github\L5GN-Tools
git pull origin main
python verify.py               # GREEN, same fix commit as gaming rig
python run.py config            # confirm host, role: producer, estate: work
python run.py build --fresh     # --fresh: this rig's data/ cache predates the fix too
python -c "import pathlib; t=pathlib.Path('data/estate.json').read_text(encoding='utf-8'); names=['raw_claude_files','raw_gemini_files','chat_threads','vault_staging','Takeout']; c={n:t.count(n) for n in names if t.count(n)}; print('total', sum(c.values()), c)"
```

**Expect `total 0`** here too, for the same reason as Step 2.

---

## Step 4 ▸ KNIGHT — remove the superseded bundles, per DECISIONS 0029

**Do this before the fresh deposits land**, so there is no window where a stale
and a fresh copy coexist under the same name. 0029 is explicit: *removed, never
edited, never partially scrubbed* — this is a delete, not a diff.

```bash
ssh l5gn-castle
# Personal estate: the landed bundle and its one history snapshot.
rm -f  ~/vault/estates/personal/estate.json
rm -f  ~/vault/estates/personal/deposit_manifest.json
rm -f  ~/vault/estates/personal/history/estate-2026-07-25.json

# Work estate: same shape.
rm -f  ~/vault/estates/work/estate.json
rm -f  ~/vault/estates/work/deposit_manifest.json
rm -f  ~/vault/estates/work/history/estate-2026-07-25.json

ls -la ~/vault/estates/personal/ ~/vault/estates/personal/history/ 2>/dev/null
ls -la ~/vault/estates/work/     ~/vault/estates/work/history/     2>/dev/null
```

**Verify:** both `history/` directories are empty (or absent) and neither
estate has a live `estate.json`. `estate_diff` / `drift` reports under
`~/vault/estates/<estate>/reports/` are pure derivatives of these — they will
regenerate clean on the next `consume`, so there is nothing to hand-delete
there, but don't be surprised if `consume` reports `insufficient_history` for
one pass (expected: the history series just lost its only snapshot).

---

## Step 5 ▸ WORK, then ▸ GAMING — deposit the fresh bundles

Same order and same stage-then-push discipline as
`RUNBOOK_refresh_and_deposit.md` Step 5.

**▸ WORK:**

```powershell
python run.py deposit           # stage only; prints the exact push command
dir data\outbox\work            # estate.json + deposit_manifest.json, nothing else
python run.py deposit --push
```

**▸ GAMING:**

```powershell
python run.py deposit --push
```

**Verify (each):** output ends `pushed : OK -> l5gn-castle:vault/estates/<estate>/`.

**Wall check (knight):**

```bash
ls -la ~/vault/estates/work/ ~/vault/estates/personal/
```

Both carry a fresh `estate.json` + `deposit_manifest.json` dated today. MCF
projects must appear only under `work/` — same check as always.

---

## Step 6 ▸ KNIGHT — consume, then confirm clean by the same measurement

```bash
cd ~/L5GN-Tools
python3 run.py consume
```

**Verify:** both `work` and `personal` report `manifest_verified: true`. A
first pass after a history wipe may show `estate_diff: insufficient_history` —
that's correct (Step 4 intentionally emptied the series), not a fault.

**Now re-run Step 1's exact measurement command** against the freshly landed
files. **Expect `total 0`, or no output at all, for every estate and every
history snapshot.** A remediation nobody re-measures is a claim, not a fix —
this is the check that turns it into one.

---

## Step 7 ▸ record it

- Before/after counts (numbers only) per deposit, in
  `docs/COWORK_REPORT_scanner_scope_bypass.md`.
- The commit that fixed the producer, on both rigs.
- Confirmation that `history/` was emptied and rebuilt, not scrubbed in place.
- A results-log entry with a `uat:` stamp (per `docs/README.md` §3) — no
  `gate=` field, per the brief.
- One acknowledgement line on
  `docs/investigation/2026-08-02_knight-roles_claude_2-response.md` (K3/K4),
  per `docs/README.md` §4, once this lands.

## If it goes wrong

Nothing here is destructive to the *producers* — `data/estate.json` on the
gaming rig and work rig are rebuilt from the live repos at any time by
`run.py build`. The only one-way step is Step 4's deletion on the knight, and
that is exactly what DECISIONS 0029 rules should happen to a deposit found to
violate its own contract — there is no "restore the tainted copy" path,
by design. If Step 5's deposit fails partway, re-run `deposit --push` for that
estate before running `consume` — don't consume a partial bundle.
