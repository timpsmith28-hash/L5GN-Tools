<!-- gate-frozen: commit=d1a1b76 -->

> **ARCHIVED** 2026-07-27 · completed pair · pairs with `COWORK_BRIEF_relink_scoring.md`; walk-sheet + results archive alongside
> Superseded by: the scorer fix this reports on landed and was walked (`UAT_relink_scoring_results.md`, 2026-07-25), then consumed by `apply_alignment`'s precondition 1.
> Read as testimony from 2026-07-25 (gaming rig, against a 4-day-old snapshot, no live vault touched). Its own `gate-frozen` marker above already exempts this file's "6 auditors + 40 testers" claim from live-count drift — do not update that number.

# Cowork report — relink scoring: evidence made independent before it compounds

**Pair:** `docs/COWORK_BRIEF_relink_scoring.md`. Session 2026-07-25, gaming rig.
**Gate:** `python verify.py` → **GREEN** (6 auditors + 40 testers), before and after
(the +2 testers are `tester_relink_scoring` and `tester_registry_path`).
**Nothing committed.** Everything staged for Tim's review.

Evidence is the 4-day-old snapshot the brief names
(`L5GN-Castle/data/Chronicler_Backup/chronicler.db`), driven through the real
`score_thread` / `decide` on a throwaway copy — no live vault touched, no `--apply`.

---

## Done vs pending

| Task | State | Note |
|---|---|---|
| A — co-origin de-duplication | **done** | structured `origin` column (Tim's ruling) stamped by S4/S5, derived as fallback in relink |
| B — auto-link requires corroboration | **done** | `MIN_AUTOLINK_ORIGINS = 2`; single-origin winners → `suggest` |
| C — cap filename/path counts | **done** | `SIGNAL_COUNT_CAP` filename_xref/path_mention = **3** (ratified after the dry-run) |
| E — no synthetic `repo_folder_path` | **done** | real path or NULL, never `<scope>/<canon>` |
| F — one config-driven `REGISTRY_PATH` | **done** | `db.resolve_registry_path()`, env-overridable; the five literals collapse to one |
| D — measured-ownership stoplist | **deferred** | as the brief permits; a precision improvement, not the `--apply` blocker |

A/B/C are the `--apply` blocker and are landed; the double-count is dead.

---

## The defect, as it actually appears on the live-derived snapshot

The brief's `filename_xref(0.97) ⊕ path_mention(0.90)` on `world_graph.json` is
stylised: `path_mention` keys on the *folder* token, not the file, so it never
shares a basename with `world_graph.json`. Reproduced against the snapshot
(365 thread/project pairs carrying persisted evidence), the three failure modes
are all present but their weight differs:

1. **Co-origin double-count (Task A).** The real co-origin case is `name_alias` +
   `path_mention` firing on the same **repo-name token** — **35 occurrences**
   (`l5gn_armory_v4`, `l5gn-crystal-spire`, `smelt-gateway`). One mention of the
   repo name produced two "independent" signals that compounded.
2. **Uncapped filename count (Task C).** `filename_xref` had no cap; distinct
   basenames per pair ran **1 → 32** (see distribution).
3. **Lone-signal auto-link (Task B).** A single unique-filename hit is weight
   1.0 → capped 0.97, clearing 0.90 with no rival — **192 pairs sit at exactly one
   file**, so a lone confident sentence could silently `evidence`-lock a thread.

---

## Task A — co-origin collapse

`origin` is stamped at produce time (`link_evidence.origin`, migrated in place on
existing DBs) and read by relink; a NULL origin (legacy/snapshot row) is derived
identically from `(signal, detail)` so behaviour is the same stamped or derived.
The key normalises `lower → strip one extension → strip separators`, so
`world_graph.json`, `world-graph` and the alias `world graph` all collapse to
`worldgraph`, and the folder token `L5GN_Armory_v4` and alias `l5gn armory v4` to
`l5gnarmoryv4`. `combine()` groups a project's signals by origin, keeps the
**strongest per origin**, then applies the per-type count cap and per-weight CAP.

**Before/after — the acceptance case and two real threads:**

| Case | Before | After | Why |
|---|---|---|---|
| `world_graph` cited as filename_xref + path_mention + name_alias (unit) | **0.997** | **0.970** | one origin, capped 0.97 |
| three *distinct* owned files (unit) | 0.99997 | 0.99997 (3 origins) | legitimately corroborated — unchanged |
| `SolConfig` "Code base audit and test coverage" | auto 0.970 (1 file) | **suggest 0.970, origins=1** | lone filename, no corroboration |
| `L5GN_Armory_v4` "Demo phase rollout" | auto 0.900 (repo-name alias+path) | **suggest 0.900, origins=1** | co-origin collapse → single origin |

Cross-type corroboration still counts when the types cite **different** origins
(`universal-content-pipeline` "UCP master smelter" keeps 4 origins at adjusted
0.9984 and still auto-links).

---

## Task B — corroboration floor

An auto-link writes an `evidence`-locked row, so it now requires **≥ 2 independent
origins** post-collapse, on top of `adjusted ≥ 0.90` and `lead ≥ 0.25`. The origin
count rides in the decision `summary` (`origins=N`).

Snapshot decision table, old scorer vs new:

| bucket | OLD | NEW |
|---|---|---|
| auto-link | 80 | **28** |
| suggestion | 61 | **113** |
| ambiguous | 27 | 27 |
| downgrade | 2 | 2 |
| no-op | 850 | 850 |

**52 former auto-links (all single-origin) are now suggestions.** Every one of the
28 surviving auto-links rests on **≥ 2 origins** (observed minimum = 2). Ambiguous
and downgrade volumes are unchanged, so the collapse/roll-up rules still hold.

---

## Task C — count caps, value defended

Distribution of distinct-basename `filename_xref` count per (thread, project):

| files | pairs |  | files | pairs |
|---|---|---|---|---|
| 1 | 192 |  | 6 | 6 |
| 2 | 52 |  | 8 | 5 |
| 3 | 28 |  | 9 | 2 |
| 4 | 7 |  | 10 | 1 |
| 5 | 1 |  | 19 | 1 |
|  |  |  | 32 | 1 |

`SIGNAL_COUNT_CAP` sets `filename_xref` and `path_mention` to **3**, mirroring the
spec's `vocabulary: 3`. The full dry-run at **cap 3 and cap 5 produced identical
decision buckets** (28/113/27/2) — the caps only scale already-saturated
file-heavy scores, so the choice is decision-neutral and 3 is the tighter,
spec-consistent value that loses nothing. A collapses *co-origin* duplicates (Task
A); C bounds *distinct-origin* pile-up — different levers, both retained.

---

## Task E — no dead `repo_folder_path`

`load_registry()` no longer synthesises `f"{SCOPE_TO_ROOT[scope]}/{canon}"`. It
writes a real `repo_folder_path` when the registry entry carries one, else
**NULL** — so `upsert_project` can never stamp a `L5GN/<name>` path that exists on
no rig and mis-classifies a concept as a repo (`vault_reader` keys repo-vs-concept
on this column being NULL). The registry carries no absolute repo path today
(`file_inventory` holds only repo-relative paths), so the honest result is NULL
until a real path is supplied — never a guess.

---

## Task F — one registry path, resolved through config

`db.resolve_registry_path()` is the single source: `CHRONICLER_REGISTRY_PATH` env
first, else the per-host derived `<github_root>/L5GN/.intel_sync/…`. `build_registry`,
`relink` and `xref_filenames` call it; `build_inventory` / `build_activity` /
`build_vocabulary` inherit via `build_registry`. No literal
`GITHUB_ROOT_FS/"L5GN"/".intel_sync"` remains in five places, and a set env path is
honoured verbatim (no silent fallback to the dead literal).

**Confirmed fragility (why F matters):** on the restructured checkout
(`GitHub/L5GN/L5GN-Tools`) the derived `.parent.parent` now lands in
`GitHub/L5GN/L5GN/…` and no generated registry exists there — exactly the breakage
F removes. On the knight, set `CHRONICLER_REGISTRY_PATH` (already the recommended
knob) and writer + readers agree deterministically.

---

## UAT — acceptance checks (Tim walks these)

Full sheet: `docs/UAT_relink_scoring.md`. Every item **ready to walk**, none passed.
The decisive walk is on the **knight against the live vault** — that belongs to the
apply brief (Step 4); here the acceptance is the snapshot dry-run plus the hermetic
testers.

---

## Files changed

- **Code:** `chronicler/pipeline/db.py` (resolver + origin helpers),
  `relink.py` (A/B/C/E/F), `xref_filenames.py` (origin column, F),
  `extract_path_mentions.py` (origin column), `build_registry.py` (F).
- **New testers:** `tests/tester_relink_scoring.py` (A/B/C/E),
  `tests/tester_registry_path.py` (F); both registered in `verify.py`.
- **Doc housekeeping (Tim's ruling):** the +2 testers moved the gate count
  37 → 39; the stale count was updated in place in the six live docs that quote it
  (`COWORK_REPORT_file_census`, `COWORK_REPORT_intent_evidence`,
  `UAT_file_census`, `UAT_intent_evidence`, `UAT_cowork_run_2026-07-24` and its
  results log), and the now-stale optional `gate=6a/37t` was dropped from the
  walked results stamp (`docs/README.md` §3 — omit rather than assert a count you
  didn't observe). Actual archiving of the finished pairs is deferred to Step 5.
- **`verify.py` GREEN** (6 auditors + 40 testers) before and after.

Nothing committed. Nothing written to any live vault.
