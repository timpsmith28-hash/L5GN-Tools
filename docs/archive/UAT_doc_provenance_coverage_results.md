<!-- uat: commit=dec7dc5 dirty=true host=gaming-rig walked=2026-07-28 -->
<!-- gate-frozen: commit=dec7dc5 -->

> **ARCHIVED** 2026-08-19 · completed pair (results) · results for `docs/archive/UAT_doc_provenance_coverage.md`
> Superseded by nothing — this is testimony, kept intact · Original purpose: record what the 2026-07-28 walk on the gaming rig, against the personal estate, actually reached.
> Accurate as written. Its "6 auditors, 50 testers" line is a frozen build-time count, already covered by this file's own `gate-frozen` marker; `dirty=true` is the pair's own uncommitted changes, stated in the body. No item was deferred or left unwalked.

# UAT results — document provenance and coverage

Walked against the pair `docs/COWORK_BRIEF_doc_provenance_coverage.md` +
`docs/COWORK_REPORT_doc_provenance_coverage.md`, on the gaming rig (personal
estate), working tree dirty (this pair's own changes, uncommitted).

`python verify.py` ran GREEN: 6 auditors, 50 testers, `tester_doc_census`
present and passing.

---

## A — the personal estate's number becomes honest — **PASS**

Walked from the live `report.html` Docs tab.

- [x] **A1.** Every project row shows authored count with generated noted
      beside it in parentheses — e.g. `17 (341 generated)` for
      Continuous-Ingestion-Daemon, `2 (286 generated)` for Armory_v4.
- [x] **A2.** Continuous-Ingestion-Daemon and Armory_v4 are visibly the two
      heavy generators, not folded into a blended number.
- [x] **A3.** Confirmed on this fresh build: totals across the row (90
      authored, 24 classified) give 26.7%, well above the old blended 5.5%
      figure, and it is the number this build actually produced, not an
      estimate.

## B — no false positives — **not walked this pass**

Tim: "will investigate as we go." Left open.

## C — `_KNOWLEDGE_` matches correctly — **blocked, needs the work rig**

Requires the work estate, not reachable from the gaming rig. Open.

## D — the grid reads as coverage, not a score — **PASS**

- [x] **D1.** Project × document-type matrix, ticks with a count, dashes for
      absence — confirmed in the live Coverage table.
- [x] **D2.** No total column, no rank.
- [x] **D3.** `L5GN_Managed_Workspace` (one README, nothing else) reads as
      exactly what it has, not as failing.
- [x] **D4.** Tim: "D feels to fit for coverage" — confirmed at a glance what
      each project lacks, no implied pass/fail.

## E — the rules are stated in the report — **PASS**

- [x] **E1.** The rule text is printed directly under the Coverage table in
      the live report (knowledge/adr/decisions/readme/etc. rules, and the
      generated-directory rule), visible without reading the brief.

## F — out-of-band document count — **PASS**

- [x] **F1.** Banner names Continuous-Ingestion-Daemon (358), Crystal-Spire
      (97) and Armory_v4 (288) against the estate median (26), threshold 78.
- [x] **F2.** No small project flagged.

## G — the gate — **PASS**

- [x] **G1.** `python verify.py` GREEN, 6 auditors + 50 testers, including
      `tester_doc_census`.
- [x] **G2.** `tester_estate_diff` and the rest of the gate ran clean on the
      new `doc_type`/`provenance` keys — nothing downstream broke.

---

## Report-back items — still open, for Tim to rule on

- [ ] **H1.** Whether Task B's rule would classify `L5GN-Castle`'s payload
      out. Finding stands: it would not (duplicate backup folders don't
      start with `.`/`_` and aren't on the explicit list). 1.A2 still open.
- [ ] **H2.** Whether to capture document mtime for a future staleness
      check. Not built; Tim's call.

---

## Not archivable yet

B and C are outstanding, and both report-back items remain open. This pair
stays live until B/C are walked (C needs the work rig, which Tim is pinging
next) and H1/H2 get a ruling.
