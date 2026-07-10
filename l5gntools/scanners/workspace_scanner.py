"""workspace_scanner -- AST code inventory for a project.

Merges the old workspace_scanner v1/v2/v5 into one. Excludes vendored code
(venv/site-packages/models) so counts reflect your own work.
"""
from __future__ import annotations

import ast
from pathlib import Path

from ..common import iter_files, is_vendored, rel

NAME = "workspace_scanner"
DESCRIPTION = "AST code inventory: per-file classes, functions and imports."
ESTATE_LEVEL = False


def _module_imports(tree: ast.AST) -> list[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return sorted(names)


def scan(target: Path) -> dict:
    modules: list[dict] = []
    classes: list[str] = []
    n_files = n_classes = n_funcs = 0
    vendored_files = 0

    for path in iter_files(target, suffixes=(".py",)):
        if is_vendored(path):
            vendored_files += 1
            continue
        n_files += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except (SyntaxError, ValueError):
            modules.append({"path": rel(path, target), "error": "parse_failed"})
            continue
        mod_classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        mod_funcs = [n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        classes.extend(mod_classes)
        n_classes += len(mod_classes)
        n_funcs += len(mod_funcs)
        modules.append({
            "path": rel(path, target),
            "classes": mod_classes,
            "functions": len(mod_funcs),
            "imports": _module_imports(tree),
        })

    modules.sort(key=lambda m: m["path"])
    top = sorted({c for c in classes})[:40]
    return {
        "project": target.name,
        "py_files": n_files,
        "vendored_py_files_excluded": vendored_files,
        "classes": n_classes,
        "functions": n_funcs,
        "top_classes": top,
        "modules": modules,
    }
