<!-- gate-frozen: commit=5016eb8 -->
# Cowork report — architecture census (DECISIONS 0030)

**Pair:** `docs/COWORK_BRIEF_architecture_census.md`. Session 2026-08-17.
**Precondition:** DECISIONS 0030 ("Shape is generated; rationale is authored.
ARCHITECTURE.md keeps the half that can't be derived") was already ratified
and accepted before this session began — the brief's precondition clause was
satisfied on entry, not negotiated during the build.
**Gate:** `python verify.py` → **GREEN, 10 auditors + 75 testers** (was
9 + 73 at `a0c3901`, this round's true base commit; +1 auditor:
`auditor_architecture_current` [Task 4], +2 testers:
`tester_architecture_census` [Task 2] and `tester_architecture_current` (the
new auditor's own pure-logic tester -- the commit-line mask below).
**Base commit:** `a0c3901` — this session's cloud clone had been taken from
`github.com/timpsmith28-hash/L5GN-Tools` at `afc246b`, eight commits behind
the actual local checkout (`LucasGoonPC`'s `correctness_sweep` round,
unpushed). Discovered when the local device's `git log` was checked before
syncing changes back; the whole round was rebased from `afc246b` onto
`a0c3901` before landing (clean rebase, no conflicts even on
`pyproject.toml`, which both this round's Task 6 and the correctness sweep
touch). Every fact and figure below is from the tree at `a0c3901` plus this
round's changes, not from the stale `afc246b` snapshot the build started
against.

This is testimony about what was built, not a status board — it will not be
updated as the tree moves on.

---

## What was built

| Task | State |
|---|---|
| 1 — the census scanner, six sections + provenance | **done** — `l5gntools/scanners/architecture_census.py`, registered in `registry.py` |
| 2 — determinism / no-absolute-paths / unparsed-not-zero, each with a tester | **done** — `tests/tester_architecture_census.py` |
| 3 — the renderer, `docs/_architecture_shape.md` | **done** — `l5gntools/report.py:render_architecture_shape` + `write_architecture_shape`, `python run.py render-architecture` |
| 4 — the gate refuses a stale render | **done** — `auditors/auditor_architecture_current.py`, registered, reports only, never writes |

Two defects were found and fixed along the way, neither of them A1–A12 and
neither of them a rewrite of `ARCHITECTURE.md`:

* **`doc_census.classify_provenance` ignored the filename's own leading
  `.`/`_`**, checking only directory segments (`relpath.split("/")[:-1]`).
  `docs/_architecture_shape.md` is exactly the shape that gap misses — its
  directory (`docs/`) is ordinary, only its filename carries the convention
  — and the brief names this as a hard UAT check ("`doc_census` counts
  `_architecture_shape.md` as generated, not authored"). Verified
  empirically before touching anything: `classify_provenance("docs/_architecture_shape.md")`
  returned `"authored"` on the unmodified tree. Fixed by widening the loop
  to the full path including the filename (`l5gntools/scanners/doc_census.py`);
  every existing fixture case in `tests/tester_doc_census.py` already had
  its underscore/dot on a directory segment, so the fix could only add
  `generated` classifications, never remove one — confirmed by running the
  existing suite unchanged before adding new cases. Two new fixture cases
  added (`docs/_architecture_shape.md`, `docs/.hidden_note.md`).
* **`PRAGMA table_info` column indexing bug in this round's own schema
  introspection** — `pk` is index 5, not 4 (4 is `dflt_value`). Caught by
  eyeballing the first render, where `status`, `is_custom_gem`,
  `review_status`, `suggested_close` and `tags` all read `PK` on
  `threads`. Fixed in `architecture_census._introspect_schema`; the render
  now shows exactly one PK per table, correctly.

---

## Section 1 — Scanners

**17** registered in `l5gntools/registry.py`, `architecture_census` now
counted among them (it describes itself; nothing about the contract
excludes a scanner from appearing in its own census, and excluding it would
have been a special case earned by nothing).

## Section 2 — Gate composition

`verify.py`: **10 auditors, 75 testers**, both lists read directly from
`verify.py`'s `AUDITORS`/`TESTERS` via `ast` (the file uses annotated
assignment, `NAME: list[str] = [...]` — the census's `_string_list_assign`
handles both `Assign` and `AnnAssign`, found by the count first coming back
zero against the real file and tracing why). This is the count-drift problem
the brief named dying at source: any future auditor or tester addition
changes this section on the next `render-architecture`, not on the next
person who happens to grep `verify.py` by hand and update a doc.

## Section 3 — Route table, `chronicler/review/app.py`

**42** routes declared directly with `@app.<verb>(...)` in that file (routes
a module contributes through `app.include_router(descriptor.router(ctx), ...)`
— the descriptor-registry half of the app, `modules.registered()` — are not
decorated in `app.py` itself and are correctly out of this table's scope;
the brief asked for routes *in* `chronicler/review/app.py`, not the whole
served surface).

Dependency, by literal name of the helper called in the route body:
**27 `estate`**, **6 `vault`**, **9 `none`**. `_need_curator_estate()` calls
are bucketed as `estate` (substring match on the literal identifier, not a
guess) — `curator_data`'s own docstring calls the curator gate
"estate-labelled by construction," so this is a grounded fold, not an
invented fourth category the brief didn't name.

## Section 4 — Write targets, per module (**reproduces A4**)

**31** modules under `l5gntools/` or `chronicler/` call a connection factory
or issue `.execute()`/`.executemany()`/`.executescript()`. "Opens a DB" is
defined at that level (issuing SQL against a handed-in connection counts,
not only opening one) specifically because `chronicler/review/core.py`
never opens its own connection — `app.py`'s `_connect` does that and hands
`core.py` the handle — and core.py is exactly where A4 lives.

**The review endpoint** (`chronicler/review/core.py`) writes
`{projects, review_rulings, threads}`. `review_queue` is **not** in that
set, with zero unresolved (dynamic-SQL) write lines to hedge the claim.
`ARCHITECTURE.md` §5 states the opposite — the census independently
reproduces finding **A4** exactly as the brief predicted it would, from AST
alone, with no foreknowledge encoded into the scanner.

For contrast, `review_queue` **is** written by three pipeline modules also
in this table — `render_md.py` (sync-back, matching the investigation's
`render_md.py:254` citation almost line-for-line: my numbers land at 103 and
314 because line numbers moved since the investigation's snapshot),
`relink.py`, and `backfill_candidate_project.py` — which is the pipeline
side of 0024's boundary, not a contradiction of it.

**5 modules** carry `unresolved_write_lines`: a real write whose target
table is not a literal string (an f-string, a module-level DDL constant, a
file read). Two are worth naming rather than burying in the table:
`chronicler/pipeline/db.py:220` (`conn.executescript(f.read())` — a
migration reading its own DDL from disk) and, self-referentially,
`l5gntools/scanners/architecture_census.py:350` — this scanner's own schema
introspection (`conn.executescript(path.read_text(...))` against an
in-memory DB) is itself flagged unresolved, for the same honest reason: the
scanner cannot statically rule out that `schema.sql`'s text might someday
contain an `INSERT`. Nobody asked for this case; it fell out of applying the
rule uniformly, which is closer to proof than any fixture could be.

## Section 5 — Schema shape (**reproduces A12**)

`schema.sql`: **8 tables**. `schema_frozen.sql`: **11 tables**. Delta —
only in frozen: **`meta`, `path_scan_log`, `render_log`**; only in schema:
none. `render_log` present in `schema_frozen.sql` and absent from
`schema.sql` is finding **A12**, reproduced without being looked for, via
`sqlite3` executing each `.sql` file against `:memory:` and reading it back
with `PRAGMA table_info` — deliberately not a hand-rolled SQL parser, on the
same "don't invent a second read path" instinct the brief applies to AST
over regex.

## Section 6 — Dependency wall

`l5gntools/`: **zero** third-party imports found, zero declared — the
stdlib-only claim holds, checked rather than assumed.
`chronicler/pipeline/`: imports match the `chronicler` extra exactly
(`yaml`, `sentence_transformers`), nothing undeclared, nothing unused.
`chronicler/` (top-level, `scrape_gemini_share.py`): matches `scrape`
(`playwright`) exactly.

**`chronicler/review/`: one undeclared import, one unused extra.**
`pydantic` is imported (every request/response model in `app.py` is a
`pydantic.BaseModel`) but not declared — `app.py`'s own docstring already
says why ("pydantic ships with fastapi"), so nothing is silently missing at
runtime, but it is a real, load-bearing dependency riding in unlisted on
the assumption that FastAPI's own pin stays compatible. `httpx2` is the
opposite shape: declared in the `review` extra (added by the
`correctness_sweep` round, `142c11f`, this round's true base) but never
`import`ed anywhere in `chronicler/review/` — it exists only so
`starlette.testclient` prefers it over `httpx` in the gate's own test
routes, a transitive need the census correctly cannot see from imports
alone (nothing in this repo names `httpx2` in a Python `import` statement;
`pip` resolves it as a dependency of `fastapi.testclient.TestClient`'s
preferred backend). Neither is fixed here — Task 6 emits facts, and both a
one-line `pyproject.toml` addition and a documented exception for
transitive-only extras are edits this brief did not ask for. Recorded so
neither has to be rediscovered.

---

## Determinism, no-absolute-paths, unparsed-not-zero (Task 2)

All three checked by `tests/tester_architecture_census.py`, in the gate:

* **Determinism.** `census(TOOLKIT_ROOT)` run twice, `json.dumps(..., sort_keys=True)`
  compared byte-for-byte — identical, both in the gate and by hand
  (`python3 -c "..."`, twice, diffed). No field is excluded from the
  comparison: the provenance block carries `toolkit_git_info()` only
  (`commit`, `dirty`) and deliberately no `generated_at` — every other
  estate-level scan in this toolkit stamps one; this one doesn't, so there
  is no wall-clock field to carve out of the equality check anywhere, ever.
  A second, independent proof against a small synthetic fixture tree (so
  the check does not depend on this repository's own state staying still
  mid-gate-run).
* **No absolute paths.** Every string in the payload checked; none starts
  with `/` (excepting the app's own `/api/...` route paths, which are URLs,
  not filesystem paths, and are the one legitimate case) and none matches a
  Windows drive letter. `str(TOOLKIT_ROOT)` does not appear anywhere in the
  payload.
* **Parse failure, never a silent zero.** A synthetic
  `chronicler/pipeline/broken.py` with a syntax error is planted in the
  fixture tree; `census()` reports it as
  `{"module": "chronicler/pipeline/broken.py", "status": "unparsed", "reason": "SyntaxError: ..."}`
  and — the part that actually matters — it does **not** also appear in
  `write_targets` reading as a module with no writes. A regex scan could
  not make this distinction; that is why the whole scanner is AST, with no
  regex anywhere near source-code parsing (regex is used exactly once, to
  read a DML verb + table name out of an *already-AST-extracted* literal
  SQL string — parsing SQL text, not Python source).

## The gate refusing a stale render (Task 4, walked by hand)

**A real chicken-and-egg found while walking this, not a hypothetical.** The
do-not-edit header names "the producing commit" — but the commit that
*adds or updates* the render necessarily gets a new SHA the moment it is
made, so the render a commit lands always names its own *parent*, never
itself. First commit of this round went RED on the very next `verify.py`
run for exactly that reason: `auditor_architecture_current` regenerated
fresh, saw the freshly-regenerated header now naming the just-made commit,
compared it against the committed header naming the commit *before* that,
and correctly called them different. Fixed by excluding the header's
commit line from the auditor's red/green diff — the identical shape as
`census()`'s own "no wall-clock inside the compared payload" rule, applied
to the one line that is provenance about *when this was committed*, not
about the tree's shape. Everything else in the file is still compared in
full, and `tests/tester_architecture_current.py` proves the mask hides
*only* a commit-line difference, never a real one.

One line of `docs/_architecture_shape.md` was hand-edited; `python verify.py`
went RED with `auditor_architecture_current` printing a unified diff and the
path to a freshly regenerated copy in `/tmp`; the file was restored;
`python run.py render-architecture` was NOT needed for the restore (a plain
revert sufficed) and the gate went GREEN again. Separately, deleting the
committed file entirely produces a distinct, named failure ("does not
exist — run `python run.py render-architecture` and commit it") rather than
a generic diff, so the two ways a stale-doc gate typically breaks (wrong
content vs. missing entirely) both report legibly.

---

## The estate-level "no root, no config" shape (Grounding, brief)

Every other scanner in `registry.SCANNERS` takes a target — a project
folder or a discovered list of them. `architecture_census` always describes
`TOOLKIT_ROOT`, so `scan_estate(projects)` accepts and ignores the
`projects` argument entirely; the real entry point is `census(root)`, which
takes an explicit root precisely so the Task 2 testers can point it at a
throwaway fixture instead of this repository. This is unusual enough to be
worth stating rather than discovering by reading the diff: it is the one
scanner in this registry with no meaningful input.

**The self-scan estate-level caching defect (self-scan finding #2)** was
not inherited, for a structural reason rather than a careful one:
`build_estate`'s cache (`report._cached`) is keyed only by filename, never
by the input project set, so a changed project set doesn't invalidate it.
`architecture_census` has no input project set to key against in the first
place — its one real input is the tree itself, and `auditor_architecture_current`
(Task 4) never reads the cached `data/architecture_census.json` at all; it
calls `census()` fresh every gate run and diffs the regeneration directly
against the committed markdown. The cache can go stale between builds and
it would not matter to the one thing enforcing freshness.

---

## What the census shows about the app-tier boundary (0034)

Not this brief's to fix — `docs/ARCHITECTURE.md` §3 stays silent about
0034 and the `l5gntools` ↔ app-tier split, and rewriting it is explicitly
out of scope here (the missing acknowledgement is `unified_app`'s own
outstanding item, per `docs/COWORK_REPORT_unified_app.md`). But this
round's own sections 4 and 6 make that boundary visible as data, which is
the whole point of generating shape instead of asserting it:

* Section 6 shows `l5gntools/` at **zero** third-party imports and
  `chronicler/review/` needing `fastapi`, `uvicorn` and (undeclared)
  `pydantic` — the stdlib-only core and the dependency-heavy app tier are
  not just a claim in DECISIONS 0034, they are a fact this section would
  contradict if it were false.
* Section 4 shows every DB-writing module living under `chronicler/`
  (pipeline or review); nothing under `l5gntools/` writes to the vault at
  all (`l5gntools/backup.py` and `l5gntools/dbsafe.py` both open
  connections — `backup.py` read-only via `connect_readonly`, `dbsafe.py`
  defines the factories others call — but neither issues a write). The
  single-writer boundary DECISIONS 0007/0014 describe is exactly what the
  tree does, not merely what it says.

The next time someone writes the app-tier paragraph ARCHITECTURE.md §3 is
missing, sections 4 and 6 of `docs/_architecture_shape.md` are the shape
half of that paragraph, already generated and already current.

---

## Acknowledgement

Per `docs/README.md` §4's convention (first use), an `actioned:` line was
added to `docs/investigation/2026-08-02_architecture-drift_claude_2-response.md`
naming A4 and A12 and the commit that closed them.
