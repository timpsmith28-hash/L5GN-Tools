# Registry ratification worksheet — 2026-07-25

The reconciliation decision session. Prepared from the first registry build that
could see **both** estates. A Cowork thread can lay the table out; **the rulings
are Tim's** — tick each row, then apply them by editing the curated source
`config/project_registry.json` and re-running `build_registry.py`.

**Inputs**

- `personal` estate — generated 2026-07-25T10:00:04+01:00, 8 projects (gaming rig,
  retargeted to `…/GitHub/L5GN`).
- `work` estate — generated 2026-07-25T10:23:10+01:00, 19 projects (`10280L`,
  roots MCF + L5GN). **First-ever work deposit** — this is what unblocked the MCF
  half of the registry.
- Registry dry-run: **42 project entries** (18 curated/manual + 24
  auto-from-deposit), 10 unmapped Claude-project names, both consumes
  `verified=True`.

**How to read a row.** An `auto` entry carries a real **repo** (paths, git dates)
but no curated home. A `manual` entry carries the curated **group** and intent
but no repo. Reconciliation = joining the two where they're the same project, and
placing the rest. Ruling column: `✓` accept proposal · `✗` reject · or write the
alternative.

---

## A. Clean merges — auto repo into its curated MCF entry (5)

Same canonical name; the curated entry already sits in group **MCF**. Merge the
auto repo's facts into the manual id; drop the standalone auto id.

| Auto id (repo) | → Curated id | Name | Repo first_seen | Ruling |
|---|---|---|---|---|
| `activitystatements` | `mcf-activity-statements` | ActivityStatements | unknown (non-git) | ☐ |
| `pricingmodelisation` | `mcf-pricing-modelisation` | PricingModelisation | 2026-07-22 | ☐ |
| `solconfig` | `mcf-sol-config` | SolConfig | 2026-07-22 | ☐ |
| `tsstoassets` | `mcf-tss-to-assets` | TSsToAssets | unknown (0-commit) | ☐ |
| `validationautomation` | `mcf-validation-automation` | ValidationAutomation | 2026-07-24 | ☐ |

## B. Merges the matcher missed — name/typo mismatch (3)

Real duplicates the auto-join couldn't see because the names differ.

| Auto id (repo) | → Curated id | Why it didn't auto-match | Ruling |
|---|---|---|---|
| `churnlevelindictor` (ChurnLevelIndictor) | `mcf-churn-level-indicator` (**ChurnLevellIndictor**) | double-L typo in the curated name — merge **and** fix the typo | ☐ |
| `l5gn-crystal-spire` (repo, personal+work) | `crystal-spire` (Claude-project, L5GN) | curated name is the Claude short form "Crystal Spire" | ☐ |
| `chronicler` (repo, work, scope l5gn) | `l5gn-tools-chronicler` **or** `chronicler-gas`? | two curated Chronicler concepts exist; pick the one this repo *is* | ☐ (which: ______) |

## C. Unclaimed repos — assign each to a program (16)

Real deposited repos with no curated entry. Proposed program follows the deposit
scope; confirm or redirect. (Repos in **both** estates noted — they live on the
gaming *and* work rig.)

### L5GN scope → propose program **L5GN** (13)

| Auto id | Name | Estates | first_seen | Ruling (program) |
|---|---|---|---|---|
| `l5gn-armory` | L5GN-Armory | personal | 2026-06-13 | ☐ |
| `l5gn-armory-v2` | L5GN-Armory_v2 | personal | 2026-06-15 | ☐ |
| `l5gn-armory-v4` | L5GN_Armory_v4 | personal+work | 2026-06-17 | ☐ |
| `l5gn-archive` | L5GN-Archive | personal | unknown (non-git) | ☐ |
| `l5gn-castle` | L5GN-Castle | personal | 2026-05-29 | ☐ |
| `l5gn-continuous-ingestion-daemon` | L5GN-Continuous-Ingestion-Daemon (CID) | personal | 2026-06-26 | ☐ |
| `l5gn-bridge` | L5GN_Bridge | work | unknown (non-git) | ☐ |
| `l5gn-managed-workspace` | L5GN_Managed_Workspace | personal+work | 2026-05-28 | ☐ |
| `smelt-gateway` | smelt-gateway | work | 2026-05-29 | ☐ |
| `desktopsanddungeons` | DesktopsAndDungeons | work | 2026-05-16 | ☐ |
| `gemtopairs` | GemToPairs | work | 2026-06-24 | ☐ |
| `v1-proto` | v1 proto | work | unknown (non-git) | ☐ |
| `vba-json` | VBA-JSON | work | **2014-09-15** (oldest repo) | ☐ |

### MCF scope → propose program **MCF** (3)

| Auto id | Name | Estates | first_seen | Ruling (program) |
|---|---|---|---|---|
| `gulamdataexport` | GulamDataExport | work | unknown (non-git) | ☐ |
| `unifedintelligencesource` | UnifedIntelligenceSource | work | unknown (non-git) | ☐ |
| `wizforgeanalytics` | WizForgeAnalytics | work | unknown (non-git) | ☐ |

## D. Curated entries with no deposited repo (10)

These carry intent but no repo facts. Decide: keep as a concept, mark as
awaiting-a-repo, or (for real ones) arrange a deposit.

| Curated id | Name | Group | Note / proposal | Ruling |
|---|---|---|---|---|
| `l5gn-tools` | L5GN Tools | L5GN | the toolkit itself — **self-excluded from scans**, so it will never auto-appear; keep manual | ☐ |
| `vertex-3` | Vertex-3 | L5GN | = `mesh-vertex-3_prod`, **never deposited** (knight-slaved, un-moveable). Repo-less until scanned as a 2nd root or from the knight | ☐ |
| `mcf-data-access-layer` | DataAccessLayer | MCF | no repo in either estate — confirm it exists / should be deposited | ☐ |
| `l5gn-tools-chronicler` / `chronicler-gas` | Chronicler (2026) / (GAS-era) | L5GN | whichever the `chronicler` repo (§B) is *not* | ☐ |
| `auditor-arbiter` | Auditor | L5GN | Claude-project concept; keep | ☐ |
| `chancellor` | Chancellor | L5GN | Claude-project concept; keep | ☐ |
| `l5gn-mesh-network` | L5GN Mesh Network | L5GN | concept; keep | ☐ |
| `l5gn-os` | L5GN OS | L5GN | concept; keep | ☐ |
| `universal-content-pipeline` | L5GN Journal / Universal Content Pipeline | L5GN | concept; link target for "UCP …" Claude names (§E) | ☐ |
| `learning-ai-and-computers` | Learning about AI and computers | L5GN | generic; keep or retire | ☐ |

## E. Unmapped Claude-project names → link target (10)

Chat-vault project names that matched no repo. Proposals are inference from the
name — **confirm each**, since these drive how threads link to projects.

| Claude project name | Proposed target | Confidence | Ruling |
|---|---|---|---|
| `CitadelMicroIDE` | `l5gn-continuous-ingestion-daemon` (CID) | high | ☐ |
| `CitadelMicroIDE v4` | `l5gn-continuous-ingestion-daemon` | high | ☐ |
| `CID v4.1` | `l5gn-continuous-ingestion-daemon` | high | ☐ |
| `CID v5.0` | `l5gn-continuous-ingestion-daemon` | high | ☐ |
| `Solution Configurator` | `mcf-sol-config` (SolConfig) | high | ☐ |
| `MCF Solution Configurator` | `mcf-sol-config` | high | ☐ |
| `UCP Personal Smelter` | `universal-content-pipeline` | medium | ☐ |
| `L5GN Tools Mobile` | `l5gn-tools` | medium | ☐ |
| `How to use Claude` | (none — generic, not a project) | — | ☐ |
| `MCF Solution Configurator` (2nd, malformed id) | see §F | — | ☐ |

## F. Data hygiene & deposit gaps (record, not urgent)

- **Malformed project_id.** `MCF Solution Configurator` appears twice in the
  unmapped list — one entry's `project_id` is the literal display name
  (`"MCF Solution Configurator"`), the other is `mcf-solution-configurator`.
  Collapse to one; fix the display-name-as-id in the vault's `projects` table.
- **Undated S3 windows (vcs=none).** Non-git folders deposit no git dates, so
  their activity window is undated: `L5GN-Archive`, `ActivityStatements`,
  `Chronicler`, `GulamDataExport`, `L5GN_Bridge`, `UnifedIntelligenceSource`,
  `v1 proto`, `WizForgeAnalytics`. If any should have history, it needs to be a
  real git repo before the next deposit.
- **`TSsToAssets` (vcs=git, 0 commits).** Recognised as a git repo but has no
  commits, so still undated — and it's the live carrier of the 0-commit note.
- **`VBA-JSON` first_seen 2014-09-15.** Legitimately the oldest repo; not an
  error, just the outlier to expect in any "earliest activity" view.

## G. Applying the rulings & what's still open

**To apply.** Edit the curated source `config/project_registry.json` (not the
generated `.intel_sync/project_registry.json`): fold §A/§B repos into their
curated ids, set the §C programs, add the §E aliases to their targets. Then
`ssh l5gn-castle` → `.venv/bin/python chronicler/pipeline/build_registry.py`
(re-run `--report-aliases` first to confirm the unclaimed/unmapped lists shrink
as expected). Ship the edited config out with
`scp config/local.json …` / the curated registry per KNIGHT_PLAYBOOK §8.

**Still open after this session (by design, not a miss):**

- **Relink scoring fix.** `relink` was *skipped* this run (no input), so no link
  writes happened. The double-count / 0.997-from-one-sentence fix
  (`SIGNAL_COUNT_CAP`, dry-run-before-apply) remains its own brief — the
  highest-value unwritten one. Ratifying this registry is the input it needs, not
  a substitute for it.
- **Two convention tweaks** (from the work-rig walk): give `upload_r141`-style
  prod aliases a literal form if you want blast-radius to escalate them to `prod`
  tier; align `ValidationAutomation`'s `DECISIONS.md` entry headings to
  `## <NNNN> — …` if you want its decisions counted. Neither blocks anything.
- **Castle / Chronicler `.gitignore`.** The one remaining scope leak on each rig
  is a chat archive inside a non-git-ignored folder — one `.gitignore` line each,
  your ruling.

---
*Prepared 2026-07-25 against toolkit `1951cfe`, registry dry-run (42 entries).
Rulings are Tim's; this sheet records the options, not the decision.*
