# Cowork brief — Phase 3: linking through the Curator — claims become the linking evidence

> **Draft status:** written 2026-08-17, ahead of its build. The Curator and
> ledger will both have moved by then — **re-verify every "already exists"
> claim against the tree before building**, per the estate's own rule that a
> brief describes the code in front of it, not the code remembered.

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` Phase 3; Tim's ruling that the Knowledge
Curator is the better route for linking conversations.
**Precondition:** Phase 2 closed green — link-proposal events need the ledger
to land in.
**Depends on — this repo's rulings:** **0032** (recency is truth order),
**0033** (propose/ratify/execute — every link is ratified), **0037** (plan-
derived parameters; K-stage invocations stay conductor-scoped), **0039**
(the Curator is scoped to the machine's declared estate), **0040** (stable
conversation ids join through the curated map), **0044** (Curator data dir
posture), **0046** (recency resolves the curated map), D-C/D-D as ratified,
and **D-E — ratified before code** (thread↔project linking derives from
Curator claims and is ratified through Desk cards; the Curator's read-only
rule is preserved by writing through the ledger's ruling path, never by the
Curator itself; draft in `docs/investigation/2026-08-17_quartermaster_fable_2-response.md`).
**Deliverable:** the Curator's match pass gains project-identity as a match
target; confirmed matches become link-proposal events; the Desk gains its
second card type (thin-evidence linking); a ratified card writes
`project_link` / `link_evidence` through the established narrow ruling path;
`relink.py` demotes to fallback. **Exit test: the substantive-thread linking
coverage number (INTENT §2's ~8%) is re-derived after a month of use, and it
moved.**

---

## Why claims, restated once

`relink.py` links whole threads on thin signals, and coverage on threads
that matter sat near one in twelve. K2 extracts claims whose
`quoted_source` must be a verbatim substring of the thread; K4 confirms
matches in two stages (shortlist, then a yes/no with the matched span quoted
back). A thread whose *claims* match a project's corpus and identity signals
is linked by evidence a human can read in one glance — the only link INTENT
permits anyone to trust. The Curator built the engine; this round points it
at the estate's oldest debt.

## What should already exist — re-verify at build time

- K1's `knowledge_index.json` join surface (generated registry, per-project
  paths); K2's claim cache with watermark; K4's two-stage confirm and its
  decision rules; K5's report.
- The conductor's plan/approve/run path over K-stages
  (`planner.py`, `conductor_run.py`, `candidates.py`), with the calibration
  ledger — linking sweeps are conductor-planned work, not a new runner.
- The ledger's event tables and the Desk's card mechanics (two rounds old
  by now, with their reports to read first).
- The narrow ruling write path (`review/core.py`'s scope pattern) and the
  confidence order `none < fuzzy < evidence < exact < manual`.

## Working rules

- **The Curator stays read-only, without exception.** New match targets, new
  proposal output — still zero writes from any K-stage to any vault table.
  Proposals land as ledger events written by the K-stage's *output consumer*
  (the same posture as scanners writing under `data/`), and the vault write
  happens only at ratification, through the ruling path.
- **Every link is ratified in v1.** No auto-linking, no confidence floor
  that self-applies. If a future policy (Phase 4) is ever to auto-ratify
  `exact`-tier matches, that is a promotion ratified from *observed* ruling
  repetition, not a default shipped here.
- **A proposal card quotes both sides** — the claim's `quoted_source` and
  the matched project signal — K-spec discipline carried onto the card. A
  link card the operator cannot verify in one glance is not raised.
- **Confidence vocabulary is 0032/ARCHITECTURE's existing order**, not a new
  scale. A claim-derived link lands as `evidence` with its
  `link_evidence` rows; ratification is what `manual` already means.
- **Newest-first within a project, whole-project or prefix units** (0037) —
  linking sweeps obey the same planning rules as every other K-stage run.
- **`relink.py` demotes, not deletes** — the 0036/0041 mothball posture:
  fallback for corpora with no extracted claims, named as such where it
  runs.

## Tasks

1. **The identity corpus.** Per project, derive matchable identity signals
   from what already exists — registry names, repo folder paths, K1's
   knowledge files, filename mentions (S5's `path_scan_log` /
   `xref_filenames` already mine these). No new scanning; this is a join of
   existing signal sources into K4's shortlist input.
2. **The match-pass extension.** K4 gains the project-identity target
   alongside the KNOWLEDGE corpus: same shortlist mechanics, same two-stage
   confirm, output a **link proposal** `{thread_id, project, claim_ids,
   quoted spans, confidence rationale}` rather than a gap/cross-project row.
   Unlinked substantive threads first — that is where the 8% lives.
3. **Link-proposal events.** The run's consumer writes proposals to the
   ledger (append-only, superseding stale proposals for the same thread per
   0046's recency rule). The K5 report gains a linking section so a run is
   still legible without the Desk.
4. **The second card type.** Desk cards from open proposals: thread title +
   date, proposed project, the quoted claim spans, options `ratify` /
   `reject` / `not sure — resurface with next run`. Ratify writes
   `project_link` + `link_evidence` rows through the ruling path and marks
   the proposal event superseded. Card volume is throttled (newest-first, N
   per render) — the Desk's failure mode is flood, and this card type is
   the one that can flood.
5. **The sweep as conductor work.** Linking runs are planned, approved and
   paced like any K2/K4 work — idle-window sweeps are exactly what the
   calibration ledger and thermal governor were built for. No new runner,
   no cron.

## Explicitly out of scope

- Auto-ratification at any confidence tier (Phase 4 territory, and only via
  observed promotion).
- Contradiction detection, Layer-C semantic grouping revival (0041 stands),
  or any new embedding dependency.
- Backfilling non-substantive Takeout fragments — coverage of what matters
  beats coverage (INTENT §4).
- Any change to ingest, normalizers, or the relink scoring it falls back to.

## Stop conditions

- Any K-stage writes to any vault table → stop (D-E's core clause).
- A link lands without a ratification ruling behind it → stop.
- A proposal card is raised without both quoted sides → stop.
- A new confidence scale appears → stop; the existing order is the contract.
- A sweep interleaves projects or reorders within one → stop (0037).
- The Desk floods (more link cards raised than the throttle) → stop and
  design the dedupe against the real noise, per the plan's standing risk.

## UAT — acceptance checks (Tim walks these)

- `[G]` A ratified card produces exactly the `project_link` +
  `link_evidence` rows the ruling path allows, and nothing else; a rejected
  one produces a superseding event and no vault write.
- `[G]` Re-running the sweep after ratifications proposes nothing already
  ruled (recency supersession working), and the claim cache watermark skips
  unchanged threads.
- `[G]` `relink.py` still runs, labelled as fallback, and touches nothing
  the claim path now owns.
- `[H]` **Ratify twenty real link cards.** How many were right? A wrong
  proposal *ratified* is the record-believed-while-wrong failure (INTENT
  §6.2) — count near-misses honestly.
- `[H]` **Ask the falsification questions** from INTENT §2 (*why was
  vocabulary killed; why 0.6*) once coverage has moved. Can the system
  answer either yet? That is the thesis's own test, and this phase is its
  best shot to date.
- `[H]` **The coverage number, re-derived after a month**: state it beside
  the ~8% baseline. This line is the round's verdict.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Reporting

`docs/COWORK_REPORT_curator_linking.md`, walk-sheet
`docs/UAT_curator_linking.md`, stamped results after the month, not the
build. Record: D-E as ratified; the identity-corpus sources used; proposal
precision from the twenty-card walk; the coverage number, before and after;
and whether the falsification questions can now be answered.
