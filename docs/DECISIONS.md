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

---

## 0027 — Summary-only governs artefacts that travel; a local surface reads the source at render time

**Date:** 2026-07-28 · **Status:** accepted · **Builds on:** 0010 (the wall),
0013 (serve a snapshot), 0025 (gate the surface, not the data) ·
**Source:** design thread

**Context.** Scanners capture summaries and never contents — sizes, counts,
titles, 120-character marker excerpts — and `blast_radius` explicitly stores no
script body, alias or credential. The reason is that **the report is a deposit
artefact**: it is pushed to the knight, consumed by other estates, and lands
beside material it must never carry. That is why 1.A2 treats even leaked *paths*
as a defect. The rule protects the artefact, not the operator.

A local-only surface is not an artefact. It renders on the machine that owns
the files, to the person who already owns them, and nothing it displays leaves
the process. The constraint that makes summary-only necessary simply is not
present.

**Decision.** The summary-only rule is **unchanged for anything that is
captured, written to `data/`, or deposited.** Separately, a **local-only
surface may read a file from disk at render time** and display its contents,
provided:
1. it persists nothing — no cache, no copy under `data/`, nothing that could be
   deposited;
2. it is bound to loopback, enforced structurally as 0025 already requires; and
3. it reads only within the configured estate roots and vault home — never an
   arbitrary path supplied by the caller.

**Consequences.** `blast_radius`' guardrail stays literally true: nothing is
stored, so nothing can leak through a deposit. The deck gains full fidelity
without a single scanner capturing more than it does today. The risk moves from
*what the artefact contains* to *what the surface can reach*, which is why (3)
is a hard requirement and not a nicety: a render-time reader with a path
parameter is a file-disclosure bug waiting for the day someone binds it wrong.

---

## 0028 — A local surface may stage a working-tree change; it may never commit

**Date:** 2026-07-28 · **Status:** accepted · **Builds on:** 0007, 0024
(write surfaces are narrow and column-scoped), 0025 (loopback), 0027
(render-time reads) · **Source:** design thread

**Context.** Every write surface so far touches the vault and nothing else. The
docs board's one genuine action — archiving a completed pair — is a change to
the **source tree**: `git mv` and a prepended stamp. The `docs-archivist` skill
already performs exactly this, by hand, under a hard rule: *never move a file
until Tim has ratified that specific move*, and leave everything **staged,
uncommitted**.

**Decision.** A local-only surface (loopback, own estate, per 0025/0027) may
**stage** a working-tree change, subject to all of:
1. the change is confined to `docs/` and is a `git mv` into `docs/archive/`
   plus a stamp prepended above the title — **never a body edit**;
2. it is performed only on a per-pair ratification given in that session, never
   in bulk and never inferred from a green gate;
3. **it never runs `git commit`.** The human reviews `git diff --staged` and
   commits in a terminal. The gate runs on that commit, as it does today.

**Consequences.** The mechanical layer is automated; the judgement layer is not.
The pre-commit gate remains the last word, because a commit is still a human
act. A surface that can stage but not commit cannot produce an unreviewed
change — the worst case is a working tree the operator must clean up, not a
laundered history.

---

## 0029 — A deposit found to carry more than its contract is replaced, never edited

**Date:** 2026-08-02 · **Status:** accepted · Builds on: 0010 (the wall), 1.A2 (leaked paths are a defect), 0013 (snapshots are frozen by construction) · Source: the 2026-08-02 scanner-scope finding

**Context.** Two scanners bypassed the data-directory guard, so every deposit taken since carries thousands of paths from inside raw export trees. The artefacts are self-describing and sha256-manifested (the deposit contract), so a deposit cannot be edited in place without invalidating the manifest that makes it trustworthy — and editing it would also destroy the record of what was actually produced on that date.

**Decision.** A deposit discovered to violate its own contract is replaced by a fresh deposit from a fixed producer, and the superseded bundle is removed — never edited, never partially scrubbed. The consumer's per-estate history/ is treated the same way: a superseded snapshot is dropped whole.

**Consequences.** The estate loses the affected history window rather than keeping a doctored version of it, which is the same trade docs/README.md §3 makes for archived documents — testimony is either kept intact or removed, not corrected. The alternative, an in-place scrub, produces a manifest-valid bundle whose contents nobody can date, which is worse than a gap.

---

## 0030 — Shape is generated; rationale is authored. ARCHITECTURE.md keeps the half that can't be derived

**Date:** 2026-08-02 · **Status:** accepted · **Amends:** 0016 (does not
supersede it) · **Builds on:** `docs/README.md` §1's governing rule ·
**Source:** the 2026-08-02 architecture drift audit

**Context.** `ARCHITECTURE.md` holds two kinds of content. **Rationale** — why
the `l5gntools/` ↔ `chronicler/` boundary is capability and not custody, why
the `--no-syncback` belt was traded for the `render_log` base — cannot be
derived from anything and is the reason the document exists. **Shape** — which
modules exist, which routes require what, which tables a module writes, what
the gate is composed of — is derivable from the tree, and is the half that
drifted. All twelve findings of the 2026-08-02 audit are shape claims in a
rationale document.

`docs/README.md` §1 already rules on this: *a document earns its place by
holding something that can't be derived.* Status is derived, so it does not
live in `docs/`. Shape is derived by the same argument and nobody had noticed.

**Decision.** The two halves are separated:
1. **Shape is generated** by a scanner, from the tree, and rendered to a
   committed, machine-owned document. It is never hand-edited.
2. **`ARCHITECTURE.md` keeps the rationale** and cites the generated document
   for shape. It stops asserting module lists, route tables, write targets and
   gate composition — the claims it cannot keep current.
3. **0016's resolution stands.** ARCHITECTURE remains the replacement for the
   never-located `chronicler_design_and_intent_v2.md`; what it is *authoritative
   for* narrows to rationale, with shape delegated to a document that cannot
   disagree with the code because it is produced from it.

**Consequences.** The A1/A4/A8 failure class becomes structurally impossible
rather than a thing to remember. The cost is a generated file in the repo and a
gate check that refuses a stale one — the lockfile pattern, with the lockfile's
familiar friction: adding a route means regenerating. That friction is the
feature. A document that *can* silently disagree with the code eventually does.

---

## 0031 — A non-gating check surface reports findings and never issues a verdict

**Date:** 2026-08-03 · **Status:** accepted · **Builds on:** 0022 (provenance
for actions), `docs/README.md` §3 (the gate polices where an acceptance claim
came from, never whether it was earned) · **Source:** the UAT-sidebar round

**Context.** `verify.py` answers *"does the code work"* and gates commits. A
human walking a sheet answers *"does it do what was asked"* and closes a pair.
Between them sits a class of check that is fully deterministic yet needs a
rendered surface and minutes rather than seconds — too slow and too stateful
for the pre-commit hook, too mechanical to be a human's judgement. Today those
checks live on walk-sheets, where they inflate the human's queue with work no
human needs to do.

**Decision.** A **witness** is a deterministic check surface that runs outside
the commit gate and:
1. asserts **rendered or observed state** against an expected state;
2. emits **findings**, never a verdict — it cannot mark a UAT item passed, and
   nothing it produces closes a pair;
3. **never gates a commit.** The Windows pre-commit hook remains the only gate.

A witness failure means *"the surface did not render what the code claims"* —
not *"the code is broken"* (`verify.py`'s job) and not *"this isn't what I
wanted"* (the walk-sheet's job).

**Consequences.** Two authorities can never disagree about green, because only
one of them is allowed to say it. The estate gains a place to put deterministic
UI checks that is not the human's queue. The cost is a fourth artefact class to
keep honest, which is why (2) is stated as a prohibition rather than a
convention.

---

## 0032 — The Knowledge Curator reads local transcripts, is MCF-scoped, and treats recency as truth order

**Date:** 2026-08-07 · **Status:** accepted · **Builds on:** 0025 (a solo box
reads its own estate), 0026 (knowledge documents), 0030 (derived output is not
a document) · **Source:** `docs/SPEC_Knowledge_Curator.md` review,
`docs/COWORK_BRIEF_knowledge_curator.md`

**Context.** The Curator was specced against `chronicler.db`. Retargeting it at
the local Cowork transcript store removes its vault dependency, its linking-
coverage ceiling, and its cross-estate exposure in one move — but introduces a
question the estate has not ruled on: when two conversations disagree, which is
true?

**Decision.**
1. The Curator reads the **local transcript store on the machine that owns it**,
   is **scoped to the work/MCF estate**, and never reads personal-estate
   content. It is a solo-machine tool (0025) and produces no travelling artefact.
2. **Recency is the truth order.** Conversations are processed newest-first by
   real modified time; the newest claim on a topic is current, an older
   conflicting claim is **superseded and reported as such**, never discarded and
   never treated as a gap.
3. Its output is **derived**, written under `data/`, and does not earn a place
   in `docs/` (0030, `docs/README.md` §1).

**Consequences.** The tool gains an honest answer to "why does the current
knowledge say this" — the superseded trail — which the vault route could not
have produced. The cost is that recency is a heuristic: a newer casual remark
can supersede an older considered one. Accepted, because both are quoted and
dated in the report, so a wrong ordering is visible rather than silent.

---

## 0033 — Staging is confined by a code-declared path allowlist, not by directory; 0028's `docs/`-only clause is widened once, by name

**Date:** 2026-08-08 · **Status:** accepted · **Amends:** 0028 (does not
supersede it) · **Builds on:** 0025, 0027, 0032 · **Source:** design thread

**Context.** 0028 permits a local surface to stage a working-tree change and
forbids it to commit. Its clause (1) confines the change to `docs/`, to a
`git mv` into `docs/archive/`, and to a prepended stamp — never a body edit.
That confinement was written around the one action then in view: the docs
board archiving a completed pair.

The Curator's K0 ratification is a different shape of the same act. It writes
`config/mcf_conversation_map.tsv` — a curated join surface, one row per
conversation, each row ratified individually by the operator reading the
evidence for that row. It is in `config/`, it is not a move, and the body is
the change.

But the property 0028 was actually protecting is not the directory, and is not
the `git mv`. It is clause (3): **the human reads `git diff --staged` and
performs the commit**, so the gate runs on a human act and no unreviewed
change can enter history. That property is untouched here.

**Decision.** 0028's clause (1) is replaced by:

1. The change is confined to a **path allowlist declared in code**, not in
   config, each entry carrying a declared shape. Two entries at this ruling:
   - `docs/**` → `git mv` into `docs/archive/` plus a prepended stamp, never a
     body edit (0028's original clause, unchanged in substance);
   - `config/mcf_conversation_map.tsv` → **append a row**, never edit or
     remove an existing one.

Clauses (2) and (3) stand **unchanged and unweakened**: per-item ratification
given in that session, never in bulk, never inferred from a green gate; and
**never `git commit`**.

Additionally, and specific to the map: **every staged row records how it was
arrived at** — machine-matched by which pass, or human-picked from a refused
collision, or hand-mapped with no machine candidate. A row resting on the
operator's memory rather than on a match must say so, permanently, in the
file. This is the registry's `alias_sources` pattern (S1), for the same
reason: a curated identity whose provenance is lost becomes indistinguishable
from a derived one, and 0011 and 0017 spent two rounds cleaning up the
consequences of that.

**Consequences.** There is now an allowlist where there was a directory
constant — a knob where 0028 had none. Accepted deliberately, and bounded two
ways: it is **declared in code**, so widening it is a commit that the gate
sees and a reviewer reads, not a config edit; and the never-commit rule is
what actually makes staging safe, and it is not being touched. The worst case
remains a working tree the operator must clean up.

---

## 0034 — The stdlib-only contract is a package boundary, not a repo boundary; the app tier is a declared dependency

**Date:** 2026-08-08 · **Status:** accepted · **Amends:** the stdlib-only
contract as recorded in ARCHITECTURE §3 and §6 · **Builds on:** 0007, 0025 ·
**Source:** design thread

**Context.** The read-only/stdlib contract exists to protect the *scanners*:
they run against folders they must never write to, on machines whose Python
environment is not guaranteed, and `auditor_stdlib` + `auditor_readonly` police
that. That reasoning is entirely about `l5gntools/scanners/` and the package
that carries them.

It was then generalised into a property of the repository, and the review app
was built as an *optional extra* to preserve it. That was right while the app
was a bolt-on for applying ~19 rulings. It stops being right when the app is the
way the system is used at all: `available()` returning False then describes a
broken install, not a legitimate configuration, and reporting it as a graceful
skip makes a defect look like a choice.

**Decision.** The contract is scoped to what it was always protecting:

1. **`l5gntools/` — including every scanner — remains stdlib-only and
   read-only, unchanged and unweakened.** `auditor_stdlib` and
   `auditor_readonly` keep their present scope. Nothing in this entry permits
   a scanner to grow a dependency.
2. **The application tier (`chronicler/review/`, the launcher) declares its
   dependencies as required, not optional.** FastAPI and uvicorn move out of
   `[project.optional-dependencies].review` and into the app's declared tier.
3. **The dependency direction is one-way and auditable: the app imports
   `l5gntools`; `l5gntools` never imports the app.** This is the property that
   makes (1) survivable, so it is enforced by an auditor, not remembered.
4. `available()` and `run.py review`'s loud skip are retired *for the app path*.
   A missing web stack is an install error with a stated remedy, not a skip.

**Consequences.** The repo can no longer claim "runs on a bare Python" without
qualification, and ARCHITECTURE §3's boundary paragraph becomes wrong the moment
this lands — rewriting it is part of the round, not a follow-up. The scanners
remain independently installable and independently testable, which is the
property that actually mattered; `verify.py` must keep proving it with no web
stack present, or (1) is decorative.
 
---

## 0035 — `run.py app` is the single entry point; the physical data-root move is deferred to its own round

**Date:** 2026-08-08 · **Status:** accepted · **Source:**
COWORK_BRIEF_unified_app.md Task 4 · **Builds on:** 0007, 0013, 0025, 0034

**Context.** Task 4 asked for two things bundled as one: (1) `run.py app`
replacing `serve` + `review` as one process on one port, and (2) moving
`data/`, `chronicler.db` and `config/local.json` out of the install tree,
because a packaged application must not write into the folder it was
installed from. The brief itself names the stop condition for the second
half: *"The data-root move puts the vault at any risk. Stop. The vault is
the one irreplaceable thing here; a working app with the DB where it is
today is a complete success and Task 4 can be its own round."*

That condition is live, not hypothetical, in the environment this round
was actually built in: the repository is reached through a mounted
filesystem with observed, reproducible anomalies unrelated to any code in
this estate -- files that cannot be `rm`'d or `mv`'d across the mount
boundary immediately after creation (worked around throughout this round
by renaming within the same directory), and `VACUUM INTO` failing with a
raw `disk I/O error` when its destination is on that mount rather than a
normal local disk (confirmed in Task 3's Datasette verification: the exact
same snapshot call succeeded immediately once retargeted at `/tmp`). A
data-root migration is, by definition, a write to the one irreplaceable
artefact in the estate (INTENT §5) performed through a filesystem layer
already shown to fail silently-in-the-small on ordinary operations. That
is precisely the condition the stop clause describes, not a reason to
route around it with extra retries.

**Decision.**

1. **`run.py app` is ratified as the canonical entry point**, replacing
   the conceptual two-process shape of `serve` + `review`. It is not new
   code so much as a rename-with-consequences: the same preflight,
   the same routes, now also carrying Datasette as a sub-app (0013/0034
   Task 3) in the one process. `run.py serve` and `run.py review` remain
   fully functional, unchanged in behaviour, for one round -- each now
   prints a one-line notice naming `app` as where it went, per the
   brief's own instruction, not silently deprecated.
2. **The physical data-root relocation is deferred**, invoking the
   brief's own stop condition rather than forcing it through in an
   environment that cannot currently be trusted with the operation. The
   config-driven resolution this estate already has (`l5gntools.config`,
   `viewer.resolve_db_path`'s env → machine → default chain) is the
   correct foundation for that move when it happens; nothing about this
   round weakens or forecloses it. Deferring is a scheduling decision,
   not a technical one -- the mechanism is understood, the environment
   to execute it safely was not available here.
3. **The `role` vocabulary (`producer`/`consumer`, read by `l5gntools/
   census.py` and asserted in `tests/tester_census.py` /
   `tests/tester_config.py`) is NOT changed by this entry**, despite the
   brief's framing that a standalone, unified app "collapses" the role to
   one value. `census.py`'s producer/consumer domain reporting remains
   meaningful independent of whether the mesh (DECISIONS-adjacent, Task 6
   of this same brief) is enabled on a given box, and changing a
   contract with its own test fixtures is exactly the kind of drive-by
   widening this estate's own governance treats as a defect. A
   `standalone` role, if wanted, is Task 6's or a future round's to add
   deliberately -- recorded here so it is not lost, not decided here so
   it is not rushed.

**Consequences.** `run.py app` is the answer to "how do I start the deck"
from this commit forward; documentation and playbooks written after this
point should say `app`, not `serve`/`review`. The data root -- `data/`,
`chronicler.db`, `config/local.json` -- stays inside the install tree
until a round runs in an environment proven safe for the migration (a
normal local disk, not this session's mount). Task 4's stop condition is
exercised, not merely quoted: **"a working app with the DB where it is
today is a complete success."** Whoever picks up the data-root move next
should start by confirming `VACUUM INTO` and ordinary `rm`/`mv` behave
normally on the target machine before touching the live vault -- that
check is now a known prerequisite, not an assumption.

---

## 0036 — The cross-machine mesh stands down; mothballed behind a config flag, not deleted

**Status:** accepted · **Date:** *(absent — see below)* · **Source:**
`COWORK_BRIEF_unified_app.md` Task 6

> **Metadata stamped 2026-08-28, not written at the time.** This entry landed
> carrying neither a `Status` nor a `Date` line — the only one of fifty-seven,
> found by parsing the log during the 2026-08-28 restart rather than by reading
> it, because every other entry matched the format and this one silently did not.
> The status is stamped in place under §4, which unfreezes the status line and
> nothing else. **`Date` is left absent rather than inferred:** 0035 and 0037 both
> read 2026-08-08, which makes that the obvious guess and a guess is what it would
> be. Git holds the landing date and is the authority for it (`CONVENTION_decisions.md`
> §2.1). So this entry stays non-conformant on a required field, deliberately, and
> is a charter member of the list 0056's Consequences admit does not exist.

**Context.** COWORK_BRIEF_unified_app.md Task 6. The mesh (producers scanning
and pushing `estate.json` snapshots; the knight consuming them, ingesting chat
exports, and running the interpret sweep) was the estate's original shape and
ARCHITECTURE §2/§4 still describe it as *the* shape, not *a* shape. It has not
failed — 0035 explicitly declined to touch it — but a single-machine
application (Tasks 1-5 of this same brief) and a two-role mesh answer
different questions, and documentation that asserts both as simultaneously
current is documentation nobody can trust cold. Something had to give: keep
the mesh live and let the app-tier docs describe a shape most installs no
longer run, or say plainly that the mesh is optional now and mean it.

**Decision.**

1. **`deposit`, `consume`, `intake`'s drop zone, and `deploy/`'s auto-ingest
   trigger are gated behind a `mesh` machine-config flag**
   (`l5gntools/config.py:mesh_enabled()`, reading `"mesh": true` from
   `config/machines.json` or `config/local.json` with the same host
   precedence as every other machine setting). Off by default. Each gated
   `run.py` command keeps existing, keeps its help text, and refuses with
   `"<command>: mesh mode is not enabled -- set \"mesh\": true ..."` and exit
   code 1 rather than a traceback or a silent no-op. `run.py ingest` degrades
   rather than refuses: its intake sub-step is skipped with a printed notice
   (equivalent to `--skip-intake`) and the rest of the pipeline still runs,
   since ingest's backup and pipeline stages are not mesh-specific.
2. **`mesh` is a `pyproject.toml` extra with an empty dependency list**, not a
   config-only flag with no `pip install -e .[mesh]` story. This matches the
   brief's own framing and the shape of every other optional surface in this
   file (`chronicler`, `scrape`, `viewer`, `review`, `desktop`) even though
   deposit/consume/intake are stdlib-only and there is genuinely nothing to
   install — the extra documents the boundary; the config flag enforces it.
3. **No code is deleted.** `l5gntools/deposit.py`, `l5gntools/consume.py`,
   the vendored `intake.py`, and everything in `deploy/` are unchanged and
   fully functional the moment `"mesh": true` is set. Mothballed, not
   removed — this is a documentation and default-posture change, not a
   capability change.
4. **`KNIGHT_PLAYBOOK.md` and `PRODUCER_PLAYBOOK.md` archive** via
   `docs/README.md` §3 route 2 (superseded), stamped, naming this entry.
   Both describe a configuration that still works and is not currently in
   use — the stamp says exactly that, not that they were wrong.
5. **`ARCHITECTURE.md` §2 and §4 are rewritten** to describe the
   single-machine application as the default shape, with the mesh recorded
   as an opt-in mode rather than *the* topology. The root `README.md`'s
   loop diagram (producer → knight ASCII flow) is removed with it — a
   diagram of the default path that stopped being the default path is
   actively misleading, not merely outdated.

**Consequences.** A fresh clone with no `config/local.json` `"mesh"` entry
now runs as a standalone application out of the box — `run.py app` / `run.py
window` — with no drop-zone or push/consume step required or expected.
Re-enabling the mesh on a box that wants the two-role split again is one
config key, not a code change or a revert; the archived playbooks are the
correct read for how to do it, their ARCHIVED stamps notwithstanding.
`SOLO_PLAYBOOK.md` is untouched by this entry — it was never listed in
`docs/README.md`'s core-doc table and describes a third case (both roles,
one box) that this entry does not rule on either way; it may need its own
pass later, but that is a separate, undecided question, same as 0035's
treatment of the `role` vocabulary. `deploy/`'s systemd units still install
and still trigger on a delivered zip; what changed is that the `run.py
ingest` they call now no-ops its intake step by default, so the watcher
needs the same config flag as everything else in this entry to do anything
beyond the backup + pipeline stages.

---

## 0037 — Execution parameters are generated from a ratified plan, never supplied by a caller; and a budgeted run's unit of work is a project, or a newest-first prefix of one

**Date:** 2026-08-08 · **Status:** accepted · **Builds on:** 0032 (recency is
the truth order), 0033 (propose, ratify, execute), the curator tab's execution
allowlist · **Source:** design thread, after real K2 runs on the work rig 

**Context.** The curator tab's execute route accepts a stage key and nothing
else: no argv, no path, no flag. That rule made the surface's execution remit
auditable at a glance. A conductor cannot hold to it literally — pacing a run
means invoking K2 scoped to one project, with a cool-down, repeatedly.

Separately: 0032 makes recency the truth order. Conversations are processed
newest-first, and an older conflicting claim is *superseded* rather than a gap.
That property is established **by the order of processing**. A budget planner
free to pick any subset of work — "the twenty quickest conversations across the
estate" — would silently destroy it, and the destruction would be invisible in
the output, because a wrongly-ordered supersession looks exactly like a
correctly-ordered one.

**Decision.**

1. **A caller supplies a plan identifier, never a parameter.** Execution
   parameters are derived server-side from a **ratified plan**, which is itself
   generated server-side from a bounded set of policy inputs (budget, policy
   name, thermal profile). `STAGE_TABLE` remains the single place a runnable
   stage is declared, and gains a **declared parameter schema** per stage —
   which parameters that stage accepts, and their permitted ranges. A
   parameter outside its declared range is a refusal, not a clamp.
2. **A plan is proposed, shown, and approved before it runs**, in the same
   posture as 0033's per-row ratification. An unapproved plan does not execute.
3. **The unit of work in any plan is a whole project, or a newest-first prefix
   of one.** Never an arbitrary subset, never a cross-project interleaving,
   never "the cheapest N conversations". Within a project, newest-first is
   absolute and the planner may not reorder it.
4. **A plan states its own estimate's provenance**, and where there is no
   measurement it says so and offers no estimate. A budget plan built on a
   guessed throughput is a fabricated window.

**Consequences.** (1) is a real weakening: parameters now reach a subprocess
that previously took none. It is bounded by being schema-declared in code
rather than config, by the caller never naming a parameter, and by (2) putting
a human between the plan and the process. (3) costs granularity — an hour that
cannot fit a whole project fits a prefix of it, and sometimes fits nothing,
which the planner must say plainly rather than filling the time with work that
corrupts the ordering. That cost is accepted: a shorter honest run beats a
fuller one whose supersessions cannot be trusted.
 
---

## 0038 — Conversation, session and thread are three distinct things with three distinct names

**Date:** 2026-08-11 · **Status:** accepted · **Builds on:** 0032 (the Curator's
conversation unit), `SPEC_Chronicler.md` S1 · **Source:** design thread

**Context.** The estate has used "thread" for three different entities, and the
ambiguity is no longer only in prose — it is encoded in a ratified artefact.

`config/mcf_conversation_map.tsv`'s key column is named **`session_id`** and
holds the `local_<uuid>` **conversation** id. `ingest_local_transcripts.py` says
*"Cowork sessions never get a direct link"*, where "session" means the inner
`<uuid>.jsonl`. `chronicler.db` calls its rows `threads`. And the design
discussion that produced the Curator was conducted in "threads" while meaning
"conversations" throughout — which is what made the Curator's curated map look
like a competitor to Chronicler's linking rather than a solution to a problem
Chronicler had declared unsolvable.

A naming collision that survives into a committed schema is not a style
question. It caused a design point to be missed for two rounds.

**Decision.** Three terms, fixed:

1. **Conversation** — the outer unit a human recognises as one continuous
   exchange. Cowork: the `local_<uuid>` folder. Claude: one `conversations.json`
   entry, keyed on its `uuid`. Gemini work: the 32-char hex id from field 2 of
   the share export. Gemini personal: **no native conversation identity exists**
   — see 0040.
2. **Session** — one transcript file within a conversation: a `<uuid>.jsonl`,
   including `subagents/agent-*.jsonl` and resumes. **One conversation, N
   sessions.**
3. **Thread** — a row in `chronicler.db`'s `threads` table. A *storage* entity,
   not a source entity. It usually corresponds to one conversation; for Gemini
   personal it is synthesised, which is exactly why the distinction matters.

4. The map's key column is **renamed `conversation_id`**. This is a schema change
   to a ratified artefact, performed once and explicitly, with the former name
   recorded here so the change is traceable rather than mysterious. K1, K2 and K4
   read it and change together.

5. Code and prose use these three words as defined. Where an existing document
   says "thread" and means "conversation", it is **wrong** — but existing
   documents are not retro-edited (`docs/README.md` §2); the error is corrected
   where the words are next used, not by rewriting the record.

**Consequences.** `ARCHITECTURE.md` gains the glossary, because this is exactly
the kind of boundary definition it exists to hold. The rename is a small
migration with a real risk attached: a half-applied rename would leave K1 reading
a column K0 no longer writes, so it lands as one change with its testers, or not
at all.

---

## 0039 — The Curator is scoped to the estate declared for the machine it runs on, not to MCF

**Date:** 2026-08-11 · **Status:** accepted · **Amends:** 0032 clause (1) (does
not supersede the entry) · **Builds on:** 0025 (a surface rendering only the
local machine's own estate is not gated), 0026, 0030 · **Source:** design thread

**Context.** 0032 scoped the Curator to the work/MCF estate on two grounds. The
first was a value argument, quoted in its brief: personal-estate knowledge is
*"regurgitation/reuse of existing principles"*, where MCF knowledge is
domain-specific and unrecoverable. The second was a safety argument: the tool
never reads personal content, so **there is no mixed artefact to police.**

The safety argument is sound and is preserved below. The value argument has an
exception 0032 did not see: **this toolkit.** Thirty-seven decisions, a dozen
investigations and the reasoning behind them are precisely the non-derivable
material 0026 made a first-class artefact — and `docs/README.md` currently gives
investigations no route to graduate anywhere at all. They are evidence that never
becomes knowledge, which is a gap in the doc classes, not a property of
investigations.

Scoping by **estate label** was also the wrong instrument, and 0025 already
established the right one for the deck: gate by the **surface**, not by the data's
label.

**Decision.**

1. The Curator is scoped to the **estate declared for the machine it runs on**,
   never to a fixed estate name, and **never to more than one estate in a single
   run or a single output.**
2. A machine whose declared estate is **`both` (the knight) does not run the
   Curator.** It is a solo-machine tool, and this makes the exclusion explicit
   where 0032 achieved it only by accident.
3. Outputs remain **per estate and are never merged.** No artefact under
   `data/knowledge_curator/` spans two estates.
4. 0032's clauses (2) recency-as-truth-order and (3) derived-output-lives-under-
   `data/` are **unchanged**.
5. The Curator still **never writes a `KNOWLEDGE*.md` file.** A toolkit knowledge
   document is authored by hand; the Curator only proposes. That rule is what
   keeps the write path closed regardless of which estate is in scope.

**Consequences.** The safety property survives intact — a single run reads one
estate and produces one estate's output, so there is still no mixed artefact.
What is given up is the simplicity of "it only ever touches MCF", which was easy
to verify by reading one constant and is now a per-machine config read. That is
the same weakening 0025 accepted, for the same reason, and it is bounded by (2).

One thing this entry does **not** settle and which must be confirmed before the
first personal-estate run: whether `data/knowledge_curator/` sits inside the
deposit contract. If a Curator report can travel, per-estate outputs are not
sufficient on their own and a deposit exclusion is required.

### Why the scoping is by machine and not by topic — two worked examples

The curated conversation lists contain two cases that look like estate mixing and
are not. Both are recorded because a future reader will otherwise take them for
errors and "fix" them.

- **`Solution Configurator (MCF)` appears in the Gemini *personal* list.** Two
  conversations, conducted on a personal phone, as open exploration of the
  subject — not work on the MCF deliverable. The material is personal-estate: it
  is on a personal account, in personal time, and nothing about it belongs to the
  employer. It merely *discusses* a work topic.
- **`L5GN-Tools` appears in the *work-rig* Cowork list.** The toolkit is built
  partly on the work rig, deliberately — it is a toolkit for that work, and spare
  compute goes into it when it is available. The original Chronicler build
  happened this way before being assimilated here. That material is work-estate
  by provenance while being about a personal project.

**The principle both cases establish: estate is a fact about provenance and
disclosure, never about subject matter.** Whose account, whose machine, whose
time — not what the conversation is about. Topic does not partition cleanly and
never will; provenance does.

This is the argument *for* scoping by the machine's declared estate rather than
by any label attached to content. A topic-based scoping would have misfiled both
examples, in opposite directions.

The residual risk is content, not classification: an "open exploration" of an MCF
topic could still contain MCF-specific detail, and the Curator quotes verbatim.
Nothing deposits, so the wall is untouched — but the first personal-estate run
should spot-check the claims extracted from those conversations, because that is
where domain knowledge would surface into a personal artefact if it were going to.

### Clause (3) constrains the artefact, not the author

"Outputs are never merged" reads as a block on the toolkit's own knowledge base,
since `L5GN-Tools` conversations exist on **both** estates and would therefore be
proposed by two separate runs on two machines.

It is not a block, because of clause (5): **the Curator never writes a
`KNOWLEDGE*.md` file.** Two runs produce two proposal sets; the human authors one
document from both. The tool never produces a mixed artefact — a person reads two
sets of proposals and writes a single document, which is a different act
entirely, and the act every knowledge document in this estate is already the
product of.

---

## 0040 — Where a source carries a stable conversation id, a curated map is the join of record

**Date:** 2026-08-11 · **Status:** accepted · **Builds on:** 0011 and 0017 (what
derived identities cost us), 0033 (stage, ratify, never commit), 0038 (the three
names) · **Relates to:** `SPEC_Chronicler.md` S1–S6 · **Source:** design thread

**Context.** K0/K1 produced an **exact** conversation→project join for the Cowork
store by curating, once and under review, the one identifier the source natively
carries. `ingest_local_transcripts.py` had declared that join impossible —
*"Cowork sessions never get a direct link"* — because `cwd` encodes the session's
own path rather than the project. The impossibility was real for *derivation* and
false for *curation*.

The same property holds elsewhere, and was not noticed because of 0038's naming
collision:

- **Claude export** — `conv["uuid"]` is stable and is already the `thread_id`.
  Current linking is exact-title-match, else a `prompt_template` substring, else
  nothing.
- **Gemini work** — `parse_gemini_export.py` recovers a stable 32-char hex id
  from field 2, across all 110 files. A closed account and a finite backfill.
- **Gemini personal** — **no conversation identity of any kind.** Takeout's My
  Activity is a flat stream of turn-pairs; each record's `title` is the *user
  prompt*, not a conversation title. Verified against the July export: no
  per-record chat id, and every Gemini URL in it is the same generic
  `gemini.google.com/gems/view`.

**Decision.**

1. Where a source carries a **stable native conversation id**, a **curated map
   keyed on that id is the join of record.** Fuzzy or derived linking is not used
   for that source. Where a source offers **more than one id space**, the map
   keys on the **resolved, canonical** id and never on a transient one: Gemini
   now issues `share.gemini.google/<token>` short links which resolve to
   `gemini.google.com/share/<hex>`, and only the latter is the id the skeletons
   and the manifest are keyed on. A key that can be reissued is not a key.
2. Maps are **per source**, one file each, carrying the same per-row provenance
   discipline 0033 requires: how each row was arrived at, machine-matched or
   human-mapped, never overwritten by a re-run.
3. **Chronicler consumes them at `project_confidence: 'manual'`**, which S1's
   standing override rule already protects from every automated pass.
4. **A curated map is never committed.** It joins the same class as
   `config/project_registry.json` and `config/local.json` — authored here,
   shipped manually, gitignored. `/config/*conversation_map.tsv` covers the
   pattern so the next source's map inherits the rule rather than having to
   remember it. Existing history on the remote is accepted as spilt; the rule
   governs from here.

   **This costs 0033's review mechanism, and the cost is named rather than
   absorbed.** That ruling's safety property is *"the human reads
   `git diff --staged` and commits"*. An untracked file produces no diff. The
   replacement is twofold: the curator tab's staged-rows view becomes the
   **primary** review rather than a convenience, and a **`<map>.sha256`
   fingerprint is committed beside the map** — so the repo still records that a
   map was ratified, when, and against what content, while carrying no title. An
   audit trail that proves a ratification happened is not the same as one that
   shows what was ratified, and that reduction is accepted deliberately.

5. **Gemini personal keeps the scrape**, and its role is restated: the scrape's
   product is **conversation boundaries**, not links. The two sources are
   **jointly necessary, not merely complementary**, and the measured reason is
   specific — the skeletons carry `created_date: None` and
   `published_date: None`, so they hold no time at all, while Takeout holds real
   UTC timestamps and no boundaries. `reconcile_gemini.py` exists to marry the
   two. Retiring the scrape would not save a fuzzy match; it would cost the
   ability to say where one conversation ends, and with it 0032's newest-first
   ordering for that source.

6. **A public share link is a transient means, revoked once captured.** The
   scrape requires a conversation to be publicly shared. That is a **real
   disclosure**, and Gemini's move to `share.gemini.google` short links is a
   reasonable reading of shared chats having surfaced in web search. So sharing
   is a step in the capture, not a state the estate leaves behind: **once a
   skeleton is captured, the share link is revoked.** This is what makes clause
   (5) affordable — the scrape's privacy cost becomes momentary rather than
   standing, which was the original objection to keeping it.

7. **Gaps are named, with their reason, and sized where they can be.** Two
   stand:
   - **Work standard chats** — out of scope. The usage predates the estate's
     shape and was mostly learning how to direct the work rather than doing it,
     so the recoverable knowledge is low. Measured, not missed.
   - **Gemini personal strays** — the curated sheet **is** the enumeration, so
     the gap is not unbounded. Three skeletons exist that the sheet does not
     list, recovered from the stale backup and predating the scrape run's URL
     list. Three known items, not an open horizon.

   A named gap is acceptable. A silent one is the confident-zero failure, and an
   unsized one that could have been counted is the same failure wearing a hedge.

**Consequences.** A stated impossibility is retired, and the estate gains one
pattern in place of four bespoke linking strategies. The exposure of the existing
map narrows to columns that identify nothing.

The cost is real: four curated maps to keep, and every future source needs one
before it can be joined. That is deliberately the same trade 0011 and 0017 were
paid for — two rounds spent cleaning up identities a generator had invented — and
curation is the price of never paying it a third time.

It also leaves the evidence system carrying almost nothing. See 0041.

---

## 0041 — S2 vocabulary and S6 evidence scoring are declared dormant, not deleted

**Date:** 2026-08-11 · **Status:** accepted · **Follows the pattern of:** 0004
(Layer C kept, declared unproven and dormant) · **Builds on:** 0003, 0015, 0040 ·
**Source:** design thread

**Context.** 0003 dropped vocabulary as a linking signal and named the temporal
anchor as the root cause. 0015 revived it "with guards", superseding 0003's
"final". With 0040, three of four sources join **exactly** through a curated map,
and the fourth — Gemini personal — joins through ratified boundaries once
scraped. The population the evidence system exists to score is close to empty.

Machinery that runs over nothing does not fail loudly. It succeeds over an empty
set and reports zero, which is indistinguishable from working.

**Decision.** Following 0004 exactly: S2's vocabulary fingerprints and S6's
evidence scoring are **dormant as a linking signal** — kept in the tree, declared
unproven for the current corpus, not deleted, and not run in the default chain.

They are **not** declared useless, and the distinction is the point of this
entry. Two conditions warrant taking them back up, and the second is now the
likelier:

1. **A source appears that cannot be joined exactly.** The original condition.
2. **A labelled set exists to evaluate them against.** 0040's curated maps are
   the first ground truth this estate has ever had for linking. S2 was dropped
   (0003) and revived-with-guards (0015) **without ever being evaluable** — both
   rulings were made on argument rather than measurement, which is why they
   contradict each other. A curated map turns "does vocabulary predict the right
   project" from a debate into a score against known-correct answers, and lets
   the weighting be **reverse-engineered from the answers** rather than guessed
   at in advance.

**A candidate application already exists, in a different tool.** `match_claims`'
K4 shortlist ranks corpus chunks by `difflib.SequenceMatcher` containment —
contiguous character runs, with **no term weighting of any kind**. The module
already records what that costs: a code-detail claim ranked an 8,000-character
section that plausibly held the answer at 0.003 while a 51-character stub heading
took the top slot, *"a likely major contributor to a full run coming back with
zero captured outcomes"* (2026-08-08, work rig). Weighting by distinctiveness is
exactly what a containment score cannot express, and exactly what S2 computes.

So the machinery may be **relocated rather than revived** — the same computation,
serving the Knowledge Curator's shortlist instead of thread linking, where its
output can be measured against the confirm step's own verdicts on every run.

**Consequences.** 0015's "revivable with guards" stands; this restates *when*
revival is warranted rather than withdrawing permission, and adds the condition
that actually makes revival answerable.

The risk is that dormant code rots. Mitigation: **its testers stay registered**,
so the gate keeps exercising it even while the chain does not, and a revival —
or a relocation — starts from something proven rather than something merely
present.

---

## 0042 — A consumer repo declares its own runnable stages; the toolkit executes them under a committed repo allowlist and never widens what they can do

**Date:** 2026-08-13 · **Status:** accepted · **Builds on:** 0037 (execution
parameters come from a ratified plan, never a caller), 0033 (a staging allowlist
declared in code), 0025 (a loopback, single-estate surface is not gated) ·
**Precedent next door:** `sf-data-service` **0029** (object read-scope is a
committed, fail-closed allowlist; widening is a reviewed one-line edit) and
**0032** (the estate view delegates freshness rather than re-deriving it) ·
**Source:** `COWORK_BRIEF_project_wizard.md` review

**Context.** 0037 clause (1) says `curator_control.STAGE_TABLE` "remains the
single place a runnable stage is declared". That held while everything runnable
lived in this repo, and every containment surface built so far — `docs_board`'s
`REPO_ROOT` anchor, `estate_data.resolve_contained` — treats *"stay inside this
repo"* as structural rather than configurable.

The Project Wizard asks the toolkit to run stages declared in **other repos'**
committed manifests. That is a second declaration site, and one `verify.py` never
sees: the auditors walk this repo. It is the first surface asked to reach outside
this checkout on purpose, and the widening is real enough to need ruling on
rather than assuming.

**Decision.**

1. **A consumer repo declares its own runnable stages**, in a committed manifest
   at its own root. The toolkit never authors that file and never imports the
   repo's code. Declaration belongs to the repo that owns the work — the same
   reasoning that puts `.request.json` inside `sf-data-service` rather than in a
   central registry.
2. **The toolkit looks only where a committed allowlist says.** A repo absent
   from it is never read, listed, or executed, **even if a manifest physically
   exists there.** Widening is a reviewed, committed edit — `sfds-0029`'s
   discipline, applied one gate further out.
3. **The execution allowlist is derived from validated manifests at board-build
   time**, and the execute route accepts a `(repo_key, stage_key)` pair and
   nothing else. 0037 clause (1)'s property survives intact one repo out: **the
   caller names the work, never the parameters of it.**
4. **A manifest's `command` is a fixed, literal argv list with no parameter
   slot.** 0037 permitted schema-declared parameters because the conductor needed
   pacing; this surface does not need them, so it **does not take the
   weakening**. A parameter slot may be added later, by its own entry, with its
   own reason.
5. **Containment runs through the existing `resolve_contained` against a new
   anchor set** — never a second implementation. A `cwd` or output path escaping
   its own declared repo root is refused exactly as a symlink escaping `docs/` is
   refused today.
6. **The toolkit never widens what a consumer repo can do.** A read-only tool
   stays read-only when a button in this app invokes it rather than a terminal.
7. **Where a consumer repo answers a question about itself, ask it.** Freshness
   above all: delegate to the repo's own engine and show its answer, never
   compute a second, competing number. `sfds-0032`'s precedent, adopted.

**Consequences.** Two are uncomfortable and are stated rather than absorbed.

**The declaration of what is executable now lives outside the gate.**
`verify.py`'s auditors walk this repo; a manifest in another repo is reviewed by
whoever reviews that repo. Today that is one person on a solo work rig, which is
an adequate answer *and an explicitly time-limited one*. It stops being adequate
the moment a pilot repo gains a second contributor, and it is recorded here so
that change is noticed rather than quietly inherited.

**The repo allowlist is config, not code.** 0033 chose code deliberately, so that
widening was "a commit that the gate sees and a reviewer reads, not a config
edit". This allowlist must be per-host — MCF repos sit at different absolute
paths on different machines, which is exactly what `machines.json` exists to
handle — so a code constant is not available without hardcoding paths. It is
committed and reviewed like `machines.json`, but **no auditor covers it**. A step
down from 0033's posture, taken knowingly.

Clauses (3) and (4) are the mitigation for both: a manifest nobody reviewed still
cannot receive a parameter, and still cannot name a path outside its own repo.

---

## 0043 — A ruling from another repo is cited with its repo, at every mention

**Date:** 2026-08-13 · **Status:** accepted · **Relates to:** `docs/README.md`
§1 (the trinity), `sf-data-service` 0023 (that project's docs follow the same MCF
convention) · **Source:** `COWORK_BRIEF_project_wizard.md` review

**Context.** That brief's "Depends on" line listed `0023, 0025, 0029, 0031, 0036,
0037` — of which **0029 and 0032 are `sf-data-service`'s entries, not this
repo's**. Here, 0029 is *"a deposit found to carry more than its contract is
replaced, never edited"* and 0032 is the Knowledge Curator's scoping. Both stop
conditions later in the same brief cite them bare.

A reader resolving those against this log gets a confidently wrong answer, and it
is nobody's mistake: several repos now follow the same docs convention and each
keeps its own `00NN` sequence, so collisions are guaranteed rather than unlucky.
The shared convention is a strength; ambiguous citation is the cost it has not
yet paid for.

**Decision.** A reference to another repo's ruling **carries that repo's name at
every mention**, not only in a depends-on list — `sf-data-service 0029`, or a
short consistent prefix such as `sfds-0029`. **A bare `00NN` always means this
repo's log.** Applies to briefs, reports, runbooks, DECISIONS entries and code
comments alike.

**Consequences.** Cheap, and it removes a whole class of confident-wrong reading
before the estate grows a third and fourth repo keeping the same convention. It
also makes the shared convention visible where today it is only implied.

---

## 0044 — The Curator runs on the personal estate; `data/knowledge_curator/` is outside the deposit contract

**Date:** 2026-08-17 · **Status:** accepted · **Settles:** the question 0039
left explicitly open · **Builds on:** 0039 (scoped by machine, never by a fixed
estate name), 0040 (curated maps are per source; the resolved id is the key),
0027 (summary-only governs artefacts that travel), 0029 (a deposit carrying more
than its contract is replaced, never edited) · **Source:** Grand Walk, 2026-08-17

**Context.** 0039 already ruled the substance: the Curator is scoped to *the
estate declared for the machine it runs on*, **never to a fixed estate name**,
and only a machine declaring `both` (the knight) is excluded. It named one thing
it did not settle, and required it **before the first personal-estate run**:

> *"whether `data/knowledge_curator/` sits inside the deposit contract. If a
> Curator report can travel, per-estate outputs are not sufficient on their own
> and a deposit exclusion is required."*

That run is now wanted. Two facts decide it. A Curator report carries **quoted
source spans** — literal substrings of conversation content, by 0032's
`quoted_source` rule — which is content, not summary, and 0027 keeps content out
of anything that travels. And per-estate outputs prevent *mixing*; they do
nothing to prevent *travelling*.

**A defect is recorded here because this entry is what corrects it.** The tab
does not implement 0039. `app.py`'s `curator_estate_gap` gates on *"declared
estate is not work/MCF"*, reason string `not_work_mcf_estate`, citing **0032**
— the clause 0039 amended three days before that code was written.
`curator_data.RATIFIED_MAP_PATH` is hardcoded to
`config/mcf_conversation_map.tsv`, which is the fixed estate name 0039 clause 1
forbids and the per-source pattern 0040 clause 2 replaced.

**Decision.**

1. **`data/knowledge_curator/` is outside the deposit contract**, excluded
   structurally rather than by remembering. The reports hold quoted content.
2. **The exclusion is enforced twice, deliberately.** A declared path exclusion
   in the deposit builder, **and** an auditor over the built deposit that fails
   if the artefact carries anything under `data/knowledge_curator/`. One states
   the rule, the other proves it held. This follows `auditor_readonly` and
   `auditor_stdlib`, which police properties the code could otherwise quietly
   lose, and it follows 0029, which was paid for once already when a deposit was
   found carrying more than its contract.
3. **The estate gate is corrected to 0039 clause 2.** The Curator runs on any
   machine whose declared estate is not `both`. `not_work_mcf_estate` becomes a
   reason naming the actual condition, and the tab's absence text stops citing a
   superseded clause.
4. **The ratified map is resolved from the declared estate name, never a fixed
   filename.** `config/mcf_conversation_map.tsv` becomes one instance of the
   pattern 0040 clause 2 declared; each estate's map carries its own committed
   fingerprint under 0040 clause 4 and 0045.
5. **The personal estate's sources are the Claude local transcript store and the
   Gemini share-scrape corpus.** Both carry a stable conversation id and so join
   under 0040 clause 1:
   - **Claude local transcripts** — `session_id` is the `local_<uuid>`
     conversation id, native and stable.
   - **Gemini personal via the share scrape** — `scraped_gemini/<share_id>.json`,
     keyed on the **resolved** `gemini.google.com/share/<hex>` form, never the
     reissuable `share.gemini.google/<token>` short link (0040 clause 1).

   **What is out is the Takeout export taken alone.** My Activity is a flat
   stream of turn-pairs whose `title` is the user prompt, with no per-record
   chat id — 0040's finding, unchanged. The distinction matters and was stated
   wrongly during this walk as *"Gemini personal has no identity"*: the **scrape**
   supplies identity and boundaries, the **Takeout** supplies real UTC
   timestamps, and 0040 clause 5 already ruled the two **jointly necessary**.
6. **Gemini personal enters the Curator only after `reconcile_gemini.py` has run
   for the conversations concerned.** The skeletons carry `created_date: None`
   and `published_date: None` — they hold no time at all — and 0032 clause 2
   makes recency the truth order, excluding and naming unresolvable-timestamp
   conversations. Reconciliation is not a nicety for this source; it is what
   makes it admissible.
7. 0039's clauses (1)–(5) are otherwise **unchanged**, including that the
   Curator never writes a `KNOWLEDGE*.md` file and never spans two estates in one
   run or one output.

**Consequences.** The first personal-estate Curator run becomes legal, and this
toolkit's own build conversations become the test corpus — a fairer test than
MCF, because the ground truth sits in this file and can be checked rather than
remembered.

Clause 3 means the estate gate stops being verifiable by reading one constant.
That weakening is the one 0039 accepted and priced, bounded by the same clause:
one run, one estate, one output.

Clause 2's double enforcement is the deliberate expense. A deposit that **can**
carry `data/knowledge_curator/` is a defect regardless of whether one ever has,
and an exclusion held only in the builder is a rule with no witness.

---

## 0045 — A pinned copy is one mechanism, not three: origin, anchor, hash, reported never repaired

**Date:** 2026-08-17 · **Status:** accepted · **Builds on:** 0040 clause 4 (the
map's committed fingerprint), `Claude_Migration` 0005 (the vendored parser as a
pin), ARCHITECTURE §5 (config is a shipped artifact), 0043 (cross-repo citation)
· **Source:** Grand Walk, 2026-08-17

**Context.** The same shape has now been designed three times, independently,
for three subjects:

| Subject | Where | State |
|---|---|---|
| `local_transcripts.py`, vendored | `Claude_Migration` `vendor/PROVENANCE.md` + `pack_builder/vendor_check.py` | **built, running** |
| `docs/README.md`, copied to other projects | `COWORK_BRIEF_convention_scaffold.md` Tasks 1–3 | designed, unbuilt |
| `config/*conversation_map.tsv`, untracked | 0040 clause 4 | fingerprint committed, **no checker** |

Each is *an artefact that cannot live in this repository's git in its live form,
plus a committed record of which version was ratified, checked at use so drift
is detected rather than assumed absent.* Three implementations of one mechanism
is two more than can be kept correct — the argument this estate already made
about path resolvers.

The field-tested format is the richest and is the one adopted:
`Claude_Migration`'s `vendor/PROVENANCE.md` records origin repo, origin path, the
origin commit last touching the file, the origin repo's HEAD at vendoring time,
the date and rig, and the content hash — **two commits rather than one**, because
*which release this is* and *what the world looked like when it was taken* are
different questions. That is the same reasoning 0040 clause 4 used for recording
a hash as well as a pin, arrived at independently.

**Decision.**

1. **One mechanism, one implementation.** A pin records: origin (repo and path,
   or `local` for an untracked file in this repo), the anchor commit where one
   exists, the date and host it was taken on, and the **content hash** of the
   pinned artefact. Every mention of another repo's anchor carries that repo's
   name, per 0043.
2. **Verification reports; it never repairs.** A mismatch is stated with both
   hashes and the artefact is left exactly as found — `Claude_Migration` 0005
   clause 4's rule, generalised. A tool that silently re-pins has destroyed the
   only signal the pin exists to give.
3. **An unresolvable anchor is a violation, not a silent pass** — the bar
   `auditor_uat_stamp` and the `gate-frozen` marker already hold.
4. **Reading a pin is read-only and may live in `l5gntools/`** (`hashlib` is
   stdlib; 0034 clause 1 untouched). **Writing or bumping one is not a scanner**
   — it writes, so it is a `run.py` command, dry-run by default.
5. **Working ahead of a pin is a normal state, not an error.** A live artefact
   may sit ahead of its pinned release; that is a draft, not drift. Report it as
   information so a bump is prompted, never forced.
6. **The pin record is one file per artefact, beside the artefact** — not a
   central registry. Both built cases already do this (`vendor/PROVENANCE.md`,
   `<map>.sha256`), and three reasons keep it: a pin must **travel with the
   artefact** when it is copied into another repository, which a registry in this
   repository structurally cannot do; a registry is a second place to forget to
   update, so the pin and the thing it pins can silently disagree; and a central
   list of the state of things held elsewhere is a status board by another name,
   which §5 of `docs/README.md` retires by class for exactly the rot it invites.

**Consequences.** `convention_scaffold` stops being a design problem and becomes
an application of an existing mechanism to a third subject — which is most of why
that round looked expensive. 0040 clause 4's fingerprint gains the checker it was
written without. And `Claude_Migration` can adopt this by name under its own 0001
rather than diverging.

The cost is that the first subject to use the shared helper pays for generalising
it. Accepted: the alternative is three verifiers with three mismatch messages and
three ways to be subtly wrong about what a hash covers.

---

## 0046 — The curated map resolves by recency: the last row for a key wins, every consumer resolves it the same way, and a superseding row says so

**Date:** 2026-08-17 · **Status:** accepted · **Builds on:** 0032 clause 2
(recency as truth order), 0033 (stage, never commit), 0040 (the curated map is
the join of record) · **Source:** Grand Walk, 2026-08-17

**Context.** A hand-ratification cannot currently be undone. A row clicked to see
what it did is permanent, and the module is **right** to make it so:
`curator_ratify.append_ratified_row` is *"a pure byte-append (opened `"a"`, never
`"r+"` or a rewrite)"* and *"provenance is permanent."*

Deletion is the wrong fix, and this estate has ruled it three times already:
DECISIONS is append-only and superseded by a later entry naming the earlier;
`docs/README.md` §4 rules that *"a reverted action is another line, not a
deletion"*; 0029 replaces a deposit that carried too much rather than editing it.

**The rule that makes correction possible is already written.** 0032 clause 2 —
recency as truth order — is unchanged by 0039. In an append-only file, **file
order is recency**, so no timestamp column is needed.

**What is missing is the reader.** `curator_data.ratified_map_rows` returns every
row with no resolution, so a second row for the same `session_id` today produces
a **duplicate**, not a correction — and the join of record would disagree with
itself depending on which consumer asked.

**Decision.**

1. **The last row for a given key wins.** Earlier rows for that key are
   superseded, retained in the file as provenance, and never deleted. The key is
   the source's resolved conversation id (0040 clause 1) — `session_id` for the
   Claude local store.
2. **Resolution happens in exactly one place**, and every consumer calls it —
   `knowledge_index.py`, `match_claims.py`, `candidates.py`, `curator_data` and
   the Curator tab. **Two implementations of the join of record is one more than
   can be kept correct**, the argument 0027's containment check already won.
3. **A superseding row carries an explicit status** (`corrected`, `revoked`) as
   well as being later. Recency alone resolves it; the status makes the *intent*
   legible to a human reading the raw file, which recency cannot express. A row
   that supersedes without saying so reads as a duplicate to everyone except the
   resolver.
4. **A raw, unresolved view remains available and is the reviewing view.** The
   superseding row and the row it supersedes are both visible to a human
   ratifying; only the *consuming* read resolves. A correction that hides what it
   corrected is a deletion wearing a different hat.
5. **Undo is an append.** Correcting a ratification means appending a row for the
   same key with the corrected `project_id` and a status per clause 3, its
   `notes` stating what it supersedes and why — the per-row provenance discipline
   0040 clause 2 already requires. Nothing is rewritten.
6. **Capture is the same act.** A conversation K0 never proposed a candidate for
   — the case `unmapped_local_folders` already reports — is entered through the
   same `build_row` → `_validate_new_row` → `append_ratified_row` →
   `stage_ratified_map` path, from the UI, rather than by hand-editing the TSV.
   One writer, one validation, one staging rule (0033).

**Consequences.** The map becomes correctable without becoming mutable, which is
the property that made it trustworthy. A mis-click is recoverable, so
ratification stops being a decision a human has to be afraid of — and a surface
people are afraid of is one that gets used carelessly, or not at all.

Clause 6 closes the case K0 structurally cannot reach: a conversation whose
opener the model never matched. Those were being entered by hand into a file the
tool owns, which is exactly the side channel that makes an audit trail untrue.

The cost is that the map grows monotonically and now contains rows no longer in
force. That is the cost DECISIONS pays, for the same reason. 0040 clause 4's
fingerprint continues to record what was ratified and when — a superseded row is
part of that history, not noise in it.


---

## 0047 — 0021's supervisor is superseded: there are no longer three processes to coordinate

**Date:** 2026-08-17 · **Status:** accepted · **Supersedes:** 0021 (the
supervisor runs the read/review/deck trio) · **Builds on:** 0013 (serve a
snapshot, never the live vault), 0034, 0035 (`run.py app` is the single entry
point) · **Source:** `COWORK_REPORT_unified_app.md`, closing out an obligation
the build flagged and could not yet discharge

**Context.** 0021 ruled that one supervisor should bring up `serve`, `review` and
the deck together, because the knight was starting to run three long-lived
processes and keeping them alive in step was becoming a real cost.

`COWORK_BRIEF_unified_app.md` Task 3 mounted Datasette as an **ASGI sub-app** of
the review app, and Task 4 made `run.py app` the single entry point (0035 clause
1). After both, there are **zero processes left to supervise for this half**:
one process, one port, one loopback bind.

`chronicler/review/datasette_mount.py` recorded this at the time and declined to
act on it, correctly — *"0021 is not wrong, it is moot — superseded by there
being nothing left to coordinate. Record it here rather than editing 0021 (the
log is append-only); a future DECISIONS entry can mark 0021 formally superseded
when Task 4 lands the single entry point."* Task 4 landed. This is that entry.

**Decision.**

1. **0021 is superseded.** The coordination problem it solved no longer exists.
   Its reasoning was correct for the shape it addressed and is preserved
   unedited, as the log requires.
2. **The supervisor is not to be rebuilt** as a way of running the deck. A
   second long-lived process for this purpose would recreate the problem 0021
   was written to manage, and `unified_app` was largely about removing it.
3. **0013 is untouched.** Datasette still serves a snapshot, never the live
   vault. The process boundary moved; the reason did not — a co-resident writer
   breaking `--immutable` is the identical failure 0013 diagnosed, and this
   process contains one.
4. **If a second long-lived process is ever proposed**, this entry is not an
   objection to it — but 0021 is the precedent for what it costs, and it should
   be read before, not after.

**Consequences.** One fewer standing obligation, and the deck's operational story
becomes a shortcut rather than a supervised trio. The cost is that Datasette's
staleness is now tied to the app's lifetime rather than its own — *"restart the
app"* replaces *"re-launch `run.py serve`"*. That is one fewer thing to remember,
not a new promise about freshness.

---

## 0048 — The unit of throughput is a decision; a surface that wants attention raises a card

**Date:** 2026-08-18 · **Status:** accepted 2026-08-19 · **Builds on:** 0031 (findings,
never verdicts), 0033 (propose, ratify, execute) · **Source:** the Quartermaster
vision thread, `docs/investigation/2026-08-17_quartermaster_fable_2-response.md`
(carried there as **D-A**) · **Depends on:** INTENT §8

**Context.** Every surface this estate has built shows *artifacts* — scans,
reports, boards, threads — because artifacts are what the system produces. But
artifacts are not why it exists. INTENT §8 now states the widened thesis: the
decision is the product, and the record exists so decisions arrive cheaper,
fewer and durable.

That reframe only becomes operative if it changes what a surface is allowed to
be. Today a new tab is justified by the facts it can display. Nine tabs later,
the cost of that justification is visible: surfaces are visited on patrol rather
than because something needs deciding.

**Decision.**

1. **The unit of throughput is a decision, not an artifact.** A surface that
   asks for the operator's attention raises a **card**. Everything else —
   dashboards, browsers, transcripts, free query — is the reference room,
   reached from a card's evidence, not patrolled.
2. **The card's anatomy is fixed**: the question in one sentence; the trigger
   that made it necessary now; the evidence, pre-assembled, each item carrying
   its provenance; the options, with their cost where a measurement exists and
   no estimate where none does (0037 clause 4); a default; an expiry. **A card
   missing any field is not raised** — an unassembled card spends the attention
   it was built to save.
3. **Silence is an input, and its consequence is stated on the card.** What
   happens if the operator does not rule, and when, is never implicit.
4. **`default` and `expiry` are declared now and inert until a policy engine
   exists.** Every default reads `hold — nothing runs`; expiry only re-raises a
   card marked `aged`. This is deliberate, and named because a field identical
   on every card for months trains the eye past it — their going live later is a
   change the operator should be told to expect, not discover.
5. **A standing ruling carries a sunset.** A policy expires unless renewed, and
   renewal is itself a card carrying that policy's own firing record as
   evidence. A policy that has authorised nothing since the week it was made
   answers its own renewal question. This is preferred to a policy-watching
   actor for INTENT §5's reason: prefer *can't* to *shouldn't*. A watcher is one
   more thing to own at 2am; an expiry needs owning by no one.

**Consequences.** A new surface must now be justified by the decisions it moves,
not the facts it shows — which is a harder bar, and meant to be. The estate's
existing surfaces are not retired by this entry; they are reclassified as
reference, and the Desk becomes the front door aspiration made literal.

Clause 2's "not raised" is the expensive clause: a trigger the system cannot
evidence produces no card at all, so some real staleness will go unreported
rather than reported thinly. That is the intended trade — INTENT §5's fail-loud
rule says a plausible wrong answer is worse than none, and a bare accusation
with no evidence is exactly that.

**What would show this wrong.** If cards arrive faster than they are ruled, or
if the operator rules without reading the evidence because assembling it was
never the expensive part, the anatomy is wrong and this entry is the thing to
re-argue — not the surface built on it. INTENT §8's first added failure mode
(*"the desk becomes a feed"*) is this entry's own alarm.

---

## 0049 — Frontier conversations are a sensed input; the system moves work down-tier rather than budgeting spend it cannot see

**Date:** 2026-08-18 · **Status:** accepted 2026-08-19 · **Builds on:** 0037 (measurement
before estimation; refuse, never clamp), 0040 (the conversation corpus and its
joins) · **Source:** the Quartermaster vision thread,
`docs/investigation/2026-08-17_quartermaster_fable_2-response.md` (carried there
as **D-B**), redrafted 2026-08-18 · **Depends on:** INTENT §8

**Context.** The vision proposed a frontier *envelope*: a weekly allowance drawn
down by logged spend, with the planner refusing a plan that would exceed it.
That version does not survive contact with how the frontier is actually used
here.

The toolkit does not invoke frontier models and is not going to — a frontier
step in a plan is a prepared handoff, not an API call. So spend happens in
vendor interfaces, outside any ledger, and an envelope would be drawn down by
numbers the operator typed in about work the system never saw. **A figure
nothing observes must not be given the authority to refuse a plan.** That is the
fabricated-number failure 0037 already refuses in the estimation case.

What the estate does have is the conversations themselves: ingested, and already
mined for claims by the Curator. The useful question is not *how much was
spent* but *what was asked repeatedly that a local tier could have prepared*.

**Decision.**

1. **The toolkit invokes no frontier model.** A frontier step in any plan is a
   prepared handoff — assembled context and a stated question — never a direct
   call. Direct invocation, if ever wanted, is its own entry.
2. **There is no spend envelope, and no plan is refused on a spend number.**
   This clause exists to prevent a precise-looking number nobody measured from
   acquiring authority.
3. **The conversation corpus is a sensed input for down-tier opportunities.**
   Recurring asks — work of a shape that keeps coming back — are surfaced as
   findings against the corpus, the same way any other sensor reports.
4. **A down-tier proposal names the local capability that would replace the ask,
   and the evidence that it can.** Without both it is a wish, and wishes are the
   thing INTENT §6's first failure mode is watching for.
5. **Success is the recurrence declining in the corpus, observed** — never a
   claimed saving, and never the label on a purchase.

**Consequences.** The economic half of the Quartermaster frame stops being a
budget mechanism and becomes an observation mechanism, which is the only half
this estate can honestly build. It also relocates the work: finding repeated
asks is a query over claims, so it belongs beside the Curator's linking work
rather than in a separate accounting round.

The cost is that nothing stops an expensive week. This entry offers no brake,
because the brake it replaced was decorative — and a decorative brake is worse
than none, since it invites the belief that spending is governed.

**What would show this wrong.** If the corpus turns out to hold no legible
repetition — if every frontier session is genuinely novel — then clause 3 has
nothing to sense and the entry is an elegant description of nothing. That is
testable against the corpus that already exists, and should be tested before
anything is built on it.

---

## 0050 — A source declares its own staleness as a feed; the Desk consumes declared feeds, and a source it cannot reach reads as unknown, never as fresh

**Date:** 2026-08-19 · **Status:** accepted 2026-08-20 · **Builds on:** 0042 (a consumer
repo declares its own runnable stages; clause 7 — where a repo answers a
question about itself, ask it), 0048 (the card anatomy; a card missing any
field is not raised), 0047 (one process, modules in it), 0025 and 0036 (a
loopback single-estate surface is not gated; the mesh stands down) ·
**Source:** design thread, 2026-08-19, following the Desk's first build round
· **Brief:** `COWORK_BRIEF_staleness_feeds.md`

**Context.** `desk.py` derives cards from two hard-coded triggers, both read
out of wizard manifests: delegated staleness and dependency staleness. That
was the right size for one card type on one fixture repo, and it worked.

The next source of staleness is a cloud-export manager on the work rig which
already knows, on its own terms and against its own schedule, which exports
are stale. The obvious implementation is a third branch in `cards()`. The one
after that is a fourth for `sf-data-service`.

Follow that line and the Desk becomes what the deck was before
`modules.ModuleDescriptor`: one surface accumulating a special case per
source, where every new source requires a change to *this* repo before
another repo's staleness can be seen at all. This estate has already paid to
learn that lesson twice — once with the module registry, once with 0042's
manifests — and both times the fix was the same shape: **the thing that owns
the work declares it; the surface consumes the declaration.**

There is a second, quieter reason. Two of the sources that matter most are
**cadence-shaped**, not dependency-shaped: a statement due by the 5th of the
month, a sync that should have run last night. No arrangement of mtimes and
`depends_on` expresses those. Teaching the Desk a calendar would be building
the second freshness engine 0042 clause 7 exists to forbid — a competing
opinion about a question the source can already answer.

**Decision.**

1. **Staleness is declared, not detected.** A repo may declare a
   `staleness_feed` in its committed manifest: a read-only command, run under
   the existing allowlist, containment and literal-argv rules, printing a
   list of items. The Desk renders those answers as cards. It computes no
   staleness of its own and applies no threshold to a feed's verdict.
2. **One contract, not one integration per source.** A new source is a new
   declaration in the repo that owns it — never a new branch in `desk.py`.
   The two existing triggers become one provider of the same item shape,
   behaviour and fingerprints unchanged.
3. **Cadence lives in the source.** An item whose staleness comes from a
   schedule is an ordinary item whose source computed it and whose evidence
   states the schedule out loud. The Desk holds no cron, no expected-interval
   field, and no opinion about the 5th of the month.
4. **A source that cannot be reached reads as `unknown`, never as fresh.** A
   feed that times out, exits non-zero, or prints unparsable output raises no
   cards — and an empty Desk is indistinguishable from good news, so it must
   not be the only signal. Every declared feed's last outcome is rendered as
   a health line, and a failure is recorded as an event. Silence is never
   evidence of freshness.
5. **An item that cannot fill 0048's anatomy raises no card, visibly.** In
   particular an item claiming staleness without stating when it became
   observable has no latency clock and no expiry, so it is not raised — and
   the reason appears on the health line rather than nowhere. 0048 clause 2's
   trade, taken again, with its cost made visible this time.
6. **A feed may name an action; it may not name work.** An item's optional
   action is an existing `(repo_key, stage_key)` pair from a validated
   manifest the host's allowlist already permits, checked at parse time. The
   Desk gains no execution path: the button posts the wizard's existing
   execute route with that pair and nothing else (0037, 0042 clauses 3–4).
   An item with no valid action is an acknowledge-only card, which is a
   legitimate and expected shape.
7. **The contract crosses machines; data never does.** A second rig runs its
   own Desk against its own feeds, allowlist and sidecar. What is shared
   between rigs is this schema and the card anatomy, copied. There is no
   aggregation, no listener, no shared store — 0036 stands unamended.
8. **The ruling vocabulary belongs to the card, not the module.** An item may
   declare the options it offers; the Desk validates a ruling against the
   options *that card actually offered*, not against a module-level list.
   `rebuild / snooze / dismiss` was staleness's vocabulary and generalises
   badly: a ratification decision is `ratify` or `refuse`, and recording a
   refusal as `dismiss` would erase exactly the distinction promotion
   detection is built to read (0048 clause 5; the Dispatcher's Task 3). **An
   option that carries no action is a first-class outcome, not a lesser one**
   — recording which way the operator decided is the point, and a card whose
   consequence is a human act elsewhere still produces a real ruling. Where
   the record and the world then disagree, the world wins and the card
   re-raises: cards derive, so a ruling that claims a thing was done, on a
   source that still reports it undone, is self-correcting rather than
   authoritative.

**Consequences.**

**The Desk's card quality is now bounded by its sources' honesty, and the
Desk cannot tell.** A source with a broken clock or a wrong schedule reports
confident nonsense and the Desk repeats it faithfully. This is the same trade
0042 clause 7 already took, one gate further out, and the mitigation is the
same and only partial: the answer is quoted verbatim with its source named,
so a wrong card is legibly *that source's* wrong answer rather than an
anonymous claim by the system. It is worth restating that this is a real cost
and not a technicality — the previous design's triggers were dumb, but they
read the filesystem directly and could not be lied to.

**The two rigs will drift.** Feed implementations on the work rig will learn
things this contract does not know, and there is no mechanism here to
reconcile them — deliberately, because every mechanism that would is a mesh.
Reconciliation is a human reading both and amending the contract, which is
Phase 5's extraction work and is named here so it is expected rather than
discovered.

**The Desk now costs wall clock to open.** Feeds are polled on render, with
timeouts. A slow feed makes a slow tab, and a slow tab gets visited less —
which is the exact failure the whole programme is trying to remove. The
budget and its overrun must be measured and stated, never hidden behind a
cache that quietly serves an old answer.

**What would show this wrong.** If, after two or three real sources, the
contract has had to be extended for each one, then the seam is in the wrong
place: the variation is in the sources, not at their boundary, and three
honest branches in `desk.py` would have been the cheaper truth. The test is
concrete — count the schema changes per source wired. One extension across
three sources vindicates this entry; three extensions across three sources
refutes it, and the refutation should be written as its own entry rather than
absorbed as maintenance.

**Noted against that test before it starts:** clause 8 was added to this
entry *while it was still `proposed`*, prompted by its first intended
consumer (the workcycle feed) needing a ruling vocabulary that staleness's
three verbs could not express. That is legitimate — an unratified entry is
meant to change on re-read — but it is also one extension banked before a
single source is wired, and it should be counted as such rather than
forgotten because it happened before the clock started.

---

## 0051 — A work-estate corpus may live on the personal rig, bounded by construction rather than by intention: conversations are named frozen snapshots, the repo mirror is replaced whole and never accumulated

**Date:** 2026-08-22 · **Status:** accepted 2026-08-28 · **Builds on:** 0023 (work-estate
visibility is auth-gated), 0025 (visibility is scoped by surface), 0027
(summary-only governs artefacts that travel; a local surface reads the source
at render time), 0029 (a bundle that violates its own contract is replaced or
removed whole, never scrubbed in place), 0036 (the cross-machine mesh stands
down), 0044 (`data/knowledge_curator/` sits outside the deposit contract
*because* Curator reports carry quoted source spans) · **Source:** design
thread, 2026-08-22, at the Claude tenant migration

**Context.** The migration forced every work repo to a clean, committed state
on one day, and produced a dated snapshot of that moment: two git bundles
(WizForgeAnalytics and its `sf-data-service` submodule, whose recorded
pointer matches the submodule bundle's HEAD exactly), an estate report taken
after the git work closed, and two conversation tarballs — the raw export and
a processed pack.

The walls this estate built — 0023, 0025, 0027 — exist so work data does not
leak into a personal estate that syncs, publishes and deposits. They were
never meant to make the operator work blind on their own side of the fence,
and that is what they currently do: personal work intended to serve the work
persona has no corpus to develop against, so the harness is being designed
against imagination.

Two properties of this particular artefact make it different from the live
access those rulings refused. It is **frozen** — a snapshot of one day, which
cannot grow, refresh or sync. And it is **bounded** — it can be deleted whole,
in one act, leaving nothing behind. That is categorically unlike the
cross-machine mesh 0036 stood down, which was a standing channel.

**Amended before ratification, 2026-08-24.** Clause 1 originally allowed one
named snapshot and nothing else. Two needs surfaced immediately: the repo
half wants refreshing when the work side asks the personal side for something
that requires reading it, and the conversation half wants one further
snapshot so the new tenant's shape can be checked against the old one rather
than assumed. Refusing both would have made the entry a rule kept by not
using it.

The distinction the amended clause turns on is **accumulation, not
frequency.** A git bundle of a repo *replaces* its predecessor — a newer
bundle contains the older one's history, so holding the new one and deleting
the old leaves exactly one artefact and loses nothing. Conversation exports
do not work that way: each is a distinct slice of time, and a second one sits
*beside* the first rather than superseding it. Clause 1's original fear was a
corpus that grows without anyone deciding it should. A mirror replaced whole
does not do that; a pile of exports does. So the two halves get different
rules, and the frequency question turns out to have been the wrong axis.

One argument offered for it is explicitly **not** relied on here: that the
corpus "goes stale by not being in the new loop". Staleness is an argument
about *relevance* — it explains why the corpus will stop misleading the
operator. It says nothing about confidentiality. Stale employer data is still
employer data, and no clause below rests on that reasoning.

The scrub is also not claimed to be complete. Measures were taken; leakage is
possible. This entry is written on the assumption that something got through,
which is why the mechanism is structural rather than a promise.

**Decision.**

1. **What may be held is named here, and the two halves are governed
   differently — by whether they accumulate, not by how often they arrive.**

   **(a) Conversation exports are named, dated, frozen snapshots.** The
   2026-08-22 pre-migration export may be held. **One further export may be
   taken after the migration**, for the single stated purpose of checking the
   new tenant's shape against the old — pre and post, two named artefacts,
   compared. Neither grows: no sync, no refresh, no incremental top-up. A
   *third* export is a third entry, with its own reasoning, because each one
   sits beside the last rather than replacing it and a pile is what this
   clause exists to refuse.

   **(b) The repo mirror is replaced whole, on demand, and never
   accumulated.** Bundles of the WizForgeAnalytics program repo and every
   submodule beneath it may be re-taken on the work rig and carried across by
   hand. Three conditions bound it, and all three are structural rather than
   intentions:

   - **A run needs a stated reason recorded with it** — specifically, that
     the work side has asked the personal side for something that requires
     reading the repo. No request, no bundle. This is not a schedule and must
     never become one; a periodic mirror is a sync with extra steps, and 0036
     already stood down the standing channel.
   - **Landing a new mirror removes the previous one and everything cloned
     from it, as one act.** Exactly one mirror exists at any moment. This is
     clause 5's posture applied per-refresh rather than only at the end, and
     it is what keeps the corpus from growing while being refreshed.
   - **The transport is manual and one-directional.** Nothing on the personal
     rig may fetch, pull or reach the work rig, and a clone made from a
     bundle has its origin removed so it cannot. What arrives, arrives
     because a person carried it.

   Clauses 2 to 6 apply to everything named here, unchanged and at full
   strength.
2. **It lives at a declared path, outside every scanner root.** The corpus and
   everything unpacked from it sit under one declared directory that no
   estate scanner walks and no deposit carries. Enforced by an auditor over
   the built deposit, the way 0044 enforced `data/knowledge_curator/` — a
   path exclusion plus a check that the exclusion held, because 0029 was paid
   for once already.
3. **Derivatives inherit the containment.** Anything extracted from the
   corpus — claims, knowledge indexes, match reports, census output — lands
   under the same declared path and travels no further. A corpus that never
   leaves the rig, whose `claims.json` reaches a deposit, is the same leak
   with extra steps. 0027 applies at full strength: quoted spans are content,
   and content does not travel.
4. **The known carriers are named, so they can be checked rather than
   assumed.** Commit metadata in `sf-data-service` carries an employer email
   address, so any author rollup surfaces it. That repo also tracks nine daily
   `logs/sf_service_*.jsonl` service logs — the highest-risk content in the
   pack. Both are inside the declared path and neither may be read by a
   surface that publishes.
5. **Deletion is one act, and nothing outlives it.** The snapshot can be
   removed whole. No index, cache or derived artefact may hold a copy that
   survives that removal — 0029's posture, that testimony is kept intact or
   removed rather than partially scrubbed, applied to a corpus rather than a
   deposit.
6. **The exclusion is declared, never silent.** A scanner that skips this path
   says so in its output. An estate report that omits a directory inside its
   own root, without saying it omitted one, is a confident wrong picture —
   the failure INTENT §5 refuses everywhere else.

**Consequences.**

**The toolkit goes blind inside its own estate root, on purpose.** The
scanners cannot see this folder, so `report.html` is incomplete by
construction and every count it reports excludes it. That is the trade:
visibility given up for containment. Clause 6 keeps it honest by making the
gap visible, but a gap that is visible is still a gap, and any measurement
taken across the estate from now on carries an asterisk this entry put there.

**Governance tooling cannot govern this corpus.** Everything the estate built
to notice drift, duplication and untracked risk is exactly what may not run
here. The corpus is therefore held to a lower standard than the rest of the
estate at the same moment it carries the most sensitive content in it. That is
uncomfortable and it is stated rather than absorbed.

**A refreshed mirror carries more of the highest-risk content than the one it
replaced, and clause 1(b) does nothing about that.** Clause 4 names the nine
`logs/sf_service_*.jsonl` service logs as the worst of it. A bundle taken
three months from now carries every log written since, and "replaced whole"
means the quantity of employer content on this rig ratchets up each time
while the *number* of artefacts stays at one. Holding one file is not the
same as holding less, and the clause's honest description of what it bounds
is the artefact count, not the exposure. The exposure grows with the work.

**"A stated reason" is the weakest clause in this entry, because the operator
is the one who states it.** Every other bound here is structural — a path a
scanner cannot walk, an origin that is removed, a predecessor deleted. This
one is a habit, and it is the clause that will quietly become a schedule if
it fails. It is written this way because the alternative — a mechanism
deciding when a bundle is warranted — needs a thing that can see the request,
and no such thing exists on this side of the wall.

**What would show this wrong.** If a derivative escapes the declared path —
found in a deposit, a report, or a synced artefact — the mechanism failed and
the corpus goes, not the mechanism. And if, in practice, useful work turns out
to require lifting the containment, then the honest conclusion is that the
wall was drawn in the wrong place and needs redrawing by its own entry — never
that the containment is inconvenient and may be worked around case by case.

**Two counts for clause 1(b), and the first is the one that kills it.**

**Count mirror refreshes that were not preceded by a request from the work
side.** Clause 1(b) rests entirely on there being a reason each time. One
refresh taken because it had been a while, or because a build thread was
about to open and it seemed prudent, is the clause failing in the only way it
can fail — and it will not look like a failure at the time, it will look like
being organised. If that count is not zero at three months, 1(b) should be
replaced by something structural or withdrawn, not restated.

**Count mirrors held simultaneously.** The answer is one, always, by
construction. Two — an old clone left beside a new one because deleting felt
premature — means "replaced whole" was aspirational and the corpus is
accumulating exactly as clause 1(a) refuses for exports. Cheap to check and
worth checking, because it is the difference between this entry's reasoning
and its wishful version.

---

## 0052 — A skill scripts a procedure and cites its convention; the convention lives in the repo, because skills do not migrate

**Date:** 2026-08-22 · **Status:** accepted 2026-08-28 · **Builds on:** 0042 (a consumer
repo declares its own runnable stages — declaration belongs to the repo that
owns the work), 0043 (a ruling from another repo is cited with its repo, at
every mention), 0030 (`docs/README.md` §1's governing rule: a document earns
its place by holding something that cannot be derived) · **Source:** design
thread, 2026-08-22, and the work rig's `HANDOVER_ADDENDUM_2026-08-22.md` §5

**Context.** Two independent findings, from opposite sides of the wall, in the
same week.

On this rig, `commit-scribe` measured the last 40 commits and found 33 of 40
carrying the house prefix — with the seven failures clustered in a single build
thread. The conclusion written into `CONVENTION_commits.md` was that a
convention living in whoever happens to be typing is not a convention, and the
fix was to put the format in a document and have the skill cite it.

On the work rig, a migration handover reached the same conclusion from the
other direction: reasoning had been put in commit bodies and a fresh thread
reads files. Its §5 names the sharper case — **the sandbox-git hazard lives in
one skill, which is the one thing that does not migrate** — and records that it
cost two separate threads an hour each, the second one rediscovering what the
first had already learned.

Meanwhile 0050 predicted that two rigs sharing a contract would drift. Within
seventy-two hours, the work-side copies of both the commit convention and the
`commit-scribe` skill had diverged in size from the personal ones, with nothing
recording what changed or why.

Five skills now exist on this rig. Two of them have no convention document to
cite, which means they carry their format themselves. That is the state this
entry rules on, not a hypothetical.

**Decision.**

1. **A skill scripts a procedure with a judgement boundary.** A thing that
   produces a fact with no judgement step is a script or a feed, and making it
   a skill adds a layer that can drift without adding a decision anyone makes.
2. **The convention lives in the repo that owns the work; the skill cites it
   and does not restate it.** Where the two disagree, the convention wins and
   the skill is the artefact that needs updating. This is 0042 clause 1 applied
   to conventions rather than to runnable stages: declaration belongs to the
   thing that owns the work, and a skill owns a procedure, never a rule.
3. **No rule may have a skill as its only home.** A rule discovered while
   writing or running a skill lands in a convention document first, and the
   skill then cites it. A skill is a consumer of rules and never their
   registry.
4. **An environment rule belongs to the environment, not to a skill.** The
   worked example is the sandbox-git hazard: never run plain git against a
   mounted Windows repo from a sandbox. It binds every thread doing anything,
   not only threads drafting commits, and it currently sits inside one skill —
   which is precisely why it was learned twice.
5. **A skill with no convention to cite says so in its own text and names the
   debt.** It may carry the format in the interim; it may not do so silently.
   `brief-scribe` is written this way and is the pattern.
6. **A skill is edited from observed misbehaviour, and the edit cites the run
   that prompted it.** Review-driven polish of a skill nobody has run is how a
   procedure accumulates rules for problems it does not have.

**Consequences.**

**This entry creates debt on the day it is made.** `brief-scribe` and
`round-closer` have no convention document, so under clause 5 they carry their
format and announce themselves as the drift risk. That is honest and it is
still debt, and it will be discharged slowly or not at all, because writing a
convention is less interesting than writing the skill that uses it.

**Adding a skill gets slower, and the friction lands at the worst moment.**
Clause 3 means the convention comes first, which will feel like ceremony
exactly when the procedure seems obvious — and a procedure that seems obvious
while you are writing it is the one whose rules are least written down.

**More documents, and conventions rot too.** This trades a rotting skill for a
rotting document. The trade is taken because a document in `docs/` is visible
to the gate, to `docs_board`, to the archivist and to a cold reader, whereas a
stale rule inside a skill is visible to nobody until it is wrong in front of
someone.

**It does not fix cross-rig drift.** Two rigs will still diverge; 0050 already
said so and this entry does not amend it. What changes is only that the
divergence becomes **locatable** — two files that can be diffed — instead of
invisible, which is two behaviours that can only be compared by watching them.
That is a smaller win than it sounds and worth naming as smaller.

**What would show this wrong.** Two counts, both cheap.

**Count the rules whose only home is a skill.** Today it is at least one (the
sandbox-git hazard, on the work rig). Under this entry it should trend to zero.
If after three months the count is level or rising, the ruling is not being
followed — and the honest reading then is not that the operator lacks
discipline but that clause 3's cost is too high in practice, in which case this
entry should be replaced by something cheaper rather than restated more firmly.

**Count the rules rediscovered the hard way at the next rig or tenant switch.**
The 2026-08-22 migration recorded two, one of them learned twice. If the next
switch records the same number or more, this entry did not do the job it was
written for, whatever the first count says.
---

## 0053 — The gate emits verdicts only: a check that can go red without a defect belongs outside it, split by a committed per-host declaration and never by a third exit state

**Date:** 2026-08-24 · **Status:** accepted 2026-08-28 · **Builds on:** 0031 (a non-gating
check surface reports findings and never issues a verdict — the *witness*
category, which never gates), 0045 (verification reports and never repairs; a
tool that silently re-pins has destroyed the only signal the pin exists to
give), 0042 (per-host configuration is resolved through `config.machine()`,
not re-derived) · **Source:** the work task force's `TOOLKIT_notes_2026-08-23`
§1.1 and §1.1a, produced from a `verify.py` run on a clean checkout at
`25f1120`

**Context.** `verify.py` went red on a clean checkout of a consumer host. One
of the three failures was `auditor_conversation_map_pin` reporting a hash
mismatch — and the auditor was working exactly as 0045 clause 2 requires: it
stated both hashes and repaired nothing.

The diagnosis, done on the consumer side before the complaint was sent, found
no drift at all. The map is untracked and travels by hand; its pin is tracked
and travels by `git pull`. The pin on that host was five days newer than the
map it fingerprints, because the map had been edited and re-pinned on the
authoring rig and the copy had never been re-handed. Nothing was corrupt. The
auditor's `CLEAN_STATES` covers *no copy* and *current copy* and fails on the
state in between — which is the state every consumer machine spends most of its
life in.

Two things follow, and only one of them is about the pin.

**The gate lost its meaning, not its correctness.** A correct, informative
"understand this before re-pinning" and a genuine "the scanner is broken"
arrive through the same exit status, and `.githooks/pre-commit` cannot tell
them apart. The complaint's own sentence is the hazard: the next red gets
waved through by the same reasoning that waved this one, and the one after
that.

**The printed remedy is destructive where the finding can appear.** The
finding says to re-pin deliberately with `run.py pin bump`. On the authoring
rig that is right. Run on a consumer machine it computes a pin from a stale
copy and commits it over the authoritative fingerprint — replacing a correct
pin with a wrong one, converting a false alarm into real corruption, and
turning the gate green. Nothing currently says not to.

0031 already drew the line this entry needs. It invented the **witness**: a
deterministic surface that emits findings, never a verdict, and never gates.
What it did not say is the converse, and the converse is what broke here — the
gate had a finding-producer inside it.

**Decision.**

1. **`verify.py` emits verdicts only.** A red means *this tree is defective on
   this host*. A check that can go red for a reason which is not a defect on
   the host it is running on does not belong in the gate.
2. **Where a check is a defect on one host and an observation on another, it
   is split by a committed, per-host declaration**, resolved through
   `config.machine()` — never by a flag, an environment variable, or a
   caller's argument. **The declaration has to be the thing the check
   actually turns on.** `role` is the right axis where the question is what a
   host is *for*; it is the wrong axis for the pin, because this estate has
   two `producer` hosts and the question is which of them authors a given
   artefact. Authorship is therefore declared **per artefact** — `authors` in
   `machines.json` / `local.json` — and an artefact no host declares is
   refused everywhere rather than permitted everywhere. A check that invents
   a split no declaration carries has chosen its axis instead of reading it,
   which is the same failure as a flag with better manners. The authoring
   host gates; a host holding a copy does not.
3. **There is no third exit state.** Two states, and the hook keeps one
   meaning. A state that means "red, but you may proceed" is waived by
   definition, and once one red is waivable the operator is judging every red
   rather than reading one.
4. **A check that cannot make the distinction degrades to a named clean
   state**, and says in its own output which state it took. A skip that
   announces itself is a finding; a skip that is silent is indistinguishable
   from a pass, which is the failure INTENT §5 refuses everywhere else.
5. **A remedy printed by a check must be safe to run wherever that check can
   fire.** Where it is not, the tool it names refuses on the hosts where it
   would be wrong — `run.py pin bump` refuses where the artefact is not
   authored. A remedy that is correct on one machine and destructive on
   another is a defect in the *message*, not an error by the operator who
   followed it.
6. **0045 clause 2 is untouched.** Report, never repair, still stands
   unchanged. This entry rules on *where* a report is emitted and *who* it
   gates, not on whether it may fix what it finds.

**Consequences.**

**The gate gets weaker on consumer machines, deliberately and specifically.**
After this, a consumer host's `verify.py` will not tell it that its
hand-copied map is stale. That knowledge does not move somewhere better by
itself — it is simply not in the gate any more, and unless a witness (0031) or
a declared feed (0050) picks it up, it is lost. The trade is taken because a
gate that reports non-defects stops being read at all, and a channel nobody
reads carries nothing either. But the loss is real between the split and the
replacement, and that gap should be measured rather than assumed brief.

**Green now means different things on different machines.** A role-dependent
gate is harder to reason about than "green is green", and it makes "did the
gate pass" an incomplete question — the answer needs a host. That is a genuine
complication and it is the price of clause 1.

**Existing auditors may already fail clause 1.** Applying this entry is not
free: it will evict checks that people are used to seeing in the gate, and
each eviction will feel like a loss of coverage at the moment it happens. The
honest reading of that feeling is that the coverage was in the wrong channel,
not that it was worth having there.

**Clause 2 buys its correctness with a declaration someone has to remember to
write.** An artefact nobody declares is refused everywhere, which is the right
default and is also a new way to be stuck: the operator meets a refusal whose
fix is a config edit, at the moment they were trying to clear a red. That is
preferred to the alternative — an undeclared artefact being pinnable anywhere
— because the failure it replaces was silent corruption of an audit trail, and
this one announces itself and names the file to edit. It is still friction
that did not exist before, and it lands on the authoring rig as much as
anywhere.

**What would show this wrong.** Two counts, and the second is the one that
could kill the entry.

**Count reds on a clean checkout, per host, over a month.** If a consumer
host's `verify.py` still goes red for things that are not defects on that
host, clause 1 is not being applied and the split has not actually happened.

**Count defects found later that a pre-split gate would have caught.** If
moving finding-producers out of `verify.py` means real defects start reaching
commits on consumer machines, the line was drawn in the wrong place — and the
right response is to move it, not to re-argue clause 3. If that count is
non-zero within the first quarter, this entry is wrong in its detail even if
right in its principle.
---

## 0054 — Configuration is split by who is entitled to decide a value, not by whether it varies; a machine fact is derived and confirmed rather than typed, and a packaged tool carries no estate layer

**Date:** 2026-08-25 · **Status:** accepted 2026-08-28 · **Builds on:** 0012 (`scope` is a
config tag on the producer's root, never inferred from folder nesting), 0036
(the mesh stood down — the objection was the standing channel, not the
transfer), 0042 clause 2 (the wizard allowlist is a reviewed, committed edit —
the clause untracking silently narrowed), 0045 (a pin is verified read-only and
reported, never repaired), 0048 clause 4 (a field with one possible value
trains the eye past it), 0050 (a source declares its own staleness; one that
cannot be reached reads as unknown, never as fresh), 0051 (a work-estate corpus
is bounded by construction rather than by intention), 0052 (a convention lives
in the repo that owns the work; a skill cites it and never houses a rule), 0053
clause 2 (a check that splits per host reads a declaration rather than choosing
an axis; `authors` is declared per artefact in `machines.json` / `local.json`)
· **Source:** design thread, 2026-08-25; the work task force's
`2026-08-25_REPLY_harness_census`, §"The root path" and its objection to the
`authors` mechanism · **Convention:** `docs/CONVENTION_config.md`

**Context.** Three findings in one week, and the third is the one that changes
the shape.

**The consumer held the correction.**
`config/local.json` on this rig carries `D:/Work/Github/MCF` for host `10280L`.
That path has never existed on that machine; the work rig's own copy reads
`C:/Users/tim.smith/Github/MCF` and has for days. So this is not "one copy went
stale, probably the consumer's" — it is a consumer machine holding a correction
the **authoring** machine does not have, on the file whose entire job is to
carry machine truth outward. The file is untracked on both sides, so no diff on
either machine could ever have shown it. It was found by two people putting two
documents side by side, which is not a mechanism.

**The transport destroys machine-written state.** The survey behind
`CONVENTION_config.md` §1 found that `config/local.json` is written at runtime
by `governor.set_profile` and `curator_control.set_curator_model` — both
careful read-modify-writes — while the file's own comment instructs
`scp config/local.json <host>:…`. A governor profile learned on the knight and
a curator model chosen on the work rig are destroyed by the next ship, silently,
on both ends. `curator_control`'s docstring says *"this never writes anything
that travels"*; the file travels, just not by git.

**And a tool left the estate and worked.** On 2026-08-24 `Claude_Migration` —
built substantially out of this repo — was run by a **second operator** on a
machine this estate has never configured, and succeeded first time. It has no
per-machine config file. It enumerates `%LOCALAPPDATA%\Packages`, shows the
human what it found, and takes an override. Its `vendor/l5gntools/config.py` is
a stub whose `machine()` raises if called, so it shipped no host list, no paths
and no project names — by construction.

That is the same value this repo asks a human to look up on one machine and
type into a file describing a different machine. Two tools, one estate, opposite
architectures, and the one that has never been able to assume is the one that
works on a stranger's laptop.

None of the above is carelessness. Each is what happens when four independent
questions — *does it vary*, *who decides*, *may it be published*, *how does it
arrive* — are answered by a single tracked-versus-untracked binary.

**Decision.**

1. **Configuration is split by authority, into five layers**: tool policy
   (the code decides), estate policy (the estate's author decides), machine
   facts (only the machine can know), operator facts (the person decides), and
   estate corpus, which is not configuration at all and is ruled on separately
   (0055, 0056). *Does the value vary per machine* is not the split; **who is
   entitled to decide it** is. `role` and `cowork_transcripts_home` both vary
   per machine and belong to different layers.
2. **A machine fact is derived, reported, confirmed — not typed.** Code
   enumerates what it can observe about the machine it is running on, reports
   what it found *including nothing*, and proceeds on what a human confirmed. A
   configured value is the **override** for when derivation fails, and it is
   permitted only where derivation is impossible or has failed.
3. **One precedence ladder, everywhere, for every value**: tool policy <
   estate policy < operator file < machine file < environment. **An environment
   variable is a debugging override only** — never where a value lives — and
   any value resolved from one is reported as such.
4. **A value is resolved once, at the edge, and passed inward as an argument.**
   No module resolves configuration in the middle of its own work. A call site
   that resolves for itself invents its own order, which is how four ladders
   came to exist for one class of value with nothing able to force them to
   agree.
5. **No layer travels by whole-file overwrite.** A file one machine writes at
   runtime and another overwrites wholesale cannot keep anything, and loses it
   silently at both ends.
6. **`authors` is estate policy and lives in the tracked file only.** This
   resolves the ambiguity 0053 clause 2 left open by naming both files. An
   untracked declaration of authorship makes *"no host declares this artefact"*
   and *"the declaration has not been shipped here yet"* the same input with two
   meanings — the first is a config gap, the second is a stale copy, and 0053
   clause 2 requires the check to read a declaration rather than choose. A
   declaration that can be un-shipped is not a declaration.
7. **A tool packaged out of this repo carries no estate and no operator
   layer**, and any estate-shaped import it retains is stubbed to **raise**, not
   defaulted and not silently empty. A quiet default on a stranger's machine
   produces a confident answer about an estate that is not there.
8. **Malformed or unrecognised configuration fails loudly.** A typo in a config
   file may not be indistinguishable from an absent one.

**Consequences.**

**Clause 4 is expensive and touches working code.** It reaches `vault_reader`,
`backup`, `census`, `scrape` and `db` — and `db.py` cannot be brought to it
without changing module-level constants that every importer already binds to.
That is a real refactor with no user-visible feature at the end of it, and it
is the clause most likely to be deferred indefinitely while the other seven
land.

**Clause 2 trades a known failure for an unknown one.** A typed path is wrong
when the machine changes and right forever otherwise. A derived path is right
across machines and breaks when a vendor changes a store layout — and it breaks
on every machine at once rather than on one. The trade is taken because the
current failure mode is silent and the new one is loud, not because derivation
is safer.

**Clause 8 will make a previously-working machine stop working**, at least
once, on a key someone misspelled years ago that has been quietly ignored ever
since. That is the point of the clause and it will still be annoying on the day.

**The operator layer has one occupant and may be over-fitted to a single
event.** One person ran one tool once. Building a whole layer on that is a bet
that it recurs; if it does not, clause 1 has five layers doing four layers'
work, and the honest remedy then is to collapse it rather than to defend it.

**This does not fix cross-rig drift**, and 0050 already said it would not. What
changes is that drift becomes **locatable** — two files that can be compared by
a command — rather than discoverable only by two people reading documents to
each other. That is a smaller win than it sounds, and worth naming as smaller.

**More files, and a second place to look.** Four hosts split across two files
each is eight where there was one. The compensation is that no file describes a
machine its author cannot see.

**What would show this wrong.** Three counts, all cheap.

**Count the machine facts still typed, three months after the split.** Today
every path in the machine layer is hand-entered. If the machine file still
holds hand-typed store roots then, clause 2 was aspiration rather than a rule,
and the honest reading is that derivation costs more than it saves — in which
case replace it with a *currency stamp* on the typed value rather than
restating clause 2 more firmly.

**Count divergences found by a tool versus by a person.** Today the score is
0-1: the only config divergence this estate has ever detected was found by two
people comparing documents. If, after origin reporting exists, the next
divergence is still found by a human, the reporting is not being run and
building more of it will not help.

**Count the layers that ever hold more than one occupant.** If in six months
the operator layer still has one person and the tool-policy layer holds nothing
that estate policy could not have held, clause 1 over-fitted and should be
collapsed to three layers plus corpus.
---

## 0055 — The project registry is curated corpus, not configuration: its rules live in the repo rather than inside the artefact, and any judgement the generator can undo is a key rather than a sentence

**Date:** 2026-08-25 · **Status:** accepted 2026-08-28 · **Builds on:** 0010
(`project_link` is estate- and account-agnostic by design), 0011 (link values
predating the registry are reset, not trusted), 0012 (the registry is three
tiers — program, project, repo — and `scope` is a config tag on the producer's
root), 0040 clause 4 (a curated artefact that cannot be diffed carries a
committed fingerprint instead), 0045 (a pin is reported, never repaired), 0051
(containment by construction), 0052 (a convention lives in the repo; a skill
cites it), 0054 (configuration is split by authority, and corpus is not
configuration) · **Source:** design thread, 2026-08-25; the survey recorded in
`docs/CONVENTION_project_registry.md` §1 · **Convention:**
`docs/CONVENTION_project_registry.md`

**Context.** 0054 clause 1 puts corpus outside configuration and defers the
rest. This entry is the rest, for the registry.

**The convention was inside the artefact it governs.** `config/project_registry.json`
carries roughly a page of rules in four comment keys — `_comment`, `_schema`,
`_id_scheme`, `_low_signal_body`. They are good rules: what the three tiers
mean, the evidence that settled them, why the id scheme won, what
`low_signal_body` does and the measurement behind it, how the generator merges,
how to ship the file and how to confirm the destination. All of it lives in a
**gitignored** file. A machine that lacks the registry also lacks the rules for
building one, and the rules cannot be diffed, reviewed or cited apart from the
data they describe.

That is 0052's finding with a file in the role of the person, and 0052's remedy
applies unchanged.

**Nothing verifies it.** 31 projects, 4 programs, 30 entries carrying curated
aliases — and zero auditors, no committed fingerprint, and no stamp recording
when it was authored or on which host. The neighbouring artefact of the same
class has all three (0040 clause 4), so the mechanism exists and was never
applied here.

**Two files share one name.** The curated seed at
`config/project_registry.json` and the generated registry `build_registry.py`
writes to relink's `REGISTRY_PATH` have different authors, different lifecycles
and different edit rules. They are also resolved by two independent code paths
under two different environment variables.

**Decision.**

1. **The registry is curated corpus.** It is authored from local knowledge that
   no scan can recover — the census clusters, the scrape title sheet, live
   queries, a person's judgement about what is one effort — and configuration's
   only role is to resolve **where it is found**.
2. **Its rules live in a convention document in the repo, and the artefact
   cites rather than carries them.** Where the two disagree the convention
   wins (0052 clause 2, applied to a file).
3. **The generator never removes or rewrites manual-provenance content, and a
   human never edits the generated registry.** One rule, both directions.
4. **Any human judgement the generator can undo is expressed as a key, not as a
   note.** `seed_suppress` is the worked example: a prose note explaining that
   an alias is a false friend does not stop the seeder re-deriving it every
   run; the key does. A judgement recorded only in prose is a judgement that
   will be silently reversed.
5. **Identity is the registry `id`, at every tier, in every consumer** — never a
   `canonical_name`, never a folder name. The id is what survives the renames
   this estate actually performs.
6. **Tier is decided by evidence, and the entry records the reasoning.** A repo
   is an incarnation of an existing project unless the evidence clusters say
   otherwise, and the entry carries a `note` saying which and why.
7. **The registry declares its currency.** It carries a pin recording origin,
   anchor, date and host, on the same reported-never-repaired footing as 0045,
   so a consumer copy older than the pin reads as **not current** rather than as
   fine (0050).
8. **Names never cross a boundary; counts, shape and schema may.** A redaction
   that leaves the ids intact leaves the join intact and is not a redaction.

**Consequences.**

**Clause 7 creates a red state on every consumer that has not been re-handed**,
which is exactly the condition 0053 moved outside the gate. So this clause buys
a signal and simultaneously commits us to keeping that signal out of
`verify.py` — and a report nobody is forced to read is a report that will not
be read. That tension is not resolved here.

**Clause 4 grows the schema, and prose will keep being written anyway** because
a sentence is faster than deciding what key it should have been. The likely
real outcome is a mixture, with the keys covering the cases someone was burned
by and notes covering the rest.

**Clause 2 costs the convenience that the rules travelled with the file.**
Today a machine handed the registry is handed its rules in the same act. After
this, the rules arrive by `git pull` and the data by hand, which is precisely
the split that produced 0053's whole problem for the conversation map. We are
choosing that asymmetry knowingly because the alternative is rules nobody can
read without the data.

**Moving the artefact out of `config/` breaks two resolvers and every path that
names it**, including one on the knight that must match `relink.REGISTRY_PATH`.
This entry does not schedule that move; it establishes that the artefact's
class is corpus, which is what makes the move correct when it happens.

**What would show this wrong.**

**Count judgements the generator reversed.** Every time a re-run re-derives an
alias a human had ruled out in prose, that is one. If the count is zero over
twenty generator runs, clause 4 is solving a problem that does not occur and
the schema growth is not earning its keep. If it is non-zero and the
corresponding keys were never added, the clause is not being followed and the
remedy is a report at generation time, not a firmer rule.

**Count registry divergences detected after clause 7's pin exists, against
re-hands performed.** If the registry is re-handed five times and the pin never
once reports a stale consumer, either nothing diverges — in which case clause 7
is machinery for an absent problem — or the pin is not being bumped, which
clause 4's own logic says will happen unless something enforces it.

**Check whether a cold reader can rebuild an entry from the note alone.** Nine
of 31 projects currently carry no `note`. If, a year from now, a person cannot
say why a repo was filed as an incarnation rather than a project, clause 6 was
recorded but not practised.
---

## 0056 — 0044 clause 4 is enforced by the pattern, not by an enumerated path; and a pin records when and where it was taken as well as what

**Date:** 2026-08-25 · **Status:** accepted 2026-08-28 · **Builds on:** 0040 clause 2 (maps
are per source, one file each) and clause 4 (a curated map is never committed;
a `<map>.sha256` fingerprint is committed beside it, because an untracked file
produces no diff), 0044 clause 4 (the ratified map is resolved from the declared
estate name, never a fixed filename, and **each estate's map carries its own
committed fingerprint**), 0045 (one pin: origin, anchor, hash — verified
read-only, reported never repaired), 0046 (recency resolution; a superseding row
says so), 0048 clause 4 (a check that is always red trains the eye past it),
0053 clause 5 (a remedy must be safe wherever it can fire; `run.py pin bump`
refuses where the artefact is not authored), 0054 (corpus is not configuration),
0055 (the neighbouring artefact of the same class) · **Source:** design thread,
2026-08-25; the survey recorded in `docs/CONVENTION_conversation_map.md` §1
· **Convention:** `docs/CONVENTION_conversation_map.md`

**Context.** This entry is narrow on purpose. Most of the map's discipline is
already ruled and already built — append-only writes, a mandatory
`[provenance:…]` tag the writer refuses to append a row without, per-row actions
with nowhere to put a bulk-accept, recency resolution with revocation, a
committed fingerprint and an auditor that checks it. Ruling on that again would
be a decision about work already done.

**What forced this is a conformance finding, not a new rule.** 0044 clause 4 is
accepted and says plainly that *"each estate's map carries its own committed
fingerprint under 0040 clause 4 and 0045."* Two maps exist.
`personal_conversation_map.tsv` has **no `.sha256`**, and
`auditor_conversation_map_pin` names `mcf_conversation_map.tsv` by a hardcoded
constant. So an accepted clause has been unimplemented for one of its two
instances, and the check that exists to enforce it cannot see the instance that
violates it.

The `.gitignore` half generalised correctly — `/config/*conversation_map.tsv` is
the pattern 0040 clause 4 wrote *"so the next source's map inherits the rule
rather than having to remember it"*. The ratification half did not, because it
was written against a path. **That difference is the transferable finding, and
it is what this entry rules on**: a rule expressed as a pattern and enforced by
an enumeration will silently stop covering its own subject the moment a second
instance appears, and nothing will report the gap, because the enforcing code
has no opinion about instances it was not told to look at.

**Second, the pin records a third of what clause 4 undertook to keep.**
`config/mcf_conversation_map.tsv.sha256` holds a hash line only.
`l5gntools/pin.py` already supports and verifies a metadata line carrying
`origin`, `anchor`, `date` and `host`, and `verify_pin` implements
`anchor-unresolvable` as a distinct violation state. Clause 4's undertaking was
that the repo would record *"that a map was ratified, when, and against what
content"*. The hash carries **what**. The **when** and the **where** are
supported by the mechanism and absent from the artefact.

**Third, and genuinely open.** 0040 clause 2 makes maps per **source**; 0044
clause 4 resolves the filename from the declared **estate** and reconciles the
two by calling the estate map *"one instance of the pattern 0040 clause 2
declared"*. That reconciliation holds precisely while each estate has one
source. Neither entry says what happens when one has two, and after that point
the answer costs a migration of ratified rows.

**Decision.**

1. **A check enforcing a pattern rule is driven by the pattern.** Where a
   ruling's subject is defined by a pattern — `/config/*conversation_map.tsv`
   here — the auditor enumerates matches at run time and reports on each. An
   enumerated path is permitted only where the ruling's subject is genuinely a
   single named artefact, and a check that narrows a pattern to one instance
   states that it has done so in its own output.
2. **A map that exists without a pin recorded for it is a violation, not an
   absence.** This restates nothing new — 0044 clause 4 already requires it —
   and is written here only because clause 1's mechanism is what will make it
   true. `artefact-absent` remains clean; *artefact present, pin absent* does
   not.
3. **A pin carries its metadata line**: origin, anchor where one exists, date,
   and the host that took it. A hash-only pin is incomplete under 0040 clause 4
   and is reported as incomplete rather than accepted as passing.
4. **A consumer copy older than the current pin stays outside the gate**
   (0053), and clause 3 is what makes that state legible: the pin names the
   authoring host and the date, so the remedy — be re-handed a copy from that
   host — is readable from the failure alone rather than requiring someone to
   know the estate's shape.
5. **Source is the axis; estate is how a filename is currently derived.** Where
   an estate acquires a second source, the answer is a further file resolved by
   *(estate, source)* — never a second column in an existing map, and never one
   map spanning two sources. 0039 clause 1 and 0044 clause 4 continue to govern
   how a name is resolved; they do not govern what a map contains.

**Consequences.**

**Clauses 1 and 2 turn a currently-green tree red.** `personal_conversation_map.tsv`
exists and has no pin, so the day this lands `verify.py` fails on this rig until
a pin is written. That is the ruling working, and it will still arrive at
whatever moment is least convenient. It also means this entry cannot be landed
and left — it lands with work attached.

**Clause 3 makes the existing MCF pin incomplete**, and under 0053 clause 5 only
the authoring host may re-bump it. So the remedy cannot be applied wherever the
problem is noticed; it has to be carried back to the rig that authors the map.
That is the correct constraint producing an inconvenient workflow, which is what
0053 clause 5 costs in general.

**Clause 1 is the expensive one, and its cost is not in this artefact.** Written
generally, it implicates every other check in the estate that names a path where
its ruling named a class — and this entry does not audit for those, so it
creates an unknown quantity of latent non-conformance and no list of it. Naming
the rule without producing the list is half the work, and the half that is
missing is the half that would tell us how big the other half is.

**Clause 5 may cost nothing ever.** If no estate acquires a second source, it is
a sentence written for a case that never came. It is written now because the
alternative is deciding it while holding 37 ratified rows that would have to
move.

**What would show this wrong.**

**Count the checks in `verify.py` whose ruling names a pattern and whose code
names a path.** Today at least one, and that one was found by writing a
convention rather than by any check. If a deliberate sweep finds it is the only
one, clause 1 is a general rule earning its keep on a single instance, and
should be narrowed to this artefact rather than left standing as doctrine. If
the sweep finds several, clause 1 was under-stated and wants an auditor of its
own.

**Count pins whose metadata line is absent, after clause 3 lands.** Today one of
one. If it is still one of one in a month, `run.py pin bump` is not writing the
line and the defect is in the writer, not in the ruling — restating clause 3
will achieve nothing.

**Count red `verify.py` runs on a consumer caused by the in-between state** — a
copy older than the pin, no defect present. 0053 moved that outside the gate. If
generalising the auditor under clause 1 causes that state to start firing inside
the gate, then clause 1 was applied before 0053's split was finished, and the
correct reading is that clause 1 should have waited rather than that 0053 was
wrong.
---

## 0057 — A skill is estate IP with one source of truth and branches rather than copies; it declares the kind of authority it needs, resolves it at run time, and stops rather than working from its own text

**Date:** 2026-08-26 · **Status:** accepted 2026-08-28 · **Builds on:** 0042 clause 1
(declaration belongs to the repo that owns the work), 0043 (a ruling from
another repo is cited with its repo, at every mention), 0045 (a pinned copy is
verified read-only and reported, never repaired), 0050 (a source declares its
own staleness; one that cannot be reached reads as unknown, never as fresh),
0051 (containment by construction rather than by intention), 0052 clauses 2, 3
and 5 (the convention lives in the repo that owns the work; no rule may have a
skill as its only home; a skill with no convention says so and names the debt),
0054 clause 7 (*proposed* — a packaged tool carries no estate layer and stubs
its estate-shaped imports to raise) · **Source:** design thread, 2026-08-26,
and the operator's statement of ownership; the work task force's
`2026-08-26_NOTE_ecosystem_and_gates` §6 and `CATALOGUE_skills_2026-08-26.md`

**Context.** 0052 predicted this and named the falsifier that would show it:
*"count the rules whose only home is a skill."* The count came back from the
other side of the wall, and it is not zero.

**The measurement.** `CATALOGUE_skills_2026-08-26.md` recorded seven skills
configured on the work rig: three vendored into that program's repo, **one
byte-identical to the copy that actually loads**. The two vendored copies that
differed were both adaptations — one adopted at program level and pointed at
that repo's convention, one revised after its first walk — and **neither
adapted text was ever the one in the loop while work was done.** The estate was
running the unadapted skills while holding better ones it never loaded.

**Three of five shared skills name an estate in their own prose.**
`commit-scribe` says *"for L5GN-Tools"*, `docs-archivist` says *"in
L5GN-Tools"* and sends its reader to `docs/README.md` §3 six times — a file
absent from the repo it was loaded in. `consultant-docs` points at
`docs/Consultants/`, which `wfa-0025` clause 6 has since **retired**. And
`round-closer` states, as a general anti-pattern, *"no MCF repo has a gate"* —
which is false here, where `.githooks/pre-commit` runs `verify.py`. The
catalogue names the sharpest version of this: **a pointer that half-resolves is
worse than one that fails**, because the reader follows it and lands somewhere
plausible.

**The metric in use could not have caught any of it.** Compared byte for byte,
all five shared skills differ, and every vendored copy is *longer* than the
configured one — which is exactly what the catalogue observed. Normalised for
line endings, **all five are byte-identical, zero changed lines.** The whole
difference is CRLF against LF. A drift check across a Windows working tree and
a synced store reports every file as changed, on every run, forever; the same
artefact produced a phantom 757-line rewrite in `Work_Bridge` on the same day.

**And what forces a ruling now rather than a note.** The operator has settled
the ownership question the work rig put: **the skills are his IP, `L5GN-Tools`
is the source of truth for the published ones, and a task force may tailor its
own.** That answer only works if tailoring produces something diffable.

**This entry's first draft assumed it did not, and was wrong.** It was written
believing the shared skills lived in a plugin directory outside every
repository, tracked by nothing — the third instance of a class that already
included the conversation map and `config/local.json`. `git ls-files
.claude/skills/` says otherwise: all five are tracked, and have been. The
source-of-truth problem clause 1 was drafted to solve did not exist for them.
What the class does still describe is the **account store** the skills sync
into, and the work rig's vendored copies, neither of which any tool compares.

**Decision.**

1. **A skill is estate IP with one source of truth, and that source is the
   repo's own load path.** `L5GN-Tools` publishes every skill this estate
   authors from `.claude/skills/`, which is tracked and is also where Claude
   Code loads project skills from. **That identity is the point**: what is
   published is what runs, so there is no gap for a publish-versus-load
   divergence to live in. The account or plugin store a skill is synced into is
   a **deployment**, never the source, and a change made only there has not
   happened as far as the estate is concerned. **A second tracked skills
   directory is a defect, not a publication surface.**
2. **A task force branches; it never copies.** A tailored variant is a git
   branch of the published skill, offered back as a merge. A copy outside git
   is not a variant — it is an untracked divergence, and it is what this entry
   exists to stop. 0052's consequences said drift would remain and only become
   *locatable*; a branch is what locatable means.
3. **A skill declares the kind of authority it needs, never where it lives.**
   `CONVENTION_commits.md`, not a path, and never an estate name in its prose.
4. **Authority is resolved at run time, most-specific first**: the repo the
   skill is running in, then the estate's source-of-truth repo, then stop.
5. **A skill that cannot read its authority stops.** It does not fall back to
   its own text, to memory of a previous thread, or to a reconstruction.
   `orientation` is the worked example and states the rule already: *"If the
   file cannot be read, stop and say so."* This clause promotes it from one
   skill to every skill.
6. **A skill states no estate-specific fact.** How many repos have a gate,
   which folder holds a class, what a particular tree contains — all belong in
   a convention. A skill that resolves to the wrong facts is worse than one
   that resolves to nothing, because nothing fails loudly.
7. **A convention adopted from another estate names the adoption in its own
   header** — origin repo, origin file, date. The work task force's census
   found that *method does not cite*, and that a convention adopted whole
   leaves a fainter trace than a ruling cited. This is the correction, and it
   costs one line.
8. **A drift check over hand-carried text normalises line endings before
   comparing.** A raw byte or hash comparison across a Windows working tree and
   a synced store is not evidence of change.

**Consequences.**

**Clause 5 will stop work, and the first time will be soon.**
`consultant-docs` refuses immediately — the class it points at is retired on
one rig and absent on the other. `brief-scribe` and `decision-scribe` have no
convention on this rig until Thread E lands. So this entry creates a dependency
it does not discharge: **three of five skills are inoperative under clause 5 on
the day it binds**, and that is correct behaviour rather than a bug.

**Clause 2's cost is smaller than this entry first claimed.** The five shared
skills are already tracked at `.claude/skills/`, so editing where they run *is*
editing in git, and the round trip this clause was expected to impose does not
exist for them. What remains is the discipline of branching rather than editing
on top, and of offering the branch back — a habit rather than a mechanism, and
the falsifier's second count is how we will know whether it held.

**Clauses 3 and 4 make every skill longer and slower to write**, and add a
resolution step to a thing whose whole appeal is that it starts immediately.

**Clause 8 is the one that will look like pedantry until it isn't.** It is
invisible today because no check exists; the moment one does, it is the
difference between a useful reader and one that is red on every file forever —
which is 0048 clause 4's failure arriving through a back door.

**This does not fix drift**, and 0052 already said it would not. Two rigs will
still diverge. What changes is only that a divergence is a branch someone can
diff instead of two behaviours someone can only compare by watching them. That
is a smaller win than it sounds and is worth naming as smaller, again.

**What would show this wrong.** Three counts, all cheap, all runnable today.

**Count the skills whose declared authority resolves to nothing on the rig they
run on.** Today it is four: `consultant-docs` (retired class),
`docs-archivist` on the work rig (`docs/README.md` §3 absent there), and
`brief-scribe` and `decision-scribe` here. Under this entry the count should
trend to zero. If it is level in three months, resolution was a rule nobody
implemented and the honest reading is that clauses 3 and 4 cost more than
naming a path does — in which case replace them with a *currency stamp* on the
named path rather than restating them more firmly.

**Count branches offered back as merges, against edits made outside git.** If
after three months no branch has been offered and skills have nonetheless
changed on both rigs, clause 2 is aspiration and the plugin store is the real
source of truth whatever this entry says.

**Count the times a skill stopped rather than proceeding on its own text.**
Zero is ambiguous and must be read against the first count: zero stops with
zero unresolvable authorities means the estate is conformant; zero stops with
four unresolvable authorities means clause 5 is not implemented and the skills
are still working from memory.

---

## 0058 — A link records the mechanism that produced it, as a closed value refused at write and on a different axis from confidence; a mechanism that cannot answer abstains, and the abstention is counted

**Date:** 2026-08-28 · **Status:** accepted 2026-09-02 · **Builds on:** 0038 (conversation,
session and thread are three distinct things; clause 3 — the `threads` table is a
*storage* entity, not a source entity), 0040 clause 1 (where a source carries a
stable native conversation id, a curated map keyed on it is the join of record,
and **fuzzy or derived linking is not used for that source**), clause 2 (maps are
per source and carry per-row provenance — *how each row was arrived at,
machine-matched or human-mapped, never overwritten by a re-run*) and clause 3
(Chronicler consumes the map at `project_confidence: 'manual'`), 0046 (recency
resolution through one shared resolver; the `[provenance:…]` tag was chosen over
a status column deliberately, because a column would have needed a migration),
0048 clause 4 (a check that cannot fail trains the eye past it), 0050 (a source
declares its own staleness; a source that cannot be reached reads as **unknown**,
never as fresh) · **Source:** design thread, 2026-08-27/28, and the measurement
in `docs/investigation/2026-08-27_intent-coverage-remeasure_claude_2-response.md`
§6b, §10a and §10d-iii · **Brief:** `COWORK_BRIEF_conversation_grain.md` ·
**Convention:** `docs/CONVENTION_conversation_map.md`

**Context.**

Three mechanisms were measured against the same corpus on 2026-08-27/28, and
they do not fail alike.

- **The Cowork sidecar.** `userSelectedFolders`, compared against a
  hand-curated sheet the operator assigned from what each conversation was
  *about* rather than from the Cowork UI, so the two are independent. Of 49
  conversations present in both: **35 agree, 0 disagree, 14 carry an empty
  array.** The misses are empty, not wrong.
- **Title plus first user message**, on the 39-conversation Claude export: **16
  resolve to one project, 4 to more than one, 19 to none.** The shape is
  instructive — short openers are silent but never wrong; long openers are
  usually a pasted document and go ambiguous.
- **`relink`'s alias scoring.** §10d-iii recorded threads scoring
  `adjusted = 1.000` for `universal-content-pipeline` on **nine** compounding
  body aliases, because the thread pasted a project list. They were withheld by
  the ambiguity guard — *a tie, not a rule that understood why they were wrong.*

**The vault records how confident each link is and not how it was reached.**
`project_confidence` ∈ {`evidence`, `exact`, `fuzzy`, `manual`, `none`} is one
axis doing two jobs, and the three mechanisms above are indistinguishable once
written.

**What forced this is a conformance finding that the schema made invisible.**
0040 clause 1 is accepted and says that where a source carries a stable native
conversation id, the curated map is the join of record and *"fuzzy or derived
linking is not used for that source."* The Cowork store carries exactly such an
id — the sidecar's `sessionId` field — which is what 0040's own Context
established. Yet §6b records that the refresh of 2026-08-27 gave
`claude-local-personal` **11 evidence links, every one of them a `relink`
auto-link** on a title-plus-body alias pair at 0.92–0.96, taking that corpus from
0.0% to 15.5%.

So derived linking ran against a source a ruling excludes it for, produced most
of that day's coverage rise, and **nothing reported it** — because the column
that would have shown it records confidence rather than mechanism. Eleven of the
35 substantive evidence links the estate currently publishes as its headline
figure were produced by a mechanism an accepted clause does not permit for that
source. That is not a scoring defect; the scorer behaved as specified. It is the
record being unable to describe itself well enough for its own rules to be
checkable.

**And the tag that was supposed to carry this is free text.** 0040 clause 2
requires per-row provenance; 0046 implemented it as a mandatory `[provenance:…]`
tag at the head of `notes` which `curator_ratify` refuses to append a row
without. The refusal covers the tag's *presence*. Its *payload* is unconstrained
— today `machine-matched:pass-1` — so a second mechanism can write a third
spelling and every consumer will accept it.

**Decision.**

1. **Every link records the mechanism that produced it, from a closed
   vocabulary, and a write outside that vocabulary is refused.** Not warned, not
   accepted and documented against. The vocabulary is declared in
   `CONVENTION_conversation_map.md`; the shared parser reads it from there and
   does not carry a second copy. Adding a value is an amendment to that
   convention, not a call made while writing a row.

2. **Mechanism and confidence are different axes and are recorded separately.**
   `project_confidence` continues to mean *how sure*; the mechanism field means
   *how derived*. Neither is inferred from the other. A curated-map row is
   `manual` under 0040 clause 3 whatever mechanism proposed it, and the
   mechanism field is what says whether a human, a sidecar or a text match
   proposed it.

3. **A mechanism that cannot answer abstains, and produces no row.** Not a
   low-confidence row, not a guess carried forward for a human to knock down.
   The Cowork sidecar's 14 empty `userSelectedFolders` are the worked example.
   This is 0050's rule applied one level down: a source that cannot be reached
   reads as unknown; **a mechanism that cannot decide reads as silent.**

4. **Abstentions are counted and reported wherever coverage is reported.** An
   abstention that is invisible is indistinguishable from a mechanism that was
   never run, which is the *confident zero* this estate has now met in five
   separate costumes. A coverage figure published without its abstention count
   is incomplete.

5. **Where a mechanism does not populate a field, the field is present and
   explicitly null rather than omitted**, so that *"this mechanism did not
   derive that"* is distinguishable from *"this key does not exist"* by reading
   one row. A field that is structurally always null for every mechanism is a
   defect in the record shape and is removed rather than carried.

6. **A link whose mechanism is excluded for its source by 0040 clause 1 is
   reported as a violation.** The check is driven by the source's declared
   possession of a native conversation id, not by an enumerated list of sources
   — 0056 clause 1's shape, applied here. **This entry does not decide what
   happens to the eleven links already in the vault**; it decides that they are
   visible. Removing them, or amending 0040 clause 1 to permit derived linking
   as corroboration where a map is sparse, is a separate ruling and wants the
   count in front of it.

**Consequences.**

**Clause 6 turns a green tree red, and it does so against the estate's own
published figure.** Eleven of the 35 substantive evidence links violate 0040
clause 1 for their source. The day this lands, that is reportable, and the
INTENT §2 figure of 10.42% is thereafter a number with a footnote — because the
honest reading is either 24/336 or 35/336 depending on a ruling nobody has made
yet. **This entry makes the estate's headline worse and does not fix it.** That
is the ruling working; it is also the least comfortable thing in this log.

**Clause 2 costs a vault schema change**, which
`COWORK_BRIEF_conversation_grain.md` puts explicitly out of scope. So clause 2
cannot be implemented by that round and needs one of its own. 0046 declined a
status column on exactly this reasoning — *"a column would have needed a
migration, a notes tag does not"* — and this entry accepts the migration it
declined, for a different field and with a different justification: a tag in a
`notes` string is fine for a curated map that one writer appends to, and is not
fine for a column every consumer of the vault must join on.

**Clause 1 will refuse something legitimate at an inconvenient moment.** A
closed vocabulary means the first genuinely new mechanism is blocked until the
convention is amended, mid-round, by an operator who wanted to be doing
something else. That friction is the point and it will not feel like it.

**Clause 3 costs coverage, permanently and on purpose.** Fourteen of 49 measured
conversations produce nothing rather than a guess. A design that guessed would
show a higher number today and would be wrong an unknown fraction of the time,
which INTENT §5 rates as the worst thing this system can produce. The trade is
taken knowingly; it is still a trade.

**Clause 4 makes every future coverage figure longer to state**, and a figure
that needs two numbers is a figure that gets quoted as one. This is a real risk
and the mitigation is only that the report format demands both.

**What would show this wrong.**

**Count the values in the closed vocabulary six months after this lands.** If it
is still the four it started with — `sidecar`, `first-message`, `cwd`, `human` —
then closure was never under pressure, bought nothing, and a free-text tag with
an auditor would have done the same work for none of clause 1's friction. If it
has grown past eight, the field is being used as a general-purpose label rather
than a mechanism, and it wants splitting before the vocabulary becomes a
taxonomy nobody can hold in their head.

**Count the links clause 6's check reports, in its first run and three months
later.** Today the expected answer is eleven. If it reports eleven and then never
fires again, clause 6 was a one-off cleanup wearing a rule's clothes and should
have been a task in a brief. If it keeps firing, the exclusion in 0040 clause 1
is being routed around by ordinary work, and the entry to write is the one that
amends 0040 rather than the one that keeps reporting it.

**Count abstentions that a human later resolves to the answer the abstaining
mechanism would have produced.** This is clause 3's falsifier and it is the
sharpest one here. Take the 14 empty-`userSelectedFolders` conversations, let the
operator ratify them by hand, and compare each against what a guessing mechanism
would have said. **If most abstentions would have been right, clause 3 is buying
a safety that was not needed and is paying real coverage for it** — and the
correct ruling is to let a mechanism propose at a low confidence rather than stay
silent. If the guesses would have been wrong or split, clause 3 is vindicated and
the 14 are the cost of not being wrong.

**Count how often two mechanisms disagree about the same conversation once both
are recorded.** The design assumes the sidecar is a join and the text match is a
signal. If they disagree at any material rate, one of them is not what this entry
says it is, and clause 2's separate axis is what makes that measurable at all —
which is the argument for clause 2 surviving even if everything else here falls.

---

## 0059 — 0048 clause 2 is amended: a card's completeness is measured and shown rather than used to refuse it, and "not enough to decide yet" becomes a ruling with a named thing to fetch

**Date:** 2026-08-28 · **Status:** accepted 2026-09-02 · **Amends:** 0048 clause 2 (the
fixed card anatomy and its refusal to raise) · **Builds on:** 0048 clauses 1, 3,
4 and 5 (all four stand unamended — the operator confirmed each fits and
justifies), 0031 (a non-gating surface reports findings, never a verdict), 0037
clause 4 (no estimate where no measurement exists), 0045 (report, never repair),
0050 (a source that cannot be reached reads as unknown, never as fresh) ·
**Source:** `docs/UAT_quartermaster_frame.md` Q2, walked 2026-08-28 ·
**Report:** `docs/UAT_quartermaster_frame_results.md`

> **Drafted, not written by the operator.** The wording below is
> `decision-scribe`'s rendering of an answer given in conversation. **The
> operator's editing pass is the intended next step**, and the reading in
> clause 1 in particular is an inference he has not yet confirmed — it is
> stated as an inference so that correcting it is a read, not an
> archaeology. **Number 0059 and not 0058:** `data/decisions_draft/0058_proposed.md`
> is drafted and unappended and holds that number.

**Context.**

0048 clause 2 fixed the card's anatomy at six fields — question, trigger,
evidence with provenance, options with costs where measured, default, expiry —
and gave it teeth: *"A card missing any field is not raised — an unassembled card
spends the attention it was built to save."*

Q2 of the Quartermaster frame's walk-sheet asked the operator to lay a real
decision against those six fields and say whether it would have fitted. The
answer, in his words:

> what I'm leaning towards is something that helps validate if enough of a
> complete picture is there to make a decision or more info required - that in
> itself can be a decision
>
> so I think points 1, 3, 4, 5 fit and justify but for point 2 I think we need a
> more flexible definition.

And the reason, which is the finding rather than the verdict:

> it comes down to what is a decision - and the broadness of that scope is
> making me resistant to a fixed schema

**The evidence he was ruling against was measured, not recalled.** The two
question blocks in `docs/investigation/2026-08-17_quartermaster_fable_1-prompt.md`
— the exchange that produced 0048 itself — carry, across seven decisions:
question 7/7; a trigger 0/7 (every context sentence is a state claim, not a
reason it was necessary *now*); evidence 7/7 as a single clause with **0/7**
citing a file, line or measurement; cost on any option **0/7**; default **0/7**;
expiry **0/7**. **Three of six fields, in the session that proposed six.**

That is not an argument that the fields are wrong. It is evidence that a rule
refusing to raise a card missing any of them would have refused every card in the
exchange that invented it.

**And there is a hole the refusal was hiding.** The Desk's ruling options today
are rebuild, snooze and dismiss. **There is no ruling that means "not enough here
to decide — fetch X."** A card arriving incomplete has nowhere to go but a snooze
that records nothing about why, so the estate cannot distinguish *deferred* from
*unanswerable-as-presented* — which is the same shape as the deferral that named
the wrong blocker in `UAT_desk_stale_card_results.md` D9, one week earlier, in the
same subsystem.

**Decision.**

1. **0048 clause 2's field list stands; its refusal does not.** The six fields
   remain the shape of a complete card. What is struck is *"a card missing any
   field is not raised."* **This reading — that the operator's "more flexible
   definition" narrows the refusal and not the fields — is an inference from his
   acceptance of clauses 3 and 4, which both depend on `default` and `expiry`
   existing. If the intent was to loosen the field list itself, this clause is
   wrong and should be rewritten before ratification.**

2. **A card declares its own completeness, and the declaration is derived, never
   typed.** Each of the six fields is present, absent, or **not applicable to
   this card kind** — and a card renders which. A surface reports this; it does
   not grade the card or withhold it (0031).

3. **An incomplete card is raised, marked incomplete.** Refusing to raise it
   moves the attention cost from the operator to nobody and loses the fact that
   something wanted deciding. Raising it with its gaps named is the reporting
   posture 0045 takes everywhere else.

4. **`insufficient` is a ruling, and it carries what is missing.** A fourth
   ruling joins rebuild, snooze and dismiss: *not enough to decide — this is
   needed.* It records the named thing to fetch, and it is a decision in the
   log's own terms rather than a non-answer. **A card ruled `insufficient` with
   no named item is refused at write**, on 0058's principle that a mechanism
   which cannot answer abstains explicitly rather than silently.

5. **Completeness is not a threshold and never gates.** No count of fields
   authorises or blocks anything. There is no minimum, no score, and no
   automatic escalation on incompleteness — that would rebuild the refusal
   clause 1 strikes, with arithmetic instead of a rule.

**Consequences.**

**`desk.py` has hard-coded the anatomy once already**, and Q2's own wording
warns that this is the moment to change it — before a second surface copies it.
That cost is real: the module ships a fourth ruling kind and a completeness
derivation it does not have today.

**The Desk gets noisier, deliberately.** Cards that clause 2 would have silently
withheld now appear, marked incomplete. If the board fills with them, that is
information about the assembling machinery and not about the operator — but it
will be irritating before it is useful, and 0048's own Consequences already name
card flood as the Desk's failure mode rather than card famine.

**"What is a decision" is not settled by this entry, and the broadness the
operator named remains.** This amendment makes the schema survivable rather than
answering the question underneath it. That question is live and this entry
should not be read as having closed it.

**Two of 0048's clauses now point in slightly different directions.** Clause 3
says silence's consequence is stated on the card; an incomplete card's `default`
may itself be absent. Clause 4's *"every default reads `hold — nothing runs`"*
resolves it in practice for now, and that is a dependency on clause 4 remaining
true when the policy engine arrives.

**What would show this wrong.**

- **Count `insufficient` rulings after one month. If it is zero**, the option was
  a comfort rather than a gap being filled, and clause 4 should be struck —
  either every card really was complete enough, or the ruling is one nobody
  reaches for under pressure.
- **Count cards raised marked incomplete, and how many are ever ruled at all.**
  If incomplete cards are systematically ignored rather than ruled
  `insufficient`, clause 3 has produced noise, the refusal 0048 wrote was right,
  and this entry is the mistake.
- **Read the `insufficient` rulings' named items after a month.** If the same
  item is named three times, the assembling machinery has a fixable gap and did
  not notice — which is 0048 clause 5's promotion test arriving from the
  evidence side, and a stronger result than anything above.
- **Check whether any surface has begun refusing to raise on completeness.** If
  one has, clause 5 failed and the threshold came back through the code rather
  than through a ruling.

  ---

## 0060 — A rule declares the subject it binds, in a form something can enumerate; a rule that cannot is recorded as unenforceable rather than reported against a substituted subject, and a rule, its checker and its remedy are three artefacts that must agree

**Date:** 2026-08-31 · **Status:** accepted 2026-09-01 · **Builds on:** 0031 (a non-gating
surface reports findings, never a verdict), 0045 (a pin is one mechanism —
origin, anchor, hash — verified read-only, reported never repaired; clause 2's
report-never-repair is what keeps a conformance reader a reader), 0048 clause 4
(a check that cannot fail trains the eye past it), 0050 (a source that cannot be
reached reads as unknown, never as fresh — the posture this entry extends from
sources to subjects), 0052 clauses 2 and 3 (the convention lives in the repo
that owns the work and the skill cites it; **no rule may have a skill as its
only home**), 0053 clause 5 (a remedy printed by a check must be safe to run
wherever that check can fire), 0056 clause 1 (a check enforcing a pattern rule
is driven by the pattern, and a check that narrows a pattern to one instance
states that it has done so in its own output) · **Source:** design thread
2026-08-31, session 1 of the week's order; the five worked instances in
`docs/AGENDA_conformance_instances_2026-08-31.md`, each verified against the
tree or against a run · **Brief:** `COWORK_BRIEF_conformance_reader.md` ·
**Convention:** none yet — see clause 7

> **Drafted, not written by the operator.** The wording below is
> `decision-scribe`'s rendering of a position assembled from five instances the
> operator's own instruction promoted to the front of the week. **His editing
> pass is the intended next step.** Where a clause rests on an inference it says
> so, so that correcting it is a read rather than an archaeology.
>
> **Filed in `data/decisions_draft/`**, matching 0058 and 0059. `data/decision_drafts/`
> also exists and holds 0054-0057. **Two live draft directories is how a draft
> goes missing**, and this entry does not fix that — it is named here so the next
> reader does not have to rediscover it.

**Context.**

**What forced this is not a new idea. It is a count that moved.** On 2026-08-28
`AGENDA_running_order_2026-08-28.md` §6a recorded an aggregate — *"an accepted
rule with no reader, or a reader that structurally cannot see what its rule is
about"* — and left promoting it as an open call, on the ground that deciding it
was a restructure. Three days later: seven rulings accepted in one afternoon
(0051-0057), two more proposed (0058, 0059), and two conventions added on
2026-08-29 (`CONVENTION_project_process.md`, `CONVENTION_skills.md`), both
declared STUB, **neither enforced and neither carrying 0057 clause 7's adoption
header.** The estate is now at 59 rulings and 11 conventions, and the count of
rules without readers is growing faster than any card mechanism can raise
questions about them.

**Five instances were worked on 2026-08-31 and they are not one failure.** The
08-28 aggregate assumed a single shape. Worked out, they are five, and a ruling
addressing only the first would leave four live:

| | failure mode | instance | found by |
|---|---|---|---|
| 1 | two rules that cannot both hold, and no reader of the conflict | 0054 cl.6 required `authors` in a tracked file; `config/machines.json` declared itself *"TEMPLATE (committed, no real machine data)"* | reading |
| 2 | a reader whose subject is narrower than its rule's | `auditor_conversation_map_pin` bound to one hardcoded path while a second map sat unpinned beside it | reading |
| 3 | an invariant between components that must not know about each other | `db.resolve_registry_path` and `review/core.resolve_registry_path`, kept in step by a code comment | reading |
| 4 | a rule whose subject set is not enumerable at all | 0057 cl.7 binds conventions *"adopted from another estate"*, and nothing determines which those are | reading |
| 5 | a rule whose checker and whose remedy disagree | the auditor written that same morning demanded 0056 cl.3's metadata; `pin bump` short-circuited on hash equality and refused to write it | **running the gate** |

**Mode 4 is the one that did measurable harm, and it is not the missing-reader
shape at all.** A conformance figure — *"4 of 9 conventions carry an adoption
header"* — was computed by counting headers against **every** convention, when
clause 7 binds only conventions adopted from another estate. That is a different
denominator, not a rounder one. The figure travelled into
`AGENDA_design_gaps_2026-08-28.md` and `AGENDA_running_order_2026-08-28.md` and
was repeated unchallenged for four days, while the denominator itself went stale
(9 → 11) inside three. **A rule whose subject nobody can enumerate does not
produce silence; it produces a confident wrong number**, which is the failure
`INTENT.md` §5 refuses everywhere else, arriving through the estate's own
governance rather than through its data.

**Mode 5 was introduced by the session that catalogued modes 1-4**, in the act of
fixing mode 2, and survived until the operator ran `verify.py`. Four modes were
found by careful reading. **Only running found the reader with no remedy.** That
asymmetry is evidence about what a conformance sweep can and cannot discover
about itself, and it is why clause 5 below is not a documentation rule.

**Decision.**

1. **A rule declares the subject it binds, in a form something can enumerate.**
   Where the subject is a pattern, the rule states the pattern and any checker is
   driven by it (0056 clause 1, which this generalises from pattern rules to all
   rules). Where the subject is a fixed set of artefacts, the rule names them.
   Where the subject is *"every X"*, the rule names how X is decided and by
   reading what. A subject recoverable only from prose is not a declared subject.

2. **A rule whose subject cannot be enumerated is recorded as unenforceable, and
   that is a permitted outcome.** It is not a defect in the rule and does not
   make the rule void — it may still be read and followed. What is refused is
   the third state: a rule treated as enforced, checked against a subject
   somebody chose at the moment of counting. **`unknown` over the right subject
   beats a number over the wrong one** (0050, extended from sources to subjects).

3. **A conformance figure names the subject it was computed over, and a figure
   computed over a substituted subject is a defect rather than an approximation.**
   Any count of the form *"N of M"* published in this estate carries what M is
   and how M was derived. A figure whose M is not the rule's own subject is
   withdrawn, not adjusted.

4. **A rule declares its reader, or declares that it has none, and the set of
   rules with no reader is an artefact rather than an impression.** The list is
   generated, never hand-maintained, and its being long is information rather
   than an embarrassment to manage.

5. **A rule, its checker and its remedy are three artefacts, and something
   asserts the round trip.** Where a check names a remedy, something verifies
   that running that remedy satisfies that check. A checker demanding what no
   sanctioned writer produces is **strictly worse than an unenforced rule**: it
   converts a green gate into a permanently red one with a documented fix that
   does nothing. This extends 0053 clause 5, which required a remedy to be
   *safe* wherever it can fire; a remedy can be perfectly safe and inert, and
   inert passed that clause.

6. **Where a rule's subject spans two components that must not know about each
   other, the reader lives in the gate and not in either component.** A shared
   invariant expressed as a code comment in one of them is not a mechanism. The
   independence is preserved; the drift is not.

7. **A conformance reader is a reader.** It reports; it never repairs (0045
   clause 2), and it emits verdicts only where it is in the gate (0053 clause 1).
   Following 0052 clause 2, the rules above belong in a convention this repo
   owns — `CONVENTION_conformance.md`, which **does not exist**, and writing it
   is the first act of the brief rather than a debt this entry discharges by
   naming.

8. **This binds rules made from today. It does not retroactively invalidate
   anything.** Existing rulings and conventions acquire declared subjects when
   something next touches them, or when the clause-4 sweep reaches them.
   Backdating a subject onto an accepted entry would edit its body, which the log
   forbids; the subject is declared in the sweep's output, not in the entry.

**Consequences.**

**The clause-4 list will be long, and most of the estate will appear on it.**
Twelve auditors cover a handful of claim classes across 59 rulings and 11
conventions. The honest first output is closer to *"almost nothing is checked"*
than to a tidy gap list, and 0056's own Consequences already conceded *"an
unknown quantity of latent non-conformance and no list of it."* **Producing the
list makes the estate look worse than it did yesterday while being exactly as
conformant.** That is the trade and it is taken knowingly.

**Clause 3 costs the estate some of its rhetoric.** Several published figures —
the adoption-header count certainly, and plausibly others — do not survive it,
and withdrawal rather than adjustment means an agenda that cited one becomes
wrong rather than imprecise. This is the correct cost and it will be irritating
the first time it lands on a number somebody liked.

**Clause 1 slows drafting.** Every future ruling now owes a subject statement,
and for genuinely broad rules that statement is hard to write — which is the
point, because the difficulty is the rule discovering it may be unenforceable.
The risk is the mirror image: a `Subject:` field that becomes ceremony, filled
in with something plausible and never read. Clause 2 exists so that *"cannot be
enumerated"* is an available and non-shameful answer, because a rule with no
honest escape hatch produces dishonest declarations.

**Clause 5 will find more mode-5 defects, and each is a red gate.** Asserting
round trips on existing checks means discovering remedies that never worked. The
gate goes red for real reasons that were previously invisible, at whatever moment
is least convenient — the same shape 0056 predicted for itself and got right.

**Clause 8 leaves a long tail of undeclared rules for an indefinite period**,
and during it the estate holds two classes of rule that look identical in the
log. Nothing distinguishes them in `DECISIONS.md` itself; only the sweep's output
does. A reader who reads only the log will not know which is which, and that is a
real cost of refusing to edit accepted entries.

**What would show this wrong.**

- **Count the subjects.** After the next ten rulings, count how many declare a
  subject a reader could enumerate without reading prose. **Eight or more
  vindicates clause 1; four or fewer means the field is ceremony** and the
  declaration should be replaced by something that costs more to fake.
- **Watch the unenforceable count.** If clause 2 is being used honestly, some
  new rules will be recorded unenforceable. **Zero unenforceable rules after ten
  is not success — it is evidence the escape hatch is being avoided**, and every
  rule is being given a plausible subject instead of an accurate one.
- **Does the clause-4 list shrink?** Generate it, then generate it again in a
  month. **If the count of rules with no reader has not fallen, naming the gap
  does not drive closure** and this entry bought bookkeeping rather than
  conformance — in which case the 08-28 deferral was right and Cards C and D
  were the better week.
- **Run the round trips.** Assert clause 5 against every check that prints a
  remedy. **If mode 5 turns out to be unique to `pin bump`, clause 5 is a rule
  written from one instance** and should be demoted to a note on 0053.
- **The 0057 clause 7 test, specifically.** Try to give it an enumerable
  subject. **If "adopted from another estate" cannot be made enumerable even
  deliberately, then clause 2 is carrying more weight than clause 1** — most
  rules are unenforceable rather than merely unchecked — and this entry has
  mis-diagnosed the estate's problem as a tooling gap when it is a drafting one.
