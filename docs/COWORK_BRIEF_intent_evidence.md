# Cowork brief — intent evidence: connect the file inventory to the chat vault

**Origin:** design thread, 2026-07-21. Tim's observation: almost everything in
this estate was built by talking to an AI, so even where git history is missing,
the **conversation that started it** survives — and the file structure is the key
that unlocks it. This brief is Tier 1 of that idea: make the join work.

**Read first:** `chronicler/pipeline/build_inventory.py`,
`chronicler/pipeline/xref_filenames.py`,
`chronicler/pipeline/extract_path_mentions.py`, `docs/COWORK_REPORT_file_census.md`,
DECISIONS 0010 / 0012.

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report.
- **Evidence producers only.** This brief writes `link_evidence` rows and nothing
  else. It does **not** run `relink --apply`, does not write `project_link`, does
  not touch the reset. Evidence is not a decision.
- Live-vault work happens on the knight. Without a route to it, write exact
  runbooks and say plainly what is unrun — the evidence-collection runbook from
  the reconciliation pass is the model and it worked.
- Pipeline scripts run as `.venv/bin/python` (`docs/PRODUCER_PLAYBOOK.md` §10).

---

## The finding this brief acts on

Two evidence producers already exist and are already gated:

- **S4 `xref_filenames.py`** — joins the `attachments` table against each
  project's `file_inventory`. A unique basename hit is *"the strongest automatic
  link signal available"* (weight 1.0); a multi-hit splits 1/n; generic names are
  stoplisted.
- **S5 `extract_path_mentions.py`** — scans `messages.content` for filesystem
  paths and votes when a segment matches a project name or alias (weight 0.9),
  case- and separator-insensitively.

**S4 has never had anything to join against.** `build_inventory.py:177` resolves
each project as `GITHUB_ROOT_FS / root / entry["canonical_name"]` — the identical
folder-walk defect round 3 fixed in `build_registry.py` and found blocking
`build_activity.py`. That layout exists on no machine, so on the knight every
project resolves missing, `file_inventory` is empty, and the strongest automatic
signal in the system has been dark since the day it was written.

**Three instances of one bug.** Fix the class, not the instance.

**And the census is the replacement.** `file_inventory` wants
`{file_count, paths[], source_commit | source_signature}`; the file census
produces exactly that, per project, inside the deposit — which is also the only
route that respects the wall. Its non-git `source_signature` path already covers
the four folders with no git at all.

---

## Task 0 — FIRST: L5GN-Crystal-Spire's git position

**Do this before anything else, and do not rush it.** It is not part of the
evidence pipeline; it is the thing that must be settled while it is still cheap.

### The facts, established in the design thread

`L5GN-Crystal-Spire` **is** a git repo — 11 commits, HEAD `77045a5`
(2026-07-16, the hygiene sweep), 1,738 tracked files. `git_summary` and
`estate_status` both report `is_git: false` for it, and the file census reports
`true`. **The census is right and the older scanner is wrong** (see Task B2).

`world_graph.json`, `world2.json` and `canon_index.json` are **tracked and
already committed**. The repo's own audit reports —
`NAME_GAZETTEER_SCAN.md` and `DRIVE_ID_SCAN.md`, both untracked, both written in
that repo — establish that those files contain at least six and probably eight
real people's names (colleagues, one with a surname and a directory-style
formatting leak) and **33 genuine live Google Drive/Sheets file IDs**.

So the content Tim intended to scrub before it reached git is already in git
history.

### What this task does

**Establish, propose, and only then execute.** Nothing here is a judgment call
the thread gets to make alone.

1. **Facts first.** `git remote -v` — is there a remote at all, and has anything
   ever been pushed (`git log --branches --not --remotes` / reflog)? Which
   commits introduced each of the three files? Report before proposing.
2. **Back the repo up first**, whole, including `.git`, to a location outside
   the estate. A history rewrite with no backup is not a plan.
3. **The zero-cost mitigation, do it regardless of the ruling:** add the three
   world files to `.gitignore` and `git rm --cached` them, so the working tree
   stops adding exposure with every commit. State plainly in the report that this
   does **not** remove them from history.
4. **Present the two real options with their consequences**, for Tim to choose:
   - **`git filter-repo`** to purge those blobs — keeps the 11 commits, surgical,
     and every commit hash after the first affected one changes.
   - **Scrub, then fresh init** (`rm -rf .git && git init`, one clean initial
     commit) — loses 11 commits of history, gains certainty. Cheapest to reason
     about, and the repo's history is 5 days old.

   Recommend one. Note that **both are safe and easy today precisely because
   nothing has been pushed**, and neither is either of those things after a push.
5. **Execute only the ratified option.** Never push. Never add a remote.

### Explicitly not in scope

**The scrub itself.** Removing the real names and Drive IDs from the corpus is a
content task with its own method — `SCRUB_MAP`, `HYGIENE_SWEEP.md` and the two
scan reports are Tim's existing apparatus for it and they are further along than
anything this brief could invent in a session. Do not start it, do not
half-start it.

### One knock-on to note, not to fix

Untracking the world files changes Crystal Spire's census: its working set
shrinks and its at-risk count rises (untracked-not-ignored → ignored). That is
correct behaviour, and it means the `file_inventory` built in Task A will no
longer carry those basenames for S4 to match on. Note the effect; do not
compensate for it.

---

## Task A — BUILD: `build_inventory` reads deposited census, not disk

The core of the brief.

1. Refactor project resolution to read the **deposited estate** — the same source
   `build_registry` uses after round 3's Task C. Do not invent a second
   discovery path; if `build_registry` already resolves a project to its deposit,
   reuse that.
2. Populate `file_inventory` from the census: `paths` from the working-set file
   list, `file_count` from the summary.
3. Preserve `source_commit` (git HEAD) where the deposit carries it, and
   `source_signature` where it does not — the skip-if-unchanged behaviour must
   survive, and it is what makes the non-git projects work.
4. Keep a **local-disk fallback** for a producer running against its own working
   tree (the `LOCAL_ESTATE_JSON` pattern `build_registry` already uses). On the
   knight, deposits win.

**The truncation question — decide it explicitly and say why.** The census caps
its per-file list at 2000 with `truncated: true`. `L5GN-Castle` exceeds that. A
truncated inventory means S4 silently cannot match the missing files. Options:
raise the cap for inventory purposes, carry a basenames-only list beyond the cap
(cheap — basenames are all S4 needs), or accept the cap and report the blind spot
per project. **Recommend one and implement it; do not leave it implicit.**

Cover with a hermetic tester: a synthetic deposit in, a correct `file_inventory`
out, including a non-git project and a truncated one.

---

## Task B — REPORT: audit the folder-walk class

Find every remaining place that resolves a project by walking
`<root>/<L5GN|MCF>/<canonical_name>` or equivalent. Known: `build_activity.py`,
`build_vocabulary.py`. Report each with its line number and whether the census
now supplies what it needs.

### B2 — the `is_git` contradiction

`common.is_git_repo` is `(path / ".git").exists()`, and `L5GN-Crystal-Spire` has
a `.git` directory with 11 commits — yet `git_summary` and `estate_status` report
`is_git: false` for it, while `file_census` reports `true`. `estate_status` says
7 repos where there are at least 8.

Find the cause. It is not "the folder isn't a repo" — that has been checked
directly. Report the mechanism, fix it if the fix is obvious, and say which other
projects the same bug has misreported (`test_folder` is the other disputed one).
The registry takes `first_seen` / `last_activity` from these git facts, so a
project silently classed as non-git loses its dates.

**Fix `build_activity.py` if — and only if — it is small.** Round 3 judged the
refactor "small, contained" and noted the deposits already carry
`first_commit_date` / `latest_date`. If it holds up, S3 activity windows become
real for the first time, which unblocks the time-plausibility signal S5 scoring
wants and the vocabulary work parked twice. If it is bigger than it looked, say
so and stop — a second task done badly costs more than a first task done well.

---

## Task C — BUILD then REPORT: run S4 and report what fires

With inventories populated, run `xref_filenames.py` **dry-run** (its default).

Report:

- evidence rows it *would* write, by project and by weight class (unique 1.0,
  multi-hit 1/n);
- the stoplist's effect — how many basenames were suppressed as generic, and
  whether the list needs extending for this estate (`main.py`, `README.md`,
  `handover_schema.py` appears in three projects, `citadel_archetypes.json` in
  five);
- **projects that gain their first evidence ever.** `L5GN-Archive`,
  `L5GN-Crystal-Spire` and `L5GN-server-hub-iso` have little or no usable git
  history, which is why they are thin in the registry. Filename evidence is the
  route to linking them, and this is the moment it becomes possible.

Then apply, if and only if the dry-run is clean and Tim rules GO. `link_evidence`
is additive and idempotent per producer, so this is a safe write — but it is
still a write, and `run.py backup` comes first.

---

## Task D — BUILD then REPORT: run S5 and report what fires

Same shape for `extract_path_mentions.py`. Report the vote distribution, the
watermark behaviour on a second run (it must add nothing), and any project whose
name is too generic to match safely.

**The two producers must not double-count.** A thread that mentions
`L5GN-Crystal-Spire\world_graph.json` produces both a path mention and a filename
hit. Report how relink's scorer treats two evidence rows for one thread/project —
whether they compound, cap, or are deduplicated — and flag it if the answer is
"compound", because that would let one sentence outvote three separate sources.

---

## Task E — REPORT: the origin query

The actual ask: *where did this project start?*

For each project, the **earliest** thread carrying evidence above a confidence
floor, with its title, date, account and the evidence that links it.
`project_trail` already does newest-first per project; this is that, inverted,
with a floor.

Deliver a table: project · earliest evidenced thread · date · account · signal ·
confidence. Plus the ones with **no** evidence at any date — an empty row is a
finding, not a gap in the report.

**Two caveats to state in the output, not bury:**

- **File mtime is weak evidence of origin.** A copy, a zip extraction or a folder
  move resets it, and this estate has done all three. The chat timestamp is the
  anchor; file dates corroborate, never lead.
- **Earliest evidenced ≠ where the idea started.** It is the earliest *surviving,
  ingested, matched* mention. Threads predating the vault's coverage, or in an
  account never exported, cannot appear. Say so per row where the earliest hit is
  suspiciously late.

This task **reports**. Deciding that a thread is a project's origin is Tim's
call, and it goes in the registry only after he says so.

---

## Task F — REPORT: harvest the delve index — the estate's first labelled dataset

Every link this system produces has been an unvalidated heuristic checked by eye.
`L5GN-Crystal-Spire` can change that.

Its world was **forged from Tim's chat corpus**: world keys are
`delve_<era>_<NNNN>_f<N>`, and its own audit report describes delve 92 as *"a
136-floor registry/manifest **conversation**"*. A delve is a thread; a floor is a
chunk of one. The embedded manifests carry the lineage explicitly — e.g.
`L5GN_Scratchpad|FoundingTheEmpireVol01|1|<driveID>` — and `L5GN-Archive` holds
the matching `raw_history_txt/L5GN_SAGA_STITCHED_VOLUME*.txt` volumes.

**Harvest the mapping** — delve → era → volume → Drive ID, plus the ten
`ERA_DIGEST_*.md` era definitions — into
`docs/investigation/2026-07-21_crystal-spire-delve-index_2-response.md`.

**Then score the producers against it.** Where S4 or S5 links a thread to
`crystal-spire`, does the delve index agree? Report precision and recall, on real
data, for the first time in this estate's life.

**Read-only, and mind the boundary.** Take structure — delve ids, era names,
volume names, counts. Do **not** copy floor content into `docs/`: the corpus
contains real colleagues' names and live Drive IDs (Task 0). Stay out of
`modules_v3/` entirely. If the index cannot be built without quoting content,
stop and report that instead.

**Two caveats to carry into the scoring:**

- The world was forged from *stitched saga volumes* (Drive-hosted scratchpad
  documents). The vault holds *Claude threads*. They are drawn from the same
  history but may not be the same records — establish whether a delve maps to a
  vault thread at all before treating disagreement as a producer error.
- The Linux sandbox mount **silently truncates files above ~12–13MB**, which both
  `world_graph.json` (13.4MB) and `world2.json` (12.5MB) exceed. Crystal Spire's
  own scans discovered this independently and worked around it host-side. Any
  count taken through the mount is wrong; say which side of the boundary each
  number came from.

---

## Explicitly not in scope

- `relink --apply`, any `project_link` write, the DECISIONS 0011 reset.
- Tier 2 (a new producer scanning message *content* for basenames rather than
  attachments). It is the natural next brief and depends on this one landing.
- Vocabulary (S2). Task B may unblock it; building it is a separate decision.

---

## Suggested order

**0 → A → B → C → D → E → F.**

Task 0 first and on its own — it is unrelated to the rest and it is the only item
that gets cheaper by being done sooner. Then A gates everything downstream.

If the budget runs short, **0, A and C are a successful session** — the git
position settled, and the join working once with numbers. F is the most
interesting task here and the most skippable; it validates work that must exist
first.

---

## UAT — acceptance checks (Tim walks these)

- **A:** `file_inventory` exists for every deposited project, `file_count`
  matches the census summary, and the four non-git projects have a
  `source_signature` rather than an empty block.
- **A (truncation):** whatever was decided for Castle is visible in the output —
  either the full basename set, or an explicit statement of what is missing.
- **C:** the S4 dry-run names threads Tim recognises as being about the project
  it linked them to. Spot-check three; a wrong one is worth more than ten right.
- **D:** a second S5 run adds nothing (the watermark holds).
- **E:** for two or three projects Tim knows well, the earliest evidenced thread
  is plausibly the one where it started — or the report says why it can't be.
- **0:** the Crystal Spire backup exists and opens; the three world files no
  longer appear in `git status` as tracked; whichever history option was ratified
  has been applied and `git log` shows what Tim expects. No remote exists.
- **F:** the delve index names eras Tim recognises, and the precision/recall
  numbers are computed from a stated side of the mount boundary. No floor content
  was copied into `docs/`.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report: tasks green vs pending; the truncation decision and its reasoning; the
folder-walk audit; the S4 and S5 dry-run tables; the origin table with its empty
rows; and the **UAT walk-list**.

Write the report as `docs/COWORK_REPORT_intent_evidence.md` and the walk-sheet as
`docs/UAT_intent_evidence.md`. The results log needs a uat stamp or the gate
refuses the commit.

Nothing commits. Everything staged, for Tim's review.
