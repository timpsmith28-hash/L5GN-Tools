# Cowork brief — the solo playbook: one machine plays the whole mesh

**Origin:** design thread, 2026-07-27, immediately after the golden close-out.
**Deliverable:** `docs/SOLO_PLAYBOOK.md` — one document, two profiles.

Today the estate assumes two boxes: a **producer** rig that scans and deposits, and
the **knight**, a consumer that ingests, runs the pipeline and serves. Two playbooks
describe that split (`PRODUCER_PLAYBOOK.md`, `KNIGHT_PLAYBOOK.md`) and neither
describes a machine doing both. Two real needs now want exactly that:

- **`[WORK]` the work laptop** — already described in
  `COWORK_BRIEF_governance_scanners.md` as *"a solo consumer of its own MCF threads,
  while still a producer in the wider mesh sync."* That dual role has never been
  written down as a procedure.
- **`[DEV]` the gaming rig** — a full local build, so the development loop stops
  being *commit → push → knight pull → run → read output over ssh*. This is the one
  that pays for itself daily.

**Approach ruling (Tim, 2026-07-27): docs-first.** Walk the whole loop on the rig
against a throwaway vault, then write the playbook **from what actually happened**.
Change code **only where the walk proves it necessary** — no speculative
`role: "solo"` refactor, no config vocabulary added in advance of a failure that
demands it. If the walk finds no failures, the code change set is empty and that is
the successful outcome, not a thin one.

**Read first:** `docs/PRODUCER_PLAYBOOK.md`, `docs/KNIGHT_PLAYBOOK.md`,
`docs/RUNBOOK_knight_fresh_build.md`, `docs/RUNBOOK_refresh_and_deposit.md`,
`docs/archive/COWORK_REPORT_apply_alignment.md` (the two defects it found are both
solo-relevant), and DECISIONS **0010** (the wall), **0012** (three tiers),
**0013** (serve a snapshot), **0014** (single writer), **0023** (work-estate
visibility is auth-gated).

---

## Working rules

- Stdlib-only, no new dependencies. The gate is the door: `verify.py` GREEN before
  every commit, never `--no-verify`.
- **The dev vault is a throwaway**, under its own `CHRONICLER_HOME`, never the
  knight's vault and never a path that a `deposit --push` could reach. Nothing in
  this round touches the live vault or the knight.
- The `[WORK]` profile is **written, not walked** — no work-laptop access from this
  session. Mark every work item ready to walk.
- Anything written into the playbook must have been **run**. A step nobody executed
  goes in as a marked gap, not as an instruction.

---

## Grounding — what the code already does

Established by reading the source this session. Do not re-derive it; do verify
anything you're about to depend on.

- **`config.machine()`** is keyed by `socket.gethostname()`, merged from
  `config/machines.json` (committed template) and `config/local.json` (gitignored
  override). One host = one entry = **one `role` string**.
- **`role` branches in exactly one place**: `census.run_census` chooses
  `producer_domain` (scan `roots`) or `consumer_domain` (scan `code_root` +
  `chronicler_home`). It has a `--target` escape hatch that bypasses role routing
  entirely. Everywhere else `role` is only *reported* — `deposit.py` writes it into
  the manifest, `run.py config` prints it.
- **`deposit.build_bundle`** stages `estate.json` + the latest history snapshot into
  `data/outbox/<estate>/` with a sha256 manifest. **The push is a separate step**
  (`--push`, requiring `push_target`). A machine with no push target stages
  successfully and reports it — the golden run confirmed this is a clean, expected
  path, not a failure.
- **`consume.sweep(estates_dir)`** ingests every `<estate>/` directory it finds
  under `estates_dir`, then writes shared vault-reader / project-trail reports.
- **`run.py _chronicler_env()`** maps the machine's `vault` → `CHRONICLER_DB_PATH`
  and `chronicler_home` → `CHRONICLER_HOME`. Both per-machine config, never
  hardcoded. So a solo entry plausibly just carries **both key sets**: `estate` +
  `roots` (producer) *and* `vault` + `estates_dir` + `chronicler_home` (consumer).
- **Windows interpreter**: `.venv\Scripts\python`, not the `.venv/bin/python` every
  knight-side instruction uses. `chronicler/pipeline/*.py` import `l5gntools`, so a
  bare `python` fails with `ModuleNotFoundError` (PRODUCER_PLAYBOOK §10).

**The hypothesis to test first, in Task A:** on a solo box, point `estates_dir` at
the machine's own `data/outbox` and `consume` reads its own deposit in place — no
push, no second host, no code change. If that holds, the whole loop is a config
shape and a document. If it doesn't, name precisely why before proposing code.

---

## Sharp edges that must appear in the playbook

Each was found the hard way. None should be rediscovered by a reader.

1. **A freshly built vault is not frozen.** `chronicler/pipeline/finalize_db.py`
   stamps `PRAGMA user_version = 1`; `vault_reader` and `project_trail` gate on it.
   Skip it and `consume` reports `vault: schema_mismatch` with `drift=needs_inputs`
   and no obvious cause — this cost the golden run a real debugging detour. On a
   dev rig, where vaults get rebuilt constantly, it will bite **every time**.
   `finalize_db.py --apply` belongs in the loop, not the troubleshooting section.
2. **`deposit --push` is a producer action.** Running it on the consumer side of the
   same box gets a "not configured" note that looks like a fault and isn't. Solo
   stages and consumes locally; say so plainly.
3. **`config/project_registry.json` is gitignored** — it carries employer codenames
   and is shipped by scp like `local.json`. A solo machine gets **no registry from
   `git pull`**. It must either be seeded from that machine's own scan
   (`build_registry.py`) or copied across. On the work laptop this is the difference
   between a working install and a silently empty registry.
4. **`seed_suppress` (`b7c2390`).** A deliberately-removed alias must be declared in
   the registry, or the next `build_registry.py` regenerates it. Any solo profile
   that rebuilds its own registry inherits this.
5. **Serve reads a snapshot, never the live DB** (0013), and single-writer is
   structural (0014). On one box the temptation to point something at the live file
   is much higher than on two — state the rule where a reader will meet it.

---

## Task A ▸ walk the loop on the rig, against a throwaway vault

**This is the research. The document is written from its transcript.**

Set up a second `CHRONICLER_HOME` (e.g. `C:\Users\timps\Documents\chronicler_dev\`)
and a `config/local.json` entry for the rig carrying both key sets. Then run the
sequence end to end, in Windows form, recording the **exact command and its actual
output** at each step:

`run.py config` → `run.py census` → `run.py build` → `run.py deposit` (stage, no
push) → `run.py consume` → `run.py ingest` → `finalize_db.py --apply` →
`build_registry.py` → `build_inventory.py` → `build_activity.py` →
`xref_filenames.py` → `extract_path_mentions.py` → `relink.py --out …` (dry-run
only) → `run.py serve`.

Log, for every step: did it work, did it need a workaround, and did it *lie* (report
success while doing nothing, or fail with a message that names the wrong cause).

**Acceptance:** a transcript of the full loop with real commands and real output,
plus a friction list with a named cause for each entry. The outbox-as-`estates_dir`
hypothesis is answered yes or no, with evidence.

**Stop condition:** if the loop cannot complete on the rig at all, stop and report
where it broke. A blocked walk is a result; a guessed playbook is not.

---

## Task B ▸ write `docs/SOLO_PLAYBOOK.md`

Match the shape of the two existing playbooks — numbered sections, a location map,
a **Verify** line per step, a troubleshooting section keyed to errors actually seen
in Task A. Use `[DEV]` / `[WORK]` markers the way the producer playbook uses
`RIG` / `KNIGHT`.

Must contain: what solo is and what it is **not** (a solo box is not the mesh — its
deposits reach the knight only if pushed); the expected-locations map for both
profiles; prerequisites and install; the config entry with both key sets shown in
full; the loop from Task A; the five sharp edges above; and troubleshooting.

**Acceptance:** a cold reader on a fresh machine gets from clone to a served read
surface without opening either of the other playbooks.

---

## Task C ▸ only the code changes Task A proves necessary

Every change must name the observed failure it fixes, and carry a tester. Changes
that are *plausible* but that Task A didn't force are **out of scope** — write them
up as carried-open instead.

Anticipated candidates, none authorised in advance: census role-routing on a box
that is genuinely both; a local-staging path if the outbox-as-`estates_dir`
hypothesis fails; a clearer error when `estates_dir` is unset. If a `role: "solo"`
vocabulary turns out to be genuinely needed, **that is a DECISIONS entry first** —
stop and hand it back, do not add it inside this brief.

**Acceptance:** gate GREEN; each change traceable to a line in the Task A friction
list. An empty Task C is a valid, well-evidenced outcome.

---

## Task D ▸ the `[WORK]` profile — written, not walked

The wall discipline is the part that has to be right, because this is the profile
where being wrong has consequences:

- `estate: work`, roots tagged `scope: mcf` (and `l5gn` where the laptop carries
  both, per the existing template).
- A solo work box **never** carries a personal root and **never** deposits into the
  personal namespace — `deposit`'s namespace guard enforces this, and the playbook
  must say why it exists rather than treating it as a formality (0010).
- Restate 0023: work-estate data is behind the TOTP gate even to *view*, on any
  surface that renders both estates.
- Note the registry-shipping problem (sharp edge 3) — on this machine specifically,
  the registry carries employer codenames and must not be committed.

**Acceptance:** every `[WORK]` item is marked ready to walk, with a walk-sheet Tim
can take to the laptop unmodified.

---

## Explicitly out of scope

- The two open follow-ups from DECISIONS 0017 (relink's flat-registry guard testing
  content not key presence; the scorer refusing a `link_evidence.project` key that
  isn't a link target). Real, and named — but they belong to a relink brief, not
  this one. Do not touch `relink.py` here.
- The knight's unconfigured automated off-box backup push (`backup_target` /
  `backup_transport`), carried open from the golden run.
- Any change to the deposit wall or the estate namespace rules.

---

## UAT — acceptance checks (Tim walks these)

- **`[DEV]` loop.** Following `SOLO_PLAYBOOK.md` alone on the rig, clone → served
  read surface, with no reference to the other playbooks and no undocumented step.
- **Honest failure.** Deliberately skip `finalize_db.py --apply` and confirm the
  playbook's troubleshooting entry names the resulting `schema_mismatch` correctly.
- **Isolation.** The dev vault is provably separate from anything the knight owns —
  no shared path, no push target that could reach it.
- **`[WORK]` profile.** Reads correctly against the laptop's real layout; the wall
  rules are stated, not assumed.
- **No silent code creep.** Every code change in the round appears in the report
  with the Task A failure that justified it.

Mark each **ready to walk**, never "passed". The results log must carry a uat stamp
(`commit`, `host`, `walked`, and `gate=` only if observed) or the gate refuses the
commit.

---

## Reporting

`docs/COWORK_REPORT_solo_playbook.md`, walk-sheet `docs/UAT_solo_playbook.md`,
stamped results `docs/UAT_solo_playbook_results.md`. Record the Task A transcript
and friction list, the hypothesis result, every code change with its justifying
failure, and anything carried open.

If any new doc quotes a gate count, give it the `gate-frozen` marker at the time of
writing (`auditors/auditor_doc_claims.py`) — a frozen build-time count is history,
and the next round that adds a tester should not reopen it.
