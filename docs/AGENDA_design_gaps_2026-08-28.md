# Agenda — design gaps forced by 0051-0057, 2026-08-28

`AGENDA_running_order_2026-08-28.md` was frozen at its own date and written
while 0051-0057 were still `proposed` — §6 says so explicitly: *"None is
ratified and this plan does not assume ratification."* All seven were
ratified later the same day. This note is what that reread found: places
where an accepted clause requires something the running order does not name,
checked against the tree rather than assumed. Nothing here is filed as a
brief or a card; that is Card-A-through-F's job, and this list is an input to
that sequencing, not a replacement for it.

---

## 1. 0056 broke the gate on this rig today, and nothing schedules the fix

0056's own Consequences say it plainly: *"this entry cannot be landed and
left — it lands with work attached."* Checked against `config/`:

- `personal_conversation_map.tsv` exists and has **no `.sha256`** —
  confirmed by directory listing. Clause 2: *"A map that exists without a pin
  recorded for it is a violation, not an absence."*
- `auditor_conversation_map_pin` still passes on this tree, which is exactly
  the failure clause 1 names: it is written against the single path
  `mcf_conversation_map.tsv`, not the `/config/*conversation_map.tsv` pattern
  0040 clause 4 actually rules on, so it cannot see the instance that
  violates it.
- The existing MCF pin (`config/mcf_conversation_map.tsv.sha256`) is
  **hash-only**. Clause 3 requires the full metadata line — origin, anchor,
  date, host — which `l5gntools/pin.py` already supports but the artefact
  does not carry.
- Clause 1's own falsifier is unaudited: *"count the checks in `verify.py`
  whose ruling names a pattern and whose code names a path"* — the entry
  names one instance and says finding more "creates an unknown quantity of
  latent non-conformance and no list of it." No sweep has been run.

None of this is in Cards A-F or the "not in the order" list. It is smaller
than any of them and more urgent than all of them — it is gate hygiene that
is *already* silently wrong, not gate hygiene contingent on a future round.

## 2. 0054's config-layering refactor has no card anywhere

`CONVENTION_config.md` §1 states its own status: *"authored, not enforced,
and not yet true."* Two threads inside 0054 are not cosmetic:

- **Clause 5 (no whole-file overwrite) is a live bug, not a future risk.**
  0054's own Context describes it happening now: `config/local.json` is
  written at runtime by `governor.set_profile` and
  `curator_control.set_curator_model`, and the file's own comment instructs
  shipping it by `scp` — which silently destroys whatever the runtime wrote,
  on both ends, on the next ship.
- **Clause 6 (`authors` lives in the tracked file only) directly feeds Card
  B.** The running order scopes Card B "against 0053," and 0053 clause 2's
  `authors` declaration is exactly what 0054 clause 6 resolves an ambiguity
  in. Card B cannot be scoped correctly without this being settled first.
- Clause 2 and clause 4 (derive machine facts; resolve configuration once, at
  the edge) are named in 0054's own Consequences as "a real refactor with no
  user-visible feature at the end of it… the clause most likely to be
  deferred indefinitely." That prediction is a reason to name it here, not a
  reason to leave it unnamed.

## 3. 0055's registry migration is drafted but not done

`docs/CONVENTION_project_registry.md` exists (277 lines) — the convention
0055 clause 2 requires is written. The artefact it governs is not migrated to
cite it:

- `config/project_registry.json` still carries `_comment`, `_schema`,
  `_id_scheme` and `_low_signal_body` as its own keys — confirmed by reading
  the file. This is precisely 0052's finding "with a file in the role of the
  person," restated by 0055, and it is still true.
- No auditor and no pin exist for the registry. 0055 clause 7 requires a pin
  (origin, anchor, date, host) on the same reported-never-repaired footing as
  0045; none was found (`auditors/` has nothing matching `registry`).

## 4. 0051's containment has no auditor

Clause 2 requires the exclusion be *"enforced by an auditor over the built
deposit, the way 0044 enforced `data/knowledge_curator/`."* Clause 6 requires
a scanner that skips the path to say so in its own output. No auditor
referencing the work-estate corpus was found in `auditors/`. This is
containment for the most sensitive material this estate holds, resting on
"measures were taken" rather than a check.

## 5. hermetic_gate's own precondition is now met, and the running order can't say so

The running order defers `hermetic_gate` explicitly: *"gate hygiene gated on
0053 (proposed)… run it whenever 0053 is ratified; it does not belong in this
sequence."* 0053 is accepted now. The document is frozen at its own date and
does not update itself — Card B's "scope against 0053 (proposed)" and Card
C's "touches 0053 (proposed)" are both now stale parentheticals, and
`hermetic_gate`'s place in the sequence (before, alongside, or folded into
Card B, which already scopes against 0053) is an open call nobody has made.

## 6. Smaller, worth a look rather than confirmed

- **0052's own falsifiers have no tracker.** "Count the rules whose only home
  is a skill" and "count rules rediscovered at the next rig switch" are
  stated as the entry's own falsifiers but nothing produces either count.
  Adjacent to Card D's promotion mechanism, not the same thing — Card D
  tracks Desk rulings, not skill-only rules.
- **0057 clause 7 (adoption header).** Of the nine `CONVENTION_*.md` files,
  only two (`CONVENTION_decisions.md`, `CONVENTION_docs.md`) plus
  `CONVENTION_briefs.md` and `CONVENTION_gitignore.md` carry an "Adopted
  from" line. That is not evidence the other five were adopted from
  elsewhere without citing it — most may be original to this repo — but it
  was not checked file by file here and is worth a five-minute pass before
  assuming it is clean.

## Checked and clear — not gaps

- **0057 clause 1** (a second tracked skills directory is a defect):
  `.claude/skills` is the only one; nothing else in the tree is tracked
  under that name.
- **0052 clause 4** (an environment rule belongs to the environment, not a
  skill): the sandbox-git hazard now lives in `CLAUDE.md`, not in
  `commit-scribe`.
- **0052 clause 5's named debt** (brief-scribe / decision-scribe with no
  convention to cite): both conventions now exist; the debt 0057 described as
  live "until Thread E lands" reads as discharged.
