<!-- gate-frozen: commit=a202ba0 -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_docs_board.md` + `COWORK_REPORT_docs_board.md`, walked 2026-08-01
> Superseded by the board being live, and by `CONVENTION_docs.md` §2-§4, which took the lifecycle rules this pair read out of `docs/README.md` · Original purpose: render `docs/` as a board whose columns derive mechanically from filenames.
> Accurate history: how the board derives each column. **Stop trusting:** "6 auditors + 54 testers" — the live gate is **12 auditors + 81 testers**; and note **Tasks 3 (ratification) and 4 (staging) were deferred by instruction and never revisited**, so "the board ships read-only" is still true and is an open thread rather than a finished decision.

# Cowork report — the docs board, read-only

**Brief:** `docs/COWORK_BRIEF_docs_board.md`. **Implements:** DECISIONS 0027
(render-time reads). **Scope:** Tasks 1 and 2 only — Task 3 (ratification) and
Task 4 (staging) were deferred by instruction, so **the board ships read-only**
and DECISIONS 0028, though accepted, is not exercised by any code here.
**Status:** built and gate-GREEN; walk-sheet is `docs/UAT_docs_board.md`.

**Base commit:** `a202ba0`. **Gate:** `python verify.py` → **GREEN, 6 auditors +
54 testers** (+1: `tester_docs_board`). **Nothing committed. No write path
added. No deposit. Nothing persisted.**

---

## Precondition — 0028 was already ratified

The brief made 0028's ratification a hard gate on Task 4. `docs/DECISIONS.md`
records it as **Status: accepted**, so nothing was blocked. It is also not
*used*: 0028 authorises staging a working-tree change, and this slice stages
nothing. The entry stands unexercised until slice 2, which is the honest state
to leave it in — an authorisation is not a commitment to spend it.

---

## Task 1 — the derivation

`chronicler/review/docs_board.py`. Stdlib-only, read-only, no writer to
disable. `board()` walks `docs/` and `docs/archive/` on every call and returns
a fresh answer; there is no board state file and no cache, because a stored
board is the status board `docs/README.md` §5 retires *by class*. Shipping one
inside the tool that renders the convention would have been a fine joke.

### The rules, as implemented

| Column | Condition |
| --- | --- |
| **In flight** | a brief, no report |
| **Built, not walked** | a brief and a report, no results log |
| **Walked** | a results log exists |
| **Archived** | the files are in `docs/archive/` |

**`Archivable` is not a column**, and the tester asserts it never becomes one.
It is not derivable: it needs a human saying the walk happened (§3 route 1,
§6). A results log proves a walk was *recorded*, never that it *passed*.

### The board today — the brief's table was four days stale

Recomputed from the live repo, and it disagrees with the brief in four places.
The brief was right to warn about this; it was written 2026-07-28.

| column | cards |
|---|---|
| **In flight** (3) | `local_deck_evidence`, `local_deck_overlap`, `uat_sidebar` |
| **Built, not walked** (6) | `docs_board`†, `estate_restructure` (0 done/11 open), `file_census` (36/19), `intent_evidence` (0/85), **`local_deck_docs_and_time` (0/43)**, `scanner_bugfixes` (0/9) |
| **Walked** (5) | `command_deck_proto` (10/5), `doc_provenance_coverage` (0/19), `repo_tier_producers` (0/17), **`toolkit_self_scan` (15/25)**, `work_rig_solo` (0/30) |
| **Archived** (25 cards, 45 files) | 8 pairs, 3 walk-only, **14 unmatched** |

† This round. It was *in flight* while the code was being written and moved the
moment this report landed beside its brief — the board deriving its own round,
and the cheapest end-to-end check available. Its own open-item count is
deliberately not quoted here: it drops every time a check on
`docs/UAT_docs_board.md` is ticked, so a number written into this report would
be stale by the next walk. Read it off the board.

**What moved since the brief.** `toolkit_self_scan` went *in flight* →
*walked* (its report, sheet and stamped results log all landed).
`local_deck_docs_and_time` went *in flight* → *built, not walked*. The brief
listed itself as in flight and it still is.

**The brief counted "12 pairs" archived. There are 8.** The other 17 files
group into 3 walk-only cards and 14 unmatched ones. Nothing regressed and
nothing was lost — `archive/` simply does not divide into pairs the way a
one-line summary implied, which is the difference between a count taken by eye
and a count taken by the rule.

## Non-pair shapes — three kinds, none of them broken

A brief and its report form a pair. Three shapes on disk are not pairs, and
forcing them into one would render real documents as defects:

- **`walk_only`** — a walk-sheet, usually with a results log, and **no brief**.
  `UAT_work_rig_solo` is the live case: a walk of an existing build on a second
  machine, not a build round, so there was never a brief to write. **It is on
  the board, as itself, in Walked.** It is never rendered as half a pair. Three
  more sit in `archive/` (`cowork_run_2026-07-24`, `rig_only`, `round_3`).

- **`unmatched`** — an archived file anchoring no brief-plus-report pair *by
  filename*. **Fourteen of them**, and this is the pot the brief's "12 pairs"
  count was smoothing over.

- **off the board entirely** — the trinity, the three playbooks,
  `SPEC_Chronicler.md` and the runbooks: maintained or reference, never
  *finished*, so they have no column to be in. Eleven documents, **listed with
  the reason each is off** rather than silently skipped. `investigation/` is
  not walked at all (§4: a separate lifecycle that never graduates).

### The unmatched pot, and why it is counted on the column

`docs/archive/` predates the current naming convention in places.
`COWORK_ROUND_1/2/3_REPORT.md` will not pair with
`COWORK_BRIEF_build_round_1/2/3.md` however hard you squint at the stems, and
`chronicler_system_design.md`, `WORKSHEET_registry_ratification_2026-07-25.md`,
`HANDOFF_final_2026-07-18.md` and `NEXT_SESSION_PLAN_final.md` pair with
nothing at all — the last two by design, being retired *by class* (§5).

The pre-convention report shape is *recognised* by the classifier and still
fails to pair, which is deliberate: rewriting `round_1` into `build_round_1` to
force a match would be the board inventing history to make its own arithmetic
tidy.

**`unmatched_count` is published on the Archived column header**, beside a
`file_count` that accounts for all 45 files. That is the guard the brief's own
table failed: a pot of quietly-dropped files looks exactly like a smaller
archive, so a pairing regression would be invisible. A published count moves on
its own when pairing breaks. The column reads **25 cards · 45 files · 14
unmatched · 3 walk-only** today; any of those numbers changing without
`archive/` changing is a bug in this module.

### Disposition comes from the stamp; "unmatched" and "unstamped" are different things

Each card's disposition is parsed from its `ARCHIVED` stamp — `completed pair`,
`superseded`, `retired`, `recovered historical brief` — never inferred from the
filename. The stamp is the archivist's judgement, made with the body read, and
it outranks the board's arithmetic.

The two therefore disagree in places, and the card shows both.
`COWORK_BRIEF_chronicler_alignment.md` is stamped **completed pair** and pairs
mechanically as **unmatched**: its partner is an investigation doc whose
filename does not carry the stem. Both statements are true and the board picks
neither as the winner.

**Unstamped is a finding, not a card kind.** *Unmatched* is a statement about
naming. A file in `archive/` with **no stamp at all** is a breach of §3 — moved
without anyone recording what in the body to stop trusting — and it goes to
`findings`, never to a column tally. **There are none today**: all 45 archived
files carry a stamp. Two of them (`UAT_round_3_results.md`,
`UAT_solo_playbook_results.md`) carry it *below* a multi-line `uat` comment, so
the parser reads 60 lines rather than the obvious 5; a tighter window would have
manufactured two findings out of two correctly-stamped files, and the tester
pins that case.

## The checkbox inconsistency — surfaced, not normalised

The brief predicted the board's first job would be exposing this. It was, and
the board found **two more cases than the brief named**.

Five cards are walked (or archived-as-walked) with **zero ticks on the sheet
and the evidence in the results log**:

| card | sheet | results log |
|---|---|---|
| `doc_provenance_coverage` | 0 done / 19 open | 12 / 2 |
| `repo_tier_producers` | 0 / 17 | 14 / 3 |
| **`work_rig_solo`** | 0 / 30 | 21 / 6 |
| **`apply_alignment`** (archived) | 0 / 35 | 6 / 0 |
| **`relink_scoring`** (archived) | 0 / 15 | 11 / 3 |

The brief named the first two. The other three are new, and the archived pair
is the more interesting half: the convention was already being applied two ways
*before* the two live cases, and both pairs were archived without anyone
noticing. `command_deck_proto` (10/5) and `toolkit_self_scan` (15/25) had their
sheets ticked, so the flag distinguishes rather than fires on everything.

**Nothing was fixed.** The affected sheets still read 0 done and the card still
prints `walk-sheet 0 done / 19 open` in the same breath as the flag. The board
carries the instruction on the card: *do not tick the sheet to clear this.*
Normalising it would destroy the only evidence that the convention is
ambiguous, which is the finding. The tester asserts both halves — that the flag
fires on the split case, and that a properly ticked sheet is **not** flagged, so
the flag keeps meaning something.

## Task 2 — the render

A fifth tab on the existing deck; no second service. Four columns, cards, and
**actions that are a function of the column and nothing else**:

| column | action |
|---|---|
| In flight | open the brief — the work is elsewhere |
| Built, not walked | open the walk-sheet, open items inline (slice 2 attaches "walk it" here) |
| Walked | open the results log; remaining open items shown |
| Archived | read-only; the stamp |

**The write-side controls are absent, not disabled.** There is no greyed-out
"UAT ratified?" and no greyed-out "Prepare archive". A disabled button is a
promise the surface cannot keep; an absent one is honest about what shipped.
`actions_enabled: false` is a first-class field in the response.

Bodies render per 0027: read from disk at request time, returned raw,
`textContent` into a `<pre>`. Document text cannot become markup — the same
call slice 1 made, for the same reason.

## The containment anchor — extending one resolver, not writing a second

**The obstacle.** Slice 1's resolver is anchored to `config.estate_roots()`,
which is the right boundary for estate documents and the wrong one here. The
toolkit *happens* to sit inside a configured root on the gaming rig (since
`6dd70f1`); on the work rig it does not. A board anchored to the estate roots
would therefore render card bodies on one machine and refuse them on the other —
for a directory the process is sitting inside.

**The fix.** `estate_data.REPO_ROOT`, derived from `Path(__file__).parents[2]`.
Structural, not a config knob: there is no value that widens or narrows it and
no way to misconfigure a machine into reading the wrong tree.

**One resolver.** The containment check was extracted into
`estate_data.resolve_contained(candidate, anchors, ...)`, and
`EstateData.resolve_document_path` now delegates to it with its refusal tags
and wording unchanged. What varies between the two callers is the **anchor set**
and the vocabulary of the refusal, both parameters; never the resolution logic,
because a second copy of `path_within_roots`' `os.sep` subtlety is a second
place to get it wrong. The tester runs the `<repo>-evil` / `<repo>` case against
the new anchor to prove that subtlety survived the move.

Both of slice 1's checks are kept, for the same reasons:

1. **The route never sees a path.** A card body is addressed by a digest
   resolved against the catalogue the call rebuilds. `../../etc/passwd` and
   `docs/DECISIONS.md` both arrive as identifiers that are digests of nothing —
   asserted at module level *and* over the wire.
2. **Containment is re-verified before the open**, after `realpath`, even for an
   id that resolved. Not redundant: a symlink in `docs/` pointing at `~/.ssh`
   passes check 1.

An empty anchor set refuses everything. "No boundary configured" must never
degrade into "no boundary applies".

## The estate clause — scoped to what it actually governs

**The obstacle.** `run.py _cmd_review` called `account_clause_for_estate`
unconditionally and exited 2 on `both`, a missing estate, or anything
unrecognised. That clause is a `t.account LIKE …` predicate on the vault's
queue tables: **it scopes threads, and only threads.** `docs/` is not estate
data, carries no account column, and is governed by 0027's containment rule
instead — so the old behaviour took the board off every machine whose declared
estate is not exactly `personal` or `work`, over a wall the board does not
stand behind.

**The fix, stated as a rule.** The refusal is scoped to the routes the clause
governs. An unresolvable estate now disables the **vault half** — the queue
routes 503 with `reason: estate_unresolved`, naming the estate rather than
claiming a missing DB that is sitting right there — and the document routes
carry on.

**The wall is tightened, not loosened.** A machine that cannot name one estate
now serves **no thread at all**, and that is enforced structurally rather than
argued: `create_app` raises if it is handed a `db_path` with no
`account_clause`. Previously the same condition was a startup argument that a
later refactor could have softened into a default. `account_clause_for_estate`
itself is untouched — `both`, `None` and junk still refuse, and the existing
tester still asserts it.

**One consequence, taken deliberately.** The preflight's "neither half present"
case no longer exits 2. The board needs neither a vault nor an estate build; it
needs this checkout, which is present wherever `run.py` is. Refusing to start
would refuse to render a directory the process is inside. It prints both gaps
and serves the board — the preflight split from slice 1 run to its conclusion,
not an exception to it.

## Task 3 and Task 4 — deferred, and what that leaves open

Both were deferred by instruction. Nothing about the deferral expires: 0028 is
ratified and stays ratified.

**The ratification-storage question is left unruled**, because ruling on where
a control stores its state before building the control would be deciding it in
the abstract. The brief's recommendation — **session-scoped** — is unchanged and
looks stronger after building Task 1, for a reason the derivation made concrete:
the board is recomputed on every load and stores nothing, so a ratification
persisted anywhere would be the only durable state in the feature and the one
thing that could go stale against a tree that moved under it. Ratification's
only purpose is to authorise the very next action.

## Files

| File | Change |
| --- | --- |
| `chronicler/review/docs_board.py` | **new** — derivation, stamp parsing, card kinds, render-time read |
| `chronicler/review/estate_data.py` | `REPO_ROOT`; containment extracted to `resolve_contained`; `resolve_document_path` delegates |
| `chronicler/review/app.py` | 2 board routes; the no-clause guard; `health` reports the board |
| `chronicler/review/static/index.html` | Docs board tab, columns, cards, findings, off-board list |
| `run.py` | estate clause scoped to the vault half; "neither half" serves the board |
| `tests/tester_docs_board.py` | **new** — derivation on a fixture tree, containment on the real anchor, routes end-to-end |
| `verify.py` | registers `tester_docs_board` |
| 5 finished docs | `gate-frozen` markers — see below |

## The gate went red on five files nobody moved, and why they were frozen

Registering `tester_docs_board` moved the live tester count from 53 to 54 and
turned `auditor_doc_claims` red on five documents this slice did not otherwise
touch. Per the archivist skill's rule — *a gate going red on a file you did not
move is a real finding, surface it* — here is the finding.

All five state the count in the past tense, at a commit they name themselves:
"**Gate at build time** … base commit `ac7710d`", and in the results log,
"`verify.py` on 2026-08-01: GREEN, …". This is the scope error
`docs/README.md` §6 already documents: the auditor cannot tell a doc *asserting*
a count from one *quoting* one.

**They were frozen, not edited.** `docs/README.md` §3 provides
`<!-- gate-frozen: commit=<sha> -->` for exactly this — "the doc is not wrong,
it is just *finished*" — and each marker carries the commit that document
already names (`ac7710d`, or `a202ba0` for the results log, taken from its own
`uat` stamp). Every marker resolves to a real commit, which the auditor checks.

Editing 53 to 54 was the alternative and was rejected. On
`UAT_toolkit_self_scan_results.md` it would have falsified an observation — the
number `verify.py` *printed* on a stated day at a stated commit — which is the
one thing a results log exists to prevent, and precisely the drift the auditor
was built to catch, run backwards. **This is a judgement call on five documents
and it is reversible**; it is UAT check F1 for that reason.

Worth naming as a recurring cost, not a one-off: every round that registers a
tester will red the previous round's finished docs until they are archived. The
marker is the sanctioned answer and this is the second round to reach for it.

## Rendering markdown in the document viewport — for the design thread

Raised on the first walk as "a cheap add", and appearing in a few places now
(this board, the Documents tab, and slice 2's evidence lines). It splits into
two asks that are priced very differently, so they should be fed back
separately.

**The viewport half is cheap and is done.** Height, width, line-height,
monospace sizing and a drag-to-resize edge are pure CSS over text that is still
inserted with `textContent`. Most of the readability complaint was the box, not
the syntax.

**The rendering half is not cheap, and it is the one slice 1 already declined.**
That report chose `<pre>` deliberately: *"a hand-rolled heading/paragraph pass
is a second parser to maintain and, more to the point, a path by which document
text becomes markup. `textContent` into a `<pre>` cannot produce markup at
all."* Nothing about that has changed, and this slice makes it slightly worse —
the board renders documents that are *about* HTML and markdown, including this
report, so a renderer would be parsing its own description of itself.

Three routes, priced honestly:

1. **Hand-rolled renderer.** A second parser, maintained forever, and every bug
   in it is a potential injection. It is the option that was rejected on a
   surface with a *smaller* corpus.
2. **A library from a CDN.** Fails the local-surface posture: a loopback deck
   that reaches the internet to render a local file, and a supply-chain
   dependency in the path between a document and the DOM. Vendoring it moves
   the problem without shrinking it.
3. **A tightly-scoped subset**, escape-first: escape the whole document, then
   re-introduce markup for headings, bold, code spans and fenced blocks only —
   never links, never images, never raw HTML passthrough. Escaping *before*
   marking up is the same order the search snippets already use with `\x02` /
   `\x03` markers, and that pattern is proven in this codebase.

**Recommendation for the thread: (3), or nothing.** It is the only option that
keeps "document text cannot become markup" true by construction rather than by
a parser being careful. It is a slice of its own, not a line in this one — and
if it is not worth a slice, the honest answer is that a `<pre>` that is
pleasant to read is worth more than a renderer that might be wrong.

## Left open

- **Walked and accepted 2026-08-01** — 40 passed, 5 with notes, 1 carried.
  Results: `docs/UAT_docs_board_results.md`, stamped at `53ab5ba`. The
  evidence is on the **sheet** and the **ruling** is in the results log, which
  is the convention this round exists to defend: five existing pairs do it the
  other way round, and this one declined to be the sixth. The `docs_board` card
  is consequently the only walked pair on the board with no split-evidence
  flag.
- **E7 is carried, not walked** — the repo anchor cannot be evidenced on the
  gaming rig, where the toolkit sits inside a configured root. It is the one
  claim in this slice resting on a tester alone; walk it on the next work-rig
  session.
- **The walk found one defect and it was fixed.** The loopback refusal named
  `work` where the condition is `!= "personal"`; scoping the estate clause is
  what made that line reachable with `both`. Message text only — the wall did
  not move, which was the risk worth checking.
- **C5 is open for the design thread.** The card renders the mechanical kind as
  a chip and the stamp's disposition as body prose, which weights them the
  opposite way round from this report's own argument. Not a derivation defect.
- **`UAT_docs_board.md` is a live doc with an open sheet**, so the board shows
  its own round in *built, not walked* — self-demonstrating, and it means the
  `docs_board` card is the first thing to check against reality.
- **Route coverage is conditional.** FastAPI is an optional extra, so
  `_route_checks` reports `skipped` on a machine without it rather than
  passing silently. Any machine that can run the surface gets the coverage.
- **The five `gate-frozen` markers are the reversible part of this slice.** If
  the ruling should have gone the other way, the counts are one edit away.
- **Out of scope as briefed:** ratification (Task 3), staging (Task 4), the UAT
  sidebar (slice 2), boards for other projects' docs, any change to
  `docs/README.md`'s convention.
