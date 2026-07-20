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