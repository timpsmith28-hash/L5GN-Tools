"""file_census -- what files are actually in a project, and which of them are not
safely in git.

No other scanner answers "what is in this folder". `workspace_scanner` sees
`.py`, `doc_census` sees markdown, `bloat_audit` flags rather than lists, and
`duplicate_finder` reports only collisions. The question this exists for is the
one asked before archiving a dormant repo or dropping code out of L5GN-Castle:
**what is in there that is not safely in git?** A file list is useful; a file
list that names the at-risk set is what stops you deleting something you cannot
get back.

Three tiers, because the working set and the mass need different treatment and a
naive census across eleven repos plus a 90MB model tree would make `estate.json`
unusable:

* **Tier 1 -- `directories`.** A rollup per directory, always, no cap. Depth-capped
  at :data:`DEPTH_CAP` levels; anything deeper folds into its capped ancestor,
  which is then marked ``depth_collapsed``. Counts are *direct* files only (the
  files immediately in that directory), so a tree renderer sums descendants
  itself and no byte is counted twice. The invariant, asserted by the tester:
  ``sum(directories.files) + sum(mass.files) == summary.total_files``.
* **Tier 2 -- `files`.** Per-file entries for the working set: non-vendored,
  non-ignored. Capped at :data:`FILE_CAP` per project, path-sorted so the kept
  slice is deterministic and browsable. When capped, ``truncated`` is true and
  ``file_count`` carries the true number. **Never a silent truncation.**
* **Tier 3 -- `mass`.** Vendored trees, git-ignored trees and `.git` itself:
  rollup only, never per-file. Each entry says how big it is and *why* it was
  excluded, so a reader can see the mass without paying for it.

Plus two headline sets emitted in full:

* ``outliers`` -- the 20 largest files in the project, whatever tier they fall in.
* ``at_risk`` -- **untracked and not ignored**. This is the point of the scanner.
  It is never truncated, because a truncated at-risk list is worse than none: it
  reads as complete.

Two deliberate design biases, both stated so a later reader can disagree with
them on purpose rather than by accident:

1. **`at_risk` over-reports rather than under-reports.** Anything git does not
   list as tracked and does not report as ignored is called ``untracked``. A
   false positive costs a glance; a false negative costs a file.
2. **`at_risk` inside a Tier 3 tree is a rollup, not a truncation.** An
   unprotected vendored tree appears as one entry carrying its *exact* file count
   and byte total (``"rollup": true``) rather than 8,000 filenames. Nothing is
   hidden and no count is approximate -- and "this entire tree is unprotected" is
   the more useful sentence anyway.

Read-only and stdlib-only, like every scanner. It shells out to git twice per
project -- never per file -- and both invocations carry ``--no-optional-locks``,
because `git status` will otherwise refresh `.git/index`: a write inside a
scanned folder, which the contract forbids (see `common.git_argv`).
"""
from __future__ import annotations

from ..contract import SAFE

import heapq
import os
from datetime import datetime, timezone
from pathlib import Path

from ..common import NO_OPTIONAL_LOCKS, is_git_repo, is_ignored_dir, rel, run_git

NAME = "file_census"
DESCRIPTION = "Three-tier file inventory naming the untracked, un-ignored at-risk set."
ESTATE_LEVEL = False
SAFETY = SAFE

#: Directory depth that still earns its own Tier 1 entry. Deeper folds upward.
DEPTH_CAP = 4
#: Per-file Tier 2 entries kept per project before `truncated` is set.
FILE_CAP = 2000
#: How many largest-files-in-the-project to report, across all tiers.
OUTLIER_COUNT = 20

_ROOT_KEY = "."
_NO_EXT = "(none)"


# --- helpers -----------------------------------------------------------------
def _iso(timestamp: float) -> str:
    """A file mtime as a local-offset ISO timestamp, seconds precision."""
    return (datetime.fromtimestamp(timestamp, tz=timezone.utc)
            .astimezone().isoformat(timespec="seconds"))


def _ext_of(name: str) -> str:
    return os.path.splitext(name)[1].lower() or _NO_EXT


def _basename(relpath: str) -> str:
    """Last segment of a census relpath. Census paths are always '/'-separated
    (built by string join, not os.path), so this must not use os.path.basename,
    which would not split on '/' when run on Windows."""
    return relpath.rsplit("/", 1)[-1]


def _capped(reldir: str) -> tuple[str, bool]:
    """Map a project-relative directory to the Tier 1 key that holds it.

    Returns ``(key, collapsed)`` where ``collapsed`` is true when ``reldir`` sat
    below :data:`DEPTH_CAP` and its contents were folded into an ancestor.
    """
    parts = [p for p in reldir.split("/") if p]
    if len(parts) <= DEPTH_CAP:
        return (reldir or _ROOT_KEY), False
    return "/".join(parts[:DEPTH_CAP]), True


def parse_status_z(raw: str) -> tuple[set[str], set[str]]:
    """Parse ``git status -z --porcelain --ignored`` into ignored dirs and files.

    Pure and separately testable. ``-z`` is not a nicety: without it git quotes
    and escapes paths containing spaces or non-ASCII, and a census that silently
    mangles the one filename you were worried about is worse than no census.

    Rename and copy records carry a *second* NUL-terminated field (the source
    path), which must be consumed or every subsequent record is misread by one.
    """
    ignored_dirs: set[str] = set()
    ignored_files: set[str] = set()
    records = raw.split("\0")
    i = 0
    while i < len(records):
        record = records[i]
        i += 1
        if len(record) < 4:
            continue
        xy, path = record[:2], record[3:]
        if xy == "!!":
            if path.endswith("/"):
                ignored_dirs.add(path.rstrip("/"))
            else:
                ignored_files.add(path)
        elif "R" in xy or "C" in xy:
            i += 1  # the source path of a rename/copy is its own record
    return ignored_dirs, ignored_files


def _git_lookup(target: Path) -> dict | None:
    """One `ls-files` and one `status` per project, parsed into a lookup.

    ``None`` when ``target`` is not a git repository -- the caller then reports
    ``git: null`` for every file rather than guessing.

    Both invocations pass ``--no-optional-locks`` explicitly. `run_git` injects
    it for read-only subcommands anyway, and the injection is idempotent; it is
    written out here so the reason this scanner cannot touch `.git/index` is
    visible at the call site rather than three files away.

    ``--untracked-files`` is deliberately left at its default (``normal``), which
    collapses a wholly-ignored directory to a single ``.venv/`` record. ``-uall``
    would expand it into thousands -- the very cost this scanner exists to avoid.
    Untracked files need no enumeration here: anything neither tracked nor
    ignored is untracked by elimination.
    """
    if not is_git_repo(target):
        return None

    # Paths in --porcelain output are relative to the repository root, which is
    # not necessarily the scan target. Compute the offset rather than assume.
    top = run_git(target, "rev-parse", "--show-toplevel")
    prefix = ""
    if top:
        offset = rel(target.resolve(), Path(top).resolve())
        if offset not in ("", "."):
            prefix = offset.rstrip("/") + "/"

    def to_target(path: str) -> str | None:
        if not prefix:
            return path
        return path[len(prefix):] if path.startswith(prefix) else None

    tracked = {p for p in
               (to_target(x) for x in run_git(target, "ls-files", "-z").split("\0") if x)
               if p}
    raw = run_git(target, NO_OPTIONAL_LOCKS, "status", "-z", "--porcelain", "--ignored")
    ignored_dirs_raw, ignored_files_raw = parse_status_z(raw)
    ignored_dirs = {p for p in (to_target(x) for x in ignored_dirs_raw) if p}
    ignored_files = {p for p in (to_target(x) for x in ignored_files_raw) if p}
    return {"tracked": tracked, "ignored_dirs": ignored_dirs,
            "ignored_files": ignored_files}


def _under_ignored_dir(relpath: str, ignored_dirs: set[str]) -> bool:
    if not ignored_dirs:
        return False
    parts = relpath.split("/")
    for i in range(1, len(parts)):
        if "/".join(parts[:i]) in ignored_dirs:
            return True
    return False


def status_of(relpath: str, git: dict | None) -> str | None:
    """``tracked`` / ``untracked`` / ``ignored``, or ``None`` outside a git repo.

    The fallback is ``untracked`` on purpose: see the module docstring's first
    design bias. Anything git has not claimed as tracked and has not called
    ignored is treated as unprotected.
    """
    if git is None:
        return None
    if relpath in git["tracked"]:
        return "tracked"
    if relpath in git["ignored_files"] or _under_ignored_dir(relpath, git["ignored_dirs"]):
        return "ignored"
    return "untracked"


def _classify_dir(name: str, child_rel: str, git: dict | None) -> str | None:
    """Why this directory is Tier 3 mass, or ``None`` if it is working set.

    git's own opinion wins over ours: a directory the repo ignores is reported as
    ``ignored`` even when it also looks vendored, because that is the more
    accurate answer to "why is this not in the working set".
    """
    if name == ".git":
        return "git-internal"
    if git is not None and child_rel in git["ignored_dirs"]:
        return "ignored"
    if is_ignored_dir(name):
        return "vendored"
    return None


# --- the scan ----------------------------------------------------------------
def scan(target: Path) -> dict:
    target = Path(target)
    git = _git_lookup(target)

    directories: dict[str, dict] = {}
    files: list[dict] = []
    mass: list[dict] = []
    at_risk: list[dict] = []
    loose_ignored: dict[str, dict] = {}
    outliers: list[tuple] = []          # bounded min-heap of (bytes, path, tier)
    # Basenames of working-set files that did NOT fit inside FILE_CAP. The S4
    # filename cross-reference matches on basename alone, so carrying just the
    # basenames past the cap costs a few KB and removes the blind spot that a
    # truncated `files` list would otherwise open in the strongest automatic
    # link signal the system has. Empty for every project under the cap.
    beyond_cap: set[str] = set()

    counts = {"total_files": 0, "total_bytes": 0, "ws_files": 0, "ws_bytes": 0,
              "mass_files": 0, "mass_bytes": 0, "risk_files": 0, "risk_bytes": 0}

    def note_outlier(size: int, path: str, tier: str) -> None:
        if len(outliers) < OUTLIER_COUNT:
            heapq.heappush(outliers, (size, path, tier))
        elif size > outliers[0][0]:
            heapq.heapreplace(outliers, (size, path, tier))

    def touch_dir(key: str, collapsed: bool) -> dict:
        entry = directories.get(key)
        if entry is None:
            entry = {"path": key, "files": 0, "bytes": 0, "ext": {},
                     "depth_collapsed": False}
            directories[key] = entry
        if collapsed:
            entry["depth_collapsed"] = True
        return entry

    def roll_up_mass(root: Path, root_rel: str, reason: str) -> None:
        """Summarise a whole Tier 3 subtree without emitting a single file entry."""
        n_files = n_bytes = 0
        risk_files = risk_bytes = 0
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                n_files += 1
                n_bytes += size
                relpath = rel(path, target)
                note_outlier(size, relpath, "mass")
                # Only a *vendored* tree can hold at-risk files. An ignored tree
                # is ignored by definition, and `.git` is git's own storage --
                # calling either one unprotected would be noise that drowns the
                # signal this list exists to carry.
                if reason == "vendored" and status_of(relpath, git) == "untracked":
                    risk_files += 1
                    risk_bytes += size
        entry = {"path": root_rel, "files": n_files, "bytes": n_bytes,
                 "reason": reason}
        mass.append(entry)
        counts["mass_files"] += n_files
        counts["mass_bytes"] += n_bytes
        counts["total_files"] += n_files
        counts["total_bytes"] += n_bytes
        if risk_files:
            at_risk.append({"path": root_rel, "files": risk_files,
                            "bytes": risk_bytes, "rollup": True, "reason": reason})
            counts["risk_files"] += risk_files
            counts["risk_bytes"] += risk_bytes

    for dirpath, dirnames, filenames in os.walk(target):
        reldir = rel(Path(dirpath), target)
        reldir = "" if reldir == "." else reldir

        # Split mass subtrees off before descending, so the working-set walk
        # never enters a venv and the mass is paid for exactly once.
        keep: list[str] = []
        for name in sorted(dirnames):
            child_rel = f"{reldir}/{name}" if reldir else name
            reason = _classify_dir(name, child_rel, git)
            if reason is None:
                keep.append(name)
            else:
                roll_up_mass(Path(dirpath) / name, child_rel, reason)
        dirnames[:] = keep

        key, collapsed = _capped(reldir)
        entry = touch_dir(key, collapsed)

        for name in sorted(filenames):
            path = Path(dirpath) / name
            try:
                stat = path.stat()
            except OSError:
                continue
            size = stat.st_size
            relpath = f"{reldir}/{name}" if reldir else name
            counts["total_files"] += 1
            counts["total_bytes"] += size
            state = status_of(relpath, git)

            if state == "ignored":
                # A loose ignored file is mass too, but it has no tree of its own.
                # Group by parent so it reports as "the ignored files in config/"
                # rather than as a synthetic bucket with an invented path.
                bucket = loose_ignored.setdefault(key, {
                    "path": key, "files": 0, "bytes": 0,
                    "reason": "ignored", "partial": True})
                bucket["files"] += 1
                bucket["bytes"] += size
                counts["mass_files"] += 1
                counts["mass_bytes"] += size
                note_outlier(size, relpath, "mass")
                continue

            note_outlier(size, relpath, "working_set")
            entry["files"] += 1
            entry["bytes"] += size
            ext = _ext_of(name)
            entry["ext"][ext] = entry["ext"].get(ext, 0) + 1
            counts["ws_files"] += 1
            counts["ws_bytes"] += size

            if len(files) < FILE_CAP:
                files.append({"path": relpath, "bytes": size,
                              "mtime": _iso(stat.st_mtime), "git": state})
            else:
                beyond_cap.add(name)
            if state == "untracked":
                at_risk.append({"path": relpath, "bytes": size,
                                "mtime": _iso(stat.st_mtime)})
                counts["risk_files"] += 1
                counts["risk_bytes"] += size

    mass.extend(loose_ignored.values())
    mass.sort(key=lambda m: (-m["bytes"], m["path"]))
    ranked = sorted(outliers, key=lambda o: (-o[0], o[1]))

    summary = {
        "total_files": counts["total_files"],
        "total_bytes": counts["total_bytes"],
        "working_set": {"files": counts["ws_files"], "bytes": counts["ws_bytes"]},
        "mass": {"files": counts["mass_files"], "bytes": counts["mass_bytes"]},
        "at_risk": {"files": counts["risk_files"], "bytes": counts["risk_bytes"]},
        "largest": ranked[0][1] if ranked else None,
    }

    return {
        "project": target.name,
        "is_git": git is not None,
        "summary": summary,
        # The true working-set count, always -- `files` may hold fewer.
        "file_count": counts["ws_files"],
        "truncated": counts["ws_files"] > FILE_CAP,
        "file_cap": FILE_CAP,
        "directories": sorted(directories.values(), key=lambda d: d["path"]),
        "files": files,
        # Basenames of the working-set files `files` had no room for, MINUS any
        # already recoverable from `files` itself. Union this with the basenames
        # of `files` to get the project's complete basename set even when
        # `truncated` is true -- which is what the S4 filename cross-reference
        # consumes. Always present; empty when not truncated.
        #
        # The subtraction is what makes this cheap. On L5GN-Castle the raw
        # beyond-cap set is 1,764 names of which 1,627 already appear in the
        # emitted slice (repo trees repeat basenames heavily -- __init__.py,
        # index.md, per-module names). Storing only the 137 genuinely
        # unrecoverable ones is an order of magnitude smaller and carries
        # exactly the same information.
        "basenames_beyond_cap": sorted(
            beyond_cap - {_basename(f["path"]) for f in files}),
        "mass": mass,
        "outliers": [{"path": p, "bytes": b, "tier": t} for b, p, t in ranked],
        "at_risk": at_risk,
        # Nothing is in version control at all, so "untracked" is not a
        # distinction this project can make. Said plainly rather than reported as
        # an empty at-risk list, which would read as reassurance.
        "at_risk_note": (None if git is not None else
                         "not a git repository -- no file here is in version control"),
    }
