# UAT — the record moves to conversation grain

**Walk-sheet of record** for `docs/COWORK_BRIEF_conversation_grain.md`. Written
with the brief, before the build, per `CONVENTION_briefs.md` §2.

**Host:** `LucasGoonPC`. **Estate:** personal (0039).

**Before walking anything:** open a shell with **no `CHRONICLER_*` variables
set** for every `verify.py` run, and the Step 0 shell (variables set per
`RUNBOOK_chronicler_refresh.md`) for everything that reads the vault. The gate is
not hermetic against those variables and will report issues that have nothing to
do with this round.

`[G]` — a machine or an unambiguous procedure decides.
`[H]` — a human judgement is genuinely required.

**14 `[G]`, 5 `[H]`.** The `[H]`s are counted deliberately: four ask about the
operator's *experience* of the result rather than its behaviour, and one asks
whether a number should be believed. None of them stands in for a property that
could have been checked mechanically.

---

## A. Preconditions

**A1 `[G]`** — `grep -c "^## 00" docs/DECISIONS.md` returns **57**.

**A2 `[G]`** — `git log --oneline -1 -- chronicler/pipeline/run_pipeline.py`
shows the encoding fix landed. Then, in a shell whose output includes a non-ASCII
character, run a pipeline stage that fails and confirm **the tail is printed**
rather than the exit code alone.

**A3 `[G]`** — `python data\_vault_status.py` runs and its INTENT figure is
recorded verbatim in the report. Expected at drafting: `35 / 336 = 10.42%`.
**If it differs, record the difference — do not adjust the brief.**

**A4 `[G]`** — `python verify.py` is GREEN in a clean shell before any task
begins.

## B. The sidecar reader (Task 1)

**B1 `[G]`** — The reader returns a `conversation_id` for
`local_c36655b7fc0044539a482639949b1a74.json` equal to
`local_c36655b7-fc00-4453-9a48-2639949b1a74`. **A reader keyed on the filename
returns the 32-hex form and fails this check.**

**B2 `[G]`** — The report states how many sidecars carry each filename shape.
Both counts are present and they sum to the total discovered.

**B3 `[G]`** — For the test conversation the reader returns **both** folders —
`…\GitHub\L5GN-Tools` and `…\WizForge\Work_Bridge` — not the first one only.

**B4 `[G]`** — The reader is shown, by inspection or instrumentation, to read
named fields only. A reader that parses the whole sidecar fails this check even
if its output is correct.

**B5 `[H]`** — Read the reader's output for three conversations you remember
well. **Is the title the one you would recognise, and the folder set the one you
actually had open?** This is the check that the sidecar means what the round
assumes it means.

## C. Candidates (Task 2)

**C1 `[G]`** — Every conversation with an empty `userSelectedFolders` produces
**no row**. Count them; the count appears in the report.

**C2 `[G]`** — No candidate row's `project_id` was derived from a generic
container alone (`Documents`, `Downloads`, `Desktop`, `GitHub`, `Backups`,
`scratch`, `vendors`, the user root).

**C3 `[G]`** — The test conversation appears as **`AMBIGUOUS`** with both
candidates shown, not resolved to either.

**C4 `[G]`** — Any conversation naming `Work_Bridge` is emitted as its **own
record kind**. It appears in neither the personal nor the work link set.

**C5 `[G]`** — `config/personal_conversation_map.tsv` is **byte-identical** to
its pre-round state. `git diff --stat config/` shows no change to it.

**C6 `[H]`** — Open the Curator tab and look at ten candidates. **Could you
ratify any of them without going and looking something up?** If you have to open
the conversation to decide, the candidate has not arrived assembled and that is a
design finding, not a walk failure — record it as one.

## D. Provenance vocabulary (Task 3)

**D1 `[G]`** — Attempting to write a row whose provenance tag carries a value
outside the declared set is **refused**. Not warned, not accepted with a note.

**D2 `[G]`** — The declared set appears in `CONVENTION_conversation_map.md` §5,
and the parser reads it from there rather than carrying its own copy.

**D3 `[G]`** — If the ruling has not been ratified, Task 3 is **staged and
uncommitted**. `git status` shows the work; `git log` does not.

## E. The ratified rename (Task 4)

**E1 `[G]`** — `head -1` on both maps returns `conversation_id` as the first
column.

**E2 `[G]`** — `grep -rn "session_id" ` across the map's consumers returns
nothing that reads the map's key. Occurrences relating to a *session* in 0038's
sense are correct and must remain.

**E3 `[G]`** — The Curator tab loads and renders rows after the rename.

**E4 `[G]`** — The rename is **one commit**, and its message names every file
changed.

## F. Fingerprint parity (Task 5)

**F1 `[G]`** — `config/personal_conversation_map.tsv.sha256` exists and matches
the file computed on Windows.

**F2 `[G]`** — Corrupt a copy of the map, run the auditor, and confirm it
**fails**. An auditor that cannot fail is 0048 clause 4's defect and this check
exists to prove it can.

## G. Both figures (Task 6)

**G1 `[G]`** — One command prints the thread-grain figure, the
conversation-grain figure, and the excluded count, from one vault in one run.

**G2 `[G]`** — The thread-grain figure equals `data/_vault_status.py`'s to the
row. **A disagreement between two readers of the same vault is a stop, not a
rounding difference.**

**G3 `[G]`** — The command's own output states the denominator's definition.

**G4 `[H]`** — **Read the two figures side by side. Does the conversation-grain
number look better than the estate actually is?** If the rise is mostly the
Gemini fragments leaving the denominator, the definition has manufactured it and
Task 6 has failed at its one job — regardless of what the checks above say.

## H. The falsifier

**H1 `[G]`** — The disagreement rate between sidecar-derived candidates and
rows you subsequently ratify is computed and recorded **before** it is
interpreted.

**H2 `[H]`** — **If the rate is above zero, look at every disagreement
individually. Is the sidecar wrong, or were you?** The design rests on this join
being deterministic; a disagreement the operator resolves in the sidecar's favour
is a different result from one where the sidecar was simply wrong, and only a
human can tell which happened.

## I. The round as a whole

**I1 `[G]`** — `python verify.py` GREEN in a clean shell, with every new tester
registered.

**I2 `[H]`** — **A week from now, are you reading the map, or are you back in
the spreadsheet?** The sheet exists because the mechanism was empty. If the
mechanism is still the harder path after this round, the round moved rows and
not the problem.

---

## Results

Record in `docs/UAT_conversation_grain_results.md`, with the stamp:

```
<!-- uat: commit=<sha> dirty=<bool> host=LucasGoonPC walked=<YYYY-MM-DD> -->
```

`commit` and `walked` are required. **Omit `gate=` rather than assert a count
nobody observed** — `auditor_uat_stamp` checks it against `verify.py` when
present.
