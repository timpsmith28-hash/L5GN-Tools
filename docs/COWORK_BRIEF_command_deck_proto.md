# Cowork brief — Command Deck prototype: the queue, grouped by project

**Origin:** design thread, 2026-07-27, after the solo playbook round.
**Deliverable:** a working deck on the rig dev vault that makes the pending
review queue *rulable* — grouped by candidate project, worked a batch at a time.

The golden apply left roughly **364 suggestions and 139 ambiguous threads** queued
for human judgement, and that queue is currently a wall: one flat list, ordered by
confidence, mixing every project together. Tim's framing, verbatim: *"if it just
filtered to one project — I check them off — that way batches them up into the same
thinking space."* That is the prototype's whole job. Everything else in the deck
(personas, knight commands, the run ledger) is explicitly **later**.

**Read first:** `chronicler/review/{core,app}.py` and `tests/tester_review.py` (the
base being extended, and the discipline it was built with),
`docs/SOLO_PLAYBOOK.md` (the dev loop this round runs in),
`docs/DECISIONS.md` **0007** (the DB access surface and its column-scope rule),
**0010** (the wall), **0012** (a ruling may be made at any tier), **0013**
(snapshot vs live), **0019** (LLM/query paths are structurally read-only),
**0021** (the supervisor), **0023** (work visibility is auth-gated).

---

## Rulings already taken (do not re-litigate)

| Question | Ruling |
|---|---|
| Prototype scope | **Read + rulings.** No personas, no knight command buttons, no run ledger. |
| Where it runs | **Rig dev vault**, per `SOLO_PLAYBOOK.md`. Knight deployment is a later, separate task. |
| Stack | **Extend `chronicler/review`.** Not a second service. |
| Candidate project | **Add a structured column; relink writes the registry id.** Not a note parse, not a read-time re-derivation. |
| Batch UX | **Check-off list with an explicit "not this project" action**, so working a project's batch *clears* it rather than leaving the same rows to resurface. |
| The wall | **Personal-estate data only.** The work path is hard-disabled with 0023's requirement stated in the code, not a runtime flag. |

---

## Working rules

- The stdlib-only core stays stdlib-only. FastAPI/uvicorn remain an **optional
  extra**; `available()` must keep reporting absence and `run.py review` must keep
  skipping loudly.
- **All DB logic in `core.py`, hermetically tested with plain sqlite3.** `app.py`
  stays a thin HTTP shell. That split is what lets the gate exercise the real write
  path with no web stack — do not move logic into route handlers.
- Dev-loop hygiene, from the solo round's near-misses: set **`CHRONICLER_HOME`**
  *and* **`CHRONICLER_REGISTRY_PATH`** explicitly before running anything directly
  (sharp edges 6–7). `resolve_registry_path()` derives a path by hopping two levels
  up from `CHRONICLER_HOME` and, unset, silently found Tim's **real** curated
  registry from a throwaway home. Never run `verify.py` or commit in a shell where
  those were set for a walk (sharp edge 9).
- Gate GREEN before every commit. Use `git commit -F <file>`, not `-m` with
  embedded newlines — PowerShell collapses them.

---

## Task 1 ▸ give the queue a structured candidate

`review_queue` carries `type / thread_id / candidate_thread_id / confidence /
status / note`. The candidate project exists **only inside `note`**, as prose
written by `relink.stage_decision` (`"suggest -> <display label>
(adjusted=0.83); evidence: …"`), via `lbl()` — a *display name*, not an id. There
is nothing to group by.

1. **Schema.** Add `candidate_project TEXT` (a registry id) and
   `rival_project TEXT` (nullable) to `review_queue`, in both `schema.sql` and
   `schema_frozen.sql`. `link_ambiguous` rows have two real candidates — best and
   second — and the grouping must not silently drop the rival, or a thread
   disappears from the batch of the project it might actually belong to.
2. **Relink writes them.** `stage_decision` already has `best["project"]` and
   `second["project"]` as ids in hand; write them to the columns as well as into
   the note. **Keep the note** — it is the human-readable evidence summary and the
   deck should show it.
3. **Backfill the existing rows.** ~500 pending rows predate the column. Prefer a
   small, re-runnable, `--apply`-gated backfill (the `finalize_db.py` pattern) that
   maps each row's noted label back to a registry id and reports anything it cannot
   resolve, rather than a full relink re-run — a re-run would rewrite the queue and
   is a much bigger blast radius on a vault that was just aligned. **Unresolvable
   rows must be reported, never guessed.**

**Acceptance:** every pending row in the dev vault carries a `candidate_project`
that resolves in the registry, or appears on the backfill's unresolved list with a
reason. Hermetic testers for the relink write and the backfill mapping.

**This runs against the dev vault only.** The live knight vault is untouched this
round.

---

## Task 2 ▸ the grouped read surface

In `core.py`, stdlib-only and tested:

- `queue_by_project(conn)` → per candidate project: the registry id, its
  `hierarchy` breadcrumb, and counts split by type (suggestion / ambiguous /
  downgrade). This is the deck's left-hand navigation.
- `pending_rulings(conn, project_id=None)` → the existing payload plus
  `candidate_project`, `rival_project`, and each one's breadcrumb; filtered to a
  single candidate when `project_id` is given. **A thread whose rival is the
  filtered project must appear in that project's batch too**, marked as a rival
  rather than a suggestion — that is the whole point of carrying the rival column.

Preserve the existing exclusion rule exactly: rows whose thread is already
`project_confidence='manual'` drop off the list, and the endpoint still never
writes `review_queue` to achieve that.

In `app.py`: `GET /api/queue/projects` and a `project` query parameter on
`/api/pending`. Thin shells over the core functions.

---

## Task 3 ▸ the rejection path — **stop here and draft a decision first**

This is the one place the prototype outgrows what 0007 authorised, and it must not
be resolved by whoever is typing.

Today the endpoint's audited invariant is: it mutates **only**
`threads.project_link` and `threads.project_confidence`, plus an idempotent
`projects` identity row. It deliberately never touches `review_queue` — that column
boundary *is* the single-writer guarantee, and `tester_review` asserts it.

"Not this project" has nowhere to go under that rule. An accept is expressible as a
link; a rejection is a fact about a *proposal*, and proposals are pipeline-owned.

**Draft a DECISIONS entry proposing the resolution, in the report, and stop for
Tim's ratification before writing the code.** The option this brief recommends —
argue against it if the code says otherwise:

> A new **endpoint-owned, append-only `review_rulings` table**: `(thread_id,
> candidate_project, verdict, ruled_at)`. The human's decisions become their own
> record, the deck filters resolved rows out by joining it, and `review_queue`
> stays entirely pipeline-owned. Disjoint ownership is preserved rather than
> traded away, and the shape matches the run ledger 0022 already calls for.

The alternative — letting the endpoint write `review_queue.status='rejected'` — is
simpler and breaks the boundary that has held since 0007. If it's chosen, it should
be chosen deliberately, in the log, not incidentally in a UI round.

**Nothing in Task 4 or 5 that depends on rejection may be built before this entry
is ratified.** The accept path is not blocked by it.

---

## Task 4 ▸ the write path, still narrow

- **Bulk accept.** `POST /api/rule/batch` over a list of `(thread_id,
  project_id)`. It must loop the existing per-thread `apply_ruling` — **one
  validated write per thread, not a widened UPDATE** — inside a single
  transaction, and return per-thread results so a partial failure is visible
  rather than swallowed. Every id still validated against the registry; a ruling
  is still allowed at any tier (0012).
- **Reject.** Per the ratified Task 3 entry. Rejecting must be enough to clear the
  row from that project's batch — if it isn't, the check-off loop doesn't actually
  clear anything and the feature fails its own purpose.

`MANUAL_CONFIDENCE` stays the top of relink's authority ladder: a ruled thread is
skipped by the nightly pass and can never be overwritten. The write is also the
lock; don't weaken that for batching.

---

## Task 5 ▸ the deck UI

Replace/extend `chronicler/review/static/index.html`. Single file, no build step,
no framework — consistent with everything else here.

- **Left:** programs → projects → repos, each showing its pending count. Zero-count
  entries collapse or hide; a wall of empty projects is the same problem again.
- **Right:** the selected project's batch — title, date, account, confidence,
  the evidence summary from `note`, and a snippet. Rival-derived rows are visibly
  distinct from suggestions.
- Check-off with select-all, then **Confirm** (accept ticked) and **Not this
  project** (reject unticked, or an explicit per-row action — the build thread
  should propose which reads better and say why).
- After a batch, the project's count updates and cleared rows leave the list.

**Design constraint worth stating:** this UI's only job is to let one person rule a
project's worth of threads in one sitting. If a feature doesn't serve that, it
belongs in a later round.

---

## Task 6 ▸ the wall, stubbed and stated

Personal-estate rows only. `threads.account` is already surfaced per row. The work
path is **absent or hard-disabled in code**, with a comment naming 0023 — work data
is behind the TOTP gate *even to view*, and that gate does not exist yet. Not a
config flag, not a default someone can flip: the prototype must be structurally
incapable of rendering work threads.

The deck reads the **live** vault for the queue (as `review` already does, and for
the same reason — a snapshot would re-serve threads already ruled). 0013 governs
`serve`, not this. Say so explicitly in the code where a future reader will ask.

---

## Explicitly out of scope

- Personas / inference (0018), knight command buttons and the run ledger (0022),
  the TOTP gate itself (0023), the 0021 supervisor.
- The two open follow-ups from DECISIONS 0017 (relink's flat-registry guard;
  the scorer refusing a non-target evidence key). Do not touch `relink.py`'s
  scoring — Task 1 touches only what `stage_decision` writes.
- A DECISIONS entry on ambient/derived config resolution (the root cause behind
  solo sharp edges 6–9). Real and wanted; not this round.
- Any deployment to the knight, and any write to the live vault.

---

## UAT — acceptance checks (Tim walks these)

- **The wall becomes a list of walls.** Open the deck on the dev vault; every
  project with pending threads shows its own count, and picking one shows only its
  batch.
- **The rival case.** A `link_ambiguous` thread appears in **both** candidates'
  batches, visibly marked, and ruling it in one removes it from the other.
- **Batch accept.** Ticking several threads and confirming writes them all as
  `manual`; re-running relink leaves them alone.
- **Rejection clears.** "Not this project" removes the row from that batch and it
  does not resurface on reload.
- **Partial failure is visible.** An invalid id inside a batch reports per-thread
  rather than silently succeeding or failing the lot.
- **Column scope held.** `tester_review`'s invariant still passes: no write outside
  the authorised columns and whatever Task 3's ratified entry added.
- **Work is unreachable**, not merely unshown.
- **Honest skip.** Without the optional web stack, `run.py review` still refuses
  cleanly with the install hint.

Mark each **ready to walk**, never "passed". The results log needs a uat stamp or
the gate refuses the commit.

---

## Reporting

`docs/COWORK_REPORT_command_deck_proto.md`, walk-sheet
`docs/UAT_command_deck_proto.md`, stamped results
`docs/UAT_command_deck_proto_results.md`. Record: the backfill's resolved/
unresolved split, the drafted Task 3 decision entry and its ratification, every
schema change, and anything carried open.

Any gate count quoted in a new doc gets a `gate-frozen` marker at the time of
writing.
