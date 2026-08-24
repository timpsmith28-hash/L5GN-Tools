<!-- uat: commit=174e57e dirty=true host=LucasGoonPC walked=2026-08-17 -->

# UAT results — the unified app (`COWORK_BRIEF_unified_app.md`)

Sheet: `docs/UAT_unified_app.md`. Pair:
`docs/COWORK_BRIEF_unified_app.md` → `docs/COWORK_REPORT_unified_app.md`.

**Walked:** 2026-08-17 on `LucasGoonPC`, against `174e57e`.
`dirty=true` — two results logs from this Grand Walk were uncommitted at walk
time; no code was uncommitted.

**Gate:** `python verify.py` GREEN, and green via the pre-commit hook on every
commit in `13fef34..174e57e`.

*(No auditor/tester counts are stated here. The `uat` stamp above names the
commit, and the gate's composition at that commit is derivable from it —
`docs/README.md` §1: a document earns its place by holding something that
cannot be derived. The walk-sheet carries the build-time count, frozen, which
is where a frozen number belongs.)*

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

  **Diagnosed after the walk**, from a cold-start run on `10280L` with
  `__pycache__` deleted. It is not a slow start:

  ```
  INFO:     Uvicorn running on http://127.0.0.1:54553 (Press CTRL+C to quit)
  app: server did not answer /api/health within 20s
  ```

  The server came up correctly — startup complete, uvicorn bound, every route
  ENABLED. `create_app` does its heavy work **before** uvicorn can answer
  anything: an FTS5 index over **1812 authored documents** plus a Datasette
  snapshot, all ahead of the bind. On a cold cache that exceeds
  `HEALTH_TIMEOUT_S` (20s).

  That also explains why it is work-rig-only: `LucasGoonPC` carries **241**
  authored documents to `10280L`'s 1812.

  **The failure mode matters more than the delay.** The launcher reports failure
  while the server reports success, and its message — *"see its output above for
  why"* — points at output stating that everything worked. `H4` passed above;
  this is the case that would have failed it.

  **The fix is not the timeout.** `/api/health` should mean *the server is up* —
  bind first and build the index lazily, or have the launcher distinguish *no
  answer* from *answered, still initialising*. Raising 20s to 60s hides the same
  failure for a larger corpus.

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

**The pair closes with this log and its report.**
`docs/COWORK_REPORT_unified_app.md` was written 2026-08-17 — the only artefact
that had been missing, which is why the board showed `unified_app` in *In
flight* while the code had been complete since `f1d7df3`. The board moved it to
*Walked* on the report landing.

The report carries this walk's two additions: **H2's first-load failure**, now
diagnosed above, and 0035's deliberate deferral of the physical data-root move
— Task 4 is partial **by ruling, not by omission**, and the report says so
plainly so a cold reader does not record it as unfinished work.

It also records two things it found that this walk did not look for:
`ARCHITECTURE` §3 is still silent about the app tier (the string `0034` appears
nowhere in that file), and 0021's supersession entry — flagged by the build as
due once Task 4 landed — was never written. Both are outstanding deliverables
of this round rather than follow-ups.

## Carried findings

1. **Unsubmitted judgement is lost on reload** (H1). Declared, warned about, and
   still the most expensive thing that can go wrong. Evidence for a future
   draft-persistence decision; not a defect against this round.
2. **First load after a `git pull` fails on `10280L`** (H2, diagnosed). Not a
   slow start: `create_app` builds an FTS5 index over 1812 documents and mounts
   Datasette before uvicorn binds, so `/api/health` cannot answer inside the
   launcher's 20s wait on a cold cache. **The launcher reports failure while the
   server reports success.** Work-rig only — the gaming rig carries 241
   documents. Fix by binding before building, not by lengthening the timeout.
