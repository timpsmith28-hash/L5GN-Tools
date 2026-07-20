# Producer setup — standing up the work rig

The exact, in-order steps to turn a machine into a **producer**: a rig that scans
its own repos into an `estate.json` snapshot and pushes it to the knight. Written
for the work laptop, but the steps are the same for any producer.

Companion to `KNIGHT_PLAYBOOK.md` (which covers the *consumer* side). Read
`ARCHITECTURE.md` §2 first if the producer/consumer split isn't familiar.

> **Why this matters right now.** The work rig has never deposited. Until it
> does, every MCF project exists in the registry as a link target with no repo
> facts attached — `build_registry.py --report-aliases` will show them with
> `present=false`. This deploy is what unblocks the MCF half of the registry, and
> it is the first real exercise of the deposit wall.

---

## 0. Before you start

You need:

- Python 3.10+ on the rig (`python --version`).
- `git`.
- SSH access to the knight, ideally as an alias in `~/.ssh/config` so the
  push target can be written as `l5gn-castle:vault/estates` rather than a raw
  host string. Confirm with `ssh l5gn-castle 'echo ok'` — it must print `ok`
  without prompting for a password.
- The rig's hostname: `python -c "import socket; print(socket.gethostname())"`.
  **Write it down** — every config entry is keyed by it.

**The wall, stated plainly.** A producer sends *only* what `run.py deposit`
stages: the estate snapshot and its manifest. It never sends repo contents, and
the knight never reaches back onto this machine. Work and personal estates land
in separate directories on the knight and are never merged. If a step here looks
like it would copy source code off the work rig, stop — it shouldn't.

---

## 1. Clone the toolkit

```powershell
cd C:\Users\<you>\Github          # wherever you keep repos
git clone https://github.com/<owner>/L5GN-Tools.git
cd L5GN-Tools
```

**Verify:** `git log --oneline -1` prints a commit.

---

## 2. Create the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux
```

**Verify:** `python -c "import sys; print(sys.prefix)"` prints a path inside
`.venv`. If it prints the system Python, the activate didn't take.

---

## 3. Install the toolkit

```powershell
pip install -e .
```

The core is stdlib-only, so this installs no third-party packages — that is
expected, not a failure. A producer needs none of the optional extras
(`[viewer]`, `[review]`, `[chronicler]`); those are consumer-side.

**Verify:** `python -c "import l5gntools; print(l5gntools.__version__)"` prints a
version.

---

## 4. Configure this machine

Create `config\local.json` (git-ignored — it never syncs to GitHub, which is the
point: employer paths and codenames stay off the public repo). Copy
`config\local.json.example` as a starting point.

Use **your hostname** from step 0 as the key:

```json
{
  "RENAME-ME-WORK-LAPTOP": {
    "role": "producer",
    "estate": "work",
    "roots": [
      {"path": "D:/Work/Github/MCF",  "scope": "mcf"},
      {"path": "D:/Work/Github/L5GN", "scope": "l5gn"}
    ],
    "push_target": "l5gn-castle:vault/estates",
    "push_transport": "scp"
  }
}
```

Four things are load-bearing:

- `role: producer` — this machine scans and pushes; it never consumes.
- `estate: work` — the landing directory on the knight, and the wall boundary.
  It **must** be `work` here; `personal` is the gaming rig's.
- `roots` — the folders whose *child* directories are the projects to scan. Point
  these at the `MCF/` and `L5GN/` folders that actually exist on this machine.
- `scope` on each root — this is how a project gets its registry scope
  (DECISIONS 0012). Scope is declared on the root, never inferred from folder
  nesting, precisely so no machine has to reorganise its folders to match a
  convention. An untagged root still scans; its projects land as scope `other`
  and are listed under DEPOSIT GAPS by `build_registry.py --report-aliases`.

**Verify:**

```powershell
python run.py config
```

It must print your hostname with **no** "(no matching entry -> using default)",
`role: producer`, `estate: work`, and each root listed *without* `(MISSING)`. A
`(MISSING)` root is a wrong path — fix it now; a scan against a missing root
produces an empty estate, not an error.

---

## 5. First scan

```powershell
python run.py build
```

**Verify:** `data\estate.json` exists and lists your real projects:

```powershell
python -c "import json; d=json.load(open('data/estate.json')); print(len(d['projects']), [p['name'] for p in d['projects']][:10]); print(d['roots'])"
```

You should recognise the project names as your actual repos, and `roots` should
show each path with its scope tag. If `scope` is `null` on the projects, step 4's
root tagging didn't take.

---

## 6. Stage the deposit (no push yet)

```powershell
python run.py deposit
```

Without `--push` this only *stages* — it prints the push command it would run.
Read that line before you send anything off the work machine.

**Verify:** `data\outbox\work\` exists and contains `estate.json` and
`deposit_manifest.json`, and nothing else you wouldn't want leaving the rig.

---

## 7. Push to the knight

```powershell
python run.py deposit --push
```

**Verify:** the output says `pushed : OK -> l5gn-castle:vault/estates/work/`.
On the knight:

```bash
ls -la ~/vault/estates/work/
```

You should see `estate.json` and `deposit_manifest.json` with a current
timestamp.

---

## 8. Consume on the knight

```bash
cd ~/L5GN-Tools
python3 run.py consume
```

**Verify:** the output lists the `work` estate with `manifest_verified: true`
(the sha256 in the manifest matches the file that landed — a failed verify means
a truncated or tampered transfer, not a warning to skip past).

First run reports `estate_diff=insufficient_history` because one snapshot cannot
be diffed. That is correct, not a fault; it becomes a real diff after a second
deposit on a later day.

---

## 9. Rebuild the registry with both estates

This is the payoff — the first time the registry can see the MCF projects.

```bash
cd ~/L5GN-Tools
python3 chronicler/pipeline/build_registry.py --report-aliases
```

**Verify:** the ESTATE SOURCES block at the top lists **both** `personal` and
`work` with no "MISSING estate" line, and the MCF projects now appear with real
repo facts (`present`, a `first_seen` date) instead of `NOT IN ANY DEPOSIT`.

When the list looks right, write it:

```bash
python3 chronicler/pipeline/build_registry.py
```

---

## 10. Routine, from here on

```powershell
python run.py build
python run.py deposit --push
```

Two commands, whenever you want the knight's picture refreshed. Everything else
is consumer-side.

---

## Future: auto-apply on pull (documented, NOT implemented)

A `post-merge` git hook on the knight could run `verify.py` (and optionally
`consume`) automatically after every `git pull`, so a deploy is one push.

**Not implemented this round, deliberately.** A `post-merge` hook turns `git
pull` into `execute arbitrary code from the remote`. That is a genuine
supply-chain surface: anyone who can land a commit on the remote can run code on
the knight, and `pull` stops being the safe, inspectable operation it looks like.

The caveat is *acceptable here* because this is a repo only Tim controls, with no
third-party contributors and no CI bot with write access. It would not be
acceptable on a shared repo. If it is ever implemented, the conditions to
re-check are: still single-maintainer, still no automated writers to the remote,
and the hook runs `verify.py` **before** anything else so a red gate stops the
deploy rather than deploying and then failing.

---

## If something goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `run.py config` shows "(no matching entry -> using default)" | hostname key doesn't match | re-read the hostname from step 0; JSON keys are case-sensitive |
| a root prints `(MISSING)` | wrong path in `roots` | fix the path; use forward slashes even on Windows |
| `estate.json` has 0 projects | roots point at the project folders themselves, not their parent | `roots` are the *parents* whose children are projects |
| projects have `scope: null` | roots left untagged | use the `{"path": ..., "scope": ...}` form |
| push fails with a host error | ssh alias not resolving | test `ssh l5gn-castle 'echo ok'` first |
| `manifest_verified: false` on the knight | truncated/partial transfer | re-run `deposit --push`; do not consume an unverified bundle |
