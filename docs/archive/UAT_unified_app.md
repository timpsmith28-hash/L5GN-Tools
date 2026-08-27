<!-- gate-frozen: commit=f1d7df3 -->

> **ARCHIVED** 2026-08-24 · completed pair · walk-sheet for `docs/archive/COWORK_BRIEF_unified_app.md`
> Superseded by its own results log, `docs/archive/UAT_unified_app_results.md`. Original purpose: the acceptance checks for the one-application round.
> Read as the questions that were asked, never as work outstanding. Walked 2026-08-17 at `174e57e`; the ticks are in the results log. **Do not run this as a task list.**

# UAT walk-sheet — the unified app (COWORK_BRIEF_unified_app.md)

Pair: `docs/COWORK_BRIEF_unified_app.md` → `docs/COWORK_REPORT_unified_app.md`.
Built across `8ba9751`..`f1d7df3` (Tasks 1-6 plus three live-walk fixes). Gate
at build time: `python verify.py` **GREEN**, **8** auditors + **66** testers
(frozen build-time count). Mark each check **ready to walk**, never "passed"
— the walk is Tim's.

`[G]` = the gate, an auditor, or a hand-built smoke test already proves this
(cited per item) · `[H]` = only walking the real app, on the real machine,
answers it.

---

## `[G]` items — already proven, listed for completeness

These don't need re-checking, but they're the floor the `[H]` items above
stand on. If any of these feels wrong while you're walking the `[H]` list
below, that's a finding, not a false negative on your part — say so.

- **1.** `verify.py` GREEN with no web stack installed. *(auditor_stdlib +
  auditor_dependency_direction; re-run any time with fastapi/uvicorn
  uninstalled to re-confirm.)*
- **2.** An auditor fails a deliberate import of the app tier from inside
  `l5gntools/`. *(auditor_dependency_direction — 0034 clause 3.)*
- **3.** Adding a module is one registration plus one view file.
  *(auditor_module_contract + tester_module_registry; a throwaway module was
  added and removed during the build to confirm the shape.)*
- **4.** `auditor_module_contract` fails on a bad registration or an
  unregistered view file. *(direct test during Task 1.)*
- **5.** A module with unmet `requires` renders declared-degraded with a
  named cause. *(walked live: Time/Curator both show this on a
  no-vault/wrong-estate machine — see the screenshot you already sent.)*
- **6.** Reload on any view lands on that view; a deep link opens it directly.
  *(app.js's hash router — `showPane()` reads `location.hash` on load and on
  `hashchange`.)*
- **7.** One process, one port, one bind, loopback only; no CORS middleware
  anywhere. *(read directly off `chronicler/review/app.py` — one `uvicorn.run`
  call, no `CORSMiddleware` import in the tree.)*
- **8.** A work-estate machine asked to bind beyond loopback refuses to
  start. *(DECISIONS 0025's structural check, unmodified by this round.)*
- **9.** The report view changes when `data/estate.json` changes, with no
  rebuild; the exported `report.html` doesn't, and says so on its own face.
  *(estate_report.py re-reads on every request; `.exportban` banner added to
  `l5gntools/report.py`'s template.)*
- **10.** Starting a second instance refuses; it never opens a second server
  on the same vault. *(walked in-sandbox: launched instance 1, waited for its
  own health check to pass, launched instance 2 — exit code 1, correct
  refusal message, no second server spawned.)*
- **11.** Killing the window stops the server; no orphan uvicorn.
  *(walked in-sandbox via SIGTERM — required a fix, see the report; confirmed
  clean after.)*
- **12.** The window failing to open prints a loopback URL and the server
  keeps working. *(walked in-sandbox — no GTK/Qt backend there, hit the real
  `WebViewException` path, not a simulation.)*
- **13.** `deposit`/`consume`/`intake` without `"mesh": true` report a stated
  refusal, not a traceback. *(walked directly — all three tested, exit 1,
  correct remedy text each time.)*
- **14.** The archived playbooks carry stamps naming the ruling (0036); no
  core `docs/` file still asserts a two-role mesh as the default.
  *(`git mv` + stamps in `67d543a`; ARCHITECTURE/README rewritten alongside.)*

---

## `[H]` items — need your walk

### H1. Reload mid-UAT-walk, and mid-curator-ratification

Open the deck, start actually working through something — the UAT sidebar, or
a Curator ratification — get partway through **without submitting**, then hit
browser reload (F5). What actually happens to the unsubmitted judgement?
Screenshot before and after if it's not obvious from memory.

*Why this one matters most: it's the one item on this whole list that could
surface a real data-loss bug, not just a rough edge.*

### H2. Start it from the shortcut, cold

Close everything. Double-click `Start Chronicler Deck.bat` like you've never
seen this before. Does it feel like an application, or like a terminal with a
costume on? Note anything that breaks the illusion — console flashes, delay
before the window appears, anything that reads as "this is secretly two
things."

### H3. Is anything harder to find than it was across two ports?

You used to have Datasette on one port and the review app on another. Now
it's all one deck with a `Datasette` link/tab. Walk around it — is there
anything you used to reach directly that now takes more clicks, or that you
can't find at all?

### H4. Could you debug it at 2am?

Hypothetically: the window is blank, or a tab errors out (like the Estate
report did). Is the path from "something's wrong" to "here's the failing
route" shorter or longer than it was with two daemons and a supervisor? You
just lived this for real with the Estate report bug — that's good evidence
for this item, not a separate exercise.

### H5. Is the eighth module actually easy now?

Not "did the throwaway module work" during the build — would *you* reach for
adding one? If you had a new idea for a tab tomorrow, does this feel like a
system you'd extend, or one you'd route around?

---

## What to send back

For each `[H]` item: a sentence or two of what happened, plus a screenshot
where one's useful (H1 and H2 especially). Doesn't need to be formal — I'll
turn it into the results log and the final report.
