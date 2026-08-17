# Cowork brief — curator correction: the estate gate, the per-estate map, and a recency resolver that isn't duplicated four times

**Origin:** Grand Walk, 2026-08-17 (DECISIONS 0044, 0046).
**Depends on:** DECISIONS **0032** (Curator: local-transcript, recency-as-truth-order — clause 1 superseded, clauses 2–3 stand), **0033** (staging confined to a code-declared allowlist; the map's entry is "append a row, never edit or remove"), **0039** (the Curator is scoped to the machine's declared estate, never a fixed name; excluded only when that estate is `both`), **0040** (a curated map, keyed on the source's stable id, is the join of record; per-source, gitignored, pinned by a committed `.sha256`), **0044** (settles 0039's open question: `data/knowledge_curator/` is outside the deposit contract, enforced twice; the estate gate and the map path are corrected to what 0039 actually ruled), **0046** (the map resolves by recency, last row per key wins, resolution lives in exactly one place, a superseding row says so explicitly, the raw view stays visible, undo is an append, and UI capture reuses the one write path).
**Deliverable:** four defects fixed as one round, because they rewrite the same layer — `chronicler/review/curator_data.py`, `curator_ratify.py`, `app.py`'s curator routes, `curator.js`, `knowledge_index.py`, `match_claims.py`, `candidates.py`, and `l5gntools/deposit.py` — plus the auditor that proves the new deposit exclusion holds.

0044 and 0046 are already ratified. This brief does not re-argue either; it turns each clause into a numbered task, names the design calls the decisions left to the build round, and states the ones I'm making now so you can veto before code exists rather than after.

---

## Why this is one round, not four

`curator_data.RATIFIED_MAP_PATH` is the single constant every consumer imports — `curator_ratify`, `curator_control`, `app.py`'s eleven-odd curator routes, `candidates.py` (via `app.py`), and (independently, which is itself part of the defect) `knowledge_index.py`. Making the path per-estate (Task 2) touches the same import in every one of those files. Making resolution happen in one place (Task 3) has to land in that same constant's neighbourhood, because the whole point is that every consumer stops rolling its own join. Fixing the gate (Task 1) is small on its own but is what makes Task 2 reachable on a personal-estate machine in the first place — there's no personal-estate map to resolve if the tab still refuses to serve one. Splitting these into separate rounds means opening the same eight files twice and re-deriving the same call graph twice.

---

## What's actually wrong, named precisely

Both defects are quoted directly from 0044's own text, because it already did the archaeology:

1. **The gate cites a clause 0039 had already amended three days before this code was written.** `app.py`'s `_need_curator_estate()` (and `run.py`'s preflight, where `curator_estate_gap` is actually computed) gates on `declared_estate_for_curator != "work"`, with reason string `not_work_mcf_estate`, and the surrounding comments cite `0032` — the MCF-only scoping 0039 already superseded on 2026-08-11. 0039 clause 2 is unambiguous: only a machine declaring `both` (the knight) is excluded. Everything else — including `personal` — should run the Curator. The tab's absence text (`curator.js`, keyed on the same reason string) repeats the wrong story to the user's face.

2. **The map path is hardcoded to one estate's filename.** `curator_data.RATIFIED_MAP_PATH = REPO_ROOT / "config" / "mcf_conversation_map.tsv"` is the fixed estate name 0039 clause 1 forbids ("never to a fixed estate name") and the per-source pattern 0040 clause 2 replaced ("maps are per source, one file each"). A personal-estate run — which the gate fix in Task 1 makes legal for the first time — has no map to write to or read from without this.

3. **A second ratification for the same key is silently a duplicate, not a correction.** `curator_data.ratified_map_rows` returns every row with no resolution. `append_ratified_row` actively *refuses* a second row for an already-seen `session_id` (`"already_ratified"`, writes nothing) — which is the opposite problem from duplication, but the same root cause: there is no way to say "this ratification was wrong, here is the correction" without either editing history (forbidden, 0033) or being silently blocked. Recency — 0032 clause 2, unchanged by everything since — is the rule that would resolve this, and nothing implements it.

4. **`data/knowledge_curator/` can leave the machine.** A Curator report quotes source spans verbatim (0032's `quoted_source` rule) — content, not summary — and 0027 keeps content out of anything that travels. `l5gntools/deposit.py`'s `build_bundle` currently only ever copies two named files (`estate.json`, the latest history snapshot) into the outbox, so today's deposit is accidentally safe — but "accidentally safe because nobody's touched that function since" is exactly the convention-based invariant DECISIONS keeps warning against (INTENT §5: *"the one convention-based invariant in the estate is the one that lost 133 links"*). 0044 wants the exclusion **stated** (so the next person who adds a directory-walk to `build_bundle` sees a wall, not silence) **and proven** (an auditor that would catch it if they didn't).

---

## Design calls this brief is making (flag now if any is wrong)

0044 and 0046 rule the *what*; they leave some *how* open. Rather than surface these as open questions, I'm making a call on each and naming it, so the brief is something you can veto a line of rather than a blank you have to fill in.

**Call 1 — the reason string gets renamed, not just its meaning.** `not_work_mcf_estate` describes the superseded rule. The corrected condition is "this machine's declared estate is `both`", so the reason string becomes `curator_excluded_both_estate`. It is declared once, as a constant in `curator_data.py` (not re-typed in `run.py`, `app.py`, and `curator.js` separately — that would just be a fourth place to duplicate a string). `curator.js` cannot `import` a Python constant, so its comparison string is a literal that carries a comment pointing at `curator_data.CURATOR_ESTATE_GAP_REASON` — an accepted, named duplication of one string across a language boundary, not a fourth *implementation*.

**Call 2 — the per-estate filename keeps `mcf_conversation_map.tsv` for the work estate, by name, rather than renaming it to `work_conversation_map.tsv`.** The file is gitignored (0040 clause 4) but its `.sha256` pin **is** committed, at `config/mcf_conversation_map.tsv.sha256`, and an operator's real, ratified, on-disk TSV already exists under that name. Renaming it is a migration with no upside — 0040 clause 2 requires "one file each" per source, not one *name scheme* each. So: a declared-in-code mapping, `MAP_FILENAMES = {"work": "mcf_conversation_map.tsv", "personal": "personal_conversation_map.tsv"}`, in `curator_data.py`, and `ratified_map_path_for_estate(estate)` resolves against it. An estate absent from the dict (i.e., not `work` or `personal` — `both` never reaches this code because Task 1's gate already excludes it) is a stated `KeyError`-equivalent refusal, never a guessed filename.

**Call 3 — a superseding row is marked in `notes`, not a new TSV column.** `curator_ratify.py` already made this call once, for provenance, and said why in its own docstring: *"there is no dedicated provenance column in the existing, already-shipped schema — widening it would be a header edit this module refuses to make."* The same argument applies to status. A `[status:corrected]` / `[status:revoked]` tag, alongside the existing `[provenance:...]` tag, in the same `notes` field, needs no header migration and no handling for a mismatched old-format file that a header-widening would require. Absence of a status tag means "active, first ratification" — every row in every map on disk today reads correctly under this rule with zero migration.

**Call 4 — `append_ratified_row` keeps its exact current contract; correction is a sibling function, not a new mode on the old one.** The stop condition says *"if `append_ratified_row` stops being a pure byte-append, stop."* It already is one, and its refuse-on-duplicate-session_id behaviour is tested today (`tests.tester_curator_ratify`) and must keep meaning exactly what it means now: a fresh ratification of a session_id already in the map is a no-op. Correction is a **new**, second entry point — `append_correction_row` — whose precondition is the opposite (`session_id` **must** already be present) and whose row **must** carry a status tag and a `notes` sentence stating what it supersedes and why (0046 clause 5's own wording). Both funnel through one shared private byte-append primitive, so there remains exactly one piece of code that touches the file's bytes — two named callers expressing two different intents, not two ways of writing.

**Call 5 — resolution excludes a `revoked` row from the resolved view entirely; `corrected` replaces the prior row's `project_id` in place.** Neither 0046 nor 0032 spells this distinction out, but the two provenance tags in Call 3 are meaningless if they resolve identically. `corrected` is "the project_id was wrong, here is the right one" — the resolved view shows the corrected mapping. `revoked` is "this conversation should not be mapped at all" — the resolved view drops the key. Both remain, in full, in the raw view (0046 clause 4).

---

## Task 1 ▸ correct the estate gate to 0039 clause 2

- `run.py`'s preflight (where `curator_estate_gap` is computed, ~line 522): the condition changes from `declared_estate_for_curator != "work"` to `declared_estate_for_curator == "both"`. The message changes from *"...is scoped to the work/MCF estate only (DECISIONS 0032)..."* to state the actual rule: the Curator runs on any machine whose declared estate is not `both`, citing 0039 clause 2 / 0044 clause 3, not 0032.
- `curator_data.py`: add `CURATOR_ESTATE_GAP_REASON = "curator_excluded_both_estate"` (Call 1). `run.py` and `app.py` both import and use this constant — no hand-typed reason string anywhere else in Python.
- `app.py`: every occurrence of the literal `"not_work_mcf_estate"` (four call sites: `_need_curator_estate`, `curator_header`, and the two inline dicts near lines 518/528/853) becomes the imported constant. The comments at ~172, ~507–514 citing "(0032: MCF-scoped, work estate only)" are corrected to cite 0039/0044 and describe the actual condition.
- `curator.js` (line 34): the comparison literal updates to match the new reason string (Call 1), and the absence text drops "Absent on this machine" phrasing that implied a wrong-estate-forever state in favour of language matching the corrected message from `run.py`.
- A new tester (`tests.tester_curator_estate_gap` or folded into an existing curator tester if one already covers `run.py`'s preflight) proves: `estate="both"` → gap set, reason is the new constant; `estate="personal"` → no gap; `estate="work"` → no gap; `estate=None`/unknown → **flag for your call in review**: 0039 clause 1 says "never to a fixed estate name" but says nothing about an *absent* one. This brief's default is that an unset/unrecognised estate also gates (fail loud, per INTENT §5, rather than guessing), same posture as the existing `declared_estate` refusal in `run.py`'s loopback check a few lines below. Flag if you want `None` treated differently from `"both"`.

## Task 2 ▸ per-estate map path

- `curator_data.py`: add `MAP_FILENAMES` (Call 2) and `def ratified_map_path_for_estate(estate: str) -> Path`. `RATIFIED_MAP_PATH` as a bare module constant is removed — every caller either receives a `Curator` instance (which now resolves its own path from the declared estate at construction) or calls `ratified_map_path_for_estate` directly. Grepping the tree for the old name is the check that nothing was missed.
- `Curator.__init__` gains the estate resolution: `ratified_map_path` defaults to `ratified_map_path_for_estate(config.machine().get("estate"))` rather than the old bare constant, still overridable by an explicit argument (tests already construct `Curator(data_dir=..., ratified_map_path=...)` directly and keep working unchanged).
- `run.py`: `curator_data.Curator()` construction passes nothing new — it already reads `config.machine()` itself now — but the comment explaining the curator preflight is updated to say the map path is per-estate, not a fixed name.
- `curator_control.STAGE_TABLE`: K1 (`knowledge_index.py`) and K4 (`match_claims.py`) argv lambdas currently omit `--map` and rely on each script's own hardcoded default (`config/mcf_conversation_map.tsv`), which is now wrong on a personal-estate machine. Both argv lambdas add `"--map", str(curator.ratified_map_path)` (the `cfg` closure already has access to the running `Curator`; confirm the exact plumbing when writing the code — `curator_control.py`'s stage functions take `cfg`, not `curator`, directly today, so this may need `curator` threaded through the same way `CURATOR_DATA_DIR` already is via the module import, or passed at STAGE_TABLE-build time — this is an implementation detail, not a design call, but don't let it default silently back to the hardcoded work-estate path).
- `bootstrap_conversation_map.py` (K0) is **not** touched — it doesn't import `RATIFIED_MAP_PATH` and doesn't take `--map` (confirmed: no `DEFAULT_MAP` constant in that file). If K0 is later found to read the ratified map for its own matching, that's a separate finding, not silently absorbed here.
- Each estate's map gets its own committed `.sha256` fingerprint (0040 clause 4) beside the file, same convention as today's `config/mcf_conversation_map.tsv.sha256`. This round does **not** build 0045's general pin-checker (verification tool) — that's future work 0045 itself scopes separately and explicitly leaves "no checker" as the honest current state for this pattern. This round only makes sure a personal-estate map, once ratified, gets a fingerprint committed the same manual way the work-estate one already does — documented in the report, not automated.

## Task 3 ▸ one recency resolver, every consumer calls it

- `curator_data.py` gains the resolver (Call 3, Call 5):
  - `_row_status(row: dict) -> str | None` — parses a `[status:...]` tag out of `notes`, mirroring `curator_ratify`'s existing `[provenance:...]` parsing exactly (reuse its tag-slicing logic rather than inventing a second parser).
  - `resolve_map_rows(rows: list[dict]) -> dict[str, dict]` — walks `rows` in file order (file order **is** recency, per 0046's own framing — no timestamp column needed), last non-revoked row per `session_id` wins, a `revoked` row removes the key from the result.
  - `resolved_map_rows(path: Path | None = None) -> list[dict]` — `list(resolve_map_rows(ratified_map_rows(path)).values())`, the one call every consumer below switches to.
- **`knowledge_index.py`'s `load_map` stops reimplementing TSV loading.** Today it opens the file itself with its own `csv.DictReader` loop, independent of `curator_data` entirely — this is the second implementation 0046 clause 2 names directly. It becomes a thin adapter: call `curator_data.resolved_map_rows(path)`, convert each resolved dict into a `MapRow` exactly as today. `match_claims.py` imports `knowledge_index.load_map` as `k1.load_map` already, so fixing this one call site fixes both consumers named in the task list without a second edit — confirm this at code time; if `match_claims.py` turns out to also read the TSV independently anywhere else, fix that site too rather than assuming the one fix covers it.
- **`candidates.py`** doesn't read the file itself — it receives `map_rows` as a parameter, built by whichever `app.py` route calls it. `app.py`'s `curator_conductor_candidates` route (the only caller, ~line 729) currently passes `ratified_map_rows(c.ratified_map_path)` — raw, unresolved. It changes to `resolved_map_rows(c.ratified_map_path)`. `candidates.py`'s own `{row["session_id"]: row["project_id"] for row in map_rows}` dict comprehension is left as-is (it now receives already-deduplicated input, so the comprehension's implicit "last value wins" behaviour is inert, not load-bearing — noted here so nobody "fixes" it into a second resolver later).
- **`curator_data.py`'s own internal consumers** — `k0_state`, `k1_state`, `k2_state`'s `ratified_row_count()` calls — currently count raw rows (every append, including superseded and revoked ones). Decide, and state in the report: the tab's header `ratified_row_count` becomes the **resolved** count (meaningful, currently-active mappings — what an operator means by "how many have I ratified"), with the raw total surfaced separately in Task 4's raw view. `k1_state`/`k2_state`'s "header-only, ratify at least one row" blocked-reasoning switches from `ratified_row_count(path) == 0` to `len(resolved_map_rows(path)) == 0` for the same reason — a map with one ratified-then-fully-revoked row is not meaningfully different from an empty map for the purpose of "is there anything for K1 to join against."
- **The Curator tab's own JS** doesn't currently do any resolution (it renders `candidate_map.tsv` cards, Task 2 of the original curator-tab brief — the *ratified* map's rows aren't rendered as a list anywhere in the existing UI, only counted). Task 4 below adds the first UI surface that renders ratified-map rows directly, and it uses the resolver from the start.
- New tester (`tests.tester_curator_resolve` or folded into `tester_curator_data`): three ratified rows for the same key — plain, then `corrected`, then a fourth row for a *different* key that's `revoked` — proves last-wins, proves a revoked key vanishes from `resolved_map_rows`, proves `ratified_map_rows` (raw) still returns all four untouched.

## Task 4 ▸ raw view + explicit status, surfaced

- New route, `GET /api/curator/k0/map/raw`, gated behind `_need_curator_estate()` like every other curator route: returns every row from `ratified_map_rows()` in file order, each annotated with its parsed status (`None`/`corrected`/`revoked`) and a computed `is_current` boolean (true iff this exact row object is the one `resolve_map_rows` would return for its key) — so a superseding row and the row it superseded are both visible, and which one currently wins is legible without the reader re-deriving recency by eye.
- `curator.js` gains a rendering for this — a new sub-view alongside K0's existing candidate-card view (the existing `showCuratorSub("k0")` pattern; this becomes a second sub-tab, not a replacement). Superseded rows render visually distinct from current ones (dimmed, or struck through — implementation detail for the build round) but are never hidden or filtered out by default. This is the reviewing surface 0040 clause 4's second paragraph names: *"the curator tab's staged-rows view becomes the primary review rather than a convenience."*
- The header's `ratified_row_count` (Task 3's call) is shown next to a second, explicit "including superseded: N" figure, so the resolved/raw distinction is visible at the point it's collapsed, not just correct underneath.

## Task 5 ▸ undo as append

- `curator_ratify.py` gains `append_correction_row(row: dict, path: Path | None = None) -> dict` (Call 4). Validation (`_validate_new_row`'s sibling, e.g. `_validate_correction_row`) requires: `session_id` already present among *raw* rows in the target file (refuse `unknown_session_id` if not — you can't correct a ratification that was never made); `notes` carries **both** a `[provenance:...]` tag (unchanged rule) **and** a `[status:corrected]` or `[status:revoked]` tag; for `corrected`, `project_id` must differ from the row currently resolved for that key (refuse `no_op_correction` if identical — a "correction" that doesn't change anything is a bug in the caller, not a legitimate row); the free-text portion of `notes` must be non-empty and state what it supersedes (0046 clause 5) — a bare `[status:corrected]` tag with nothing after it is refused the same way a bare `[provenance:...]` tag is refused today.
- Both `append_ratified_row` and `append_correction_row` call a shared private `_append_row(row, path)` that is the actual `open(..., "a")` — the one and only byte-append code path (Call 4).
- `app.py` gains `POST /api/curator/k0/correct`, taking a payload shaped like the existing `CuratorRatifyRow` plus a `status` field (`corrected`/`revoked`) and a required `reason` string that becomes the `notes` free text. Same staging behaviour as `/ratify`: on success, `stage_ratified_map(REPO_ROOT)`, never a commit.
- New tester: append a row, correct it (`corrected`, different `project_id`), attempt a no-op correction (refused), revoke a different row, confirm `resolved_map_rows` reflects both outcomes and `ratified_map_rows` still shows all rows.

## Task 6 ▸ UI capture for a folder K0 never proposed

- `unmapped_local_folders` already exists in `curator_ratify.py` and is already surfaced by `curator_k0_candidates` (app.py ~line 555) as a finding, not an action. This task adds the action: `app.py`'s existing `POST /api/curator/k0/ratify` route already accepts a `CuratorRatifyRow` payload and calls `build_row` → `append_ratified_row` → `stage_ratified_map` — **the exact path this task is required to reuse.** No new write route is needed for this task specifically; what's missing is only the frontend affordance — `curator.js`'s rendering of `unmapped_local_folders` (around the "retention finding" section, `curator_ratify.py`'s own docstring language, ~line 94 of `curator.js`) gains an inline form (session_id pre-filled from the folder entry's `conversation_id`, `local_folder` pre-filled, `project_id` and `conversation_name` operator-entered) that POSTs to the same `/api/curator/k0/ratify` endpoint every other ratify action already uses, with `provenance` fixed to `hand-mapped:no-candidate` (the existing tag `curator_ratify.PROV_HAND_MAPPED` — no new provenance vocabulary).
- If the build finds `CuratorRatifyRow`'s existing schema doesn't carry a `provenance` field the frontend can set explicitly (worth checking before assuming), that's a small, named addition to the payload shape — not a new writer.

## Task 7 ▸ the deposit exclusion, stated and proven

- `l5gntools/deposit.py`: add a module-level constant, `EXCLUDED_FROM_DEPOSIT = ("knowledge_curator",)`, and an assertion inside `build_bundle` — after `files` is assembled and before the manifest is written — that no entry in `files` (nor, defensively, any path under `outbox`) contains `"knowledge_curator"` as a path segment. Today's `files` list is a fixed two-item whitelist (`estate.json`, one history snapshot) built by explicit `shutil.copy2` calls, so this assertion cannot fail today — that's the point. It's the wall the next person who adds `shutil.copytree(data_dir, outbox)` runs into, per 0044's own framing (*"one states the rule"*).
- New auditor, `auditors/auditor_deposit_exclusion.py`, registered in `verify.py`'s `AUDITORS` list. Builds a bundle against a temporary `data_dir` seeded with a fake `data/knowledge_curator/leaked.md` file (and the two files `build_bundle` actually requires — `estate.json`, and optionally a history snapshot), and fails if anything under the resulting `outbox/` contains `knowledge_curator` anywhere in its path — proving the exclusion holds even under a hypothetical future `build_bundle` that *does* walk the whole data dir, not just checking today's code reads correctly. This is dynamic (it actually builds a bundle), which is a different shape from the AST-walking `auditor_readonly`/`auditor_stdlib` — flagged because if you'd rather this live in `tests.TESTERS` next to the existing `tests.tester_deposit`, that's an equally valid reading of "auditor" in 0044's text and a one-line move in `verify.py`; my default is `AUDITORS`, because 0044 clause 2 names it "an auditor" specifically, echoing `auditor_readonly`/`auditor_stdlib`'s "proves a property the code could otherwise quietly lose" framing.

---

## Explicitly out of scope

- **0045's general pin-checker.** This round extends the existing per-map `.sha256` convention to a second estate (Task 2) but does not build the verifier that reads and checks a pin — that's 0045's own scope, a separate decision with its own build round.
- **`bootstrap_conversation_map.py` (K0)'s own matching logic.** Untouched. It produces `candidate_map.tsv`; nothing in this brief changes how candidates are matched, only how the *ratified* map downstream of K0 is pathed and resolved.
- **The vault schema.** Not touched, per the working rules below and because nothing in 0044/0046 concerns `chronicler.db`.
- **`l5gntools/scanners/`.** Zero edits, per the working rules — Task 7 touches `l5gntools/deposit.py`, which is explicitly not a scanner (its own docstring: *"deliberately outside the read-only scanner contract... never registered"*).
- **A UI for browsing/searching the raw map beyond Task 4's list.** Filtering, search, pagination — the raw view is a flat list in file order; if that's unusable at real row counts, that's a finding for the next round, not a scope creep into this one.
- **Migrating existing on-disk `mcf_conversation_map.tsv` files.** Call 3's notes-tag approach needs no migration; nothing in this brief rewrites a byte of any existing map.

---

## Working rules

- Gate GREEN before every commit — the pre-commit hook enforces it; don't work around a red gate.
- `git commit -F <file>`, never `-m` with an embedded newline.
- Zero edits under `l5gntools/scanners/`.
- Do not touch the vault schema.
- Logic lives in testable functions, never in route handlers — `app.py`'s job stays "call the function, shape the response," per the pattern already established by every existing curator route.
- Every new behaviour gets a tester registered in `verify.py`. No auditor or tester is deleted or disabled to make the gate green.

## Stop conditions

- **If `append_ratified_row` stops being a pure byte-append**, stop. Correction is `append_correction_row`, a sibling, not a new mode grafted onto the existing function.
- **If two consumers end up resolving the map differently**, stop. `resolve_map_rows`/`resolved_map_rows` in `curator_data.py` is the one place; a second inline resolution anywhere (a second `{row["session_id"]: ...}` loop that isn't provably inert, per Task 3's `candidates.py` note) is the defect this round exists to remove, not to add a third instance of.
- **If the deposit exclusion ends up enforced only in `build_bundle` with no auditor (or only in the auditor with no declared constant in `build_bundle`)**, stop. 0044 clause 2 requires both, named as separate, deliberate expenses.
- **If the estate-gate fix ends up gating on anything other than `declared_estate == "both"`** (e.g. reintroducing an allowlist of estate names), stop and re-read 0039 clause 1 — "never to a fixed estate name" is the thing that broke last time.

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[G]` On a machine configured `"estate": "personal"`, the Curator tab renders (not an absence message) and `/api/curator/header` returns `available` reflecting real on-disk state, not a gap.
- `[G]` On a machine configured `"estate": "both"`, the Curator tab shows a stated absence whose text names the `both`-estate exclusion (0039 clause 2), not a stale reference to work/MCF scoping.
- `[G]` On a machine configured `"estate": "work"`, behaviour is unchanged from before this round — the existing `config/mcf_conversation_map.tsv` is still the map read and written.
- `[G]` A fresh personal-estate machine with no `config/personal_conversation_map.tsv` on disk shows K0–K5 as correctly blocked (same "header-only" reasoning as the work estate shows today), not an error.
- `[H]` **Ratify a row twice on purpose** — once as a normal ratification, once more attempting to re-ratify the same `session_id` with no status tag. The second attempt is refused as a no-op, exactly as it is today. This must not have changed.
- `[H]` **Correct a ratification.** Ratify a row, then submit a correction with a different `project_id`. The resolved view (wherever K1 reads from) reflects only the corrected `project_id`. The raw view (Task 4) shows both rows, the corrected one marked, and it's legible from the UI alone which one is current without reading the TSV by hand.
- `[G]` **Revoke a ratification.** The revoked key disappears entirely from `resolved_map_rows`/K1's join; the raw view still shows the original row and the revocation, neither deleted.
- `[G]` Attempting a correction with an identical `project_id` to what's already resolved is refused (`no_op_correction`), not silently appended.
- `[G]` Attempting a correction for a `session_id` never ratified is refused (`unknown_session_id`).
- `[H]` **Capture a folder from `unmapped_local_folders` through the UI.** Pick a folder K0 never proposed a candidate for, type a `project_id`, submit, and confirm the appended row carries `[provenance:hand-mapped:no-candidate]` and is staged (`git diff --staged` shows it) but not committed.
- `[H]` **Read the raw map view as a human deciding whether to trust it.** Does a superseded row read as "this was corrected, here's what it says now" or does it read as noise/a duplicate? If the latter, the status tag isn't doing its job.
- `[G]` `knowledge_index.py` run directly (not through the tab) against a personal-estate map produces correct output — confirms the shared resolver, not just the tab's use of it.
- `[G]` A deposit built (`run.py deposit`, or the equivalent test harness) from a machine with a populated `data/knowledge_curator/` carries nothing under that path in the resulting outbox.
- `[G]` The new deposit auditor fails loudly (red gate, named violation) if `EXCLUDED_FROM_DEPOSIT`'s check is temporarily commented out in a scratch branch — confirms the auditor actually exercises the property rather than trivially passing.
- `[W]` `python verify.py` is green, and the printed auditor/tester counts match what's claimed in the report.

---

## Reporting

`docs/COWORK_REPORT_curator_correction.md` — what was built, any design call in this brief you overrode, and the actual reason strings/constants/route names if they ended up different from what's drafted above. `docs/UAT_curator_correction.md` — the walk-sheet, `[G]`/`[W]`/`[H]` per 0031, for you to walk against a real personal-estate run. No forward-looking status document — `docs/README.md` §5 retires those by class.
