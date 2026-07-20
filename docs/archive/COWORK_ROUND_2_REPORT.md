> **ARCHIVED** 2026-07-20 · completed pair · brief: `docs/archive/COWORK_BRIEF_build_round_2.md`
> Superseded by commit `433a5f1` + DECISIONS 0012–0016 · Original purpose: what round 2
> built — the review write endpoint (proven column-scoped in `tester_review`), the
> validated registry, and copy-paste runbooks for backup / reset / relink.
> Sandboxed again with no path to the knight, so Task 0's *ship*, Task B and Task D are
> **runbooks handed off, not executed**. Two flags it raised are answered elsewhere: the
> `project_link` id-vs-`canonical_name` divergence and the PROTECTED-`exact`-row question
> both go to round 3 Task D. The registry sha256 recorded here is only valid until the
> registry next changes. Read as testimony, not status.

# Cowork build round 2 — report (2026-07-18)

**Execution constraint up front:** this Cowork session runs in a sandbox with **no
network path to the knight** (`l5gn-castle` doesn't resolve; no Tailscale, no SSH
key). So the live-vault steps — Task 0 *ship*, all of Task B, Task D — could not be
*executed* here. They are analysed and handed off as **exact copy-paste runbooks**
below. Task A (code reading) and Task C (build the endpoint) were fully doable and
are **done + verified in-sandbox** against the local proof DB. This matches the
established split (DECISIONS 0011 notes the design thread likewise "had no execution
access to the live vault").

**Nothing was committed.** All changes sit in the working tree, uncommitted, for your
review. `verify.py` is **GREEN** (5 auditors + 20 testers). I could not `git add`
from the sandbox (a stale `.git/index.lock` I lack permission to remove) — stage them
yourself when you review.

**DO NOT TOUCH list honoured:** no edits to `render_md.py`, `sync_back()`, or the
`render_log` base.
 
---

## Status at a glance

| Task | State | Where |
|---|---|---|
| **A** — relink write/lock model + reset | ✅ done (analysis) | §Task A below |
| **0** — validate registry | ✅ done (local) | valid JSON, 13 ids, sha256 below |
| **0** — ship to knight | ⏳ runbook | §Task 0 runbook |
| **C** — write endpoint | ✅ **done + verified** | `chronicler/review/`, gate green |
| **B** — backup/reset/relink | ⏳ runbook | §Task B runbook |
| **D** — live smoke test | ⏳ runbook (stretch) | §Task D runbook |

**Write endpoint command + URL (Task C.7):**

```
python run.py review        # on the knight; binds 0.0.0.0:8002
```
`http://<knight-100.x>:8002/` (phone on tailnet) · `http://<knight-192.168.x>:8002/`
(work rig on LAN). Port **8002** by default — distinct from `serve`'s 8001 so both
run at once. Override with `--port`.

---

## Task A — relink's write/lock model, and the precise reset

### What relink writes when it applies a link

Read from `chronicler/pipeline/relink.py` (`apply_decision`). Per decision category:

- **auto_link:** `threads.project_link := <canonical_name>`,
  `project_confidence := 'evidence'`, `link_evidence_ids := <json>`. Inserts inline
  `link_evidence` rows (`producer_version='relink/1.0'`), upserts a `projects` row
  (`project_id = canonical_name`), and inserts an **informational** `review_queue`
  row `type='link_upgrade'`, `status='confirmed'`.
- **suggest:** `review_queue` `type='project_link'`, `status='pending'`; sets
  `threads.review_status='pending'`.
- **ambiguous:** `review_queue` `type='link_ambiguous'`, `status='pending'`;
  `review_status='pending'`.
- **downgrade:** `review_queue` `type='link_downgrade'`, `status='pending'`;
  `review_status='pending'`.

### What marks a thread "locked" / skipped on a future run

There are **two independent locks** (both in `run()` / `decide()`):

1. **Confidence gate.** `project_confidence in {'manual','exact'}` → `skip_manual` /
   `skip_exact` (PROTECTED, automation never overwrites). `project_confidence ==
   'evidence'` → `skip_evidence` (LOCKED — only a human may change an evidence link).
   This is why relink is idempotent: its own winners become `'evidence'` and are
   skipped next run.
2. **Human-ruling gate** (`human_ruled_threads()`). A thread is skipped (`skip_ruled`)
   if it has a `review_queue` row with `status IN ('confirmed','rejected',
   'reassigned')` **and** `type IN ('project_link','link_ambiguous','link_downgrade')`.
   Note relink's own `link_upgrade` rows are `status='confirmed'` but type
   `link_upgrade` — **excluded** from this gate, so they lock via confidence, not here.

### Does nulling `project_link`/`project_confidence` fully unlock a thread?

**For the confidence gate: yes.** `project_confidence = NULL` is read as `'none'` →
actionable. **For the human-ruling gate: no — it's separate.** A thread with a
confirmed/rejected/reassigned project-link queue row stays `skip_ruled` regardless of
confidence.

**But today that second gate is empty:** the only thing that creates human rulings is
the write endpoint, which didn't exist before this round. The census confirms **0
`manual`** rows. So nulling the confidence columns **is** sufficient to fully unlock —
*provided you re-confirm at execution time*:

```sql
-- Must return 0, or STOP: a human ruling exists and must not be cleared.
SELECT COUNT(*) FROM review_queue
 WHERE status IN ('confirmed','rejected','reassigned')
   AND type   IN ('project_link','link_ambiguous','link_downgrade');
```

### The precise reset statement

Clear the derived rollup on every thread **except** human-authority ones, matching
relink's own PROTECTED set (`manual`, `exact`):

```sql
-- 1) count first (this is the number to report)
SELECT COUNT(*) FROM threads
 WHERE COALESCE(project_confidence,'none') NOT IN ('manual','exact')
   AND (project_link IS NOT NULL OR project_confidence IS NOT NULL);

-- 2) the reset
UPDATE threads
   SET project_link       = NULL,
       project_confidence = NULL,
       link_evidence_ids  = NULL
 WHERE COALESCE(project_confidence,'none') NOT IN ('manual','exact');
```

Notes, all load-bearing:

- **`link_evidence` (raw evidence) is NOT touched** — correct per brief B.2. The reset
  only nulls the three derived columns on `threads`. (Relink's *own* next `--apply`
  will delete its prior `producer_version='relink/1.0'` inline rows per thread as
  normal idempotency — never S4/S5 raw evidence.)
- **⚠ The 1 `exact` row — decide before running.** The brief (A.3) lumps `exact` into
  "automation-derived," but `relink.py` treats `exact` as **PROTECTED, human-authority-
  equivalent** ("'exact' protected like 'manual'"). These disagree. My recommendation:
  **do not reset it.** relink will `skip_exact` it anyway, so resetting would just blank
  a link nothing re-derives. Eyeball that one thread; if you truly want it re-evaluated,
  change the `WHERE` to exclude only `'manual'`. **Flagging, not choosing** — per the
  brief's "don't guess" rule.
- **`threads.review_status`** leftover `'pending'` values aren't cleared by the reset
  (cosmetic; relink doesn't read it for decisions). Optionally `SET review_status='auto'`
  in the same UPDATE if you want a clean slate.
- **Optional queue cleanup:** prior relink `link_upgrade` (confirmed) rows accumulate
  and aren't auto-deleted. For a spotless baseline you *may*
  `DELETE FROM review_queue WHERE type='link_upgrade';` — optional, not required.

### `created_at` NULL — does it affect relink? (A.4)

**No crash, graceful degrade.** `relink` → `parse_thread_date(None)` → `None` →
`time_plausibility` returns a **neutral 0.7** (never 1.0), flagged `time:unknown` in the
evidence summary. Consequence: for the undated older `gemini-work` threads (created_at
only populated from ~2026-05-30), the **time signal is inert** — they can still be
linked by title/filename/alias evidence, but the era-discriminator that separates
same-vocabulary different-era projects (legacy vs current) does nothing for them.
**Don't build any era-bucketing report that assumes every thread is dated.**

---

## Task 0 — registry validated; ship runbook

**Local validation (done):** `config/project_registry.json` is **valid JSON**,
`sha256 = 64a492f45c0eaf416591dac84e18aa52a9afa6fdf1bae8db6fbdef3d2a3110ff`.
It yields **13 link-target ids** (10 top-level + 3 dict sub-projects):
`l5gn-os, chronicler-gas, chancellor, auditor-arbiter, mcf-solution-configurator,
mcf-company-context, wizforge-analytics, crystal-spire, l5gn-mesh-network,
l5gn-tools-chronicler, universal-content-pipeline, vertex-3, learning-ai-and-computers`.

**⚠ Registry data-quality note:** sub_projects are shaped inconsistently — `l5gn-os`
uses dicts *with ids* (link targets), but `crystal-spire` lists **bare strings**
("Smelt Gateway", etc.) with no id (**not** link targets). If you want those assignable,
give them ids. The endpoint handles both shapes (strings ignored as targets).

### ⚠ Where relink expects the registry — and why it's fragile

`relink.REGISTRY_PATH = CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" /
"project_registry.json"`, where `CHRONICLER_ROOT = CHRONICLER_HOME` (if set) else the
`chronicler/` dir. **The path moves with `CHRONICLER_HOME`:**

| `CHRONICLER_HOME` | resolved `REGISTRY_PATH` |
|---|---|
| *unset* | `<github_root>/L5GN/.intel_sync/project_registry.json` |
| `/home/l5gn/vault` | `/home/L5GN/.intel_sync/project_registry.json` ← probably **not** what you want |

Plus, `relink.py`'s bare imports (`from db import`) mean `from chronicler.pipeline
import relink` **fails from the repo root** — run it from `pipeline/`. So resolve the
real target **in the same env relink runs in**:

```bash
# on the knight, from the pipeline dir, with CHRONICLER_HOME set exactly as the
# pipeline sets it when it runs relink:
cd ~/L5GN-Tools/chronicler/pipeline
CHRONICLER_HOME=/home/l5gn/vault python3 -c "import relink; print(relink.REGISTRY_PATH)"
```

### Ship it (gaming rig → knight), then verify byte-for-byte

```bash
# from the gaming rig repo root
scp config/project_registry.json l5gn-castle:<PATH-FROM-THE-COMMAND-ABOVE>

# verify both sides match 64a492f4...
sha256sum config/project_registry.json                      # local
ssh l5gn-castle "sha256sum <PATH-FROM-THE-COMMAND-ABOVE>"    # remote — must equal
```

**Recommendation (kills the fragility):** set `CHRONICLER_REGISTRY_PATH` on the knight
to an explicit stable path, ship there, and point both the endpoint (already honours
it) and — in round 3 — relink at it. The new endpoint's resolver checks
`CHRONICLER_REGISTRY_PATH` first for exactly this reason.

---

## Task C — the write endpoint (done + verified)

Built in **`chronicler/review/`** (the writer subsystem — outside the l5gntools
read-only/stdlib scanner contract, so the auditors that scope to `SCANNERS` don't and
shouldn't apply to it). See `chronicler/review/README.md` for the full design.

**The guarantee, and how it's proven.** A ruling writes **exactly two columns** —
`threads.project_link := <registry id>` and `project_confidence := 'manual'` — and
touches nothing else pipeline-owned. That column boundary is the single-writer safety
(DECISIONS 0007), and `tests/tester_review.py` proves it: seed a thread with non-default
values in every column, apply a ruling, assert **only** those two columns changed and
every `link_evidence`/`review_queue` row is byte-for-byte unchanged. Unknown ids and
unknown threads are rejected loudly (nothing written).

**Verified in-sandbox against the proof DB — full HTTP path:**

- `GET /api/pending` → surfaces the pending project-link row *with account* (0010).
- `POST /api/rule {bad id}` → **HTTP 400**, "unknown project id …", nothing written.
- `POST /api/rule {valid}` → **HTTP 200**, writes the two columns, returns previous values.
- Ruled thread **drops off** `/api/pending` (via `manual` confidence — no `review_queue`
  write; the queue row was confirmed still `pending`).
- `projects` identity row upserted (FK target); static UI mounts at `/`; and
  `python run.py review` **boots uvicorn on `0.0.0.0:8002`** end-to-end.

**Gate:** `python verify.py` → **GREEN** (5 auditors + 20 testers, incl. the new
`tester_review`). Two stale doc-claims ("19 testers") were updated to 20 to keep the
doc-claims auditor green — that's the auditor doing its job.

**Scope respected (C):** project-link rulings only; estate/account-agnostic (0010);
config-driven paths (C.4); binds 0.0.0.0 (C.5). The real pending backlog is
`project_link` (136) + `link_ambiguous` (15) + `link_downgrade` (4) = **~155 items** —
*your* job to work through over the coming days; the endpoint existing is the
deliverable. `close_suggestion` (880) and `thread_grouping` (192) are a **different
pipeline stage** and out of scope — do not conflate "grouped" with "project-linked."

### ⚠ Flags for round 3 (decisions, not bugs to silently fix)

1. **`project_link` identifier divergence.** The endpoint stores the registry **id**
   (`crystal-spire`, per the brief). `relink.py` stores the **canonical_name**
   (`Crystal Spire`). Same project can end up as two `projects` rows / two spellings.
   Reconcile (simplest: switch relink to the id).
2. **Pending queue rows linger** after a manual ruling — by design (endpoint must not
   write `review_queue`). Cosmetic; the read query filters them. A pipeline-owned
   reconciliation could flip them to `confirmed` later.

---

## Task B — runbook (backup → reset → relink → report)

Run on the knight, **in order** (backup before reset, reset before relink). Ship the
registry (Task 0) first so relink reads the new one.

```bash
# 1) PRE-FLIGHT BACKUP — confirm a dated off-box snapshot lands before touching data
python run.py backup

# 2) CENSUS + SAFETY CHECK (sqlite3 on the vault)
sqlite3 /home/l5gn/vault/chronicler.db <<'SQL'
SELECT COALESCE(project_confidence,'(null)') c, COUNT(*) FROM threads GROUP BY c ORDER BY 2 DESC;
-- must be 0, else STOP (a human ruling exists):
SELECT COUNT(*) FROM review_queue
 WHERE status IN ('confirmed','rejected','reassigned')
   AND type   IN ('project_link','link_ambiguous','link_downgrade');
SQL

# 3) RESET — see Task A for the exact statement + the 'exact'-row decision.
#    Report the COUNT(*) the reset affects.

# 4) RE-RUN RELINK — dry first, review, then apply
cd chronicler/pipeline
CHRONICLER_HOME=/home/l5gn/vault python3 relink.py --out relink_dryrun.txt   # review this
CHRONICLER_HOME=/home/l5gn/vault python3 relink.py --apply
```

### Report the new coverage in the original shape (B.4)

```sql
-- link_evidence breakdown by signal
SELECT signal, COUNT(*) FROM link_evidence GROUP BY signal ORDER BY 2 DESC;

-- project_confidence distribution
SELECT COALESCE(project_confidence,'(null)') c, COUNT(*) FROM threads GROUP BY c ORDER BY 2 DESC;

-- honest substantive coverage. Baseline (INTENT §2) = 27/332 substantive threads
-- carrying an EVIDENCE LINK. substantive = >= 4 messages. Report the ratio plainly.
WITH sub AS (
  SELECT t.thread_id
    FROM threads t
    JOIN (SELECT thread_id, COUNT(*) n FROM messages GROUP BY thread_id) m
      ON m.thread_id = t.thread_id
   WHERE m.n >= 4
)
SELECT
  (SELECT COUNT(*) FROM sub)                                                   AS substantive_total,
  (SELECT COUNT(*) FROM sub WHERE thread_id IN (SELECT DISTINCT thread_id FROM link_evidence)) AS substantive_with_evidence_link,
  (SELECT COUNT(*) FROM sub WHERE thread_id IN (SELECT thread_id FROM threads WHERE project_link IS NOT NULL)) AS substantive_assigned;
```

`substantive_with_evidence_link / substantive_total` is the figure directly comparable
to the old **8.1% (27/332)** — this is what INTENT §2 gets corrected to next session.
`substantive_assigned` is the "has a project_link now" view. **Don't round up.**

### What should auto-resolve vs still needs a human (B.5)

Relink itself auto-resolves the strong cases on `--apply` (clear evidence + exact name
match → `auto_link` → `evidence`). What's left for the endpoint to surface is the
genuinely-ambiguous/contested set. See the composition:

```sql
SELECT type, status, COUNT(*) FROM review_queue GROUP BY type, status ORDER BY 3 DESC;
```

The endpoint (Task C) surfaces exactly the pending `project_link` / `link_ambiguous` /
`link_downgrade` rows — that's your ~155-item worklist.

---

## Task D — runbook (live smoke test, stretch; skip if budget tight)

```bash
# on the knight (after Task 0 shipped the registry and Task B ran)
python run.py review          # binds 0.0.0.0:8002
```

1. From a phone/desktop on the tailnet, open `http://<knight-100.x>:8002/`.
2. Pick **one** genuinely-pending `project_link` item, choose a registry project,
   submit. Expect a green "✓ <name>".
3. Confirm it landed via the read surface:
   ```bash
   python run.py serve      # Datasette, read-only
   # then query: SELECT thread_id, project_link, project_confidence
   #             FROM threads WHERE project_confidence='manual';
   ```
   The thread should show the id + `manual`. That's the first real proof of the write
   path outside the hermetic test.

---

## Files changed this round (uncommitted, in the working tree)

```
NEW  chronicler/__init__.py                 (makes chronicler.review importable)
NEW  chronicler/review/__init__.py
NEW  chronicler/review/core.py              (stdlib write core — validated + tested)
NEW  chronicler/review/app.py               (FastAPI + StaticFiles shell, optional deps)
NEW  chronicler/review/static/index.html    (functional vanilla-JS UI)
NEW  chronicler/review/README.md
NEW  tests/tester_review.py                 (hermetic gate for the two-column guarantee)
NEW  docs/COWORK_ROUND_2_REPORT.md          (this file)
MOD  run.py                                 (+ `review` command, help, dispatch)
MOD  verify.py                              (register tester_review)
MOD  pyproject.toml                         (+ [review] optional extra: fastapi, uvicorn)
MOD  docs/HANDOFF.md, docs/NEXT_SESSION_PLAN.md  (19 -> 20 testers, doc-claims auditor)
```
