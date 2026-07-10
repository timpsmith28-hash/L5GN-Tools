"""import_scanner -- import surface for a project, split stdlib / third-party / local."""
from __future__ import annotations

import ast
import sys
from collections import Counter
from pathlib import Path

from ..common import is_vendored, iter_files

NAME = "import_scanner"
DESCRIPTION = "Import census: stdlib vs third-party vs local module usage."
ESTATE_LEVEL = False


def _stdlib_names() -> set[str]:
    names = set(getattr(sys, "stdlib_module_names", set()))
    # A few always-present extras across versions.
    names |= {"__future__", "typing_extensions"}
    return names


def scan(target: Path) -> dict:
    stdlib = _stdlib_names()
    # Local top-level module/package names = python files/dirs at project root.
    local: set[str] = {p.stem for p in target.glob("*.py")}
    local |= {p.name for p in target.iterdir() if p.is_dir()}

    counts: Counter[str] = Counter()
    third_party: Counter[str] = Counter()
    files = 0
    for path in iter_files(target, suffixes=(".py",)):
        if is_vendored(path):
            continue
        files += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError):
            continue
        seen: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                seen |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                seen.add(node.module.split(".")[0])
        for name in seen:
            counts[name] += 1
            if name not in stdlib and name not in local:
                third_party[name] += 1

    return {
        "project": target.name,
        "py_files_scanned": files,
        "third_party": dict(third_party.most_common()),
        "top_imports": dict(counts.most_common(25)),
    }
