# UAT walk-sheet — build round 3

The acceptance checks for round 3, in the form you actually run them.

**Why this exists separately from the report.** `COWORK_ROUND_3_REPORT.md` is
testimony — what the build thread found and built, frozen as written
(`docs/README.md` §2). This is the operational artifact: the same checks, with
four defects in the report's version corrected, prerequisites named, and every
command runnable as printed. Corrections are listed at the bottom so the
difference between the two is visible rather than silent.

`verify.py` green proves the code **works**. These prove it **does what was
asked**. Only Tim walking them passes them; nothing here is marked passed in
advance. **A completed pair is archivable only once this sheet is walked**
(`docs/README.md` §3).

---

## Before you start ▸ KNIGHT

Everything below runs on the knight unless marked otherwise.

```bash
cd ~/L5GN-Tools
.venv/bin/python run.py config          # note the vault path it reports
```

Two conventions used throughout:

- `$VAULT` means **the vault path `run.py config` just printed** — not a
  hardcoded `~/vault/chronicler.db`. Export it so the commands paste cleanly:
  ```bash
  export VAULT=~/vault/chronicler.db      # replace with what config reported
  ```
- Pipeline scripts are invoked as `.venv/bin/python`, never bare `python3` —
  they import `l5gntools` and fail outside the venv
  (`PRODUCER_PLAYBOOK.md` §10).

Optional extras this sheet needs, on the knight only:

```bash
.venv/bin/pip install -e '.[viewer]'    # datasette — item B
.venv/bin/pip install -e '.[review]'    # fastapi + uvicorn — items B, D
```

**Take a backup first.** Item D writes to the live vault, and this is the repo's
own doctrine (DECISIONS 0005/0006):

```bash
.venv/bin/python run.py backup
```

Confirm a dated snapshot landed off-box before going further.

---

## A — WAL and busy_timeout (DECISIONS 0014)

**Claim under test:** a reader and a writer can hold the live vault at the same
time without the reader erroring or seeing a torn state — the false-`malformed`
class is gone.

**Step 0, and it matters.** WAL is persistent in the DB file but has to be *set*
once by a read/write connection from the new code. If you probe a vault that
hasn't been opened since the upgrade, `journal_mode` reports `delete` and the
check looks like a failure when it's simply not been applied yet. So touch it
first:

```bash
.venv/bin/python -c "from l5gntools import dbsafe; import os; c=dbsafe.connect(os.environ['VAULT']); print(dbsafe.journal_mode(c))"
```

Expect `wal`.

**Then the concurrency probe.** Shell 1 takes the write lock — `BEGIN IMMEDIATE`
alone is enough, no row needs writing:

```bash
# shell 1
sqlite3 $VAULT
sqlite> PRAGMA journal_mode;      -- must print: wal
sqlite> BEGIN IMMEDIATE;          -- write lock now held, nothing written
```

```bash
# shell 2, while shell 1 still holds it
sqlite3 $VAULT "SELECT COUNT(*) FROM link_evidence;"
```

```bash
# back in shell 1
sqlite> ROLLBACK;
sqlite> .quit
```

**Passing:** shell 2 returns a count immediately — no `database is locked`, no
`disk image is malformed`. `PRAGMA journal_mode` returns `wal`.
**Failing:** any error from the reader.

---

## B — serve reads a snapshot, never the live vault (DECISIONS 0013)

**Claim under test:** the read surface shows a frozen copy, says how stale it is,
and refuses rather than falling back to live.

```bash
.venv/bin/python run.py review        # rule one thread; note the time
# stop review (Ctrl-C), then:
.venv/bin/python run.py serve
```

**Passing — three things:**

1. `serve` prints a `live vault` line and a **different** `snapshot` line, plus a
   "showing vault as of &lt;time&gt; — re-launch to refresh" note. The Datasette
   index page carries the same note in its banner (this is the one that matters —
   the usual reader is a phone on the tailnet, nowhere near this terminal).
2. The printed argv still contains `--immutable`, and the path after it is the
   **snapshot**, not the live DB.
3. The ruling you just made is **absent** from `serve` but present live:
   ```bash
   sqlite3 $VAULT "SELECT project_link FROM threads WHERE thread_id='<the one you ruled>';"
   ```
   That absence is correct behaviour — "refresh to see it", not a lost ruling.

---

## C — build_registry reads deposited estates

**Claim under test:** the registry builds from deposit facts rather than walking
a folder layout that exists on no machine — the error that made it never once run
successfully.

```bash
cd ~/L5GN-Tools
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases
```

**Passing:** no `configured root missing` error; an ESTATE SOURCES block naming
the deposits it read; a project list you recognise as your actual repos.

**Look at, specifically:**

- The five auto/unclassified projects — `L5GN-Archive`, `L5GN-Castle`,
  `L5GN-Continuous-Ingestion-Daemon`, `L5GN-server-hub-iso`,
  `L5GN_Managed_Workspace`. Each became its own single-repo project with
  `provenance: auto`. Nothing is lost; they're unfiled. File them in
  `config/project_registry.json` when you know where they belong.
- The DEPOSIT GAPS section. Scope gaps here are expected until the rig re-runs
  `run.py build` — the current `data/estate.json` predates root tagging.

**If it reports `no such table: projects`:** the vault path is wrong, not the
registry. See `PRODUCER_PLAYBOOK.md` §10.

---

## D — three tiers, one identifier (DECISIONS 0012)

**Do the migration first**, and only after the backup above. `l5gn-os` was a
project id and is now the *program* id; the old meaning survives as
`l5gn-os-program`. Check the count before changing anything — under DECISIONS
0011 these early values are being reset rather than trusted, so it may be zero
and moot:

```bash
sqlite3 $VAULT "SELECT COUNT(*) FROM threads WHERE project_link='l5gn-os';"
# only if that count is non-zero:
sqlite3 $VAULT "UPDATE threads SET project_link='l5gn-os-program' WHERE project_link='l5gn-os';"
```

Run this with the pipeline **not** running.

**Then the checks:**

```bash
.venv/bin/python chronicler/pipeline/relink.py       # dry-run is the default
.venv/bin/python run.py review                       # rule ~3 threads
sqlite3 $VAULT \
  "SELECT project_link, COUNT(*) FROM threads WHERE project_link IS NOT NULL GROUP BY 1;"
```

**Passing:**

- The dry-run's SUGGESTIONS block shows a `[L5GN OS > Citadel MicroIDE >
  smelt-gateway]` style breadcrumb on every line.
- In the review UI each option carries its hierarchy.
- After ruling, the SQL returns **only registry ids** — no folder-style names
  mixed with id-style names in the same column.
- Rulings persist across a restart of `review`.

---

## E — vocabulary rebuild

**Not ready to walk.** Blocked: `build_activity.py` has the same folder-walk
defect Task C fixed in `build_registry.py`, so S3 activity windows can't be
produced on the knight, and vocabulary depends on them. See
`COWORK_ROUND_3_REPORT.md` § "Task E — why it stopped".

---

## F — work rig ▸ RIG

Follow `PRODUCER_PLAYBOOK.md` start to finish on the work laptop.

**Passing:** you reach the end without hitting an undocumented gap or an
unanswered question — the doc's own UAT is whether it got you there. Then §10
rebuilds the registry and the MCF projects appear with real repo facts instead of
`NOT IN ANY DEPOSIT`.

Note anything that made you stop and think. That's the finding, not a failure.

---

## Corrections applied to the report's version

Recorded so the divergence is visible, per `docs/README.md` §3 — the report
itself is unedited.

1. **Pipeline commands were unrunnable as printed.** `python3
   chronicler/pipeline/build_registry.py` fails with `ModuleNotFoundError: No
   module named 'l5gntools'`: Task A made `chronicler/pipeline/db.py` import
   `l5gntools.dbsafe`, and pipeline scripts run with the pipeline dir on
   `sys.path`, not the repo root. Now `.venv/bin/python` throughout. (The same
   bare `python3` was in `PRODUCER_SETUP.md` §9 and is fixed there too.)
2. **Item A could fail for the wrong reason.** `PRAGMA journal_mode` only reports
   `wal` after a read/write connection from the new code has opened that vault.
   Added step 0.
3. **Item A wrote to the live vault unnecessarily.** The original held the lock
   with `BEGIN IMMEDIATE` *plus* an `INSERT INTO review_queue`, needing a
   remembered `ROLLBACK`. `BEGIN IMMEDIATE` alone takes the lock; the INSERT is
   gone.
4. **Paths were hardcoded** to `~/vault/chronicler.db` in a system that is
   otherwise config-driven. Now `$VAULT`, from `run.py config`.

Also added: the optional-extras prerequisites (B and D need `[viewer]` /
`[review]`), and `run.py backup` before item D's live-vault migration, per
DECISIONS 0005/0006.
