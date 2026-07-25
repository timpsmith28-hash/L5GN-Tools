"""duplicate_finder -- locates the same file appearing across multiple projects.

Two views:
* identical content (sha1) shared by >= 2 projects -- true copy-paste drift.
* same filename shared by >= 2 projects, each group **labelled** by whether the
  copies are byte-identical or divergent (governance Task D):
    - `identical`  -- same basename, same sha1 everywhere: a genuine copy, a
      shared-toolkit or drift candidate.
    - `divergent`  -- same basename, different content: coincidental or forked.
  The file is hashed **once** and the digest feeds both views -- no second pass.
"""
from __future__ import annotations

from ..contract import SAFE

import hashlib
from collections import defaultdict
from pathlib import Path

from ..common import iter_files, rel
from ._scope import Scope

NAME = "duplicate_finder"
DESCRIPTION = "Finds identical / same-named files reused across sibling projects."
ESTATE_LEVEL = True
SAFETY = SAFE

_SUFFIXES = (".py", ".json", ".sh")
_SKIP_NAMES = {"__init__.py"}


def _sha1(path: Path) -> str | None:
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return None


def label_shared(digests: list[str | None]) -> str:
    """Label a same-basename group by the content behind it. Pure and testable.

    `identical` only when every location hashed and all digests agree; a group
    with an unreadable file (None digest) cannot be proven identical, so it is
    `divergent` -- the honest, over-reporting direction."""
    if not digests or any(d is None for d in digests):
        return "divergent"
    return "identical" if len(set(digests)) == 1 else "divergent"


def scan_estate(projects: list[Path]) -> dict:
    by_hash: dict[str, list[str]] = defaultdict(list)
    # filename -> {project: digest} (one representative per project; identical
    # copies within a project do not change the cross-project verdict).
    by_name: dict[str, dict[str, str | None]] = defaultdict(dict)

    for proj in projects:
        scope = Scope(proj)
        for path in iter_files(proj, suffixes=_SUFFIXES):
            if scope.skip(path) or path.name in _SKIP_NAMES:
                continue
            digest = _sha1(path)                       # hashed once, used twice
            by_name[path.name].setdefault(proj.name, digest)
            if digest:
                by_hash[digest].append(f"{proj.name}/{rel(path, proj)}")

    identical = [
        {"sha1": h[:12], "count": len(locs), "locations": sorted(locs)}
        for h, locs in by_hash.items()
        if len({loc.split('/')[0] for loc in locs}) >= 2
    ]
    identical.sort(key=lambda d: d["count"], reverse=True)

    shared_names = []
    for n, per_proj in by_name.items():
        if len(per_proj) < 2:
            continue
        shared_names.append({
            "filename": n,
            "projects": sorted(per_proj),
            "content": label_shared(list(per_proj.values())),
        })
    # Divergent-but-shared names are the more interesting signal (a forked copy),
    # so surface those first, then by breadth.
    shared_names.sort(key=lambda d: (d["content"] != "divergent",
                                     -len(d["projects"])))

    return {
        "identical_content_groups": len(identical),
        "shared_filename_groups": len(shared_names),
        "shared_filename_divergent": sum(1 for s in shared_names
                                         if s["content"] == "divergent"),
        "identical_content": identical[:100],
        "shared_filenames": shared_names[:100],
    }
