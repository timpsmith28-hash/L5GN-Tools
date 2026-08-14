# UAT walk-sheet — Project Wizard

**Brief:** `docs/COWORK_BRIEF_project_wizard.md`
**Report:** `docs/COWORK_REPORT_project_wizard.md`

**Built:** 2026-08-13, on `LucasGoonPC` (no MCF corpus on this machine).
**Gate at build time:** the auditors and testers most directly touched by
this change (`auditor_module_contract`, `auditor_dependency_direction`,
`auditor_stdlib`, `auditor_readonly`, `auditor_tool_contract`,
`auditor_doc_claims`, `auditor_uat_stamp`, `tester_module_registry`,
`tester_file_census`, `tester_census`, `tester_project_root`,
`tester_docs_board`, `tester_review_preflight`) were run individually and are
green. **A full `python verify.py` has not been run in this session** — this
build's remote-shell tooling times out before the whole auditor+tester suite
finishes in one call; run it for real on whichever rig picks this up next
before treating the gate as GREEN. **Nothing below has been walked** — this
is a skeleton, not a completed walk. Do not read a `[G]` item as passed
because the underlying code was exercised programmatically in
`COWORK_REPORT_project_wizard.md`'s "Execution, run markers, and outcome"
section — that is this module's own claim about itself, not a human's claim
about the running surface (0031).

Mark each `[G]` / `[H]` per 0031 once walked. Results log needs a `uat`
stamp naming the commit; do not write a `gate=` field.

- `[ ]` `[G]` A malformed manifest (bad JSON, missing `command`, unknown
  `schema_version`) blocks only that repo's card, with **every** validation
  error shown at once — the rest of the board renders normally.
- `[ ]` `[G]` The execute route refuses any `(repo_key, stage_key)` pair not
  present in the allowlist built from validated manifests, with no argv,
  path, or flag accepted alongside it.
- `[ ]` `[G]` A repo path not present in `project_wizard.allow.json` is
  never read, described, or executed, **even if a manifest file physically
  exists there.**
- `[ ]` `[G]` A `cwd`/`output_glob` that resolves outside its own repo's
  root (crafted relative path, or a symlink) is refused by
  `resolve_contained`, not by a bespoke check.
- `[ ]` `[G]` Triggering `sf-data-service`'s stage runs `estate refresh`
  exactly, streams its output live, and reflects `estate status`'s own
  freshness answer on the card — never a second, Project-Wizard-derived
  staleness number. **Cannot be walked yet — `sf-data-service` has no
  manifest and is not on any host's allowlist (see the report's "PricingModel
  and SolConfig discovery findings" section).**
- `[ ]` `[G]` Kill a running stage's process: the lock is left held, reported
  stale via pid+heartbeat on the next board render, and is never
  auto-reclaimed — only an explicit break action clears it.
- `[ ]` `[G]` Two clicks on the same stage in quick succession: the second is
  refused as "already running", never queued, never silently dropped.
- `[ ]` `[G]` No card offers an action that chains into another stage; there
  is no "refresh then rebuild" button anywhere in this slice.
- `[ ]` `[G]` On the gaming rig, the board renders the dev fixture and **no
  MCF repo is reachable, described, or listed** — the host entry is the only
  thing consulted.
- `[ ]` `[H]` **Walk the sf-data-service card for real** — trigger it, watch
  it stream, confirm the freshness shown afterward matches what
  `estate status` reports directly from the command line. **Blocked: no
  manifest exists for `sf-data-service` yet (report, Task 5).**
- `[ ]` `[H]` **Walk the PricingModel and SolConfig discovery findings** —
  did Task 5 correctly identify the real generator script for each, and is
  each confirmed safe to re-run before its manifest went live? **Blocked:
  the discovery step itself has not been done (report, Task 5) — there is
  nothing yet to walk.**
- `[ ]` `[H]` **Does the board tell you what you actually want to know at a
  glance** — which repos are stale, which just ran, which failed — or does
  it need another pass at the layout before it earns a spot next to the
  Knowledge Curator tab?
- `[ ]` `[H]` **Is the manifest shape something you'd want to hand-author for
  a fourth repo later**, or does Task 1's schema already feel like it's
  missing something obvious once you've lived with three real examples?
  **Only the dev fixture (two stages, one repo) exists to judge this by so
  far — worth re-asking once the three pilots are live.**
- `[ ]` `[H]` **Was the dev fixture enough to build against?** Per the
  report: yes for Tasks 1–4's own logic (manifest parsing, allowlist
  layering, containment, freshness's `self` path, the board, the lock, the
  streaming execute/outcome/marker path); **not** exercised by the fixture:
  a `"delegated"` freshness source, and a genuinely long-running stage
  proving the streaming shows progress before exit. Confirm on the rig
  that actually walks this whether those two gaps mattered in practice.

## Beyond the brief's own UAT list — worth walking too

- `[ ]` `[G]` The `project_wizard` tab appears in the tab strip, between
  Docs board and UAT sidebar, and opens onto an honest "no repos configured"
  message on a host with an empty allowlist entry (rather than a greyed-out
  tab or an error) — confirm this reads as intended on a fresh browser load.
- `[ ]` `[G]` `WizardPlanSpec.validate()` accumulates every problem in a
  malformed plan (missing `plan_id`, a step naming a pair outside a given
  `known_pairs`) rather than raising on the first — confirm this if Task 4's
  shape is ever exercised by real code, since it was only unit-checked
  against synthetic input in this build, not against a plan built from a
  live board.
