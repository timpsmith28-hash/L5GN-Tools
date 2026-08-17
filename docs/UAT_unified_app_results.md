<!-- uat: commit=174e57e dirty=true host=LucasGoonPC walked=2026-08-17 -->

# UAT results — the unified app (`COWORK_BRIEF_unified_app.md`)

Sheet: `docs/UAT_unified_app.md`. Pair:
`docs/COWORK_BRIEF_unified_app.md` → `docs/COWORK_REPORT_unified_app.md`.

**Walked:** 2026-08-17 on `LucasGoonPC`, against `174e57e`.
`dirty=true` — two results logs from this Grand Walk were uncommitted at walk
time; no code was uncommitted.

**Gate:** `python verify.py` GREEN, 8 auditors + 66 testers, and green via the
pre-commit hook on every commit in `13fef34..174e57e`.

The sheet's **14 `[G]` items were already proven and cited during the build**
and are not re-walked here; the sheet lists them with their proofs. This log
records the **5 `[H]` items**, which only a human on the real machine could
answer. All five are now walked.

---

## `[H]` items

- [x] **H1. Reload mid-UAT-walk and mid-curator-ratification.**
  **Walked — unsubmitted content is lost.** Confirmed directly: verdicts and
  evidence entered but not emitted do not survive a reload.

  **This is declared behaviour, not a surprise.** The pane states it above the
  form, in bold: *"Nothing here is saved until you emit the results log — reload
  this tab, or lose the session, and these notes are gone."* The sheet's own
  `B5` item exists to check exactly this and treats it as the intended design.
  So the round did not introduce a regression and the warning is where a walker
  will read it.

  **Recorded as a finding anyway, because it is the highest-cost failure mode in
  the tool.** The two surfaces that hold unsubmitted human judgement — a UAT
  walk and a Curator ratification — are the two places in the estate where lost
  input cannot be recomputed from anything. A scan can be re-run; a judgement
  cannot. An accidental F5 partway through a 40-item sheet costs the walk.

  Not a defect against this round, and **not something to fix by reflex** —
  session-scoped-by-design is a real position, and the pane argues it. But if a
  draft-persistence pass is ever considered, this is its evidence, and the app
  being a local loopback surface means browser storage is available to it in a
  way it would not be elsewhere.

- [x] **H2. Start it from the shortcut, cold.**
  **Walked — partial pass with a real defect.** Tim: *"it feels halfway
  better — sometimes doesn't load first time on the work rig, but clicking
  again seems to work; feels like it times out on the initial load, then the
  follow-up is fine."*

  It reads as an application rather than a terminal in a costume, which is what
  the item asks. But an intermittent first-load failure that a retry fixes is a
  defect, and a launcher that sometimes needs a second go is the sort of thing
  that erodes exactly the "is this an application" property this item measures.

  `launcher.py` waits on `/api/health` before opening the window, so the
  suspicion is that wait being too short for a cold start on a slower machine —
  **suspected, not diagnosed.** Only reproducible on `10280L`. Do not lengthen
  the timeout without timings from a real cold start there; a timeout extended
  by guesswork is a longer wait before the same failure.

- [x] **H3. Is anything harder to find than it was across two ports?**
  **Passed.** *"Everything seems to be findable now."* Consolidation did not
  bury a surface — the finding this item exists to catch did not occur.

- [x] **H4. Could you debug it at 2am?**
  **Passed.** *"As it stands, yes I believe so — I can trace things to the
  files as needed."* The path from a symptom to the failing route is traceable
  with one process and one entry point.

- [x] **H5. Is the eighth module actually easy now?**
  **Passed, and it answers the brief's closing question.** Tim: *"it doesn't
  feel too crowded... I'm happy with it as the current iteration, but for future
  passes on the UI front we'll now be able to start from a proper list of
  modules which we can then organise properly before we build everything."*

  That is the round's own stated purpose met. `COWORK_BRIEF_unified_app.md`
  asks, last: *"State plainly, at the end, whether the deck is now in a shape a
  **design** round can work on."* The answer, in the walker's words, is that
  there is now a list of modules to organise **before** building — which is the
  thing that did not exist when the tab strip was seven hardcoded entries in
  markup. The descriptor registry (Task 1) is what makes a design round
  possible, and this is the evidence that it does.

  Recorded honestly alongside it: the module list grew by accretion rather than
  by design, and the walker says so. That is a statement about how it got here,
  not a finding against the shape it is in.

---

## Where this leaves the pair

All 19 acceptance checks on the sheet are answered — 14 `[G]` proven at build
time and cited on the sheet, 5 `[H]` walked here.

**The pair does not close yet.** `docs/COWORK_REPORT_unified_app.md` does not
exist, which is the only reason the docs board still shows `unified_app` in
*In flight* — the board's rule is a brief with no report, and the code has been
complete since `f1d7df3`. The report is the outstanding artefact, not the work.

The brief names what it must record: the 0034 ratification and what
ARCHITECTURE §3 now says; the module descriptor with the one migrated tab quoted
in full and the cost of migrating it; the Datasette verdict **and the honest
answer to what it was used for**; what became of 0013 and 0021; the data-root
resolution order and the exact migration step an existing install takes; the
launcher's second-instance behaviour; and everything now behind the `mesh` extra.

Two things this walk adds to that report: **H2's intermittent first load**, and
0035's deliberate deferral of the physical data-root move — Task 4 is partial by
ruling, not by omission, and the report should say so plainly so a cold reader
does not record it as an unfinished task.

## Carried findings

1. **Unsubmitted judgement is lost on reload** (H1). Declared, warned about, and
   still the most expensive thing that can go wrong. Evidence for a future
   draft-persistence decision; not a defect against this round.
2. **Intermittent first-load failure on `10280L`** (H2). Retry succeeds.
   Suspected `/api/health` wait; needs timings from a real cold start on that
   rig before anything is changed.
