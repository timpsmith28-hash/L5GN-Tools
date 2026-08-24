# Cowork brief — a gate check reads the tree, never the machine it happens to be on

> **Draft status:** written 2026-08-24, from a live diagnosis rather than from
> memory — every code claim below was read out of the tree at the time of
> writing and is cited with file and line. The tree has not been built against
> since. Re-verify the line numbers as the round's first act anyway; the
> `relative_to` inventory in Task 1 is the part most likely to have moved.
>
> **Widened the same day** to cover all three gate failures rather than two.
> The auditor split was originally scoped out because it was blocked on `role`
> being unable to express authorship; `authors` landed that afternoon and
> removed the block. Folding it in is not scope creep — it is what makes the
> deliverable a whole sentence, and it removes a carve-out the acceptance
> checks would otherwise have had to carry.

**Origin:** the work task force's `TOOLKIT_notes_2026-08-23` §1.1/§1.1a, §1.2
and §1.3 — **all three** failures in a `verify.py` run on a clean checkout at
`25f1120` on host `10280L`. The complaint offered each as a shape, not a
patch, and explicitly asked that §1.2 be treated as a class rather than fixed
at the one site. Diagnosis on this side found §1.2 and §1.3 to be **code
defects, not test defects** — a different round from the one the complaint
anticipated.

**Precondition:** **0053** ratified, including the clause 2 reword of
2026-08-24 (split by a committed per-host declaration, not by role). This
round is the application of that entry, and building the application of a
`proposed` ruling is the thing 0033 exists to stop.

**Depends on — this repo's rulings:** **0053** (the gate emits verdicts only;
a check that can go red without a defect on the host it runs on does not
belong in it; clause 4 — a check that cannot make the distinction degrades to
a named clean state and says which one it took), **0031** (a non-gating check
surface reports findings and never issues a verdict — the *witness* category,
which never gates), **0045 clause 2** (verification reports and never repairs
— untouched here, and 0053 clause 6 says so explicitly), **0042 clause 5**
(containment runs through the existing `resolve_contained` against a new
anchor set, never a second implementation), **0037 clause 4** (where there is
no measurement, say so and offer no estimate — the discipline
`conductor_panel` already applies to its `governor` field and fails to apply
to its ledger read).

**Ratify before code:** nothing new. All three fixes fall inside 0053 as
reworded. If 0053 is refused or further reworded at ratification, this brief
is rewritten rather than built.

**Deliverable:** `verify.py` is green on a clean checkout of every configured
host, and each of the three checks fails only for a reason that is a defect
*on the host it fired on*. The round is finished when a clean checkout on
`10280L` is green with nothing carved out — and when the knowledge the gate
gave up has a home rather than being lost.

---

## The thing all three have in common

None of these is a machine difference. All three are checks whose red depends
on the machine they happen to be running on, in a gate whose red is supposed
to mean the tree is defective.

Clause 1's phrasing is the test: a red must mean **this tree is defective on
this host**. A red that means "this host has a long username", or "this host
has a model loaded", or "this host has not been handed the current map" is not
a verdict about the tree at all.

They divide into two kinds, and the division decides the fix:

- **§1.2 and §1.3 are environment readers inside checks that declare
  themselves hermetic.** The fix is to stop reading the environment. Nothing
  is given up, because the check never needed the machine in the first place.
- **§1.1 is a real question that the gate is the wrong channel for.** The map
  on a consumer host genuinely may not be current, and that is worth knowing.
  The gate cannot say it without saying "defective", so it goes — and unless
  something else picks it up, the knowledge is lost. 0053's own consequences
  name that gap and this round is required to close it, not just to open it.

The work rig found all three because it differs from this one in three boring
ways. That is the value of a second host, and it should be said plainly:
**none of these was findable here.**

## Defect A ▸ a resolved path made relative to an unresolved anchor

**What the tree does today.**
`estate_data.resolve_contained` (`chronicler/review/estate_data.py:147`)
returns `Path(os.path.realpath(str(candidate)))` — a **fully resolved** path.
That is correct and load-bearing: `_norm` realpaths both sides, which is what
makes the containment check hold against a symlink pointing out of the estate.

`uat_sidebar.sheet_view` (`chronicler/review/uat_sidebar.py:282-283`) then does:

```python
sheet_rel = sp.relative_to(root).as_posix()
results_rel = rp.relative_to(root).as_posix()
```

`sp` and `rp` came through `resolve_contained` and are resolved. `root` is the
caller's argument, untouched. On this rig the two agree, because `timps` needs
no short name. On a host whose profile directory has an 8.3 alias — a username
over eight characters **containing a dot**, which `tim.smith` is — `%TEMP%`
hands the test `C:\Users\TIM~1.SMI\...`, `realpath` hands the code
`C:\Users\tim.smith\...`, and `relative_to` has two paths with different
prefixes.

`tester_uat_sidebar` (`tests/tester_uat_sidebar.py:47-48, 81`) builds its
expectation from the same unresolved `root`, so it is a second instance of the
defect rather than an independent check of it.

**Why this is the code's defect and not the test's.** The rule the code is
missing is not "tests should resolve their temp dirs". It is that
`resolve_contained` deliberately hands back a *normalised* path, and a caller
that then measures it against a *raw* anchor has silently mixed two coordinate
systems. Fixing the test would leave every other caller exposed and would leave
the next one to be written exposed too.

**Known sites, as of drafting.** Eighteen `relative_to(` calls across
`chronicler/`, `l5gntools/` and `auditors/`. Not all are exposed — many
relativise against a module-level root that was itself resolved at import
(`auditor_doc_claims.py:189`, `auditor_uat_stamp.py:128`), and
`config.scope_for_path` (`l5gntools/config.py:277`) resolves both sides
already, which is the pattern the rest should match. The exposed set is
specifically **a resolved left-hand side against a caller-supplied anchor**,
and enumerating it is Task 1, not this paragraph.

## Defect B ▸ a "hermetic" check that reads the real machine's ledger

**What the tree does today.** `conductor_panel.preconditions`
(`chronicler/review/conductor_panel.py:46-54`):

```python
pf = ctl.preflight(curator, endpoint=endpoint or ctl.DEFAULT_ENDPOINT)
entries = led.load_entries()
return {**pf, "calibration_available": bool(entries)}
```

`led.load_entries()` with no argument resolves to `DEFAULT_LEDGER_PATH`
(`chronicler/pipeline/ledger.py:137-140`) — **the real machine's ledger**.
`preconditions` has no `ledger_path` parameter at all.

Its sibling in the same module does. `calibration_state`
(`conductor_panel.py:61`) takes `ledger_path` and threads it through. So the
module already knows the right shape and one of its two functions does not use
it. That asymmetry is the defect, stated more precisely than "the test asserts
the environment".

`tester_conductor_panel` (`tests/tester_conductor_panel.py:1-8`) opens by
declaring itself *"Hermetic. Every ledger/lock path is a temp file… never the
real machine's LM Studio or `data/knowledge_curator/`."* Line 31 then asserts
`calibration_available is False`. It cannot hold that guarantee, because the
function it calls offers no way to.

**A correction to the complaint, to be carried back.** §1.3 attributes the
failure to LM Studio being reachable on `localhost:1234`. Reachability lands in
`pf["lm_studio"]`, which the test never asserts on; the assertion that fails is
`calibration_available`, and that is a ledger read. The operator's conclusion —
*the test is asserting the environment, not the code* — is right, and the
mechanism named is not. Worth sending back because §1.3's stated remedy
("stub the panel's reachability probe") would not have fixed it.

The endpoint probe is a real second exposure and is in scope: `preflight` is
called with a live endpoint from a test that says it never touches the real
machine's LM Studio.

## Defect C ▸ the gate reports a state that is normal on the host it fired on

**What the tree does today.** `auditors/auditor_conversation_map_pin.py`
declares `CLEAN_STATES = {"matches", "artefact-absent", "absent",
"git-unavailable"}` and fails on everything else. `l5gntools/pin.py`'s
`verify_pin` returns `mismatch` whenever the artefact's hash differs from the
pin, and it is right to: it has no way to know why, and 0045 clause 2 says
report and do not repair, which it does.

The auditor's docstring reasons carefully about `artefact-absent` — a machine
never handed a copy is *"the documented normal state, not a defect"* — and
stops one step short. A machine handed a copy **and not handed the current
one** is the same normal state, and per §1.1a it is where a consumer machine
spends most of its life: the map is untracked and arrives by hand, the pin is
tracked and arrives by `git pull`, so the pin routinely runs ahead.

**The split is exactly one state wide, and that is worth stating as a
constraint rather than discovering.** Of the four failing states, only
`mismatch` is host-dependent:

| state | on the authoring host | on a host holding a copy |
|---|---|---|
| `mismatch` | a defect — the artefact drifted under its pin | **not a defect** — the pin is ahead of a hand-carried copy |
| `unpinned` | a defect (0040 clause 4 requires a pin) | a defect — the pin is tracked and should have arrived |
| `pin-malformed` | a defect | a defect — a malformed file is malformed anywhere |
| `anchor-unresolvable` | a defect (0045 clause 3) | a defect — the anchor is a commit in this repo |

A fix that splits more than `mismatch` has evicted coverage that was doing its
job, which is the eviction 0053's third consequence warns will feel like a
loss and this time actually would be one.

**Where the split lives matters.** Not in `pin.py`: `verify_pin` is the
mechanism, it is host-agnostic, and `tester_pin` proves it that way. The split
belongs in the **auditor**, which is the thing that gates. Keeping `pin.STATES`
unchanged also keeps `tester_conversation_map_pin`'s closing sanity check
meaningful — it asserts every declared state is classified, and a new state
added here would weaken it.

**Clause 4's announcement has nowhere to go, today.** An auditor returns
`list[str]`, and `verify.py` treats any non-empty list as failure and prints
`[ OK ]` on an empty one. There is no channel for "clean, and here is the
state I took". No auditor in the tree prints. So this round establishes a
small precedent, and it should be taken deliberately: **the auditor prints one
line before returning clean.** A silent skip is indistinguishable from a pass,
which is the failure clause 4 exists to refuse.

**And the knowledge needs a home, or the round is a net loss.** 0053's first
consequence says it plainly: after the split a consumer host will not be told
its map is stale, and *"unless a witness (0031) or a declared feed (0050)
picks it up, it is lost."* `tests/witness/` already exists, is deliberately
absent from `verify.py`, and its `schema.py` is stdlib-only with an outcome
vocabulary — `matched` / `diverged` / `error` — that has no word for "passed"
on purpose. A pin witness needs no server and no browser, so it uses
`schema.py` and never `harness.py`.

## Working rules

- **One implementation, per 0042 clause 5.** Whatever Defect A's fix is, there
  is one of it. A second normaliser beside `_norm` is the outcome this round
  most needs to avoid.
- **Report, never repair, is untouched** (0045 clause 2, restated by 0053
  clause 6). Nothing here changes what a check does with what it finds.
- **A fix that makes a test pass without changing what the code guarantees is
  not a fix.** Both defects are currently *visible* as failing assertions; the
  cheap version of this round makes them invisible instead.
- **Never run plain git against a mounted Windows repo from a sandbox.** This
  round touches the gate, so it will be tempting to run `verify.py` from
  wherever is convenient.

## Task 1 ▸ enumerate the class, before fixing anything

Produce a committed inventory: every site that relativises, compares or
prefixes one path against another, with three columns — **is the left side
resolved, is the right side resolved, and is the anchor caller-supplied**. Not
a grep dump; a table with a verdict per row.

Land it at `docs/investigation/2026-08-<dd>_path_anchoring_inventory.md`.

Rows that need no change say so and say why, because the value of this table is
as much in the safe rows as the unsafe ones — the next person to add a
`relative_to` should be able to read it and know which pattern they are copying.

**Stop condition:** if the inventory finds only the one known site, stop and
say so rather than generalising a single case into a helper. A class of one is
a bug, and the fix is a line.

## Task 2 ▸ the house rule, as one mechanism

From Task 1's table, land the fix as a single named thing in
`chronicler/review/estate_data.py`, beside `resolve_contained` and documented
as its partner: **a path that came out of `resolve_contained` may only be
relativised against an anchor that went through the same normalisation.**

The shape is the round's to choose, and Task 1 decides it. Two candidates, both
acceptable:

- `resolve_contained` returns the resolved anchor alongside the resolved
  candidate, so a caller cannot hold one without the other; or
- a `relative_to_anchor(resolved, anchor)` helper that normalises the anchor
  the same way and raises the same `DocumentRefused` vocabulary on a miss.

What is **not** acceptable: each call site resolving its own anchor inline.
That is eighteen chances to get it wrong instead of one, and it is how `_norm`
came to exist in the first place.

Update every exposed site the inventory named. `uat_sidebar.py:282-283` is one
of them, not the point of the task.

## Task 3 ▸ `preconditions` takes a ledger path, and an endpoint it can stub

Give `preconditions` a `ledger_path` parameter, threaded to `load_entries`,
matching `calibration_state`'s existing signature exactly rather than inventing
a second convention. Make the endpoint probe injectable by the same standard
`pin.verify_pin`'s `commit_exists` already sets — a resolver the caller may
supply, with the real one as the default.

The test then becomes hermetic in fact rather than in its docstring, and the
docstring's claim becomes checkable.

## Task 4 ▸ make the two testers prove what they claim

- `tester_uat_sidebar`: assert against a resolved root, and add a case that
  passes an anchor which is *not* resolved and proves the code copes — the
  regression the class fix exists for. Keep the existing `os.name == "nt"`
  case-mismatch guard; it tests a different property.
- `tester_conductor_panel`: pass a temp `ledger_path` and a stub probe, and
  keep the `calibration_available is False` assertion — it is a real property
  of an empty ledger and should stay asserted, now truthfully.
- Add, to whichever tester is the better home, a check that a check declaring
  itself hermetic touches no path outside its temp dir. If that turns out to be
  awkward to write, say so in the report; it is the kind of guarantee that is
  easy to claim and hard to hold, and finding that out is worth the attempt.

## Task 5 ▸ the auditor splits on authorship, and says so

`auditors/auditor_conversation_map_pin.py`:

- `check()` gains an injected `authored` argument, in the same shape as its
  existing `commit_exists` resolver — a value a tester supplies directly, so
  the split is provable without touching config or the real host.
- `run()` resolves it once, through `config.authors_artefact(
  "config/mcf_conversation_map.tsv")`. Through `config.machine()`, per 0053
  clause 2; never a flag, an environment variable or an argument to
  `verify.py`.
- **Only `mismatch` splits.** With `authored=False` a `mismatch` returns no
  findings; every other failing state fails exactly as it does today. The
  table in Defect C is the specification.
- On taking the degraded path, `run()` **prints one line** naming the state,
  the artefact, the host, and the host that does author it — then returns
  clean. The line reads as a finding about the copy, not as an apology for
  skipping.
- `pin.py` is not touched. `pin.STATES` does not grow.

The degraded state is named `not-authored-here` rather than something like
`pin-ahead-of-copy`, deliberately: the auditor cannot prove the pin is ahead.
It knows only that this host does not author the artefact, so a mismatch is
not a verdict it is entitled to issue. Naming the state after what is actually
known, rather than after what is probably true, is the same discipline 0037
clause 4 applies to estimates.

## Task 6 ▸ the witness picks up what the gate put down

`tests/witness/witness_map_pin.py`, registered in `run_witness.SUITES` as
`map_pin`, writing `data/witness/map_pin.json`.

- Imports `tests.witness.schema`, `l5gntools.pin` and `l5gntools.config`.
  **Never `harness.py`** — that module imports `uvicorn`, this witness needs
  no server, and the package's own docstring makes the gate's freedom from
  that dependency a rule rather than a preference.
- One `Observation` per pinned artefact: `matched` where the hash matches,
  `diverged` where it does not (detail naming both hashes and the authoring
  host), `error` where the pin or artefact could not be read at all — which is
  distinct from `diverged`, because a witness that cannot run is not evidence
  the copy is stale.
- Runs on any host, including the authoring one. A witness that only runs
  where the gate is silent is a witness nobody ever sees working.

**Stop condition:** if the witness cannot be written without importing
`harness.py`, stop. That import is the one thing the witness package's
docstring forbids by name, and routing around it would put `uvicorn` one
import from the gate.

## Explicitly out of scope

- **Anything else 0053 clause 1 would evict from the gate.** The audit of every
  existing check against clause 1 is real work and is a separate round; doing
  it here would turn a three-defect fix into an estate sweep.
- **Wiring the witness into anything that runs it on a schedule.** It is a
  suite invoked by hand, as `witness_uat_sidebar` already is. What schedules a
  witness is 0031's question and not this round's.
- **A declared staleness feed for the map** (0050). A feed is the other half of
  0053's "witness or feed" sentence and is the better long-run answer; it is
  `COWORK_BRIEF_staleness_feeds.md`'s round, and this brief must not jump ahead
  of it.
- **`config.machine()`'s unmatched-host behaviour**, `run.py pin bump`'s
  authorship refusal, and `config/README.md` — landed 2026-08-24, before this
  brief, and not to be re-opened inside it.
- Touching `_norm`, `path_within_roots` or the containment semantics.
  Containment is *correct*; it realpaths both sides. Only the callers that
  measure against it are wrong, and a round that "improves" containment while
  fixing its callers is a round that broke containment.
- The 8.3 short-name behaviour as a general Windows concern — filenames,
  display, config values. This is about anchoring only.

## Stop conditions

- A second path-normalisation implementation appears anywhere → **stop**
  (0042 clause 5).
- The fix lands as per-call-site inline resolution rather than one mechanism →
  stop.
- Containment behaviour changes in any observable way → stop; that is not
  this round.
- A test is made to pass by weakening its assertion rather than by fixing what
  it asserts against → stop. Deleting the `calibration_available` assertion
  would close this round and lose the property.
- Task 1's inventory is not committed before Task 2 begins → stop.
- The round grows a fourth defect → stop, and brief it separately.
- The auditor split touches any state other than `mismatch` → stop; that is
  evicting coverage that was doing its job.
- `pin.py` gains a state, or the split lands inside `verify_pin` → stop. The
  mechanism is host-agnostic and `tester_pin` depends on it staying so.
- The witness imports `harness.py`, or anything in `verify.py`'s lists gains a
  path into `tests/witness/` → stop.
- The auditor's degraded path returns clean without printing → stop. A silent
  skip is the failure clause 4 exists to refuse, and it is the easiest half of
  Task 5 to drop.
- Task 6 is deferred "until the split is proven" → stop. The split without the
  witness is a net loss of coverage, and a deferral here is how 0053's first
  consequence becomes permanent.

## UAT — acceptance checks

Ids match `docs/UAT_hermetic_gate.md` one for one; that sheet is this section
extracted so it can be walked and stamped.

**A · The gate is green where it was red**

- `[G]` **A1** `tester_uat_sidebar` and `tester_conductor_panel` pass on a host
  whose username is over eight characters and contains a dot, with LM Studio
  reachable on `localhost:1234`. Both conditions present in the same run.
- `[G]` **A2** `verify.py` is green on a clean checkout of that host, **with
  nothing carved out**. No expected reds.

**B · Defect A — anchoring**

- `[G]` **B1** Passing an unresolved anchor to `sheet_view` returns the same
  `sheet_rel` as passing the resolved one.
- `[G]` **B2** Exactly one path-normalisation mechanism exists in
  `chronicler/review/`: `realpath` and `normcase` appear only in `_norm` and
  its documented partner.
- `[G]` **B3** No call site resolves its own anchor inline.
- `[G]` **B4** Containment behaviour is unchanged; a symlink out of the estate
  is still refused.

**C · Defect B — the hermetic claim**

- `[G]` **C1** `preconditions(curator, ledger_path=<temp>)` reports
  `calibration_available` from the temp ledger and `False` for an empty one.
  The `is False` assertion still stands in the tester.
- `[G]` **C2** `preconditions` accepts an injected probe and makes no network
  call when one is supplied.
- `[G]` **C3** Its `ledger_path` signature matches `calibration_state`'s
  convention rather than introducing a second one.
- `[G]` **C4** No file outside the temp directory is read during
  `tester_conductor_panel`.

**D · Defect C — the auditor splits on authorship**

- `[G]` **D1** On a host that does not author the map, a mismatching pin
  returns no finding and prints one line naming `not-authored-here`, the
  artefact, this host and the authoring host.
- `[G]` **D2** On the authoring rig the same mismatch still fails, with both
  hashes named as it does today.
- `[G]` **D3** With `authored=False`, `unpinned`, `pin-malformed` and
  `anchor-unresolvable` all still fail. The split is one state wide and this
  is what proves it.
- `[G]` **D4** `pin.STATES` is unchanged and `tester_pin` passes untouched.
- `[H]` **D5 — read the degraded line as if you had not written it.** Does it
  tell you your copy might be stale and what to do, or does it read as the gate
  apologising for not checking? It replaces a red; if it is easy to skim past,
  the coverage really was lost and the witness is carrying all of it.

**E · The witness picks up what the gate put down**

- `[G]` **E1** `python -m tests.witness.run_witness map_pin` writes
  `data/witness/map_pin.json` on both hosts.
- `[G]` **E2** It carries `matched` on the authoring rig and `diverged` on a
  host whose copy is behind, both hashes in the detail; an unreadable pin or
  artefact reads `error`, never `diverged`.
- `[G]` **E3** Nothing under `tests/witness/` is named in `verify.py`'s
  `AUDITORS` or `TESTERS`, and no module either list names imports it,
  directly or transitively.
- `[G]` **E4** `witness_map_pin.py` does not import `harness.py`.
- `[H]` **E5 — a month from now, will you have looked at
  `data/witness/map_pin.json` even once?** Record the prediction at walk time
  and again when this round's report is re-read.

**F · The inventory**

- `[G]` **F1** Task 1's inventory is committed, every row carries a verdict,
  and every row marked exposed is either fixed or carries a stated reason it
  was left.
- `[H]` **F2 — read the inventory cold.** If you were adding a new
  `relative_to` tomorrow, would this table tell you which pattern to copy? If
  it only catalogues, it did the smaller half of its job.
- `[H]` **F3 — did the class turn out to be a class?** Record the count of
  exposed sites found against the one the complaint named. If Task 1 found one
  and the round still built a helper, say so plainly: that is over-fitting a
  single complaint, and worth recording as a miss even though the code works.

**G · The reply**

- `[G]` **G1** The report carries the correction to `TOOLKIT_notes_2026-08-23`
  §1.3 — the failing assertion is a ledger read, not a reachability probe, and
  the remedy §1.3 proposed would not have fixed it.

Four `[H]`s, and the count is deliberate rather than residual. F2 and F3 cannot
be mechanised — whether a document teaches, and whether a round over-fitted a
single complaint, are both judgements. D5 asks about the *experience* of the
replacement rather than its behaviour, which is the shape that earns an `[H]`.
E5 is a prediction recorded before the answer is known, which is the only way
that particular failure gets caught at all.

## Reporting

`docs/COWORK_REPORT_hermetic_gate.md`, walk-sheet `docs/UAT_hermetic_gate.md`,
stamped results.

Record, specifically:

- Task 1's table in full, including the rows that needed nothing.
- Which of the two Task 2 shapes was taken and what decided it.
- The count of exposed sites found versus the one the complaint named — the
  number that says whether "treat it as a class" was right.
- **The auditor-prints precedent, named as a precedent.** No auditor printed
  before this round. Record that it now does, why the return-value contract
  had no room for clause 4's announcement, and what would justify changing the
  contract properly rather than leaving one auditor different from eleven.
- **What the gate stopped covering, stated as a loss and not as a tidy-up.**
  0053's first consequence asks for the gap between the split and its
  replacement to be measured rather than assumed brief. This round closes it
  in the same sitting, so the number should be zero — say so explicitly, since
  a zero nobody wrote down reads later as a gap nobody looked for.
- **A note to send back to the work side**, correcting §1.3's attribution: the
  failing assertion is a ledger read, not a reachability probe, and the remedy
  §1.3 proposed would not have fixed it. That correction is the useful reply,
  and per the complaint's own terms it is answered by another dated file, not
  by a channel.
