# L5GN Projects Review

**Generated:** 2026-07-10 · **Refreshed:** 2026-07-13 · **Scope:** `C:\Users\timps\Documents\GitHub`
**Method:** git metadata (latest commit / branch / history depth / working-tree state), README + design docs, and Python AST scans of each project.

**Confirmed classifications (2026-07-13):**

- **Active projects (3):** `L5GN-Continuous-Ingestion-Daemon`, `L5GN-Crystal-Spire`, `l5gn-mesh-vertex-3_prod`. Most other repos are previous iterations of these two lineages (Archive → Armory → Armory_v2 → Armory_v4 → **CID**; Castle → **mesh-vertex-3_prod**).
- **Assets, not projects:** `all-MiniLM-L6-v2` (vendored embedder, loaded by CID via `CITADEL_MINILM_PATH`), `godot-demo-projects` (upstream samples), `L5GN-server-hub-iso` (infra: ISO, Rufus, TLS material).
- **Estate tooling (new since last review):** `L5GN-Tools` — the cross-repository scanner toolkit, covered below.

> Note on line counts: `L5GN-Castle` and `L5GN_Armory_v4` bundle their virtual-env / `site-packages` and model files, so raw AST class counts run into the thousands. The "real" project code (excluding vendored deps) is ~89 and ~112 `.py` files respectively — the figures in prose below refer to your own code, not the vendored libraries.

---

## Projects table

| Project | Status | Latest commit | Date | Branch | Commits | Working tree | Remote |
|---|---|---|---|---|---|---|---|
| **L5GN-Continuous-Ingestion-Daemon** | **Active** | `32b3826` — *feat(library): task cards — ADR-0020* | 2026-07-03 | main | 52 | 228 dirty | `L5GN-Continuous-Ingestion-Daemon.git` |
| **l5gn-mesh-vertex-3_prod** | **Active** | `be2b0d2` — *aligned to mesh network llm capability routing* | 2026-06-11 | master | 136 | 45 dirty | *(no remote)* |
| **L5GN-Crystal-Spire** | **Active** | *(not a git repo — file snapshot)* | newest file 2026-07-10 | — | — | — | — |
| **L5GN-Tools** | **Active (estate tooling)** | `7c7f008` — *feat: CID-ready tool contract + pip packaging* | 2026-07-10 | main | 2 | clean | *(no remote)* |
| **L5GN_Armory_v4** | Prior iteration → CID | `0e21976` — *prototype: Added doc_census_scanner.py to root* | 2026-06-24 | main | 80 | 386 dirty | `L5GN_Armory_v4.git` |
| **L5GN-Armory_v2** | Prior iteration → CID | `2b44083` — *refactor: centralize plugin lifecycle contracts, unify theme/event matrices* | 2026-06-16 | main | 10 | 77 dirty | `L5GN-Armory_v2.git` |
| **L5GN-Armory** | Prior iteration → CID | `488df20` — *feat(ui): scale tier 2 architecture (terminal log + artifact ledger plugs)* | 2026-06-14 | main | 6 | 83 dirty | `L5GN-Armory.git` |
| **L5GN-Archive** | Prior iteration → CID (snapshot) | *(not a git repo — file snapshot)* | newest file 2026-06-22 | — | — | — | — |
| **L5GN-Castle** | Prior iteration → mesh-vertex | `96d099a` — *core catchup* | 2026-06-04 | main | 12 | 378 dirty | `l5gn-mesh-vertex-3_v0.git` |
| **L5GN_Managed_Workspace** | Supporting / ingestion source | `4247770` — *first UCP attempt* | 2026-05-29 | main | 3 | 29 dirty | `L5GN_Managed_Workspace.git` |
| **L5GN-server-hub-iso** | **Asset** (infra) | *(not a git repo — infra assets)* | newest file 2026-06-13 | — | — | — | — |
| **all-MiniLM-L6-v2** | **Asset** (3rd-party embedder) | `1110a24` — *Add base_model metadata* (Tom Aarsen) | 2026-06-01 | main | 31 | 25 dirty | `huggingface.co/sentence-transformers/all-MiniLM-L6-v2` |
| **godot-demo-projects** | **Asset** (3rd-party samples) | `ee4f6ec4` — *Merge PR #1318 (fix state machine start state)* | 2026-05-14 | — | — | — | `godotengine/godot-demo-projects.git` |
| **test_folder** | Scratch | *(not a git repo — scratch/snapshot)* | newest file 2026-06-28 | — | — | — | — |

*(Also present in root: `Godot_v4.6.3` engine executables — tooling, not a project.)*

---

## What each project is for

### The Citadel MicroIDE line — your Prompt → Context Engineer's IDE lineage

**L5GN-Archive** — The earliest surviving snapshots of the MicroIDE idea (v1.x). A CustomTkinter/CTk desktop shell (`CitadelMicroIDE`, `CoreAppWindow`, `CitadelMatrixState`, `CitadelForgeEngine`) built around a thread-safe event bus and a "plug" UI pattern (`BaseCitadelPlug`, `ArtifactLedgerPlug`, `ControlPanel`). It already contains the whole vocabulary you keep — forge engine, artifact ledger, personas, workspace scanner — plus a fleet of `forge_*` scrapers/generators that turn raw chat/history into JSON. Think of this as the concept's fossil record: multiple `citadel_deck` versions (v1, v1.5, v2, v3_core) sitting side by side.

**L5GN-Armory** — The first properly git-tracked rebuild of that concept into a clean `core/` layout. Same event-bus + plug architecture, but now with formal contracts: `EventBusProtocol`, `BaseCitadelPlug`, a `PipelineOrchestrator`/`pipeline_runner`, and — notably — a `CitadelContextCompiler` and `ChainExecutor`/`ChainStep`/`ChainRequest`, which is where the "compile context, run a chain of LLM steps" idea starts to crystallise. Small (6 commits) but architecturally deliberate.

**L5GN-Armory_v2** — A consolidation pass over Armory. The commit history is explicitly about hardening the plug lifecycle (`BasePlug`, `AppWindowPlugs`, `AppWindowLayouts`, `AppWindowThemes`), unifying theme/event matrices, and fixing thread-safety bugs (consultant log multiplication, terminal queue polling, forge worker init). Adds `AgentNode`, `ConsultantPlug`, `BaseChain` and an integration-test harness (`CitadelIntegrationTest`). This is the "make the plugin system trustworthy" iteration.

**L5GN_Armory_v4** — The most mature MicroIDE and the current flagship of this line. The README is a real architecture spec: an event-driven, single-process desktop IDE for **orchestrating a local AI mesh**. It codifies three "architectural laws" (logic-separation between transient `tools/` and resident `core/services/`; an event nervous system of typed enums + frozen payloads; UI-thread safety), enforced by static AST auditors. Real services now exist — `InferenceService` (capacity-aware routing across mesh nodes), `DocumentService` (declarative multi-stage forge chains with chunking + resume), a `CIDMonitor`/`AgentLoop` persona with an approval gate, and a `ForgeEngine` worker pool. `README_THE_FUTURE.md` casts the AI collaborator as "Clyde" and lays out the L5GN development protocol. This is where the IDE stops being a UI shell and becomes an orchestration platform.

**L5GN-Continuous-Ingestion-Daemon (CID)** — The newest evolution (Citadel v5, most recently active at 2026-07-03) and arguably the conceptual leap toward "context engineering." It keeps v4's laws but inverts the frame: instead of a human driving a UI, an **always-on orchestrator** on a headless node ("the Knight") continuously ingests, aligns, and assimilates knowledge/code into a governed, **contract-first, vault-backed** core, dispatching heavy inference to a pool of endpoints. Persistence is principled (ADR-driven): `.md` Vault = source of truth, vector Index = derived/rebuildable, SQL only for relational state. It's "assisted-first" (CID proposes, a human adjudicates). The `docs/ROADMAP-blueskies.md` "Librarian / Scanner Planner / chat-log path" ideas — *give the system context before judgment* — are essentially a manifesto for the Context Engineer's IDE.

### The Castle / mesh-vertex ingestion line

**L5GN-Castle** — A service-oriented content-processing and knowledge-management backend. Distinct "Floors" (blueprint ingestion, archival sharder, archival triage) feed centralised `core/` services — `InferenceService`, `Dispatcher`, `ContentVault`, `TelemetryCollector` — with a FastAPI `api/` layer and a SQLite `castle.db`. Its remote is `l5gn-mesh-vertex-3_v0`, marking it as the v0 of the mesh-vertex backend. (Working tree carries a bundled venv, hence the large vendored class count.)

**l5gn-mesh-vertex-3_prod** — The productionised, containerised descendant of Castle: `Dockerfile.gateway` + `Dockerfile.worker` + `docker-compose.yml`, a `core/sieve` (SieveSharder, PipelineRunner, SieveTriageFilter), `core/conduit` (Dispatcher, CastleSortingOffice), and a `MeshRouter` for LLM capability routing across nodes. The deepest history here (136 commits on `master`) suggests this is where the ingestion→mesh pipeline was actually driven to a running state. No remote configured — local production line.

**test_folder** — Not a real project: a Castle README snapshot plus a couple of `forge_scraper_to_json` / `extract_deep_git_history` utilities and Gemini conversation exports. Scratch/staging area.

### Cross-repository tooling — new since the last review

**L5GN-Tools** — The answer to the "three copies of `workspace_scanner`" problem flagged below: one estate-level, **read-only** scanner toolkit at the GitHub root that runs against any sibling folder (`--target <name>` or `--all`). Ten tools behind a single CLI contract (workspace_scanner, git_summary, git_deep_history, doc_census, import_scanner, env_scanner, bloat_audit, todo_adr_scanner, plus estate-level estate_status and duplicate_finder), a `verify.py` gate with auditors enforcing the read-only / stdlib-only / CLI contracts (pattern borrowed from CID), and a self-contained `report.html` estate dashboard. Crucially it's already **bridged into CID**: `pip install -e ../L5GN-Tools` exposes the scanners as gated CID BaseTools via a `ToolHostService` seam — adding a scanner to the registry makes it appear in CID automatically. This is the first piece of tooling that genuinely works *across* repositories rather than being copy-pasted into each. Clean working tree, 2 commits, no remote yet.

### Supporting / infrastructure

**L5GN_Managed_Workspace** — The "Garrison" scaffolding foundry: a pipeline-driven project generator. A `FoundryEngine.run_pipeline()` runs a chain of callable `System` classes (Git init, environment init, project config, blueprint ingestion, atomizer, complexity planner, documentation init) with an `AI_Interface` abstraction over LLM vendors and a `prompt_loader`. This is the "spin up a new governed workspace" tooling that the other repos assume exists.

**L5GN-server-hub-iso** — *Confirmed: asset, not a project.* Not code: the physical/infra side of the mesh. An Ubuntu 20.04 server ISO, Rufus (USB imaging), and `l5gn.com` TLS key/cert material — i.e. the bits for standing up the self-hosted hub the mesh runs on. ⚠ Note: private TLS key material sitting in a general working folder is worth moving somewhere access-controlled.

**L5GN-Crystal-Spire** — A creative side-project, and a fun one: a solo terminal dungeon-crawler whose world is generated *from the estate's own project history*. Each era is a wing, each delve a themed descent, each floor built from your real documents ("the loot is the estate's real paperwork reframed as treasure"). One `Engine`, one `savegame.json`, a Textual TUI plus a plain REPL, a curated 17-delve/425-floor "spine," and a similarity-scan tool to route the campaign. Most recently touched folder (2026-07-10). Not the IDE lineage, but it reuses the same forge/sharding instincts on your own corpus.

### Third-party assets (confirmed — vendored, not your work)

**all-MiniLM-L6-v2** — Cloned Hugging Face sentence-embedding model (sentence-transformers). Almost certainly the embedder backing the CID/Castle vector Index. Last commit is upstream's, not yours.

**godot-demo-projects** — Cloned Godot engine sample projects (upstream `godotengine`), alongside the Godot 4.6.3 executables in root. Unrelated to the L5GN system — likely game-dev exploration adjacent to Crystal Spire.

---

## Consolidation notes — toward the Context Engineer's IDE

Two parallel evolutionary tracks are visible, and they're converging:

1. **The UI / orchestration track** (Archive → Armory → Armory_v2 → **Armory_v4**): a desktop MicroIDE that grew a rigorous event-bus + plug + services architecture and a local-mesh inference router.
2. **The ingestion / knowledge track** (Castle → **mesh-vertex-3_prod**, plus MiniLM as the embedder): a sharding/triage/vault pipeline with mesh routing.

**L5GN-Continuous-Ingestion-Daemon (CID / Citadel v5)** is the first repo that fuses both — v4's architectural laws with Castle's ingestion mission — under a contract-first, vault-as-source-of-truth, assisted-first governance model. If you're building the Context Engineer's IDE, CID is the strongest trunk to grow from, with **Armory_v4** contributing the mature UI/plug/mesh-routing layer and **Managed_Workspace** contributing project scaffolding.

Redundancy worth resolving before consolidation:

- Three+ copies of the same primitives (`workspace_scanner`, `forge_scraper_to_json`, `extract_deep_git_history`, `citadel_archetypes.json`, `ExecutionContextComponent`/`ResponseComponent` handover schema) exist across Archive, Armory*, Castle, mesh-vertex, Managed_Workspace and test_folder. CID's own roadmap flags this exact problem (the "`workspace_scanner.py` lands three times as three unrelated artefacts"). **Update 2026-07-13: L5GN-Tools now resolves this** — the scanners live once at the estate root and take the target repo as a parameter; the legacy copies can be deleted as part of the freeze pass.
- Two overlapping `InferenceService` implementations (Castle/mesh-vertex vs. Armory_v4/CID) with different routing models — pick the capacity-aware mesh router from v4/CID.
- `L5GN-Archive`, `test_folder`, and `L5GN-Castle` are effectively superseded snapshots; safe to freeze/archive once their unique utilities are lifted out.
- Several repos carry very large dirty working trees (Armory_v4: 386, Castle: 378, CID: 228) and bundled venvs/models in git — a `.gitignore` + commit pass would make the lineage far easier to reason about.

---

## Proposed next design specs (per active project)

### L5GN-Continuous-Ingestion-Daemon (CID / Citadel v5)

Current state (per `docs/HANDOFF.md`, ADR-0001…0021): pipeline hardened end-to-end — git-scoped ingest, content-hash dedup, secret quarantine, Librarian dedup clustering + task cards, chat-log route (skips Reconcile, lands library cards), Scanner Planner (import in-degree ordering), and the L5GN-Tools bridge. Proposed next specs:

1. **Librarian write path (supersede, don't edit).** ADR-0017/0020 built the read-only curator; the open decision from `ROADMAP-blueskies.md` is the promotion path when a human accepts a consolidation. Spec: Librarian always lands a *new* superseding artefact rather than mutating landed `.md` — keeps "Vault = source of truth, append-friendly" intact and reuses ADR-0011's jailed writer as-is.
2. **Batch ingestion Service.** `demo.py` is still the driver for estate migrations. Spec: promote it to a gated `MigrationService` that consumes a Scanner Planner plan per target repo, with resume + per-repo provenance, so legacy repos (Armory line, Castle, Managed_Workspace, test_folder) can be assimilated then frozen.
3. **Estate-aware ingestion via L5GN-Tools.** The bridge exists; the next rung is CID using `duplicate_finder`/`estate_status` output to pre-plan a migration ("these 3 copies of `forge_scraper_to_json` are byte-identical — ingest once, cross-reference twice").

### l5gn-mesh-vertex-3_prod

Deepest history (136 commits), but stalled since 2026-06-11 and **no remote** — one disk failure loses the whole production line. Proposed next specs:

1. **Push to a remote** (private GitHub, matching the others) — cheapest insurance available.
2. **Define its role relative to CID.** Two clean options: (a) mesh-vertex becomes CID's *Pool* — MeshRouter fronts the LM Studio endpoints and CID rents inference through it; or (b) its unique pieces (MeshRouter capability routing, containerised gateway/worker split) get assimilated into CID and the repo is frozen like Castle. Option (a) preserves the two-track architecture (orchestrator vs. mesh) and matches CID's "rent heavy inference from a Pool" framing.
3. **Deploy target spec:** docker-compose onto the server-hub hardware (the ISO/TLS assets exist for exactly this), giving the Knight a real headless node.

### L5GN-Crystal-Spire

Beta ("act one": Founding the Empire + The Manifesto Reborn) is built, with GDD, spine, era digests, and a mostly-ticked playtest checklist. Proposed next specs:

1. **Git-init and commit.** It's the most recently active project and the only active one with no version control at all.
2. **Finish the beta gate:** the remaining unticked checklist items (e.g. `help` completeness), then cut the act-one release from `CrystalSpireBeta.zip`.
3. **Act two content pipeline:** eras 3+ from `SPINE.md` via `forge_v2.py`.
4. **Longer-term convergence spec:** regenerate the world graph from the CID Vault instead of static forge output — the Spire becomes a *view* over the governed estate corpus, which is the same "context before judgment" idea wearing a game skin.

---

## Suggested additions beyond current scope

- **Estate hygiene pass:** ~1,226 dirty files across 7 repos (per `L5GN-Tools/data/estate_status.json`). A `.gitignore`-and-commit sweep — `bloat_audit` already pinpoints the tracked venvs/models — would make every lineage question answerable from git alone.
- **Remotes everywhere:** mesh-vertex-3_prod and L5GN-Tools are the two repos that matter most without off-machine backup.
- **Freeze protocol:** once CID assimilates their unique utilities, formally archive Archive/Armory/Armory_v2/test_folder (README banner + final commit + GitHub archive flag) so the estate map stays legible.
- **Scheduled estate dashboard:** `python run.py build` in L5GN-Tools regenerates `report.html`; running it weekly (or on demand from Cowork) keeps this review's table from going stale — this document could then link to the live report instead of freezing numbers.
- **Secrets sweep:** `env_scanner` flags exposure by name; the server-hub TLS keys are the known offender. Worth one deliberate pass.
- **Per-repo `CLAUDE.md`:** CID's doc culture (HANDOFF + GLOSSARY + ADRs) is what makes it easy to resume; a minimal version in mesh-vertex and Crystal Spire would pay for itself in one session.

---

*Original review only read the repositories. 2026-07-13 refresh edited this document only — no project files were modified.*
