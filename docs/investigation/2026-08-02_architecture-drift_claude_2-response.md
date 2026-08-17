<!-- actioned: 2026-08-17 · A4 · commit=001d037 · architecture_census (DECISIONS 0030) independently reproduced A4 from AST alone: chronicler/review/core.py writes {projects, review_rulings, threads}, never review_queue -- see docs/_architecture_shape.md §4 -->
<!-- actioned: 2026-08-17 · A12 · commit=001d037 · architecture_census (DECISIONS 0030) independently reproduced A12 from schema introspection: render_log present in schema_frozen.sql, absent from schema.sql -- see docs/_architecture_shape.md §5 -->

# Response — ARCHITECTURE drift audit

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) ·
**Partner prompt:** `2026-08-02_architecture-drift_claude_1-prompt.md`

Investigation, per `docs/README.md` §4. Born frozen: never maintained, never
corrected, never graduates. The `actioned:` block above is the one exception and
it records consequences, never content — see the convention note at the end.

**Nothing here asserts current truth beyond 2026-08-02.** Every claim below was
checked against the working tree on that date and cites the file and line it was
checked at.

---

## Headline

`ARCHITECTURE.md` was last written at `c1c81ee` on **2026-07-18**. It cites
decisions 0002, 0004, 0005, 0006 and 0008, and none of the twenty entries
ratified since. That alone would be ordinary staleness.

The sharp part is that **three of its statements are not merely incomplete but
inverted** — they assert as as-built fact things the code does not do, and in two
cases they name the exact boundary a later decision says has never been crossed.
`docs/README.md` §1 rules that where a brief, report or archived doc disagrees
with the trinity, *the trinity wins*. A cold read resolving a conflict in
ARCHITECTURE's favour today would resolve it toward a system that has not existed
for a fortnight.

The single most consequential finding is not a drift at all. It is that **0008's
removal precondition has been satisfied since 2026-07-27 and nobody noticed** —
the write endpoint it was waiting for exists, is tested and is in daily use, and
`sync_back()` is still in the tree.

---

## 1. The document asserts a one-directional render that does not exist

`ARCHITECTURE.md` §5, verbatim:

> **Rendering is one-directional; the DB is the only write target.** … Because
> nothing edits the `.md`, there is nothing to sync back — the render is purely
> DB → file, one direction, forever.

That is 0008's *intent*, written in the present tense. In the tree:

- `chronicler/pipeline/render_md.py:185` — `def sync_back(conn)`, live.
- `render_md.py` docstring, lines 1–8 — *"This script therefore always runs
  `sync_back()` for every thread before `render()` for any thread."*
- `render_md.py:39` — the usage block still documents `--no-syncback` as the way
  to *opt out* of sync-back, which is only meaningful if sync-back is the default.

Sync-back is not merely present, it is **on by default**. The document does not
describe an aspiration; it states the aspiration as the shape of the system.

This is precisely the class of defect `auditor_doc_claims` exists to catch —
*"the estate's whole purpose is catching drift between what is said and what is
done, yet nothing checked the docs against the code"* (`auditors/auditor_doc_claims.py`,
docstring). The auditor checks numeric claims. It cannot check a prose claim
about a data flow, and this is what that gap looks like in practice.

## 2. 0008's precondition is satisfied and the gate was never walked through

0008 (2026-07-18) is explicit about ordering:

> `sync_back()` and the `render_log` 3-way base can be retired once the write
> endpoint (0007) exists to receive the rulings they used to carry — *order
> matters: the endpoint must exist before sync-back is removed, or the ~19
> pending rulings have nowhere to land.*

The endpoint now exists. `chronicler/review/` is built, has `tester_review` in
the gate, was walked on the work rig on 2026-07-28 (Part 5 of
`UAT_work_rig_solo_results.md` records real rulings taken through it), and has
since gained the estate routes, the search index and the docs board.

So the condition 0008 set opened somewhere around 2026-07-27, and the removal it
authorised has not been scheduled, briefed, or written down as available. The
hazard class behind the estate's only data-loss incident is still in the tree
with its own deprecation notice attached, waiting on a dependency that was
satisfied a week ago.

**This is the same shape as 0015.** Vocabulary was declared revivable "once the
dependency is satisfied", the dependency was satisfied, and it sat in the
standing backlog. A decision whose precondition is met but whose action is
unowned is invisible — nothing in the system watches for it.

## 3. 0002 was never implemented either, and says so

0002 decided to drop the `--no-syncback` belt from the full chain, keeping the
`render_log` base as the single structural guard. In the tree,
`chronicler/pipeline/run_pipeline.py:32–37` still describes the belt as the
current design:

> Every stage in the full chain WRITES the DB … render is therefore run
> DB->file only (`--no-syncback`) in the full chain

This is **not a violation.** 0002's own consequences say *"Must be implemented
and tested before the next full run against the live vault — until then the belt
stays, because the live behaviour is unchanged until the code changes."* The belt
staying is the documented interim state.

It is a finding because the interim has lasted two weeks across two vault
rebuilds with nothing tracking it, and because 0002 and 0008 are the same work:
0008 removes the thing 0002 was rebalancing. They should be executed together or
not at all, and neither has an owner.

## 4. §5 names `review_queue` as the endpoint's write target — the one table it may never write

`ARCHITECTURE.md` §5:

> human *rulings* go through a narrow write endpoint that writes only
> `review_queue` ruling columns directly to the DB

0024 states the opposite as a load-bearing invariant:

> `review_queue` is pipeline-owned: relink is its only writer, and the review
> endpoint's audited invariant (0007, `tester_review`) is that a human ruling
> touches only `threads.project_link` / `threads.project_confidence` plus an
> idempotent `projects` identity row — **never `review_queue`**.

The code agrees with 0024, not with ARCHITECTURE. In `chronicler/review/core.py`:

| line | statement | target |
|---|---|---|
| 550 | `INSERT INTO projects … ON CONFLICT DO UPDATE` | `projects` |
| 585 | `UPDATE threads SET project_link=?, project_confidence=?` | `threads` |
| 650 | `INSERT INTO review_rulings …` | `review_rulings` |

No write to `review_queue` anywhere in the endpoint.

This is the worst individual line in the document, because it is not vague — it
is specific, confident, and names precisely the boundary that has held since 0007
and that 0024 was written to avoid reopening. A future round reading ARCHITECTURE
as authoritative would conclude the boundary was always meant to be crossed.

*(For completeness: `review_queue` **is** written at `render_md.py:254`, by
sync-back, logging `manual_override` rows. That is the pipeline side and is
consistent with 0024. It is also the mechanism that logged the 359 bogus rows in
the 133-link incident.)*

## 5. The two-role mesh is now a three-mode system

§2 describes producers that scan and push, and one consumer that receives and
interprets. 0025, 0027 and 0028 created a third mode that the document has no
word for: **a local-only surface, on a producer, rendering that machine's own
material to the operator sitting in front of it**, bound to loopback, persisting
nothing, and — since 0028 — able to stage a working-tree change.

This is not a footnote. It is where every feature of the last week landed: the
knowledge base, the search index, the timeline, the docs board. `run.py review`
now serves on a machine with **neither** a vault **nor** an estate build
(`run.py`, the both-halves-absent branch), which is a shape §2's taxonomy cannot
express at all.

## 6. Three smaller inversions in the same document

**§3 — "Enforced by: auditors over `registry.SCANNERS`."** True of four auditors
(`cli_contract`, `readonly`, `stdlib`, `tool_contract`). Untrue of two:
`auditor_doc_claims` and `auditor_uat_stamp` audit **documents**, and neither
imports `registry`. The auditor surface has grown a second jurisdiction — the
docs — and the table still describes the first one only.

**§6 — "The three contracts."** There are now four in all but name. The
local-surface contract has harder invariants than the deposit contract: loopback
enforced structurally (0025), containment against configured roots with two
independent checks (0027), and stage-but-never-commit (0028). It is
tester-pinned in `tester_estate_data` and `tester_review_preflight`. It is not in
the list.

**§5 — "the DB is the only write target."** Superseded by 0028, which authorises
a `git mv` plus a prepended stamp inside `docs/`.

## 7. Two citations that have decayed

**§7 cites Layer C's embeddings as chronicler's dependency**, "currently inert
and intended to become load-bearing." 0018 then ruled persona/LLM inference into
a **separate, pluggable service, never inside the toolkit wall**, with embeddings
running there. Whether `chronicler/` should still carry the dependency at all is
now an open question the document does not know exists.

**§7 cites "~8% of substantive threads (see INTENT §2)."** `docs/INTENT.md:168`
marks that figure **`[CONFIRM]`** — its own author flagged it as unverified.
ARCHITECTURE cites it without the flag, which launders an open number into a
settled one. The figure also predates the fresh vault build (0017, executed
2026-07-27) and the golden apply's 343 threads, so it describes a corpus that no
longer exists.

## 8. A hypothesis that did not survive, recorded because it did not

I expected a live hazard here and did not find one. Recording it, because a
scary-sounding claim that survives into a report unchecked is worse than no
claim, and because the disconfirmation is itself useful.

**Hypothesis.** `render_log` is declared in `chronicler/pipeline/schema_frozen.sql:146`
but **not** in `schema.sql` (verified: `schema.sql` creates 8 tables,
`schema_frozen.sql` creates 11 — the extras are `path_scan_log`, `render_log`,
`meta`). `chronicler/pipeline/db.py:49` builds from `schema.sql`. The knight took
the fresh-build path on 2026-07-27 (0017). So a freshly built vault has no
`render_log`, therefore no base for any thread, therefore — if a missing base
were treated permissively — stale `.md` files surviving the rebuild would be read
as human edits. That is the 133-link clobber exactly.

**Disconfirmed, twice over.**

1. `render_md.py:79–85` carries `RENDER_LOG_DDL`, a self-contained
   `CREATE TABLE IF NOT EXISTS`, executed at the top of `load_render_bases()`
   (line 103) with the comment *"so render works before/after any migration."*
   The table is created on first use.
2. More importantly, `sync_back()` fails **closed**, not open:
   - line 222 — `if base is None: continue` (no render_log row → DB wins)
   - line 225 — `if base_norm is _NO_BASE: continue` (field absent from the
     snapshot → DB wins)

   The docstring at line 193 states the intent plainly: *"Without a base … we
   conservatively decline to override, so a stale pre-existing file can never
   clobber a fresh DB write."*

The guard is correct and it is structural. **The code is safer than the document
drift implied** — which is the opposite of the usual direction and worth saying
out loud.

The residual is small and real: the same DDL now lives in three places
(`schema.sql` omits it, `schema_frozen.sql` has it, `render_md.py` recreates it).
`db.py:150` already names DDL-in-two-places as a stated drift risk; this is the
third copy, and it is the one nobody would look for.

---

## Findings

Appended per the ruling on this investigation. Numbered for the `actioned:` block
above to reference.

| id | finding | evidence | severity |
|---|---|---|---|
| **A1** | §5 states the render is one-directional as as-built fact; `sync_back()` is live and on by default | `render_md.py:185`, docstring 1–8, usage line 39 | **doc asserts a property the code lacks** |
| **A2** | 0008's removal precondition (write endpoint exists) has been satisfied since ~2026-07-27; the removal is unowned and unscheduled | 0008 consequences; `chronicler/review/` built + `tester_review` green + walked 2026-07-28 | **decision with a met precondition and no owner** |
| **A3** | 0002's belt-drop never implemented; full chain still forces `--no-syncback` | `run_pipeline.py:32–37` | interim state, two weeks old, untracked |
| **A4** | §5 names `review_queue` as the endpoint's write target — the one table 0024 says it may never write | 0024; `review/core.py:550, 585, 650` | **inverted, and specific** |
| **A5** | §2's producer/consumer taxonomy has no term for the local-only surface, where every feature of the last week landed | 0025, 0027, 0028; `run.py` both-halves-absent branch | structural omission |
| **A6** | §3 attributes all enforcement to auditors over `registry.SCANNERS`; 2 of 6 audit documents instead | `auditor_doc_claims.py`, `auditor_uat_stamp.py` | incomplete |
| **A7** | §6's "three contracts" omits the local-surface contract, which has harder invariants than the deposit contract | 0025/0027/0028; `tester_estate_data`, `tester_review_preflight` | incomplete |
| **A8** | §5's "the DB is the only write target" superseded | 0028 | superseded |
| **A9** | §4's data-flow diagram contains no review endpoint, no deck, no board | `ARCHITECTURE.md` §4 | incomplete |
| **A10** | §7 describes embeddings as chronicler's dependency; 0018 moved inference outside the toolkit wall | 0018 | superseded |
| **A11** | §7 cites ~8% coverage without INTENT's own `[CONFIRM]` flag; figure predates the fresh vault build | `INTENT.md:168`; 0017 | laundered uncertainty |
| **A12** | `render_log` DDL exists in three places and is absent from the one a fresh build reads | `schema.sql` (8 tables) vs `schema_frozen.sql:146`; `db.py:49`, `:150`; `render_md.py:79` | drift risk, **not** a live hazard — see §8 |

### Not a finding

- **The `render_log` clobber hypothesis (§8).** Disconfirmed. `sync_back()` fails
  closed at `render_md.py:222` and `:225`. Recorded so a future read does not
  re-derive the fear and act on it.

### What this investigation deliberately did not do

- **No code changed.** Not the docstrings, not `schema.sql`, not ARCHITECTURE.
- **No ARCHITECTURE rewrite.** A2 and A4 need Tim's ruling before the document is
  rewritten around them — A2 in particular is a live decision to schedule, not a
  paragraph to edit.
- **No DECISIONS entry drafted.** A2 probably wants one; that is a separate act.
- **INTENT.md was read but not audited.** Its `[CONFIRM]` markers are its own
  open items and belong to a different pass.

---

## The acknowledgement stamp — proposed convention

Tim's ask: *"I think we might design a stamp that allows acknowledgement if
something has been actioned as a result of it."*

**The tension it has to survive.** §4 says investigations are *"never maintained,
never corrected, never graduates"* and *"no stamps — they're born frozen."* An
acknowledgement looks like maintenance.

**The resolution is the one §3 already makes for archived docs:** *the body is
evidence; do not edit it — say what's wrong with it in the stamp instead.* An
acknowledgement is not a correction of the body. It is a record **about** the
document — what it caused — and it lives above the title where the body is not.
§4's "no stamps" rule was written against the *archive* stamp, which is terminal
and asserts a disposition. This one asserts nothing about the investigation's
status; the investigation stays exactly where it is, forever.

**Proposed form**, at the very top, above the `# Title`:

```
<!-- actioned: YYYY-MM-DD · <finding-id> · <commit-sha|DECISIONS NNNN> · <one line: what was done> -->
```

Rules, in the spirit of §3 and §5:

1. **Append-only, one line per actioned finding.** Never edited, never removed —
   if an action is later reverted, that is another line, not a deletion.
2. **Strictly backwards-looking.** It records what *was* done. A line that says
   what *should* be done is the forward-look that killed the handoffs (§5) and is
   forbidden.
3. **Must name a resolvable anchor** — a commit sha in this repo, or a DECISIONS
   entry number. Same bar as the uat stamp's `commit=` and the `gate-frozen`
   marker: an unresolvable anchor is a violation, not a silent pass.
4. **The body is never touched.** Not the numbers, not the reasoning, not the
   disconfirmed hypothesis.
5. **An investigation with no actioned lines is normal, not a failure.** Most
   findings are recorded, not fixed. `<!-- actioned: (none yet) -->` is a
   complete and honest state.

**What it buys.** It closes the loop `investigation/` currently has no way to
close: today a reader can see what was found but not whether anything came of it,
and the answer lives only in a thread that has since evaporated. It is the same
provenance instinct as `toolkit_git_info` for scans and the uat stamp for
acceptance claims — an artifact asserting something should carry where it came
from, and this one carries where it *went*.

**What it does not buy, stated so nobody expects it.** It is not a task list, not
a status board, and not checkable by the gate as specified here. Making it
machine-checkable — resolving each anchor the way `auditor_uat_stamp` resolves
`commit=` — is a real option and a small auditor, but it is a separate decision
and should not be assumed by writing the stamp.
