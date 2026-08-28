# Agenda — design thread restart, 2026-08-28

A restart note under `CONVENTION_design_thread_restart.md` §5. Frozen at its
date. It establishes state; it decides nothing. The planning it introduces is
`AGENDA_running_order_2026-08-28.md`, and that file is the longer of the two —
which is the §5 test this note has to pass.

**Host:** `LucasGoonPC`, personal estate. **Read, never recalled** (§2): every
figure below was re-derived from the artefact on this reading, or is marked
unknown. Nothing was taken from the operator's framing without checking it.

> **Amended once, 2026-08-28, later the same day.** Three of the five sources
> this note recorded as unread were then read on the rig, in a Windows shell
> this session could not reach: `git status`, `python data\_vault_status.py`,
> `python verify.py`, and `python run.py build --fresh`. The amendments are
> marked **[AMENDED]** inline and the original readings are left standing above
> each one, because what a restart could not reach is itself a finding and
> deleting it would make the gaps section look cleaner than the session was.
> One of the three came back **disagreeing with the framing this thread opened
> with** — see the git line.

---

## Stage 1 — estate freshness

`python estate_freshness_check.py`, verbatim, not re-derived:

```
84.0h old (generated_at=2026-08-24T22:04:25+01:00) -- STALE
```

**Not rebuilt.** Rebuilding is a decision and this restart did not take it
(§8). Stages 2-4 below read `docs/`, not `data/estate.json`, so the stale
reading does not contaminate them; it does bear on any card that reads the
census.

**[AMENDED]** The operator then took that decision and ran `python run.py build
--fresh` — 9 projects scanned, feed rewritten, viewer rewritten. The Deck now
reports `build 2026-08-28T10:05:27+01:00 · commit 386d764 · 9 projects, 303
authored docs`. **Recorded as taken** (0045), not folded into the reading above.

**One thing the line proves about itself.** `data/estate.json`'s mtime on this
reading is 2026-08-28T10:05 — today. Its `generated_at` is four days old. The
script reads the field and not the mtime, and this reading is the case that
would have lied.

## Stages 2 and 3 — pending decisions, **by repo**

**The program/project axis does not exist** and was not substituted (§4).
`docs/DECISIONS.md` is repo-scoped and carries no registry id, so "pending
program decisions" and "pending project decisions" cannot be answered as asked.
0012 defines the tiers and the registry assigns them; the join is still one
field away. Reported by repo, and said so.

| | count |
|---|---:|
| entries (`grep -c "^## 00"`) | 57 |
| `accepted` | 49 |
| `proposed` — **not authority** | 7 — 0051, 0052, 0053, 0054, 0055, 0056, 0057 |
| **carrying no `Status` line at all** | **1 — 0036** |

**0036 has neither a `Status:` nor a `Date:` line.** It is neither accepted nor
proposed; the log does not say. This convention's own header cites 0036 as
authority for §6's no-standing-channel rule, and the entry it cites cannot be
shown to be in force. Found by parsing, not by reading — every other entry
matched the format.

**Unappended:** `data/decisions_draft/0058_proposed.md`, drafted 2026-08-28, not
in the log. While it sits under `data/` it is invisible to `run.py
decisions-map` and to every reader. It gates `COWORK_BRIEF_conversation_grain.md`,
which is written.

**Two draft directories exist**, both live: `data/decisions_draft/` (0058) and
`data/decision_drafts/` (0054-0056, 0057 — spent). §4 of the convention names the
second. Small, and it is how a draft goes missing.

**Behind the wall, named rather than omitted** (0051): the work-side `wfa-` and
`sfds-` logs were not read and cannot be. Stages 2-3 on this rig are
structurally incomplete about work-estate rulings.

## Stage 4 — board status

**The program/project board does not exist.** The docs board was read in its
place and is reported as what it is: a board over documents.

Derived from `docs/` filenames on this reading — both lists match the operator's
framing exactly:

- **10 briefs with no report** (talked, not built): conversation_grain,
  curator_linking, dispatcher, distillation_extraction, hermetic_gate,
  ledger_migration, model_bench, staleness_feeds, validation_ratify,
  wizard_tiers.
- **10 reports with no `_results` log** (built, not walked): conductor,
  estate_restructure, file_census, gap_closure, intent_evidence,
  knowledge_curator, local_deck_docs_and_time, project_wizard,
  quartermaster_frame, scanner_bugfixes.
- 11 rounds closed. `UAT_work_rig_solo_results.md` has no report on this rig.

**Twenty in flight is a finding about the board, not about the backlog.** It is
carried into the running order rather than judged here.

## Stage 5 — inbound from beyond the operator

Selected by the **open** test (§6.1), not by what looked new. Every source
pulled once, at restart time.

| exchange | owed? | closed by |
|---|---|---|
| `TOOLKIT_notes_2026-08-23` | complaint | `to-work/2026-08-24_REPLY_toolkit_notes` |
| `to-work/2026-08-24_REPLY_toolkit_notes` | — | `to-personal/2026-08-25_REPLY_harness_census` |
| `to-personal/2026-08-26_NOTE_ecosystem_and_gates` | **declares none** | closed on arrival; cited anyway by 0057 |
| `to-work/2026-08-27_REQUEST_harness_frame` | **yes, explicitly** | `to-personal/2026-08-27_REPLY_harness_frame`, by name |
| `to-personal/2026-08-27_REPLY_harness_frame` | declares none | — |

**Context packs: none on this rig.** The channel §6 calls the purpose-built one
has no instance here. Named as **unread**, not as empty.

**The bridge's obligation mechanism tracks files, not asks — and the last row is
the proof.** `2026-08-27_REPLY_harness_frame` declares no reply owed, so it is
closed by the letter of §6.1. It nonetheless puts three things to this side that
no artefact answers: what Governor's *decay detected* routes to (§5, its own
strongest finding), whether `0057`'s branch mechanism reaches the work rig or
amends the bridge's third exclusion (§0.2), and which of Warden or the Desk is
cheaper to finish (§1). The file that argues *the route that works is an
obligation with a named owner* carries three asks with no obligation attached.

**Owed a reply, and named as owed:** one correction back across the bridge. See
the running order §4.

**§2's corollary — the prompt was put.** The operator was asked what exists only
in memory. Answer, recorded because the asking is the mechanism: *"you've got
everything so far — but I'm hoping our session shakes out anything else we need
or haven't considered."* Nothing new entered the round at this stage.

## One reading taken outside the stages, because it was put to this thread

**0040 clause 1 against `relink.py`.** The clause is `accepted`. `relink.py`
carries **no source predicate of any kind** — nothing referencing 0040, a native
id, or an excluded source — so it cannot honour the clause. The investigation
§6b's eleven `claude-local-personal` auto-links at 0.92–0.96 stand as read.

**But the record can express the violation**, contrary to the premise this was
handed over with: `link_evidence.signal` is a closed enumeration,
`threads.source` is indexed alongside `account`, and `project_confidence`
separates `exact` / `evidence` / `manual`. The query exists; the reader does not.
Consequence carried into the running order §5a.

## Generated pairs

| pair | state |
|---|---|
| `DECISIONS.md` → `_decisions_map.md` | map reports 57 entries / 7 proposed — **agrees**. Its mtime is ~1h behind its source; mtimes on a mount are advisory, so this is **unresolved, not clean**. Settle with `python run.py decisions-map` on Windows. |
| `ARCHITECTURE.md` → `_architecture_shape.md` | header records *"Producing commit: 7324f69, **dirty at generation time**"*. A shape doc generated from a dirty tree records a shape no commit holds. |

Neither was regenerated here. Commands handed back, not run.

## What could not be read

1. **git, on Windows — unread.** Plain git against this repo from a sandbox is
   forbidden (`CLAUDE.md`). So: working-tree state, "clean and up to date with
   `origin/main`", and **which of the 20 drafts in `data/git_warden/` are
   spent** are all **unknown on this reading**. The operator's statement is
   recorded as his, unverified.

   **[AMENDED] — and the framing was wrong.** `git status` on the rig reports
   *"Your branch is ahead of `origin/main` by 2 commits."* The tree is otherwise
   clean, with only this note and the running order untracked. So the thread
   opened on *"clean and up to date with origin/main… any note that says 16
   commits ahead is stale"*, and the correct reading is **2 ahead, unpushed**.
   The direction of the correction matters less than the fact that the stale
   figure was replaced with a fresh assertion rather than with a reading — which
   is the exact move §2 exists to prevent, made in the prompt that cited §2.
   **Which of the 20 `git_warden` drafts are spent is still unread**; nothing
   run so far answers it.

2. **The live vault — unreachable.** `C:\Users\timps\Documents\chronicler_dev\chronicler.db`
   is not mounted into this session and `data/_vault_status.py` cannot run here.
   **10.42% is unknown on this reading** (0050) — it has a readable source in
   `docs/investigation/2026-08-27_intent-coverage-remeasure_claude_2-response.md`
   §6b, and it was not re-derived today.

   **[AMENDED] — read on the rig, and it holds exactly.** 1,330 threads, 336
   substantive, 65 evidence-linked, 19 project rows, newest
   `2026-08-22T20:00:13.289Z`. **`35 / 336 = 10.42%`.** Two things the
   investigation did not carry, now on record:

   | account | threads | substantive | +ev | |
   |---|---:|---:|---:|---:|
   | `claude-personal` | 39 | 32 | 6 | **18.8%** |
   | `claude-local-personal` | 97 | 71 | 11 | **15.5%** |
   | `gemini-personal` | 1,194 | 233 | 18 | **7.7%** |

   **The corpus is 90% Gemini by thread count and Gemini is the worst-linked
   source in it.** The estate's headline figure is therefore mostly a statement
   about Takeout, not about the record the thesis is actually about. And
   non-substantive threads carrying an `exact` link is now **18**, not §6b's 17
   — the exact join keeps landing where the metric cannot see it.

3. **[NEW, and it is live] The linker is disarmed by default on this rig.**
   `data\_vault_status.py` §2, with a clean shell:

   ```
   CHRONICLER_REGISTRY_PATH   = (unset)
   resolves to : C:\Users\timps\Documents\GitHub\L5GN\.intel_sync\project_registry.json
   exists      : False
   >> relink WILL BE SKIPPED by run_pipeline's has_registry() gate,
      and the chain will still finish green.
   ```

   Read out of the code rather than inferred: `db.resolve_registry_path()` falls
   back to `<github_root>/L5GN/.intel_sync/project_registry.json`, and **there is
   no `L5GN` repo** — the estate scan lists nine and none is that. `relink.py`
   would `SystemExit` loudly on a missing registry, but it is never reached,
   because `run_pipeline.has_registry()` skips the stage first. **The loud
   failure is pre-empted by a quiet skip.**

   This is the mechanical cause of `RUNBOOK_chronicler_refresh.md`'s finding 1
   — *"relink last ran at 2026-07-27T21:48:20Z… the linker has therefore never
   seen the 71 local-transcript threads."* The linker runs when a human
   remembers an environment variable. `INTENT.md` §5: *"Any rule that survives
   only because the operator remembers it is a defect awaiting its incident —
   and we have the receipt."* **This is the second receipt, in the subsystem the
   thesis depends on.**

4. **[AMENDED] The gate is GREEN** — 12 auditors, 81 testers, at `386d764`.
   Including `tester_registry_path`, which is hermetic by design: it asserts the
   *resolution order* and that no consumer keeps a local literal. **It does not
   assert that the resolved path exists on the host it runs on**, and nothing
   else does either. The gate is green and the linker is disarmed, at the same
   moment, correctly by every check's own contract.
5. **Work-side ruling logs** — behind the wall, above. Still unread.
6. **Context packs** — no instance on this rig, above. Still unread.
7. **The program/project axis** — does not exist; wanted by three stages.
8. **Which of the 20 `git_warden` drafts are spent** — still unread; needs
   `git log` against the message bodies, which nothing run so far does.

## The agenda, in one line

**Settle what a route is, on one rule, and let the mechanism that results tell
you which of the twenty in flight to touch — rather than choosing between them
by hand.** Scoped in `AGENDA_running_order_2026-08-28.md`.

**[AMENDED]** With the rig's readings in, that agenda has a cheaper first move
than it had this morning: **answer D9 — it is now answerable — and arm the
linker.** One sitting and one small round, and between them they unblock four
phases and the only stage that raises coverage.

---

**Nothing was ratified.** Seven proposed entries and one unappended draft sat in
front of this restart and none was stamped (§8, 0033).
