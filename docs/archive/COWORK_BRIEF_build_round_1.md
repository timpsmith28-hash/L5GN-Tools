> **ARCHIVED** 2026-07-20 · completed pair · report: `docs/archive/COWORK_ROUND_1_REPORT.md`
> Superseded by the as-built code (commit `cdd7df4`) + `docs/ARCHITECTURE.md` · Original
> purpose: the first post-trinity build brief — Datasette read surface (DECISIONS 0007
> stage 1), relink folded into the pipeline, off-box backup (0005/0006),
> `auditor_doc_claims`, and the Gemini scrape stage. All five tasks landed.
> Read as the record of *what was asked*, frozen at the moment of asking — not as work
> outstanding. Task E's chromium prerequisite was left open here and is **still open**:
> round 3 did not address it, and the install steps live in `KNIGHT_PLAYBOOK.md` §10.3
> unwalked. (An earlier version of this stamp said round 3 Task F carried it. That was
> wrong — corrected 2026-07-20.) Where this brief and the trinity disagree, the trinity
> wins.

# Cowork brief — build round 1 (post-trinity)

**Origin:** design thread, 2026-07-18, after the INTENT/ARCHITECTURE/DECISIONS trinity
landed. Authoritative rationale is in `docs/DECISIONS.md` (entries referenced below)
and `docs/ARCHITECTURE.md`. Where this brief and those docs disagree, the docs win.

**Working rule this round: BUILD, then STOP before committing.** Get each task to
green (`python verify.py` passes) and leave it staged/uncommitted for Tim's review.
Do **not** run `git commit`. Tim commits after reviewing the diff.

**Rules:**
- `python verify.py` must be green before you consider a task done.
- Any status claim you write into `docs/` must be checked against the code, not
  recalled. (This round *adds an auditor that enforces exactly that* — Task D.)
- New pipeline code stays stdlib-only where it can, so its tester runs in the core
  gate. Where a task needs a dependency (embeddings, playwright), gate the stage so it
  **skips cleanly and loudly** when the dep is absent — never silent-fail.

**DO NOT TOUCH this round — sync-back.** DECISIONS 0008 rules that rendered `.md` is
read-only output and sync-back is slated for removal — *but only after* the write
endpoint (0007 stage 2) exists to receive rulings, which is NOT in this round. Until
then the current guarded state stands. Do not drop the `--no-syncback` belt, do not
alter `sync_back()` or the `render_log` base, do not "tidy" `render_md.py`'s direction.
Leave it exactly as it is.
 
---

## Task A — Datasette read surface (DECISIONS 0007 stage 1)

The DB has never been queryable; the INTENT §2 falsification test can't be run at all.
This is the highest-value task because it's the first time the corpus becomes visible.

1. Add Datasette as an **optional** dependency (its own extra, e.g.
   `pip install -e .[viewer]` or a documented `requirements-viewer.txt` — match
   whatever pattern `chronicler`'s extras already use; check `pyproject.toml` first).
   It must not enter the stdlib-only core or the default install.
2. Add a `run.py serve` (or similarly-named) command, OR a documented one-line
   invocation in the playbook, that launches Datasette against the live
   `chronicler.db` **read-only** (`--immutable` — this is what guarantees it can't
   violate single-writer), resolving the DB path from `CHRONICLER_HOME`, never
   hardcoded.
3. Bind for Tailscale reach: host `0.0.0.0` so the knight answers on both its
   `100.x` tailnet address and its `192.168.x` LAN address (per 0007). Document the
   URL to hit from a phone.
4. **Do not build the write endpoint** (0007 stage 2) this round — read surface only.
   Datasette `--immutable` is structurally incapable of writing, which is the point.

Report: the exact command, the URL, and one example query that answers a real
question (e.g. "threads linked to project X") so Tim can run the falsification test.

---

## Task B — Fold `relink` into the pipeline (ARCHITECTURE §7; long-standing follow-up)

Fresh ingest lands threads unlinked; `relink.py` exists and has been run manually
(`relink_applied.txt` / `relink_dryrun.txt` in the old data dir). Coverage is ~8% of
substantive threads — this is the sharpest usability edge.

1. **Report first, before wiring:** read `relink.py` and state what it does, what it
   needs (embeddings? which dep?), and — critically — whether it is safe to run on
   *every* pipeline pass or whether it has rescan-and-apply semantics that make
   repeated runs dangerous. This determines whether it becomes a standing stage or a
   gated one.
2. If safe: add it as a stage in `run_pipeline.py`'s `STAGES`, behind its dependency,
   skipping cleanly and loudly if the dep is absent (same pattern as Layer C). Add a
   `--skip-relink` flag consistent with the other stages.
3. Add a tester covering the stage wiring (dep-present and dep-absent paths).

Note the interaction with Task E: relink is what would lift new scraped threads out of
"unlinked." Wiring it means the scrape stage's output gets linked automatically.

---

## Task C — Off-box backup for the vault (DECISIONS 0005/0006; ARCHITECTURE §7)

The knight holds the only live vault. Its one off-box copy is manual and has drifted
since the knight became primary — everything ingested since the move has no off-box
copy. This is a live loss risk, not hardening.

1. Add an automatic `VACUUM INTO` snapshot step (atomic, consistent — safe to copy
   while the DB is live, unlike a raw file copy). It should run **before** each ingest
   as a pre-flight, and/or as a standalone `run.py backup` command. Resolve paths from
   `CHRONICLER_HOME`.
2. Land the snapshot in a location that gets it **off the knight** — confirm with Tim
   where (candidate: pushed back to `L5GN-Castle\...\Chronicler_Backup` over the
   existing transport, refreshing the stale copy). Do **not** put a live SQLite file in
   any file-sync service — snapshot-then-move only.
3. Keep at least one prior generation (don't overwrite the only backup with a
   potentially-bad one). A simple dated filename + keep-last-N is enough.
4. Tester for the snapshot step (produces a valid, openable copy; path resolution).

---

## Task D — `auditor_doc_claims.py` (ARCHITECTURE purpose; the self-referential gap)

The estate's whole point is catching drift between what's said and what's done, yet
nothing checks the docs against the code — HANDOFF once claimed 18 testers when
`verify.py` had 14, and only a cold read caught it.

1. Add an auditor that fails the gate when a machine-checkable documented claim
   contradicts the code. Start **narrow and mechanical**: the count of registered
   auditors/testers, wherever it's asserted in `docs/` or `README.md`, checked against
   `verify.py`'s actual `AUDITORS` / `TESTERS` lists.
2. Register it so it runs in `verify.py` like any other auditor.
3. A small auditor that always runs beats a large one that rots — extend only to
   claims with a single, unambiguous source of truth. Do not try to parse prose.
4. While here: grep `docs/` and `README.md` for stale counts and report them (don't
   mass-edit — Tim rules on each). Known: `HANDOFF.md` may still say 18.

---

## Task E — Gemini scrape stage on the knight (settles the transport question)

Decision from the design thread: **the URL list travels to the knight; the knight
scrapes.** `chronicler/scrape_gemini_share.py`'s own docstring establishes this is
correct — it drives a *headless* browser against the *public* share URL and explicitly
rejects the session-cookie route, so **no logged-in session is required** and a
headless Ubuntu box can scrape directly. This keeps vault input originating only on the
writer (single-writer doctrine) and moves a tiny text file instead of megabytes of JSON.

1. **Verify the dormant dependency first.** The scrape needs `playwright` +
   headless chromium (`playwright install chromium` and, on Ubuntu,
   `playwright install-deps`). Check whether these are present on the knight. If not,
   this stage is silently un-runnable — exactly the Layer-C dormant-dep failure. Report
   status explicitly; add the install step to `KNIGHT_PLAYBOOK.md`.
2. Wire the flow so Tim's loop is: maintain `urls.txt` on the gaming rig → it travels
   to the knight via the existing transport → knight runs the scrape into the
   `scraped_gemini/` intake location the pipeline already consumes → pipeline ingests →
   (Task B) relink links the new threads. Document each step; make the scrape a
   `run.py` subcommand or a documented playbook invocation.
3. The script is already idempotent (skips already-scraped share-ids; `--force` to
   redo) and batch-native — preserve that; don't re-solve it.
4. **Manual steps stay Tim's and are explicitly out of scope for automation this
   round:** copying share links out of the Gemini menu into `urls.txt`, and
   un-sharing them afterward. Just document where `urls.txt` lives and how it reaches
   the knight.

Report: whether chromium is installed on the knight (yes/no is load-bearing), the
exact command sequence for one batch, and where `urls.txt` should live on each machine.

---

## Suggested order

D and C are small and self-contained (good warm-up, and D protects every later doc
claim). A is the highest *value* (makes the corpus visible). B and E interlock (relink
lifts scraped threads out of unlinked), so do B before E, or at least report B's
safety finding before wiring E. Nothing here commits — all five stop at green,
staged, for review.
