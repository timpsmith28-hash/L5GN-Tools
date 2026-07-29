# Cowork report — the local deck, slice 1: the knowledge base and the time dimension

**Brief:** `docs/COWORK_BRIEF_local_deck_docs_and_time.md`. **Implements:**
DECISIONS 0027 (ratified before any code was written — see below). **Status:**
built and gate-GREEN; walk-sheet is `docs/UAT_local_deck_docs_and_time.md`.

**Base commit:** `ac7710d`. **Gate:** `python verify.py` → **GREEN, 6 auditors +
53 testers** (+2 this slice: `tester_estate_data`, `tester_review_preflight`).
**Nothing committed. No write path added. No deposit. Nothing persisted.**

---

## Precondition — 0027 was ratified first

The brief made ratification a hard gate on Tasks 2 and 3, and the record was
ambiguous: commit `a3c22c1`'s message said "0027 drafted and ratified" while the
entry in `docs/DECISIONS.md` still read **Status: proposed**. That is exactly the
kind of discrepancy that should stop work rather than be assumed away, so it was
raised before anything was built. Tim flipped the status to **accepted**; the
entry now reads as ratified and no code was written before it did.

Worth recording because the failure mode is subtle: a commit message is not the
decision record. The record is `DECISIONS.md`, and anything reading the tree for
authority (a person, an auditor, a later session) reads the status line, not the
git log.

---

## The preflight split — which routes now require what

**The obstacle the brief named.** `run.py review`'s preflight exited 2 when the
vault DB *or* the registry was missing. That was correct when every route wrote
to the vault. It became wrong the moment the same service started rendering
estate documents, which need neither: on a plain producer rig with an estate
build and no vault, the surface would refuse to start and you could not open your
own knowledge base.

**The fix, stated as a rule.** The preflight is split by *what each route needs*,
not by one all-or-nothing check.

| Route | Requires | Behaviour when the dependency is absent |
| --- | --- | --- |
| `GET /api/registry` | vault DB + registry | **503** with `reason` + a sentence |
| `GET /api/pending` | vault DB + registry | **503** |
| `GET /api/queue/projects` | vault DB + registry | **503** |
| `POST /api/rule`, `/api/rule/batch`, `/api/reject` | vault DB + registry | **503** |
| `GET /api/estate/header` | *nothing* | always answers; reports the absence itself |
| `GET /api/estate/projects` | `data/estate.json` | **503** with `reason` |
| `GET /api/estate/documents` | `data/estate.json` | **503** |
| `GET /api/estate/document` | `data/estate.json` | **503** |
| `GET /api/estate/search`, `/search/status` | `data/estate.json` | **503** |
| `GET /api/estate/timeline`, `/api/estate/changes` | `data/estate.json` | **503** |
| `GET /api/health` | *nothing* | reports both halves separately |

**503, not 404**: the route exists and is correct; the dependency it needs is not
present *on this machine*. A 404 would say the feature doesn't exist, which is a
different and false claim.

Two deliberate exceptions to the pattern. `/api/estate/header` is **not** gated
behind the estate check, because it is how the UI learns there is no build —
refusing to serve the explanation of a missing thing is how you get a blank page
and no idea why. `/api/health` reports `vault`, `estate` and `search` as three
independent objects, so a degraded surface is distinguishable from a broken one
at a glance.

**`run.py review` now refuses only when both halves are absent**, because then
there is genuinely nothing to render. It prints which half is degraded and why:

```
review: queue routes DEGRADED -- No vault DB at ... -- this machine has no
        thread store, so the review queue has nothing to show.
review: estate build=2026-07-29T00:31:21+01:00 commit=ac7710d (toolkit dirty)
review: estate routes ENABLED -- 9 projects, 193 authored documents,
        search engine=fts5
```

New in `chronicler/review/core.py`: `VaultUnavailable` (a reason tag + a human
sentence) and `vault_preflight()`, which never raises and never exits — it
returns the gap and lets the caller decide. That is what makes the same code
usable from `run.py` and from a tester.

One naming note, because it is a real trap: `run.py`'s local `estate` variable
used to hold the *config string* (`"personal"` / `"work"`) and now the loaded
snapshot object also wants that name. The config string was renamed
`declared_estate`. They are two different things and conflating them would
quietly break the 0025 loopback rule.

---

## Task 1 — the estate data layer

`chronicler/review/estate_data.py`. Read-only, stdlib + `l5gntools` only. Loads
`data/estate.json` once at startup and exposes it.

**Staleness is surfaced, not implied.** `header()` returns `generated_at`,
`toolkit_commit`, `toolkit_dirty`, plus `age_seconds` computed server-side. The
age is computed on the server on purpose: how old a build is should not depend on
the reader's clock or timezone. The UI renders anything over 24 hours as **STALE**
in red and flags `toolkit_dirty` in amber.

**Absence degrades, it does not raise.** A missing, unreadable or malformed
`estate.json` produces an `EstateData` with `available=False` and a `reason`;
every accessor still works and returns empty. `run.py review` keeps serving the
vault half.

---

## Task 2 — the knowledge base, readable

**Navigation.** Project → authored documents grouped by `doc_type`, with
`knowledge` first (0026 makes it the artefact of record). Projects with zero
authored documents are listed and greyed rather than hidden — "L5GN-Armory has
nothing written down" is a finding, not an absence.

**Rendering.** The document is read from disk **at request time** and returned as
raw text; the browser puts it in a `<pre>` via `textContent`.

*Why `<pre>` and not a markdown pass* — the brief asked for the simpler option
with a reason. A hand-rolled heading/paragraph pass is a second parser to
maintain and, more to the point, a path by which document text becomes markup.
`textContent` into a `<pre>` cannot produce markup at all. Here the simpler
option and the safer one are the same option, so there was nothing to trade off.

### Path safety — the whole security story

**The route does not accept a filesystem path.** It accepts `doc_id`: a
16-hex-character SHA-256 digest of `project + "\0" + relpath`, resolved against
the in-memory catalogue built from `estate.json`. A digest was chosen over a
list index because it is stable across builds — an index shifts the moment a
document is added, and a link that silently starts pointing at a different file
is its own defect.

**Two independent checks, both enforced on every read:**

1. **Identifier resolution.** The id must be in the catalogue. A traversal
   attempt arrives as an id that is not a digest and resolves to nothing.
2. **Containment.** The resolved absolute path must sit inside a **configured**
   estate root, compared after `os.path.realpath` on both sides, with `os.sep`
   appended so `/estate-evil` is not read as being inside `/estate`. Run
   immediately before the file is opened, *even for an id that passed check 1*.

Check 2 is not redundant. The case it catches is a document that is genuinely in
the catalogue with a genuine identifier, but whose project path lies outside the
roots — check 1 passes for it, and a single-check design reads the file. The
tester covers exactly that case (`Outside`/`SECRET.md`).

**The safety anchor is `config.estate_roots()`, not `estate.json`'s own `roots`
field.** A snapshot is data, and data that nominates its own safe directories is
not a boundary. A snapshot produced on another machine simply falls outside this
machine's roots and is refused.

**A third, earlier guard.** A relative path containing `..`, or an absolute path,
is dropped at catalogue-build time with a warning surfaced in the header. So a
poisoned `estate.json` cannot mint an identifier pointing anywhere interesting in
the first place.

**Generated documents never enter the catalogue.** They have no identifier, so
there is no request that could reach one. On the personal estate that excludes
the 734 generated documents; 193 authored documents are addressable.

**Refusal codes.** `404 unknown_document` (nothing is disclosed about what
exists), `403 outside_estate_roots`, `403 no_configured_roots`, `403 not_a_file`,
`403 unreadable`.

**One cap worth naming:** documents over 2 MiB are truncated with a visible
notice rather than streamed whole into a browser tab.

---

## Task 3 — search

`chronicler/review/doc_search.py`.

**FTS5 capability result: available and in use.** Checked at runtime by
attempting `CREATE VIRTUAL TABLE ... USING fts5` rather than by parsing
`compile_options` — the only answer that matters is whether the statement we are
about to run succeeds. Confirmed on sqlite 3.37.2.

**Degradation is real code, not a promise.** When FTS5 is absent the index falls
back to a case-insensitive substring scan, sets `engine="substring"` and returns
a `notice` the UI renders in amber: no relevance ranking, no phrase syntax,
results still complete. The fallback is exercised on every gate run via
`DocumentIndex(estate, force_substring=True)`, and the tester asserts both engines
return **the same corpus of hits** — so the degraded path is not first exercised
on the machine that needs it.

**Index location: in memory, per process, never on disk.** `sqlite3.connect(
":memory:")`. There is no index file under `data/` because there is no code that
could write one. Startup cost on the real estate is a single pass over 193 files.

**Ranking.** FTS5 `rank`, with `knowledge` documents sorted ahead of
equally-relevant others (0026). Results carry project, title, `doc_type`, an
opaque id (so a hit opens directly) and a snippet with the match in context.
Scopable to one project or the whole estate.

**Snippet safety.** The server marks matches with `\x02`/`\x03` control
characters, never HTML. The browser escapes the snippet **first** and only then
replaces the markers with `<mark>`. A document containing `<script>` cannot
smuggle markup out through a search result.

**A malformed FTS5 expression is a typo, not a fault.** An unbalanced quote
answers as a substring search for that one query and says so, rather than
returning a 500.

**Search is subject to the same containment check as render.** The index builds
its corpus through `resolve_document_path`, so a document the surface would
refuse to display is also one it will not search — and the skipped documents are
reported in `/api/estate/search/status` with their reasons rather than silently
dropped.

---

## Task 4 — the time dimension

`chronicler/review/estate_time.py`. All of it from data already on disk.

**Per project:** first and last commit, active span in days, commit count,
dirty-file count at build time, and contributors folded through
`config/authors.json` (`timpsmith28-hash` → `L5GN`).

**Estate timeline:** every project with history on one shared axis. `offset` and
`width` are computed **server-side as fractions of the estate's whole span**,
because the axis is the claim being made and a claim the tester can check should
not live in a `<script>` tag. On the current personal build the axis runs
2026-05-28 → 2026-07-28 (61.3 days) and the lineage is visible as the brief
predicted: Armory (off 0.257) → Armory_v2 (0.290) → Armory_v4 (0.323), with
Castle early at 0.013.

**What changed since the last build:** delegates to the existing
`l5gntools/scanners/estate_diff.py` rather than growing a second diff — two
diffs that disagreed would be worse than either alone. Enriched with
`from_build` / `to_build`, each naming the snapshot **file, timestamp and toolkit
commit**, because "what changed" is meaningless without saying changed between
what and what. Fewer than two snapshots returns `insufficient_history`.

**The honesty rule, enforced in three places.** A non-git project returns
`has_history: False` with a reason and carries **no** `first_commit`,
`last_commit` or `span_days` keys at all — the tester asserts their absence, so
the fields cannot be quietly filled in later. A git repo with unreadable commit
dates gets the same treatment. And an estate whose entire span is one instant
gets `width: 0.0`, not a full-width bar. The `build_activity` `Path("")` defect
is the cautionary tale throughout: a fabricated window is worse than an absent
one, because nobody audits a number that looks reasonable.

---

## A defect found by end-to-end testing, and fixed

The in-memory FTS5 index is built once on the main thread. **uvicorn runs sync
route handlers in a threadpool**, so every request queries it from a *different*
thread — and `sqlite3` refuses cross-thread use by default:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be
used in that same thread.
```

Every unit-level tester passed while this was broken, because a single-threaded
tester never crosses a thread boundary. It surfaced only when the app was driven
through a real `TestClient`.

**Fix:** the connection is opened `check_same_thread=False` and every query takes
a `threading.Lock`. The index is read-only after construction, so the lock is
uncontended and correctness costs nothing measurable.

**Regression test:** `tester_estate_data` now runs a query from a worker thread
and fails if it raises or returns a different count. Verified to genuinely catch
it — reverting the one-line fix turns the gate red with that exact message.

Worth recording as a pattern, not just a bug: *anything cached at startup and
read per-request in this service crosses a thread boundary.* The same trap is
waiting for the next slice that memoises something.

---

## Files

| File | Change |
| --- | --- |
| `chronicler/review/estate_data.py` | **new** — snapshot loader, document catalogue, path safety, render-time read |
| `chronicler/review/doc_search.py` | **new** — in-memory FTS5 index with substring fallback |
| `chronicler/review/estate_time.py` | **new** — spans, timeline, build delta |
| `chronicler/review/core.py` | `VaultUnavailable` + `vault_preflight()` |
| `chronicler/review/app.py` | 8 estate routes; vault routes gated by `_need_vault()`; `health` reports both halves |
| `chronicler/review/static/index.html` | build stamp, tab strip, Documents / Search / Time panes |
| `run.py` | split preflight; `estate` → `declared_estate`; index built at boot |
| `tests/tester_estate_data.py` | **new** — path safety, search, time, persistence |
| `tests/tester_review_preflight.py` | **new** — the four machine shapes |
| `verify.py` | registers both testers |
| `docs/COWORK_REPORT_toolkit_self_scan.md`, `docs/UAT_toolkit_self_scan.md` | tester count 51 → 53 (`auditor_doc_claims`) |

---

## Nothing persisted

0027's condition (1), enforced structurally rather than promised:

- No `write_json`, no `open(..., "w")`, no `mkdir` in any of the three new
  modules. There is no writer to disable.
- The FTS5 index is `:memory:`. There is no index file.
- Document text is read per request and discarded. There is no cache.
- `tester_estate_data` asserts the fixture tree gains no `.db` / `.sqlite` /
  `.idx` / `.cache` file after a full load, index, search and render cycle.
- `/api/estate/search/status` reports `persisted: false` as a first-class field.

Condition (2) — loopback for a non-personal estate — is inherited unchanged from
the existing 0025 enforcement in `run.py review`; this slice adds nothing to it
and takes nothing away.

---

## Left open

- **The queue half is untested against a real vault on this machine.** The
  preflight split is tester-proven for all four machine shapes, but the
  degraded-queue path in the browser is a UAT item, not a gate item.
- **`toolkit_dirty` is true on the current build**, so the deck will show the
  amber dirty flag until a clean build is taken. That is the flag working.
- **Search ranking is FTS5's default `bm25`**, untuned. Whether it puts the right
  document first on a real query is UAT check B2, and a poor answer there is a
  finding worth a follow-up, not a defect in this slice.
- **Out of scope as briefed:** threads and vault data, evidence drill-down,
  cross-project overlap, any LLM feature, any write path.
