"""The dependency direction is one-way: the app imports `l5gntools`;
`l5gntools` never imports the app (DECISIONS 0034 clause 3).

This is the auditor clause 3 says must exist, and it is *not* a variant of
`auditor_module_contract`. That one proves a descriptor is complete. This one
proves the property that makes clause 1 survivable at all: `l5gntools/` can
stay stdlib-only next to a dependency-heavy application tier only if nothing in
it can reach for that tier. Without this check the boundary is "please don't
import that", which INTENT §5 ("guarantees are structural, not behavioural")
rules out as a guarantee.

**Where the line is.** Clause 3 names one direction and one pair of tiers:

  * **App tier** -- `chronicler.review` (the FastAPI app, its routers, its data
    layers) and the gate itself (`auditors`, `tests`, `verify`). A scanner that
    imported its own auditor would invert the same relationship.
  * **NOT app tier** -- `chronicler.pipeline`. It is the data layer the app
    also depends on, not a surface. Listing it here would forbid a dependency
    clause 3 says nothing about, and an auditor enforcing a rule nobody made is
    worse than no auditor.

Technique copied from `auditor_stdlib`: `ast` over the source, no imports
executed. It also catches the obvious dodge -- a dynamic
`importlib.import_module("chronicler.review...")` -- because a rule that only
looks at `import` statements teaches people to write a string instead.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNED_ROOT = REPO_ROOT / "l5gntools"

#: Module prefixes `l5gntools/` may never import. Matched on dotted prefix, so
#: `chronicler.review.app` is caught and a hypothetical `chronicler.reviewer`
#: is not.
APP_TIER = ("chronicler.review", "auditors", "tests", "verify")

_DYNAMIC_IMPORTERS = {"import_module", "__import__"}


def _is_app_tier(dotted: str) -> str | None:
    """The offending prefix, or None. Prefix match on dotted segments only."""
    if not dotted:
        return None
    for prefix in APP_TIER:
        if dotted == prefix or dotted.startswith(prefix + "."):
            return prefix
    return None


def check_source(label: str, text: str) -> list[str]:
    """Every app-tier import in one file's source.

    Takes the text rather than reading it, so the tester can hand this a
    deliberate violation and prove the auditor fails it -- the UAT line "an
    auditor fails a deliberate import of the app tier" is exactly this call.
    """
    out: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [f"{label}: could not parse ({exc})"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = _is_app_tier(alias.name)
                if hit:
                    out.append(f"{label}:{node.lineno}: imports app-tier module "
                               f"'{alias.name}' (DECISIONS 0034 clause 3: "
                               f"l5gntools never imports the app)")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue  # relative -- inside l5gntools by definition
            base = node.module or ""
            hit = _is_app_tier(base)
            if hit:
                out.append(f"{label}:{node.lineno}: imports app-tier module "
                           f"'{base}' (DECISIONS 0034 clause 3: l5gntools "
                           f"never imports the app)")
                continue
            # `from chronicler import review` -- the package alone is fine,
            # the name being pulled out of it is what makes it app tier.
            for alias in node.names:
                hit = _is_app_tier(f"{base}.{alias.name}" if base else alias.name)
                if hit:
                    out.append(f"{label}:{node.lineno}: imports app-tier module "
                               f"'{base}.{alias.name}' (DECISIONS 0034 clause 3: "
                               f"l5gntools never imports the app)")
        elif isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name not in _DYNAMIC_IMPORTERS:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    hit = _is_app_tier(arg.value)
                    if hit:
                        out.append(f"{label}:{node.lineno}: dynamically imports "
                                   f"app-tier module '{arg.value}' (DECISIONS "
                                   f"0034 clause 3)")
    return out


def check_tree(root: Path) -> list[str]:
    """Every `.py` under `root`, sorted so the output is stable."""
    v: list[str] = []
    if not root.is_dir():
        return [f"{root}: directory not found -- nothing was checked, which is "
                f"not the same as nothing being wrong"]
    for path in sorted(root.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            v.append(f"{path}: unreadable ({exc})")
            continue
        v.extend(check_source(str(path.relative_to(root.parent)), text))
    return v


def run() -> list[str]:
    return check_tree(SCANNED_ROOT)
