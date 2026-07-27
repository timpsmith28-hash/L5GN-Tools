<!-- uat: commit=00d590d dirty=false host=LucasGoonPC walked=2026-07-27 -->
<!-- gate= deliberately omitted, per the disposition recorded in
     docs/UAT_solo_playbook_results.md: auditor_uat_stamp checks the field
     against the LIVE tree, so a truthful historical count turns red the moment
     a tester is registered. commit, host and walked carry the provenance that
     matters; the count is recoverable from the commit. -->

# Results log — Command Deck prototype (walked 2026-07-27, gaming rig)

Partner to `docs/UAT_command_deck_proto.md` /
`docs/COWORK_BRIEF_command_deck_proto.md`. Walked on `LucasGoonPC` against the
**dev vault** (`C:\Users\timps\Documents\chronicler_dev`), not the knight.

This log records **evidence**, not acceptance beyond what is stated. Items the
walk could not reach are recorded as unwalked with the reason, not softened.

---

## Headline

**The prototype does the thing it was built to do.** The pending queue stopped
being one flat list and became 29 project-scoped batches. Tim's read at the
deck, verbatim: *"that definitely feels easier and already it sharpens the view
and mind properly."*

Two defects were found by walking it, both fixed in `00d590d`, neither visible
to the build thread's own gate:

1. **No migration path.** The round declared its schema inside `CREATE TABLE IF
   NOT EXISTS`, a no-op on an existing vault. The backfill threw `no such
   column: candidate_project` and the deck would have died on first read.
   Every tester builds its DB fresh from `schema.sql`, so the gate was
   structurally blind to it — the `CREATE` always fires under test and never
   fires in reality.
2. **A leaked sqlite handle** on `core.connect`'s refusal path, which
   `app._connect` reaches from every route handler — one open connection per
   HTTP request against an unmigrated vault. Green on Linux, red on Windows;
   see `docs/investigation/2026-07-27_gate-green-on-linux-red-on-windows.md`.

---

## Walked

| Item | Evidence |
|---|---|
| **1.1** migration on a real vault | `backfill_candidate_project.py` ran instead of throwing — `db.ensure_deck_schema` migrated `chronicler_dev` in place. **Reported 0 rows** (see Unwalked). |
| **1.3** relink writes the columns | `relink.py --apply` on the dev vault; the deck's grouping, counts and rival badges are all driven by `candidate_project`/`rival_project` from that run. |
| **1.4** review opens | Bound `0.0.0.0:8002`, registry resolved at 61 link-target ids, UI served, `GET /api/queue/projects` 200. |
| **2.1** grouped nav | **29 projects with pending threads**, each with count and breadcrumb; selecting one loads only its batch. |
| **2.2** the rival case, real data | *"Building a terminal-based D&D world for Discord"* under `build-it-yourself`, marked **rival candidate**, primary `l5gn-crystal-spire`. |
| **2.4** nav scrolls independently | Added during the walk — 29 projects overran the fold. `#nav` sticky with its own `overflow-y`; static under the 45rem breakpoint. |
| **2.5** rival tag ruling | `→ <other candidate>` button, rendered only where a second scored candidate exists; reuses `POST /api/rule` (200 observed), clears the thread from both batches. |
| **3.1** (first half) batch accept | `POST /api/rule/batch` 200, rows cleared, nav counts refreshed. |
| **3.3** rejection clears, rival survives | Both routes exercised on real data: "Not this project" cleared the row from that batch without touching the other candidate's; the rival tag ruled it across. |
| **4.1** honest skip | Hit **genuinely and unplanned** — the web stack was not installed, and `run.py review` refused with the `pip install -e .[review]` hint before doing anything else. |

Supporting environment facts recorded at walk time: the dev vault's accounts are
`gemini-personal` (1062) and `claude-personal` (39); `review_queue` also holds
1028 `close_suggestion` and 1062 `thread_grouping` rows, which the deck ignores
by design (`QUEUE_TYPES`).

---

## Unwalked, with reasons

- **1.2 — the backfill's note-parsing has never met a real note.** 1.1 reported
  **0 rows** because the dev vault had no project-link queue rows at all: the
  solo-playbook walk only ever ran relink in dry-run there. So the migration half
  is proven and the recovery half is not. **This is the item gating the knight**,
  whose ~500 live rows predate the columns and can only be recovered from `note`
  prose. Reproduce on dev with
  `UPDATE review_queue SET candidate_project=NULL, rival_project=NULL` after a
  relink apply, then dry-run the backfill.
- **1.5 — clean refusal against a real unmigrated vault.** Verified against a
  synthetic pre-deck DB (exit 2, remedy named); not against a real copy.
- **2.3 — the wall.** **This vault cannot answer it.** It holds only
  `*-personal` accounts, so there is no work thread to exclude and a clean result
  proves nothing. Covered structurally and hermetically only. The real walk is a
  machine holding work data — and per **DECISIONS 0025** that check changes
  shape, since the filter becomes estate-scoped rather than personal-only.
- **3.1 (second half) — relink skips accepted threads.** The half that proves the
  write is also the lock. Not run.
- **3.2 — partial failure in the browser.** Proven against synthetic data (one
  good + one bad pair, good committed, bad reported); needs a deliberately bad
  id to reproduce by hand, so it may reasonably stay tester-covered.
- **3.4 — column scope.** Hermetic only, by design: `tester_review`'s snapshot
  comparisons are the proof, not a browser session.

---

## Disposition

The pair is **not closed**. The prototype is accepted as doing its job; 1.2
remains open and is a precondition for taking any of this to the knight. The
deck's next state is governed by `COWORK_BRIEF_estate_scoped_visibility.md`
(0025) before the work-laptop walk.
