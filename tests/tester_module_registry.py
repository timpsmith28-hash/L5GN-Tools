"""tester_module_registry: the module descriptor, and the two auditors that
police it, exercised on their failure paths (COWORK_BRIEF_unified_app.md Task 1).

The auditors already run over the real tree on every gate, which proves they
pass. That is the cheap half. This tester proves the expensive half -- that
they *fail* when they should -- by handing each one a deliberately broken
input through the seam it was written with:

  * a registration missing a field, a registration with an unknown `requires`,
    a `registry` module whose view file does not exist, and a view file with no
    registration (the UAT line "`auditor_module_contract` fails on a
    registration missing a field, and on a view file with no registration");
  * a source file that imports the app tier, in all four spellings, plus the
    dynamic one (the UAT line "an auditor fails a deliberate import of the app
    tier from inside `l5gntools/`").

An auditor nobody has watched fail is a green light of unknown wiring.

Also checks the descriptor itself: `/api/modules` must be JSON-serialisable
(the router factory is a Python callable and must never reach the browser),
and a module whose declared requirements are absent must resolve to
declared-degraded *with a named cause* rather than to a bare False.

Hermetic and stdlib-only. No server is bound; FastAPI is never imported.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

from auditors import auditor_dependency_direction as direction
from auditors import auditor_module_contract as contract_auditor
from chronicler.review import modules as review_modules
from chronicler.review.module_contract import (
    REQUIREMENTS,
    STATUS_LEGACY,
    STATUS_REGISTRY,
    AppContext,
    ModuleDescriptor,
    capabilities,
    describe,
    resolve,
)


def _ok(*_args, **_kwargs):
    return None


def _sample(**over) -> ModuleDescriptor:
    base = ModuleDescriptor(id="sample", label="Sample", order=999,
                            status=STATUS_LEGACY, requires=("estate",))
    return replace(base, **over)


def _descriptor_shape() -> list[str]:
    v: list[str] = []

    # /api/modules must be JSON. A callable in the payload is the mistake this
    # catches: `describe` exists precisely to leave the router behind.
    for d in review_modules.MODULES:
        payload = describe(d)
        try:
            json.dumps(payload)
        except TypeError as exc:
            v.append(f"describe({d.id}) is not JSON-serialisable: {exc}")
        if "router" in payload:
            v.append(f"describe({d.id}) leaked the router factory to the browser")

    # Exactly one tab is migrated this round, by design. If this number moves,
    # it should move because someone decided to migrate another one.
    registered = review_modules.registered()
    if not registered:
        v.append("no module is registered -- the registry proves nothing")
    for d in registered:
        if d.view is None or d.router is None:
            v.append(f"{d.id}: registered without both a router and a view")

    # Tab-strip order is total and stable.
    orders = [d.order for d in review_modules.ordered()]
    if orders != sorted(orders):
        v.append("ordered() did not return modules in order")

    return v


def _degradation() -> list[str]:
    """A module whose `requires` are absent must name the cause."""
    v: list[str] = []
    caps = capabilities(AppContext())          # nothing on this machine at all
    time_mod = review_modules.BY_ID["time"]
    got = resolve(time_mod, caps)
    if got["available"]:
        v.append("time: reported available with no estate build present")
    if not got["unmet"]:
        v.append("time: degraded with no named cause")
    else:
        gap = got["unmet"][0]
        if not gap.get("detail"):
            v.append("time: unmet requirement carries no detail sentence")
        if gap.get("requirement") != "estate":
            v.append(f"time: unmet names {gap.get('requirement')!r}, expected 'estate'")

    # `lm_studio` is unknown, not absent, and unknown must NOT degrade a tab.
    if caps["lm_studio"]["available"] is not None:
        v.append("lm_studio resolved to a boolean -- it is a probe at use")
    probe_only = _sample(requires=("lm_studio",))
    if not resolve(probe_only, caps)["available"]:
        v.append("a module requiring only lm_studio was degraded by an unprobed "
                 "capability")

    # The vocabulary is closed: an unknown requirement is a stated failure.
    unknown = _sample(requires=("a_thing_nobody_declared",))
    gaps = resolve(unknown, caps)["unmet"]
    if not gaps or gaps[0]["reason"] != "unknown_requirement":
        v.append("an unknown requirement did not resolve to 'unknown_requirement'")

    for name in REQUIREMENTS:
        if name not in caps:
            v.append(f"capabilities() does not answer declared requirement {name!r}")

    return v


def _module_auditor_fails() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        views = Path(td) / "views"
        views.mkdir()
        (views / "good.js").write_text("export function mount(){}\n", encoding="utf-8")

        good = _sample(id="good", status=STATUS_REGISTRY, router=_ok, view="good.js")
        if contract_auditor.check_descriptors([good], views):
            v.append("a well-formed registration was reported as a violation")

        class Missing:            # a descriptor with no `requires` at all
            id = "missing"
            label = "Missing"
            order = 1
            status = STATUS_LEGACY
            router = None
            view = None

        cases = {
            "missing field": [Missing()],
            "unknown requires": [_sample(requires=("no_such_capability",))],
            "registry without view": [_sample(id="noview", status=STATUS_REGISTRY,
                                              router=_ok, view=None)],
            "view file absent": [_sample(id="ghost", status=STATUS_REGISTRY,
                                         router=_ok, view="ghost.js")],
            "legacy carrying a router": [_sample(router=_ok)],
            "duplicate id": [good, replace(good, order=1000)],
            "duplicate order": [good, replace(good, id="other", view="good.js")],
            "path as a view": [_sample(id="pathy", status=STATUS_REGISTRY,
                                       router=_ok, view="../secrets.js")],
        }
        for name, descriptors in cases.items():
            if not contract_auditor.check_descriptors(descriptors, views):
                v.append(f"auditor_module_contract passed a registration it must "
                         f"fail: {name}")

        # The orphan direction: a view file nobody registered.
        (views / "orphan.js").write_text("export function mount(){}\n", encoding="utf-8")
        found = contract_auditor.check_descriptors([good], views)
        if not any("orphan.js" in f for f in found):
            v.append("auditor_module_contract did not flag an unregistered view file")

    return v


def _direction_auditor_fails() -> list[str]:
    v: list[str] = []

    violations = {
        "import chronicler.review\n": "plain import",
        "import chronicler.review.app as a\n": "aliased import",
        "from chronicler.review import core\n": "from-package import",
        "from chronicler.review.app import create_app\n": "from-module import",
        "from chronicler import review\n": "name pulled from the package",
        "import importlib\nx = importlib.import_module('chronicler.review.app')\n":
            "dynamic import",
        "import tests.tester_review\n": "gate tier",
    }
    for src, name in violations.items():
        if not direction.check_source("fake.py", src):
            v.append(f"auditor_dependency_direction passed an app-tier import "
                     f"it must fail: {name}")

    allowed = {
        # The data layer the app also depends on -- explicitly NOT app tier.
        "from chronicler.pipeline import db\n": "chronicler.pipeline",
        "import chronicler\n": "the chronicler package alone",
        "from . import common\n": "a relative import inside the package",
        "import json, sqlite3\n": "stdlib",
        "x = 'chronicler.review is mentioned in this string'\n": "a bare string",
    }
    for src, name in allowed.items():
        found = direction.check_source("fake.py", src)
        if found:
            v.append(f"auditor_dependency_direction failed a legitimate import "
                     f"({name}): {found}")

    # And the real tree, through the same seam the gate uses.
    if direction.check_tree(direction.SCANNED_ROOT):
        v.append("l5gntools/ imports the app tier (see auditor_dependency_direction)")

    return v


def run() -> list[str]:
    v: list[str] = []
    v.extend(_descriptor_shape())
    v.extend(_degradation())
    v.extend(_module_auditor_fails())
    v.extend(_direction_auditor_fails())
    return v
