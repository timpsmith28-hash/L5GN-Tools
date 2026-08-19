# Commit convention

**Status:** authored, not enforced. No auditor and no hook covers this file
today (see §7). It is the single statement of the format; a skill, a build
thread, or a person writing a commit cites it rather than carrying its own
copy — because the drift measured in §1 was per-thread, and a convention that
lives in whoever happens to be typing is not a convention.

**Scope:** this repo. MCF repos may adopt it; nothing here reaches across a
repo boundary.

---

## 1. What this fixes, measured

Read from the last 40 commits at `300bab0`:

| | |
|---|---|
| carry a `type(scope):` prefix | **33 / 40** |
| carry a real body | **27 / 40** |
| subject over 72 characters | **25 / 40** |
| longest subject | **1794 characters** (`cb9e29f`) |

The convention is already 82% kept. **The defect is mechanical, not
stylistic.** The worst offender, `cb9e29f`, is a genuinely good message —
`docs(decisions): 0044-0046 …`, three ratified entries explained properly —
whose entire body was flattened into its subject line in transit. Two others
were destroyed outright by shell quoting: `a79bcc9` begins
`$(cat <<'EOF'Fix estate_freshness stage…` and `d4f1c54` begins
`$Drop the Desk's silent week…`, each with every newline stripped.

Those are good messages lost to the *mechanism*, and the cost is real: after
them, `git log --oneline` cannot be read, `--format=%s` cannot be scanned, and
`git log --grep` over subjects returns whole essays. The record survives, but
only to a reader willing to open each commit.

Second pattern, smaller: the seven prefix-less subjects are clustered in one
build thread (`fb6fa5c`, `c6c1d4a`, `d6fa9b7`, plus the two broken ones), and
`c6c1d4a` and `d6fa9b7` share a subject verbatim — two commits from one round,
indistinguishable in a log.

## 2. The mechanism — always `-F`, never inline

**Write the message to a file. Commit with `git commit -F <file>`.** Never
pass a multi-line message with `-m` and never build one with a heredoc inside
a command string. Every corrupted message in §1 came from doing that on
Windows, and the failure is silent — git accepts what the shell handed it.

```
git commit -F data/git_warden/<round>-<n>.msg
```

`data/` is gitignored wholesale, so the draft never becomes a tracked file and
never needs cleaning up. (`commit_msg.txt` at the repo root is the hand-rolled
version of this and should move; a draft in the working tree is one more
untracked file the next `git status` has to explain.)

`-m` remains fine for a genuine one-liner with no body — `chore: typo in
decisions` needs no file.

## 3. The subject line

```
type(scope): subject
```

- **≤ 72 characters.** Hard. If it will not fit, the surplus is body.
- **Imperative or noun phrase**, matching what is already here: `feat(pin):
  the pin mechanism (DECISIONS 0045), wired to the conversation map`.
- **No trailing period.**
- **`--` for an em dash**, as everywhere else in this estate's plain-text.
- **Distinguish sequential commits in one round.** `feat(model-bench): Task 5
  -- the comparison` does this well; two commits sharing `Add the Desk module`
  do not.

**`type`** — the six already in use: `feat`, `fix`, `docs`, `chore`,
`refactor`, `test`. Adding a seventh is a change to this file, not a
judgement call at commit time.

**`scope`** — the module, round or artifact the change belongs to, lowercase,
as already used: `model-bench`, `quartermaster`, `architecture-census`, `pin`,
`uat`, `decisions`, `briefs`, `archive`, `investigation`, `deps`, `run`,
`docs_board`. Omit it only when the change genuinely spans the repo.

## 4. The body

Wrap at 72. Blank line after the subject.

**Say why, not what** — the diff already says what. This estate's existing
bodies are the standard to hold: `d4f1c54`'s explanation of why the silent
week was cut is a model, and it is worth reading before writing one. It states
what was found, against what evidence, what was decided instead, and what the
consequence is. That is the same discipline `DECISIONS.md` exists for, applied
at a smaller scale.

Where a commit reverses or corrects an earlier one, name it by SHA and say
what was wrong — not as an apology, as the record.

## 5. Trailers

Last block, after a blank line, one per line:

```
Ruling: 0050
Brief: COWORK_BRIEF_staleness_feeds.md
Report: COWORK_REPORT_desk_stale_card.md
```

- **`Ruling:`** — DECISIONS numbers this change was made under, comma-separated.
  Cross-repo rulings carry their repo, per **0043**: `Ruling: sfds-0029`.
- **`Brief:`** / **`Report:`** — filename only, no path.
- Omit any trailer that does not apply. A trailer block is not mandatory; an
  *inaccurate* one is worse than none.

This is the cheapest link in the thesis. `git log --grep='Ruling: 0050'`
answers *what did that ruling actually cause* today, and after Phase 2 it is
how the ledger joins commits to ruling events without inventing a join. Right
now that information is being written in prose, inside subject lines, where
nothing can read it.

## 6. What belongs in one commit

- **A generated artifact travels with the change that caused it.** `docs/_architecture_shape.md`
  is regenerated by `python run.py render-architecture`; it is committed in
  the same commit as the change to routes, schema, scanners or the gate that
  moved it — never in a tidy-up afterwards (**0030**: shape is generated,
  rationale is authored; a shape doc that lags its tree is a false claim).
- **A doc round and a code round are separate commits**, even in one sitting.
  They are reviewed differently, they age differently, and a mixed commit
  cannot be cited cleanly by either a brief or a report.
- **An unrelated typo fix is its own commit.** `chore:` exists for this.
- **UAT stamps and their results log go together**, and cite the commit they
  were walked against in the body rather than assuming the reader can infer it.
- **A commit is still a human act** (**0028** clause 3). Nothing in this file
  changes that: the pre-commit hook runs `verify.py`, the human reads
  `git diff --staged`, the human commits.

## 7. Not a gate — and what a gate would cost

Nothing enforces this. `verify.py`'s auditors walk the tree, not the reflog,
and no auditor reads commit messages.

Enforcement is available cheaply if it is ever wanted: `core.hooksPath` is
already `.githooks`, which already holds `pre-commit`. A **`commit-msg`** hook
beside it, checking only the mechanical properties — subject ≤ 72 chars, a
known `type`, a body separated by a blank line, trailer lines well-formed —
would catch every defect in §1 at the moment it happens, and would have caught
all three corrupted messages. It cannot check whether a body says *why*, and
should not pretend to.

**Not built, deliberately, for now:** a hook that refuses a commit is a gate on
the operator's own hands, and this repo has exactly one operator whose hands
are also its only reviewer. Worth revisiting when the convention has been
followed voluntarily for a month and the failures that remain are the
mechanical ones a machine can see.

## 8. History is not rewritten

The commits in §1 stay as they are. This estate's standing position on damaged
testimony is **0029**'s: kept intact or removed, never doctored — a rewritten
history is manifest-valid and undateable, which is worse than a visible scar.
`cb9e29f` and the two broken ones are a record of how the mechanism failed,
and §2 exists because of them.

## 9. The check, before you commit

1. Message in a file; `-F`, not `-m`.
2. Subject ≤ 72, `type(scope):`, no trailing period.
3. Blank line, then a body that says *why*.
4. Trailers: `Ruling:` / `Brief:` / `Report:`, only where true.
5. Generated artifacts regenerated and staged alongside their cause.
6. `git diff --staged`, read by a human. Then commit.
