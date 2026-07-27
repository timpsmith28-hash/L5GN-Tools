> **ARCHIVED** 2026-07-27 · completed pair · pairs with `COWORK_BRIEF_apply_alignment.md`; walk-sheet + results archive alongside
> Superseded by: nothing — terminal report of this effort. The seed_suppress fix it documents (`b7c2390`) and the vault-freeze fix (`finalize_db.py --apply`) are both live in the vault/registry now, not pending.
> Read as testimony from 2026-07-27. The "412 changed" first-apply figures it references are already marked superseded within its own text and in `UAT_apply_alignment_results.md` — do not treat as current even on a second read.

# Cowork report — apply alignment: the golden close-out (chats linked to projects & programs)

**Pair:** `docs/COWORK_BRIEF_apply_alignment.md`. Session 2026-07-27, knight
(`l5gn-castle-worker`) + gaming rig (`LucasGoonPC`).
**Gate:** `python verify.py` → **6 auditors, 42 testers**, GREEN before and
after the one code change this round produced (`tester_build_registry`
gained 3 assertions; no new tester file).
**One commit:** `b7c2390` — the seed_suppress fix. Everything else this round
is vault *state*, not repo code: a relink apply (run twice — see below), a
vault-freeze stamp, and a deposit/consume pass.

This is the run that reaches the brief's **golden UAT point**. It did not go
straight there: a defect found mid-verification meant the apply was executed
twice, and a second, unrelated gap (an unfrozen vault schema) surfaced while
closing out the deposit/consume step. Both are found-and-fixed in this round,
not deferred and not laundered into a clean-looking final count — the
contaminated first pass is preserved in the results log, marked superseded,
not edited away.

---

## Done vs pending

| Item | State | Note |
|---|---|---|
| Preconditions 1–5 | **all MET** | scorer fix's missing results log closed separately this session (`UAT_relink_scoring_results.md`) |
| Task 1 — re-derive evidence live | **done** | registry/inventory/xref/path-mentions all re-run against the live vault |
| Task 2 / 8 — dry-run GO/NO-GO | **done, run three times** | baseline → +4 unmapped Claude names → + Bridge `low_signal_body` fix → (defect found) → corrected post-seed_suppress-fix |
| Task 9 — apply | **done, run twice** | first pass 412 changed (**contaminated**, see below); corrected pass 343 changed |
| **seed_suppress registry defect** | **found and fixed mid-run** | auto-regenerated a curated-removed alias, false-linking 6 threads on zero real evidence |
| Task 10 — verify landed clean | **done** | re-run in full against the corrected apply; original run's numbers kept in the log, marked superseded |
| Task 11 — deposit/consume/wall | **done** | + a second, unrelated finding (vault never frozen) found and fixed along the way |
| Task 12 — this report + walk-sheet + results | **done** | |
| Task 13 — archiving sweep | **next** | |

---

## The headline finding: `seed_aliases()` silently undid a curated removal

### What broke

`config/project_registry.json` carries a curated `note` on `l5gn-castle-repo`
explaining that its short-name alias `"Castle"` was **deliberately removed**
— it collides with the knight's own hostname (`l5gn-castle-worker`), which
appears constantly in shell transcripts, chat logs, and file paths that have
nothing to do with the actual project. The same reasoning applied to
`l5gn-archive-repo` / `"Archive"`.

`build_registry.py`'s `seed_aliases()` didn't know that. Every build, it
re-derives a short-name alias by stripping generic prefix tokens
(`{"l5gn","mcf"}`) off the canonical name — `"L5GN-Castle"` → `"Castle"` —
and the old `_merge_alias_lists()` was a pure union: curated aliases plus any
seeded alias not already present. A curated *removal* had no way to stick;
the next registry build silently put `"Castle"` right back.

### The damage

Six threads were auto-linked to `l5gn-castle-repo`/`l5gn-archive-repo` in
Task 9's first apply on **zero genuine evidence**. Direct inspection of each
thread's `link_evidence` rows (not inferred — queried) showed exactly two
rows per thread, both Castle-alias-derived (`path_mention:Castle(0.9)` +
`name_alias:Castle@body(0.15)`), nothing else. `path_mention` carries no
`low_signal_body` demotion (that fix only touches `name_alias` body hits),
so the false signal scored *harder* via path mentions than it would have via
name aliases alone.

This was caught by the golden read-surface check itself — the human-in-the-
loop step the brief's UAT explicitly calls for — not by an automated gate.
`l5gn-castle-repo`'s 11 auto-linked threads didn't look right against the
registry's own documented note, and following that thread back through the
code (not just the data) found the generator defect.

### The fix

```python
# chronicler/pipeline/build_registry.py
def _merge_alias_lists(curated: list, seeded: list, suppress: list | None = None) -> list:
    out = list(curated)
    suppressed = {norm(s) for s in (suppress or [])}
    for a in seeded:
        if norm(a) in suppressed:
            continue
        if not any(norm(a) == norm(x) for x in out):
            out.append(a)
    return out
```

A new curated field, `seed_suppress: ["Castle"]` / `["Archive"]`, tells the
generator which auto-derived aliases a human has deliberately ruled out.
Three assertions added to `tester_build_registry.py` pin the exact
false-positive class (a seeded alias not curated is still added normally;
a suppressed one is dropped; the curated alias beside it is untouched;
comparison is case/separator-normalised). `verify.py` GREEN before commit.

### The redo

Not a manual patch of the contaminated rows — a full clean redo, per Tim's
explicit ruling ("agree with your recommended course of action"):

1. Registry rebuilt with the fix (`l5gn-castle-repo` aliases confirmed
   `['L5GN-Castle']` only, no bare `'Castle'`).
2. S5 (`extract_path_mentions --rescan --apply`) re-run: 200 new evidence
   rows across 110 threads.
3. The 6 tainted threads' Castle/Archive-derived `link_evidence` rows
   deleted — caught an incomplete first cleanup SQL (missed `name_alias`
   rows, whose `detail` bakes in a position suffix — `"Castle@title"` — that
   a bare-string match doesn't catch) and broadened it.
4. Fresh dry-run: **3 / 225 / 115 / 0 / 333** (auto-link / suggestion /
   ambiguous / downgrade / no-op), 49 already-locked threads correctly
   excluded and unaffected.
5. Fresh GO ruling, in chat, against this exact table.
6. Re-apply: **"Applied. 343 thread(s) changed / queued."** (3+225+115=343,
   reconciles exactly).

The first apply's table (55/236/121/0/313, 412 changed) and its Task 10
verification are kept in the results log in full, with a superseded notice —
not deleted, not quietly corrected in place.

---

## Task-by-task, corrected/final state

### Preconditions

All five MET — scorer fix, registry ratified, clean identity base, Crystal
Spire `first_seen`, off-box backup. Full evidence table in the results log.

### Task 1 — re-derive evidence live

Registry / inventory / xref-filenames / path-mentions all re-run against the
**live** vault (not the 4-day-old snapshot the brief warns about).
`link_evidence.project` confirmed id-keyed throughout, not canonical-name
strings — the repo-tier producers round's Finding-3 fix holding as intended.

### Task 2/8 — dry-run gate

Iterated three times as unmapped-Claude-name rulings and the Bridge
`low_signal_body` fix landed, each with its own table in the results log; the
GO that actually got applied is the corrected, post-seed_suppress-fix table
above — the earlier tables were dry-runs on a still-defective registry and
were correctly never applied as-is.

### Task 9 — apply

Run twice; only the corrected 343-change apply stands. See "The redo" above.

### Task 10 — verify landed clean

Re-run in full against the corrected apply:

| check | result |
|---|---|
| `project_link IS NOT NULL` | 52 (49 prior-locked + 3 new) |
| orphan check | 0 rows |
| `link_ambiguous/pending` | 115 — exact match |
| `link_upgrade/confirmed` | 52 — exact match |
| Castle/Archive evidence rows | 0 |
| duplicate thread_id in pending queue | 0 |

One variance investigated rather than waved through: `project_link/pending`
= 251, not 225. Root-caused (date-split + dedup query, not guessed) to 10
rows pre-dating this session plus 16 stranded rows from the *first*
(contaminated) apply — `clear_pending_relink_rows()` only clears a thread's
queue row when that thread lands in a scored category on the *current* run,
so a thread that flipped from `suggest` (bad evidence) to `no-op` (correct
evidence) left its old row behind. No duplicates, no re-insertion bug — inert
staleness. **Tim's call: leave for now**, same disposition as the original
10.

### Task 11 — deposit / consume / wall check

Two corrections along the way, both surfaced rather than stepped around:

1. **Instruction error, caught immediately.** `deposit --push` was first run
   on the knight; it belongs on a *producer* rig. The knight's
   `role: consumer` config has no `push_target` by design — the "not
   configured" note was expected behaviour, not a failure.
2. **Real finding: the vault was never frozen.** `consume` reported
   `(vault: schema_mismatch)` and `drift=needs_inputs` on both estates.
   Traced to `l5gntools`' `vault_reader`/`project_trail` gating on `PRAGMA
   user_version == 1`; the live vault reported `0`. Ruled out a stale
   deploy (`git log` confirmed the knight on `b7c2390`, clean tree).
   Root cause: `chronicler/pipeline/finalize_db.py` — a round-3
   "finalize & freeze" script (P1 leaked-thread-id repair, P2 `'none'`→NULL
   migration, P3 `threads.substantive` population, then the freeze stamp)
   — had simply never been run against this vault. Dry-run confirmed it was
   safe (P1=0, P2=0, P3 recomputed the *same* already-correct 272/453
   split); applied with an automatic backup, before/after census identical,
   post-conditions passed. `consume` re-run clean: `vault: ok`, both
   estates `verified=True`, `estate_diff=ok`, real drift computed
   (`discussed_not_present=0/0`, `talked_not_built=0/0`,
   `built_not_discussed=2/4` — ordinary recent-commit drift, not a gap).

**Wall check: held.** `personal` and `work` land in independently-namespaced
directories under `/home/l5gn/vault/estates/`, each ingested and
manifest-verified separately — `deposit.py`'s namespace-enforcement guard
(a rig may only deposit into its own declared estate) confirmed intact end
to end.

---

## UAT — acceptance checks (Tim walks these)

Full sheet: `docs/UAT_apply_alignment.md`. Full walk cross-reference:
`docs/UAT_apply_alignment_results.md` (final section). Golden, provenance,
no-over-count, identity and wall checks all evidenced against the
**corrected** state; the contaminated first pass and the defect that
invalidated it are documented, not hidden.

---

## Files changed

- **Code:** `chronicler/pipeline/build_registry.py` (`seed_suppress` /
  `_merge_alias_lists`), commit `b7c2390`.
- **Tests:** `tests/tester_build_registry.py` (+3 assertions, same commit).
- **Config (rig-local, gitignored, not committed):**
  `config/project_registry.json` — `seed_suppress: ["Castle"]` /
  `["Archive"]` added to `l5gn-castle-repo` / `l5gn-archive-repo`.
- **Vault state (knight, not repo code):** relink apply (corrected, 343
  changed), `finalize_db.py --apply` (schema freeze stamp, zero data
  change), deposit/consume.
- **Docs:** `docs/UAT_apply_alignment.md` (new, walk-sheet),
  `docs/UAT_apply_alignment_results.md` (extensive, both apply passes
  recorded), this report.

Nothing else committed. The archiving sweep for this round's now-closeable
brief/report/UAT triples is the natural next step (Task 13).
