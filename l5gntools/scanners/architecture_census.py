"""architecture_census -- the toolkit's own shape, emitted as facts (DECISIONS
0030, `COWORK_BRIEF_architecture_census.md`).

`ARCHITECTURE.md` is written from DECISIONS, in the present tense, as though
what was decided were what was built. This scanner is the other half 0030
carves out: the parts of ARCHITECTURE that are **derivable from the tree**
(which scanners exist, what the gate runs, the review app's routes, which
tables a module writes, the schema's shape, the dependency wall) stop being
asserted in prose and become a generated fact sheet instead. `report.py`
renders it to `docs/_architecture_shape.md`; `auditor_architecture_current`
refuses a stale one. Nothing here decides anything -- it reads the tree once
and writes six lists.

**AST, never regex**, per the brief's whole quality bar: a regex scan of
source text cannot distinguish "this module opens no writes" from "this
module could not be parsed", and that distinction (`status: "unparsed"`,
never a silent zero) is section 4's entire point. Every parse attempt below
either succeeds and contributes facts, or fails and is reported by name --
never swallowed.

**Grounding, unusual and worth stating (brief, "Grounding").** Every other
scanner in this registry takes a target: a project folder (`scan`) or a list
of them (`scan_estate`). This one always describes the same tree --
`common.TOOLKIT_ROOT`, this checkout -- so it needs no root, no config and no
estate. `scan_estate` still takes a `projects` argument, unused, purely to
satisfy the `ESTATE_LEVEL` contract every other estate scanner shares
(`auditor_cli_contract` requires the signature, not that the argument mean
anything). The real entry point testers should call is `census(root)`, which
takes an explicit root so a tester can point it at a small synthetic tree
(the estate-level caching defect this must not inherit -- self-scan finding
#2 -- was about an *unkeyed* cache; this scanner has no cache and no keyed
input at all, so the class of bug does not apply, but a scanner with no
input argument is exactly the shape that bug hides in if anyone ever adds
one, which is why `census()` takes `root` explicitly rather than closing
over `TOOLKIT_ROOT` silently).

**No wall-clock, anywhere.** The provenance block is `toolkit_git_info()`
alone -- `{"commit": ..., "dirty": ...}` -- never `now_iso()`. Every other
estate scan in this toolkit stamps `generated_at` beside it; this one
deliberately does not, because Task 2's determinism tester diffs the *whole*
payload byte-for-byte across two runs with no field excluded, and the
brief is explicit that a real timestamp may exist only "outside the compared
region." Leaving it out entirely is simpler than drawing that line correctly
twice (here and in the tester) and getting it right once is enough.
"""
from __future__ import annotations

import ast
import os
import re
import sqlite3
from pathlib import Path

from ..contract import SAFE
from ..common import TOOLKIT_ROOT, rel, toolkit_git_info

NAME = "architecture_census"
DESCRIPTION = ("The toolkit's own shape, generated from the tree: registered "
              "scanners, gate composition, the review app's route table, "
              "per-module DB write targets, schema shape (with the "
              "schema/schema_frozen delta), and the dependency wall. "
              "Read-only, stdlib-only; feeds the do-not-edit render at "
              "docs/_architecture_shape.md (DECISIONS 0030).")
ESTATE_LEVEL = True
SAFETY = SAFE

# --- shared parse helper -----------------------------------------------------


def _parse_py(path: Path):
    """(tree, None) on success, (None, reason) on any failure to read or
    parse. Never raises -- every caller turns a `reason` into an
    `{"module": ..., "status": "unparsed", "reason": ...}` fact rather than
    dropping the file or counting it as having nothing to report."""
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    try:
        tree = ast.parse(src, filename=path.name)
    except SyntaxError as exc:
        return None, f"SyntaxError: {exc}"
    return tree, None


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


# --- section 1: registered scanners ------------------------------------------


def _scanners_section() -> list[dict]:
    # Imported lazily: this module is itself one of `registry.SCANNERS`, and
    # `registry` imports every scanner module (including this one) before its
    # own `SCANNERS` name exists -- a module-level `from ..registry import
    # SCANNERS` here would be a circular import at load time. By the time
    # this function actually runs, the registry has finished loading.
    #
    # Deliberately relative to `TOOLKIT_ROOT`, never the `root` a caller
    # passed in: `registry.SCANNERS` is the real, installed toolkit's
    # registry regardless of which tree `census()` was asked to describe --
    # a fixture root has no scanners of its own to report, and computing
    # `rel()` against a fixture root would make every module path fall back
    # to an absolute one (the exact leak this scanner exists to catch).
    from .. import registry

    out = []
    for mod in registry.SCANNERS:
        src = getattr(mod, "__file__", None)
        module_path = rel(Path(src).resolve(), TOOLKIT_ROOT) if src else None
        out.append({
            "name": mod.NAME,
            "description": mod.DESCRIPTION,
            "estate_level": bool(getattr(mod, "ESTATE_LEVEL", False)),
            "safety": getattr(mod, "SAFETY", None),
            "module": module_path,
        })
    out.sort(key=lambda e: e["name"])
    return out


# --- section 2: gate composition ---------------------------------------------


def _string_list_assign(tree: ast.Module, name: str) -> list[str] | None:
    """The string list literal bound to module-level `name`. Handles both
    `NAME = [...]` (``Assign``) and `NAME: list[str] = [...]` (``AnnAssign``)
    -- `verify.py` uses the annotated form for both `AUDITORS` and
    `TESTERS`."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if not any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                continue
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            if not (isinstance(node.target, ast.Name) and node.target.id == name):
                continue
            value = node.value
        else:
            continue
        if not isinstance(value, ast.List):
            continue
        vals = []
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                vals.append(elt.value)
        return vals
    return None


def _gate_section(root: Path, unparsed: list[dict]) -> dict:
    relpath = "verify.py"
    tree, err = _parse_py(root / relpath)
    if err:
        unparsed.append({"module": relpath, "status": "unparsed", "reason": err})
        return {"auditors": [], "auditor_count": 0, "testers": [], "tester_count": 0}
    auditors = _string_list_assign(tree, "AUDITORS") or []
    testers = _string_list_assign(tree, "TESTERS") or []
    return {
        "auditors": auditors,
        "auditor_count": len(auditors),
        "testers": testers,
        "tester_count": len(testers),
    }


# --- section 3: the review app's route table ---------------------------------

_HTTP_VERBS = {"get", "post", "put", "delete", "patch"}
# Substring match on the literal dependency-check function name called in a
# route body -- `_need_vault` -> vault, `_need_estate` / `_need_curator_estate`
# -> estate (curator's gate is an estate-scoped check by construction: see
# `chronicler/review/curator_data.py` docstring, "estate-labelled by
# construction"), anything else -> none. This is a name-grounded fact, not a
# guess: it reads the identifier actually called in the function body.
_ROUTE_DEP_ORDER = ("vault", "estate")


def _route_dependency(calls: set[str]) -> str:
    for dep in _ROUTE_DEP_ORDER:
        if any(dep in c for c in calls):
            return dep
    return "none"


def _route_table_section(root: Path, unparsed: list[dict]) -> list[dict]:
    relpath = "chronicler/review/app.py"
    tree, err = _parse_py(root / relpath)
    if err:
        unparsed.append({"module": relpath, "status": "unparsed", "reason": err})
        return []

    routes: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                   and dec.func.attr in _HTTP_VERBS
                   and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "app"):
                continue
            path = None
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                path = dec.args[0].value
            calls = {n.func.id for n in ast.walk(node)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            routes.append({
                "method": dec.func.attr.upper(),
                "path": path,
                "requires": _route_dependency(calls),
            })
    routes.sort(key=lambda r: (r["path"] or "", r["method"]))
    return routes


# --- section 4: per-module DB write targets ----------------------------------

# A module "opens a DB" if its source calls one of the connection factories
# this estate actually has (`dbsafe.connect`/`connect_readonly`,
# `db.get_connection`, the local wrappers built on them) -- OR calls
# `.execute()`/`.executemany()`/`.executescript()` directly against a
# connection it was handed (the review endpoint's shape: `core.py` never
# opens its own connection, `app.py` does, and A4 lives in `core.py`). Either
# call is "this module touches a database"; the write set below is what it
# does once it has one, which may honestly be empty.
_CONNECT_NAMES = {"connect", "connect_readonly", "get_connection", "_connect"}
_EXECUTE_NAMES = {"execute", "executemany", "executescript"}
_DML = re.compile(
    r"(?i)\b(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|REPLACE\s+INTO|UPDATE|DELETE\s+FROM)"
    r"\s+[\"'`]?([A-Za-z_][A-Za-z0-9_]*)")

_SOURCE_DIRS = ("l5gntools", "chronicler")


def _iter_module_relpaths(root: Path) -> list[str]:
    out: list[str] = []
    for top in _SOURCE_DIRS:
        base = root / top
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames
                                if d != "__pycache__" and not d.startswith("."))
            for fn in sorted(filenames):
                if fn.endswith(".py"):
                    out.append(rel(Path(dirpath) / fn, root))
    return sorted(out)


def _best_effort_text(node: ast.expr) -> str | None:
    """The literal text of a SQL argument where it can be recovered without
    executing anything: a plain string constant, or an f-string's static
    fragments joined with a placeholder standing in for each interpolated
    part (so ``f"UPDATE {table} SET x=?"`` reads as ``UPDATE {} SET x=?`` --
    close enough to classify the *verb*, honest about not knowing the
    *table* when the table itself is the interpolated part). Anything else
    (a bare name referencing a module constant, a file read, a
    concatenation of non-literal parts) returns ``None`` -- unresolved,
    never guessed."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                parts.append(v.value)
            else:
                parts.append("{}")
        return "".join(parts)
    return None


def _module_writes(tree: ast.Module) -> tuple[bool, set[str], list[int]]:
    opens_db = False
    tables: set[str] = set()
    unresolved_lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in _CONNECT_NAMES:
            opens_db = True
        elif name in _EXECUTE_NAMES:
            opens_db = True
            if not node.args:
                continue
            text = _best_effort_text(node.args[0])
            if text is None:
                # The SQL text is not recoverable at all (a bare name
                # referencing a module constant, file contents, ...): a
                # write may be happening here and this scanner cannot
                # statically say to which table. Reported, not guessed.
                unresolved_lines.append(node.lineno)
                continue
            m = _DML.search(text)
            if m and "{}" not in m.group(1):
                tables.add(m.group(1))
            elif m:
                # The verb is static but the table name itself is the
                # interpolated part -- the write is real, the target is not
                # statically known. Reported as unresolved, not guessed.
                unresolved_lines.append(node.lineno)
            # No DML verb matched at all: a read (SELECT/PRAGMA) or DDL --
            # correctly contributes nothing.
    return opens_db, tables, sorted(unresolved_lines)


def _write_targets_section(root: Path, unparsed: list[dict]) -> list[dict]:
    facts: list[dict] = []
    for relpath in _iter_module_relpaths(root):
        tree, err = _parse_py(root / relpath)
        if err:
            unparsed.append({"module": relpath, "status": "unparsed", "reason": err})
            continue
        opens_db, tables, unresolved = _module_writes(tree)
        if not opens_db:
            continue
        facts.append({
            "module": relpath,
            "status": "ok",
            "writes": sorted(tables),
            "unresolved_write_lines": unresolved,
        })
    facts.sort(key=lambda f: f["module"])
    return facts


# --- section 5: schema shape --------------------------------------------------

_SCHEMA_FILES = {
    "schema": "chronicler/pipeline/schema.sql",
    "schema_frozen": "chronicler/pipeline/schema_frozen.sql",
}


def _introspect_schema(path: Path) -> dict | None:
    """Table/column shape via stdlib `sqlite3`, executing the DDL against an
    in-memory database and reading it back with `PRAGMA table_info` --
    deliberately not a hand-rolled SQL parser (the same "don't invent a
    second read path" instinct the brief applies to AST vs regex): sqlite3
    itself is the authority on what its own schema file means."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(path.read_text(encoding="utf-8"))
        tables = {}
        for (tname,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            # PRAGMA table_info columns: (cid, name, type, notnull,
            # dflt_value, pk) -- index 5 is pk, not 4 (that's dflt_value).
            cols = [{"name": r[1], "type": r[2], "notnull": bool(r[3]),
                     "pk": bool(r[5])}
                    for r in conn.execute(f"PRAGMA table_info({tname})")]
            tables[tname] = cols
        return tables
    finally:
        conn.close()


def _schema_section(root: Path, unparsed: list[dict]) -> dict:
    shapes: dict[str, dict] = {}
    for key, relpath in _SCHEMA_FILES.items():
        path = root / relpath
        try:
            shapes[key] = _introspect_schema(path)
        except (OSError, sqlite3.Error) as exc:
            unparsed.append({"module": relpath, "status": "unparsed",
                             "reason": f"{type(exc).__name__}: {exc}"})
            shapes[key] = None

    schema_tables = set(shapes.get("schema") or {})
    frozen_tables = set(shapes.get("schema_frozen") or {})
    return {
        "schema_sql": {
            "path": _SCHEMA_FILES["schema"],
            "tables": shapes.get("schema"),
        },
        "schema_frozen_sql": {
            "path": _SCHEMA_FILES["schema_frozen"],
            "tables": shapes.get("schema_frozen"),
        },
        "delta": {
            "only_in_schema_frozen": sorted(frozen_tables - schema_tables),
            "only_in_schema": sorted(schema_tables - frozen_tables),
        },
    }


# --- section 6: dependency wall -----------------------------------------------

# PyPI distribution name -> the name(s) it is actually imported under. A
# static table, not derivable without installing the package -- kept small
# and named so a fifth extra means a fifth line, not a fifth guess.
_PACKAGE_IMPORT_NAMES = {
    "pyyaml": ("yaml",),
    "sentence-transformers": ("sentence_transformers",),
    "playwright": ("playwright",),
    "datasette": ("datasette",),
    "fastapi": ("fastapi",),
    "uvicorn": ("uvicorn",),
    "pywebview": ("webview",),
}

_VERSION_SPLIT = re.compile(r"[<>=!~;\[\s]")


def _pkg_name(spec: str) -> str:
    return _VERSION_SPLIT.split(spec, 1)[0].strip().lower()


def _parse_optional_dependencies(root: Path, unparsed: list[dict]) -> dict[str, list[str]]:
    """`[project.optional-dependencies]` from `pyproject.toml`, read with a
    parser scoped to exactly that table's array-of-strings shape -- not a
    general TOML parser (the stdlib `tomllib` needs Python 3.11+; this
    toolkit only requires 3.10), so this is intentionally narrow rather than
    silently wrong on an older interpreter. Any line outside that shape is
    ignored, never guessed at."""
    relpath = "pyproject.toml"
    path = root / relpath
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        unparsed.append({"module": relpath, "status": "unparsed",
                         "reason": f"{type(exc).__name__}: {exc}"})
        return {}

    extras: dict[str, list[str]] = {}
    in_table = False
    key = None
    buf = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_table = stripped == "[project.optional-dependencies]"
            continue
        if not in_table or not stripped or stripped.startswith("#"):
            continue
        if key is None:
            m = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*(.*)$", stripped)
            if not m:
                continue
            key, rest = m.group(1), m.group(2)
            buf = rest
        else:
            buf += " " + stripped
        if "]" in buf:
            inner = buf[buf.index("[") + 1: buf.rindex("]")]
            specs = [s.strip().strip("'\"") for s in inner.split(",") if s.strip()]
            extras[key] = [_pkg_name(s) for s in specs if s]
            key = None
            buf = ""
    return extras


def _imports_of(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def _subsystem_files(root: Path, subdir: str, recursive: bool) -> list[Path]:
    base = root / subdir
    if not base.is_dir():
        return []
    if recursive:
        out = []
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames
                                if d != "__pycache__" and not d.startswith("."))
            out.extend(Path(dirpath) / fn for fn in sorted(filenames) if fn.endswith(".py"))
        return out
    return sorted(p for p in base.glob("*.py"))


# subsystem -> (directory, recursive, extras it may draw on)
_SUBSYSTEMS = (
    ("l5gntools", "l5gntools", True, ()),
    ("chronicler", "chronicler", False, ("scrape",)),
    ("chronicler/pipeline", "chronicler/pipeline", True, ("chronicler",)),
    ("chronicler/review", "chronicler/review", True, ("review", "viewer", "desktop")),
)


def _dependency_wall_section(root: Path, unparsed: list[dict]) -> dict:
    declared = _parse_optional_dependencies(root, unparsed)

    # Local names never counted as third-party: this toolkit's own two
    # top-level packages, plus the bare sibling-module imports the pipeline
    # scripts use when run standalone (`from db import get_connection`,
    # `from build_inventory import ...`) -- every .py stem directly under
    # chronicler/pipeline/, since that is the one place this repo imports by
    # bare filename instead of a package path.
    local = {"l5gntools", "chronicler"}
    local |= {p.stem for p in _subsystem_files(root, "chronicler/pipeline", False)}

    subsystems_out = []
    for label, subdir, recursive, extra_names in _SUBSYSTEMS:
        declared_pkgs: set[str] = set()
        for extra in extra_names:
            declared_pkgs |= set(declared.get(extra, []))
        declared_import_names: set[str] = set()
        for pkg in declared_pkgs:
            declared_import_names |= set(_PACKAGE_IMPORT_NAMES.get(pkg, (pkg,)))

        found: set[str] = set()
        for path in _subsystem_files(root, subdir, recursive):
            relpath = rel(path, root)
            tree, err = _parse_py(path)
            if err:
                unparsed.append({"module": relpath, "status": "unparsed", "reason": err})
                continue
            found |= _imports_of(tree)
        # stdlib is not third-party and never "undeclared"
        import sys
        stdlib = set(getattr(sys, "stdlib_module_names", set())) | {"__future__"}
        third_party_found = {n for n in found if n not in stdlib and n not in local}

        subsystems_out.append({
            "subsystem": label,
            "extras": sorted(extra_names),
            "declared_packages": sorted(declared_pkgs),
            "third_party_imports_found": sorted(third_party_found),
            "undeclared": sorted(third_party_found - declared_import_names),
            "unused_extras": sorted(declared_import_names - third_party_found),
        })
    subsystems_out.sort(key=lambda s: s["subsystem"])
    return {
        "declared_extras": {k: sorted(v) for k, v in sorted(declared.items())},
        "subsystems": subsystems_out,
    }


# --- assembly -----------------------------------------------------------------


def census(root: Path) -> dict:
    """The full six-section fact sheet for the tree rooted at `root`. Takes an
    explicit root (rather than closing over `TOOLKIT_ROOT`) so a tester can
    point it at a small synthetic tree -- e.g. to plant one unparseable file
    and assert it surfaces, without touching this repository."""
    unparsed: list[dict] = []
    sections = {
        "scanners": _scanners_section(),
        "gate": _gate_section(root, unparsed),
        "routes": _route_table_section(root, unparsed),
        "write_targets": _write_targets_section(root, unparsed),
        "schema": _schema_section(root, unparsed),
        "dependency_wall": _dependency_wall_section(root, unparsed),
    }
    unparsed.sort(key=lambda u: u["module"])
    return {
        "provenance": toolkit_git_info(),
        "sections": sections,
        "unparsed": unparsed,
    }


def scan_estate(projects: list) -> dict:  # noqa: ARG001 -- see module docstring
    """Ignores `projects`: this scanner's target is always this checkout, not
    the discovered project set every other estate scanner receives. Present
    only so `run.py`'s generic `ESTATE_LEVEL` dispatch and
    `auditor_cli_contract`'s shape check both keep working unmodified."""
    return census(TOOLKIT_ROOT)
