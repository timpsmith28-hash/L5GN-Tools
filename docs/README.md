# docs/ — what lives here, and what doesn't

The map of this folder. Read this before adding a doc, and before believing one.

The governing rule is that **a document earns its place by holding something that
can't be derived.** Rationale can't be derived — it lives here. Status can be
derived from `verify.py`, `git log` and the DB — so it does *not* live here. Every
doc retired into `archive/` was retired for failing that test.

---

## 1. The core set

These are maintained. If one contradicts the code, that's a bug in the doc.

| Doc | Holds | Goes stale when |
|---|---|---|
| `INTENT.md` | Why the system is worth building. Wants, not facts. | The reason changes — not on a schedule |
| `ARCHITECTURE.md` | What the system *is*, as built. The authoritative shape reference (DECISIONS 0016) | The shape changes |
| `DECISIONS.md` | Append-only *why* behind each ruling. Never edited; superseded by a later entry | Never — entries are frozen by construction |
| `KNIGHT_PLAYBOOK.md` | Deploy + operate the **consumer** (the knight). Operator-facing runbook | The deploy steps change |
| `PRODUCER_PLAYBOOK.md` | Deploy + operate a **producer** rig. The other half of the runbook | The deploy steps change |
| `SPEC_Chronicler.md` | The linking/skillset spec for the ingest side | The spec is executed or superseded |

`INTENT` / `ARCHITECTURE` / `DECISIONS` are **the trinity**. Where a brief, a
report or an archived doc disagrees with the trinity, the trinity wins.

Also core, but transient: the **live round** — its brief
(`COWORK_BRIEF_build_round_N.md`), its report, and its UAT walk-sheet
(`UAT_round_N.md`), the sheet Tim actually walks to close the pair. All three
leave core `docs/` together the moment the pair completes — see §3.

## 2. Doc classes

Five kinds of file live here, across **three lifecycles** — core (maintained),
`archive/` (retired, stamped), `investigation/` (raw evidence, never maintained).

- **Trinity + reference** (§1) — maintained indefinitely. Edited in place.
- **Briefs** (`COWORK_BRIEF_*.md`) — a task handed to a build thread. Written
  once, not maintained. A brief is a *request*, frozen at the moment of asking;
  correcting it after the fact destroys the record of what was actually asked.
- **Reports** (`COWORK_*_REPORT.md`, investigations) — what a thread found or
  built. Also written once, also not maintained. A report is testimony about a
  moment; its numbers were true then and are not claims about now.
- **Archived** (`archive/*.md`) — any of the above, retired, stamped, kept for
  provenance. Read-only history.
- **Investigations** (`investigation/*.md`) — raw prompt-and-response exchanges
  captured from a thread. Evidence, never maintained, never graduates. See §4.

A brief and its report form a **pair**. Pairs are the unit of archiving.

## 3. The archiving convention

### When a doc is archivable

A doc leaves core `docs/` when it is *finished*, not when it is *old*. Three
routes in:

1. **Completed pair.** A brief plus its report, where the work is built **and Tim
   has walked the UAT**. `verify.py` green proves the code works; it cannot prove
   the code does what was asked. Only the human walking the acceptance checks
   closes a pair. A pair with a green gate and an unwalked UAT is **not**
   archivable. (This rule is a convention, not an enforced gate — see §5.)
2. **Superseded.** A later doc, or a DECISIONS entry, now holds the truth this
   one held. Name the successor in the stamp.
3. **Retired by class.** The doc is a kind of doc we've decided not to keep —
   status boards and handoff/priming docs, both of which are derivable and both
   of which demonstrably rotted. See §5.

### The stamp

Every archived file gets a blockquote stamp prepended **above** its original
`# Title`, leaving the body untouched. The body is evidence; do not edit it —
say what's wrong with it in the stamp instead.

```
> **ARCHIVED** YYYY-MM-DD · <disposition> · <pair status>
> Superseded by <successor> · Original purpose: <one line — what it was for>
> <what to trust and what not to: which parts are accurate history, which parts
> later decisions moved past, and any dangling references resolved>
```

- **disposition** — `completed pair` · `superseded` · `retired` ·
  `recovered historical brief` · `recovered historical design`
- **pair status** — the partner file, or `no report — <why this had no pair>`
- **Superseded by** — a real path or a DECISIONS entry number. If nothing
  supersedes it, say what replaced the *need* for it.
- The closing lines exist to stop a future cold read from trusting stale
  content. Be specific: cite the DECISIONS entries that moved past it.

Prefer `git mv` so the rename is recorded, not a delete-plus-add.

### The uat stamp

A round's results log (`UAT_round_N_results.md`) is the one document that asserts
*"this was tested"*, and until round 3 it was the only artifact in the system
with no provenance — every scan output already stamps `toolkit_git_info()`. So a
results log in core `docs/` must carry, at the top:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> gate=<Na/Mt> -->
```

`commit` and `walked` are required; `gate` is optional but checked against
`verify.py` when present — omit it rather than assert a count you didn't observe.
`auditor_uat_stamp` fails the gate if the stamp is missing, if a required field
is absent, if `commit` doesn't resolve to a real commit in this repo, or if
`gate` contradicts the registered counts.

It does **not** check whether the walk passed. That is the point: the gate
polices where an acceptance claim came from, never whether the acceptance was
earned. `verify.py` answers "does it work"; a human answers "does it do what was
asked"; this only makes the second answer traceable to a commit.

It exists because a results log once claimed a tester count that matched no
version of this tree — a stale number recovered from a retired doc in `archive/`
and laundered into a live one. With no commit on the document, "the walking
machine was on an old tree" and "the number was invented" were indistinguishable.

### Why the auditor stops at the archive door

`auditor_doc_claims` scans `README.md` and `docs/*.md` — **non-recursive**, so
`docs/archive/` is exempt by design. That exemption is the point: a round-1 report
recording the gate count of the day was *true when written*. Forcing it
to match today's counts would edit testimony to fit the present, which is exactly
the drift the auditor exists to catch, run backwards. Archived docs are frozen;
live docs are checked.

A live doc whose numeric claims have gone stale should be **fixed or archived**,
never exempted in place.

## 4. `investigation/` — raw exchanges

The third lifecycle. Where a thread's **starting prompt** and its **final
response** are kept verbatim, whatever the model — Gemini, Claude, anything else.
A Cowork round's output file is a response; the brief that opened it is a prompt.

The point is provenance. The trinity says what we decided and why; this folder
holds the actual exchange the decision came out of, so a future cold read can
check the reasoning against its source rather than taking DECISIONS on trust.
Eventually the *full* thread lands in the vault via Chronicler — this folder is
the endpoints of that thread, kept in the repo where the decision lives.

Rules:

- **Never maintained, never corrected, never graduates to core.** A captured
  exchange is evidence; editing it destroys the thing it's kept for. Wrong turns
  and abandoned reasoning stay in.
- **No stamps.** Investigations aren't archived, because they were never live.
  They're born frozen.
- **Nothing here asserts current truth.** A core doc may cite an investigation as
  the source of a decision; it may not defer to it for what is true now.
- Outside `auditor_doc_claims`' scan (`docs/*.md` is non-recursive), for the same
  reason `archive/` is — see §3.

### Naming

```
YYYY-MM-DD_<topic>_<model>_1-prompt.md
YYYY-MM-DD_<topic>_<model>_2-response.md
YYYY-MM-DD_<topic>_<model>_3-thread.md     (optional: full export, when it lands)
```

Date first so the folder stacks chronologically; topic before model so both ends
of one exchange sit together; the numeric `1-`/`2-`/`3-` prefix guarantees prompt
sorts above response regardless of what the words are. Lowercase, hyphens inside
a field, underscores between fields.

`chronicler_investigation_2026-07-18.md` predates this convention and is archived
as half of a completed pair rather than moved here — it was a commissioned report
against a brief, not a captured exchange.

## 5. Do not recreate

Two doc classes are permanently retired. Both are in `archive/` with their
autopsies attached.

- **No handoff / priming doc.** `HANDOFF.md` held facts-with-numbers that drifted
  and cited a `CHANGELOG.md` that never existed. Priming a fresh thread is the
  trinity's job.
- **No status / next-session board.** `NEXT_SESSION_PLAN.md` contradicted itself
  on the tester count *lines apart*, in the document warning against exactly that
  rot. Status is derived: `python verify.py`, `git log`, the DB.

Forward-looking items — "what we agreed but haven't built" — are **carried
manually into the next thread**, not written down. A written forward-look is a
promise that ages badly and gets mistaken for a commitment; the stale-forward-look
trap is what killed the handoffs.

## 6. What isn't enforced

Honest list, so nothing here reads as stronger than it is.

- The UAT precondition in §3 is a **convention**. Nothing checks that a UAT was
  walked before a pair is archived, and nothing ever will — that judgment is
  human. `auditor_uat_stamp` narrows the gap by checking the *provenance* of the
  claim (which commit, which host, which day), not the claim. Making the
  acceptance step itself structural — a prompt at commit time rather than a
  hermetic gate — remains open.
- `auditor_doc_claims` cannot distinguish a doc *asserting* a gate count from a
  doc *quoting* one. Its docstring claims narrative past-tense mentions don't
  match; they do, whenever the two numbers appear in the original order — as they
  do in any report about the auditor itself. The exemption for `archive/` and
  `investigation/` is the current answer, which means a live report quoting a
  count reds the gate until its pair closes. Scope error, not concept error, and
  the boundary it's failing at is the deterministic/acceptance line above.
- Stamp *content* is a human call. The `docs-archivist` skill
  (`.claude/skills/docs-archivist/`) scripts the mechanics — detecting candidate
  pairs, drafting the stamp, staging the `git mv` — but never moves a file
  without explicit ratification.
