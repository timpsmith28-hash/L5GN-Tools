> **ARCHIVED** 2026-08-17 · completed pair (brief) · Report:
> `archive/COWORK_REPORT_ui_witness.md` · Walked:
> `archive/UAT_ui_witness_results.md`
> Superseded by nothing — the round completed. Original purpose: commission a
> third check layer that observes rendered UI state deterministically and emits
> findings, never a verdict (DECISIONS 0031).
> Accurate as the request that was made, and what it asked for was built and
> walked — `tests/witness/` and `data/witness/<sheet>.json` are the result. Two
> things it specified have since moved: the `[G]`/`[W]`/`[H]` layer marker it
> introduced is now **rendered** in the UAT sidebar (it was parse-only when this
> round shipped, which the 2026-08-15..17 walk found as a real defect), and the
> docs board's checkbox parser it relied on was corrected in the 2026-08-17
> correctness sweep. Read as the origin of the witness layer, not as a
> description of how the sidebar behaves now.

# Cowork brief — the third check layer: rendered state, deterministically

**Origin:** the 2026-08-03 UAT-sidebar build thread, handed back to the design
thread for the layer split and the naming.
**Deliverable:** a **layer assignment rule**, a walk-sheet template that carries
it, and a scripted suite that asserts what the surface *renders* — outside the
commit gate, with no authority to close anything.
**Relates to:** `investigation/2026-08-02_knight-roles_claude_2-response.md` §4
(the Shadow), 0022 (the run ledger), `docs/README.md` §3 and §6.

The sidebar round produced the observation: *"90% of this testing could be
achieved using Chromium… the deterministic ones at the least."* Correct, and the
build thread's own split is the right one — `tester_uat_sidebar.py` already
covers sheet parsing, stamp computation, refuse-vs-append, staging, and the
board-loop closure via `TestClient` with no browser at all. What is **not**
covered is anything that only exists in the DOM: whether a refusal flags the
right item, whether the resume banner populates, whether pasted multi-line text
survives the textarea round-trip into the emitted file.

**The naming is the smaller half.** A third layer with no assignment rule drifts:
checks migrate to whichever layer is cheapest that week, which is precisely how
the uat stamp's `gate=` was bumped three times in one day by people each doing
the locally-correct thing.

---

## Precondition ▸ **ratified as DECISIONS 0031, 2026-08-03**

The authority question is settled before any code, per the 0024/0025/0027/0028
pattern. Read the entry in full; the three clauses that constrain every task
below are:

1. a witness asserts **rendered or observed state** against an expected state;
2. it emits **findings, never a verdict** — it cannot mark a UAT item passed, and
   nothing it produces closes a pair;
3. it **never gates a commit.** The Windows pre-commit hook remains the only
   authority that says green.

A witness failure means *"the surface did not render what the code claims"* — not
*"the code is broken"* (`verify.py`'s job) and not *"this isn't what I wanted"*
(the walk-sheet's job).

The name is settled: **witness**. `docs/README.md` §3 already calls a results log
*testimony*, and a witness reports what it saw and rules on nothing.

---

## Task 1 ▸ the assignment rule, and measure what it says about today

**The rule, mechanical, applied to any check:**

| question | layer |
|---|---|
| Assertable **without a running surface**? | **gate** — `tester_*` / `auditor_*` |
| Needs a **rendered surface**, deterministic expected state? | **witness** |
| Needs a human to say *"yes, that's what I wanted"*? | **walk-sheet** |

Then **retro-classify every item on every live walk-sheet** and report the
counts. That number is the deliverable of this task: it says how much of the
human queue was never human work. Expect it to be large — `UAT_local_deck_docs_and_time.md`
alone carries 43 items and B7 is *"search `zzqqxx`, confirm a clean empty
state"*.

**Do not re-file anything yet.** Measure first; the findings are the deliverable.

## Task 2 ▸ the template carries the layer, and misfiling becomes a finding

Every walk-sheet item gains a marker:

```
- [ ] [G] **B7.** Search something certainly absent (`zzqqxx`) ...
- [ ] [W] **B4.** A knowledge hit has a green left edge and sorts ahead ...
- [ ] [H] **B2.** Does it surface the *right* document? Judge this honestly ...
```

**The load-bearing property: a `[G]` item on a walk-sheet is itself a finding.**
It means a test that should exist doesn't, and the sheet reports it every time it
is walked rather than someone noticing once. That is what makes the UAT stack
shrink structurally instead of by discipline.

State in the report whether the board and the sidebar should surface the marker
counts per card — a card reading *"12 items, 9 of them [G]"* is a queue that
mostly shouldn't exist.

## Task 3 ▸ the harness — fixtures, not the live estate

Build the witness runner. Constraints, each with a reason:

- **Playwright**, reusing the existing `[scrape]` optional extra — do not add a
  second browser driver. If it wants its own extra, `[witness]`, say why.
- **Never imported by `verify.py`, never on the stdlib-core path.** The gate must
  stay installable and fast on a bare producer.
- **Against a fixture surface, never the operator's live estate.** A fixture
  `estate.json`, a fixture `docs/` tree, a fixture vault. This is the single most
  important constraint in the brief: a suite whose expected state changes when
  you add a document is flaky by construction, and a flaky suite is ignored
  within a fortnight — at which point the third layer asserts nothing and
  everything is still walked by hand.
- **Asserts structure and state, never semantics.** *"The refusal flagged item
  3.2 and rendered a message"* is a witness check. *"The message was helpful"* is
  not, and a witness that starts grading prose has become the
  sidebar-that-grades-itself failure the sidebar brief rules out.

## Task 4 ▸ first suite: the sidebar's own DOM half

Port the checks the build thread named as browser-only, and no others:

- refusal flags the correct `.uat-item` and shows a message (B3, B4)
- the "already recorded" badge renders on the right items (B6)
- the resume banner exists and populates correctly (B7)
- pasted multi-line text survives the textarea round-trip into the emitted file
  (B1's UI half — the backend half is already tester-covered)

**Explicitly not B2.** A judgement item recorded as prose with no computed pass
is the one thing this layer must never touch.

Report which of those the witness closed, and re-run the sidebar's own sheet
afterwards to show the human queue shrinking — that is the acceptance argument
for the whole layer.

## Task 5 ▸ where it runs, and who starts it

The witness is **Shadow-class but not necessarily Shadow-located**: same posture
(deterministic, no judgement, non-gating, findings-only) but it needs a surface
running with data, and the knight's docs board currently renders zero documents
(a config gap, `investigation/2026-08-02_knight-session_claude_2-response.md`
§N10).

Recommend: **the Shadow schedules the witness; the witness runs where a surface
can run.** Say in the report whether that holds, and where its findings land —
0022's run ledger is the obvious home and *"this was checked"* is the same
provenance instinct as *"this ran"*.

## Task 6 ▸ the results log — a citation, never a second stamp

The sidebar already emits `docs/UAT_<x>_results.md`. This task feeds it witness
observations **without breaking 0031 clause 2**, and the shape matters more than
the wiring.

### Where the output lives, and why it is not a document

The witness writes **`data/witness/<sheet>.json`**. Not `docs/`.

`docs/README.md` §1: *a document earns its place by holding something that can't
be derived.* Witness output is deterministic by construction — same commit, same
fixture, same answer, forever. It is therefore **derivable**, in the same
category as status, and does not earn a place in `docs/`. `data/` is already
gitignored and already the sanctioned home for scanner-shaped output.

**Shape it like a 0022 ledger row from the start.** The run ledger is the right
long-term home — *"this was checked"* and *"this ran"* are the same provenance
instinct — but 0022 is unbuilt and blocking this round behind it is not worth
it. Design the record so the migration is a move, not a rewrite: one row per
run, append-only in spirit, carrying `ran_at`, `host`, `commit`, `fixture`, the
sheet id, and the per-item observations.

### The schema has no word for "passed"

Per-item outcome is **`matched` / `diverged` / `error`**. Not pass/fail.

This is not decoration. A data shape that cannot express a pass cannot be used to
rubber-stamp one, which makes clause 2 structural rather than a convention
someone has to remember. Any field named `passed`, `ok` or `result` is a defect
in this task.

### The results log gains a citation, not a stamp

**A stamp asserts the provenance of *this document*. A citation points at a run
that happened elsewhere.** `auditor_uat_stamp` polices the former and must not
have to learn about the latter — so this needs **no auditor change**, and that is
the point of choosing a citation.

Put it as a **visible line in the body**, under the machine-verified section —
**not** an HTML comment. A comment beside the uat stamp will eventually be read
as a second stamp by a person or an auditor, and the two mean different things.
Visible prose cannot be mistaken for provenance metadata.

It must carry enough to **re-derive** the result, not the result itself:
the artefact path, the fixture identity, the commit, and when it ran.

### The log splits by layer

- **Machine-verified** — `[G]` and `[W]` items, with the citation above them and
  each item's observation inline. **No human verdict field.** If a check is
  deterministic enough for the witness to observe, it was never Tim's to rule on;
  pre-filling a verdict for him to tick is how an acceptance claim becomes
  nominal.
- **Human ruling** — `[H]` items only. This section is exactly as long as his
  judgement is required and not one line longer. That shortening is the round's
  acceptance argument.

### The sidebar stays the only writer

The witness is a **data source the sidebar reads**, never a co-author writing
into the same file. That is 0007's single-writer-by-column-scope applied to a
document instead of a table: there is never a question of which process wrote
which line.

**If the witness artefact is missing or stale relative to the current commit, say
so in the log and emit anyway.** A results log that silently omits the machine
section reads identical to one where everything passed. Honest absence, per house
style — this is failure shape #1 and it applies to us as much as to a scanner.

---

## Explicitly out of scope

- Computing whether a UAT item **passed**. Ever. See the drafted entry, clause 2.
- Gating commits on witness results.
- Re-filing existing walk-sheet items. Task 1 measures; a later round moves.
- The Shadow itself, the Historian, mutation testing, fault injection — all
  separately briefed or unbriefed.
- Any assertion about content quality, wording, or aesthetics.

## Stop conditions

- **The suite runs against the live estate** → stop. Determinism is the whole
  premise; without it this layer is worse than not having it.
- **A witness result is used to tick a walk-sheet item** → stop. That is the
  drafted entry's clause 2, violated on day one.
- **`verify.py` grows a browser dependency** → stop, however indirect.
- **The layer rule cannot place an existing check** → stop and report. A rule
  with an unplaceable case is a rule that will be applied by taste.
- **The witness JSON gains a field expressing a pass** (`passed`, `ok`,
  `result`) → stop. Clause 2 is meant to be unavailable, not merely forbidden.
- **Witness output is written into `docs/`**, or the citation is emitted as an
  HTML comment alongside the uat stamp → stop; both re-create the second-stamp
  problem this task exists to avoid.
- **A missing witness artefact produces a results log that looks complete** →
  stop. That is a confident zero in our own tooling.

---

## UAT — acceptance checks (Tim walks these)

- The assignment rule places every item on two existing sheets without argument,
  and the counts are reported.
- A walk-sheet renders its markers, and a deliberately mis-marked `[G]` item
  **shows up as a finding** rather than sitting quietly.
- The witness suite runs green against the fixture, twice, with identical output.
- **Break the UI deliberately** — remove the refusal's message element — and
  confirm the witness fails, names the element, and does **not** claim the code
  is broken.
- `verify.py` is GREEN and unchanged in runtime; no browser import reaches it.
- A witness result **cannot** be used to close a UAT item — verify by trying.
- The sidebar's own sheet is measurably shorter for a human after Task 4.
- **The emitted results log splits by layer.** The machine section carries the
  citation and the observations; the human section contains only `[H]` items and
  is visibly shorter than the sheet it came from.
- **The citation re-derives.** Follow it to `data/witness/<sheet>.json`, re-run
  the witness at the named commit against the named fixture, and get the same
  observations.
- **The citation is a visible line, not a comment**, and `auditor_uat_stamp` is
  unchanged and green.
- **Delete the witness artefact and emit again.** The log must say the machine
  section is absent and why — not quietly omit it.
- `data/witness/` contains no file that claims anything passed.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_ui_witness.md`, walk-sheet `docs/UAT_ui_witness.md`, stamped
results after the walk.

Record the ratification and the final name, the Task 1 retro-classification
counts in full, the fixture design, which sidebar items moved out of the human
queue, and the Task 5 ruling on where findings land.

Once this lands, an acknowledgement line belongs on
`investigation/2026-08-02_knight-roles_claude_2-response.md` — the Shadow section
predicted a non-gating deterministic layer and this is its first instance.
