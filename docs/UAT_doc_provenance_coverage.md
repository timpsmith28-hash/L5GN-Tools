# UAT walk-sheet — document provenance and coverage

Pair: `docs/COWORK_BRIEF_doc_provenance_coverage.md` +
`docs/COWORK_REPORT_doc_provenance_coverage.md`.

Gate at build time: `python verify.py` **GREEN** (6 auditors + 50 testers,
including the new `tester_doc_census`).

Every check below is **ready to walk**. None is passed — only Tim walking it
makes it that, and this pair is not archivable until he has.

---

## Before you start

```
cd ~/Documents/GitHub/L5GN-Tools
python verify.py            # expect: verify: GREEN -- all gates passed.
python run.py build --fresh
```

If the gate is red, stop — nothing below is meaningful.

---

## A — the personal estate's number becomes honest

Open `report.html` → **Docs** tab, on the personal-estate machine.

- [ ] **A1.** Each project row shows an **authored** count with the generated
      count noted beside it in parentheses (e.g. "17 (341 generated)" for
      Continuous-Ingestion-Daemon), not one blended number.
- [ ] **A2.** `L5GN-Continuous-Ingestion-Daemon` and `L5GN_Armory_v4` — the two
      projects holding 646 of the 824 documents — are visibly the ones with a
      large generated count, not silently dragging any ratio down.
- [ ] **A3.** The estate-wide authored-only classified percentage is
      **noticeably higher** than the old 5.5% figure (this build measured
      26.7% across the personal estate: 24 classified of 90 authored, 734
      generated). Confirm on a fresh build rather than trusting this number.

---

## B — no false positives

- [ ] **B1.** Pick 5–10 projects at random and scan their authored document
      list in the Docs tab (or `data/doc_census/<project>.json`). Nothing that
      Tim would call a real, hand-written document is marked generated.
- [ ] **B2.** Specifically check `L5GN-Armory_v2`'s `L5GN_Journal/` entries —
      this build found them authored and unclassified (ordinary prose, not a
      gap). Confirm that reads correctly rather than as a miss.
- [ ] **B3.** Same check on the work estate, which this session could not
      reach: confirm no project under `docs/`, `briefs/`, `PoC/` (no leading
      dot or underscore anywhere in the tree) has any document marked
      generated.

---

## C — `_KNOWLEDGE_` matches correctly

- [ ] **C1.** On the work estate, confirm all six known knowledge docs across
      `ActivityStatements`, `ChurnLevelIndictor`, `SolConfig`, `TSsToAssets`
      are typed `knowledge` in the coverage grid.
- [ ] **C2.** Confirm the match is unanchored — a document like
      `LEGACY_BUNDLE_KNOWLEDGE.md` (marker at the very end, not a clean
      suffix boundary) is still caught. (Verified by `tester_doc_census`
      against this exact filename; walk it against a real one if available.)

---

## D — the grid reads as coverage, not a score

Open `report.html` → **Docs** tab → the **Coverage** table underneath the
main project table.

- [ ] **D1.** It is a project × document-type matrix: ticks with a count,
      dashes for absence.
- [ ] **D2.** There is **no total column and no rank** — a project cannot be
      sorted or scored by how many ticks it has.
- [ ] **D3.** A project with one excellent README and nothing else (e.g.
      `L5GN_Managed_Workspace`) does not read as "failing" — it reads as
      exactly what it has.
- [ ] **D4.** Opening the grid, it is obvious at a glance which load-bearing
      types a given project lacks, without any number implying it should have
      them all.

---

## E — the rules are stated in the report

- [ ] **E1.** The Docs tab itself (not just this walk-sheet) states, in
      plain text, what "generated" meant on this build and what each grid
      column's classification rule is. A cold reader — someone who has not
      read the brief — can tell what the grid is answering.

---

## F — out-of-band document count

- [ ] **F1.** On the personal estate, the Docs tab shows a banner naming
      `L5GN-Continuous-Ingestion-Daemon` (358), `L5GN_Armory_v4` (288) and
      `L5GN-Crystal-Spire` (97) as out of band against the estate median (26).
      The banner reads as a scale signal, not a documentation-quality one.
- [ ] **F2.** No small project is flagged.

---

## G — the gate

- [ ] **G1.** `python verify.py` GREEN, `tester_doc_census` present in the
      tester list output.
- [ ] **G2.** `estate_diff` and any other `doc_census` consumer still run
      clean — nothing downstream broke on the new `doc_type`/`provenance`
      keys. (`tester_estate_diff` covers this in the gate; spot-check the
      Docs tab still renders after a `build --fresh` as the practical proof.)

---

## Report-back items — for Tim to rule on, not walk

These were gathered per the brief's instruction, not decided:

- [ ] **H1.** Whether Task B's rule would classify `L5GN-Castle`'s payload
      out. **Finding:** it would not — the suspect duplicate folders
      (`data/Chronicler_Backup/raw_gem_files` mirrors
      `data/chat_threads/raw_gem_files` byte-for-byte, 165,246,539 bytes /
      110 files in both places) don't start with `.` or `_` and aren't on the
      explicit list. See the report's "Report back" section. Ruling on 1.A2
      remains open.
- [ ] **H2.** Whether to capture document mtime for a future staleness check.
      Not built. Put to Tim as the brief instructs.

---

## Closing the pair

When every box above is walked, write `docs/UAT_doc_provenance_coverage_
results.md`. It **must** carry a uat stamp (`docs/README.md` §3) or
`auditor_uat_stamp` fails the gate:

```
<!-- uat: commit=<sha you walked> dirty=<true|false> host=<machine> walked=YYYY-MM-DD -->
```

**No `gate=` field** — the brief asks for the stamp naming the commit only,
not a frozen auditor/tester count.

Record what was walked and what was not, including anything that fails — a
results log naming a failure is worth more than one that quietly omits it.
Only then are the brief, the report and this sheet archivable as a pair.
