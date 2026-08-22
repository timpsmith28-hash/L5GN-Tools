---
name: commit-scribe
description: Draft commit messages for L5GN-Tools to the house convention — sweep spent drafts, survey what changed, split a mixed working tree into separate commits, write each message to a file under data/git_warden/, and hand back the exact `git commit -F` command. Use when asked to write, draft or tidy a commit message, to commit changes, to say what a commit should contain, or to split changes into commits. Drafts only; never runs `git commit`.
---

# commit-scribe

Scripts the **mechanics** of writing a commit here. Does not decide that a change
is ready to land — that is a human act, and 0028 clause 3 keeps it one.

Read `docs/CONVENTION_commits.md` first — it is the authority on the format. This
skill is the procedure; that file is the rule. If they disagree, the convention
wins and this file needs updating. Do not carry a copy of the format in your head
or restate it back to Tim from memory: the drift the convention documents (§1) was
per-thread, and a second copy of the rule is how that happens again.

## The hard rules

**Never run `git commit`.** Draft the message, stage nothing the operator did not
ask you to stage, hand back the command. The human reads `git diff --staged` and
commits. (0028 clause 3, unamended.)

**Never pass a multi-line message inline.** Not with `-m`, not with a heredoc
inside a command string. Three commits in this repo's history were destroyed that
way and the failure is silent — git accepts whatever the shell handed it. Always
write a file and use `-F`.

**Never invent a trailer.** A `Ruling:` or `Brief:` line you inferred rather than
confirmed is worse than no trailer at all. If the governing ruling is not obvious
from the round in progress, ask or omit it.

## Procedure

### 0. Sweep the spent drafts

Before anything else, so that `data/git_warden/` holds only live work and
"pending" means pending.

A draft whose **first line exactly matches the subject of a commit already in
`git log`** has been spent. Exact match, never fuzzy: a draft edited after it was
committed will not match, and that divergence is worth seeing rather than
tidying away. Check the repo root too — a stray `commit_msg.txt` is the same
thing in the wrong place, and the same test classifies it.

**Propose the deletion; do not delete.** Same posture as the rest of this skill
and as `docs-archivist`: hand back the `Remove-Item` / `rm` command and let the
operator run it.

### 1. Survey

```
git status --porcelain
git diff --stat
git diff --staged --stat
```

Know what is actually there before writing a word about it. Read the diffs of
anything you did not personally change — a message describing a change you assumed
is the failure mode this whole skill exists to prevent.

If a draft already exists for work still in the tree, re-verify it against the
current diff before reusing it. Unchanged stats are decent evidence; a file whose
mtime moved since the draft was written needs re-reading.

### 2. Split before drafting

This is the judgement step and it comes first, because the answer changes how many
messages you write. Per `docs/CONVENTION_commits.md` §6, these do **not** share a
commit:

- a doc round and a code round, even in one sitting;
- an unrelated typo or tidy-up (`chore:` exists for it);
- work belonging to two different briefs or rounds.

And this one **must** share a commit: a regenerated artifact travels with the
change that caused it. If routes, schema, scanners or the gate moved, then
`docs/_architecture_shape.md` needs regenerating with
`python run.py render-architecture` and staging alongside — a shape doc that lags
its tree is a false claim (0030).

Propose the split as a numbered sequence, with the files in each. Then draft in
that order — earlier commits are what later ones build on, and the bodies should
read that way.

### 3. Draft to a file

```
data/git_warden/<round-slug>-<n>.msg
```

`<round-slug>` names the round, usually the brief's slug (`staleness_feeds`,
`desk_stale_card`); `<n>` is the position in the sequence from step 2. `data/` is
gitignored wholesale, so the draft never becomes a tracked file.

Quality bar for the body, in order of importance:

1. **Says why, not what.** The diff says what. A body that narrates the diff is
   noise in a log that is otherwise unusually good.
2. **States what was found, against what evidence.** The best bodies in this repo
   (`d4f1c54` is the model) name the observation, the reasoning, the decision, and
   the consequence. Read it before writing a substantial one.
3. **Names what it corrects, by SHA**, where it reverses or fixes an earlier
   commit. As record, not apology.
4. **Resolves nothing it cannot support.** If the round left something outstanding,
   say so; do not let a message imply a completeness the tree does not have.

A message must not carry an instruction the operator has already followed. If a
step was done between drafting and presenting — a regeneration, a rename — rewrite
that paragraph to state the result rather than leaving it as advice.

### 4. Self-check, mechanically

Before showing it, verify the properties a `commit-msg` hook would check if one
existed (`docs/CONVENTION_commits.md` §7 — it does not, yet):

- subject **≤ 72 characters** — count it, do not eyeball it;
- subject starts `type(scope):` using a type already in use (`feat`, `fix`,
  `docs`, `chore`, `refactor`, `test`) — a seventh type is an edit to the
  convention, not a call made at commit time;
- no trailing period; `--` for an em dash;
- blank line between subject and body; body wrapped at 72;
- trailers last, one per line, `Ruling:` / `Brief:` / `Report:` only, cross-repo
  rulings carrying their repo (`sfds-0029`, per 0043);
- the subject distinguishes this commit from its neighbours in the same round.

### 5. Present and stop

Always show, per commit: the files it covers, the draft path, and the exact
command —

```
git commit -F data/git_warden/<round-slug>-<n>.msg
```

**How much of the message body to show depends on how many there are.** One or
two commits: the full text inline, because that is what gets reviewed. Three or
more: a table of subjects and paths, the bodies left on disk to read, and the
full text inline only for any commit that is blocked, unusual, or asserts
something the operator needs to check. A nine-commit backlog printed in full
buries the two that needed attention — that failure is what this rule is for.

Then stop. If the gate is likely to fail on this commit (`verify.py` runs from
`.githooks/pre-commit`), say so now rather than letting it surprise them.

## Anti-patterns

- Running `git commit`, or staging files nobody asked you to stage.
- `-m "…"` with a body, or a heredoc inside a command string. See §1 of the
  convention for what that costs.
- Guessing a `Ruling:` number to make the trailer block look complete.
- One commit covering a doc round and a code round because they happened together.
- Committing a code change without regenerating the shape doc it invalidated.
- A body that restates the diff in prose.
- Offering to fix an earlier bad commit message by rewriting history. The
  convention's §8 rules that out — 0029's posture, applied to the reflog.
- Drafting into a folder still full of spent drafts, so nobody can tell which are
  live. Sweep first (step 0).
- Deleting a spent draft yourself instead of proposing the command.
