# Runbook — refresh installs, deposit both estates, consume

A single cross-machine pass: publish the new toolkit, refresh the work rig and
the knight, deposit **both** producer estates (personal + work) to the knight,
and consume. First real exercise of the **work-rig deposit** and the estate wall.

Every step is marked **▸ GAMING** (LucasGoonPC), **▸ WORK** (10280L), or
**▸ KNIGHT** (l5gn-castle). Rig commands are PowerShell; knight commands are bash
over SSH. Nothing here writes into a scanned repo or the vault.

## Host map

| Machine | Host | Role / estate | Lands on knight as |
|---|---|---|---|
| Gaming rig | `LucasGoonPC` | producer / `personal` | `~/vault/estates/personal/` |
| Work laptop | `10280L` | producer / `work` (MCF + L5GN) | `~/vault/estates/work/` |
| Knight | `l5gn-castle` | consumer / `both` | reads every estate + the vault |

**The wall:** each rig deposits only into its own namespace; `personal` and
`work` never merge. MCF must land under `estates/work/` and nowhere else — the
one check to eyeball at the end.

---

## Step 0 ▸ GAMING — publish the new toolkit to GitHub

The bugfix / governance / blast_radius commits are local. The work rig and knight
refresh by pulling from GitHub, so publish first.

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python verify.py                 # GREEN before you push
git push origin main
```

**Verify:** `git status` shows `up to date with 'origin/main'`. (If you also want
the results log and this runbook on GitHub, commit them first — they're docs, so
they don't affect any install.)

---

## Step 1 ▸ GAMING — ship chat-export inputs to the knight  *(you're mid-way here)*

**Decided: the vault is rebuilt on the knight** (`run.py ingest`), not scp'd as a
finished DB. So this rig ships only the *inputs*; the knight does the ingest in
Step 6 before `consume`. Ship the refreshed export zips and any Gemini URL list:

```powershell
# export zips -> the knight's intake drop; urls.txt -> CHRONICLER_HOME
scp <refreshed-export>.zip l5gn-castle:vault/chat_threads/zip_downloads/
scp urls.txt              l5gn-castle:vault/urls.txt          # only if scraping Gemini shares this round
```

**Verify (knight):** `ls -la ~/vault/chat_threads/zip_downloads/` shows the new
zip(s). The actual DB rebuild happens on the knight in Step 6.1. *(Ingest runs an
automatic off-box backup as its pre-flight, so the current `chronicler.db` is
snapshotted before anything mutates it.)*

---

## Step 2 ▸ WORK — refresh the install

```powershell
cd D:\Work\Github\L5GN-Tools          # this rig's toolkit clone
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -e .                      # only strictly needed if entry points/deps changed; safe to re-run
git config core.hooksPath .githooks
python verify.py
```

**Verify:** `git log --oneline -1` matches the gaming rig's HEAD; `verify.py`
prints `verify: GREEN`. If `Activate.ps1` didn't take,
`python -c "import sys;print(sys.prefix)"` will show system Python — fix before
building.

---

## Step 3 ▸ WORK — refresh the report

```powershell
python run.py config                  # confirm this rig BEFORE scanning
python run.py build
```

**Verify:** `config` shows host `10280L`, `role: producer`, `estate: work`, and
both roots (`MCF` scope `mcf`, `L5GN` scope `l5gn`) with **no `(MISSING)`**. Then
the projects are real and scope-tagged:

```powershell
python -c "import json;d=json.load(open('data/estate.json'));print(len(d['projects']));print([(p['name'],p['scope']) for p in d['projects']][:12]);print(d['roots'])"
```

You should recognise your MCF and L5GN repos, each with a non-null scope. A
`scope: null` means an untagged root — fix it now; scope travels with the deposit
and lands MCF in the right namespace. `start report.html` to eyeball it.

---

## Step 4 ▸ KNIGHT — refresh the install

```bash
ssh l5gn-castle
cd ~/L5GN-Tools
git pull origin main
python3 verify.py
```

**Verify:** `git rev-parse --short HEAD` matches the rigs; `verify: GREEN`.
`config/local.json`, `data/`, and `~/vault/` are git-ignored, so the pull can't
disturb the vault or the knight's config. *(If you use the push-to-deploy remote
instead, `git push knight main` from the gaming rig deploys and self-verifies —
same result.)*

---

## Step 5 ▸ WORK, then ▸ GAMING — deposit both estates

Stage first and read what would leave the machine, **then** push.

**▸ WORK (the estate that has never deposited):**

```powershell
python run.py deposit                 # stage only; prints the exact push command
dir data\outbox\work                  # estate.json + deposit_manifest.json — and nothing else
python run.py deposit --push
```

**▸ GAMING:**

```powershell
python run.py deposit --push          # already retargeted + built at 10:00; re-run build first if you've changed anything since
```

**Verify (each):** output ends `pushed : OK -> l5gn-castle:vault/estates/<estate>/`.

**Wall check (knight):**

```bash
ls -la ~/vault/estates/work/ ~/vault/estates/personal/
```

Both carry a fresh `estate.json` + `deposit_manifest.json`. MCF projects must
appear **only** under `work/`. If anything MCF-shaped is under `personal/`, stop.

---

## Step 6 ▸ KNIGHT — rebuild the vault, consume, then rebuild the registry

### 6.1 — rebuild the vault from the shipped inputs (venv Python)

```bash
cd ~/L5GN-Tools
source .venv/bin/activate
python run.py intake --dry-run     # preview zip classification before mutating
python run.py scrape               # only if you shipped a urls.txt in Step 1
python run.py ingest               # [1/3] pre-flight backup -> [2/3] intake -> [3/3] pipeline (+relink)
```

**Verify:** `ingest` reports all three phases and ends without error; the pipeline
stage links freshly-ingested threads. Use the **venv** Python here — the pipeline
subprocess inherits `sys.executable` and needs pyyaml/embeddings.

### 6.2 — consume (stdlib Python is fine)

```bash
python3 run.py consume
```

**Verify:** both `work` and `personal` list `manifest_verified: true` (the sha256
in each manifest matches what landed). A `false` is a truncated transfer — re-run
that rig's `deposit --push`, don't consume past it. First-ever `work` deposit
shows `estate_diff = insufficient_history`; that's correct, not a fault — it
becomes a real diff on the next day's deposit.

Then the payoff — the registry sees MCF for the first time:

```bash
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases   # dry-run: inspect
.venv/bin/python chronicler/pipeline/build_registry.py                    # write it
```

**Use `.venv/bin/python` explicitly** — the pipeline resolves `l5gntools` only
in the venv interpreter. **Verify:** the ESTATE SOURCES block lists both
`personal` and `work` with no `MISSING estate`, and the MCF projects now carry
real repo facts (`present`, a `first_seen`) instead of `NOT IN ANY DEPOSIT`.

---

## Order at a glance

0. GAMING → `git push origin main` (publish the fixed scanners)
1. GAMING → `scp` export zips/urls to the knight's intake drop
2. WORK → `git pull` + `pip install -e .` + `verify.py`
3. WORK → `run.py config` + `run.py build`
4. KNIGHT → `git pull` + `verify.py`
5. WORK `deposit --push`, then GAMING `deposit --push` → wall check
6. KNIGHT → `ingest` (rebuild vault) → `consume` → `build_registry.py --report-aliases` → `build_registry.py`

## Gotchas carried from the playbooks

- **Publish before you pull.** Steps 2 and 4 get the new code only if Step 0 ran.
- **The vault is separate from the estates.** A fresh `consume` over a stale
  `chronicler.db` reconciles new code against old chat — rebuild it on the knight
  (Step 6.1) from the inputs shipped in Step 1, *before* `consume`.
- **Wall.** MCF only ever under `estates/work/`; the knight never reaches back to
  a rig.
- **Stale-but-honest.** An estate snapshot is a point in time; a stale one is
  honestly stale, not wrong. No schedule is mandatory.
