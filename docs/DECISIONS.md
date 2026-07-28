# DECISIONS

Append-only. Each entry records a decision and — more importantly — *why*, because
git records the what and the design docs record the shape, but neither holds the
reasoning. Entries are never edited once written; a later decision **supersedes** an
earlier one by adding a new entry that says so. If you're tempted to change an entry,
you want a new entry.

This is the doc that exists because the reasoning behind `similarity_threshold = 0.6`
and the vocabulary rollback was *nearly* lost — found in a schema comment, not here,
and the evaluation data behind it is gone for good. That near-loss is the whole
argument for this file.

Format per entry: **context** (what forced the decision), **decision** (what we
chose), **consequences** (what it commits us to, including the bad parts).

---

## 0001 — Conditional file-wins supersedes design §13.3's "unconditional"

**Date:** 2026-07-18 · **Status:** accepted · **Source:** cold-read investigation
`docs/chronicler_investigation_2026-07-18.md`, Task 1

**Context.** The Chronicler design doc (§13.3) specifies the sync-back rule as "file
wins, unconditionally" — an Obsidian frontmatter edit always overrides the DB. The
implemented code does something different and stronger: file wins *only when the
field changed since the last render*, tracked via a 3-way base in `render_log`. The
design and the code disagree.

The disagreement is not academic. The original "unconditional" rule caused the
133-link incident: after a pipeline wrote fresh links to the DB, the on-disk
frontmatter was stale (`project_link: null`); the next render read those stale nulls
back "as if a human had typed them" and clobbered 133 real evidence links to NULL,
logging 359 bogus `manual_override` rows. (Recovery succeeded — the live DB now
carries 0 `manual_override` rows and 0 clobber-signature threads.)

**Decision.** The **code is authoritative**; design §13.3's "unconditionally" is
superseded. The rule is: *file wins only when it differs from the last render (a
proven edit).* The design doc should be amended to match the implementation, not the
other way round.

**Consequences.** The design doc is no longer the last word where the code is
demonstrably better — a precedent worth stating plainly, because the reflex is to
treat the design as canon. Whenever the two disagree, the disagreement is itself a
decision that lands here; it is not silently resolved in either direction.

---

## 0002 — Drop the `--no-syncback` belt; make the render_log base the structural invariant

**Date:** 2026-07-18 · **Status:** accepted · **Supersedes part of the 133-link fix
· **Source:** investigation Task 1 (Scenario C)

**Context.** The 133-link clobber was fixed with two independent guards: **(a)** the
full pipeline chain forces `--no-syncback` on its render stage (a "belt"), and
**(b)** the `render_log` 3-way base that only treats a file value as a human edit if
it changed since the last render (the "suspenders"). The investigation proved on a
synthetic DB + real `render_md.py` (Scenario C) that **(b) alone prevents the clobber
in both directions** — with the base in place, a stale file field is correctly read
as a stale default, not an edit, and the fresh DB value wins.

That makes (a) redundant *for its stated purpose* — and (a) has a cost the base does
not: it is the sole thing that overwrites **unabsorbed Obsidian edits** during a
full-chain run. Because STATUS documents the periodic workflow as "review in Obsidian,
edits flow back on the next render," while the command it names for that run is the
full chain (which renders `--no-syncback` and does **not** absorb edits), a real
human edit dies silently unless the operator happens to run `--render-only` first.
Nothing enforces that ordering. The belt traded "stale file clobbers fresh DB" for
"fresh DB clobbers unabsorbed human edit."

**Decision.** Drop the `--no-syncback` belt from the full chain. Keep guard (b) — the
`render_log` base — as the single, **structural** protection, and make it the
documented invariant. Sync-back is always on; the base makes it safe.

Rationale is the INTENT §5 principle: *prefer "can't" to "shouldn't."* The base
cannot be forgotten — it is in the code path. The belt required the operator to
remember which of two commands absorbs edits, which is exactly the class of
convention-based guarantee that produced the 133-link incident in the first place.

**Consequences.** Removes the silent-edit-loss path. The full chain now absorbs
Obsidian edits as the workflow always claimed it did. Defence-in-depth on
irreplaceable data is reduced from two guards to one — accepted, because the one that
remains is the structural one and the one dropped was the forgettable one. Requires:
remove the forced `--no-syncback` in `run_pipeline.py`'s render stage, confirm
`render_md.py`'s base logic is the sole guard, and correct STATUS's workflow. **Must
be implemented and tested before the next full run against the live vault** — until
then the belt stays, because the live behaviour is unchanged until the code changes.

---

## 0003 — `vocabulary` dropped as a linking signal; the temporal anchor is the root cause

**Date:** 2026-07-18 · **Status:** accepted (recording a decision already made) ·
**Source:** `pipeline/SCHEMA.md` lines 75-76; investigation Tasks 2-3

**Context.** `build_vocabulary.py` sits in the tree, unused; the DB carries zero
`signal='vocabulary'` evidence rows, cleared by an explicit
`DELETE FROM link_evidence WHERE signal='vocabulary'`. Nothing in the design doc or
the git history explained why — this is the near-loss that justifies this whole file.
The rationale was eventually found in a *schema comment*: the vocabulary signal "was
evaluated and dropped — it degraded linking."

The mechanism, reconstructed from `relink.py` and the dead-fingerprint finding:
vocabulary terms overlap across projects (shared boilerplate and terminology). The
signal meant to separate same-vocabulary projects worked on in *different eras* was
`time_window` — and `time_window` is itself dead, because the Gemini share-scrape
exposes no attachment hash, so there is no fingerprint anchor and no time window
(design §11.3.2 called hash-anchor windowing "the main defense against false
positives from repeated stock phrasing"). With no temporal signal to disambiguate,
vocabulary generated false links across eras and was rolled back to the
`filename_xref` / `path_mention` baseline.

**Decision.** Vocabulary stays dropped. `build_vocabulary.py` remains on disk, unused,
as a record of the attempt rather than live code. Reviving it is coupled to reviving a
temporal anchor — it is not independently safe to switch back on.

**Consequences.** Linking runs on three content/name signals (`filename_xref` 568,
`name_alias` 98, `path_mention` 80) with **no temporal disambiguation** — a known,
accepted weakness, not an oversight. Anyone reviving vocabulary must first solve the
missing-attachment-hash problem, or reproduce the same false links. **The deeper
evaluation data behind "it degraded linking" is gone** — likely in an unreachable
chat thread. This entry is the maximum recoverable record; treat it as final.

---

## 0004 — Layer C (semantic grouping) is kept, but declared unproven and dormant

**Date:** 2026-07-18 · **Status:** accepted · **Source:** investigation Tasks 2-3

**Context.** Layer C — embeddings-based semantic grouping — has produced **zero**
groups against the entire corpus. `sentence-transformers` was evidently never
installed in the run that built the frozen DB, so Layer C "skipped cleanly," and both
its tunables (`similarity_threshold = 0.6`, `semantic_window_days = 14`) currently
govern nothing. The embeddings dependency — the single thing that makes `chronicler/`
a heavy, non-stdlib subsystem — is at present doing no work at all.

**Decision.** Keep Layer C and the embeddings dependency. Do **not** cut it as scope.
But it is to be described honestly everywhere — in ARCHITECTURE especially — as
**unproven and dormant**, not as a working layer. The subsystem-split rationale in
ARCHITECTURE §3 must not lean on Layer C as a live capability while it has never run.

Committed follow-up: install `sentence-transformers`, run Layer C against the corpus,
and only then tune 0.6 / 14 against real output (including the sub-threshold
best-similarity scores §12.3 says it records). Until that run exists, the two Layer C
tunables are untunable — there is no data.

**Consequences.** The estate carries a heavy dependency that is currently inert but
intended to become load-bearing — an accepted debt, made visible rather than hidden.
The honesty cost is real: ARCHITECTURE can no longer imply three working grouping
layers; it has two that work (A: 761 groups, B: 261) and one that has never fired.

---

## 0005 — `Chronicler\` retired; data relocated to L5GN-Castle; repo is sole code home

**Date:** 2026-07-18 · **Status:** accepted · **Source:** investigation Task 0; Tim's
ruling

**Context.** The original `GitHub\Chronicler\` folder was an untracked, non-git
directory holding a second, silently-diverging copy of `pipeline/` *and* the only copy
of the live data (92 MB `chronicler.db`, ~326 MB of raw Claude/Gemini exports). The
repo's `chronicler/pipeline/` was found to be strictly ahead of the fork — nothing in
the fork's code needed salvaging. The dual-purpose folder (code + data, both untracked)
was the one clearly-wrong state.

**Decision.** `L5GN-Tools/chronicler/` is the sole authoritative code home. The legacy
`Chronicler\` folder is **deleted**. Its irreplaceable data (DB + `chat_threads/` raw
exports) was moved into a folder under **L5GN-Castle** (the operator's area for backups
and unassigned project resources). The untracked fork no longer exists.

**Consequences & open items.** Code/data separation is now explicit: the repo holds
code, L5GN-Castle holds the data. Two things this commits us to, neither yet verified:

1. **`CHRONICLER_HOME` must be repointed** at the new L5GN-Castle data path. Any prior
   `local.json` / env value is stale; the code cannot find its DB until this is fixed.
2. **The only copy of irreplaceable data now lives in a folder named "backups" — which
   is not the same as being backed up.** If the knight is not yet populated (README
   flagged knight ingest as "live test pending"), this may be the *only* copy in
   existence. This makes the off-box `VACUUM INTO` backup (previously "Task 7", low
   urgency) a near-term priority, not a rainy-day one. A single disk failure in the
   backup area would currently lose the entire payload.

## 0006 — Correction to 0005: knight is the live primary; the L5GN-Castle copy is a stale backup

**Date:** 2026-07-18 · **Status:** accepted · **Corrects:** 0005 consequences

**Context.** Entry 0005 was written from a cold-read assumption that the knight might
not be populated, which made the L5GN-Castle copy sound like it could be the only copy
in existence. That assumption was wrong, and the log drifted from reality within a
single session — recorded here rather than by editing 0005, because that is what an
append-only log is for.

**The real state.** The knight is operational and runs the live DB
(`/home/l5gn/vault/chronicler.db` is the primary). The gaming-rig copy at
`C:\Users\timps\Documents\GitHub\L5GN-Castle\data\Chronicler_Backup` is a genuine
off-box backup — this is correct architecture, not a risk. `CHRONICLER_HOME` does not
need repointing on the gaming rig: it is a *producer*, not the Chronicler runtime, so
0005's consequence-1 is moot.

**The residual, smaller concern.** That backup is **stale** — frozen at the
pre-knight-move state and not refreshed since. Everything ingested on the knight since
the move has **no off-box copy**. So the danger is not "only one copy" but "the second
copy has drifted and is refreshed only by hand."

**Consequences.** The automated off-box backup (`VACUUM INTO`, previously deferred)
stays a near-term priority, but reframed: the goal is a *fresh* recurring copy off the
knight, not a first copy. Until it exists, a knight disk failure loses everything since
the move. The one-line manual refresh of `Chronicler_Backup` is the stopgap.

---

## 0007 — The DB access surface: Datasette to read, a narrow web endpoint to write

**Date:** 2026-07-18 · **Status:** accepted · **Source:** design thread

**Context.** The pipeline built infrastructure but no way to *see into* the DB. The
original plan — rendered `.md` files as the working surface — was chosen because it
needed no tooling (any editor opens a markdown file). That benefit died silently when
the writer moved to a headless knight: the files now sit on a box with no GUI, and the
only bridge back is a sync-back path that had never been exercised. So the thesis is
currently unprovable not because links are thin but because there is no surface to
interrogate them through — you cannot run the INTENT §2 falsification test at all.

Reading and writing are different problems with different risk. Reading is the actual
product (browse the corpus, query the links) and is nearly free. Writing — applying
the ~19 real rulings (15 `link_ambiguous` + 4 `link_downgrade`) — is where care lives,
because any write surface is a *second writer* and single-writer is doctrine.

**Decision.** Split them, staged:

1. **Read: Datasette now.** Point it at `chronicler.db`, serve it read-only, bind to
   Tailscale. Zero code, cannot violate single-writer (it only reads), and it is the
   first time the corpus becomes queryable. Deliberately chosen *before* building
   anything, to test whether querying the corpus is even useful before investing.
2. **Write: a narrow web endpoint, later.** When the rulings itch enough, build it as
   a *stripped-down copy of the `l5gn-mesh-vertex-3_prod` spine* (FastAPI + uvicorn +
   SQLAlchemy over SQLite, static HTML mounted at `/ui`) — a proven in-estate pattern,
   not a new design. It surfaces **only** `review_queue` and writes **only** the
   human-ruling columns (`review_status` and the ruling fields). Bound to Tailscale;
   no Cloudflare, no public website (that layer was the finicky part of vertex-3 and
   is entirely separable — drop it, bind to the tailnet interface instead).

**Single-writer preserved structurally.** The endpoint physically writes only the
review columns; the pipeline owns every other column; they touch disjoint sets and so
*cannot* collide. Same "can't, not shouldn't" move as the wall — not a lock, not a
convention, a column boundary.

**Consequences.** Two things to carry when the write endpoint is built, both learned
by reading vertex-3: (a) take the DB path from `CHRONICLER_HOME`, never hardcode it as
vertex-3 does (`/home/l5gn/data/castle.db`) — hardcoding re-creates the fork-path
problem; (b) vertex-3's `CORSMiddleware(allow_origins=["*"], allow_credentials=True)`
is acceptable *only* because the bind is Tailscale-only — record that as the reason, so
nobody later flips it public without re-examining. Networking: the knight binds
`0.0.0.0` and is reachable as `100.x` over Tailscale (phone on cellular, personal
desktop) and as `192.168.x` over LAN (the work rig, which is not on the tailnet but
shares the home network — no cellular equivalent for it, accepted).

---

## 0008 — Rendered `.md` is read-only output; sync-back to be removed

**Date:** 2026-07-18 · **Status:** accepted · **Supersedes:** the editable-`.md` premise;
completes 0002

**Context.** 0002 dropped the `--no-syncback` belt but left sync-back itself in place,
guarded. This entry removes the reason sync-back exists at all. The chat DB is
predominantly machine-generated content ingested from existing exports — it is not a
human-authoring surface. The `.md` files are a *view* of it. Editing that view was
never actually used, and it is the sole source of the only data-loss incident in the
estate's history (the 133-link clobber).

**Decision.** Rendered `.md` files are **read-only output**, full stop. Human viewing
happens through the read surface (0007: Datasette now, report later); human *rulings*
happen through the narrow write endpoint (0007), which writes the DB directly, never a
file. The `.md`-as-edit-surface idea is retired.

Because nothing edits the `.md` files, there is nothing to sync back: the render
becomes purely **DB → file, one direction, forever**. Sync-back code is slated for
*removal*, not just guarding — the whole hazard class (0002, and the 133-link incident
behind it) is deleted rather than mitigated. This is the structural endpoint of 0002:
there is no belt because there is no second write path through files.

**Consequences.** Removes the sync-back hazard class entirely. `render_md.py` becomes
one-directional; `sync_back()` and the `render_log` 3-way base can be retired once the
write endpoint (0007) exists to receive the rulings they used to carry — *order
matters: the endpoint must exist before sync-back is removed, or the ~19 pending
rulings have nowhere to land.* Until then, the current guarded state stands. Anyone who
later wants human-editable markdown should build the separate notes system (0009), not
re-open this path.

---

## 0009 — Deferred: a self-hosted git-backed notes vault (separate toolset)

**Date:** 2026-07-18 · **Status:** accepted as a direction, deferred · **Not part of
Chronicler**

**Context.** Considered while closing the editable-`.md` question (0008). The appeal:
replace Obsidian's paid cross-machine Sync with a self-hosted equivalent — the knight
as always-on truth-holder, Tailscale as transport, a markdown vault synced to every
edge. General principle in play: most cloud sync is self-buildable; the exception is
raw scale, which a single user does not need.

**The boundary that makes this safe.** This vault is a **separate system with a
separate data model** and must **not** touch the chat DB. The chat DB is
machine-generated, single-writer, read-only at the edge; a notes vault is
human-authored and multi-writer. Conflating the two is exactly the mistake that
stranded the edit surface — keeping them apart is the whole point.

**The real design fork (recorded so future-me starts oriented).** The hard part is not
sync, it is conflict resolution:

- *Async multi-machine* (the actual need — edit on laptop, later open on phone, never
  truly simultaneous) is **the git problem, already solved by git.** A vault that is a
  git repo, knight as bare remote, a small auto-commit/pull/push loop per edge, is a
  weekend build. It is "scripting git," not reinventing much.
- *Concurrent multi-writer* (two live cursors in one paragraph, the Google Docs feel)
  needs Operational Transformation / CRDTs — years of specialist work (Yjs, Figma,
  Docs). **A single user does not have this problem.** Building it would be textbook
  over-engineering. The standard answer to concurrent edits is a *lock*; the better
  answer here is *no lock* — git merges after the fact, which is why locks become
  unnecessary. Google did not solve locking, they eliminated it and paid in OT.

**Decision.** Legitimate future toolset, deferred. When taken up, the fork is: **build
the git-vault** if versioned, diffable notes are wanted (history-of-thought as a
first-class feature — the estate's own thesis pointed at personal notes rather than
chat logs; the coherent, on-brand build); **adopt Syncthing** if the goal is merely
presence-everywhere with zero code and no version history (a local-first tool that
shares the estate's values, right when notes-sync should be plumbing you don't think
about). The unglamorous reliability edges (half-written files mid-sync, clock skew,
interrupted transfers) are the genuine reason to weigh adopting over building.

**Consequences.** No work now. Captured so the idea does not leak into the Chronicler
work with its incompatible multi-writer data model. Revisit as its own thread.

---

## 0010 — Project linkage is estate/account-agnostic; only the deposit wall stays hard

**Date:** 2026-07-18 · **Status:** accepted · **Source:** design thread ("porous walls")

**Context.** Building the project registry surfaced a real tension: the estate wall
(path separation, the deposit contract) says personal and work never mix, structurally.
But a *project* — a body of work — doesn't respect that boundary. L5GN OS (a work-account
initiative) plausibly seeded Crystal Spire (a personal-account creative project); MCF's
Solution Configurator threads appear on both the work and personal Gemini accounts.
Treating estate/account as a hard boundary for linkage would either force false splits
(one project artificially becomes two) or pressure toward weakening the wall itself.

**Decision.** The estate wall and the concept of "project" answer different questions
and were never meant to be the same axis. The wall guards **deposits** — physical
code/data at rest, protecting against misconfiguration (a producer writing into the
wrong namespace). It stays completely hard; nothing here weakens it. **Project linkage
is a different, orthogonal axis** — a `project_link` may span any combination of
estates and accounts. The `account` field is still recorded per-thread, unflattened,
exactly as ARCHITECTURE §7 already specified ("estate vs account are related but not
identical") — this decision extends that same principle to project boundaries.

This is safe, not merely convenient: INTENT §4 already establishes the system is
single-operator, not multi-tenant, not a product. There is no confidentiality boundary
to protect between Tim's own work-account and personal-account thinking — the wall was
always about preventing mistakes, never about hiding information from the operator.

**Consequences.** `relink.py` and any future write endpoint must not gate matching on
estate or account. `project_registry.json` entries may legitimately list multiple
`account_scope` values (see `crystal-spire`, `mcf-solution-configurator`). Reports that
aggregate by project should still surface the account dimension per-thread if asked,
never silently merge it away.

---

## 0011 — Existing `project_link` values are reset, not trusted

**Date:** 2026-07-18 · **Status:** accepted · **Source:** design thread

**Context.** Live-DB queries surfaced pre-existing `project_link` values (e.g.
`019f4273-...` spanning two `gemini-work` L5GN OS threads and the `claude-personal`
Crystal Spire thread; `smelt-gateway` tying two Crystal Spire-era threads). These
predate today's registry, today's estate/account-agnostic ruling (0010), and the
Chancellor/Chronicler-GAS/Auditor sub-project hierarchy. Tim's assessment: these are
almost certainly auto-accepts from very early pipeline testing, not deliberate rulings.

**Decision.** Treat all existing `project_link` values as untrustworthy noise. They
will be cleared and re-derived once `project_registry.json` is live and the narrow
write endpoint (DECISIONS 0007 stage 2) exists to apply real rulings — not assumed
correct, not cherry-picked as "probably fine." `smelt-gateway` looks structurally
plausible on inspection but is reset along with everything else rather than special-
cased, so the fresh pass starts from one consistent baseline.

**Consequences.** Until the reset + re-link pass runs, any `project_link` seen in the
live DB should be treated as historical noise, not signal. This is a Cowork task for a
future round — not performed in this session, since it's a write against the live vault
and this thread has no execution access to it. `relink.py`'s registry-gated stage
(DECISIONS-adjacent, ARCHITECTURE §7) should re-run in full against the new registry
once the reset lands.

---

## 0012 — The registry is three-tier: program → project → repo

**Date:** 2026-07-20 · **Status:** accepted · **Source:** design thread; ground-truth
audit (`L5GN_Project_Registry_Ground_Truth_-_20260720`); live census

**Context.** The linking spec (`docs/project_linking_skillset_spec.md`, S1) defines a
**flat** registry — `scope` (l5gn/mcf) → project — and explicitly parks anything
cross-cutting ("registry `scope` field is the hook for extending later; do not build
MCF-specific logic now"). But the ground-truth audit of the actual repos, Claude
projects, and folders showed that the largest efforts are not projects — they are
*programs* that contain many projects. "L5GN OS" is not one project; it is a program
name under which Citadel MicroIDE, the UCP work, the Mesh work, Chancellor, the
GAS-era Chronicler, and others all sit. Same for "WizForgeAnalytics" on the work side
— it is the BI *program* that the individual MCF projects (ActivityStatements,
ChurnLevelIndicator, PricingModelisation, DataAccessLayer) feed into and are run by.
Tim's framing: *program* has the useful double meaning — a computer program, and a
portfolio of projects run together.

The live census confirms this is real in the data, not just tidy in the head:
`smelt-gateway` 123 evidence threads, `L5GN_Armory_v4` 58, `v1 proto` 10 — three
distinct repos, each with a substantial independent body of conversation, all serving
the one CID/Citadel lineage. A single project with aliases would not show three
separate 10-to-120-thread clusters; sibling repos under one program is exactly what
that shape means. (Contrast: if one had 123 and the rest 2 each, they'd be aliases of
one project — the data would have said "flatten," and it didn't.)

**Decision.** Evolve the registry from the spec's two tiers to **three**:

- **Program** — the umbrella (L5GN OS, WizForgeAnalytics). A portfolio identity.
- **Project** — a coherent effort (Citadel MicroIDE, Crystal Spire, Solution
  Configurator, ActivityStatements, Chronicler-2026).
- **Repo / incarnation** — the physical folders that are versions of one project
  (`v1 proto` → `L5GN_Armory_v4` → `smelt-gateway` are three incarnations of Citadel
  MicroIDE, not three projects).

This resolves every hard case the flat model couldn't: the CID lineage is three repos
→ one project → one program, with nothing forced into an alias it isn't. It is a
deliberate evolution *beyond* the spec, not a gap-fill — past-Tim chose flat and used
`scope` as the only grouping; present-Tim, with the ground-truth audit in hand, is
overruling that with evidence. Recorded as a decision, not a silent schema drift.

**Consequences.** This is a real schema change touching three consumers:
`build_registry.py` (must emit the tier fields), `relink.py`'s scoring (a repo-level
match should roll up to its project/program for reporting, and the id-vs-canonical_name
divergence — round-2 flag — must resolve to one identifier scheme across tiers), and
the review endpoint (must offer rulings at the right tier and show the hierarchy for
context). It also finally answers the standing Armory question: Citadel MicroIDE is its
own project (58+ threads of evidence), a child of the L5GN OS program, not an alias of
anything. The spec's flat `scope` field is superseded by the program tier but not
deleted — `scope` (l5gn/mcf) remains a useful orthogonal axis (organisational origin),
distinct from program (portfolio grouping).

---

## 0013 — The read surface serves a snapshot, never the live DB

**Date:** 2026-07-20 · **Status:** accepted · **Source:** design thread; live incident
(false `database disk image is malformed`)

**Context.** `run.py serve` points Datasette at the live `chronicler.db` with
`--immutable`. During a session where the review endpoint and pipeline had been
writing, Datasette began returning `database disk image is malformed` on
`link_evidence` queries. Investigation (read-only) proved the file was **completely
healthy**: `PRAGMA integrity_check` = ok, `PRAGMA quick_check` = ok,
`SELECT COUNT(*)` = 651 rows. Restarting the Datasette process cleared the error
entirely.

Root cause: `--immutable` is a *promise to SQLite that the file will not change*. It
lets Datasette skip locking and cache the page map. When another process then writes
the file, that promise is broken and Datasette serves from a stale page map — which
surfaces as a false "malformed" error on a perfectly sound database. So the read
surface was reading the live, actively-written file under a flag that assumes it is
frozen.

**Decision.** The read surface must serve a **snapshot**, never the live vault.
`run.py serve` (and any read-only consumer) points Datasette at a fresh `VACUUM INTO`
snapshot — the same artifact `run.py backup` already produces — not at
`chronicler.db`. A snapshot is frozen by construction, so `--immutable` is honestly
true and the false-malformed class cannot recur; and a reader against a copy *cannot*
collide with the writer at all.

This is the structural half of single-writer applied to reads: the read surface is
made physically incapable of touching the live file, rather than trusting it to only
read. Same "can't, not shouldn't" move as the wall and the column-scoped write
endpoint (0007).

**Consequences.** `serve` gains a snapshot step (or reads the latest backup). Trade-off
accepted: the read surface is now *slightly stale* — it shows the vault as of the last
snapshot, not the last second. For a human browsing/ruling corpus this is invisible and
fine; if live-fresh reads are ever needed, that is a deliberate separate mode, not the
default. Pairs with 0014 (WAL) as the two halves of enforcing single-writer
structurally. Note this also means the review endpoint's writes won't appear in `serve`
until the next snapshot — acceptable, and worth a one-line note in the UI so it isn't
mistaken for a lost ruling.

---

## 0014 — Single-writer is enforced structurally (WAL + busy_timeout), not by convention

**Date:** 2026-07-20 · **Status:** accepted · **Source:** design thread; the 0013
incident

**Context.** ARCHITECTURE claims "one writer," but nothing enforces it at the process
level. The review endpoint (writer), pipeline ingest/relink (writer), Datasette
(reader), and ad-hoc `sqlite3` sessions can all open the live DB concurrently. The
0013 false-malformed error was a *harmless* symptom of this — but a worse-timed
collision between two actual writers is precisely how real SQLite corruption happens.
The doctrine has now been shown, twice in one week (this and sync-back, 0002), to be a
*convention* rather than a *structure* — and conventions fail at the worst moment.

**Decision.** Make concurrent access safe by construction:
- Put the DB in **WAL mode** (`PRAGMA journal_mode=WAL`) — lets one writer and many
  readers coexist without the reader seeing a torn write or a false-malformed state.
- Set a **`busy_timeout`** (e.g. 5000ms) on every connection — a blocked access waits
  and retries instead of erroring out.
- These are the standard, boring, correct answers. This is not a lock the operator has
  to remember; it is a property of how every connection opens the file.

**Consequences.** Removes the whole false-malformed / torn-read class and hardens
against the real corruption it was mimicking. Requires every code path that opens the
DB (`db.py`'s `get_connection`, the review endpoint, serve's snapshot step) to set
these pragmas consistently — a single shared connection helper is the right home, so
it cannot be forgotten on one path. WAL adds a `-wal` / `-shm` sidecar file next to the
DB; the backup step must snapshot correctly in WAL mode (`VACUUM INTO` handles this,
but a raw file copy would not — another reason snapshots go through `VACUUM INTO`, per
0013). Pairs with 0013: 0013 isolates the reader onto a copy, 0014 makes the live file
safe for the writers that remain.

---

## 0015 — Vocabulary (S2) is revivable with guards; supersedes 0003's "final"

**Date:** 2026-07-20 · **Status:** accepted · **Supersedes:** 0003's "treat as final" ·
**Source:** design thread; recovered spec (`project_linking_skillset_spec.md` §S2);
live investigation

**Context.** 0003 recorded vocabulary as dropped-and-final because it "degraded
linking," attributing the cause to cross-project term overlap with no temporal signal
to disambiguate eras. Two things recovered/measured this session revise that:

1. **The spec shows S2 was designed *with* guards that were never built.** Vocabulary
   was meant to ship with (a) a stopword list, (b) a cross-project commonality cutoff
   (drop terms appearing in many projects — the TF-IDF-shaped weighting), and (c) the
   S3 activity-window time filter as the era-discriminator. 0003's failure was almost
   certainly vocabulary run *without* these rails, not vocabulary being unworkable.
2. **The data now says the guards are viable.** Live queries this session:
   - Cross-project *alias* overlap is **zero** — no `name_alias` value is claimed by
     2+ projects (checked both raw and placement-stripped). Alias hygiene is clean;
     the false-link risk was never in aliases, only in auto-harvested vocab terms.
   - Dating coverage is **85.6%** (1,099 dated / 1,284 total; 185 undated). The
     activity-window guard can therefore fire for the large majority of threads —
     0003 assumed the temporal anchor was dead (true for share-scrape fingerprints,
     but `created_at` gives a usable date for most threads regardless).

**Decision.** Vocabulary is **revivable**, as a guarded rebuild per spec §S2 — not a
resurrection of the broken version. The GO is conditional on all three guards being
present: stopword list, cross-project commonality cutoff, and the activity-window time
filter (with a conservative higher-threshold fallback for the 14.4% undated threads).
0003 is not wrong about what happened; it was incomplete about *why*, and it declared
final a question that new evidence reopens. That is exactly what an append-only log is
for.

**Consequences.** `build_vocabulary.py` becomes a real rebuild target, not dead code.
Work required before it writes live evidence: implement the three guards, run it in
dry-run against the corpus, and spot-check that vocabulary-*safe* projects (unique
terms like Crystal Spire's `world_graph`) gain signal while vocabulary-*dangerous*
ones (projects sharing generic design vocabulary) are correctly suppressed by the
commonality cutoff. Sequencing: S2 depends on S3 activity windows being populated
(0004-adjacent) to get its era-discriminator — build/confirm activity first. If the
guards prove insufficient in dry-run, the fallback is "enable vocabulary only for the
projects it's demonstrably safe for," not all-or-nothing.

---

## 0016 — `chronicler_design_and_intent_v2.md` was never located; ARCHITECTURE.md is its replacement

**Date:** 2026-07-20 · **Status:** accepted · **Source:** design thread

**Context.** The linking spec (`docs/project_linking_skillset_spec.md`) opens with
"Read first for context: `chronicler_design_and_intent_v2.md` (the as-built Chronicler
reference)." That document could not be found on any machine, and Tim is unsure it ever
existed as a discrete file. It leaves a dangling authoritative reference in a spec now
committed to the repo.

**Decision.** Rather than leave a ghost citation, declare the resolution explicitly:
**`docs/ARCHITECTURE.md` is the authoritative as-built Chronicler reference** in that
doc's place. This is honest because ARCHITECTURE.md's content was reconstructed this
session *from the actual code and DB* (not from the missing doc) — it independently
covers what v2 would have: the schema, the wall, single-writer, the frozen-vault
contract, the sync-back history. The spec's reference should be read as pointing at
ARCHITECTURE.md.

**Consequences.** No lost information — the reference target exists, just under a
different name and derived independently. If the original v2 doc ever surfaces, it
should be diffed against ARCHITECTURE.md and any genuinely-new rationale folded in
(then archived, per the pattern for superseded design docs), but its absence blocks
nothing. The spec and `cowork_tasks_cleanup_and_qol.md` are now both in `docs/` — note
that the cleanup doc predates several DECISIONS entries and must be triaged against
this log before any of its tasks run (in particular, any sync-back QoL item is moot
per 0008, which removes sync-back entirely).

---

## 0017 — The `projects` table is reset and rebuilt, not migrated; 0011's debt is paid

**Date:** drafted 2026-07-21, ratified 2026-07-27 · **Status:** accepted ·
**Executes:** 0011 · **Source:** `COWORK_BRIEF_projects_reconciliation.md`;
drafted in full in `docs/COWORK_REPORT_projects_reconciliation.md` §"Drafted
DECISIONS 0017"; live census 2026-07-21T10:50Z

**Context.** 0011 ruled that existing `project_link` values were noise from early
auto-accept testing and should be reset rather than trusted. The runbook was
written; no knight access existed to run it, so every relink and ruling since
layered onto a table the repo had already decided not to trust. Measured on
2026-07-21: 25 `projects` rows in three generations — 9 Claude uuids, 7 current
registry ids, 9 legacy — carrying 226 links across five duplicate identity
clusters, with zero orphans. The FK held throughout; the problem was duplication,
not breakage.

Two findings made "reset" mean more than clearing two columns. `config/project_registry.json`
had never been shipped to the knight after round 3, so the three-tier registry
(0012) had never existed there. And `relink.score_thread` keys candidates by the
raw `link_evidence.project` string, with `upsert_project` inserting whatever that
string says — 332 of 657 evidence rows were keyed to folder names rather than
ids, so a reset that left the evidence alone would be undone by the next relink
run.

**Decision.** Reset and rebuild; do not migrate. A careful merge of 226 links
across five identity clusters would produce a result nobody could audit, and the
manual tagging at risk was 13 rulings — of which 10 pointed at an id (`l5gn-os`)
that had since changed meaning and 2 looked mis-ruled on their own titles. The
links are re-earned through relink and through rulings, under one identity scheme.

**How it was actually executed (2026-07-27).** Not by the reset-and-re-key runbook
this entry was drafted around. The knight took the **fresh build** path
(`RUNBOOK_knight_fresh_build.md`) instead: the vault was rebuilt from the two
irreplaceable inputs, so `link_evidence` and `project_link` started empty
(verified: both `COUNT(*) = 0` before the apply) and there were no legacy rows to
clear and no folder-name-keyed evidence to re-key. The 332-row re-key and the
270-thread clear described above therefore never ran — the debt was paid by
rebuild rather than by migration, which is the same decision reached by the
cheaper route. The first id-keyed evidence pass wrote clean; the golden apply
(`docs/archive/COWORK_REPORT_apply_alignment.md`) landed 343 threads against it.

**Consequences.** The pre-reset links are gone, 13 of them human rulings — that is
the bad part, accepted deliberately. What survived: every thread and message, the
Claude uuid rows (Claude's own entities, holding no links), and every alias
authored by hand. `l5gn-os` keeps its program meaning.

Two follow-ups this entry commits us to, **both still open as of 2026-07-27**:

1. `relink.load_registry`'s flat-registry guard must test registry **content**,
   not key presence — it currently refuses only on a missing `programs` key,
   which the generator always emits.
2. The candidate-scoring path must **refuse a `link_evidence.project` key that is
   not a link target**. `evidence_votes` still groups by whatever string the
   column holds, with no check that it resolves in the registry.

Without both, a third generation of identity rows can grow back the same way the
second did. The `seed_suppress` defect found during the golden apply
(`b7c2390` — a curated alias removal silently regenerated, false-linking six
threads) is the same family of fault: a generator writing an identity nobody
ratified.

---

## 0018 — Persona / LLM inference is a separate, pluggable service, never inside the toolkit wall

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread (command deck review) · **Builds on:** 0007; INTENT §4/§5

**Context.** The v2 command-deck mockup adds Personas (configured agents that query the
vault and chat) and assisted Query. Vertex-3's `api/inference.py` implements exactly
this, but pulls in SQLAlchemy (`shared_schema.SessionLocal`) and an Ollama runtime.
`chronicler/review/app.py` deliberately shed both — *"No SQLAlchemy… raw sqlite3 keeps
the write path auditable at a glance"*, and FastAPI/uvicorn are an optional extra, never
in the stdlib-only core. The knight is not resource-rich, so a heavy local model is not a
given.

**Decision.** Persona/LLM inference lives in a **separate service** (the vertex-3 spine,
retrofitted), not in L5GN-Tools. The toolkit and the deck's read/write backend stay
stdlib-walled; the deck **links or proxies** the inference service. The inference
**backend is pluggable**: embeddings (`sentence-transformers`, the vendored
`all-MiniLM-L6-v2`) on the knight for retrieval; generation is a swappable backend that
may run off-box (gaming rig or a hosted API) when a query needs it. Exact model is a
config/benchmark choice on the actual knight, not an architectural commitment. The honest
default is **knight = embeddings + retrieval; generation is a swappable backend.**

**Consequences.** No heavyweight ORM or model runtime crosses the toolkit's dependency
wall. The deck degrades cleanly: if the inference service is down, reads and rulings still
work. A further DECISIONS entry is required before any persona output is allowed to
*write* — personas suggest, they never rule (see 0019).

---

## 0019 — Any LLM- or query-exposed DB path is structurally read-only

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread · **Builds on:** 0013, 0014; INTENT §5 ("guarantees are structural, not behavioural")

**Context.** The deck's Query and Personas screens are declared read-only, with a
scope-box in the UI (`review_queue` marked no-write). But an LLM that emits SQL is
write-*capable* unless the connection cannot write, and the estate's own doctrine is that
a guarantee which survives only because something *remembers* it is a defect. A scope-box
is UI copy, not a boundary.

**Decision.** Every DB handle exposed to assisted-query or a persona is opened
**structurally read-only** — a read-only connection (`mode=ro` / `PRAGMA query_only`),
surfaced through `dbsafe` so it is the single enforced place, not per-caller. A persona
physically cannot write through its handle. The scope-box remains as *disclosure*, but the
boundary is the connection, not the copy.

**Consequences.** Personas can only ever produce suggestions a human ratifies on the
Linking screen — 0007's write path stays the *only* writer to the vault. `dbsafe` gains a
read-only-connection helper alongside its existing WAL/busy_timeout one. A hermetic tester
asserts a write attempted through the query handle fails.

---

## 0020 — The Command Deck is a program-tier entity, scanned from the personal rig only

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread · **Builds on:** 0012

**Context.** The deck spans the vertex-derived inference service, the deck backend/UI, and
its consumption of L5GN-Tools — Tim's largest cross-threading effort to date, big enough to
warrant a program designation rather than sitting as a loose project. Separately, the
governance direction requires the toolkit to see its own most write-and-execute-heavy code,
which today it does not (the toolkit's own repo is outside any scanned root).

**Decision.** Register the Command Deck as a **program** in `config/project_registry.json`
(three-tier, per 0012), with the deck backend/UI and the inference service as
projects/repos under it. It is **scanned from the personal (gaming) rig only** — added as a
config root there — not from the knight or the work rig. It participates in normal scans,
`blast_radius` and `UNCOMMITTED-CRITICAL` like any other program.

**Consequences.** The estate's most write-and-execute-heavy new surface is finally inside
the scanner's sight. The program's name and its member repos are a registry ratification
item, folded into the reconciliation worksheet rather than decided here.

---

## 0021 — The deck reads the serve snapshot; one supervisor runs the read/review/deck trio

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread · **Builds on:** 0013

**Context.** The deck's vault-backed views (Linking queue, Query, Personas) read
`chronicler.db`. 0013 already ruled the read surface serves a *snapshot*, never the live
DB, after the false-`malformed` torn-read incident; a persona querying the live DB
mid-ingest is that same class of fault. Separately, the knight now runs up to three
long-lived processes — snapshot serve, the review write-endpoint, and the deck backend —
which is new operational territory.

**Decision.** All deck vault reads go through the **`serve` snapshot**, not the live DB —
making `serve` a deck dependency, which is acceptable because the deck links to it anyway. A
**single supervisor** brings the trio up: the knight already uses systemd units
(`deploy/chronicler-ingest.service`/`.path`), so the recommended shape is a systemd
**target** pulling in serve + review + deck as units (`systemctl start l5gn-deck.target`),
with a `run.py`-level launcher as the foreground/dev equivalent.

**Consequences.** No deck view can catch a half-written vault. One command brings the
surface up or down; unit boundaries keep each process independently restartable and logged.
The snapshot refresh cadence becomes a deck concern to state explicitly — how stale the
deck's view may be is now a design parameter, not an accident.

---

## 0022 — Knight-side command execution writes an append-only run ledger

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread · **Builds on:** the `toolkit_git_info` / `auditor_uat_stamp` provenance pattern

**Context.** The deck's knight-side buttons (`consume`, `ingest`) run subprocesses and
stream stdout but persist nothing — no record that a run happened, its target, result, or
trigger. This is the run/execution ledger the r141 finding argued for, and the same instinct
as stamping acceptance claims: an action asserting *"this ran"* should carry provenance.
Without it, the deck mutates the vault with less traceability than archiving a doc now has.

**Decision.** Every command fired through `POST /api/commands/*` writes an **append-only
run-ledger row** — timestamp, command, target, exit status, and the fact it was
deck-triggered. The ledger is the provenance artifact for *actions*, mirroring what
`toolkit_git_info` does for scans and the uat stamp does for acceptance claims.

**Consequences.** A fired `consume` is traceable after the fact. The ledger is a new small
store, separate from the vault; its exact location and whether it is surfaced back into the
deck are implementation details for the brief. It also gives the deck an honest activity feed
for free.

---

## 0023 — Work-estate visibility is auth-gated; only personal-estate reads stay open

**Date:** 2026-07-25 · **Status:** accepted · **Source:** design thread · **Builds on:** 0010; INTENT §4

**Context.** The plan gates only "writes or executes" and leaves reads open, with the
tailnet as the boundary. But the mesh-wide view co-renders personal and work on the knight,
and work carries MCF / PII-adjacent material. 0010 kept the deposit wall hard on disk; the
deck is the first surface to show both estates together, to any tailnet device, with no code.

**Decision.** **Work-estate data is behind the same TOTP gate as the write tier — even to
view.** Personal-estate reads stay ungated (the tailnet is enough for Tim's own material).
The wall thus becomes not only a disk boundary (0010) but a *visibility* boundary on the
display surface: seeing work requires the code; seeing personal does not.

**Consequences.** A phone on the tailnet browses personal freely but must authenticate to
reveal the work column; the mesh-wide view renders the work side as gated-until-unlocked.
This is the first place the wall governs *reading*, not just writing or merging — stated
here so a later "just show everything" convenience change has to argue against this entry.

---

## 0024 — Project-link rejections are an endpoint-owned, append-only `review_rulings` table

**Date:** 2026-07-27 · **Status:** accepted · **Source:** COWORK_BRIEF_command_deck_proto.md Task 3 · **Builds on:** 0007; 0022's ledger shape

**Context.** `review_queue` is pipeline-owned: relink is its only writer, and
the review endpoint's audited invariant (0007, `tester_review`) is that a
human ruling touches only `threads.project_link` / `threads.project_confidence`
plus an idempotent `projects` identity row — never `review_queue`. An accept
is expressible as a link (`project_confidence='manual'`), which is why that
column boundary has held. A rejection has nowhere equivalent to go: it is a
fact about a *proposal*, and proposals are `review_queue` rows, which the
endpoint has never been allowed to write.

**Decision.** Add a new table, written only by the review endpoint,
append-only: `review_rulings (thread_id TEXT, candidate_project TEXT,
verdict TEXT, ruled_at TEXT)`. "Not this project" inserts a row with
`verdict='rejected'`; the grouped read surface (`pending_rulings`,
`queue_by_project`) joins against it and excludes any `(thread_id,
candidate_project)` pair with a rejected verdict from that project's batch —
the same exclusion mechanism as the existing `project_confidence='manual'`
rule, one join further out. `review_queue` itself is never written by the
endpoint; the single-writer guarantee 0007 established is preserved exactly,
not widened.

**Consequences.** One more table and one more join on every grouped read.
A rejection becomes inspectable after the fact (who rejected what, when),
the same provenance instinct as 0022's ledger and the UAT stamp — and this
table can very plausibly *become* (or feed) that ledger later rather than
being a one-off. The alternative — `review_queue.status='rejected'`,
written directly by the endpoint — is fewer moving parts but reopens a
boundary that has held since 0007 for the sake of one UI round; if that
trade is ever preferred it should be a deliberate re-litigation of this
entry, not an incidental choice made while building the deck.

---

## 0025 — Estate visibility is scoped by *surface*, not by estate; a solo box may read its own estate on loopback

**Date:** 2026-07-27 · **Status:** accepted · **Amends:** 0023 (does not supersede
it) · **Builds on:** 0010; the solo playbook · **Source:** design thread, preparing
the work-laptop walk

**Context.** 0023 ruled work-estate data behind the TOTP gate **even to view**.
Its stated context is specific: *"the mesh-wide view co-renders personal and work
on the knight, and work carries MCF / PII-adjacent material … the deck is the
first surface to show both estates together, to any tailnet device, with no
code."* The rule protects against a **co-rendered, network-reachable** surface.

The Command Deck prototype implemented it as written — a deny-by-default
`account LIKE '%-personal'` allowlist in both read paths, with no flag to flip.
Correct for the knight. But it makes the deck structurally incapable of showing
work data anywhere, including on a **solo work laptop, holding only its own work
estate, bound to loopback, read by the operator sitting in front of it**. That
machine has no personal estate to co-render, no tailnet exposure, and no reader
other than the person whose material it already is. Gating it protects nobody and
blocks the one dataset with the cleanest project definitions in the estate.

**Decision.** Visibility is gated by the **surface**, not by the estate label:

1. A surface that **co-renders more than one estate** requires the TOTP gate to
   reveal the work side. 0023 stands, unchanged, for the knight.
2. A surface **reachable beyond the machine it runs on** requires the gate to
   show work data at all.
3. A surface rendering **only the local machine's own estate**, bound to
   **loopback only**, is the operator reading their own files, and is not gated.

The deck therefore shows the estate declared for the machine it is running on —
`personal` on the personal rig, `work` on the work laptop — and never both,
unless the gate exists and has been satisfied. The wall of 0010 is untouched:
this governs *display*, never deposits, never merging.

**Consequences.** The wall's enforcement moves from a hardcoded
`'%-personal'` string to the machine's declared estate, which means it is now
config-derived rather than constant — a real weakening of "there is no knob
here", accepted deliberately and bounded by the loopback condition, which is
**not** config-derived and must be enforced structurally: a work-estate surface
that is asked to bind beyond loopback must refuse to start, not warn.

Two things follow that this entry commits us to:

- The default bind (`0.0.0.0`, right for the knight's tailnet) must not apply on
  a work-estate machine.
- A work box should carry a **registry scoped to its own estate** — an MCF-only
  `project_registry.json` rather than the full curated file. Nothing about the
  personal estate needs to exist on that machine, and the smallest correct
  registry is also the smallest disclosure. This is a shipping practice, not a
  code change, but it belongs with this ruling.

The TOTP gate (0023) remains unbuilt and remains required for every case in (1)
and (2). This entry narrows *where* it is required; it does not remove it.

---

## 0026 — Knowledge documents are a first-class governance artefact with their own shape, not malformed ADRs

**Date:** 2026-07-28 · **Status:** accepted · **Source:** the 2026-07-28 work-rig
walk and the archiving sweep that followed · **Relates to:**
`archive/COWORK_BRIEF_governance_scanners.md` (2.B1/2.B2), INTENT §defensibility

**Context.** `todo_adr_scanner.decisions_count` counts entries matching
`^##\s+(\d+)` — the trinity's `## 0001 — title` form. Measured on real data from
both estates on 2026-07-28, it returns **zero everywhere**:

- **Work estate** (`10280L`, 9 MCF projects): 0 decision entries, 0 ADR files, and
  0 TODO/FIXME markers. Yet `doc_census` sees
  `ValidationAutomation/docs/DECISIONS.md` — title "Decisions Log", 4 headings,
  1,145 words — plus 21 documents in SolConfig and 23 in TSsToAssets, including
  `SolConfig_Knowledge.md` (15 headings, 3,562 words) and
  `LEGACY_BUNDLE_KNOWLEDGE.md` ("Knowledge & Lessons Log").
- **Personal estate** (8 scanned projects): 0 decision entries as well. CID carries
  9 ADR files; this repo's own `docs/DECISIONS.md` counts correctly when pointed
  at directly (16 entries at the time), but sits outside the scanned root.

So a counter that has **never once returned non-zero on a real scan** reports both
estates as keeping no decision records, while both demonstrably do. The counter is
not defective — it is measuring one convention, and the estate uses two.

The second convention is the substantive point. The MCF work has been about
getting knowledge out of Tim's head and into a durable form, and — his framing —
*a piece of known business information represents a decision that was made*. That
is true, and it is the reason those documents matter. But a knowledge document is
**not** an ADR wearing the wrong hat: it has no status, it does not supersede a
predecessor, it is not append-only, and it is revised in place as understanding
improves. Forcing it into ADR shape would destroy exactly the properties that make
an ADR worth counting.

**Decision.** Knowledge documents are recognised as a **distinct, first-class
governance artefact**, counted separately from decision records. Specifically:

1. **Do not reformat knowledge documents to satisfy the ADR counter.** Rewriting
   `SolConfig_Knowledge.md` into numbered entries would be the tail wagging the
   dog — the scanner exists to observe the estate, not to specify it.
2. **Do not broaden `_DECISION_ENTRY`** to swallow other heading shapes. An ADR
   count that also counts knowledge docs can distinguish neither, and the signal
   an ADR carries (a ruling, with a status, that supersedes) is destroyed by
   dilution. The regex stays narrow.
3. **`doc_census` gains a knowledge census** beside `adr_files`, keyed on a
   **cheap, explicit convention** rather than inference from prose. A classifier
   guessing "is this knowledge?" from content is the large check that rots; a
   filename or single-marker convention is the small one that always runs — the
   same reasoning `auditor_doc_claims` was built on.
4. **A zero `decisions_count` is not evidence of absent governance**, and must not
   be read or reported as such. Anywhere the report presents it, it presents the
   knowledge census alongside.

**Consequences.** The two estates become comparable without the work estate
looking ungoverned, which it plainly is not. Defensibility (INTENT) gains the
artefact it actually needs: the work estate's evidence of considered practice is
its knowledge base, not an ADR count it will never have.

A knowledge document is any .md whose filename contains _KNOWLEDGE_,
case-insensitively, anywhere in the name — in practice it is a suffix
(SolConfig_Knowledge.md, LEGACY_BUNDLE_KNOWLEDGE.md), but the match is not
anchored, so a differently-shaped name still counts. doc_census reports the
total .md count, the classified count and the classified percentage — the
raw counts always beside the ratio, because a percentage over a denominator
containing generated output is not a governance signal. Measured 2026-07-28:
work 36/77 classified (6 knowledge docs across 4 of 9 projects), personal
45/824 — where 646 of those 824 are generated output in two projects.

Not decided here: the `L5GN-Castle` payload anomaly (a capped 1.1 MB `file_census`
still present on the 2026-07-28 build). Suspected backup and duplicated folders
rather than a scanner fault; to be investigated as it is met, and it is the same
open ruling as item 1.A2 — how a non-git folder's data directories get classified
out when there is no `.gitignore` to do it.