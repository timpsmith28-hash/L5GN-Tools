# UAT walk-sheet — file census

Pair: `docs/COWORK_BRIEF_file_census.md` + `docs/COWORK_REPORT_file_census.md`.
Built on top of `03bac5d`; **nothing is committed**, so walk this against the
staged working tree.

Gate at build time: `python verify.py` **GREEN**, 6 auditors + 28 testers.

Every check below is **ready to walk**. None is passed — only Tim walking it
makes it that, and this pair is not archivable until he has.

**All five brief tasks are built.** Checks **C**, **E**, **H** and **J** were
added in round 2, along with the real measured figures for check **F**.

---

## Before you start

```
cd ~/Documents/GitHub/L5GN-Tools
python verify.py            # expect: verify: GREEN -- all gates passed.
```

If that is red, stop — nothing below is meaningful.

---

## A — the scanner tells the truth about this folder

```
python run.py file_census --target L5GN-Tools
type data\file_census\L5GN-Tools.json
```

- [x] **A1.** It runs and writes `data/file_census/L5GN-Tools.json`.
- [x] **A2.** `summary.total_files` matches what Explorer reports for the folder.
      Right-click `L5GN-Tools` → Properties → *Contains: N Files*. **Turn on
      hidden items first** (View → Show → Hidden items) — the census counts
      `.git`, and Explorer will not unless you do.
      *At build time this read 890 files / 9,350,891 bytes.*
- [x] **A3.** The `at_risk` list names files Tim recognises as **genuinely
      untracked** — not tracked files, not ignored ones. Immediately after this
      session it should name the session's own new files and nothing else.
- [x] **A4.** Nothing in `at_risk` is something Tim believed was committed. If it
      is, that is the scanner doing its job and a commit is owed.

**What would fail this:** a `total_files` that is out by more than a rounding of
Explorer's own counting, or an at-risk list containing a file that `git ls-files`
does show.

---

## B — the scan does not touch `.git`

The contract says a scanner never writes into a scanned folder. `git status`
refreshes `.git/index` unless told not to, so this is the check that the fix
actually took.

Pick a scanned repo that is **clean** (`git status` shows nothing to commit).

**PowerShell:**

```powershell
cd <that repo>
git status                                   # confirm clean
(Get-Item .git\index).LastWriteTime          # note it
cd ~\Documents\GitHub\L5GN-Tools
python run.py build --fresh
cd <that repo>
(Get-Item .git\index).LastWriteTime          # compare
git status                                   # confirm still clean
```

- [x] **B1.** `.git/index` LastWriteTime is **unchanged** across the build.
- [x] **B2.** The working tree is untouched — `git status` says the same thing
      after as before.
- [x] **B3.** Repeat on a **dirty** repo. The index mtime must still not move; a
      dirty tree is where git most wants to refresh it.

**What would fail this:** any movement in the index mtime. If it moves, the flag
is not reaching that call site — check `l5gntools/common.py` `git_argv` and
whether some new caller is building its own argv.

---

## D1 — browse the tree by clicking

```
python run.py build
```

Open `report.html` (double-click; it is a `file://` page and must work with no
server and no network).

- [x] **D1a.** A **Files** tab exists, between *Code Inventory* and *Docs*.
- [x] **D1b.** Each project is a collapsible row. Expanding one shows its
      directory tree.
- [x] **D1c.** **Find a specific file by clicking** — pick something you know the
      path of, expand down to it, and read its size. No command line.
- [x] **D1d.** Every directory row shows a **file count and a size** while still
      collapsed.
- [x] **D1e.** Disconnect the network (or trust that it never fetched anything)
      and reload. The page is unchanged — no CDN, no framework.

---

## D2 — the at-risk set is the first thing you see

- [x] **D2a.** On opening the Files tab, the **At risk** panel is visible
      **without scrolling**, above every project.
- [x] **D2b.** It names the project against each path, so a bare filename is not
      ambiguous across eleven repos.
- [x] **D2c.** A `.venv` / `__pycache__` / `models`-class row appears in a tree as
      **one summarised line** showing its file count, its size and *why* it was
      excluded — and **clicking it does not expand it**.
- [x] **D2d.** If any project shows a rollup at-risk entry (*"whole vendored tree:
      N files"*), it is legible as a tree and not mistakable for one file.
- [x] **D2e.** If a project's per-file listing was capped, the tab says so
      explicitly, and says the directory totals and at-risk set are still
      complete. **A truncation you cannot see is the failure this check exists
      for.**

---

## F — the deposit size

**Already measured** from the build Tim ran on the gaming rig. §3's projection of
1.2MB was wrong; the real number is below. What remains to walk is confirming it
on a fresh run and deciding whether it is acceptable.

| | Bytes |
|---|---:|
| `estate.json` before | 928,120 |
| `estate.json` after (measured) | **3,350,576** |
| `report.html` after | 2,393,421 |

- [x] **F1.** A fresh `python run.py build --fresh` reproduces roughly these
      figures. `(Get-Item data\estate.json).Length`.
- [x] **F2.** 3.35MB for `estate.json` and 2.39MB for `report.html` is acceptable
      to Tim, **or** check G2 below is acted on first.
- [x] **F3.** `report.html` opens acceptably fast **from a phone on the tailnet**.
      That is the constraint that actually binds — 2.39MB is a lot over a mobile
      link, and the Files tab is the reason to look at it there.
- [x] **F4.** Only `L5GN-Castle` hit `FILE_CAP` (3,805 working-set files capped to
      2,000). The tab says so where it is capped. `FILE_CAP` remains the lever if
      needed, but it is **not** the main driver — see G2.

---

## G2 — the Castle finding (the one number worth acting on)

3,599 of the estate's 3,673 at-risk files are in **one directory**:
`L5GN-Castle/data/`, untracked and matched by no `.gitignore` pattern. That is
98% of the at-risk set and 45% of `estate.json`.

- [x] **G2a.** Open the Files tab and confirm the `L5GN-Castle / data/` group
      reads as expected — 3,599 files — and that Tim recognises them as transient
      rather than as work he thought was committed.
- [x] **G2b.** Decide the disposition: gitignore it, commit it, or leave it
      pending the reorg. **No code change is needed either way** — this is the
      question the scanner exists to raise, not a defect in it.
- [x] **G2c.** If it is gitignored, re-run `build` and confirm the measured
      effect: Castle's census 1,341,094 → ~26,934 bytes, `estate.json`
      3,350,576 → ~1,857,316, and the only truncation in the estate disappears.
      *(Derived from the real feed, not estimated.)*

---

## G — the non-git projects

Four projects have no git repo at all (`L5GN-Archive`, `L5GN-Crystal-Spire`,
`L5GN-server-hub-iso`, `test_folder`). The census reports `at_risk_note` for
these rather than an empty at-risk list, because an empty list would read as
reassurance.

- [x] **G1.** The Files tab shows a *"not a git repository"* line naming them.
- [x] **G2.** Each one is a project Tim **intends** to leave outside version
      control. Any that is not is a repo waiting to be initialised — which is the
      question the whole scanner was built to raise.

---

## H — the refined at-risk panel (round 2)

Open `report.html` → **Files**.

- [x] **H1.** The **At risk** panel is **open on load** and collapses to a single
      summary line on one click.
- [x] **H2.** Its summary line carries the totals while collapsed — file count,
      size, and how many locations.
- [x] **H3.** It is **grouped**, roughly 20 rows rather than 3,673. Sorted with
      the biggest problem first.
- [x] **H4.** Expanding `L5GN-Castle / data/` lists every one of its 3,599 paths,
      largest first. **Nothing was truncated to make the list short** — grouping
      is presentation only.
- [x] **H5.** `.git` still renders as **one non-expandable mass row** with its
      size, in every project tree. Clicking it does nothing. (Ratified in round 2
      — this check exists to catch a regression, not to test a change.)
- [x] **H6.** The page still opens instantly from `file://` despite the estate
      now carrying 3,673 at-risk entries.

---

## C — `run.py census` on both machines

**On the gaming rig (producer):**

```
python run.py census
```

- [x] **C1.** It reports the **producer** domain and names the configured root
      (`C:\Users\timps\Documents\GitHub`).
- [x] **C2.** It lists all 11 projects with file counts and sizes, and flags
      `AT RISK` against the ones that have untracked files.
- [x] **C3.** It writes `data/census.json` and says where.
- [x] **C4.** `python run.py census --target <some folder>` censuses that folder
      alone, whatever the machine's role.

**On the knight (consumer) — this is the check the task exists for:**

```
python run.py census
```

- [ ] **C5.** It reports the **consumer** domain, not the producer one.
- [ ] **C6.** **Code root** is reported with a plausible file count and size, and
      its venv appears as Tier 3 mass. Compare its working-set count against the
      repo — this is the *"is this deploy the same as the repo"* question.
- [ ] **C7.** **Vault root** is reported, resolved from `CHRONICLER_HOME` /
      config, and the path is right.
- [ ] **C8.** **The DB size matches `ls -la`** on `chronicler.db`. This is the
      single most load-bearing number in the whole command; if it disagrees,
      something is resolving to the wrong file.
- [ ] **C9.** The `-wal` / `-shm` sidecars report honestly — present with a size,
      or **absent** (not zero bytes). A large `-wal` means uncheckpointed writes
      and is worth knowing about.
- [ ] **C10.** `chat_threads/vault_staging`, `backups`, `serve-snapshot` and
      `estates` all appear with counts and sizes. `backups` should show the
      keep-last-N generations; a fat `serve-snapshot` means `serve` left one
      behind.
- [ ] **C11.** `estates` breaks down per bundle — **`personal` and `work` side by
      side with their sizes.** That is correct and deliberate: a machine report of
      a directory the knight owns, not a deposit. Nothing is read *inside* either
      bundle. **If a future reader "fixes" this as a wall breach, they have broken
      it** — see the docstring and `tester_census._check_wall`.
- [ ] **C12.** Break it on purpose: run with `CHRONICLER_HOME` pointing somewhere
      that does not exist. It must say so plainly and exit non-zero — never a
      silent empty report that reads as *"the box is empty"*.

---

## E — `deploy/pull-report.ps1`

**This script has never been executed.** There was no PowerShell in the build
environment, so it is written and reviewed but unrun. Walk it expecting to find
something.

Run `python run.py census` (and `build`) on the knight first, or there will be
nothing to pull.

```powershell
cd ~\Documents\GitHub\L5GN-Tools
powershell -File deploy\pull-report.ps1 -WhatIf
```

- [ ] **E1.** The dry run **lists what it would pull** — `report.html`,
      `census.json`, `estate.json` — each with a size and an age in hours.
- [ ] **E2.** It transfers **nothing** and says *"-WhatIf -- nothing pulled"*.
- [ ] **E3.** Anything absent on the knight is named in a warning, not silently
      skipped.

```powershell
powershell -File deploy\pull-report.ps1
```

- [ ] **E4.** Files land in `data\knight\` — **not** the repo root. Confirm this
      rig's own `report.html` is untouched; overwriting it would destroy the local
      build.
- [ ] **E5.** The knight's `report.html` **opens locally**, and its Files tab
      shows the knight's own domain (code root + vault), not the gaming rig's
      projects.
- [ ] **E6.** `-NoOpen` pulls without opening.
- [ ] **E7.** Break it on purpose: point `-Remote` at a host that does not
      resolve. It must fail **loudly** and exit non-zero — no partial pull
      reported as success.
- [ ] **E8.** If the knight's newest file is over 24h old, the stale warning
      fires.

---

## J — the round-2 gate

- [ ] **J1.** `python verify.py` is GREEN and reports **6 auditors + 28 testers**.
- [ ] **J2.** `python run.py list` shows `file_census` among the tools and
      `census` among the commands.
- [ ] **J3.** `README.md`'s tools table has the `file_census` row.

---

## Closing the pair

When every box above is walked, write `docs/UAT_file_census_results.md`. It
**must** carry a uat stamp (`docs/README.md` §3) or `auditor_uat_stamp` fails the
gate and the commit is refused:

```
<!-- uat: commit=<sha you walked> dirty=<true|false> host=<machine> walked=YYYY-MM-DD gate=6a/26t -->
```

`gate=6a/26t` is correct as built. If you add or remove a tester before
committing, that number moves and the auditor will say so — it already did once
in this session, on this very sheet, four hours after it was written.

Record what was walked and what was **not**, including anything that fails —
a results log naming a failure is worth more than one that quietly omits it.
Only then are the brief, the report and this sheet archivable as a pair.
