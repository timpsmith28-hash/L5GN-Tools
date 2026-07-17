"""
S1 - Project Registry generator.

Builds / refreshes `L5GN/.intel_sync/project_registry.json`, the canonical join
surface between the filesystem world (repo folders) and the conversation world
(Chronicler DB). See `project_linking_skillset_spec.md` §S1.

Sources it seeds from:
  (a) folder scan of the L5GN + MCF roots (one entry per direct sub-folder),
  (b) the project rows already described in Intent.md (for the status column),
  (c) Chronicler's `projects` table (Claude project names -> aliases of the
      matching repo; names that match no repo are reported for the HITL step).

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
    python3 pipeline/build_registry.py --windows-root "D:\\Repos"   # override path base
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, CHRONICLER_ROOT

# --- Locations -------------------------------------------------------------
# CHRONICLER_ROOT is .../Github/L5GN/Chronicler ; the Github root is two up.
GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent          # filesystem path
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
INTENT_MD = GITHUB_ROOT_FS / "L5GN" / "Intent.md"

# The `path` field must be the path on Tim's real Windows machine regardless of
# where this script runs (it may be generated from the Cowork sandbox). Built
# from this base + scope-folder + canonical_name, so it is always correct for
# Tim even when the filesystem we scan is a Linux mount. Override with
# --windows-root if the repos ever move.
DEFAULT_WINDOWS_ROOT = r"C:\Users\tim.smith\Github"

# scope folder name -> scope tag
ROOTS = {"L5GN": "l5gn", "MCF": "mcf"}

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


# --- filesystem discovery --------------------------------------------------
def git_first_commit_date(fs_path: Path):
    try:
        out = subprocess.run(
            ["git", "log", "--reverse", "--format=%aI"],
            cwd=str(fs_path), capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip().splitlines()[0][:10]
    except Exception:
        pass
    return None


def folder_earliest_date(fs_path: Path):
    """Coarse fallback for non-git folders: earliest file mtime (date only)."""
    earliest = None
    for root, dirs, files in os.walk(fs_path):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            try:
                m = os.path.getmtime(os.path.join(root, fn))
            except OSError:
                continue
            earliest = m if earliest is None else min(earliest, m)
    ts = earliest if earliest is not None else os.path.getmtime(fs_path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def discover_folders(windows_root: str):
    """Yield an entry dict per direct sub-folder of each root (skipping hidden
    dotfolders). Loud failure if a configured root is missing."""
    entries = []
    for root_name, scope in ROOTS.items():
        root_fs = GITHUB_ROOT_FS / root_name
        if not root_fs.is_dir():
            raise SystemExit(f"[build_registry] configured root missing: {root_fs}")
        for child in sorted(root_fs.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            canonical = child.name
            is_git = (child / ".git").is_dir()
            win_path = f"{windows_root}\\{root_name}\\{canonical}"
            if is_git:
                first_seen = git_first_commit_date(child) or folder_earliest_date(child)
            else:
                first_seen = folder_earliest_date(child)
            entries.append({
                "canonical_name": canonical,
                "path": win_path,
                "scope": scope,
                "vcs": "git" if is_git else "none",
                "aliases": list(seed_aliases(canonical).keys()),
                "alias_sources": seed_aliases(canonical),
                "status": "active",
                "first_seen": first_seen,
                "registry_updated": utc_now(),
                "_fs_path": str(child),  # transient, stripped before write
            })
    return entries


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


def build_alias_index(entries):
    """norm(alias) -> canonical_name, for matching Claude project names."""
    idx = {}
    for e in entries:
        for a in e["aliases"]:
            idx.setdefault(norm(a), e["canonical_name"])
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


def attach_claude_aliases(entries, claude_projects, alias_index):
    """Add matching Claude project names as claude_project-sourced aliases.
    Returns the list of (project_id, name) that matched NO entry — the tribal-
    knowledge mapping Tim must resolve (HITL)."""
    by_canonical = {e["canonical_name"]: e for e in entries}
    unmapped = []
    for pid, name in claude_projects:
        canonical = alias_index.get(norm(name))
        if canonical is None:
            unmapped.append((pid, name))
            continue
        e = by_canonical[canonical]
        if not any(norm(name) == norm(a) for a in e["aliases"]):
            e["aliases"].append(name)
            e["alias_sources"][name] = "claude_project"
    return unmapped


# --- validation ------------------------------------------------------------
REQUIRED_KEYS = {"canonical_name", "path", "scope", "vcs", "aliases",
                 "alias_sources", "status", "first_seen", "registry_updated"}


def validate(registry) -> None:
    if not isinstance(registry, dict) or "projects" not in registry:
        raise SystemExit("[build_registry] registry root malformed")
    for e in registry["projects"]:
        missing = REQUIRED_KEYS - set(e)
        if missing:
            raise SystemExit(f"[build_registry] entry {e.get('canonical_name')} "
                             f"missing keys: {sorted(missing)}")
        if e["scope"] not in ("l5gn", "mcf", "other"):
            raise SystemExit(f"[build_registry] bad scope on {e['canonical_name']}")
        if e["vcs"] not in ("git", "none"):
            raise SystemExit(f"[build_registry] bad vcs on {e['canonical_name']}")
        for a in e["aliases"]:
            if a not in e["alias_sources"]:
                raise SystemExit(f"[build_registry] alias '{a}' on "
                                 f"{e['canonical_name']} has no provenance")


# --- main ------------------------------------------------------------------
def build(windows_root: str):
    entries = discover_folders(windows_root)
    status_map = parse_intent_status(INTENT_MD)
    for e in entries:
        if e["canonical_name"] in status_map:
            e["status"] = status_map[e["canonical_name"]]

    conn = get_connection()
    try:
        claude_projects = load_claude_projects(conn)
    finally:
        conn.close()

    alias_index = build_alias_index(entries)
    unmapped = attach_claude_aliases(entries, claude_projects, alias_index)

    # merge with existing registry if present
    if REGISTRY_PATH.is_file():
        old = read_json(REGISTRY_PATH)
        old_by_name = {e["canonical_name"]: e for e in old.get("projects", [])}
        merged = []
        for e in entries:
            if e["canonical_name"] in old_by_name:
                merged.append(merge_entry(e, old_by_name[e["canonical_name"]]))
            else:
                merged.append(e)
        # NOTE: entries present in old but not on disk anymore are NOT dropped
        # here silently; a folder rename is a discrepancy for the nightly task
        # to flag, never an auto-merge. We keep them, flagged.
        seen = {e["canonical_name"] for e in entries}
        for name, oe in old_by_name.items():
            if name not in seen:
                oe.setdefault("status", "active")
                oe["_orphaned"] = True  # folder gone / renamed — flag, don't drop
                merged.append(oe)
        entries = merged

    # Drop from the HITL 'unmapped' list any Claude project name now covered by
    # an existing alias (a manual/claude_project mapping from a prior sitting),
    # so the review is genuinely one-time and later runs don't re-nag.
    covered = {norm(a) for e in entries for a in e["aliases"]}
    unmapped = [(pid, name) for pid, name in unmapped if norm(name) not in covered]

    # strip transient fields before writing
    fs_paths = {e["canonical_name"]: e.pop("_fs_path", None) for e in entries}

    registry = {
        "schema_version": SCHEMA_VERSION,
        "producer_version": PRODUCER_VERSION,
        "generated_at": utc_now(),
        "windows_root": windows_root,
        "projects": entries,
    }
    validate(registry)
    return registry, unmapped, fs_paths


def print_alias_report(registry, unmapped):
    print("=" * 70)
    print("SEEDED ALIAS LISTS — review / extend (S1 HITL step)")
    print("=" * 70)
    for e in registry["projects"]:
        flag = " [ORPHANED: folder missing]" if e.get("_orphaned") else ""
        print(f"\n{e['canonical_name']}  ({e['scope']}, {e['vcs']}, "
              f"status={e['status']}, first_seen={e['first_seen']}){flag}")
        for a in e["aliases"]:
            print(f"    - {a!r:40}  [{e['alias_sources'].get(a)}]")
    print("\n" + "=" * 70)
    print("UNMAPPED Claude project names — matched no repo folder.")
    print("These need Tim to say which repo (if any) each belongs to.")
    print("=" * 70)
    for pid, name in unmapped:
        print(f"    - {name!r}   (project_id {pid})")
    if not unmapped:
        print("    (none)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build/refresh the project registry (S1).")
    ap.add_argument("--dry-run", action="store_true", help="Print, write nothing.")
    ap.add_argument("--report-aliases", action="store_true",
                    help="Dry-run and print the seeded alias lists + unmapped "
                         "Claude projects for the HITL review step.")
    ap.add_argument("--windows-root", default=DEFAULT_WINDOWS_ROOT,
                    help="Base for the Windows `path` field (default Tim's Github).")
    args = ap.parse_args()

    registry, unmapped, _ = build(args.windows_root)

    if args.report_aliases:
        print_alias_report(registry, unmapped)
        print(f"\n(dry-run: {len(registry['projects'])} entries would be written "
              f"to {REGISTRY_PATH})")
    elif args.dry_run:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
        print(f"\n(dry-run: {len(registry['projects'])} entries, "
              f"{len(unmapped)} unmapped Claude projects)")
    else:
        write_json_atomic(REGISTRY_PATH, registry)
        print(f"Wrote {len(registry['projects'])} entries to {REGISTRY_PATH}")
        if unmapped:
            print(f"{len(unmapped)} Claude project name(s) matched no folder — "
                  f"run with --report-aliases to review.")
