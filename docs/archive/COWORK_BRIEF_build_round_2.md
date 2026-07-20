> **ARCHIVED** 2026-07-20 · completed pair · report: `docs/archive/COWORK_ROUND_2_REPORT.md`
> Superseded by the as-built code (commit `433a5f1`) + DECISIONS 0010–0013 · Original
> purpose: ship the project registry, reset the untrusted `project_link` values (0011),
> and build the narrow write endpoint (0007 stage 2) — the round's main deliverable.
> Read as the request, not current truth: it assumes the flat project model that
> DECISIONS 0012 replaced with three-tier program→project→repo, and its treatment of the
> `exact` row was flagged by the report as needing a ruling (round 3 Task D).

# Cowork brief — build round 2: registry live, links reset, write endpoint

**Origin:** design thread, 2026-07-18, following the project-registry design session.
Read `docs/DECISIONS.md` entries 0007, 0008, 0010, 0011 and `docs/INTENT.md` before
starting — this brief assumes that context, doesn't restate it in full.

**Time-boxed.** Weekly usage is near its limit; this is likely the last full session
before reset. **Priority order below is deliberate — if time runs out, stop after the
task you're on and report clearly what's done vs pending. Do not rush Task C (the
write endpoint) to "looks done" at the cost of leaving Task B's reset half-applied.**

**Working rule: BUILD, then STOP before committing** (same as round 1). Get each task
to green / verified, leave staged/uncommitted, report clearly. Do not `git commit`.

**DO NOT TOUCH this round:** `render_md.py`, `sync_back()`, the `render_log` base.
Sync-back removal (DECISIONS 0008) is gated on the write endpoint existing and being
proven — this round builds the endpoint, it does not yet retire sync-back. That's a
round-3 task once Tim has tinkered with and trusts the new endpoint.
 
---

## Task 0 — Ship the registry, confirm the path (fast, do first)

1. `config/project_registry.json` exists on the gaming rig (gitignored, not in git).
   Confirm it's present and valid JSON before shipping.
2. On the knight, confirm the exact path `relink.py` expects:
   ```
   python3 -c "from chronicler.pipeline import relink; print(relink.REGISTRY_PATH)"
   ```
   (Run from `chronicler/pipeline/` if the bare `from db import` fails outside that
   directory — this import-context fragility was flagged in round 1 and not yet fixed;
   note it if it recurs, don't silently work around it without reporting.)
3. `scp config/project_registry.json <that resolved path>` and verify byte-for-byte
   (hash both sides, same method as `local.json` verification in round 1).

---

## Task A — Investigate relink's write/lock model before touching any data

**Report first, do not reset yet.** Round 1 found relink is "idempotent — winners
become locked evidence and are skipped next run; human-ruled threads are never
re-touched." That "locked" behavior means simply re-running relink will NOT undo
existing `project_link`/`project_confidence` values from before the registry existed
— an explicit reset is required first, and it must target the right columns.

1. Read `relink.py` and report exactly: which table(s)/column(s) it writes when it
   applies a link (`threads.project_link`? `threads.project_confidence`? a separate
   `link_evidence` or `review_queue` row?), and what marks a thread as "locked" /
   already-resolved so relink skips it on a future run.
2. Confirm: does resetting `project_link`/`project_confidence` to NULL fully unlock a
   thread for re-evaluation, or is there a separate lock flag/table that also needs
   clearing? Report the precise reset statement needed — don't guess column names.
3. Sanity-check against the live census (round-1 investigation): 0 threads currently
   have `project_confidence='manual'`. If Task A's read confirms this is still true,
   the reset in Task B is safe by INTENT's own logic — nothing human-ruled exists to
   lose, only automation-derived (`evidence`/`fuzzy`/`exact`) rollups, which are
   *derived data* (INTENT §5: "the derived is free... rebuild, never merge"). If any
   `manual` rows *do* exist now, stop and report before resetting — do not clear a
   human ruling. (A fresh `project_confidence` census on 2026-07-19 shows: null/blank
   997, `evidence` 141, `none` 37, `fuzzy` 7, `exact` 1 — no `manual` bucket present,
   consistent with the round-1 finding. Re-confirm at execution time regardless.)
4. **Data-quality flag, check before relying on dates:** a spot-check found `created_at`
   is NULL for most older `gemini-work` threads — only populated from ~2026-05-30
   onward, suggesting an ingestion-pipeline change partway through. Report whether this
   affects relink or era-bucketing logic; don't assume all threads have a usable date.

---

## Task B — Backup, reset, re-run relink, report new coverage

**Sequencing matters: backup before reset, reset before relink.**

1. Run the existing `run.py backup` (round 1) as a pre-flight snapshot before touching
   live data. Confirm it succeeds and lands a dated snapshot before proceeding.
2. Apply the precise reset from Task A's findings — clear the automation-derived
   project-link rollup (not `link_evidence`, which is raw evidence and stays; only the
   derived assignment). Report exact row count affected.
3. Re-run the `relink` pipeline stage fresh against the newly-shipped registry.
4. Report the new coverage numbers in the same shape as the original investigation:
   `link_evidence` breakdown by signal, `project_confidence` distribution, and —
   critically — the honest substantive-thread coverage (the ~8% figure from INTENT §2
   was `27/332` substantive threads before any of this). Report the new ratio plainly;
   don't round up or editorialize if it's still low. This number is what INTENT gets
   corrected to next session.
5. Flag anything in `review_queue` that looks like it should auto-resolve now that real
   registry entries exist (e.g. `project_link` type rows where the registry gives an
   exact name match) vs. what still needs a human ruling — this shapes what Task C's
   UI actually needs to surface.

---

## Task C — The write endpoint (DECISIONS 0007 stage 2) — the main deliverable

Build per 0007's spec, modeled on the `l5gn-mesh-vertex-3_prod` spine (FastAPI +
uvicorn + SQLAlchemy over SQLite, static HTML mounted via `StaticFiles`), stripped
down and pointed at the vault. **Functional over polished — Tim will tinker with the
UI himself tomorrow. Prioritize correctness of the write path over visual design.**

**Scope for this round — project-link rulings only.** Not thread_grouping, not
close_suggestion, not reconciliation_gap. Those stay read-only-via-Datasette for now.
This keeps the write surface narrow, matching 0007's "surfaces only review_queue,
writes only ruling columns" principle, and fits the time budget.

**Expectation-setting, not a scope change:** the real pending backlog for this
endpoint is `project_link` (136) + `link_ambiguous` (15) + `link_downgrade` (4) =
**~155 items**, not the ~19 estimated earlier (that figure only counted the last two).
Don't try to clear it this session — the endpoint existing and working is the
deliverable; working through 155 rulings is Tim's job over the following days.
Separately, `close_suggestion` has 880 pending and `thread_grouping` 192 pending —
both explicitly out of scope, noted here only so their size doesn't get mistaken for
project-link progress (they are a different pipeline stage entirely; do not conflate
"thread grouped" with "thread project-linked" in any report).

1. **Read side:** surface pending `project_link`-type `review_queue` rows (post-Task-B,
   so the queue reflects the new registry) plus `link_ambiguous`/`link_downgrade` rows,
   each showing enough context to rule on it — thread title, snippet or link to the
   Datasette row, the registry's candidate project(s) if any matched.
2. **Write side:** a ruling submits `project_link` (a registry `id`) and
   `project_confidence='manual'` for a thread. **Writes ONLY these two columns.**
   Never touches `link_evidence`, `review_queue` status of *other* rows, or anything
   pipeline-owned. This is what makes single-writer safe by column-scope (DECISIONS
   0007) rather than by lock.
3. **Estate/account-agnostic per DECISIONS 0010** — do not filter, group, or gate the
   UI by estate or account. A thread from any estate/account may be assigned to any
   project. Do surface the account per-thread (informational), never hide it.
4. **Path resolution:** DB path from `CHRONICLER_HOME`, exactly like `serve`/`backup` —
   never hardcoded (round 1's viewer.py/backup.py are the reference pattern).
5. **Bind for Tailscale + LAN**, same as `run.py serve` (`0.0.0.0`, report the port).
6. Add a hermetic tester covering: the write path only touches its two columns (seed a
   thread, apply a ruling, assert every other column unchanged), and that project_link
   values only accept ids present in the shipped registry (reject unknown ids loudly,
   don't silently write garbage).
7. Wire it as `run.py review` (or similar, consistent with `serve`/`backup`/`scrape`
   naming) — report the exact command and URL, same as round 1's Task A report shape.

---

## Task D — Stretch, only if time remains after C is solid

One real end-to-end smoke test: apply a single actual ruling through the new endpoint
against the **live** vault (not a copy) for one genuinely-pending thread, and confirm
it's visible via `run.py serve` afterward. This is the first real proof the write path
works outside a hermetic test. **Skip this task entirely if the budget is tight** — a
untested-but-correct-by-code-review endpoint is a fine place to stop; Tim can run the
first live ruling himself tomorrow.

---

## Reporting

At minimum, before the session ends, report: which tasks reached green, the new
project-link coverage numbers (Task B.4), the exact command + URL for the write
endpoint (Task C.7), and anything left in a partial state. Do not commit — everything
stops at staged, for Tim's review.
