---
name: docs-archivist
description: Propose archiving finished docs in L5GN-Tools — detect completed brief+report pairs and superseded docs in docs/, draft the ARCHIVED stamp, and stage the git mv into docs/archive/. Use when asked to archive docs, tidy docs/, retire a doc, stamp an archived file, or check which docs are archivable. Proposes only; never moves a file without explicit ratification.
---

# docs-archivist

Scripts the **mechanics** of archiving a doc in this repo. Does not make the
**judgment**. The split is deliberate: deciding a doc is finished requires knowing
whether Tim walked the UAT, and no tool can know that.

Read `docs/README.md` §3 first — it is the authority on the convention. This skill
is the procedure; that file is the rule. If they disagree, `docs/README.md` wins
and this file needs updating.

## The hard rule

**Never move, rename, or stamp a file until Tim has ratified that specific move.**
Present the proposal, wait for a yes. A "tidy up docs/" instruction is *not*
ratification — it authorises the proposal, not the move. Ratify per pair, not in
bulk, unless Tim explicitly says "all of them".

## Procedure

### 1. Survey

- List `docs/*.md` (core) and `docs/archive/*.md` (already done).
- Group core files into candidate **pairs**: `COWORK_BRIEF_<x>.md` + its report
  (`COWORK_<X>_REPORT.md`, or an investigation doc it commissioned). A brief with
  no report is not a pair — it is either in flight or orphaned.
- Flag singletons: docs superseded by a DECISIONS entry or by a newer doc.
- Never treat a trinity file (`INTENT` / `ARCHITECTURE` / `DECISIONS`) or
  `KNIGHT_PLAYBOOK.md` as a candidate. They are maintained, not finished.

### 2. Classify each candidate

For each, determine the route in (`docs/README.md` §3):

- **completed pair** — built *and* UAT walked. **Ask Tim about the UAT.** Do not
  infer it from a green gate or from a report claiming completion; a report can
  only say "ready to walk". If the answer is no or unknown, the pair stays put.
- **superseded** — identify the successor by path or DECISIONS entry number. If
  you can't name one, it isn't superseded, it's just old.
- **retired by class** — status boards and handoff/priming docs (§5).

### 3. Draft the stamp

Use the format in `docs/README.md` §3. Draft it from a real read of the file —
open the doc and the DECISIONS entries that moved past it. A stamp is only worth
writing if it tells a cold reader **what in the body to stop trusting**, and that
requires knowing what's in the body.

Quality bar, in order of importance:

1. Names its successor concretely (path or entry number).
2. States, specifically, which parts are accurate history and which later
   decisions overtook — cite entry numbers.
3. Resolves any dangling reference the body makes (a doc that was never found, a
   file since renamed).
4. Carries a blunt instruction where one is warranted: *do not recreate*, *do not
   run as a task list*, *read as origin, not current truth*.

A generic stamp ("archived, superseded, kept for history") is a failure. It costs
a future cold read nothing to ignore.

### 4. Propose

Show, per candidate: the files, the route in, the drafted stamp in full, and the
exact `git mv` commands. Then stop and ask.

### 5. Execute, once ratified

```
git mv docs/<file>.md docs/archive/<file>.md
```

Then prepend the stamp **above** the original `# Title` line, with a blank line
between stamp and title. **Do not edit the body.** Not the numbers, not the
claims, not the typos — the body is evidence, and the stamp is where you say
what's wrong with it.

Rename on archive only when the original name asserts currency that is no longer
true (`HANDOFF.md` → `HANDOFF_final_2026-07-18.md`). Otherwise keep the name.

### 6. Verify

```
python verify.py
```

Expect **GREEN**. Two things to know:

- `auditor_doc_claims` scans `docs/*.md` non-recursively, so archiving a doc with
  stale gate counts *clears* those failures rather than requiring an edit. That's
  by design, not a loophole (`docs/README.md` §3).
- If the gate goes red on a file you did **not** move, that's a real finding —
  surface it, don't archive your way around it. Archiving is not a tool for
  silencing a live doc that has gone stale; fix that doc instead.

Leave everything **staged, uncommitted**, for Tim's review. Never commit.

## Anti-patterns

- Moving a brief whose round is still in flight.
- Archiving a live doc to make the gate green.
- Editing a report's numbers "for consistency". They were true when written; the
  whole convention exists to protect that.
- Writing a forward-looking "what's next" line into a stamp. Stamps look
  backwards only (`docs/README.md` §5).
