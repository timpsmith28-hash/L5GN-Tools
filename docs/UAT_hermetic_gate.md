# UAT — hermetic gate

Walk-sheet for `docs/COWORK_BRIEF_hermetic_gate.md`. Ids match that brief's
acceptance section one for one. Results land in
`docs/UAT_hermetic_gate_results.md` with the usual stamp.

**This sheet must be walked on a host with a dotted, over-eight-character
username, LM Studio reachable, and a conversation map it does not author.**
Walked on the authoring rig alone it proves almost nothing: none of the three
defects is reproducible here, which is why none of them was found here. Where
a check needs the authoring rig instead, it says so. If the consumer host is
unavailable, record that and do not tick A1, A2, D1 or E2.

`[G]` = a machine or an unambiguous procedure decides.
`[H]` = human judgement genuinely required.

---

## A · The gate is green where it was red

- [ ] **A1** `[G]` `tester_uat_sidebar` and `tester_conductor_panel` both pass
      on a host whose username is over eight characters and contains a dot,
      with LM Studio reachable on `localhost:1234`. Both conditions present in
      the same run — record the hostname and the endpoint's response.
- [ ] **A2** `[G]` `verify.py` is green on a clean checkout of that host,
      **with nothing carved out**. Record the full output; any red at all
      fails this check. This sheet carries no expected-red exception — an
      earlier version had one for `auditor_conversation_map_pin`, and the
      round was widened specifically to remove it.

## B · Defect A — anchoring

- [ ] **B1** `[G]` Passing an **unresolved** anchor to `sheet_view` returns the
      same `sheet_rel` as passing the resolved one. Call it both ways in one
      session and compare the two strings.
- [ ] **B2** `[G]` Exactly one path-normalisation mechanism exists in
      `chronicler/review/`: grepping for `realpath` and `normcase` returns
      `_norm` and its documented partner, and nothing else.
- [ ] **B3** `[G]` No call site resolves its own anchor inline. The fix is one
      named thing; eighteen local fixes fail this check even if every test
      passes.
- [ ] **B4** `[G]` Containment behaviour is unchanged: the existing containment
      tests pass untouched, and a symlink pointing out of the estate is still
      refused.

## C · Defect B — the hermetic claim

- [ ] **C1** `[G]` `preconditions(curator, ledger_path=<temp>)` reports
      `calibration_available` from the temp ledger, and `False` for an empty
      one. The `calibration_available is False` assertion still stands in the
      tester — deleting it fails this check.
- [ ] **C2** `[G]` `preconditions` accepts an injected probe and makes no
      network call when one is supplied.
- [ ] **C3** `[G]` Its `ledger_path` signature matches `calibration_state`'s
      convention rather than introducing a second one.
- [ ] **C4** `[G]` No file outside the temp directory is read during
      `tester_conductor_panel`. If this proved awkward to assert mechanically,
      tick it as `[H]` instead and say so in the results — that outcome is
      itself a finding the brief asked for.

## D · Defect C — the auditor splits on authorship

- [ ] **D1** `[G]` On a host that does **not** author the map, a mismatching
      pin returns no finding and `verify.py` prints one line naming
      `not-authored-here`, the artefact, this host, and the host that does
      author it. Paste the line into the results log verbatim.
- [ ] **D2** `[G]` On the **authoring rig** the same mismatch still fails, with
      both hashes named exactly as it does today. Prove it by editing the map,
      running the gate, and restoring the map — do not simulate it.
- [ ] **D3** `[G]` With `authored=False`, the states `unpinned`,
      `pin-malformed` and `anchor-unresolvable` **all still fail**. The split
      is one state wide and this is the check that proves it. Any of the three
      going clean fails the round.
- [ ] **D4** `[G]` `pin.STATES` is unchanged and `tester_pin` passes untouched.
      The split lives in the auditor, never in the mechanism.
- [ ] **D5** `[H]` **Read the degraded line as if you had not written it.**
      Does it tell you your copy might be stale and what to do about it, or
      does it read as the gate apologising for not checking? This line
      replaces a red. If it is easy to skim past, the coverage really was lost
      and the witness is now carrying all of it — say so rather than ticking.

## E · The witness picks up what the gate put down

- [ ] **E1** `[G]` `python -m tests.witness.run_witness map_pin` writes
      `data/witness/map_pin.json` on both hosts.
- [ ] **E2** `[G]` The record carries `matched` on the authoring rig and
      `diverged` on a host whose copy is behind, with both hashes in the
      detail. An unreadable pin or artefact reads `error`, never `diverged`.
- [ ] **E3** `[G]` Nothing under `tests/witness/` is named in `verify.py`'s
      `AUDITORS` or `TESTERS`, and no module either list names imports it —
      directly or transitively. Check the transitive half properly; the
      package's own docstring makes this a rule, and `harness.py` imports
      `uvicorn`.
- [ ] **E4** `[G]` `witness_map_pin.py` does not import `harness.py`.
- [ ] **E5** `[H]` **A month from now, will you have looked at
      `data/witness/map_pin.json` even once?** Record the honest prediction
      now, at walk time, and again when this round's report is re-read. A
      witness nobody reads is the channel 0053's first consequence warned
      about; predicting it is cheaper than discovering it.

## F · The inventory

- [ ] **F1** `[G]` `docs/investigation/2026-08-<dd>_path_anchoring_inventory.md`
      is committed, every row carries a verdict, and every row marked exposed
      is either fixed or carries a stated reason it was left.
- [ ] **F2** `[H]` **Read the inventory cold.** If you were adding a new
      `relative_to` tomorrow, would this table tell you which pattern to copy?
      If it only catalogues the unsafe rows, it did the smaller half of its
      job — say so rather than ticking.
- [ ] **F3** `[H]` **Did the class turn out to be a class?** Record the count
      of exposed sites found against the one the complaint named. If Task 1
      found one and the round still built a helper, say so plainly: that is
      the round over-fitting a single complaint, and it is worth recording as
      a miss even though the code works.

## G · The reply

- [ ] **G1** `[G]` The report carries a note correcting
      `TOOLKIT_notes_2026-08-23` §1.3's attribution — the failing assertion is
      a ledger read, not a reachability probe, and the remedy §1.3 proposed
      would not have fixed it. Answered by a dated file, not by a channel.

---

**Stop conditions, restated so they can be noticed mid-walk.** Any of these
ends the walk rather than failing a check: a second normalisation
implementation appears; the fix lands as per-call-site inline resolution;
containment behaviour changes observably; a test is made to pass by weakening
its assertion; Task 1's inventory was not committed before Task 2 began; the
round grew a fourth defect; the auditor split touches any state other than
`mismatch`; `pin.py` gains a state or the split lands inside `verify_pin`; the
witness imports `harness.py`; the auditor's degraded path returns clean
without printing; Task 6 was deferred "until the split is proven".
