> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_toolkit_self_scan.md` + `COWORK_REPORT_toolkit_self_scan.md`, walked 2026-08-01
> Superseded by `L5GN-Tools` now being scanned as a normal project (`is_project: true` in the machine config) · Original purpose: close **0020**'s own noted gap — the toolkit could not see its own write-and-execute-heavy code.
> Accurate history: the argument that `l5gn-tools` had zero repos and no deposit, so `filename_xref` — the strongest automatic link signal — was structurally unavailable for the most-discussed project in the vault. **Stop trusting:** the registry state it describes; the config has moved since.

# Cowork brief — the toolkit sees itself

**Origin:** design thread, 2026-07-28. Long overdue: flagged in **DECISIONS 0020's
own context** — *"the governance direction requires the toolkit to see its own
most write-and-execute-heavy code, which today it does not (the toolkit's own repo
is outside any scanned root)."*
**Deliverable:** `L5GN-Tools` is scanned as a normal project on the gaming rig.

**The sharpest argument is not governance, it is linking.** `config/project_registry.json`
carries `l5gn-tools` as a project with **zero repos and no deposit**, so it has no
`file_inventory` — which means `filename_xref`, the strongest automatic link
signal in the system, is **structurally unavailable for it**. Meanwhile it is
almost certainly the most-discussed project in the vault: 33 Cowork sessions and
26 CLI transcripts, overwhelmingly about `verify.py`, `relink.py` and
`DECISIONS.md`. Not one of those filenames can produce a single piece of evidence
today. Self-scan closes a real hole in the evidence pipeline.

**Read first:** DECISIONS **0020** (context paragraph especially), **0012**
(three tiers), **0010** (the wall), `l5gntools/scanners/_scope.py`,
`config/machines.json` / `local.json` shape, and
`archive/COWORK_REPORT_apply_alignment.md`'s `seed_suppress` finding.

---

## Rulings already taken

| Question | Ruling |
|---|---|
| Shape | **A normal project**, scanned like any other — not a separate `selfscan` artefact. Only a real deposit produces the `file_inventory` this exists to create. |
| Which machine | **The gaming rig only** (`LucasGoonPC`), following 0020's "scanned from the personal rig only" precedent. |
| Why one rig | Two rigs depositing the same repo produces the same project under two estates — the duplicate-identity mess 0011 and 0017 cleaned up. Do not re-create it. |

---

## Working rules

- Read-only, stdlib-only, gate GREEN before commit.
- **Config change on one machine, not a code change** wherever possible. If code
  changes are needed, each must be justified by an observed failure.
- The toolkit is scanned *by itself while running*. Treat every result as suspect
  until the hygiene checks in Task 2 pass.

---

## Task 1 ▸ add the root, and get the registry right

The gaming rig's roots point at `…/Documents/GitHub/L5GN`; the toolkit sits beside
it at `…/Documents/GitHub/L5GN-Tools`, outside every root.

- Add it as a **tagged root** (`scope: l5gn`) in the gaming rig's `config/local.json`
  entry — or, if the parent `GitHub` folder would drag in unrelated siblings, add
  the toolkit path specifically. Choose and say which, with the folder listing
  that justifies it.
- **Registry:** `l5gn-tools` exists as a project with no repos. After the first
  scan it will have a deposit named `L5GN-Tools`. Per 0012 it needs its repo-tier
  entry so the deposit binds to the existing project id rather than generating a
  second identity. **Run `build_registry.py --report-aliases` first and read it
  before writing anything.**
- **Alias hygiene — expect a `seed_suppress` case.** `seed_aliases()` strips
  generic prefix tokens (`l5gn`, `mcf`) to derive a short alias, so `L5GN-Tools`
  will derive **`Tools`**. That is common English and will behave exactly like the
  `Castle` false-positive that contaminated the golden apply (six threads
  auto-linked on zero real evidence, `b7c2390`). Add
  `seed_suppress: ["Tools"]` and say so in the report. Consider `low_signal_body`
  as well: every thread about every project mentions the toolkit in passing.

## Task 2 ▸ hygiene — prove the self-scan isn't scanning its own exhaust

The toolkit generates into itself. Confirm, with evidence, that each of these is
excluded and say by which mechanism:

- `data/` (gitignored — the scanners' own output, including `estate.json`)
- `report.html` (gitignored)
- `.venv`, `__pycache__`, `*.egg-info` (`is_ignored_dir`)
- `chronicler/**` runtime data (gitignored: `*.db`, `raw_*`, `scraped_gemini`,
  `serve-snapshot`, `manifest.jsonl`)
- `config/local.json`, `config/project_registry.json` (gitignored — **and the
  registry carries employer codenames, so a leak here is the one that matters**)

**Then check for the reflexive case:** does the scan pick up `docs/archive/`
and `docs/investigation/`? Both are legitimate content, not exhaust — but they
will move the toolkit's document counts significantly and the report should say
what it decided and why.

`auditor_readonly` is unaffected: it audits **scanner source** for write calls,
not scan targets. Confirm rather than assume.

## Task 3 ▸ read what it says about itself, honestly

This is the point of the exercise. Record, and do not soften:

- **`blast_radius`.** The toolkit is the estate's most write-and-execute-heavy
  code — `relink.py --apply`, `finalize_db.py --apply`, `run.py ingest`,
  `deposit --push`, every `dbsafe` writer. **Expect it to light up, and expect it
  to be the highest-tier result in the whole estate.** That is the true picture,
  and the first time the instrument has been measured. Report the tiers verbatim.
- **`doc_census`.** ~84 authored documents, 74 classified in the doc round's own
  measurement against this repo. The estate median is 26 and `out_of_band`'s
  3× threshold is 78 — **the toolkit will trip the anomaly flag immediately.**
  That is correct behaviour on a genuinely doc-heavy project, but it means the
  threshold should be re-examined with the toolkit in the population. Report the
  new median and whether the rule still discriminates.
- **`todo_adr_scanner`.** The toolkit's own `DECISIONS.md` uses `## NNNN — …`,
  so `decisions_count` should be **non-zero for the first time on a real scan** —
  the counter that has never once fired (see `archive/COWORK_BRIEF_governance_scanners.md`'s
  stamp). Confirm it, and report the number against `verify`-time expectations.
- **`env_scanner`, `duplicate_finder`, `import_scanner`, `file_census`** — record
  what they say. Anything embarrassing is a finding, not something to tidy first.

## Task 4 ▸ the linking payoff, measured

The reason for all of it:

- After the scan and deposit, confirm `build_inventory.py` gives `l5gn-tools` a
  real `file_inventory` — **record the file and basename counts.**
- Run `xref_filenames.py` **dry-run** and record how many `filename_xref` rows now
  land on `l5gn-tools` that previously could not exist. `verify.py`, `relink.py`,
  `DECISIONS.md`, `SOLO_PLAYBOOK.md` are the obvious carriers.
- **Do not `--apply` and do not run relink.** This brief measures the payoff; it
  does not change any link. That is a separate, deliberate act with its own
  dry-run gate.

---

## Stop conditions

- **The registry generates a second identity** for the toolkit rather than binding
  to `l5gn-tools` → stop, report, do not deposit.
- **Anything gitignored turns up in the scan output** → stop; that is a scope
  defect, and the registry case is a disclosure defect.
- Adding the root pulls in unrelated sibling folders → stop and re-scope the root.

## Explicitly out of scope

- Any `--apply` on evidence or links.
- Scanning the toolkit from the work rig or the knight.
- The docs board (its own brief) and anything in the local-deck slices.
- Fixing whatever the self-scan finds. **Measure first; the findings are the
  deliverable.**

---

## UAT — acceptance checks (Tim walks these)

- `L5GN-Tools` appears as a project in the estate report with sane counts.
- **Nothing gitignored appears** — especially not `config/project_registry.json`
  or `config/local.json`.
- The registry binds the deposit to the existing `l5gn-tools` id; no second entry.
- `Tools` is **not** a live alias (`seed_suppress` holding, `--report-aliases`
  shows the curated list).
- `blast_radius` on the toolkit reads as true — the dangerous operations are the
  ones flagged, and nothing important is missing.
- `decisions_count` is non-zero for the toolkit.
- `l5gn-tools` gains a `file_inventory`, and the S4 dry-run shows evidence rows
  that were previously impossible.
- The estate's `out_of_band` rule still discriminates with an 84-doc project in
  the population.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_toolkit_self_scan.md`, walk-sheet
`docs/UAT_toolkit_self_scan.md`, stamped results after the walk. Record every
scanner's verdict on the toolkit verbatim, the alias decisions, the before/after
linking numbers, and anything the toolkit says about itself that we would rather
it hadn't.
