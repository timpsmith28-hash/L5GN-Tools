# Cowork brief — the record moves to conversation grain, and the join it already has gets read

**Where you are:** `C:\Users\timps\Documents\GitHub\L5GN-Tools`, host
`LucasGoonPC`.

**Read before Task 1, in this order:** `CLAUDE.md` at the repo root — it is the
map and it carries the environment hazards; then this brief in full; then
`docs/UAT_conversation_grain.md`, which is the walk-sheet of record and is not a
summary of what follows; then `docs/CONVENTION_conversation_map.md`, which
governs the artefact every task below writes into.

**Draft-status:** written 2026-08-28, from the design thread of 2026-08-27/28.
Every "already exists" claim below was checked against the tree while drafting
and the check is named at each task. **Re-verify them as the round's first act.**
Two consecutive findings in the originating thread came from instruments
reporting something other than what happened — including two in the drafter's
own measurement code, corrected mid-thread.

---

## Origin

`docs/investigation/2026-08-27_intent-coverage-remeasure_claude_2-response.md`
§6d recorded a proposed rework and left six questions open. The design thread of
2026-08-27/28 answered five, measured three new facts, and found that most of
what the rework needs is already built.

**What the thread measured, and that this round rests on:**

1. **Local conversation storage is restored** when the cloud setting is switched
   off at project level. Verified on the test conversation `Local storage test`
   (`local_c36655b7-fc00-4453-9a48-2639949b1a74`): the sidecar **and** its
   transcript both landed — `…\local_c36655b7-…\audit.jsonl`, 19 records
   carrying the full exchange. §10d-i had written this off.
2. **The sidecar join is accurate.** `userSelectedFolders` was compared against
   the operator's hand-curated sheet, which he assigned from what each
   conversation was *about* rather than from the Cowork UI — so it is
   independent ground truth. Of 49 conversations present in both:
   **35 agree, 0 disagree, 14 have an empty `userSelectedFolders`.**
   The misses are empty arrays, not wrong answers.
3. **The Claude export is not stale — it is split.** The export of
   2026-08-27T22:37:22Z returned `projects-000.zip` current to within an hour
   (`L5GN Tools Mobile`, `updated_at 2026-08-27T21:36:17`) and a
   `conversations.json` byte-identical to the two before it: 51,367,337 bytes,
   39 conversations, 922 messages, newest `updated_at 2026-07-20T13:41:31`.
   The pipeline works; Cowork conversations never enter that corpus.
   **No cadence of requesting an export closes the gap.**
4. **The export has no native conversation→project join at all.** Zero of 39
   conversations carry a project reference; the keys are `uuid, name, summary,
   created_at, updated_at, account, chat_messages`.

**The operator's rulings from that thread**, which this brief implements rather
than re-opens: the target is conversation→**code**, reached in stages, with
commit-message cross-reference as a later mechanism; the sync is **on demand for
the first iteration**; the `.md` export is a **convenience, not a route**;
`Work_Bridge` gets **its own record kind**; Gemini is **demoted**.

## Precondition — hard

1. `grep -c "^## 00" docs/DECISIONS.md` → **57**. Anything else and this brief
   was written against a different tree.
2. **`data/git_warden/pipeline_stage_encoding-1.msg` is applied and committed.**
   It is two arguments and it repairs the chain's only diagnostic surface
   (§6c: a stage failing after one non-`cp1252` byte reports its exit code with
   no tail at all). Applying it during a long run rather than before one is how
   this round loses its own failure diagnostics.
3. `python data\_vault_status.py` has been run on `LucasGoonPC` in this sitting
   and its INTENT figure recorded in the report. The thread that produced this
   brief could not run it — the sandbox has no configured host — so **every
   coverage number quoted here is second-hand until that command is run.**
   Expected at drafting: `35 / 336 = 10.42%`.

## Depends on — this repo's rulings

- **0012** — the registry's three tiers and id scheme, which `project_id`
  resolves against.
- **0028** clause 3 — a commit is a human act; a local surface may stage, never
  commit.
- **0030** — shape is generated, rationale is authored; a generated artefact is
  never hand-edited.
- **0033** — propose, ratify, execute.
- **0038** — conversation, session and thread are three distinct things. Clause 3
  (`threads` is a *storage* entity, not a source entity) is the ruling this whole
  round applies. **Clause 4 is accepted and unimplemented** — see Task 4.
- **0039** clauses 1-2 — the ratified map is named from the machine's declared
  estate; a run does not mix estates.
- **0040** — where a source carries a stable conversation id, a curated map is
  the join of record. Clauses 1, 2 and 4 are load-bearing here.
- **0045** — verification reports and never repairs.
- **0046** — recency resolution through one shared resolver; a superseding row
  says so; undo is an append.
- **0048** clause 4 — a check that cannot fail trains the eye past it.
- **0050** — a source declares its own staleness; unreachable reads as unknown,
  never as fresh.
- **0051** — containment by construction.
- **0052** clause 4 — an environment rule belongs to the environment.

## Ratify before code

This round needs one ruling that does not exist: **the provenance vocabulary is
closed and refused at write** (Task 3). Draft it with `decision-scribe` as
`proposed`; **Task 3 is drafted, staged and left uncommitted until it binds.**
Tasks 1, 2, 4, 5 and 6 do not depend on it and may be built now.

Ratification is a re-read by the operator on a different day. **This round
ratifies nothing**, including the map rows it produces — those are candidates for
the Curator tab, exactly as `curator_ratify` already requires.

## Deliverable

The Cowork sidecar becomes a declared, provenance-stamped input to the
conversation map that already exists, and the estate gains a coverage figure
computed at conversation grain that is reported **alongside** the thread-grain
figure rather than replacing it. The round is finished when
`config/personal_conversation_map.tsv` carries a ratifiable candidate row for
every Cowork conversation whose sidecar names a project folder, every row's
`notes` opens with a `[provenance:...]` tag naming which mechanism produced it,
and one command prints both the thread-grain and the conversation-grain figure
from the same vault in the same run so the two can be compared without anybody
recomputing either by hand.

---

## The thing this round exists to prevent

**A stronger join being invisible to the scoreboard that judges it.**

§10e is the shape: reading the sidecar would take substantive threads carrying a
project link from 27 to roughly 65 — at `project_confidence='exact'`, which is
*stronger* than `evidence` and which INTENT's numerator does not count. Measured
after the refresh, exactly 4 substantive threads sit at `exact` while 18
non-substantive ones do, so the best link type in the estate is invisible twice
over: excluded by confidence and too short to count.

So the target property is not "coverage goes up". It is: **the record says how
each link was established, and the measure can see every mechanism it holds.**
A round that raised the figure without that is the flattering half of the truth
INTENT §2 exists to correct.

## Working rules

**Ask git for anything about git.** Never run plain git against the mounted
Windows repo from a sandbox. `git bundle verify` needs a repository context.

**A sandbox mount serves stale, byte-truncated content deterministically and
without error.** A second read confirms a false answer rather than catching it.
Hash on Windows.

**Normalise line endings before concluding anything changed.** `.gitattributes`
sets `* text=auto eol=lf`, so this tree is LF throughout; the hazard is at the
boundaries.

**Check your matcher before you trust its agreement.** The measurement this
round rests on was wrong twice before it was right — once from operator
precedence in a substring test that manufactured agreement, once from POSIX
`os.path.basename` declining to split Windows backslashes and manufacturing
disagreement. **Any comparison that reports perfect agreement or perfect
disagreement is a matcher to inspect before it is a result to report.**

**Read-only until the writer.** Discovery, parsing and candidate generation
touch no transcript, no database and no ratified map. Only `curator_ratify`
writes, through its existing validation.

**Stage, hand back, never commit** (0028 clause 3). Draft each commit message to
`data/git_warden/<slug>-<n>.msg` and hand back the exact `git commit -F` command
with its `git add` line. `data/` is gitignored wholesale — confirm with
`git check-ignore -v data/git_warden`.

**Run `verify.py` in a shell with no `CHRONICLER_*` variables set.** The gate is
not hermetic against them: with `CHRONICLER_HOME` and `CHRONICLER_DB_PATH`
exported, `tester_census` reports 7 issues and `tester_review_preflight` 3.
Reproduced on two machines. The pre-commit hook runs `verify.py`, so a commit
from the working shell goes red for reasons unrelated to the commit.

**A partial round is a real result.** If a stop condition trips, stop, report
where, and hand back what is done.

---

## Task 1 ▸ a sidecar reader

**Checked while drafting:** `chronicler/pipeline/local_transcripts.py` exists and
owns discovery, parsing and grouping for the Cowork store;
`chronicler/pipeline/bootstrap_conversation_map.py` reuses it and says so in its
docstring (*"does not write a second discoverer"*). Re-verify both.

Add a reader that extracts, per Cowork conversation, from its
`local_<uuid>.json` sidecar and nothing else:

`conversation_id` (the `sessionId` **field**, not the filename), `title`,
`cliSessionId`, `userSelectedFolders`, `resolvedFolderKinds`, `createdAt`,
`lastActivityAt`.

**Key on the `sessionId` field, never on the filename.** The test conversation is
`local_c36655b7fc0044539a482639949b1a74.json` — 32 hex, no dashes — while its
`sessionId` is `local_c36655b7-fc00-4453-9a48-2639949b1a74`. Every one of the 62
sidecars measured on 2026-08-27 used the dashed form in the filename. **The
filename shape is not stable and a matcher keyed on it silently misses
conversations.** Count both shapes and report the split.

**Never parse the whole sidecar.** It is ~600 lines for a two-message
conversation, overwhelmingly embedded MCP tool schemas. Read named fields only.

**Reuse `local_transcripts.py` for store location.** Do not write a second
discoverer, and do not read the MSIX-virtualised `%APPDATA%` view — the packaged
path is the one `machines.json` warns about.

**Lands:** a sidecar reader in `chronicler/pipeline/`, and a tester registered in
`verify.py` covering both filename shapes and the empty-`userSelectedFolders`
case.

## Task 2 ▸ candidate rows from the sidecar

**Checked while drafting:** `config/personal_conversation_map.tsv` exists with
the five ratified columns and **4 rows**. `curator_ratify` is the one writer and
refuses a row whose `notes` lacks a `[provenance:...]` tag.
`bootstrap_conversation_map.py` produces a candidate map for human ratification
and never applies it. Re-verify all three.

Generate candidate rows from Task 1's reader, in the **candidate** shape the
Curator tab already consumes — not the ratified shape, and not written directly
into the ratified file.

Resolution rules, and they are the round's substance:

- **One non-generic folder → one candidate**, `project_id` resolved against the
  registry.
- **Generic folders are not project signal.** `Documents`, `Downloads`,
  `Desktop`, `GitHub`, `Backups`, `scratch`, `vendors` and the user root are
  containers, not projects. In the measured sample, 26 of 35 agreeing
  conversations named `…\GitHub` alongside the real repo.
- **Empty `userSelectedFolders` produces no row.** Not a low-confidence row, not
  a guess. 14 of 49 in the sample. **An abstention is the correct output and
  must be counted, not hidden** (INTENT §5).
- **More than one non-generic folder is `AMBIGUOUS`**, carried to the Curator tab
  with every candidate shown. It is rare — 1 of 35 — and the test conversation
  proves it happens across the estate wall: `local_c36655b7` names both
  `…\GitHub\L5GN-Tools` and `…\WizForge\Work_Bridge`.
- **A folder resolving to `Work_Bridge` is its own record kind**, not an
  L5GN-Tools link and not a work-estate link. `Work_Bridge` is the permitted
  meeting point between the two task forces, governed by its own README. Emit it
  as its own kind; **do not fold it into either estate.**

**Lands:** a candidate map generator, its tester, and a candidate TSV under
`data/`. **Nothing is written to `config/personal_conversation_map.tsv` by this
round** — ratification is the operator's act at the Curator tab.

## Task 3 ▸ the provenance vocabulary, closed and refused at write

**Held until the ruling drafted under *Ratify before code* binds. Draft, stage,
hand back; do not commit.**

**Checked while drafting:** provenance is enforced today as a mandatory
`[provenance:...]` tag at the head of `notes`, parsed through one shared parser,
chosen over a column deliberately (0046: *"a status column would have needed a
migration, a notes tag does not"*). `CONVENTION_conversation_map.md` §5 states
the mechanism. Re-verify.

Close the vocabulary. Today the tag's payload is free text
(`machine-matched:pass-1`). Constrain it to a declared set — at minimum
`sidecar`, `first-message`, `cwd`, `human` — and **refuse a write outside it**
rather than accepting and documenting against it.

The work task force's position, offered as reasoning rather than authority
(`Work_Bridge/to-personal/2026-08-27_REPLY_harness_frame.md` §4): *one store,
closed record kinds, refusal at write, and explicit null rather than absent*,
with *"a field that is structurally always null is a schema lie, not an optional
field."* Their `sf-data-service` card 7 walk-sheet rules the same way in three
checks. **Cite it; do not restate it** — and note in the report that card 7 was
unbuilt when they wrote it, so it is a position taken, not a result reported.

**Why this matters more than it looks.** The measured mechanisms are not equally
trustworthy and today's schema flattens them: the sidecar was 35/35 with honest
abstentions; title-plus-first-message on the export corpus was 16 unique, 4
ambiguous and 19 silent out of 39; `relink`'s alias scoring produced threads at
`adjusted = 1.000` for the wrong project on nine compounding aliases, saved only
by a tie-break. **These are different epistemic claims and one confidence column
cannot hold them.**

**Lands:** a closed vocabulary in the shared parser, refusal at the writer, its
tester, and an amendment to `CONVENTION_conversation_map.md` §5.

## Task 4 ▸ 0038 clause 4, which was accepted and never implemented

**Checked while drafting:** 0038 is `accepted`, dated 2026-08-11. Clause 4 reads
*"The map's key column is **renamed `conversation_id`**… K1, K2 and K4 read it
and change together."* Both maps still carry `session_id` as their first column.
Re-verify with `head -1` on each.

Implement it. Rename the column in both maps, and change every reader in the
same commit.

**This is a schema change to a ratified artefact**, performed once and
explicitly, exactly as clause 4 describes. Do not do it as a tidy-up riding with
another task.

**If the rename would break a consumer this brief has not named → stop and
report.** The clause names K1, K2 and K4; the tree may have grown others.

**Lands:** both map headers, every consumer, one commit, and a report line naming
every file that changed.

## Task 5 ▸ fingerprint parity for the personal map

**Checked while drafting:** `config/mcf_conversation_map.tsv.sha256` exists;
**there is no `personal_conversation_map.tsv.sha256`.**
`CONVENTION_conversation_map.md` §1 already records this as *maps carrying a
committed fingerprint: 1 of 2* and *maps covered by an auditor: 1 of 2*.
Re-verify by listing `config/*.sha256`.

Give the personal map the fingerprint 0040 clause 4 requires, and extend the
existing auditor to cover it. **Do not write a second auditor.**

The round is about to make this map the estate's primary join. A map that grows
from 4 rows to dozens without the check its sibling already has is the
convention's own §1 gap widening under load.

**Lands:** `config/personal_conversation_map.tsv.sha256`, an extended auditor,
its tester.

## Task 6 ▸ both figures, one command, one run

**Checked while drafting:** `data/_vault_status.py` exists and prints the INTENT
figure, the by-confidence breakdown and the by-account table. `data/` is
gitignored wholesale, so the script is **untracked** — named as debt #5 in
`RUNBOOK_chronicler_refresh.md`. Re-verify it is still there.

Produce a tracked command that prints, from one vault in one run:

- **thread grain** — INTENT §2's definition unchanged: substantive threads
  (≥4 messages) at `project_confidence='evidence'`, over substantive threads.
- **conversation grain** — the same question asked of conversations: sessions
  folded into their conversation per 0038, sub-agent sessions folded into their
  parent, CLI sessions left as themselves.
- **the excluded set, explicitly counted** — every record carrying no native
  conversation identity, which under 0038 clause 1 is the whole Gemini-personal
  corpus. **Stated as a number beside the figure, never dropped.**
- **a breakdown by provenance mechanism**, once Task 3 binds.

**The denominator must be defined so that regrouping cannot manufacture a rise.**
This is the round's most likely way to produce a comfortable lie: 844 of
Gemini-personal's threads hold exactly two messages, so folding the corpus to
conversations shrinks the denominator and lifts the percentage for free. Fix the
denominator on a property regrouping does not change, state the definition in the
command's own output, and report both figures side by side.

**Do not edit `INTENT.md` or `ARCHITECTURE.md`.** §7 of the originating
investigation holds a drafted §2 replacement at 10.4% and notes ARCHITECTURE §7's
"~8%" goes stale in the same act. Both move together or neither does, and that is
the operator's call.

**Lands:** a tracked subcommand, its tester, and the two figures recorded in the
report.

---

## The one deliberate widening, named

**A sidecar is configuration, and this round makes it evidence.**

`ingest_local_transcripts` ruling 2 concluded that *"Cowork sessions never get a
direct link — their cwd encodes the session's own outputs dir, no project
signal."* That is true of the **session's** `cwd` and correctly observed. It is
false of the **conversation's** sidecar one level up, which names the repository
outright. 0038 is why the two were confused, and 0040 is why the sidecar
qualifies as a join of record.

Taken knowingly, bounded three ways: only the named fields are read, never the
file; the sidecar produces **candidates for ratification**, never applied links;
and where it is silent it produces nothing rather than a weak guess.

## Explicitly out of scope

- **Any schedule.** On demand for the first iteration, by the operator's ruling.
  A daily catch-up is a later decision and it must argue against 0036 and 0051
  — *"a periodic mirror is a sync with extra steps"* — rather than assume it.
- **The `.md` export.** Ruled a convenience, not a route. Building it here would
  make this round about a surface.
- **Rewriting the vault, or any schema change beyond Task 4's ratified rename.**
  The store did not break; the code around it did.
- **Gemini.** Demoted. It appears in Task 6 only as an explicitly counted
  exclusion.
- **The mobile throne.** Its conversations are outside the record by
  construction — cloud-on suppresses the local write, and Cowork conversations
  never enter the export. Recording that is a later decision; **do not build
  around it here.**
- **Re-running `relink`, `xref_filenames` or `extract_path_mentions`.** They
  write. Detection and action are different programs (INTENT §5).
- **Fixing `resolve_registry_path()`.** It currently resolves to a path that
  does not exist, so `has_registry()` is false and the skip is visible — the
  loud failure, not the silent one. Its real fix is a round of its own.
- **`verify.py`'s hermeticity.** Named in the working rules as a hazard to work
  around, not a defect to fix here.
- **Ratifying anything**, including the map rows this round generates.

## Stop conditions

- `grep -c "^## 00" docs/DECISIONS.md` does not return 57 → **stop.**
- `pipeline_stage_encoding-1.msg` is still unapplied → **stop.** Do not start a
  long run with the diagnostic surface broken.
- **A comparison reports 100% agreement or 100% disagreement** → **stop and
  inspect the matcher** before recording the result. This happened twice while
  drafting.
- The sidecar reader keys on the filename rather than the `sessionId` field →
  **stop.** That is the defect Task 1 exists to prevent, reintroduced.
- A candidate row is written directly into `config/personal_conversation_map.tsv`
  → **stop.** Ratification is the operator's act.
- An empty `userSelectedFolders` produces a row of any confidence → **stop.**
  Abstention is the correct output.
- A `Work_Bridge` folder is folded into either estate's links → **stop.**
- Task 4's rename would leave one consumer reading `session_id` and another
  `conversation_id` → **stop.** Two readers of one key is the collision 0038
  exists to end.
- The conversation-grain figure rises while the excluded count is not reported
  beside it → **stop.** That is the flattering figure, rebuilt.
- You find yourself designing around a governance question rather than answering
  it → **stop.** That is what sank the mesh framing.

## The round's falsifier

**Does the sidecar join hold at full scale?**

The measurement is 35 of 35 with 14 honest abstentions, on 49 conversations
joined by title against a sheet the operator assigned from what each conversation
was about. If, across the whole Cowork corpus, the disagreement rate against
ratified rows is materially above zero — or if the abstention rate is high enough
that the map stays sparse — then the sidecar is a *signal* and not a *join of
record*, 0040 does not apply to it, and the design goes back to scoring with all
of §10d-iii's problems intact.

**Write the answer down before deciding what it means.** A disagreement rate
above zero is the more informative outcome and must not be smoothed away: the
whole argument for conversation grain is that this join is deterministic.

## Open questions this round does not close

Recorded so they are not answered by accident.

1. **What the measure becomes.** Q5 of §6d, deliberately left open by the
   operator. Task 6 produces both figures precisely so the comparison exists
   before the metric is chosen. **Choosing it is a later decision and this round
   may not make it.**
2. **Whether `Work_Bridge` surfacing unanswered exchanges makes it a queue.** Its
   README says *"Nothing here is a queue, an inbox, or a thing anyone is expected
   to poll"*, while also saying *"a reply is owed."* Task 2 emits the record kind;
   it does **not** build the obligation view, and the argument has to be made in a
   ruling before anything does.
3. **Who owns the currency of an ingested copy.** The work task force names five
   instances of a copy whose currency is asserted by convention rather than by
   anything that looks; §10d-i is a sixth (the capture reported success for
   thirteen days against a store that had stopped) and an ingested `Work_Bridge`
   is a seventh. **No staff member owns this class.**
4. **Whether the throne is visible to any export path.** `L5GN-Mobile-Throne` is
   absent from the export's nine projects. Whether it postdates the snapshot or
   Cowork spaces are simply not claude.ai projects is undetermined; a second
   export distinguishes them.
5. **Whether the work account carries the local-storage setting at all.**
   Unverified, on the other rig, and it changes what the work side can capture.

## Reporting

`docs/COWORK_REPORT_conversation_grain.md`. It must record:

1. **The vault figure re-derived on `LucasGoonPC`** at the start of the round,
   and again at the end — thread grain and conversation grain, with the excluded
   count beside each.
2. **The sidecar filename split** — how many `local_<dashed-uuid>.json` against
   how many 32-hex, and whether any conversation was reachable only by the
   `sessionId` field.
3. **The candidate table**: rows emitted, abstentions, ambiguous, and
   `Work_Bridge` rows, each as a count. **The abstention count is a result, not a
   shortfall.**
4. **The falsifier's answer** — the disagreement rate against ratified rows,
   stated before it is interpreted.
5. **Every file Task 4's rename touched**, by name.
6. **Whether Task 3 was committed or held**, and against which ruling number.
7. **Every stop condition that tripped**, and what was left undone.
8. **Anything this brief got wrong about the tree.** The draft-status note says
   the claims were checked; where one was stale by the time you read it, that is
   the most valuable line in the report.
