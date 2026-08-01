<!-- gate-frozen: commit=ac7710d -->
<!-- The sheet's claim is explicitly "gate at BUILD TIME", at the commit named
     on the line below it. That is testimony about a moment, not an assertion
     about the live tree, and it stays true as later rounds register testers.
     The sheet itself is still open — this freezes one number, not the walk. -->

# UAT walk-sheet — the local deck, slice 1: documents and time

Pair: `docs/COWORK_BRIEF_local_deck_docs_and_time.md` +
`docs/COWORK_REPORT_local_deck_docs_and_time.md`.

**Built:** 2026-07-29, base commit `ac7710d`, working tree dirty.
**Gate at build time:** `python verify.py` → **GREEN**, 6 auditors + 53 testers
(+2: `tester_estate_data`, `tester_review_preflight`).
**Nothing committed** — walk against the working tree.

Every check below is **ready to walk**. None is passed — only Tim walking it
makes it that, and this pair is not archivable until he has.

Results go in `docs/UAT_local_deck_docs_and_time_results.md` with a `uat` stamp
naming the commit. **Do not write a `gate=` field** — the stamp records the walk,
not the gate.

---

## Before you start

```
cd ~/Documents/GitHub/L5GN-Tools
python verify.py               # expect: verify: GREEN -- all gates passed.
python run.py build            # only if data/estate.json is older than you want
python run.py review --host 127.0.0.1
```

Open `http://127.0.0.1:8002/`. If the gate is red, stop — nothing below is
meaningful.

The startup banner is itself the first evidence. Expect lines naming the estate
build's timestamp and commit, `estate routes ENABLED`, the authored-document
count, and `search engine=fts5`.

---

## A — a knowledge document opens, on the machine that owns it

Go to the **Documents** tab.

- [ ] **A1.** The left nav lists all 9 projects with their **authored** counts.
      `L5GN-Tools` shows ~103; `L5GN_Armory_v4` shows 2 with "288 generated" in
      the sub-line. `L5GN-Armory` shows 0 and is greyed out and unclickable.
- [ ] **A2.** Pick a project with knowledge docs. The groups render with
      **`knowledge` first and in green**, then decisions, adr, intent,
      architecture, brief, report, and so on down to `unclassified`.
- [ ] **A3.** Click a document. It renders as monospace text with headings
      intact, and the header states the project, path, doc_type, the byte count
      **on disk now**, and "read at render time (0027) · not cached".
- [ ] **A4.** **The content matches the file.** Open the same file in an editor
      and compare the first and last few lines. This is the check that matters —
      a viewer that renders *something* is not the same as one that renders
      *the file*.
- [ ] **A5.** Edit that file in your editor, save, and click the document again
      in the deck **without restarting the server**. The change is there. That
      is the render-time read, proven — a cache would show you the old text.
- [ ] **A6.** No generated document is offered anywhere. `L5GN_Armory_v4` shows
      2 documents, not 290. Nothing under `AutoFiles/` appears in any list.

---

## B — search finds something you had forgotten

Go to the **Search** tab. This is the honest test and the reason the slice
exists.

- [ ] **B1.** Search a term you know is in one of the MCF or L5GN knowledge
      documents but cannot remember the location of. The status line reads
      `N result(s) · engine: fts5 · scope: whole estate`.
- [ ] **B2.** **Does it surface the right document?** Judge this honestly. If
      the document you meant is not in the top few results, that is a **finding**
      — write it in the results log with the query and what did come back. A
      ranking that doesn't work is worth knowing about; a ranking nobody checked
      is worth nothing.
- [ ] **B3.** The snippet shows the match highlighted in context, and the hit
      names the project, doc_type and path.
- [ ] **B4.** A hit from a `knowledge` document has a green left edge and sorts
      ahead of equally-relevant ordinary documents.
- [ ] **B5.** Click a hit. It jumps to the Documents tab, selects that project,
      and opens that document at the right place.
- [ ] **B6.** Set the scope dropdown to one project and repeat. Results are
      restricted to it.
- [ ] **B7.** Search something certainly absent (`zzqqxx`). "Nothing matched"
      reads as a clean empty state, not an error.
- [ ] **B8.** Search a deliberately broken FTS5 expression — a bare `"` — and
      confirm you get an amber explanatory line and substring results, not a
      500 or a blank page.

---

## C — path safety

Tester-proven for the traversal, forged-id, prefix-collision, symlink and
outside-roots cases. These are the manual attempts worth making anyway.

- [ ] **C1.** In the browser, hand-edit the URL to
      `http://127.0.0.1:8002/api/estate/document?doc_id=../../../../etc/passwd`
      (or `..\..\..\windows\win.ini`). Expect **404** with
      `{"reason": "unknown_document"}`.
- [ ] **C2.** Try a real path as the id:
      `?doc_id=C:\Users\timps\Documents\GitHub\L5GN-Tools\README.md`.
      Expect **404 unknown_document** — the route does not take paths at all.
- [ ] **C3.** Try a plausible-looking forged digest: `?doc_id=0000000000000000`.
      Expect **404 unknown_document**.
- [ ] **C4.** Confirm there is **no route anywhere** that accepts a path. Open
      `http://127.0.0.1:8002/api/docs` and read the estate route signatures:
      every one takes `project`, `doc_id` or `q`. None takes a path.
- [ ] **C5.** Header warnings: if the build stamp shows a "warning(s)" count,
      read it. It means a document was dropped from the catalogue for having a
      non-relative path — worth knowing where that came from.

---

## D — no vault, still serves

The case the preflight split exists for. Walk this on a rig with no vault, or
simulate it.

- [ ] **D1.** Point the machine at a vault path that does not exist (rename the
      vault dir temporarily, or edit `config/local.json`), then
      `python run.py review --host 127.0.0.1`. **It starts.** The banner says
      `queue routes DEGRADED -- ...` and `estate routes ENABLED -- ...`.
- [ ] **D2.** The **Documents**, **Search** and **Time** tabs all work normally.
- [ ] **D3.** The **Review queue** tab says the queue is unavailable on this
      machine and explains why — it does not show a JavaScript error, a spinner
      that never resolves, or an empty list implying there is nothing to rule on.
- [ ] **D4.** `curl http://127.0.0.1:8002/api/health` shows `vault.available:
      false` with a reason, and `estate.available: true`. Both halves reported
      separately.
- [ ] **D5.** The mirror case: restore the vault and temporarily rename
      `data/estate.json`. The server still starts, the **queue works**, and the
      estate tabs say there is no build and to run `python run.py build`.
- [ ] **D6.** With **both** absent, `run.py review` refuses with exit code 2 and
      names both gaps. (`echo $LASTEXITCODE` in PowerShell.)

---

## E — staleness is visible

- [ ] **E1.** The build stamp is the first thing on the page and states
      `generated_at`, the age, and the toolkit commit.
- [ ] **E2.** `toolkit_dirty` at build time shows an amber "toolkit dirty at
      build time" flag. (It is currently **true** on `ac7710d`, so expect to see
      it — that is the flag working, not a fault.)
- [ ] **E3.** **Make a build read as stale.** Point the deck at an older
      snapshot: copy `data/history/estate-2026-07-27.json` over
      `data/estate.json` (keep a backup), restart, and confirm the age shows in
      days and the word **STALE** appears in red. Restore afterwards.

---

## F — nothing persisted

The strongest check in this sheet. Do it last, after using every tab.

- [ ] **F1.** Before starting the server, capture the state of `data/`:
      `Get-ChildItem data -Recurse -File | Measure-Object` (note the count), or
      `git status --short data/`.
- [ ] **F2.** Browse several documents, run several searches, open the Time tab.
- [ ] **F3.** Stop the server. Re-run the same command. **The file count is
      unchanged** and `git status` shows no new file under `data/`.
- [ ] **F4.** Search `data/` for any index or cache artefact:
      `Get-ChildItem data -Recurse -Include *.db,*.sqlite,*.idx,*.cache`.
      Expect nothing new.
- [ ] **F5.** `curl http://127.0.0.1:8002/api/estate/search/status` reports
      `"persisted": false`.

---

## G — time views are honest

Go to the **Time** tab.

- [ ] **G1.** The estate timeline draws every project with history on one shared
      axis, with the date range and total span in the heading.
- [ ] **G2.** **The lineage is visible.** Armory → Armory_v2 → Armory_v4 sit in
      that order along the axis, and Castle sits early. If the ordering does not
      match your memory of how these projects actually went, that is a finding.
- [ ] **G3.** The "Per project" table gives first commit, last commit, days,
      commit count and contributors. **Contributors read `L5GN`**, not
      `timpsmith28-hash` — the alias fold is working.
- [ ] **G4.** **`L5GN-Archive` appears under "No history — stated, not guessed"**
      with the reason "not a git repository". It is **not** given a span, a first
      commit, or a date of any kind. On the work rig, all four non-git folders
      appear here.
- [ ] **G5.** Hover a timeline bar. The tooltip gives the real dates, span and
      commit count. A project whose whole history is one afternoon still shows a
      visible marker but a truthful number beside it.
- [ ] **G6.** "What changed since the last build" **names both builds** by file,
      timestamp **and toolkit commit** — e.g. `estate-2026-07-28.json —
      2026-07-28T22:20:48+01:00 @ 87253c8` → `estate-2026-07-29.json — ... @
      ac7710d`. If it does not say which two builds, the whole panel is
      unreadable.
- [ ] **G7.** The delta's claims are checkable: pick one project it says gained
      commits and confirm against `git -C <project> log`.

---

## H — the existing queue still works

Regression. The queue routes were touched (each gained a `_need_vault()` guard)
and the page was restructured into tabs.

- [ ] **H1.** On a machine **with** a vault: the Review queue tab loads its
      project nav and batches exactly as before.
- [ ] **H2.** Accepting a batch, "Not this project", and the "→ other candidate"
      button all still work.
- [ ] **H3.** Switching between tabs does not lose the queue's selected project
      or its loaded batch.

---

## Findings

Anything that fails, surprises you, or reads wrong goes in the results log with
the check number. **B2 in particular is a judgement call, not a pass/fail** — if
search does not surface what you expected, record the query and the results.
That is the return on the work estate and it is worth measuring honestly.
