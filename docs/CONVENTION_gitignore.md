# Convention — `.gitignore`

**Scope: this repo, `L5GN-Tools`.** This file is the sole authority for the
baseline block's contents. `DECISIONS.md` does not restate it, and neither does
`.gitignore` itself — the file carries the block, this document says what the
block is for.

**Status: `proposed`.** It may be read and followed now; it is not authority to
cite until it is ratified by a re-read on a later day.

**Adopted from:** repo `WizForgeAnalytics`, file `docs/CONVENTION_gitignore.md`,
read from the `wizforge-mirror-2026-08-26` snapshot on **2026-08-27** under
**0051** clause 1(b). **The mechanism is adopted; the contents are not.** Their
block enumerates rules true of nine repos in another estate — data-export
extensions, a `context/**` rule for a directory this repo decided against
(`CONVENTION_docs.md` §5), and a `data/git_warden/` rule this repo already covers
more broadly. What transfers is the shape: **block first, marker lines, nothing
above the lower marker edited locally, exceptions as commented negations below
it**, and their reasoning on secrets (§4). Their §3 worked example and §4
adoption notes are about their repos and are dropped.

**`.gitignore` is not edited by the round that wrote this file.** §2 describes
the target; §3 says exactly what the current file would have to change to reach
it, and that change is its own commit in its own round.

---

## 1. Why a written baseline

An ignore rule is invisible when it works and invisible when it is deleted. The
estate this convention comes from lost eight rules to a commit whose message
described adding one, and the loss went unnoticed for three days because nothing
anywhere stated what the file was supposed to contain.

**A written baseline makes that class of silent loss diffable.** That is the
whole of it. It is not about tidiness, and it does not make the file shorter.

## 2. The baseline block

The block is the **first thing** in `.gitignore`. Nothing precedes it. It opens
and closes with a marker line, and **nothing between the two markers is edited
locally** — not reordered, not recommented, not extended.

```gitignore
# ─── L5GN baseline — docs/CONVENTION_gitignore.md · do not edit above the lower marker ───

# Python build and environment artefacts.
__pycache__/
*.pyc
*.egg-info/
.venv/
venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/

# Editors / OS noise.
.idea/
.vscode/
.DS_Store
Thumbs.db
.fuse_hidden*

# Secrets and credentials. Extensions and exact names ONLY — filename-substring
# patterns such as *secret*, *credential* or *token* are deliberately NOT here,
# because they match anywhere in a path and would swallow a
# CONVENTION_secrets.md or a token_parser.py. See §4.
.env
*.env
!.env.example
*.pem
*.key
*.p12
*.pfx

# --- repo-specific below this line ---
```

### The rules

1. **The block is first.** Nothing precedes the upper marker.
2. **Nothing between the markers is edited locally.** A change to the block is an
   amendment to this file, not a local edit that later gets copied outward.
3. **Repo-specific rules go below the lower marker**, each with a comment saying
   why — the current file's comments are the standard to match, and several of
   them carry reasoning that exists nowhere else.
4. **An exception to a baseline rule is a negation *below* the lower marker**,
   with a comment naming what it re-admits and why. This works because **git
   applies patterns in order**, and everything below the marker is later than
   everything above it. A negation placed above its pattern silently does
   nothing — it does not error, it does not warn, it simply has no effect, and
   that is the failure mode this rule exists to prevent.
5. **Verification is `git check-ignore -v <path>`, and nothing else.** It names
   the file and the line number that decided, which is the only way to be sure
   which of two rules won.

### Reading `.gitignore` is not evidence

**A read of the file is not evidence of what git ignores**, and this rule is here
because a mount served a truncated copy of a `.gitignore` stably across three
consecutive reads and sent a thread in circles. The file may be stale, truncated,
overridden by `.git/info/exclude` or by a global excludes file, or beaten by an
earlier pattern. **Ask git.** `git check-ignore -v` is the answer; opening the
file is a guess that reads like an answer.

## 3. What this repo's `.gitignore` would have to change

The current file is not wrong — every rule in it works — but it is arranged by
subject rather than by baseline-then-local, and it has one real gap.

**Already present, and moves into the block unchanged:** the Python group
(`__pycache__/`, `*.pyc`, `*.egg-info/`, `.venv/`, `venv/`, `.mypy_cache/`,
`.pytest_cache/`, `.ruff_cache/`), the editor/OS group (`.idea/`, `.vscode/`,
`.DS_Store`, `Thumbs.db`) and `.fuse_hidden*`.

**The gap: this repo has no secrets rules at all.** No `.env`, no `*.pem`, no
`*.key`. That is the one thing the block adds, and it is the reason to adopt it.

**Stays below the line, repo-specific, unchanged:** `/data/`, `/report.html`,
`data/urls.txt`; the four `config/` rules and every word of their comments —
particularly the `project_wizard.allow.json` note, which records that untracking
the file narrows **0042** clause 2 and says so rather than hiding it; the
`chronicler/` runtime group; and `/test_ledger.jsonl`.

**Not adopted from the source block, and why:**

- **`data/git_warden/`** — redundant here. `/data/` already ignores it, verified
  by `git check-ignore -v data/git_warden` returning `.gitignore:2:/data/`. A
  redundant rule is harmless, but adding one whose effect depends on a broader
  rule staying put is a trap for whoever narrows `/data/` later.
- **The data-export extensions** (`*.csv`, `*.tsv`, `*.xlsx`, `*.xlsm`, `*.xls`)
  — bare, path-independent rules that would ignore such a file **anywhere** in
  the tree. This repo is a toolkit rather than a data estate, and a fixture or a
  test input is a plausible tracked file here in a way it is not there. Not
  adopted without a per-path check against what git already tracks.
- **`context/**`** — there is no `context/` in this repo and
  `CONVENTION_docs.md` §5 decided there will not be one. A rule for a directory
  that does not exist teaches a reader it does.

**No rule in §2's block newly ignores a file git already tracks.** That is a
condition of adoption, not an observation about it: the check is
`git ls-files` against each pattern, run before the block lands, and the block
does not land until it returns nothing.

## 4. Secrets — what the block catches, and what it does not

Extensions and exact names only. **`*secret*`, `*credential*` and `*token*` are
deliberately excluded**, because they match anywhere in a path: they would
swallow a `CONVENTION_secrets.md`, a `token_parser.py`, a
`docs/investigation/*_credential_rotation_*.md`. A repo that wants them adopts
them below its marker, knowingly.

**The cost, stated plainly: a file called `salesforce_credentials.txt` passes the
baseline.** So does `api_keys.json`, and so does anything a person names badly.
The block catches file *types* and a few exact names. It does not catch words,
and only a per-repo rule — or not writing the file — stops those.

## 5. What this does not do

- **It does not protect what is already tracked.** An ignore rule has no effect
  on a file git is already following. A repo with a committed secret keeps it
  until someone runs `git rm --cached`, and that is a migration round with a
  history question attached, not this file's business.
- **Nothing checks that `.gitignore` matches this document.** No auditor reads
  either. The block is a claim that is true immediately after it is written and
  drifts silently thereafter. Generating the file from this document would fix
  that and is a later decision.
- **`.git/info/exclude` and the global excludes file are invisible here.** Both
  can ignore a path this document says nothing about, which is the second reason
  §2's verification rule says `check-ignore` rather than "read the file".
- **The block has never been propagated.** It describes one repo today. If a
  second repo in this estate adopts it, nothing will notice when the two drift.
