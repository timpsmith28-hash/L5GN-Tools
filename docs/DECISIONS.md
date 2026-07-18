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