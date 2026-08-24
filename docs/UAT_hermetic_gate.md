# UAT — hermetic gate

Walk-sheet for `docs/COWORK_BRIEF_hermetic_gate.md`. Results land in
`docs/UAT_hermetic_gate_results.md` with the usual stamp.

**This sheet must be walked on a host with a dotted, over-eight-character
username and LM Studio reachable.** Walked on the authoring rig it proves
nothing: neither defect is reproducible here, which is why neither was found
here. If that host is unavailable, record that and do not tick A1 or A2.

`[G]` = a machine or an unambiguous procedure decides.
`[H]` = human judgement genuinely required.

---

## A · The gate is green where it was red

- [ ] **A1** `[G]` `tester_uat_sidebar` and `tester_conductor_panel` both pass
      on a host whose username is over eight characters and contains a dot,
      with LM Studio reachable on `localhost:1234`. Both conditions present in
      the same run — record the hostname and the endpoint's response.
- [ ] **A2** `[G]` `verify.py` is green on a clean checkout of that host, with
      the single exception of `auditor_conversation_map_pin`, which is out of
      scope for this round and expected to stay red until its own. Record the
      full output; any *other* red fails this check.

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
- [ ] **B4** `[G]` Containment behaviour is unchanged: the existing
      containment tests pass untouched, and a symlink pointing out of the
      estate is still refused.

## C · Defect B — the hermetic claim

- [ ] **C1** `[G]` `preconditions(curator, ledger_path=<temp>)` reports
      `calibration_available` from the temp ledger, and reports `False` for an
      empty one. The `calibration_available is False` assertion still stands in
      the tester — deleting it fails this check.
- [ ] **C2** `[G]` `preconditions` accepts an injected probe and makes no
      network call when one is supplied.
- [ ] **C3** `[G]` `preconditions`' signature matches `calibration_state`'s
      convention for `ledger_path` rather than introducing a second one.
- [ ] **C4** `[G]` No file outside the temp directory is read during
      `tester_conductor_panel`. If this proved awkward to assert mechanically,
      tick it as `[H]` instead and say so in the results — that outcome is
      itself a finding the brief asked for.

## D · The inventory

- [ ] **D1** `[G]` `docs/investigation/2026-08-<dd>_path_anchoring_inventory.md`
      is committed, every row carries a verdict, and every row marked exposed
      is either fixed or carries a stated reason it was left.
- [ ] **D2** `[H]` **Read the inventory cold.** If you were adding a new
      `relative_to` tomorrow, would this table tell you which pattern to copy?
      If it only catalogues the unsafe rows, it did the smaller half of its
      job — say so rather than ticking.
- [ ] **D3** `[H]` **Did the class turn out to be a class?** Record the count
      of exposed sites found against the one the complaint named. If Task 1
      found one and the round still built a helper, say so plainly: that is
      the round over-fitting a single complaint, and it is worth recording as
      a miss even though the code works.

## E · The reply

- [ ] **E1** `[G]` The report carries a note correcting `TOOLKIT_notes_2026-08-23`
      §1.3's attribution — the failing assertion is a ledger read, not a
      reachability probe, and the remedy §1.3 proposed would not have fixed it.
      Answered by a dated file, not by a channel.

---

**Stop conditions, restated so they can be noticed mid-walk.** Any of these
ends the walk rather than failing a check: a second normalisation
implementation appears; the fix lands as per-call-site inline resolution;
containment behaviour changes observably; a test is made to pass by weakening
its assertion; Task 1's inventory was not committed before Task 2 began; the
round grew a third defect.
