"""Every registered deck module must honour the module contract: every field
declared, a closed `requires` vocabulary, and -- for a migrated module -- a
view file that exists. Modelled on `auditor_tool_contract`, which proves the
same class of thing for scanners.

Orphans are checked in both directions, because only one direction is the
interesting one. A registration pointing at a missing view file fails loudly at
runtime anyway (the tab breaks the moment you click it). A view file with no
registration is the quiet failure: dead code that looks live, which the next
reader will maintain for nothing. So `static/views/` is *walked*, not trusted
from the registry.

Imports `chronicler.review.modules`, which is stdlib-only by construction --
router factories import FastAPI inside themselves. This auditor therefore runs
on a machine with no web stack installed, which DECISIONS 0034's consequence
paragraph requires of the gate.
"""
from __future__ import annotations

import re
from pathlib import Path

from chronicler.review import modules as review_modules
from chronicler.review.module_contract import (
    ALLOWED_STATUS,
    DESCRIPTOR_FIELDS,
    REQUIREMENTS,
    STATUS_LEGACY,
    STATUS_REGISTRY,
    VIEWS_DIR,
)

#: Ids appear in a URL fragment, an element id and a filename stem. Keep the
#: intersection of what all three tolerate rather than finding out later.
_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def check_descriptors(descriptors, views_dir: Path) -> list[str]:
    """The whole check, against an explicit list and views directory.

    Taking both as arguments is what lets the tester feed a deliberately
    broken registration and prove this auditor fails it -- a gate nobody has
    watched fail is a gate nobody knows works.
    """
    v: list[str] = []
    seen_ids: dict[str, int] = {}
    seen_orders: dict[int, str] = {}
    declared_views: set[str] = set()

    for d in descriptors:
        label = getattr(d, "id", None) or repr(d)

        missing = [f for f in DESCRIPTOR_FIELDS if not hasattr(d, f)]
        if missing:
            v.append(f"{label}: descriptor missing field(s) {', '.join(missing)}")
            continue

        if not isinstance(d.id, str) or not _ID_RE.match(d.id or ""):
            v.append(f"{label}: id must match {_ID_RE.pattern}")
        if not isinstance(d.label, str) or not d.label.strip():
            v.append(f"{label}: label is empty")
        if not isinstance(d.order, int) or isinstance(d.order, bool):
            v.append(f"{label}: order must be an int, got {type(d.order).__name__}")

        if d.id in seen_ids:
            v.append(f"{label}: duplicate module id")
        seen_ids[d.id] = seen_ids.get(d.id, 0) + 1
        if isinstance(d.order, int) and not isinstance(d.order, bool):
            if d.order in seen_orders and seen_orders[d.order] != d.id:
                v.append(f"{label}: order {d.order} already taken by "
                         f"{seen_orders[d.order]!r}")
            seen_orders.setdefault(d.order, d.id)

        if d.status not in ALLOWED_STATUS:
            v.append(f"{label}: status {d.status!r} not in {sorted(ALLOWED_STATUS)}")

        if isinstance(d.requires, str) or not isinstance(d.requires, (tuple, list)):
            v.append(f"{label}: requires must be a tuple of requirement names")
        else:
            for req in d.requires:
                if req not in REQUIREMENTS:
                    v.append(f"{label}: requires unknown capability {req!r} "
                             f"(vocabulary: {sorted(REQUIREMENTS)})")

        if d.status == STATUS_REGISTRY:
            if not callable(d.router):
                v.append(f"{label}: status 'registry' but router is not callable")
            if not isinstance(d.view, str) or not d.view.endswith(".js"):
                v.append(f"{label}: status 'registry' but view is not a .js filename")
            elif "/" in d.view or "\\" in d.view or ".." in d.view:
                v.append(f"{label}: view {d.view!r} must be a bare filename, never a path")
            else:
                declared_views.add(d.view)
                if not (views_dir / d.view).is_file():
                    v.append(f"{label}: view file {d.view!r} not found in {views_dir}")
        elif d.status == STATUS_LEGACY:
            # A legacy module is a real registration whose routes and pane are
            # still inline. Half-migrated is the state that rots: a router with
            # no view, or a view the shell never loads.
            if d.router is not None:
                v.append(f"{label}: status 'legacy' must not carry a router factory")
            if d.view is not None:
                v.append(f"{label}: status 'legacy' must not carry a view file")

    if views_dir.is_dir():
        for path in sorted(views_dir.glob("*.js")):
            if path.name not in declared_views:
                v.append(f"{path.name}: view file has no registration in "
                         f"chronicler/review/modules.py")

    return v


def run() -> list[str]:
    v = check_descriptors(review_modules.MODULES, VIEWS_DIR)
    for mid, descriptor in review_modules.BY_ID.items():
        if descriptor.id != mid:
            v.append(f"{mid}: BY_ID key does not match descriptor id "
                     f"{descriptor.id!r}")
    if len(review_modules.BY_ID) != len(review_modules.MODULES):
        v.append("BY_ID has fewer entries than MODULES -- duplicate module id")
    return v
