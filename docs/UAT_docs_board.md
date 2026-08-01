# UAT walk-sheet — the docs board, read-only

**Brief:** `docs/COWORK_BRIEF_docs_board.md`
**Report:** `docs/COWORK_REPORT_docs_board.md`
**Built:** 2026-08-01, base commit `a202ba0`, working tree dirty.
**Nothing committed** — walk against the working tree.
**Gate at build time:** `python verify.py` → **GREEN**, 6 auditors + 54 testers
(+1 `tester_docs_board`). Five `gate-frozen` markers were added to finished docs
so `auditor_doc_claims` stops red — that is check **F1** below, not unrelated
tidying.

**Scope:** Tasks 1 and 2 only. The board is **read-only**: there is no
ratification control and no archive staging, and their absence is itself a
check (C3). Do not walk this sheet looking for them.

Start: `python run.py review --host 127.0.0.1`, open the **Docs board** tab.

Mark each: `- [x]` passed · `- [~]` passed with a note · `- [ ]` failed or not
walked. **Write the note on the line.** If you record evidence anywhere other
than this sheet, you have reproduced finding B1 in the act of walking it.

---

## Walk log

| when | who | what | evidence |
|---|---|---|---|
| 2026-08-01 | Tim | **A and B**, on the personal rig at `53ab5ba` (working tree dirty), surface on the tailnet at `:8002` | six screenshots of the Docs board tab + `python verify.py` GREEN + `git status` |
| 2026-08-01 | Tim | **C and D**, same rig and commit, after the two-pane layout change | twelve screenshots + three `git status` runs |
| 2026-08-01 | Tim | **E** (simulated: `estate: both` on the gaming rig), **F**, **G** | boot log + uvicorn access log + Review-queue screenshot + full `verify.py` + `git status` |

**No results log has been opened yet, deliberately.** `UAT_docs_board_results.md`
would move this card from *built, not walked* to *walked* on a walk that is two
sections in — and worse, ticks recorded there against an untouched sheet would
reproduce finding **B1** in the act of walking B1. The evidence goes on the
sheet, which is what the sheet is for. The results log opens when the walk
closes.

**Walk complete. 40 passed, 5 passed with a note, 1 carried.**

| check | state | note |
|---|---|---|
| **E7** | carried | needs the work rig — the gaming rig cannot evidence the repo anchor, the toolkit sits inside a root there. `tester_docs_board` covers the logic; only the work rig covers the configuration |
| **A5** | `~` | the two counts were re-run in the build sandbox, not on the rig |
| **A7** | `~` | the reload-is-identical half was not separately observed |
| **C5** | `~` | *presentation*, not derivation — the card weights kind above disposition. Design-thread question, not a defect |
| **G3** | `~` | no-bleed-through confirmed in dark; `Canvas` resolves per theme so light is a different render |
| **G9** | `~` | the ~70rem breakpoint was not exercised |

**One defect found and fixed by this walk** — see E6. The loopback refusal
message named `work` where the condition is `!= "personal"`, and this slice is
what made that line reachable with `both`. Message text only; the wall itself
did not move, which was the risk.

**Results log:** `docs/UAT_docs_board_results.md`, stamped at `53ab5ba`.

**Windows note, because it cost three checks.** `grep` and `curl` in the
original sheet were POSIX habits, and the example port was wrong. On `cmd.exe`:
`powershell -Command "(Select-String -Path docs\<file> -Pattern '^\s*- \[ \]').Count"`
for a checkbox count, `curl.exe` (never bare `curl`) for a request, and the
port is **8002**. This sheet is walked on a Windows rig; its commands should be
Windows commands, and its examples should match `REVIEW_DEFAULT_PORT`.

**Layout was changed after this walk** (CSS and element order only —
`board-col` scrolling, opaque sticky heads, viewer moved above the board). No
derivation, route or count changed, so A and B stand as walked. The layout
fixes are new section **G**.

---

## A · The board matches reality

The brief's table was four days stale; the report's is recomputed. Where the
board and the report disagree, the board is probably right — check which.

- [x] **A1** Four columns: In flight, Built not walked, Walked, Archived.
      — *Heads read `In flight 3` · `Built, not walked 6` · `Walked 5` ·
      `Archived 25`.*
- [x] **A2** *In flight* holds exactly `local_deck_evidence`,
      `local_deck_overlap`, `uat_sidebar` — and **not** `docs_board`, which has
      a report now and should have moved to *built, not walked*. (The board
      deriving its own round is the cheapest end-to-end check there is.)
      — *Three cards, and `docs board` is the first card of the next column.*
- [x] **A3** *Built, not walked* holds `estate_restructure`, `file_census`,
      `intent_evidence`, `local_deck_docs_and_time`, `scanner_bugfixes`,
      `docs_board`. Confirm `local_deck_docs_and_time` is here and **not** in
      flight — the brief had it wrong.
      — *All six present; `local deck docs and time` reads 0 done / 43 open.*
- [x] **A4** *Walked* holds `command_deck_proto`, `doc_provenance_coverage`,
      `repo_tier_producers`, `toolkit_self_scan`, `work_rig_solo`. Confirm
      `toolkit_self_scan` is here — the brief had it in flight.
      — *All five present; `toolkit self scan` reads 15 done / 25 open with its
      results log listed.*
- [~] **A5** Open-item counts on two cards match a hand count of `- [ ]` in the
      sheet. Suggested: `intent_evidence` (85 open) and `scanner_bugfixes` (9).
      — *The screenshots alone did not settle this: they show the board
      asserting 0/85 and 0/9, which is the board agreeing with itself, and the
      check exists to catch the counter being wrong. The independent side was
      then run against the same tree —
      `grep -c '^\s*- \[ \]' docs/UAT_intent_evidence.md` → **85**, and
      `docs/UAT_scanner_bugfixes.md` → **9**. Both match. Marked `~` rather
      than `x` because it was run in the build sandbox, not by the walker on
      the rig; re-run the two greps there to close it.*
- [x] **A6** There is **no `Archivable` column** anywhere. It is not derivable.
      — *Four column heads, no fifth.*
- [~] **A7** Reload the page. The board is identical, and `git status` shows no
      new file — nothing was written to derive it.
      — *Second half evidenced and it is the load-bearing half: `git status`
      after the session lists only the ten modified and four untracked files
      this slice authored — no board state file, no cache, no index. The
      reload-is-identical half was not separately observed; it is cheap to add
      when C–F are walked.*

## B · The checkbox inconsistency is visible, not normalised

- [x] **B1** Five cards are flagged: `doc_provenance_coverage`,
      `repo_tier_producers`, `work_rig_solo`, and the archived
      `apply_alignment` and `relink_scoring`. The brief named the first two;
      the other three are the board finding more than was asked.
      — *Banner reads `5 finding(s)` and names exactly those five.*
- [x] **B2** Each flagged card **still shows 0 done** on its sheet, beside the
      results log's count. The numbers were not reconciled.
      — *`doc provenance coverage` 0/19 beside 12/2; `repo tier producers` 0/17
      beside 14/3; `relink scoring` 0/15 beside 11/3; `apply alignment` 0/35
      beside 6/0; `work rig solo` 0/30 beside 21/6. Both numbers on every card.*
- [x] **B3** `command_deck_proto` (10/5) and `toolkit_self_scan` (15/25) are
      **not** flagged — the flag distinguishes rather than firing on everything.
      — *Both cards carry no amber flag. The flag means something.*
- [x] **B4** No sheet in `docs/` gained a tick. `git diff` on
      `docs/UAT_doc_provenance_coverage.md` is empty.
      — *Stronger evidence than asked for: `git status` lists no
      `UAT_doc_provenance_coverage.md`, `UAT_repo_tier_producers.md` or
      `UAT_work_rig_solo.md` under modified at all, so all three diffs are
      empty. The five modified docs are the `gate-frozen` files in F1.*

## C · Odd shapes are handled, never rendered as broken pairs

- [x] **C1** `work_rig_solo` appears in *Walked*, tagged **walk only**, and its
      card claims no brief. It is a walk-sheet with no brief — a legitimate
      shape, deliberately on the board as itself.
      — *Blue `WALK ONLY` tag; the card lists `walk` and `results` rows only,
      with no brief row and no empty brief slot.*
- [x] **C2** The Archived column header reads **25 cards · 45 files · 14
      unmatched · 3 walk-only**. Count the files in `docs/archive/` — the
      `file_count` must account for every one, so nothing was silently dropped.
      — *`Archived 25` / `45 files · 14 unmatched · 3 walk-only`, as derived.*
- [x] **C3** No card in *Walked* offers a "UAT ratified?" control, and no card
      anywhere offers "Prepare archive". They are **absent**, not greyed out.
      — *Walker confirmed neither control appears anywhere on the board.*
- [x] **C4** `COWORK_ROUND_1_REPORT.md` and `COWORK_BRIEF_build_round_1.md`
      appear as **two separate unmatched cards**, not one broken pair. Same for
      rounds 2 and 3.
      — *`build round 1` (brief) and `ROUND 1` (report_legacy) are two cards,
      both tagged UNMATCHED, both stamped `completed pair`. Rounds 2 and 3
      evidenced in the first walk's screenshots.*
- [~] **C5** `HANDOFF_final_2026-07-18.md` and `NEXT_SESSION_PLAN_final.md` are
      unmatched cards stamped **retired**. Their disposition came from the
      stamp, not the filename.
      — *Walker reported "no mention of retired". The attached evidence does
      carry it — both cards read `stamped retired — but pairs with nothing by
      filename` — so the derivation is right and the check passes on substance.
      Recorded `~` because what failed is **presentation**: the kind
      (`UNMATCHED`) is an amber chip and reads as the card's headline, while
      the disposition — the archivist's judgement, which this report says
      outranks the kind — is body prose two lines below it. The card weights
      them backwards. A disposition chip beside the kind chip would fix it.
      **Open for the design thread; no code changed on this walk.***
- [x] **C6** `COWORK_BRIEF_chronicler_alignment.md` is tagged **unmatched** and
      shows *stamped `completed pair`*. Both are on the card; neither was
      dropped in favour of the other.
      — *Both present, with the line explaining why they differ.*
- [x] **C7** `cowork_tasks_cleanup_and_qol.md` reads **superseded** — its stamp
      elaborates well past the vocabulary (`SUPERSEDED — do NOT run as a task
      list`) and still classified.
      — *Card reads `stamped superseded`; prefix matching held.*
- [x] **C8** **Findings shows no unstamped file.** All 45 archived files carry a
      stamp, including `UAT_round_3_results.md` and
      `UAT_solo_playbook_results.md`, whose stamps sit *below* a multi-line
      `uat` comment. If either shows up as unstamped, the parser's window is
      too tight and this is a false finding.
      — *Banner reads `5 finding(s)`, all five the checkbox-convention case. No
      unstamped finding, so the 60-line window is wide enough for both.*
- [x] **C9** The "deliberately not on the board" list expands to 11 documents —
      trinity, playbooks, spec, runbooks — each with a reason.
      — *Exactly 11, each with its reason and a `§1` citation where one applies.*

## D · Reading a card body

**The port is 8002, not 8000.** `REVIEW_DEFAULT_PORT = 8002`, chosen so
`review` and `serve` can run at once. Earlier drafts of this sheet said 8000 and
cost two checks to a connection refused that had nothing to do with the code —
read the port off the `review: binding …` line at startup rather than off any
example. `curl` is shadowed by an alias in PowerShell; `curl.exe` from
`cmd.exe` is the reliable spelling.

- [x] **D1** Click a brief on any card. It renders as plain text, not markup.
      — *`COWORK_BRIEF_uat_sidebar.md` and `COWORK_BRIEF_local_deck_evidence.md`
      both render with their `#`, `**` and backticks visible as characters. No
      heading became a heading, which is the check.*
- [x] **D2** Click a file in `docs/archive/`. The stamp is visible at the top of
      the body.
      — *`docs/archive/UAT_apply_alignment_results.md` opens with its `uat`
      comment and the full `> **ARCHIVED** 2026-07-27 · completed pair
      (results)` block above the `# Results log` title — stamp above title,
      body untouched, exactly as §3 requires.*
- [x] **D3** `curl.exe -i "http://127.0.0.1:8002/api/docs/document?doc_id=docs/DECISIONS.md"`
      → **404 `unknown_document`**. The route takes a digest, never a path.
      — *`HTTP/1.1 404 Not Found`, body
      `{"detail":{"reason":"unknown_document","detail":"No board document with
      that identifier. The board addresses documents by digest, never by
      path."}}`. Note what is **not** in that body: no statement about whether
      `docs/DECISIONS.md` exists. The refusal discloses nothing.*
- [x] **D4** Same with `doc_id=../../etc/passwd` → **404**. Nothing is disclosed
      about what exists.
      — *Byte-identical refusal to D3 — which is the point: a traversal attempt
      and a real-but-unlisted path are indistinguishable to the caller, because
      both are simply digests of nothing. Walked with `curl.exe`; a browser
      address bar cannot test this at all, having normalised `../../` away
      before sending.*
- [x] **D5** `git status` after browsing several documents: still clean. Bodies
      are read at request time and nothing is cached.
      — *Three `git status` runs across the session, before and after browsing:
      byte-identical output every time. Ten modified, four untracked, all
      authored by this slice. No cache, no index, no board state file.*

## E · The board runs on a machine the old preflight refused

The point of the estate-clause change. If you have the work rig to hand, walk
this there; otherwise simulate by setting the declared estate to `both` in
`config/local.json` and reverting after.

- [x] **E1** With the declared estate set to something unrecognised (`both`),
      `run.py review --host 127.0.0.1` **starts** instead of exiting 2.
      — *Simulated on the gaming rig with `estate: both`. Server bound and
      `Application startup complete`. Under the old preflight this exited 2.*
- [x] **E2** Startup prints that **no thread is rendered** on this machine, and
      says the document routes are unaffected.
      — *Verbatim: `review: queue routes DEGRADED -- Thread routes are disabled
      on this machine: unrecognised estate 'both': …` and `review:
      estate='both' -- NO thread is rendered on this machine (DECISIONS 0025…).
      Document routes are unaffected -- docs/ and the estate build are not
      estate-labelled data.` Estate routes ENABLED on the same boot, 9 projects
      / 195 authored documents.*
- [x] **E3** The Docs board tab works fully.
      — **The check the whole section exists for, and it passes.** *Second
      `both` boot, `127.0.0.1:8002`: the Docs board tab renders the findings
      banner (5), all four columns with cards, and
      `docs/COWORK_BRIEF_docs_board.md` open in the viewer — a card body read
      from disk on a machine whose declared estate resolves to no clause at
      all. Under the old preflight this process would not have started.*

      *One thing worth reading correctly on that screen: the build stamp says
      `estate personal` while the machine's declared estate is `both`. Not a
      contradiction — the stamp reports `estate_name` from the **snapshot**,
      which was built when the config said personal. The declared estate is a
      property of the machine now; the snapshot's is a property of when it was
      taken. Slice 1 renamed the config string `declared_estate` to keep those
      two apart, and this screen is why.*
- [x] **E4** `curl.exe -i "http://127.0.0.1:8002/api/pending"` → **503**, with
      reason `estate_unresolved` naming the estate — not a claim about a
      missing DB.
      — *Closed on the wire on the second attempt (the first went to port 8000;
      `review` binds 8002). `HTTP/1.1 503 Service Unavailable` with body
      `{"detail":{"available":false,"reason":"estate_unresolved","detail":
      "Thread routes are disabled on this machine: unrecognised estate
      'both'…"}}`. The reason tag is exactly the new one, and the sentence
      names the estate rather than claiming a missing DB — which was the point,
      since this rig's vault absence and its unresolved estate are two
      different gaps and the old code could only report one.*
- [x] **E5** The Review queue tab degrades with that sentence rather than
      showing threads.
      — *Tab shows "Review queue unavailable on this machine." with the full
      reason, "No vault here." in the nav, and the amber note that Documents,
      Search and Time work regardless. No thread rendered anywhere.*
- [x] **E6** Restore the declared estate. `--host 0.0.0.0` on a non-personal
      estate **still refuses to bind** (0025's loopback rule is untouched by
      any of this). This is the check that matters most in this section.
      — **PASSED, and it found a defect this slice introduced.** *`python
      run.py review` on `estate: both` (default host `0.0.0.0`) printed
      `refusing to bind '0.0.0.0' -- this machine's declared estate is 'both'`
      and returned without binding a port. The wall holds: scoping the estate
      clause to the vault half did not weaken the loopback rule, which was the
      risk.*

      **The defect.** *The same message went on to say 0025 "requires a
      **work-estate** surface to bind loopback only" — while printing
      `'both'` one clause earlier. The condition has always been
      `!= "personal"`, but until this slice an unrecognised estate exited at
      the clause check and never reached this line, so only `work` ever saw it
      and the wording was true by accident. Making the clause refusal
      vault-scoped is exactly what made it reachable with `both`. Corrected to
      "any non-personal estate". Message text only — the condition is
      unchanged, and the refusal it describes was already correct.*
- [ ] **E7** On the work rig specifically: card bodies render even though the
      toolkit sits outside every configured estate root. This is the whole
      reason for the repo anchor.
      — **CARRIED — not walkable on this machine.** *Section E was simulated on
      the gaming rig, where the toolkit sits inside a configured root (since
      `6dd70f1`). The repo anchor therefore does nothing observable there:
      containment would pass on the estate roots alone, so a green result would
      evidence nothing. This needs the work rig and no substitute exists.*

      *What stands in the meantime: `tester_docs_board` drives the anchor
      directly — it asserts `REPO_ROOT` resolves to this checkout, reads a real
      `docs/` file through it, and refuses both an outside path and the
      `<repo>-evil` sibling case. That is the logic. The work rig is the only
      thing that evidences the **configuration** the logic was written for.
      **Walk this on the next work-rig session and record it here**; it does
      not block the pair, but it is the one claim in this slice resting on a
      tester alone.*

## F · The gate, and the part that is reversible

- [x] **F1** **The five `gate-frozen` markers.** `git diff` on
      `docs/COWORK_REPORT_toolkit_self_scan.md`,
      `docs/COWORK_REPORT_local_deck_docs_and_time.md`,
      `docs/UAT_toolkit_self_scan.md`, `docs/UAT_local_deck_docs_and_time.md`
      and `docs/UAT_toolkit_self_scan_results.md` shows **only an added marker
      and comment — no body text or number changed**. Then rule: freezing was
      chosen over editing 53 → 54 because the results log records what
      `verify.py` printed on a stated day. If you disagree, say so here — this
      is one edit away from reversal.
      — **RATIFIED.** *Tim: "F1 you did the right thing." The diff is
      29 insertions, 0 deletions across the five files; no body line was
      touched. The judgement stands: a results log records an observation, and
      an observation is not edited to match a later tree.*
- [x] **F2** `python verify.py` → **GREEN**. If it is red on a file this slice
      did not touch, that is a real finding — record it, do not work around it.
      — *GREEN on the rig. Six auditors OK, every tester OK.*
- [x] **F3** `python verify.py` reports **54 testers**, `tester_docs_board` OK.
      — *`[ OK ] tester_docs_board`, last in the list, with the route half
      driven (fastapi is installed in the rig's `.venv`).*
- [x] **F4** Nothing persists: after the full walk, `git status` shows only the
      files this slice added or edited. No board state file, no cache, no index.
      — *Ten modified, four untracked, unchanged across every `git status` of
      the session including after the `both` boot and a browsing pass.*
- [x] **F5** Nothing was committed by any of the above.
      — *`git status` still reads "no changes added to commit"; HEAD unmoved at
      `53ab5ba`.*

## G · Layout fixes (added 2026-08-01, after the A/B walk)

Three complaints from the first walk. CSS and element order only — no
derivation, route, count or refusal changed, which is why A and B were not
re-walked.

**Walked 2026-08-01.** Tim: *"the look and feel is there now — not noticed any
of the things to watch for from the UAT list."* Recorded per check below; the
two carrying `~` each name a sub-condition the walk could not have covered.

- [x] **G1** Each column scrolls independently, capped at roughly a screen. The
      Archived column's 25-card tail no longer sets the height of the page.
- [x] **G2** All four column heads stay on screen together while a column
      scrolls — that is the only view in which the four counts can be compared.
- [~] **G3** **No bleed-through.** Scroll a column and confirm cards pass
      *behind* the head, not through it. The head was translucent; it now sits
      on the UA's own `Canvas` colour, so check it in **both** light and dark —
      the fix is theme-derived, not a hardcoded hex, and a hardcoded one would
      have been right in exactly one theme.
      — *No bleed-through observed. `~` only because every screenshot in this
      session is dark: `Canvas` resolves per theme, so light is a genuinely
      different render and the one a hardcoded hex would have broken. One
      OS-theme toggle closes it.*
- [x] **G4** The pane opens with a **two-column header**: findings and the
      off-board list on the left, the document viewer on the right, both the
      same fixed height. The board sits full width underneath it.
- [x] **G5** Click a file on any card — including one at the bottom of the
      Archived column — and the text appears in the right-hand pane without
      scrolling past the archive tail. Clicking a card already near the top
      does **not** yank the page around.
      — *Evidenced in the D2 screenshot: `UAT_apply_alignment_results.md`,
      opened from the Archived column, renders in the right pane with the board
      still visible below.*
- [x] **G6** The header is a fixed height whether the viewer is empty or
      showing a long document, so the board always starts in the same place.
      Both panes scroll internally; neither stretches the row.
- [x] **G7** Open a long document (`docs/COWORK_REPORT_docs_board.md`). The
      filename stays pinned at the top of the viewer as the body scrolls, and
      the body does **not** bleed through it.
- [x] **G8** The viewer text is more readable than before but is **still plain
      text** — read the note on markdown rendering in the report before
      treating this as a half-fix.
- [~] **G9** Narrow the window below ~70rem. The header stacks to one column
      and the board's columns stack too; nothing is clipped or unreachable.
      — *Not specifically exercised; the walk was at desktop width throughout.
      The breakpoint is real code (`@media (max-width: 70rem)`) and untested by
      the walk. Drag the window narrow once to close it.*

---

**Ready to walk.** Results go in `docs/UAT_docs_board_results.md` with a `uat`
stamp naming the commit walked; **do not write a `gate=` field** — a truthful
historical count turns red the moment the next round registers a tester, and
the cheapest way back to green is to edit the record. `docs/README.md` §3 makes
`gate=` optional for exactly that reason.
