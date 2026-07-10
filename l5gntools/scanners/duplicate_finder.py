"""duplicate_finder -- locates the same file appearing across multiple projects.

Two views:
* identical content (sha1) shared by >= 2 projects -- true copy-paste drift.
* same filename shared by >= 2 projects -- candidate for a shared tool.
"""
from __future__ import annotations

from ..contract import SAFE

import hashlib
from collections import defaultdict
from pathlib import Path

from ..common import is_vendored, iter_files, rel

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


def scan_estate(projects: list[Path]) -> dict:
    by_hash: dict[str, list[str]] = defaultdict(list)
    by_name: dict[str, set[str]] = defaultdict(set)

    for proj in projects:
        for path in iter_files(proj, suffixes=_SUFFIXES):
            if is_vendored(path) or path.name in _SKIP_NAMES:
                continue
            by_name[path.name].add(proj.name)
            digest = _sha1(path)
            if digest:
                by_hash[digest].append(f"{proj.name}/{rel(path, proj)}")

    identical = [
        {"sha1": h[:12], "count": len(locs), "locations": sorted(locs)}
        for h, locs in by_hash.items()
        if len({loc.split('/')[0] for loc in locs}) >= 2
    ]
    identical.sort(key=lambda d: d["count"], reverse=True)

    shared_names = [
        {"filename": n, "projects": sorted(ps)}
        for n, ps in by_name.items() if len(ps) >= 2
    ]
    shared_names.sort(key=lambda d: len(d["projects"]), reverse=True)

    return {
        "identical_content_groups": len(identical),
        "shared_filename_groups": len(shared_names),
        "identical_content": identical[:100],
        "shared_filenames": shared_names[:100],
    }
