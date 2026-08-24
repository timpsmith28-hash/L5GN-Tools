# Cowork brief — a gate check reads the tree, never the machine it happens to be on

> **Draft status:** written 2026-08-24, from a live diagnosis rather than from
> memory — every code claim below was read out of the tree at the time of
> writing and is cited with file and line. The tree has not been built against
> since. Re-verify the line numbers as the round's first act anyway; the
> `relative_to` inventory in Task 1 is the part most likely to have moved.

**Origin:** the work task force's `TOOLKIT_notes_2026-08-23` §1.2 and §1.3, two
of the three failures in a `verify.py` run on a clean checkout at `25f1120` on
host `10280L`. The complaint offered both as shapes, not patches, and
explicitly asked that §1.2 be treated as a class rather than fixed at the one
site. Diagnosis on this side found both to be **code defects, not test
defects** — which is a different round from the one the complaint anticipated.

**Precondition:** **0053** ratified. This round applies its clause 1 (the gate
emits verdicts only) to two specific checks, and building the application of a
`proposed` ruling is the thing 0033 exists to stop.

**Depends on — this repo's rulings:** **0053** (the gate emits verdicts only; a
check that can go red without a defect on the host it runs on does not belong
in it), **0031** (a non-gating check surface reports findings and never issues
a verdict — the *witness* category), **0042 clause 5** (containment runs
through the existing `resolve_contained` against a new anchor set, never a
second implementation), **0037 clause 4** (where there is no measurement, say
so and offer no estimate — the discipline `conductor_panel` already applies to
its `governor` field and fails to apply to its ledger read).

**Ratify before code:** nothing new. Both fixes fall inside 0053 as drafted.
If 0053 is refused or materially reworded at ratification, this brief is
rewritten rather than built.

**Deliverable:** `verify.py` passes on a clean checkout of any configured host,
whatever that host's username length and whatever is running on it. The round
is finished when `tester_uat_sidebar` and `tester_conductor_panel` both pass on
a machine with a dotted, over-eight-character username and a reachable LM
Studio — and when neither passes for a reason that would change if that machine
were reconfigured.

---

## The thing both defects have in common

Neither of these is a machine difference. Both are code that consults the
machine it happens to be running on, inside a check that declares it does not.

That is the converse of what 0053 ruled. 0053 evicted a *finding-producer* from
the gate. This round evicts two *environment readers* from checks that claim to
be hermetic — and the reason it is the same ruling is clause 1's phrasing: a
red must mean **this tree is defective on this host**. A red that means "this
host has a long username" or "this host has a model loaded" is not a verdict
about the tree at all.

The work rig found both because it differs from this one in two boring ways.
That is the value of a second host and it should be said plainly: neither
defect was findable here.

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

## Explicitly out of scope

- **The `auditor_conversation_map_pin` split by host role.** That is 0053's own
  application and the third of the three failures; it wants its own round, and
  it is the one blocked on the fact that `role` cannot express authorship
  (both rigs are `producer`). Not this brief.
- **Anything else 0053 clause 1 would evict from the gate.** The audit of every
  existing check against clause 1 is real work and is a separate round; doing
  it here would turn a two-defect fix into an estate sweep.
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
- The round grows a third defect → stop, and brief it separately.

## UAT — acceptance checks

- `[G]` `tester_uat_sidebar` and `tester_conductor_panel` pass on a host whose
  username is over eight characters and contains a dot, with LM Studio
  reachable on `localhost:1234`. Both conditions present in the same run.
- `[G]` `verify.py` is green on a clean checkout of that host, except for
  `auditor_conversation_map_pin`, which is out of scope and expected to remain
  red until its own round.
- `[G]` Passing an unresolved anchor to `sheet_view` returns the same
  `sheet_rel` as passing the resolved one. The two calls agree.
- `[G]` `preconditions(curator, ledger_path=<temp>)` reports
  `calibration_available` from the temp ledger, and reports it `False` for an
  empty one, with no file outside the temp dir read.
- `[G]` `preconditions` accepts an injected probe and makes no network call
  when one is supplied.
- `[G]` Exactly one path-normalisation mechanism exists in
  `chronicler/review/`: `grep` for `realpath` and `normcase` returns only
  `_norm` and its documented partner.
- `[G]` Task 1's inventory is committed, every row carries a verdict, and every
  row marked exposed is either fixed or carries a stated reason it was left.
- `[H]` **Read the inventory cold.** If you were adding a new `relative_to`
  tomorrow, would this table tell you which pattern to copy? If it only
  catalogues, it did the smaller half of its job.
- `[H]` **Did the class turn out to be a class?** If Task 1 found one exposed
  site and the round still built a helper, say so plainly in the report. That
  is the round over-fitting a single complaint into a mechanism, and it is
  worth recording as a miss even though the code works.

Two `[H]`s, both deliberate. The first cannot be mechanised — whether a
document teaches is a judgement. The second is the round's own honesty check
and exists because "treat it as a class" was the complaint's instruction, and
an instruction followed past the point where the evidence supports it is a
failure that looks like diligence.

## Reporting

`docs/COWORK_REPORT_hermetic_gate.md`, walk-sheet `docs/UAT_hermetic_gate.md`,
stamped results.

Record, specifically:

- Task 1's table in full, including the rows that needed nothing.
- Which of the two Task 2 shapes was taken and what decided it.
- The count of exposed sites found versus the one the complaint named — the
  number that says whether "treat it as a class" was right.
- **A note to send back to the work side**, correcting §1.3's attribution: the
  failing assertion is a ledger read, not a reachability probe, and the remedy
  §1.3 proposed would not have fixed it. That correction is the useful reply,
  and per the complaint's own terms it is answered by another dated file, not
  by a channel.
