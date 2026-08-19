# Cowork brief — Phase 3: linking through the Curator — claims become the linking evidence

> **Draft status:** written 2026-08-17, ahead of its build. The Curator and
> ledger will both have moved by then — **re-verify every "already exists"
> claim against the tree before building**, per the estate's own rule that a
> brief describes the code in front of it, not the code remembered.
>
> **Amended 2026-08-19 (design thread).** D-B landed as **0049**, and its
> consequence paragraph relocated the down-tier work here: *"finding repeated
> asks is a query over claims, so it belongs beside the Curator's linking
> work rather than in a separate accounting round."* 0049 also sets its own
> homework — its **What would show this wrong** paragraph says clause 3 must
> be tested against the existing corpus **before anything is built on it**.
> That test is now **Task 0** below, and it is cheap: a query, not a build,
> runnable today against the claims corpus that already exists. It does not
> wait for Phase 2.

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` Phase 3; Tim's ruling that the Knowledge
Curator is the better route for linking conversations.
**Precondition:** Phase 2 closed green — link-proposal events need the ledger
to land in. **Task 0's recurrence probe is exempt from this precondition and
should be run first**, on its own, whenever there is an idle hour: it reads
the claims corpus and writes nothing.
**Depends on — this repo's rulings:** **0032** (recency is truth order),
**0033** (propose/ratify/execute — every link is ratified), **0049** (the
conversation corpus is a sensed input for down-tier opportunities; a proposal
names the local capability and the evidence it can, or it is a wish),
**0037** (plan-
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

## Task 0 ▸ the recurrence probe — 0049's own homework, run before anything is built on clause 3

0049 clause 3 says the conversation corpus is a sensed input for down-tier
opportunities. Its own falsifier says so plainly: *"If the corpus turns out to
hold no legible repetition — if every frontier session is genuinely novel —
then clause 3 has nothing to sense and the entry is an elegant description of
nothing."* That is testable for the cost of a query, and the query costs
nothing to run wrong, so it runs **before** any down-tier surface is designed.

**This is a probe, not a build.** Stdlib only, read-only, run from a scratch
file rather than committed to the toolkit — nothing here earns a place in
`l5gntools/` or a scanner registration until there is a finding worth
standing behind. Its output is a paragraph in this round's report.

**Input.** `data/knowledge_curator/claims.json` — the K2 extraction report:
`conversations[]`, each with `conversation_id`, `real_time`, and `claims[]` of
`{claim_text, quoted_source}`. No DB read, no vault access, no `mode=ro`
question to answer.

**Method.**

1. **Normalise** each `claim_text` to a token set: casefold, strip
   punctuation, drop a small stopword list. No stemming, no embeddings — 0041
   stands, and a probe that needs a model dependency is not a probe.
2. **Cluster** by Jaccard similarity over those token sets, with cheap
   blocking on shared rare tokens so the pass stays O(n·k) rather than O(n²).
3. **Report at three thresholds — 0.5, 0.6, 0.7 — and pick none.** The
   estate's founding near-loss was a `similarity_threshold = 0.6` whose
   reasoning was nearly lost; this probe does not get to introduce a fourth
   unexplained constant. The threshold sweep *is* the output, and the reader
   sees how much the answer depends on it.
4. **Require recurrence to be real, not echo.** A cluster counts only if it
   spans **≥ 3 distinct `conversation_id`s** and **≥ 2 distinct calendar
   weeks** by `real_time`. One long session restating itself is not a
   recurring ask, and without this filter it will dominate the top of the
   list.
5. **Print the top 20 surviving clusters**: member count, distinct
   conversations, first and last date, and **three verbatim `claim_text`
   examples with their `quoted_source`** — the evidence a human reads to
   decide whether the cluster is a real repeated ask or an artifact of the
   extraction.

**The honest caveat, stated on the output.** Claims are *statements learned*,
not *asks made*. Recurrence in claims is therefore a proxy for the recurrence
of a **topic**, not proof of the recurrence of a **request**. If the probe
passes on topic recurrence alone, say so in those words — a down-tier proposal
built on a mislabelled signal is exactly the wish 0049 clause 4 refuses.

**How to read the result.**

- **Pass** — the top 20 contains at least three clusters for which you can
  name a specific local capability that would have answered the ask, and the
  evidence that it can (0049 clause 4's bar, applied to the probe's own
  output). Clause 3 has something to sense; the down-tier work is worth
  designing, and these three clusters are its first candidates.
- **Fail** — no cluster survives the filter, or the survivors are all
  vocabulary noise ("the model", "the file"), or nothing suggests a capability
  that would replace the ask. Then 0049 clause 3 senses nothing on this
  corpus. **Record that as the finding, in the report, and do not build the
  down-tier surface.** A falsifier that fires is a successful test, and this
  one is cheap precisely so that outcome is affordable.
- **Either way, the number to write down** is the baseline 0049 clause 5 will
  be measured against later: recurrence declining in the corpus, observed —
  which is meaningless without a first observation, and this is it.

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
- Any down-tier surface, finding or proposal is built before Task 0's probe
  has been run and read → stop (0049's own instruction: tested before
  anything is built on it).
- A down-tier proposal appears without naming the local capability that would
  replace the ask **and** the evidence it can → stop; that is a wish (0049
  clause 4).
- The probe's threshold sweep collapses into a single committed constant
  without a stated reason → stop; that is the `0.6` near-loss, repeated.
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
- `[H]` **Task 0's probe, read cold.** Of the top 20 clusters, how many are
  real repeated asks rather than extraction artifacts or one session's echo?
  Name a local capability for three of them, or record that you could not —
  0049 clause 3 lives or dies on this line, and it is cheaper to kill here
  than after a surface is built on it.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Reporting

`docs/COWORK_REPORT_curator_linking.md`, walk-sheet
`docs/UAT_curator_linking.md`, stamped results after the month, not the
build. Record: D-E as ratified; the identity-corpus sources used; proposal
precision from the twenty-card walk; the coverage number, before and after;
whether the falsification questions can now be answered; and **Task 0's
probe result in full** — the three thresholds, the surviving cluster count at
each, the three named capabilities (or the honest absence of them), and the
baseline figure 0049 clause 5 will later be measured against. If the probe
failed, that paragraph is the most important one in the report, and it should
say what it means for 0049 rather than leaving the entry standing on an
untested clause.
