<!-- gate-frozen: commit=9212594 -->
# Cowork report — the Knowledge Curator tab

**Brief:** `docs/COWORK_BRIEF_curator_tab.md`
**Precondition:** DECISIONS **0033** (path allowlist replaces 0028's `docs/`-only
staging clause), ratified and committed at `e987d1a` before any code in this
round landed. Not re-litigated here — see `docs/DECISIONS.md`.
**Built:** 2026-08-08, in a Cowork sandbox with no LM Studio and no MCF corpus
reachable (as anticipated by the brief's own working assumption).

## What was built

Four new modules under `chronicler/review/`, wired into the existing app
exactly the way `estate=`/`index=`/`vault_unavailable=` already are, plus a
tab in `chronicler/review/static/index.html` (same bind, same process — no
new port, no new service):

- `chronicler/review/curator_data.py` — Task 1: read-only per-artefact state
  for K0–K5's outputs under `data/knowledge_curator/`. Staleness is
  per-artefact (never one collapsed timestamp). Blocked-reason text tells
  "map is header-only" apart from "map is ratified but this stage hasn't run"
  — a real distinction, discovered while building this: the live
  `config/mcf_conversation_map.tsv` in this checkout is **not** header-only
  (37 ratified rows at HEAD), contrary to the brief's own framing, which
  described the state at the time the Curator's build round finished. The
  data layer reads the true state on disk rather than assuming either story.
- `chronicler/review/curator_ratify.py` — Task 2: K0 candidate cards, evidence
  computation, per-row ratify/ratify-pair/hand-map actions, append-only
  staging with mandatory 0033 provenance.
- `chronicler/review/curator_control.py` — Task 3: LM Studio preflight, the
  execution allowlist, the single-run lock, per-stage model selection, real
  cache-invalidation counts.
- `chronicler/review/curator_findings.py` — Task 4 + 5: the five K5 sections
  rendered from K2/K4's own JSON, run-health-first, the transcript
  drill-through and its containment extension.
- `chronicler/review/app.py` / `run.py` — wiring: `curator=`/
  `curator_estate_gap=` threaded through `create_app()` and the `review`
  preflight, following the existing split exactly.
- `chronicler/review/static/index.html` — the tab itself: Header / K0
  ratification / Control strip / Findings / Map-coverage sub-views.

Commits on `main`:
- `772073c` — Tasks 1–5 backend (data layer, ratification, control, findings,
  coverage) + four testers, registered in `verify.py`.
- `479f3eb` — the tab UI, plus a one-line fix to
  `docs/UAT_knowledge_curator.md`'s stated tester count (61→65), which
  `auditor_doc_claims` caught as drift caused by this round's four new
  testers — the honest fix, not a suppression.

**Gate status: GREEN.** `python verify.py` → 6 auditors + 65 testers, no
failures, at both commits above.

## The three-row preflight table

`run.py review`'s preflight now resolves three independent halves, each
degrading on its own rather than all-or-nothing:

| Route family | Needs | Degrades to | Reason surfaced as |
|---|---|---|---|
| **Vault** (review queue) | vault DB + registry (`CHRONICLER_HOME` / `config/machines.json`) | 503 with `vault_unavailable` reason | `VaultUnavailable.as_dict()` |
| **Estate** (documents/search/timeline) | `data/estate.json` built on this machine | 503 with `estate.reason` | `EstateData.header()` |
| **Curator** (this round) | declared estate == `work` (0032); `data/knowledge_curator/` may still be entirely absent underneath | every curator route returns `{"available": false, "reason": "not_work_mcf_estate" \| "curator_absent", ...}` | `curator_estate_gap` (estate) or `Curator.header()` (data) |

The Curator row is the one genuinely new gate: unlike the vault/estate halves
(missing data, still the right machine), the Curator can be **the wrong
machine entirely** — `curator_estate_gap` is checked first, before any data
read, on every curator route (`_need_curator_estate()` in `app.py`), which is
also what keeps a populated Curator strip from ever appearing beside a
populated Chronicler strip on a non-work machine: the two gates
(`account_clause` for Chronicler, `curator_estate_gap` for Curator) are
independent and neither route family reads the other's data.

## The execution allowlist and the lock

`curator_control.STAGE_TABLE` is the **one place** a stage key is declared —
six entries, `K0`–`K5`, each carrying its script name, a fixed argv builder
(model stages read the model from `config/local.json`, never from the
request), and whether it is deterministic. `EXECUTION_ALLOWLIST =
frozenset(STAGE_TABLE)` is derived from it, not maintained separately.
`/api/curator/control/execute` accepts exactly one field — `stage` — and
`curator_control.run_stage`/`execute_with_lock` raise `ExecutionRefused` for
anything not in the allowlist before touching the lock or a subprocess.
Tester-proven in `tests/tester_curator_control.py`.

The lock is a real file (`data/knowledge_curator/.curator_run.lock` by
default, an injectable path in every tester), created with
`os.O_CREAT | os.O_EXCL` — an atomic exclusive create, not an in-memory flag
or a disabled button. A second `acquire_lock` call while one is held returns
`{"acquired": False, "stage": ..., "started_at": ...}`; the route surfaces
that as an HTTP 409 naming what is running and when it started. Released in
a `finally`, so a stage that fails or is blocked still frees the lock.

## The staging shape — a real staged diff

`curator_ratify.append_ratified_row` opens the map file in `"a"` mode only —
there is no code path in the module that can rewrite a byte already on disk.
`stage_ratified_map` runs `git add -- config/mcf_conversation_map.tsv` and
nothing else (0033's one map-specific allowlist entry, declared in code).

**This was exercised for real, against a throwaway `git init` repo — never
the live `config/mcf_conversation_map.tsv`**, which already carries unrelated
uncommitted WIP (a folder-name typo fix, `ChurnLevelIndictor` →
`ChurnLevelIndicator`) that this build was told not to touch. Running the
real staging code path against the live file would have staged that WIP
alongside the demonstration row. The demonstration below is the exact
`ratify.build_row` → `append_ratified_row` → `stage_ratified_map` →
`staged_diff` call chain the app.py route runs, against a seeded fixture repo
(one pre-existing row, `local_existing`), then discarded:

```
diff --git a/config/mcf_conversation_map.tsv b/config/mcf_conversation_map.tsv
index 406687f..2603729 100644
--- a/config/mcf_conversation_map.tsv
+++ b/config/mcf_conversation_map.tsv
@@ -1,2 +1,3 @@
 session_id	local_folder	project_id	conversation_name	notes
 local_existing	MCF/Foo	Foo	Foo - existing thread	[provenance:machine-matched:pass-1] pre-existing row
+local_1b8125e1-4529-4d38-a9ad-58d4422f5044	MCF/PricingModel	Pricing Model	PricingModel - Modal rate analysis plan	[provenance:machine-matched:pass-1] matched_length=142 candidates=1
```

`git status --porcelain` on the fixture repo after: `M  config/mcf_conversation_map.tsv`
— staged, one file, nothing committed. The pre-existing row is present
unchanged (a context line, not a `+`/`-`); the new row is the only addition;
its `notes` field carries the mandatory `[provenance:machine-matched:pass-1]`
tag permanently, per 0033. No dedicated `provenance` column was added to the
existing, already-shipped 5-column schema (`session_id`, `local_folder`,
`project_id`, `conversation_name`, `notes`) — widening the header is a schema
edit this module refuses to make; the tag inside `notes` keeps 0033's promise
without touching a byte of the header row or any existing data row.

Real repo state after this build: **unchanged**. `git status` on
`config/mcf_conversation_map.tsv` still shows only the pre-existing
uncommitted typo-fix WIP from before this session started; nothing from this
round was staged or committed against it.

## Containment against transcript paths

Obstacle 2 from the brief: the Cowork local transcript store is not an estate
root, so `curator_findings.transcript_store_roots()` declares it as a new
allowlisted anchor (reading the same `cowork_transcripts_home` config key K0/
K1 already read — no new config surface) and
`curator_findings.read_transcript_window` calls
`estate_data.resolve_contained()` — the **same** function `estate_data.py` and
`docs_board.py` already use, with a new anchor and new refusal vocabulary,
never a second implementation.

`tests/tester_curator_findings.py` exercises both cases the brief calls out
by name as likely uncovered by the existing suite (which only ever tested the
estate-root and repo-root anchors):

- **a traversal attempt through the identifier** — `read_transcript_window("../../../../etc/passwd", ...)`
  refuses `unknown_conversation` because the identifier never resolves against
  the in-memory conversation map (built from real discovery); there is no path
  parameter to attack in the first place.
- **a resolved path outside the declared root** — a fixture conversation whose
  (injected) file genuinely sits outside `roots` refuses
  `outside_transcript_store`, proving check two catches what check one would
  let through if the map itself were ever poisoned.

Also covered: an empty anchor set refuses rather than reading everything
(`no_transcript_store_configured`), a bounded window (never the whole
transcript — capped at `max_messages`), and three honest refusals: missing
file (`not_a_file`), oversized (`oversized`, capped at 2 MiB), and non-UTF-8
(`binary`) — never a stack trace.

## What `auditor_readonly` covers here, stated plainly

`auditor_readonly` walks `l5gntools.registry.SCANNERS` and ASTs each scanner
module for filesystem-mutating calls (`write_text`, `mkdir`, `unlink`, `open`
in a write mode, etc.). **`chronicler/review/` is not in that registry** —
nothing in this round trips it, positively or negatively. Gate-green on this
round means: (a) `auditor_readonly` ran and found zero violations in the set
it actually looks at, which excludes every file this round touched, and
(b) the two write paths this round adds (`curator_ratify.append_ratified_row`
+ `stage_ratified_map`, and `curator_control.acquire_lock`/`execute_with_lock`
's subprocess invocation) are covered **only** by the hand-written testers in
this round, not by any automated write-scanner. This is the same fact
`uat_sidebar.py`'s staging write already lived with before this round; it is
recorded here rather than left implicit.

## Task 4's superseded-ordering-flag — deliberately not built

The brief names a narrow allowed write (`flag_superseded_ordering`: "record
that the ordering got it wrong") and then, in the same breath, tells the
builder to skip it and note the deviation if in doubt. This build is in
doubt, for two reasons stated in the function's own docstring
(`curator_findings.flag_superseded_ordering`, which raises
`NotImplementedError` rather than silently doing nothing):

1. The brief's stop-condition list names exactly two write paths for the
   whole round — staging the map, invoking a stage. A third write here is one
   honest reading away from contradicting that list, even though the task
   text itself permits it.
2. "Triage state across runs" (marking a gap reviewed) is explicitly
   out-of-scope in the very next paragraph, and a structured "this ordering
   looks wrong" flag is functionally adjacent to that — a persistent,
   per-finding annotation that survives across runs. The line between the two
   is not obviously bright enough to build on a first pass.

Task 4 is otherwise fully read-only, as the brief's fallback instructs.

## K0 ratification outcome

**No real ratification happened in this sandbox**, and none was fabricated.
There is no real curated sheet in this checkout (confirmed against
`docs/COWORK_REPORT_knowledge_curator.md`: "K0 cannot run for real — there is
no real curated sheet") and `data/knowledge_curator/` does not exist on disk
here at all, so `candidate_map.tsv` was never produced and the K0 screen has
nothing real to show. The ratification *mechanism* — evidence-span
computation, six counts including zeroes, per-row actions honouring K0's own
collision rules, append-only staging with provenance — is built and
tester-proven against fixtures (`tests/tester_curator_ratify.py`), including
the real staged-diff demonstration above. Whether the unmapped-`local_*`-
folders question ("~16 expected, ~64 on disk, 48 curated") gets answered is
therefore also unanswered here: `unmapped_local_folders` is implemented and
tested against a synthetic store, but there is no real Cowork transcript
store reachable in this sandbox to run it against. Both are `[H]` items for
Tim to walk on the real rig — see `docs/UAT_curator_tab.md`.

## Deviations from the brief, summarised

1. **The superseded-ordering-flag** (Task 4) — not built; see above.
2. **Live progress streaming** ("stage 3 of 6, conversation 21 of 45") is
   designed as a data contract (`StageOutcome`, `classify_outcome`, and
   `extract_claims.py`/`match_claims.py`'s own existing terminal progress
   callbacks) but this round does not add a live-updating channel (SSE/
   websocket/poll) from a running subprocess into the browser mid-run — the
   UI shows the outcome once a stage completes, not a live counter while it
   runs. Given no LM Studio is reachable in this sandbox to exercise a real
   K2/K4 run, building an unverifiable live-progress channel would have been
   speculative; recorded here rather than silently narrowed.
3. **K0's map framing** — the brief describes the ratified map as
   header-only; the live file at HEAD already carries 37 rows. `curator_data`
   was built to read the true on-disk state either way (see "What was
   built" above) rather than assume the brief's framing.

## UAT

See `docs/UAT_curator_tab.md` for the stamped walk-sheet. `[G]` items were
verified programmatically in this session (via the testers above and direct
interactive checks against fixtures); `[H]` items are left unstamped for
Tim's walk on the work rig, per the brief's own instruction not to fake a
`[G]` on a human-only item.
