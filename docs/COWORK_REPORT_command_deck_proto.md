<!-- gate-frozen: commit=26079ed -->

# Cowork report — Command Deck prototype: the queue, grouped by project

Pair: `docs/COWORK_BRIEF_command_deck_proto.md`. Session 2026-07-27, on top of
`26079ed` (0024 ratified and committed by Tim). **BUILD COMPLETE — nothing
from this round is committed yet** (see "Not yet done" below); all six tasks
landed and the gate is GREEN.

`python verify.py` — **GREEN**, 6 auditors + **46** testers at this build
(three testers added this session: `tester_relink_apply`,
`tester_backfill_candidate_project`, `tester_deck_migration`).
*(Frozen build-time count — the estate's convention for historical gate figures.)*

| Task | State | What landed |
|---|---|---|
| 1 — structured candidate columns | **green** | `candidate_project`/`rival_project` on `review_queue`; relink writes them; re-runnable backfill for pre-existing rows |
| 2 — grouped read surface | **green** | `core.queue_by_project`, `core.pending_rulings(project_id=…)`, two new endpoints |
| 3 — the rejection path | **green, per ratified 0024** | `review_rulings` table; `core.apply_rejection`; exclusion joined into both read functions |
| 4 — write path (accept) | **green** | `core.apply_ruling_batch`, `POST /api/rule/batch`, per-thread partial-failure results |
| 5 — deck UI | **green** | `static/index.html` rebuilt: left nav + right batch, check-off, Confirm, per-row "Not this project" |
| 6 — the wall, stubbed | **green** | deny-by-default `*-personal` account filter in both read functions, named to 0023 |
| follow-up — existing-vault migration | **green** | `db.ensure_deck_schema`, wired into the backfill + relink, `core.py` refuse-and-name-remedy, `tester_deck_migration` |

---

## Task 1 — structured candidate columns

`review_queue` gained `candidate_project TEXT` and `rival_project TEXT`
(both nullable), in `schema.sql` and `schema_frozen.sql`. `relink.apply_decision`
now writes them alongside the existing `note` prose for every row type that
carries a candidate:

- `project_link` (suggest) → `candidate_project` only.
- `link_ambiguous` → `candidate_project` (best) **and** `rival_project`
  (second) — the rival is never dropped, so the deck can put the thread in
  both projects' batches.
- `link_downgrade` → `candidate_project` only.

`chronicler/pipeline/backfill_candidate_project.py` backfills the ~500
pre-existing pending rows without a relink re-run. It exploits a fact about
the existing note format: `apply_decision`'s `lbl()` helper already writes
`"<registry id> (<breadcrumb>)"`, so the id is recoverable by regex, not
guesswork — the id is validated against the live registry before being
written, and anything that doesn't parse or doesn't resolve is reported as
**unresolved**, never guessed. Dry-run by default; `--apply` to write; only
rows with `candidate_project IS NULL` are touched, so re-runs are safe.

**Not yet run against the real dev vault** — the sandbox this session doesn't
have access to `chronicler_dev`. The dry-run/`--apply` split above needs
walking there; the UAT sheet will carry the actual resolved/unresolved split
from that run.

Hermetic coverage: `tests/tester_relink_apply.py` (relink writes the two
columns correctly for suggest/ambiguous/downgrade) and
`tests/tester_backfill_candidate_project.py` (note-parsing, registry
validation, dry-run doesn't write, idempotent re-run leaves already-backfilled
rows alone).

Side effect: two new testers moved the registered gate count from 43 to 45,
which broke `docs/UAT_solo_playbook_results.md`'s stamped `gate=6a/43t` claim
(auditor_uat_stamp checks against the *live* tree, not the stamped commit's
tree). Bumped that stamp to `45t` with a one-line note explaining why —
flagging here since it's an edit to a doc from a different, already-closed
round.

---

## Task 2 — the grouped read surface

`core.queue_by_project(conn, registry)` returns one entry per candidate
project with its breadcrumb and pending counts split by type
(suggestion/ambiguous/downgrade). A `link_ambiguous` row counts under **both**
`candidate_project` and `rival_project`, so a project with only rival threads
still shows a non-zero count in the left nav. Projects with zero pending rows
simply don't appear — nothing to collapse, matching the brief's "zero-count
entries collapse or hide."

`core.pending_rulings` gained `project_id` and `registry` parameters
(both optional, so the existing unfiltered call from `tester_review.py`'s
original assertions still works unchanged). Filtered to a project, a
`link_ambiguous` row whose rival — not candidate — is that project is
included and marked `is_rival: True`, rather than dropped; the manual-
confidence exclusion rule is unchanged and still never writes `review_queue`.

`app.py`: `GET /api/queue/projects` and a `project` query param on
`GET /api/pending`, both thin shells with no logic beyond the call into
`core.py`.

New assertions in `tests/tester_review.py` seed a genuine rival case (T2:
`link_ambiguous`, candidate `l5gn-os`, rival `crystal-spire`) and a
manual-confidence thread (T3) to prove it's excluded from the grouped view
too, then check: `queue_by_project` counts, `pending_rulings("l5gn-os")`
includes T2 as the candidate, `pending_rulings("crystal-spire")` includes T2
too but `is_rival: True`.

---

## Task 3 — the rejection path (ratified as 0024, built)

Per the brief: this is the one place the prototype would outgrow what 0007
authorised — `review_queue` is pipeline-owned, write-once by relink, and the
review endpoint has never touched it. "Not this project" doesn't fit that
shape, so it needs a ruling before code.

Discussed in chat: the append-only `review_rulings` table is the better shape
— it keeps `review_queue` untouched forever rather than reopening the single-
writer boundary `tester_review` currently asserts, and it matches the shape
0022 already wants for the run ledger. Below is the decision as ratified —
**Tim confirmed and committed it as `DECISIONS.md` 0024 at `26079ed`**, ahead
of the code that implements it.

> ## 0024 — Project-link rejections are an endpoint-owned, append-only `review_rulings` table
>
> **Date:** 2026-07-27 · **Status:** proposed · **Source:** COWORK_BRIEF_command_deck_proto.md Task 3 · **Builds on:** 0007; 0022's ledger shape
>
> **Context.** `review_queue` is pipeline-owned: relink is its only writer, and
> the review endpoint's audited invariant (0007, `tester_review`) is that a
> human ruling touches only `threads.project_link` / `threads.project_confidence`
> plus an idempotent `projects` identity row — never `review_queue`. An accept
> is expressible as a link (`project_confidence='manual'`), which is why that
> column boundary has held. A rejection has nowhere equivalent to go: it is a
> fact about a *proposal*, and proposals are `review_queue` rows, which the
> endpoint has never been allowed to write.
>
> **Decision.** Add a new table, written only by the review endpoint,
> append-only: `review_rulings (thread_id TEXT, candidate_project TEXT,
> verdict TEXT, ruled_at TEXT)`. "Not this project" inserts a row with
> `verdict='rejected'`; the grouped read surface (`pending_rulings`,
> `queue_by_project`) joins against it and excludes any `(thread_id,
> candidate_project)` pair with a rejected verdict from that project's batch —
> the same exclusion mechanism as the existing `project_confidence='manual'`
> rule, one join further out. `review_queue` itself is never written by the
> endpoint; the single-writer guarantee 0007 established is preserved exactly,
> not widened.
>
> **Consequences.** One more table and one more join on every grouped read.
> A rejection becomes inspectable after the fact (who rejected what, when),
> the same provenance instinct as 0022's ledger and the UAT stamp — and this
> table can very plausibly *become* (or feed) that ledger later rather than
> being a one-off. The alternative — `review_queue.status='rejected'`,
> written directly by the endpoint — is fewer moving parts but reopens a
> boundary that has held since 0007 for the sake of one UI round; if that
> trade is ever preferred it should be a deliberate re-litigation of this
> entry, not an incidental choice made while building the deck.

*(Minor: the committed entry still reads `Status: proposed` — worth a
one-line follow-up edit to `accepted` next time `DECISIONS.md` is touched;
not changed here since it's Tim's committed doc, not mine to silently alter.)*

**Built:** `review_rulings` table (`schema.sql`/`schema_frozen.sql`, indexed
on `(thread_id, candidate_project)`); `core.apply_rejection` (writes only
`review_rulings`, validates the thread exists, never touches `review_queue`);
the exclusion join added to both `pending_rulings` and `queue_by_project` so a
rejected `(thread_id, candidate_project)` pair drops out of that project's
batch/count specifically — a thread rejected against one candidate can still
appear (correctly) in a *different* candidate's batch if it's still live
there. `POST /api/reject` in `app.py`.

Hermetic coverage added to `tests/tester_review.py`: unknown-thread rejection
raises without writing; a valid rejection is proven to touch only
`review_rulings` (snapshot comparison against `review_queue`/`threads`); the
rejected pair is confirmed gone from `pending_rulings(project_id=…)` and from
`queue_by_project`'s count for that project.

---

## Task 4 — bulk accept, still narrow

`core.apply_ruling_batch` is the existing single-thread write path
(`apply_ruling`) split into a shared `_apply_ruling_write` helper that doesn't
commit, called once per `(thread_id, project_id)` pair inside one
transaction, with `apply_ruling`/`apply_ruling_batch` each owning their own
commit boundary. Every id is still validated against the registry before
anything is written for that pair — an invalid id in the middle of a batch
writes nothing for itself and doesn't touch the pairs around it, so a mixed
batch commits every valid pair and reports the invalid one, matching the
brief's "one validated write per thread, not a widened UPDATE" and the UAT's
"partial failure is visible" requirement exactly. `POST /api/rule/batch`
takes `{"rulings": [{"thread_id", "project_id"}, …]}` and returns one result
object per input pair (`{"ok": true, …}` or `{"ok": false, "error": …}`), in
the same order, so the UI can line results up against what it sent.

`MANUAL_CONFIDENCE` is unchanged — a batched ruling still locks the thread
against the next relink pass exactly like a single one.

---

## Task 5 — the deck UI

`chronicler/review/static/index.html` rebuilt as a two-pane layout: left nav
from `GET /api/queue/projects` (breadcrumb + total count, zero-count projects
simply don't appear — nothing to hide, the API never returns them), right
pane the selected project's batch from `GET /api/pending?project=…`.

**Design choice, stated per the brief's ask ("propose which reads better and
say why"):** rejection is a **per-row button** ("Not this project"), not
"reject whatever's left unticked" after Confirm. Reasoning: checkboxes here
mean "include in this Confirm," and overloading "unticked" to also mean
"reject" makes leaving a row unticked-but-unreviewed (e.g. still reading it)
indistinguishable from actively rejecting it — a slip either accepts things
too eagerly or silently reject-clears a row nobody looked at. A per-row
button makes "not this project" a deliberate, separate action, matching
"clears the row from that batch" without overloading the checkbox's meaning.
Suggestion/downgrade rows and ambiguous-candidate rows start **ticked**
(ready for a batch Confirm, matching Tim's framing — "I check them off");
rival rows start **unticked** (accepting a rival as *this* project is a less
obvious default than accepting the primary suggestion). Rival rows also get a
visibly distinct badge and left-border, per the brief.

After Confirm or a reject, the row is removed from the DOM immediately and
the left-nav counts are re-fetched, so a cleared batch reflects instantly
without a full page reload.

Smoke-tested end-to-end via FastAPI's `TestClient` against a throwaway seeded
DB (not part of the gate — a one-off check, transcript kept in this session):
`GET /api/queue/projects`, both filtered `GET /api/pending` calls (including
the rival case), `POST /api/rule/batch` with a mixed valid/invalid pair, and
`POST /api/reject`, all behaved as designed. **Not yet opened in an actual
browser against the real dev vault** — that's Tim's walk, `UAT_command_deck_proto.md`.

---

## Task 6 — the wall, stubbed

`core._PERSONAL_ACCOUNT_CLAUSE` (`t.account LIKE '%-personal'`) is joined
into both `pending_rulings` and `queue_by_project`'s `WHERE` clause. This is a
**deny-by-default allowlist**, not a blocklist of `-work` strings: only
threads whose `account` matches the known personal pattern pass, so a new or
unanticipated account label stays walled out by construction rather than by
someone remembering to add it to an exclusion list. There is no flag, no
config key, nothing to flip — the SQL simply cannot return a non-personal row.
Comment in the code names DECISIONS 0023 directly, and separately notes 0013
doesn't govern this path (the deck reads the live vault, same as `review`
already does, for the same "don't re-serve an already-ruled thread" reason).

Hermetic coverage: a `gemini-work` thread with a pending suggestion is seeded
in `tester_review.py` and confirmed absent from both the unfiltered and
project-filtered `pending_rulings` calls and from `queue_by_project`'s counts.
Also confirmed live in the `TestClient` smoke test.

---

## Follow-up — migrate an existing vault to the deck schema

Reported by Tim from a real `backfill_candidate_project.py` run against the
dev vault: `sqlite3.OperationalError: no such column: candidate_project`.

**Root cause, confirmed exactly as diagnosed in the task.** `schema.sql`
declares the new columns inside `CREATE TABLE IF NOT EXISTS review_queue`,
which is a no-op once that table already exists — so a vault built before
this brief never gained `candidate_project`/`rival_project`. `review_rulings`
*did* get created correctly (it's a genuinely new table, so the same
`IF NOT EXISTS` fires as intended there) — the columns were the whole gap.
Every tester in the suite builds its DB fresh from `schema.sql`, so this
class of defect was structurally invisible to the gate; `tests/tester_deck_migration.py`
(below) is built specifically to close that blind spot, and is worth reusing
verbatim as a template for any future schema change on an existing table.

**Built**, following `db.ensure_origin_column`'s shape exactly:

- `db.ensure_deck_schema(conn)` — `ALTER TABLE review_queue ADD COLUMN` for
  each of the two new columns if absent, `CREATE TABLE IF NOT EXISTS
  review_rulings` + its index, idempotent (a second call is a no-op), returns
  `False` on a DB with no `review_queue` at all (nothing to migrate — a fresh
  build handles itself). Docstring states the drift risk plainly: the DDL now
  lives in two places and only the new tester keeps them honest.
- Called from `backfill_candidate_project.run()` — **unconditionally, even on
  a dry-run.** This is a deliberate reading of "dry-run writes nothing":
  adding columns/a table is schema repair, not ruling data, and the dry-run
  report is structurally unreadable without it (the query that lists
  backfillable rows needs the column to exist to run at all). Also called
  from `relink.py`, gated the same way `ensure_origin_column` already is
  (`if apply:`), right next to it.
- `review/core.py` does **not** migrate — per the brief's reasoning: it's an
  HTTP endpoint, a web process silently altering the live vault on first
  request is the wrong shape, and `review/` deliberately doesn't import
  `pipeline.db`. Instead `core.connect()` now calls `_check_deck_schema` on
  every connect, raising `DeckSchemaNotMigratedError` naming the exact
  remedy (`run chronicler/pipeline/backfill_candidate_project.py first`) if
  the columns or `review_rulings` are missing. `run.py`'s `_cmd_review` does
  a preflight `core.connect(db).close()` before printing the bind banner, so
  an unmigrated vault fails fast and clean (exit 2) rather than reaching
  uvicorn and dying on the first request.

**`tests/tester_deck_migration.py`** (registered in `verify.py`, 46th
tester): builds a DB in the pre-deck shape **by hand**, not from current
`schema.sql` (sourcing it from the current schema would silently re-create
the exact mistake this tester exists to catch). Proves: migration adds both
columns + the table; a second call is a byte-for-byte no-op; an empty DB (no
`review_queue`) returns `False` and creates nothing; a migrated DB's
`review_queue`/`review_rulings` column sets match a fresh `schema.sql`
build's, column-by-column (the anti-drift check); `core.connect` refuses an
unmigrated DB naming the remedy and accepts a migrated one clean.

**Verified beyond the hermetic tester**, reproducing the reported bug and its
fix directly: built a synthetic pre-deck DB, ran
`backfill_candidate_project.py` as a real subprocess against it — it now
migrates and reports `pending rows missing candidate_project: 0` instead of
throwing (the exact failure mode Tim hit, at the exact line number, now
closed). Then drove `run.py`'s `_cmd_review` directly (with `app.run` stubbed
so it doesn't bind a real port): against the unmigrated copy it printed the
remedy and exited 2; against the same vault after the backfill's `--apply` it
passed the preflight and reached the bind banner clean.

`docs/UAT_command_deck_proto.md` updated: item 1.1's "not yet run" caveat
removed now that the blocker is fixed — dry-run against the real dev vault is
still Tim's to walk, but nothing should throw when he does.

---

## Not yet done / carried open

- **Nothing from this round (or the migration follow-up) is committed.**
  `git commit` in this sandbox keeps hitting a `.git/index.lock` held by
  something outside the sandbox — plausibly a Windows-side tool watching the
  repo. Recommend committing from your side once the lock clears, or clearing
  it and asking me to retry. The brief asked for "one commit" for the
  follow-up specifically — everything for it is together and ready to go as
  such once the lock is clear.
- **The backfill still hasn't been run against the REAL dev vault** — the
  migration bug that blocked it is fixed and verified (synthetic pre-deck DB,
  hermetic tester, and a real subprocess run reproducing the exact reported
  failure and its fix), but walking `backfill_candidate_project.py` (dry-run,
  then `--apply`) on `chronicler_dev` and recording the real resolved/
  unresolved split is still the first item on `UAT_command_deck_proto.md`.
- **The deck has not been opened in a real browser against the real vault.**
  Everything below the hermetic tests is smoke-tested against synthetic data
  only.
- `docs/UAT_command_deck_proto.md` (walk-sheet) is written; results/stamp are
  Tim's to produce after walking it.
- 0024's `Status:` field in `DECISIONS.md` still reads `proposed` — noted
  above, small follow-up edit, not made here.
