> **ARCHIVED** 2026-07-20 · completed pair · brief: `docs/archive/COWORK_BRIEF_build_round_1.md`
> Superseded by commit `cdd7df4` and the rounds after it · Original purpose: what round 1
> built. Ran on a producer rig with no live vault and no network path to the knight, so
> the live-vault steps are analysis and runbooks, not executed work — don't read them as
> done.
> Its gate counts were true on 2026-07-18 and are now wrong; that staleness is expected
> and is exactly why archived docs sit outside `auditor_doc_claims`' scan
> (`docs/README.md` §3). Chromium-absent on the knight (Task E) remained open and is
> folded into round 3. Read as testimony about a moment, not as status.

# Cowork build round 1 — report (2026-07-18)

**Execution constraint up front:** this Cowork session ran on the **gaming rig**
(`LucasGoonPC`, a *producer*) in a Linux sandbox with **no live vault and no network
path to the knight** (`l5gn-castle` doesn't resolve). So the live-vault steps — serving
Datasette against the real DB, taking a real off-box snapshot, running the pipeline
(with the new relink stage) against the vault, and scraping Gemini on the knight —
could not be *executed* here. All five tasks were **built and hermetically tested
in-sandbox** (every new tester constructs a throwaway SQLite DB / synthetic input), and
the live invocations are handed off as documented runbooks in `KNIGHT_PLAYBOOK.md` §10.

**Working rule honoured: BUILD, then STOP before committing.** Every change sits in the
working tree, **staged/uncommitted**, for Tim's review. No `git commit` was run.
`python verify.py` is **GREEN** (5 auditors + 19 testers).

**DO NOT TOUCH list honoured:** no edits to `render_md.py`'s direction, `sync_back()`,
the `render_log` base, or the `--no-syncback` belt. The sync-back guarded state stands
exactly as it was (per DECISIONS 0008: it can't be removed until the 0007 stage-2 write
endpoint exists to receive rulings, which was **not** in this round).

---

## Status at a glance

| Task | State | Where |
|---|---|---|
| **D** — `auditor_doc_claims.py` | ✅ **done + verified** | `auditors/auditor_doc_claims.py`, gate green |
| **C** — off-box `VACUUM INTO` backup | ✅ **done + verified** (hermetic) | `l5gntools/backup.py`, `run.py backup` |
| **A** — Datasette read surface | ✅ **done + verified** (hermetic) | `l5gntools/viewer.py`, `run.py serve` |
| **B** — fold relink into pipeline | ✅ **done + verified** (hermetic) | `run_pipeline.py` STAGES |
| **E** — Gemini scrape stage | ✅ built; ⚠ chromium unverifiable here | `l5gntools/scrape.py`, `run.py scrape` |

Suggested order from the brief (D, C, A, B, E) was followed. Nothing here was run
against the live vault; all live steps are in the playbook runbook (§10).

---

## Task D — `auditor_doc_claims.py` (done + verified)

The estate's whole point is catching drift between what's *said* and what's *done*, yet
nothing checked the docs against the code — HANDOFF once claimed 18 testers when
`verify.py` had 14, and only a cold read caught it. This closes that self-referential
gap.

**What it does.** Fails the gate when a doc's compound **"N auditors + M testers"** claim
contradicts `verify.py`'s registered `AUDITORS` / `TESTERS` lists (the single
unambiguous source of truth for those numbers). It is deliberately **narrow and
mechanical** — one claim class, no prose parsing (per the brief: *a small auditor that
always runs beats a large one that rots*). Registered in `verify.py`'s `AUDITORS`; runs
like any other auditor.

**The false-positive guard, proven.** The compound pattern is specific enough that a
*narrative* mention of a past count — e.g. the brief's own "HANDOFF once claimed 18
testers when verify.py had 14" — is **not** matched; only a present-tense assertion of
both counts together, in order, trips it. `tests/tester_doc_claims.py` asserts exactly
this (detects the compound claim, ignores the narrative line, ignores a bare standalone
"14 testers", and computes the right file:line for a mismatch).

**It did its job on first run.** It fired on the two live stale claims —
`HANDOFF.md:10` ("4 auditors + 18 hermetic testers") and `NEXT_SESSION_PLAN.md:35`
("4 auditors + 14 testers"). I corrected exactly those two to the final `5 auditors +
19 testers` to green the gate.

**Stale-count sweep (Task D.4 — reported, NOT mass-edited; Tim rules on each).** Beyond
the auditor's scope, `HANDOFF.md:9` and `NEXT_SESSION_PLAN.md:13` both still say **"All
16 planned tasks are done."** That is a *task* count (not auditors/testers), so the
auditor doesn't govern it — but it is now arguably stale after this round added five
tasks. Flagging, not choosing.

---

## Task C — off-box `VACUUM INTO` backup (done + verified, hermetic)

The knight holds the only live vault; its one off-box copy had drifted since the knight
became primary (DECISIONS 0005/0006), so everything ingested since had **no** off-box
copy — a live loss risk. Fix built in `l5gntools/backup.py` (a writer, outside the
read-only scanner contract, never registered as a scanner).

- **Atomic, consistent snapshot** via SQLite `VACUUM INTO` — safe while the DB is live,
  unlike a raw file copy. The **source is opened `mode=ro`**, so a backup can never
  mutate the vault.
- **Dated filenames** (`chronicler-YYYYMMDDTHHMMSSZ.db`, lexically == chronologically
  sortable) + **keep-last-N** (default 7, floored at 1 so it never wipes the only
  generation).
- **Paths resolved from `CHRONICLER_HOME`**, never hardcoded (DECISIONS 0007
  consequence a).
- **`run.py backup`** standalone command, **and** an automatic **`[1/3]` pre-flight
  inside `run.py ingest`** (skippable with `--skip-backup`): a missing DB (first ingest)
  is a clean skip; a snapshot failure **aborts** before mutating anything; a push
  failure warns loudly but keeps the local snapshot and doesn't block ingest.

**Tim's two decisions, applied:** off-box destination is **config-driven** — a
`backup_target` key in `local.json` (candidate `l5gn-castle:vault/Chronicler_Backup`
over the existing transport) — and the snapshot **auto-pushes every run** (with
`--no-push` to stage + print instead).

**Verified hermetically** (`tests/tester_backup.py`): snapshot is a valid, openable,
complete copy; source untouched; refuses an existing target and a missing source
loudly; keep-last-N keeps the newest set and floors at 1; path/target resolution honours
`vault` / `chronicler_home` / `CHRONICLER_DB_PATH`; `make_backup` end-to-end with and
without a `backup_target`.

---

## Task A — Datasette read surface (done + verified, hermetic)

The DB had never been queryable — the INTENT §2 falsification test couldn't be run at
all. This is DECISIONS 0007 **stage 1** (read only; the stage-2 write endpoint is
explicitly **not** built this round). Built in `l5gntools/viewer.py` + `run.py serve`.

- **Read-only by construction:** launched **`--immutable`**, which cannot write the DB,
  so it cannot violate single-writer — a mode, not a convention.
- **Optional `[viewer]` extra** (`datasette`) added to `pyproject.toml`, matching the
  existing `[chronicler]` / `[scrape]` extras pattern — never in the stdlib-only core or
  default install. Absent → skips cleanly + loudly with the install hint.
- **Binds `0.0.0.0`** so the headless knight answers on both its `100.x` tailnet address
  and its `192.168.x` LAN address (per 0007).

**Report (Task A deliverable):**

- **Command:** `python run.py serve` → runs `datasette serve --immutable <vault> -h
  0.0.0.0 -p 8001` (DB path resolved from `CHRONICLER_HOME`).
- **URL from a phone:** `http://<knight-100.x>:8001/` (tailnet, cellular) or
  `http://<knight-192.168.x>:8001/` (LAN, work rig).
- **Example query answering a real question** (threads linked to a project):
  ```sql
  SELECT thread_id, title, created_at, project_confidence
  FROM threads
  WHERE project_link = 'L5GN_Armory_v4'
  ORDER BY created_at DESC;
  ```

**Verified hermetically** (`tests/tester_serve.py`): the argv is a `datasette serve`
invocation, always carries `--immutable` followed by the DB path, binds `0.0.0.0`,
passes the port as a string, opens the DB exactly once (never mutable); dep-absent
detection returns a bool; DB path is config-driven.

---

## Task B — fold relink into the pipeline (done + verified, hermetic)

**Safety finding first (Task B.1), from reading `relink.py`:**

- **What it needs:** *not* embeddings/playwright. relink is effectively **stdlib-only**
  (its only non-stdlib imports are the local `db` and `build_activity`, both stdlib
  underneath). Its real prerequisites are the **DB** and the **project registry JSON**
  (`REGISTRY_PATH`; relink `SystemExit`s if it's missing).
- **Safe to run every pass? Yes.** Dry-run is relink's own default, so the stage passes
  `--apply`. It is **idempotent**: winners become `project_confidence='evidence'`
  (LOCKED — skipped next run), and human-ruled threads (`confirmed`/`rejected`/
  `reassigned` on a link queue row) are never re-touched. Repeated `--apply` runs
  converge.

**Therefore it's a *standing* stage, not a heavy-dep-gated one.** Because there's no pip
dependency to gate, the "skip cleanly and loudly if the dep is absent" contract maps to
the **registry file existing**: `has_registry()` gates the stage, and it skips (visibly)
when the registry is absent rather than crashing.

**Wiring:** added `("relink", "relink", "relink.py", ["--apply"], has_registry)` to
`run_pipeline.py`'s `STAGES`, positioned **after `set_substantive`, before `render`** so
the rendered `.md` reflects the fresh links in the same pass. Added a `--skip-relink`
flag consistent with the other stages, and updated the stage-order docstring. This is
what lifts freshly-ingested (and, via Task E, freshly-scraped) threads out of
"unlinked" automatically.

**Verified hermetically** (`tests/tester_relink_stage.py`): the stage is registered with
the right script/argv (`--apply`), positioned between `substantive` and `render`, gated
on `has_registry`; the gate returns True when the registry file is present and False
when absent; `--skip-relink` drops the stage from the active set.

**⚠ Flag (Tim to verify on the knight, not changed here — out of scope per brief):**
relink's `REGISTRY_PATH = CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" /
"project_registry.json"` moves with `CHRONICLER_HOME`. With `CHRONICLER_HOME=/home/l5gn/
vault` it resolves to `/home/L5GN/.intel_sync/...`, which may not be where the registry
actually sits on the knight. If it's elsewhere, the stage will simply **skip** (cleanly)
rather than link. Confirm the path in the same env the pipeline runs relink in.

---

## Task E — Gemini scrape stage on the knight (built; chromium status load-bearing)

Design-thread decision: **the URL list travels to the knight; the knight scrapes.**
`scrape_gemini_share.py` drives a *headless* browser against the *public* share URL and
rejects the session-cookie route — no logged-in session required, so a headless Ubuntu
box can scrape directly. Keeps vault input originating only on the writer (single-writer
doctrine) and moves a tiny `urls.txt` instead of megabytes of JSON. Built in
`l5gntools/scrape.py` + `run.py scrape`.

- **playwright-gated:** if playwright (or chromium) is absent the stage is
  un-runnable — exactly the Layer-C dormant-dep trap — so `run.py scrape` **reports it
  and skips loudly** rather than silently no-opping.
- **Flow wired:** `urls.txt` → `run.py scrape` → `CHRONICLER_HOME/scraped_gemini/`
  (the exact intake dir the pipeline's reconcile stage already consumes) → `run.py
  ingest` → (Task B) relink links the new threads. Paths resolved from `CHRONICLER_HOME`.
- **Idempotency preserved, not re-solved:** the script already skips already-scraped
  share-ids (`--force` to redo) and is batch-native; `run.py scrape` just forwards
  `--force` / `--timeout`.
- **Manual steps stay Tim's** (out of scope for automation this round): copying share
  links out of the Gemini menu into `urls.txt`, and un-sharing them afterward. The
  playbook documents where `urls.txt` lives (`CHRONICLER_HOME/urls.txt` on the knight;
  ship with `scp urls.txt l5gn-castle:vault/urls.txt`).

**Report (Task E deliverable):**

- **Is chromium installed on the knight? UNKNOWN — could not be verified from here.**
  This session ran on the gaming rig, not the knight. This is load-bearing: without
  chromium the stage is silently un-runnable, so it **must be confirmed on the knight**.
  The exact install + confirm sequence (`pip install -e '.[scrape]'` →
  `playwright install chromium` → `playwright install-deps` → import check) is now in
  `KNIGHT_PLAYBOOK.md` §10.3.
- **Exact command sequence for one batch:** `scp urls.txt l5gn-castle:vault/urls.txt`
  → (on knight) `python run.py scrape` → `python run.py ingest`.
- **Where `urls.txt` lives:** maintained on the gaming rig; shipped to
  `CHRONICLER_HOME/urls.txt` on the knight (overridable via a `urls_file` key in
  `local.json`, or `run.py scrape /path/urls.txt`).

**Verified hermetically** (`tests/tester_scrape_stage.py`): dep detection returns a
bool; the scraper script exists where pointed; argv shape is correct with flags only
when asked; scraped dir == the pipeline intake dir; unresolved `CHRONICLER_HOME` raises
loudly rather than defaulting.

---

## Gate + one fix after handoff

`python verify.py` → **GREEN**, 5 auditors + 19 testers, all hermetic. Auditors:
`auditor_cli_contract`, **`auditor_doc_claims`** (new), `auditor_readonly`,
`auditor_stdlib`, `auditor_tool_contract`. New testers: `tester_doc_claims`,
`tester_backup`, `tester_serve`, `tester_relink_stage`, `tester_scrape_stage`.

**Post-handoff fix:** Tim's Windows run surfaced `tester_backup` raising
`PermissionError [WinError 32]` — the tester opened a SQLite connection to read the
snapshot back and never closed it, so Windows couldn't delete the temp file during
cleanup (harmless on Linux). Fixed: the read-back connection is now `try/finally`
closed, and I swept the rest of the tests for other inline unclosed connections (none).
Gate green again.

---

## Files changed this round (uncommitted, in the working tree)

```
NEW  auditors/auditor_doc_claims.py       (Task D — doc-vs-code count auditor)
NEW  l5gntools/backup.py                  (Task C — VACUUM INTO snapshot writer)
NEW  l5gntools/viewer.py                  (Task A — Datasette read-surface helpers)
NEW  l5gntools/scrape.py                  (Task E — Gemini scrape wiring)
NEW  tests/tester_doc_claims.py           (Task D hermetic gate)
NEW  tests/tester_backup.py               (Task C hermetic gate)
NEW  tests/tester_serve.py                (Task A hermetic gate)
NEW  tests/tester_relink_stage.py         (Task B hermetic gate)
NEW  tests/tester_scrape_stage.py         (Task E hermetic gate)
NEW  docs/COWORK_BRIEF_1_REPORT.md        (this file)
MOD  run.py                               (+ backup / serve / scrape cmds, ingest pre-flight, help)
MOD  verify.py                            (register auditor_doc_claims + 5 new testers)
MOD  pyproject.toml                       (+ [viewer] optional extra: datasette)
MOD  chronicler/pipeline/run_pipeline.py  (Task B — relink STAGE, --skip-relink, docstring)
MOD  docs/KNIGHT_PLAYBOOK.md              (§10 serve/backup/scrape + chromium install; §7/§9 updates)
MOD  docs/HANDOFF.md                      (18 -> 19 testers, doc-claims auditor)
MOD  docs/NEXT_SESSION_PLAN.md            (14 -> 19 testers, doc-claims auditor)
```
