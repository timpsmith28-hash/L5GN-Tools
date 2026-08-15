# UAT walk-sheet — witness fixture (do not walk; witness-only)

This sheet exists only to give `witness_uat_sidebar.py` a fixed, versioned
surface to drive. It is not a real walk-sheet and carries no brief/report
pair on purpose -- the docs board's card-pairing checks are expected to skip
it (it does not match `UAT_<stem>.md` paired with a brief/report; it is under
`tests/witness/fixtures/`, outside `docs/`, so it never appears on the real
board at all).

## A · witness fixture section

- [ ] [W] **W1** Deterministic paste-and-read-back: set a verdict and paste
      multi-line text into the evidence box; the emitted results log must
      carry it verbatim.
- [ ] [W] **W2** Deferred with no reason: emit must refuse, flag this item in
      place, and name the missing reason.
- [ ] [W] **W3** Blocked with no reason: same as W2, for `blocked`.
- [ ] [W] **W4** Already-recorded badge and resume: this item already has an
      entry in `UAT_wsample_results.md`; opening this sheet must show the
      badge and the Resume banner, and Resume must populate this item's
      verdict.
