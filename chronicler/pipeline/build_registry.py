"""
S1 - Project Registry generator.

Builds / refreshes `L5GN/.intel_sync/project_registry.json`, the canonical join
surface between the filesystem world (repo folders) and the conversation world
(Chronicler DB). See `project_linking_skillset_spec.md` §S1.

Sources it seeds from:
  (a) the **deposited estate snapshots** -- one entry per project each producer
      reported (see "Why estate.json, not a folder scan" below),
  (b) the project rows already described in Intent.md (for the status column),
  (c) Chronicler's `projects` table (Claude project names -> aliases of the
      matching repo; names that match no repo are reported for the HITL step).

Why estate.json, not a folder scan
----------------------------------
This generator used to walk `GITHUB_ROOT/L5GN/` and `GITHUB_ROOT/MCF/`. That
layout exists on **neither** machine -- the knight has an `L5GN` folder but no
`MCF`, and the gaming rig is flat -- so the walk raised "configured root missing"
everywhere and the script had never run successfully anywhere at all.

The deeper problem is that a folder walk is the wrong shape for the mesh. The
doctrine is that producers scan their own estate and *deposit facts*, and the
consumer reads the deposited facts and never reaches back to a producer's disk.
A consumer-side folder scan can only ever see the machine it runs on, which is
precisely the machine whose projects it least needs to discover. So discovery now
reads the estate snapshots the producers deposited: the knight learns about the
work rig's MCF projects because the work rig told it, not because it went
looking.

Two consequences worth stating plainly:
  * `scope` (l5gn/mcf) is a **config tag on the producer's root**, not folder
    nesting -- so no rig has to reorganise its folders to be classifiable.
  * The registry can only see estates that have actually deposited. Running with
    personal-only deposits is legitimate and reports exactly which estates it
    saw; re-run once another producer lands.

Standing rules honoured (spec §"Standing rules"):
  * manual-provenance aliases are never auto-removed or rewritten.
  * whole-file write (never a half-updated registry); tmp-file + os.replace.
  * loud failure: any problem raises and writes nothing.
  * all file I/O UTF-8 explicit; all timestamps UTC ISO-8601.

This is a *generator*, safe to re-run. On re-run it MERGES: existing manual
aliases, alias_sources, first_seen, and any downstream-added keys
(vocabulary / activity / file_inventory / trail) are preserved untouched.

Usage:
    python3 pipeline/build_registry.py                 # write the registry
    python3 pipeline/build_registry.py --dry-run       # print, write nothing
    python3 pipeline/build_registry.py --report-aliases # dry-run + HITL report
    python3 pipeline/build_registry.py --estates-dir /home/l5gn/vault/estates
    python3 pipeline/build_registry.py --estate personal   # one estate only
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, CHRONICLER_ROOT

# --- Locations -------------------------------------------------------------
# CHRONICLER_ROOT is .../Github/L5GN/Chronicler ; the Github root is two up.
GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent          # filesystem path
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
INTENT_MD = GITHUB_ROOT_FS / "L5GN" / "Intent.md"

# The producer's own build output, used when this runs on a rig with no estate
# landing area (dev / Task C.4). On the knight the deposits win.
LOCAL_ESTATE_JSON = Path(__file__).resolve().parent.parent.parent / "data" / "estate.json"

# Scan artefacts and sandbox scratch that are folders in the estate but not
# projects. Excluded here rather than at scan time so the estate deposit stays a
# faithful record of what is on disk.
SKIP_PROJECT_NAMES = {"outputs", "uploads", "test_folder"}

# The curated manual layer: programs, projects, repo groupings, aliases and the
# low_signal_body flags. Authored by hand, read here, never overwritten by the
# generator (the standing manual-provenance rule extended to the tier data).
GROUPS_PATH = Path(os.environ.get(
    "CHRONICLER_REGISTRY_GROUPS",
    str(Path(__file__).resolve().parent.parent.parent / "config" / "project_registry.json")))

SCHEMA_VERSION = 1
PRODUCER_VERSION = "build_registry/1.0"

# Generic leading tokens stripped when generating a short-name alias.
PREFIX_TOKENS = {"l5gn", "mcf"}


# --- small helpers ---------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, obj) -> None:
    """Whole-file write: serialise fully, then atomic replace. Never leaves a
    half-written registry (standing rule)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def split_tokens(name: str):
    """Split a project name into word tokens across separators AND camelCase.
    'L5GN_Armory_v4' -> ['L5GN','Armory','v4']   (acronym+digits stay atomic)
    'DataAccessLayer' -> ['Data','Access','Layer']
    'GemToPairs' -> ['Gem','To','Pairs']

    Only lowercase->UPPERCASE boundaries split; digit->UPPER does NOT, so codes
    like 'L5GN' / 'CID' survive intact."""
    parts = re.split(r"[\s\-_]+", name.strip())
    tokens = []
    for p in parts:
        if not p:
            continue
        camel = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", p)
        tokens.extend([t for t in camel.split(" ") if t])
    return tokens


def norm(s: str) -> str:
    """Aggressive normal form for equivalence tests: lowercase, alnum only."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def is_version_token(tok: str) -> bool:
    return bool(re.fullmatch(r"v?\d+(\.\d+)*", tok.lower()))


# --- alias seeding ---------------------------------------------------------
def seed_aliases(canonical: str) -> dict:
    """Return {alias: source} seeded conservatively from the canonical name.
    Sources: seed_canonical | seed_separator | seed_shortname."""
    tokens = split_tokens(canonical)
    aliases = {canonical: "seed_canonical"}

    def add(alias: str, source: str):
        alias = alias.strip()
        if not alias:
            return
        # case-insensitive dedupe; first source wins, but never downgrade
        # the canonical marker.
        for existing in aliases:
            if norm(existing) == norm(alias):
                return
        aliases[alias] = source

    # separator variants over the full token list
    add(" ".join(tokens), "seed_separator")
    add("-".join(tokens), "seed_separator")
    add("_".join(tokens), "seed_separator")

    # short name: drop leading generic prefix tokens (L5GN / MCF)
    short = [t for t in tokens]
    while short and norm(short[0]) in PREFIX_TOKENS:
        short = short[1:]
    if short and short != tokens:
        add(" ".join(short), "seed_shortname")

    # short name with trailing version tokens dropped
    core = list(short)
    while core and is_version_token(core[-1]):
        core = core[:-1]
    if core and core != short:
        add(" ".join(core), "seed_shortname")

    return aliases


# --- estate discovery (replaces the old folder walk) -----------------------
def resolve_estates_dir(explicit: str | None = None) -> Path | None:
    """Where the deposited estate bundles land.

    Order: an explicit ``--estates-dir``, then this machine's configured
    ``estates_dir`` (the knight's), then ``None``. ``None`` is not an error --
    a producer rig has no landing area and falls back to its own local build
    output, which is the right answer for dev work on the rig.
    """
    if explicit:
        return Path(explicit)
    try:
        from l5gntools import config
        configured = config.machine().get("estates_dir")
    except Exception:  # noqa: BLE001 -- config is advisory here, never fatal
        configured = None
    return Path(configured) if configured else None


def find_estate_snapshots(estates_dir: Path | None,
                          only_estate: str | None = None) -> list[dict]:
    """Locate the deposited ``estate.json`` files to read.

    Returns ``[{"estate": name, "path": Path}]``. On the knight these are
    ``<estates_dir>/<estate>/estate.json``, one per producer that has deposited.
    Absent a landing area, falls back to this repo's own ``data/estate.json`` --
    the local build output -- so the generator is runnable on a producer rig too
    (Task C.4: runnable where the estates actually are).
    """
    found: list[dict] = []
    if estates_dir and estates_dir.is_dir():
        for child in sorted(estates_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            if only_estate and child.name != only_estate:
                continue
            snap = child / "estate.json"
            if snap.is_file():
                found.append({"estate": child.name, "path": snap})
    if found:
        return found

    local = LOCAL_ESTATE_JSON
    if local.is_file() and not only_estate:
        return [{"estate": None, "path": local}]
    return []


def _git_facts(project: dict) -> dict:
    """Pull the git-derived dates the S3 activity signal needs out of a deposited
    project record. Missing dates are returned as ``None`` and reported, never
    invented -- a fabricated first_seen would silently distort the activity
    window that vocabulary and relink lean on.
    """
    gs = project.get("git_summary") or {}
    deep = project.get("git_deep_history") or {}
    is_git = bool(gs.get("is_git"))
    first = gs.get("first_commit_date") or deep.get("first_commit_date")
    last = gs.get("latest_date") or deep.get("latest_date")
    return {
        "vcs": "git" if is_git else "none",
        "first_seen": (str(first)[:10] if first else None),
        "last_activity": (str(last)[:10] if last else None),
        "commit_count": gs.get("commit_count"),
    }


def read_estate_snapshot(entry: dict) -> dict:
    """Parse one deposited estate.json into ``{"estate", "generated_at",
    "root_scopes", "projects"}``. Loud failure on unreadable JSON."""
    path = Path(entry["path"])
    try:
        data = read_json(path)
    except (ValueError, OSError) as exc:
        raise SystemExit(f"[build_registry] unreadable estate snapshot {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("projects"), list):
        raise SystemExit(f"[build_registry] estate snapshot malformed (no projects "
                         f"list): {path}")
    return {
        "estate": entry.get("estate") or data.get("estate_name"),
        "generated_at": data.get("generated_at"),
        "path": str(path),
        "roots": data.get("roots") or [],
        "projects": data["projects"],
    }


def discover_from_estates(snapshots: list[dict]) -> tuple[list, list]:
    """Build seed entries from the deposited estate snapshots.

    Returns ``(entries, gaps)``. ``gaps`` is the honest report of what the
    deposits could not tell us -- projects with no scope tag and projects with no
    git dates -- surfaced rather than papered over, because both silently degrade
    downstream signals if guessed at.

    A project seen in more than one estate keeps its first sighting and records
    the extra estate, rather than being duplicated: the same repo cloned on two
    rigs is one project.
    """
    entries: list = []
    by_name: dict = {}
    gaps: list = []

    for snap in snapshots:
        estate = snap["estate"]
        for project in snap["projects"]:
            name = project.get("name")
            if not name or str(name).startswith("."):
                continue
            if name in SKIP_PROJECT_NAMES:
                continue

            facts = _git_facts(project)
            scope = project.get("scope")
            if not scope:
                gaps.append(f"{name}: no scope tag from estate "
                            f"'{estate or 'local'}' -- tag that root in the "
                            "producer's config/local.json ('roots': [{'path': ..., "
                            "'scope': 'l5gn'|'mcf'}]); filed as 'other' meanwhile")
                scope = "other"
            if facts["first_seen"] is None:
                gaps.append(f"{name}: no git dates in the deposit "
                            f"(vcs={facts['vcs']}) -- the S3 activity window for "
                            "this project will be undated")

            existing = by_name.get(name)
            if existing is not None:
                # Same repo on two rigs. Keep one entry; record both estates.
                if estate and estate not in existing["estates"]:
                    existing["estates"].append(estate)
                if existing["scope"] == "other" and scope != "other":
                    existing["scope"] = scope
                continue

            aliases = seed_aliases(name)
            entry = {
                "canonical_name": name,
                "path": project.get("path") or "",
                "scope": scope,
                "vcs": facts["vcs"],
                "aliases": list(aliases.keys()),
                "alias_sources": aliases,
                "status": "active",
                "first_seen": facts["first_seen"] or "unknown",
                "last_activity": facts["last_activity"],
                "commit_count": facts["commit_count"],
                "estates": [estate] if estate else [],
                "registry_updated": utc_now(),
            }
            by_name[name] = entry
            entries.append(entry)

    entries.sort(key=lambda e: e["canonical_name"].lower())
    return entries, gaps


# --- three-tier assembly (DECISIONS 0012) ----------------------------------
def load_manual_groups(path: Path = None) -> dict:
    """Read the curated program/project/repo layer.

    This is manual-provenance data end to end: Tim's programs, his project
    groupings, which repo folders are incarnations of which project, his curated
    aliases and his low_signal_body flags. The generator reads it and never
    writes it -- the same rule that already protects manual aliases, extended to
    the tier structure, so a re-run can never flatten the hierarchy back out.

    Absent file is not fatal: the registry degrades to one auto project per
    deposited repo, which is exactly the old flat behaviour, and says so.
    """
    path = Path(path or GROUPS_PATH)
    if not path.is_file():
        return {"programs": [], "projects": [], "_source": None}
    data = read_json(path)
    return {
        "programs": data.get("programs", []),
        "projects": data.get("projects", []),
        "_source": str(path),
    }


def _slugify(name: str) -> str:
    """Derive an id for a repo the curated layer does not yet mention.

    Deliberately dumb and stable: lowercase, non-alphanumerics to hyphens. An
    auto id is a placeholder for Tim to replace with a curated one, not a
    permanent identity -- which is fine, because it is only ever minted for a
    repo he has not yet classified.
    """
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def assemble_tiers(entries: list, groups: dict) -> tuple[dict, list]:
    """Fold the estate-derived repo facts into the curated program/project tree.

    Returns ``(registry_body, notes)`` where ``registry_body`` has ``programs``
    and ``projects``, each project carrying a ``repos`` list.

    Three things happen here, in this order:

      1. Every curated repo is matched to a deposited project by canonical_name,
         and the deposit's facts (path, scope, git dates, estates, vcs) are
         attached to it. A curated repo with no matching deposit keeps its
         identity and is marked ``present: false`` -- it is a repo Tim knows
         about that no rig has deposited yet (very often an MCF repo, before the
         work rig deploys). It is never dropped.
      2. Every deposited repo NOT claimed by any curated project becomes its own
         single-repo project with ``provenance: 'auto'``. Nothing the estate
         reported is ever lost just because it has not been classified yet.
      3. Curated projects with no repos at all (Chancellor, the UCP, the MCF
         projects until the work rig lands) are kept as link targets regardless.
         A project's existence is a fact about the work, not about whether a
         folder for it happens to be on a disk this run could see.
    """
    notes: list = []
    by_name = {e["canonical_name"]: e for e in entries}
    claimed: set = set()

    programs = [dict(p) for p in groups.get("programs", [])]
    program_ids = {p["id"] for p in programs}

    projects: list = []
    for curated in groups.get("projects", []):
        proj = dict(curated)
        proj["provenance"] = "manual"
        proj.setdefault("aliases", [])
        proj.setdefault("low_signal_body", False)
        if proj.get("program") and proj["program"] not in program_ids:
            notes.append(f"project '{proj['id']}' names program "
                         f"'{proj['program']}', which is not declared in programs[]")

        repos = []
        for curated_repo in curated.get("repos", []):
            repo = dict(curated_repo)
            repo["provenance"] = "manual"
            deposited = by_name.get(repo.get("canonical_name"))
            if deposited is not None:
                claimed.add(repo["canonical_name"])
                repo.update({
                    "present": True,
                    "path": deposited["path"],
                    "scope": deposited["scope"],
                    "vcs": deposited["vcs"],
                    "first_seen": deposited["first_seen"],
                    "last_activity": deposited["last_activity"],
                    "commit_count": deposited["commit_count"],
                    "estates": deposited["estates"],
                    # union the seeded aliases under the curated ones
                    "aliases": _merge_alias_lists(repo.get("aliases", []),
                                                  deposited["aliases"]),
                })
            else:
                repo["present"] = False
                repo.setdefault("aliases", [])
                notes.append(f"repo '{repo.get('canonical_name')}' (project "
                             f"'{proj['id']}') is in no deposit yet -- kept as a "
                             "link target, marked present=false")
            repos.append(repo)
        # A project with no repos is normal, not a gap: Chancellor and the UCP
        # are efforts with no folder, and every MCF project is repo-less until
        # the work rig deposits. Not reported, to keep the gap list actionable.
        proj["repos"] = repos
        projects.append(proj)

    # Deposited repos nobody claimed become their own single-repo projects.
    for entry in entries:
        if entry["canonical_name"] in claimed:
            continue
        pid = _slugify(entry["canonical_name"])
        notes.append(f"unclaimed repo '{entry['canonical_name']}' -> auto project "
                     f"'{pid}' (assign it to a program/project in the curated "
                     "registry when you know where it belongs)")
        projects.append({
            "id": pid,
            "canonical_name": entry["canonical_name"],
            "program": None,
            "scope": entry["scope"],
            "aliases": list(entry["aliases"]),
            "alias_sources": entry["alias_sources"],
            "low_signal_body": False,
            "provenance": "auto",
            "repos": [{
                # Distinct id from its parent project even though they describe
                # the same folder today: ids must be unique across tiers, and if
                # Tim later files this repo under a real project the repo id
                # survives the move while the auto project id disappears.
                "id": f"{pid}-repo",
                "canonical_name": entry["canonical_name"],
                "aliases": list(entry["aliases"]),
                "provenance": "auto",
                "present": True,
                "path": entry["path"],
                "scope": entry["scope"],
                "vcs": entry["vcs"],
                "first_seen": entry["first_seen"],
                "last_activity": entry["last_activity"],
                "commit_count": entry["commit_count"],
                "estates": entry["estates"],
            }],
        })

    projects.sort(key=lambda p: (p.get("program") or "~", p["canonical_name"].lower()))
    return {"programs": programs, "projects": projects}, notes


def _merge_alias_lists(curated: list, seeded: list) -> list:
    """Curated aliases first (they are the human's words), then any seeded alias
    that is not already present case-insensitively."""
    out = list(curated)
    for a in seeded:
        if not any(norm(a) == norm(x) for x in out):
            out.append(a)
    return out


def collect_link_targets(body: dict) -> dict:
    """Flatten the tree to ``{id: {tier, canonical_name, program, project, ...}}``.

    Every tier is a link target: a thread may legitimately be about a program, a
    project, or one specific incarnation. What must NOT vary is the identifier --
    it is always the `id` (see the registry's `_id_scheme` note). Duplicate ids
    across tiers are a hard error, because one id meaning two things is the exact
    failure mode this scheme exists to prevent.
    """
    targets: dict = {}

    def _add(tier: str, tid: str, payload: dict):
        if tid in targets:
            raise SystemExit(f"[build_registry] duplicate registry id '{tid}' "
                             f"({targets[tid]['tier']} and {tier}) -- one id must "
                             "mean exactly one thing")
        targets[tid] = dict(payload, tier=tier, id=tid)

    for prog in body.get("programs", []):
        _add("program", prog["id"], {
            "canonical_name": prog.get("name", prog["id"]),
            "scope": prog.get("scope"), "program": prog["id"], "project": None,
            "aliases": prog.get("aliases", [prog.get("name", prog["id"])]),
            "low_signal_body": bool(prog.get("low_signal_body")),
        })
    for proj in body.get("projects", []):
        _add("project", proj["id"], {
            "canonical_name": proj["canonical_name"],
            "scope": proj.get("scope"), "program": proj.get("program"),
            "project": proj["id"], "aliases": proj.get("aliases", []),
            "low_signal_body": bool(proj.get("low_signal_body")),
        })
        for repo in proj.get("repos", []):
            _add("repo", repo["id"], {
                "canonical_name": repo["canonical_name"],
                "scope": repo.get("scope") or proj.get("scope"),
                "program": proj.get("program"), "project": proj["id"],
                "aliases": repo.get("aliases", []),
                # A repo inherits its project's body-signal judgement: if the
                # project name is worthless in a body, so is its folder name.
                "low_signal_body": bool(repo.get("low_signal_body",
                                                 proj.get("low_signal_body"))),
                "present": repo.get("present", False),
                "path": repo.get("path"),
                "first_seen": repo.get("first_seen"),
                "last_activity": repo.get("last_activity"),
                "estates": repo.get("estates", []),
            })
    return targets


# --- external signal sources ----------------------------------------------
def parse_intent_status(intent_md: Path) -> dict:
    """Map project name -> normalized status from Intent.md's goals table.
    Cells like 'Inferred — likely legacy/superseded' -> 'legacy'; else
    'active'. Only rows with **Project** bolded in the first column count."""
    if not intent_md.is_file():
        return {}
    result = {}
    for line in intent_md.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|.*\|\s*(.+?)\s*\|\s*$", line)
        if not m:
            continue
        name, status_cell = m.group(1).strip(), m.group(2).lower()
        if "legacy" in status_cell or "superseded" in status_cell:
            result[name] = "legacy"
        else:
            result[name] = "active"
    return result


def load_claude_projects(conn):
    rows = conn.execute("SELECT project_id, name FROM projects").fetchall()
    return [(r["project_id"], r["name"]) for r in rows]


def build_alias_index(targets: dict):
    """``norm(alias) -> registry id``, for matching Claude project names.

    Keyed by id, not canonical_name -- the single identifier scheme (0012). A
    Claude project called "Crystal Spire" folds onto the *project* tier, while
    one called "smelt-gateway" folds onto that repo, and both come back as ids.
    """
    idx = {}
    for tid, meta in targets.items():
        for a in list(meta.get("aliases", [])) + [meta["canonical_name"]]:
            idx.setdefault(norm(a), tid)
    return idx


# --- merge with existing registry -----------------------------------------
DOWNSTREAM_KEYS = ("vocabulary", "activity", "file_inventory", "trail",
                   "link_evidence_ids")


def merge_entry(new: dict, old: dict) -> dict:
    """Merge a freshly-seeded entry over an existing one, preserving:
      * manual aliases (source == 'manual') + their sources,
      * any Claude-project aliases already recorded,
      * first_seen (registry remembers when it first saw the project),
      * downstream signal blocks added by S2/S3/S4/S7.
    """
    merged = dict(new)
    # preserve first_seen
    merged["first_seen"] = old.get("first_seen", new["first_seen"])

    # union aliases: start from new seeds, then re-add any old alias whose
    # source is manual or claude_project (never auto-drop those).
    sources = dict(new["alias_sources"])
    alias_list = list(new["aliases"])
    for a in old.get("aliases", []):
        src = old.get("alias_sources", {}).get(a, "manual")
        if src in ("manual", "claude_project", "vocabulary_extract"):
            if not any(norm(a) == norm(x) for x in alias_list):
                alias_list.append(a)
            sources[a] = src
    merged["aliases"] = alias_list
    merged["alias_sources"] = sources

    # carry downstream signal blocks forward untouched
    for k in DOWNSTREAM_KEYS:
        if k in old:
            merged[k] = old[k]
    return merged


def attach_claude_aliases(body: dict, targets: dict, claude_projects, alias_index):
    """Add matching Claude project names as claude_project-sourced aliases on
    whichever tier they matched.

    Returns the list of (project_id, name) that matched NO tier — the tribal-
    knowledge mapping Tim must resolve (HITL)."""
    index_by_id: dict = {}
    for prog in body.get("programs", []):
        index_by_id[prog["id"]] = prog
    for proj in body.get("projects", []):
        index_by_id[proj["id"]] = proj
        for repo in proj.get("repos", []):
            index_by_id[repo["id"]] = repo

    unmapped = []
    for pid, name in claude_projects:
        tid = alias_index.get(norm(name))
        if tid is None:
            unmapped.append((pid, name))
            continue
        node = index_by_id[tid]
        aliases = node.setdefault("aliases", [])
        if not any(norm(name) == norm(a) for a in aliases):
            aliases.append(name)
            node.setdefault("alias_sources", {})[name] = "claude_project"
        targets[tid]["aliases"] = list(aliases)
    return unmapped


# --- validation ------------------------------------------------------------
VALID_SCOPES = ("l5gn", "mcf", "other", None)


def validate(registry) -> None:
    """Structural gate on the generated registry. Raises (loud failure) rather
    than writing anything questionable -- a malformed registry silently
    mis-links every thread downstream."""
    if not isinstance(registry, dict) or "projects" not in registry:
        raise SystemExit("[build_registry] registry root malformed")
    if "programs" not in registry:
        raise SystemExit("[build_registry] registry has no programs tier "
                         "(DECISIONS 0012 requires program > project > repo)")

    program_ids = {p.get("id") for p in registry["programs"]}
    for p in registry["programs"]:
        if not p.get("id") or not p.get("name"):
            raise SystemExit(f"[build_registry] program missing id/name: {p}")

    seen_ids: dict = {}

    def _claim(tid, tier, label):
        if not tid:
            raise SystemExit(f"[build_registry] {tier} '{label}' has no id -- the "
                             "id is the only identifier scheme (0012)")
        if tid in seen_ids:
            raise SystemExit(f"[build_registry] duplicate id '{tid}' "
                             f"({seen_ids[tid]} and {tier}) -- one id must mean "
                             "exactly one thing")
        seen_ids[tid] = tier

    for pid in program_ids:
        _claim(pid, "program", pid)

    for e in registry["projects"]:
        label = e.get("canonical_name") or e.get("id")
        _claim(e.get("id"), "project", label)
        if not e.get("canonical_name"):
            raise SystemExit(f"[build_registry] project {e.get('id')} has no "
                             "canonical_name")
        if e.get("scope") not in VALID_SCOPES:
            raise SystemExit(f"[build_registry] bad scope on {label}: {e.get('scope')}")
        if e.get("program") and e["program"] not in program_ids:
            raise SystemExit(f"[build_registry] project {label} references unknown "
                             f"program '{e['program']}'")
        if not isinstance(e.get("repos"), list):
            raise SystemExit(f"[build_registry] project {label} has no repos list")
        for r in e["repos"]:
            rlabel = r.get("canonical_name") or r.get("id")
            _claim(r.get("id"), "repo", rlabel)
            if r.get("scope") not in VALID_SCOPES:
                raise SystemExit(f"[build_registry] bad scope on repo {rlabel}")
            if r.get("present") and r.get("vcs") not in ("git", "none"):
                raise SystemExit(f"[build_registry] bad vcs on present repo {rlabel}")


# --- main ------------------------------------------------------------------
def build(estates_dir: str | None = None, only_estate: str | None = None):
    resolved = resolve_estates_dir(estates_dir)
    snapshots_found = find_estate_snapshots(resolved, only_estate)
    if not snapshots_found:
        where = str(resolved) if resolved else "(no estates_dir configured)"
        raise SystemExit(
            "[build_registry] no estate snapshots to read. Looked for "
            f"<estates_dir>/<estate>/estate.json under {where} and for the local "
            f"build output at {LOCAL_ESTATE_JSON}. Run `run.py build` on a "
            "producer and `run.py deposit --push`, or pass --estates-dir.")
    snapshots = [read_estate_snapshot(s) for s in snapshots_found]
    entries, gaps = discover_from_estates(snapshots)
    if not entries:
        raise SystemExit("[build_registry] estate snapshots contained no projects "
                         "-- refusing to write an empty registry.")
    status_map = parse_intent_status(INTENT_MD)
    for e in entries:
        if e["canonical_name"] in status_map:
            e["status"] = status_map[e["canonical_name"]]

    # Fold the estate-derived repo facts into the curated program/project tree.
    groups = load_manual_groups()
    if groups["_source"] is None:
        gaps.append(f"no curated registry at {GROUPS_PATH} -- every deposited repo "
                    "becomes its own auto project and there is no program tier "
                    "content. Author the curated layer to get the hierarchy.")
    body, notes = assemble_tiers(entries, groups)
    targets = collect_link_targets(body)

    conn = get_connection()
    try:
        claude_projects = load_claude_projects(conn)
    finally:
        conn.close()

    alias_index = build_alias_index(targets)
    unmapped = attach_claude_aliases(body, targets, claude_projects, alias_index)

    # Drop from the HITL 'unmapped' list any Claude project name now covered by
    # an alias at any tier, so the review is genuinely one-time and later runs
    # don't re-nag.
    covered = {norm(a) for meta in targets.values() for a in meta.get("aliases", [])}
    covered |= {norm(meta["canonical_name"]) for meta in targets.values()}
    unmapped = [(pid, name) for pid, name in unmapped if norm(name) not in covered]

    registry = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "generated_at": utc_now(),
        # The identifier contract, written into the artefact so every consumer
        # reads it rather than inferring it (round-3 D.3).
        "id_scheme": "id",
        "curated_source": groups["_source"],
        # Provenance: exactly which deposits this registry was built from, so a
        # partial run (personal-only, work rig not yet deployed) is visible in
        # the artefact itself and never mistaken for a complete picture.
        "sources": [{"estate": s["estate"], "path": s["path"],
                     "generated_at": s["generated_at"],
                     "projects": len(s["projects"])} for s in snapshots],
        "programs": body["programs"],
        "projects": body["projects"],
    }
    validate(registry)
    return registry, unmapped, gaps + notes, snapshots


def print_alias_report(registry, unmapped, gaps, snapshots):
    print("=" * 70)
    print("ESTATE SOURCES — what this registry could see")
    print("=" * 70)
    for s in snapshots:
        print(f"  estate={s['estate'] or '(local build output)'}  "
              f"generated={s['generated_at']}  projects={len(s['projects'])}")
        print(f"      {s['path']}")
    estates = {s["estate"] for s in snapshots if s["estate"]}
    for expected in ("personal", "work"):
        if estates and expected not in estates:
            print(f"  MISSING estate '{expected}' — its projects are invisible to "
                  "this run. Re-run after that producer deposits.")

    print()
    print("=" * 70)
    print("THREE-TIER REGISTRY — program > project > repo (DECISIONS 0012)")
    print(f"id scheme: {registry.get('id_scheme')}  "
          f"(every tier is a link target; project_link always holds an id)")
    print("=" * 70)

    by_program: dict = {}
    for proj in registry["projects"]:
        by_program.setdefault(proj.get("program"), []).append(proj)

    prog_names = {p["id"]: p.get("name", p["id"]) for p in registry["programs"]}
    order = [p["id"] for p in registry["programs"]] + [None]
    for prog_id in order:
        projects = by_program.get(prog_id)
        if not projects:
            continue
        label = (f"PROGRAM  {prog_id}  ({prog_names.get(prog_id)})" if prog_id
                 else "STANDALONE  (no program)")
        print(f"\n{label}")
        for proj in projects:
            lsb = "  [low_signal_body]" if proj.get("low_signal_body") else ""
            print(f"  PROJECT  {proj['id']:32} {proj['canonical_name']}"
                  f"  ({proj.get('scope')}, {proj.get('provenance')}){lsb}")
            for a in proj.get("aliases", []):
                src = (proj.get("alias_sources") or {}).get(a, "manual")
                print(f"      alias {a!r:36} [{src}]")
            for repo in proj.get("repos", []):
                present = "present" if repo.get("present") else "NOT IN ANY DEPOSIT"
                estates = "+".join(repo.get("estates") or []) or "-"
                print(f"      REPO   {repo['id']:30} {repo['canonical_name']}"
                      f"  [{present}, first_seen={repo.get('first_seen')}, "
                      f"estates={estates}]")
                for a in repo.get("aliases", []):
                    src = (repo.get("alias_sources") or {}).get(a, "manual")
                    print(f"          alias {a!r:32} [{src}]")

    print("\n" + "=" * 70)
    print("UNMAPPED Claude project names — matched no project in any deposit.")
    print("These need Tim to say which project (if any) each belongs to.")
    print("=" * 70)
    for pid, name in unmapped:
        print(f"    - {name!r}   (project_id {pid})")
    if not unmapped:
        print("    (none)")

    print("\n" + "=" * 70)
    print("DEPOSIT GAPS — what the estate data could not tell us")
    print("=" * 70)
    for g in gaps:
        print(f"    - {g}")
    if not gaps:
        print("    (none)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build/refresh the project registry (S1).")
    ap.add_argument("--dry-run", action="store_true", help="Print, write nothing.")
    ap.add_argument("--report-aliases", action="store_true",
                    help="Dry-run and print the estate sources, seeded alias "
                         "lists, unmapped Claude projects and deposit gaps for "
                         "the HITL review step.")
    ap.add_argument("--estates-dir", default=None,
                    help="Where deposited estate bundles live (default: this "
                         "machine's configured estates_dir, else the local build "
                         "output).")
    ap.add_argument("--estate", default=None,
                    help="Read only this estate's deposit (e.g. 'personal').")
    args = ap.parse_args()

    registry, unmapped, gaps, snapshots = build(args.estates_dir, args.estate)

    if args.report_aliases:
        print_alias_report(registry, unmapped, gaps, snapshots)
        print(f"\n(dry-run: {len(registry['projects'])} entries would be written "
              f"to {REGISTRY_PATH})")
    elif args.dry_run:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
        print(f"\n(dry-run: {len(registry['projects'])} entries, "
              f"{len(unmapped)} unmapped Claude projects, {len(gaps)} deposit gaps)")
    else:
        write_json_atomic(REGISTRY_PATH, registry)
        print(f"Wrote {len(registry['projects'])} entries to {REGISTRY_PATH}")
        for s in snapshots:
            print(f"  from estate={s['estate'] or '(local)'}  {s['path']}")
        if unmapped:
            print(f"{len(unmapped)} Claude project name(s) matched no project — "
                  f"run with --report-aliases to review.")
        if gaps:
            print(f"{len(gaps)} deposit gap(s) — run with --report-aliases to see them.")
