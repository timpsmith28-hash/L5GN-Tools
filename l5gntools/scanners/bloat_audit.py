"""bloat_audit -- flags committed venvs / bundled deps / large tracked files."""
from __future__ import annotations

from pathlib import Path

from ..common import is_git_repo, run_git

NAME = "bloat_audit"
DESCRIPTION = "Flags tracked venvs/site-packages/models, big files, missing .gitignore."
ESTATE_LEVEL = False

_BLOAT_MARKERS = ("site-packages/", "/venv/", "venv/", ".venv/", "node_modules/",
                  "/models/", "__pycache__/")
_BIG_BYTES = 5_000_000


def scan(target: Path) -> dict:
    result: dict = {
        "project": target.name,
        "is_git": is_git_repo(target),
        "has_gitignore": (target / ".gitignore").exists(),
    }
    if not result["is_git"]:
        return result

    tracked = [ln for ln in run_git(target, "ls-files").splitlines() if ln]
    result["tracked_files"] = len(tracked)

    bloat = [f for f in tracked
             if any(m in ("/" + f + "/").replace("//", "/") or m in f
                    for m in _BLOAT_MARKERS)]
    result["tracked_bloat_paths"] = len(bloat)
    result["tracked_bloat_sample"] = bloat[:15]

    big: list[dict] = []
    for f in tracked:
        fp = target / f
        try:
            size = fp.stat().st_size
        except OSError:
            continue
        if size >= _BIG_BYTES:
            big.append({"path": f, "mb": round(size / 1_000_000, 1)})
    big.sort(key=lambda b: b["mb"], reverse=True)
    result["large_tracked_files"] = big[:15]

    flags: list[str] = []
    if not result["has_gitignore"]:
        flags.append("no .gitignore")
    if bloat:
        flags.append(f"{len(bloat)} vendored/bloat paths tracked in git")
    if big:
        flags.append(f"{len(big)} file(s) >= 5MB tracked in git")
    result["flags"] = flags
    return result
