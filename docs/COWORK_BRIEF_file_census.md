# Cowork brief — file census: what is actually on each machine

**Origin:** design thread, 2026-07-21. Tim wanted a browsable view of the knight's
filesystem; the better answer is that every machine reports its own, and the
report already exists as a rendering surface. Authoritative rationale:
`docs/ARCHITECTURE.md` (the read-only/stdlib contract), `docs/DECISIONS.md` 0010
(the deposit wall).

**Read first:** `l5gntools/scanners/workspace_scanner.py`, `bloat_audit.py`,
`duplicate_finder.py` and `l5gntools/common.py` (`iter_files`, `is_vendored`,
`run_git`) — this brief reuses all of them.

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report.
- The scanners are **read-only and stdlib-only**. A census that writes anything
  into a scanned folder — including a git index refresh — is a contract breach,
  not a detail. See Task B.
- Deposit size is a design constraint, not an afterthought. A naive census across
  eleven repos plus a 90MB model tree would make `estate.json` unusable.

---

## The gap

No scanner answers "what files are in this project":

| Scanner | Sees | Misses |
|---|---|---|
| `workspace_scanner` | `.py` only, vendored excluded | every other file type |
| `doc_census` | markdown only | everything else |
| `bloat_audit` | tracked files >5MB, bloat markers | an inventory — it flags, it does not list |
| `duplicate_finder` | walks all files | reports only collisions |

The question this is for: **before archiving a dormant repo or dropping code out
of L5GN-Castle, what is in there that is not safely in git?** A file list is
useful; a file list that names the at-risk set is what stops you deleting
something you can't get back.

---

## Task A — BUILD: `file_census` scanner (project-level)

New scanner at `l5gntools/scanners/file_census.py`, registered in
`l5gntools/registry.py`. `ESTATE_LEVEL = False`, `SAFETY = SAFE`.

### Tiering — the size contract

Three tiers, because the working set and the mass need different treatment:

**Tier 1 — directory rollup. Always, no cap.**
Per directory, depth-capped at 4 levels (deeper folds into its ancestor):

```json
{"path": "l5gntools/scanners", "files": 17, "bytes": 148322,
 "ext": {".py": 17}, "depth_collapsed": false}
```

**Tier 2 — the working set. Per-file, capped.**
Non-vendored, non-ignored files:

```json
{"path": "run.py", "bytes": 19549, "mtime": "2026-07-18T21:11:00+01:00",
 "git": "tracked"}
```

`git` is one of `tracked` / `untracked` / `ignored`, and `null` when the project
is not a git repo. Cap at 2000 files per project; when capped, set
`"truncated": true` with the true count. **Never silently truncate.**

**Tier 3 — the mass. Rollup only, no per-file entries.**
Vendored and ignored trees (`is_vendored`, plus `.gitignore` matches):

```json
{"path": ".venv", "files": 8421, "bytes": 214000000, "reason": "vendored"}
```

**Plus two headline sets, always emitted in full:**

- `outliers` — the 20 largest files in the project, whatever tier they fall in.
- `at_risk` — **untracked and not ignored**. This is the point of the scanner.
  If it would exceed the cap, raise the cap for this set; do not truncate it. A
  truncated at-risk list is worse than none, because it reads as complete.

### Git status, read-only

Derive status from `git ls-files` (tracked) plus
`git --no-optional-locks status --porcelain --ignored` (untracked and ignored).
**`--no-optional-locks` is mandatory** — see Task B.

Do not shell out per file. One invocation per project, parsed into a lookup.

### Summary block

Per project, a headline the report and the CLI can print without walking the tree:

```json
{"total_files": 412, "total_bytes": 8210044,
 "working_set": {"files": 388, "bytes": 2100044},
 "mass": {"files": 24, "bytes": 6110000},
 "at_risk": {"files": 3, "bytes": 88012},
 "largest": "report.html"}
```

### Tester

`tests/tester_file_census.py`, registered in `verify.py`. Hermetic: build a
synthetic tree in `tmp` with a vendored dir, an ignored file, an untracked file
and a tracked one; assert the tiering, the cap behaviour (`truncated` set and
honest), and that `at_risk` contains exactly the untracked-not-ignored file.

---

## Task B — BUILD: stop the scan touching `.git`

`git status --porcelain` may refresh `.git/index` — a write inside a scanned
folder, which the read-only contract forbids. Two existing call sites:

- `l5gntools/scanners/git_summary.py:26`
- `l5gntools/common.py:155` (`toolkit_git_info`)

Add `--no-optional-locks` to both, and use it in the census. Consider making
`run_git` inject it for read-only subcommands so a future caller cannot forget —
propose it, build it only if it stays simple.

Report whether `auditor_readonly` could have caught this. If it could not, say so
plainly: the auditor's promise is broader than its reach, and that is worth
knowing.

---

## Task C — BUILD: `run.py census` — each machine reports its own domain

A consumer never runs `build`, so the scanner alone leaves the knight invisible.
Add a role-aware command that reports the domain of whichever machine it runs on.

**Producer domain:** the configured `roots` — same ground the scanner covers.
Re-use `file_census`; do not write a second implementation.

**Consumer (knight) domain — two roots, both needed:**

1. **Code root** — the deployed toolkit (`~/L5GN-Tools`), including its venv as
   Tier 3 mass. Answers "is this deploy the same as the repo".
2. **Vault root** — `CHRONICLER_HOME`: `chronicler.db` and its `-wal`/`-shm`
   sidecars, `chat_threads/vault_staging/`, `estates/`, the backup directory, and
   `serve-snapshot/`. Answers "what is actually on the box, and how big".

Resolve both from config, never hardcode. Write to the machine's own data dir via
the existing `write_json` helper (the only sanctioned writer), and print a
readable summary.

**On the wall:** the knight's census necessarily covers `estates/personal` and
`estates/work` side by side. That is a *machine* report, not a deposit — both
already live there and nothing crosses a boundary. Say so in the docstring so a
future reader doesn't mistake it for a wall breach and "fix" it.

---

## Task D — BUILD: the collapsible tree in `report.html`

This is the deliverable Tim actually asked for: click-through browsing without a
server.

- A collapsible directory tree per project, from the Tier 1 rollup, expanding
  into Tier 2 files on demand.
- Size and file count on every directory row, so the mass is visible while
  collapsed.
- **The at-risk set surfaced at the top**, not buried in the tree — untracked and
  not ignored is the thing worth seeing first.
- Tier 3 directories render as a single summarised row: name, count, bytes, and
  why they were excluded. Not expandable — there is nothing behind them.

Constraints: `report.html` is self-contained and offline. Inline JS and CSS only,
no CDN, no framework. Match the existing generator's style in
`l5gntools/report.py`.

---

## Task E — BUILD: `deploy/pull-report.ps1`

The mirror of `push-exports.ps1`: a producer pulls the knight's latest report and
census over ssh and opens it locally. Both directions have keys now.

Match the existing script's conventions — `-WhatIf` dry run, list what will
transfer before transferring, loud failure. Do not invent a new transport; scp,
same as everything else.

---

## Suggested order

A → B → D → C → E.

A and D together are the useful pair — census plus the view of it. B is small and
should ride along with A because the census amplifies the problem. C and E are
worth having but neither blocks the other.

If the budget runs short, **A, B and D alone are a successful session.**

---

## Housekeeping

- Register the scanner in `l5gntools/registry.py` (the single source of truth —
  the auditors read it) and add a row to the tools table in the root `README.md`.
- Add the tester to `verify.py`.
- If any doc states a tool count, it moves by one. `auditor_doc_claims` only
  polices auditor/tester counts, so nothing will catch a stale *tool* count for
  you — check by hand.
- The census makes `SKIP_PROJECT_NAMES` in `build_registry.py` look increasingly
  like a workaround for junk in the scan path. Note it for the assimilation list;
  do not change it here.

---

## UAT — acceptance checks (Tim walks these)

- **A:** `python run.py file_census --target L5GN-Tools` runs, and the summary's
  `total_files` matches what Explorer shows for the folder. The `at_risk` list
  names files he recognises as genuinely untracked.
- **B:** with a scanned repo clean, run a full `build`, then `git status` in that
  repo — the working tree is untouched and `.git/index` mtime is unchanged.
- **C:** on the knight, `run.py census` reports both the code root and the vault
  root with plausible sizes; the DB size matches `ls -la` on `chronicler.db`.
- **D:** open `report.html`, expand a project tree, find a specific file by
  clicking rather than by command line. The at-risk set is visible without
  scrolling. The `.venv` row shows its mass and does not expand.
- **E:** `deploy/pull-report.ps1 -WhatIf` lists what it would pull; without the
  flag the knight's report opens locally.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report: tasks green vs pending; the census output for L5GN-Tools itself as a
worked example; the deposit size before and after (`estate.json` bytes — the size
contract is a claim, so prove it); whether `auditor_readonly` could have caught
Task B; and the **UAT walk-list**.

Write the report as `docs/COWORK_REPORT_file_census.md` and the walk-sheet as
`docs/UAT_file_census.md`. The results log must carry a uat stamp
(`docs/README.md` §3) or the gate refuses the commit.

Nothing commits. Everything staged, for Tim's review.
