<!-- uat: commit=53ab5ba dirty=true host=LucasGoonPC walked=2026-08-01 -->
<!-- dirty=true is the honest value and the only possible one: this slice is
     uncommitted by construction (0028 stages, never commits; and nothing here
     staged anything). The walk ran against the working tree at 53ab5ba.
     gate= is deliberately omitted. `verify.py` was GREEN at every run during
     the walk, but a truthful count recorded here turns red the moment the next
     round registers a tester, and the cheapest way back to green is to edit
     this file. docs/README.md §3 makes gate= optional for exactly that reason,
     and UAT_solo_playbook_results.md records the day that lesson was learned. -->

# Results log — the docs board, read-only (walked 2026-08-01, gaming rig)

Partner to `docs/UAT_docs_board.md` / `docs/COWORK_BRIEF_docs_board.md`.
Report: `docs/COWORK_REPORT_docs_board.md`.

**Evidence lives on the walk-sheet, not here.** Every check in
`docs/UAT_docs_board.md` carries its mark and its evidence on its own line.
That is deliberate and it is the finding this round exists to expose: five
existing pairs record their evidence in the results log against an untouched
sheet, and this walk declined to become the sixth. This file records the
**ruling** — what was accepted, what was not, and what is carried.

`verify.py` GREEN proves the code works. This log records what Tim ruled on
each item; only that closes the pair.

---

## Ruling

**Sections A–G walked. 40 passed, 5 passed with a note, 1 carried.** The pair
is accepted with **E7 explicitly carried**, named below.

| section | outcome |
|---|---|
| **A** — the board matches reality | pass; A5 and A7 with notes |
| **B** — the checkbox inconsistency is visible | pass, all four |
| **C** — odd shapes handled | pass; C5 with a note |
| **D** — reading a card body | pass, all five |
| **E** — runs on a machine the old preflight refused | pass; **E7 carried** |
| **F** — the gate and the reversible part | pass, all five |
| **G** — layout | pass; G3 and G9 with notes |

---

## What was accepted, and on what evidence

**The board matches reality, and the brief did not.** Four cards sit in a
different column from the brief's four-day-old table, and the archived column
divides into 8 pairs, 3 walk-only and 14 unmatched rather than the "12 pairs"
the brief asserted. Recomputing was the right instruction.

**The checkbox convention is applied two ways, in five places.** The brief
named two; the board found `work_rig_solo`, `apply_alignment` and
`relink_scoring` as well — and the last two were **archived** in that state,
so the split predates the cases anyone had noticed. Nothing was reconciled.
Every flagged card still prints `0 done` beside the results log's count.

**The refusals hold on the wire.** `docs/DECISIONS.md` and `../../etc/passwd`
return byte-identical 404s — a traversal attempt and a real-but-unlisted path
are indistinguishable to the caller, because both are digests of nothing.

**The board runs where the old preflight refused.** With `estate: both` the
process starts, serves the board in full, and renders no thread anywhere. The
queue routes 503 with `reason: estate_unresolved` naming the estate rather than
claiming a missing DB — two different gaps that the old code could only report
as one.

**The wall did not move.** Scoping the estate clause to the vault half was the
riskiest change in this slice. `--host 0.0.0.0` on a non-personal estate still
refuses and returns without binding a port.

**The `gate-frozen` ruling stands (F1).** Five finished documents were frozen
at the commits they name rather than having `53` edited to `54`. Ruled: *"you
did the right thing."* The diff is 29 insertions and 0 deletions; no body line
was touched. The reasoning that decided it: `UAT_toolkit_self_scan_results.md`
records what `verify.py` **printed** on a stated day at a stated commit, and an
observation is not edited to match a later tree. That is the drift
`auditor_doc_claims` exists to catch, run backwards.

---

## One defect, found by the walk and fixed

**E6.** The loopback refusal printed *"DECISIONS 0025 requires a **work-estate**
surface to bind loopback only"* while printing `'both'` one clause earlier.

The condition has always been `!= "personal"`. Until this slice, an
unrecognised estate exited at the estate-clause check and never reached that
line — so only `work` ever saw it and the wording was true by accident.
Scoping the clause refusal to the vault half is precisely what made it
reachable with `both`, where it contradicts itself.

Corrected to *"any non-personal estate"*. Message text only; the condition and
the refusal are unchanged, and the refusal was already correct.

Worth recording as a shape, not just a typo: **widening what a code path
accepts makes downstream messages reachable in states their author never
pictured.** The check that caught it was the one the sheet called "the check
that matters most in this section", which is the argument for writing that
sentence on a check.

---

## Carried, not walked

**E7 — the repo anchor on the work rig.** Section E was simulated on the gaming
rig with `estate: both`. That rig has the toolkit **inside** a configured
estate root (since `6dd70f1`), so containment passes on the estate roots alone
and the repo anchor does nothing observable there. A green result would have
evidenced nothing, which is why it is recorded as carried rather than ticked.

`tester_docs_board` drives the anchor directly — `REPO_ROOT` resolves to this
checkout, a real `docs/` file is read through it, and both an outside path and
the `<repo>-evil` sibling are refused. That covers the logic.

**It does not cover the configuration.** The work rig is where the toolkit
falls outside every configured root, and that machine is the reason the anchor
was written. **This is the one claim in the slice resting on a tester alone.**
Walk it on the next work-rig session and record it on the sheet.

---

## Passed with a note

- **A5** — the counter was checked against an independent count (85 and 9, both
  matching), but in the build sandbox rather than on the rig.
- **A7** — `git status` was byte-identical across the whole session, before and
  after browsing, which is the load-bearing half. Reload-is-identical was not
  separately observed.
- **C5** — the walker looked at two cards stamped `retired` and reported "no
  mention of retired". The text was there; the **weighting** was not. The
  mechanical kind (`UNMATCHED`) renders as an amber chip and reads as the
  card's headline, while the disposition — the archivist's judgement, which
  this round's report argues outranks the kind — is body prose two lines below.
  The card weights them backwards. **Not a derivation defect and not fixed
  here**; a design-thread question about whether disposition earns a chip.
- **G3** — no bleed-through in dark. `Canvas` resolves per colour-scheme, so
  light is a genuinely different render and the one a hardcoded hex would have
  broken.
- **G9** — the ~70rem breakpoint was not exercised.

---

## What this walk cost, and why it is recorded

Three checks were lost to the sheet's own commands, not to the code: `grep` and
`curl` are POSIX habits, and the example port said 8000 where
`REVIEW_DEFAULT_PORT` is 8002. Two checks were reported as failures that were
actually `ERR_CONNECTION_REFUSED` against a port nothing was listening on — a
refused connection is not a refused document, and it evidences neither pass nor
fail.

A related trap, worth carrying forward: **a browser address bar cannot test the
traversal refusal at all.** Chrome normalises `../../` out of a URL before
sending it, so that check must be `curl.exe`, which sends the path as typed.

This sheet is walked on a Windows rig. Its commands should be Windows commands
and its examples should match the code they invoke. Both are fixed on the
sheet.

---

## Not accepted, because it was never offered

Task 3 (ratification) and Task 4 (staging) were deferred by instruction before
any code was written. **DECISIONS 0028 is ratified and remains unexercised** —
nothing in this slice stages a working-tree change, and no card offers an
archive action. C3 confirms the controls are absent rather than disabled.

Nothing was committed by this walk. `git status` reads ten modified and four
untracked files, all authored by this slice; HEAD is unmoved at `53ab5ba`. The
Windows pre-commit hook remains the gate.
