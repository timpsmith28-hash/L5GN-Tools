"""blast_radius -- rank a project by the *consequence* of the code it contains,
not the size of its files.

The estate's real risk is blast radius: the code most able to mutate a system
outside its own repo (a Salesforce prod import, a `terraform apply`, an
`rm -rf` over ssh) is exactly the code the size-ranked report was blindest to.
This scanner statically flags out-of-repo mutations, classifies each by target
environment and whether a gate guards it, and emits a per-project tier that the
report ranks **above file size**.

Discipline, non-negotiable:

* **Reads code as text, never executes it.** Detecting a prod-write is not running
  one. No import of a scanned file, no eval, no shell.
* **Reports the verdict, never the evidence body.** It captures the matched signal
  family, the file and line, the env *classification* and guarded/raw -- never the
  raw source line, and never the alias or credential. Naming `upload_r141.py` a
  raw-write-prod is the finding; pasting its body recreates the exposure (the
  Crystal Spire lesson). The guardrail is structural: the raw line is never stored.
* **Smoke detector, not SAST.** No data-flow, no exploitability proof. A dismissed
  false positive costs a glance; a missed prod-write costs a production incident,
  so it **biases toward flagging** -- unknown target env is ranked as prod, and a
  write is `raw` unless a gate is clearly present.

Scope is inherited from the bug-fix brief: the shared :class:`Scope` filter keeps
it out of gitignored / vendored / chat-archive paths, so a `sf data import` string
inside a chat transcript is not a finding.
"""
from __future__ import annotations

from ..contract import SAFE

import re
from pathlib import Path

from ..common import NO_OPTIONAL_LOCKS, capped, is_git_repo, rel, run_git
from ._scope import Scope

NAME = "blast_radius"
DESCRIPTION = "Flags out-of-repo mutations and ranks projects by write blast radius."
ESTATE_LEVEL = False
SAFETY = SAFE

_SCAN_SUFFIXES = (".py", ".sh", ".bash", ".ps1", ".js", ".ts", ".sql", ".yml",
                  ".yaml", ".cfg", ".ini", ".tf", ".cls", ".apex")

HIT_CAP = 300

# --- Signal families (data-driven, so the list extends without a code change) --
# Each family: kind ('write' | 'read') and the literal markers that name it. The
# markers are canonical signal names -- what gets stored -- so no raw source line
# ever enters the output.
SIGNALS: list[dict] = [
    {"family": "salesforce-dml", "kind": "write", "env": True, "markers": [
        r"sf\s+data\s+(?:import|upsert|update|delete)",
        r"force:data:bulk:(?:upsert|delete)",
        r"data\s+import\s+bulk",
        r"Database\.(?:update|upsert|delete|insert)",
        r"@future\(callout=true\)"]},
    {"family": "salesforce-read", "kind": "read", "env": False, "markers": [
        r"sf\s+data\s+(?:query|export)", r"Database\.query"]},
    {"family": "shell-os", "kind": "write", "env": False, "markers": [
        r"os\.system", r"subprocess\.(?:run|call|Popen|check_output)",
        r"rm\s+-rf", r"curl\s+.*-X\s*(?:POST|PUT|DELETE|PATCH)",
        r"\bscp\s", r"\bssh\s", r"\bmv\s"]},
    {"family": "cloud-infra", "kind": "write", "env": True, "markers": [
        r"aws\s+s3\s+(?:rm|cp|mv|sync)", r"terraform\s+apply",
        r"kubectl\s+(?:apply|delete)", r"gcloud\s+\S+\s+delete"]},
    {"family": "db-writes", "kind": "write", "env": False, "markers": [
        r"INSERT\s+INTO", r"\bUPDATE\s+\w", r"DELETE\s+FROM",
        r"DROP\s+(?:TABLE|DATABASE)", r"\.commit\(\)"]},
    {"family": "http-writes", "kind": "write", "env": False, "markers": [
        r"requests\.(?:post|put|patch|delete)",
        r"httpx\.(?:post|put|patch|delete)"]},
    {"family": "cloud-read", "kind": "read", "env": False, "markers": [
        r"aws\s+s3\s+ls", r"kubectl\s+get", r"requests\.get", r"httpx\.get"]},
]
def _clean_marker(m: str) -> str:
    """A readable signal name from a marker regex -- what gets stored. Deliberately
    lossy: it names the *kind* of call (e.g. 'sf data import upsert update delete'),
    never any content from the scanned file."""
    s = re.sub(r"\\s\+?", " ", m)                 # \s+ / \s -> space
    s = re.sub(r"\(\?:|[()?:|\\]", " ", s)         # strip group syntax
    s = s.replace(".*", " ").replace("+", " ")
    return re.sub(r"\s+", " ", s).strip()


# Compiled once: (family, kind, env_sensitive, compiled_regex, canonical_name)
_COMPILED = [(s["family"], s["kind"], s["env"], re.compile(m, re.IGNORECASE),
              _clean_marker(m))
             for s in SIGNALS for m in s["markers"]]

_TARGET_ORG = re.compile(r"(?:--target-?org|--targetusername)\s+([A-Za-z0-9_.-]+)",
                         re.IGNORECASE)
# Substring matches, not word-bounded: an alias like `myMainAlias` or `acmeMain`
# must read prod. Over-matching prod is the fail-safe direction (a false prod
# costs a glance; a missed prod costs an incident).
_PROD_ALIAS = re.compile(r"prod|production|live|main", re.IGNORECASE)
_SANDBOX_ALIAS = re.compile(r"sandbox|sbx|scratch|dev|test|uat|staging|qa",
                            re.IGNORECASE)
# In-file gate presence -- presence only, never a judgement of sufficiency.
_GATE_MARKER = re.compile(
    r"typed[_-]?phrase|require[_-]?typed|def\s+gate|import\s+gates|"
    r"from\s+\S*gates|four[_-]?eyes|safe[_-]?write|confirm[_-]?phrase|"
    r"approval|gated", re.IGNORECASE)

# Tier vocabulary, ordered by severity.
TIERS = ["none", "read-only", "guarded-write", "raw-write", "raw-write-prod"]
_RANK = {t: i for i, t in enumerate(TIERS)}


def classify_env(line: str) -> str:
    """prod / sandbox / unknown from a `--target-org` alias. Unknown is treated as
    prod for ranking (fail-safe), but reported honestly as 'unknown'."""
    m = _TARGET_ORG.search(line)
    if not m:
        return "none"
    alias = m.group(1)
    if _PROD_ALIAS.search(alias):
        return "prod"
    if _SANDBOX_ALIAS.search(alias):
        return "sandbox"
    return "unknown"


def hit_tier(kind: str, guarded: bool, env: str) -> str:
    """The tier a single hit contributes. A guarded write ranks *below* a bare
    write; unknown env ranks as prod."""
    if kind == "read":
        return "read-only"
    if guarded:
        return "guarded-write"
    if env in ("prod", "unknown"):
        return "raw-write-prod"
    return "raw-write"


def _changed_paths(target: Path) -> set[str] | None:
    """Relpaths that are untracked or modified (not clean, not ignored), or None
    for a non-git project. Read-only; `--no-optional-locks` so we never touch the
    scanned repo's index."""
    if not is_git_repo(target):
        return None
    raw = run_git(target, NO_OPTIONAL_LOCKS, "status", "-z", "--porcelain")
    changed: set[str] = set()
    records = raw.split("\0")
    i = 0
    while i < len(records):
        rec = records[i]
        i += 1
        if len(rec) < 4:
            continue
        xy, path = rec[:2], rec[3:]
        if "R" in xy or "C" in xy:      # rename/copy carries a second path record
            i += 1
        changed.add(path)
    return changed


def scan(target: Path) -> dict:
    target = Path(target)
    scope = Scope(target)
    changed = _changed_paths(target)
    is_git = changed is not None

    hits: list[dict] = []
    by_family: dict[str, int] = {}
    for path in scope_iter(target, scope):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        gate_in_file = bool(_GATE_MARKER.search(text))
        relpath = rel(path, target)
        for i, line in enumerate(text.splitlines(), 1):
            for family, kind, env_sensitive, rx, canon in _COMPILED:
                if not rx.search(line):
                    continue
                env = classify_env(line) if env_sensitive else "none"
                guarded = gate_in_file and kind == "write"
                tier = hit_tier(kind, guarded, env)
                hits.append({
                    "family": family, "signal": canon, "path": relpath,
                    "line": i, "kind": kind, "env": env, "guarded": guarded,
                    "tier": tier,
                })
                by_family[family] = by_family.get(family, 0) + 1
                break  # one signal per line is enough to flag it

    # Per-project tier = the loudest hit.
    project_tier = "none"
    for h in hits:
        if _RANK[h["tier"]] > _RANK[project_tier]:
            project_tier = h["tier"]

    # --- Task B: the uncommitted-critical alarm ------------------------------
    # A guarded-write-or-worse file that is untracked or uncommitted-dirty has no
    # provenance behind the code that mutates the outside world. Non-git => every
    # such file is uncommitted by definition.
    critical: dict[str, dict] = {}
    for h in hits:
        if _RANK[h["tier"]] < _RANK["guarded-write"]:
            continue
        p = h["path"]
        uncommitted = (changed is None) or (p in changed)
        if not uncommitted:
            continue
        state = "no-git" if changed is None else (
            "untracked" if p in changed else "dirty")
        cur = critical.get(p)
        if cur is None or _RANK[h["tier"]] > _RANK[cur["tier"]]:
            critical[p] = {"path": p, "tier": h["tier"], "git_state": state}

    kept, truncated, true_count = capped(hits, HIT_CAP)
    uncommitted_critical = sorted(
        critical.values(), key=lambda c: (-_RANK[c["tier"]], c["path"]))
    return {
        "project": target.name,
        "is_git": is_git,
        "tier": project_tier,
        "tier_rank": _RANK[project_tier],
        "hit_count": true_count,
        "by_family": by_family,
        "hits": kept,
        "truncated": truncated,
        "hit_cap": HIT_CAP,
        "uncommitted_critical": uncommitted_critical,
        "has_uncommitted_critical": bool(uncommitted_critical),
        "scope": scope.report(),
    }


def scope_iter(target: Path, scope: Scope):
    """Yield in-scope scan files. Split out so the walk is trivially testable."""
    from ..common import iter_files
    for path in iter_files(target, suffixes=_SCAN_SUFFIXES):
        if scope.skip(path):
            continue
        yield path
