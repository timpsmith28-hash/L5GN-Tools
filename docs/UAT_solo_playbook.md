# Walk-sheet — Task A, the solo loop on the rig (`LucasGoonPC`)

**Pairs with:** `docs/COWORK_BRIEF_solo_playbook.md`. This is the transcript
sheet for **Task A only** — walk the full producer+consumer loop on the
gaming rig against a throwaway vault, in Windows form, and paste back what
each command actually printed. I'll write `docs/SOLO_PLAYBOOK.md` (Task B)
and propose any Task C code changes from what comes back here — nothing is
written from guesswork.

**Rules baked into this sheet, per the brief:**
- Every command below is real — copy/paste it, don't paraphrase it.
- For each step, paste back: the command, the actual output (or the error),
  and whether it needed a workaround.
- If a step can't be run (missing input, blocked), say so and stop there —
  that's a valid result, not a failure of the walk.
- Nothing here touches `~/vault` on the knight or uses `--push`. If any
  command's output surprises you by mentioning the knight or a push target,
  stop and flag it before continuing.

---

## 0. Before you start — one thing I need from you

Step 9 (`run.py ingest`) rebuilds a vault from **raw chat export inputs**
(Claude/Gemini export zips). Do you already have export zips sitting
somewhere on this rig from earlier Chronicler work (e.g. a `Chronicler/`
project folder with `raw_claude_files/`, `zip_downloads/`, etc. — see
`KNIGHT_PLAYBOOK.md` §2)?

- **If yes:** note the path, we'll point the throwaway `CHRONICLER_HOME`'s
  intake at a **copy** of one small export zip (not the whole set — this is
  a throwaway vault, not a real rebuild).
- **If no:** tell me before you reach step 9 and we'll mark `ingest` onward
  as a logged gap in the transcript rather than fake it — per the brief,
  "a step nobody executed goes in as a marked gap, not as an instruction."

---

## 1. Confirm the rig — ▸ DEV

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
git log --oneline -1
python -c "import socket; print(socket.gethostname())"
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.prefix)"
python verify.py
```

Paste back: the commit, the hostname (confirm it's `LucasGoonPC` — if not,
every config key below needs to use what actually printed), the venv prefix
path, and the verify line (`verify: GREEN` expected — if red, stop and tell
me what failed before continuing).

---

## 2. Set up the throwaway `CHRONICLER_HOME`

```powershell
mkdir C:\Users\timps\Documents\chronicler_dev
```

This directory is the whole isolation guarantee for this walk — nothing
under it is the knight's vault, and it is never a path `deposit --push`
reaches. Confirm it's empty before continuing.

---

## 3. Add the solo config entry — ▸ DEV

Open `config\local.json` in the repo. It should already have a
`LucasGoonPC` entry (role: producer, estate: personal, `push_target`
pointing at the knight). **Add** the consumer-side keys to that same entry
— don't replace what's there, extend it:

```json
{
  "LucasGoonPC": {
    "role": "producer",
    "estate": "personal",
    "roots": [
      {"path": "C:/Users/timps/Documents/GitHub", "scope": "l5gn"}
    ],
    "push_target": "l5gn-castle:vault/estates",
    "push_transport": "scp",

    "vault": "C:/Users/timps/Documents/chronicler_dev/chronicler.db",
    "estates_dir": "C:/Users/timps/Documents/GitHub/L5GN-Tools/data/outbox",
    "chronicler_home": "C:/Users/timps/Documents/chronicler_dev"
  }
}
```

(Keep your real `roots` — copy them from whatever's actually in the file
now; the block above is illustrative, not a replacement.)

**This is the hypothesis under test.** `estates_dir` points at this rig's
**own** `data\outbox`, not a second machine — the idea from the brief's
grounding section is that `consume` can read a solo box's own staged
deposit in place, no push, no second host, no code change. Note if that
does or doesn't hold.

**Verify:**

```powershell
python run.py config
```

Paste back the full output. Check for: hostname matches with no
`(no matching entry -> using default)`; `role: producer`; `estate:
personal`; roots listed with no `(MISSING)`; and the new `vault` /
`estates_dir` / `chronicler_home` lines all present.

---

## 4. The loop — run each in order, paste back real output

For every step: **command run → output → workaround needed? (y/n, what) →
did it lie?** ("lie" = reported success while doing nothing, or failed with
a message that names the wrong cause — see the brief's sharp edges 1 and 2
for what this looks like).

### 4a. `census`

```powershell
python run.py census
```

Expected, per the grounding notes: with `role: producer`, this censuses
`roots` only (producer domain) — it does **not** also check the
`chronicler_home`/`vault` side, because role branches to one domain or the
other, not both. **Confirm that's what happens** — if census instead errors
or silently does something with the consumer keys, that's a real finding
for Task C, not what we expect.

### 4b. `build`

```powershell
python run.py build
```

**Verify:**

```powershell
python -c "import json; d=json.load(open('data/estate.json')); print(len(d['projects'])); print(d['roots'])"
```

Should list your real projects with non-null scope.

### 4c. `deposit` (stage only — no `--push`)

```powershell
python run.py deposit
dir data\outbox\personal
```

Confirm it stages to `data\outbox\personal\` and prints the push command
without running it (don't run `--push` for this walk — see the "Rules"
note above).

### 4d. `consume` — the hypothesis check

```powershell
python run.py consume
```

This is the step that answers the brief's central question: does `consume`
find and read the deposit this same box just staged in step 4c, using
`estates_dir` pointed at its own `data\outbox`? Paste back the full output
— specifically whether it lists a `personal` estate and what
`manifest_verified` says.

### 4e. `ingest` — only if you have an export zip (see §0)

If you have one: copy a **single small** export zip into
`chronicler_dev\chat_threads\zip_downloads\` (create that folder first),
then:

```powershell
python run.py ingest --skip-backup
```

`--skip-backup` because there's nothing to back up yet on a fresh throwaway
vault. If this errors on a missing dependency (`ingest` needs the
`[chronicler]` extra — `pip install -e ".[chronicler]"` first if so), note
that as a prerequisite gap for the playbook, not a code defect.

If you don't have an export zip: **stop here**, tell me, and skip to §4f
noting steps 4e–4l as not walked.

### 4f. `finalize_db.py --apply` — sharp edge 1

```powershell
python chronicler\pipeline\finalize_db.py --apply
```

Run this **before** the evidence producers below. Per the brief's sharp
edge 1: skipping this step is what makes `consume` report a confusing
`schema_mismatch` with no obvious cause. Paste back the output either way —
if you deliberately want to see that failure mode once for the
troubleshooting section, run `consume` again *before* this step and paste
that error too, then come back and run this, then move on.

### 4g. `build_registry.py`

```powershell
python chronicler\pipeline\build_registry.py --report-aliases
```

This is also where sharp edge 3 (gitignored `project_registry.json`, no
registry from `git pull`) and sharp edge 4 (`seed_suppress`) apply if this
is a genuinely fresh `CHRONICLER_HOME` with no registry file yet — note
whether it needed seeding.

### 4h. `build_inventory.py`

```powershell
python chronicler\pipeline\build_inventory.py --force
```

### 4i. `build_activity.py`

```powershell
python chronicler\pipeline\build_activity.py --force
```

### 4j. `xref_filenames.py` (dry-run — no `--apply`)

```powershell
python chronicler\pipeline\xref_filenames.py
```

### 4k. `extract_path_mentions.py` (dry-run — no `--apply`)

```powershell
python chronicler\pipeline\extract_path_mentions.py
```

### 4l. `relink.py --out ... ` (dry-run only — do not pass `--apply`)

```powershell
python chronicler\pipeline\relink.py --out data\relink_dryrun.json
```

### 4m. `serve`

```powershell
python run.py serve
```

Per DECISIONS 0013, this should serve a **snapshot**, not the live
throwaway vault. Confirm it starts, note the URL it prints, then Ctrl+C to
stop it — no need to leave it running. If it errors because the `[viewer]`
extra (Datasette) isn't installed, note that as a prerequisite gap.

---

## 5. Close it out

- Paste back everything from §4 in order, even the steps that failed or
  were skipped.
- One line: does the `estates_dir`-as-own-outbox hypothesis from §3 hold —
  yes/no, with the evidence from 4d.
- Anything that surprised you, needed a workaround, or pointed at the wrong
  cause for its actual error.

Once I have this, I'll write `docs/SOLO_PLAYBOOK.md` from exactly what
happened, and flag any code change candidates from Task C's anticipated
list (only if the walk actually forces one).
