"""Scanners must import stdlib + the local package only, so they run against
any sibling project regardless of that project's virtual-env.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

from l5gntools.registry import SCANNERS

_ALLOWED = set(getattr(sys, "stdlib_module_names", set())) | {
    "l5gntools", "__future__", "typing_extensions",
}


def _scan_source(path: Path) -> list[str]:
    out: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top not in _ALLOWED:
                    out.append(f"{path.name}:{node.lineno}: non-stdlib import '{top}'")
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue  # relative import within the package -- fine
            top = (node.module or "").split(".")[0]
            if top and top not in _ALLOWED:
                out.append(f"{path.name}:{node.lineno}: non-stdlib import '{top}'")
    return out


def run() -> list[str]:
    v: list[str] = []
    for mod in SCANNERS:
        src = getattr(mod, "__file__", None)
        if src:
            v.extend(_scan_source(Path(src)))
    return v
