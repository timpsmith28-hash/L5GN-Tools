# Cowork brief — the toolkit is a harness, not a member: the Project Wizard learns tiers

> **Draft status:** written 2026-08-22, deliberately early and expected to sit.
> Its Task 1 is discovery against a corpus that only became available today,
> and every task after that is provisional on what that discovery finds. This
> brief exists now so the wizard's shape can be argued *before* the
> post-migration build threads open, not so it can be built this week.

**Origin:** design thread, 2026-08-22, following the Claude tenant migration
and the reframing it forced: **WizForge is a program**; WizForgeAnalytics and
`sf-data-service` are a project and a repo beneath it; **L5GN-Tools is not a
member of that program at all** — it is the harness the program runs on, and a
program in its own right whose output other programs consume.
**Precondition:** **0051** ratified — designing against the pre-migration
corpus means reading it, and the containment must exist before the reading
does. Also the pre-migration bundles unpacked and the submodule pointer
verified.
**Depends on — this repo's rulings:** **0042** (a consumer repo declares its
own runnable stages; the toolkit executes only what a committed allowlist
names and never widens what a repo can do), **0012** and **0020** (the
three-tier scheme — program > project > repo — and a cross-threading effort
earning program designation), **0050** (a source declares its own staleness as
a feed), **0025** / **0036** (loopback, single estate, no mesh), **0037**,
**0033**.
**Deliverable:** the wizard's flat `{repo_key: path}` model replaced by one
that knows tiers — **without** the reach of the allowlist growing by a single
repo. If this round ends with more repos reachable than it started with, it
has failed at its main job.

---

## The thing this round is actually for

The current model is one flat map: `config/project_wizard.allow.json` names
`{repo_key: absolute path}` per host, and `load_manifests` reads one manifest
per named root. It has no idea that two of those roots might belong to the
same program, or that one might live *inside* another.

The corpus now proves both cases exist. `sf-data-service` is a **git submodule
of WizForgeAnalytics**, and it already carries its own
`wizforge.manifest.json` (schema_version 1, one stage: `estate_refresh`) —
which makes it the first real MCF manifest in existence and the first repo
whose root is nested inside another allowlisted root.

So the wizard is about to be asked a question its model cannot express: *what
is this repo, to what does it belong, and what may the toolkit do for it?*

## The distinction the whole round turns on

`project_wizard.allow.json` currently conflates two different things, and the
rewire is mostly the act of separating them:

- **Membership** — which program and project a repo belongs to. This is
  *identity*, it is already three-tier, and it already has a home:
  `config/project_registry.json` (0012), with `tester_registry_tiers` proving
  the rollup works.
- **Reach** — which repos this host may read and execute stages in. This is
  *authority*, and 0042 clause 2 made it explicit, per-repo and fail-closed on
  purpose.

**"The toolkit is hardwired and available at the program layer" must mean
membership, never reach.** A program-tier grant that confers repo-tier reach —
name the program, get every repo under it — would replace an explicit
allowlist with an inherited one, and inheritance is exactly the property
0042's fail-closed design refuses. Widening would stop being "a reviewed,
committed edit" and start being a side effect of registering a project.

Stated plainly so the round can be judged against it: **the harness
relationship is declared once at the program tier; the reach stays enumerated
one repo at a time.** If those two ever merge, this brief was built wrong.

Read that way, the change is smaller and safer than it first sounds — and the
allowlist should end up *shorter*, not longer, because per-repo entries stop
carrying identity they were never the right place for.

## Task 1 ▸ discovery against the real pair — before any design

Read the unpacked corpus and write a findings note. Not from memory of how MCF
repos are structured; from these two.

- **What does each repo actually declare?** `sf-data-service` has a manifest;
  does WizForgeAnalytics? If it does not, is that because the superproject has
  nothing runnable, or because nobody wrote one yet? Those want different
  answers.
- **How should a submodule be addressed?** `sf-data-service` is reachable at
  two paths — as a repo in its own right, and as a directory inside
  WizForgeAnalytics. Does it get one `repo_key` or two? Today's model would
  give it two allowlist entries with no relationship between them, and
  `resolve_contained` would see a root nested inside a root.
- **What does the program layer actually need to know** that the project layer
  does not already say? Answer with something concrete the operator wanted and
  could not get, not with a diagram. If nothing concrete surfaces, this round
  shrinks to fixing the submodule case and the tier work is deferred.

  **A partial answer already exists**, from a review of the work-side program
  layer written at the migration (`HANDOVER_ADDENDUM_2026-08-22.md` §11, in the
  frozen corpus). It names five things a program layer must be able to rely on
  before it can address projects generically:

  1. a **data contract** — one call every project answers the same way;
  2. a **processing contract** — one call by which every project records what
     it did;
  3. **one pointer file per repo, in the same shape**, so it can be generated
     rather than written;
  4. **one canonical document per subject**, rather than each project holding
     its own copy of a shared one;
  5. a **scaffold conformant enough that a project can be addressed
     generically** — with non-conformance visible somewhere, or it is tolerated
     rather than decided.

  Treat that as a hypothesis to test against this repo's two, not as a
  requirements list to implement. The question Task 1 must still answer is
  which of the five the *wizard* needs, as opposed to which the program layer
  needs elsewhere — they are not the same set, and assuming they are is how
  this round grows into something it should not be.
- **What is the per-project "plugin" in practice?** The intent is that config
  declares what the toolkit does for a given project. The manifest already
  declares stages, and 0050 added feeds. Is the plugin a third thing, or is it
  those two under a name — and if it is a third thing, what does it hold that
  neither can?
- **Where does the estate report fit?** The snapshot includes one taken after
  the git work closed. What did it see, and what would the toolkit have needed
  to be told to see it the same way from here?

**Stop condition on Task 1:** if the note cannot name a decision the tier
model would move, the tier model is not built. A registry that only makes the
picture tidier is furniture, and 0048's bar applies to config as much as to
surfaces.

### The headline risk, stated in someone else's words

The same review puts the danger better than this brief did. Paraphrased rather
than quoted, per 0051's containment: an orchestrator's job is to route work
across projects and trust what comes back, which it can only do where there is
something stable to route against — so an orchestrator laid over a moving
substrate does not reduce drift, it distributes it, at machine speed.

That is the argument for this round's sequencing, and it is stronger than
"the reach must not grow". A tier model laid over declarations that are still
changing shape does not organise the estate — it makes every inconsistency
reachable from one place, faster. **If Task 1 finds the substrate still
moving, the correct output of this round is a smaller round**, not a tier
model built on the assumption it will settle.

## Task 2 ▸ the model, provisional on Task 1

Sketch, to be rewritten:

- **The registry keeps identity.** A repo entry carries its program and
  project, as the tiered registry already supports. The wizard reads
  membership from there rather than inventing a second scheme.
- **The allowlist keeps reach**, per-repo, per-host, explicit, unchanged in
  its semantics. What it sheds is identity — it stops being the place a repo's
  name and relationships live.
- **A nested root is declared, never inferred.** A repo whose path lies inside
  another allowlisted root says so, and containment resolves against the
  *innermost* declared root. No implicit nesting: two roots overlapping by
  accident is a validation error, not a guess.
- **The harness relationship is declared once**, at program tier: *this
  program is served by this toolkit installation*. It grants nothing by
  itself.

## Task 3 ▸ what happens to 0042

If the model changes where declarations live, 0042's clauses 2 and 3 need
re-reading against the result, and the round produces either an amendment or a
plain statement that they survive untouched. **The bar: after this round, is
widening still a reviewed, committed edit that a human reads?** If the answer
needs a paragraph of explanation, the answer is no.

## Explicitly out of scope

- Any change to what a stage may do, to the execute route's `(repo_key,
  stage_key)` body, or to the literal-argv rule (0042 clauses 3–4).
- Any cross-machine anything (0036).
- The staleness feed contract and the workcycle feed — 0050's build round,
  `COWORK_BRIEF_staleness_feeds.md`, which this brief must not jump ahead of.
- Wiring any real MCF repo on the work rig. This round designs against the
  frozen corpus; the live rig is a later, separate act.
- Reading the corpus outside 0051's declared path.

## Stop conditions

- A program- or project-tier grant confers reach to a repo the allowlist does
  not name → **stop**. This is the round's central failure mode.
- The allowlist grows during this round → stop; the reach was supposed to stay
  where it was.
- Nested roots resolve by inference rather than declaration → stop.
- `resolve_contained` gains a second implementation, or a special case for
  submodules → stop (0042 clause 5).
- Corpus content reaches any surface that publishes, deposits or syncs → stop
  (0051 clause 3).
- The round proceeds without Task 1's findings note committed → stop.

## UAT — sketch, rewrite at round-open

- `[G]` The unpacked pair loads: `sf-data-service`'s manifest validates, the
  nested root resolves to the innermost declared root, and the superproject's
  own state is reported without the submodule's being double-counted.
- `[G]` Registering a program grants nothing: with a program declared and no
  allowlist entry, the board is empty and says so.
- `[G]` Two overlapping roots with no declared nesting are refused at
  validation with both paths named.
- `[H]` **Read the resulting allowlist cold.** Can you still tell, in one
  pass, exactly which repos this host may touch? That property is what 0042
  bought and it is the thing most easily lost to a tier model.
- `[H]` **Does the program tier answer a question you actually had?** Name it,
  or record that it did not and shrink the round.

## Reporting

`docs/COWORK_REPORT_wizard_tiers.md`, walk-sheet `docs/UAT_wizard_tiers.md`,
stamped results.

Record: Task 1's findings in full, and everything they changed; the
membership/reach split as landed, with proof the reach did not grow; the
submodule decision and why; 0042's clauses re-read, amended or upheld; and —
the line this round should be judged on — whether the allowlist is still
readable in one pass by a human deciding what this machine is allowed to
touch.
