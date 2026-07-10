"""Scanners must not write to disk. The only sanctioned writer is
common.write_json (which is confined to the data dir). This audits every
scanner source file for filesystem-mutating calls.
"""
from __future__ import annotations

import ast
from pathlib import Path

from l5gntools.registry import SCANNERS

# Unambiguous filesystem writers/mutators. (str.replace etc. deliberately absent.)
_FORBIDDEN_ATTRS = {
    "write_text", "write_bytes", "mkdir", "makedirs", "rmdir", "removedirs",
    "unlink", "remove", "rmtree", "touch", "symlink_to", "hardlink_to",
}


def _scan_source(path: Path) -> list[str]:
    out: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _FORBIDDEN_ATTRS:
            out.append(f"{path.name}:{node.lineno}: forbidden write call '.{func.attr}(...)'")
        if isinstance(func, ast.Name) and func.id == "open":
            mode = ""
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            if any(c in mode for c in ("w", "a", "x", "+")):
                out.append(f"{path.name}:{node.lineno}: open() in write mode {mode!r}")
    return out


def run() -> list[str]:
    v: list[str] = []
    for mod in SCANNERS:
        src = getattr(mod, "__file__", None)
        if src:
            v.extend(_scan_source(Path(src)))
    return v
