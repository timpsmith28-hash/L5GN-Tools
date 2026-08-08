"""Single source of truth for which deck modules exist.

The same instinct as `l5gntools/registry.py`, applied to the UI: a flat list
other code iterates, plus a by-id map. `create_app` includes each registered
router; `/api/modules` renders this list; the browser builds its tab strip from
that response instead of from markup. A new module is one registration here
plus one view file in `static/views/`.

**Why six of seven are `legacy` in the commit that lands this file.** The brief
(COWORK_BRIEF_unified_app.md, Task 1) asks for exactly one tab migrated
alongside the registry, on the grounds that if the two shapes cannot coexist
the descriptor is wrong and the round should find that out for the price of one
tab rather than seven. So a `legacy` entry is a real, audited registration --
it carries id, label, order and `requires` like any other, and the tab strip is
data for all seven -- but its routes are still declared inline in `app.py` and
its pane is still markup in `index.html`. Task 2 flips them one at a time by
adding a router factory and a view file and changing one word.

`time` is the migrated one. It was chosen for what it lacks: two read-only
routes, both already living in `estate_time.py`, one `requires` (`estate`), no
writes, no cross-pane calls, and a view whose helpers (`fmtDate` and four
render functions) are used by nothing else in the file. A tab that shared state
with another pane would have proved the shell's boundary rather than the
descriptor's.

**`report` is the eighth module, added whole by Task 3 -- not a migration.**
It did not exist as a deck tab before this round; it demotes the standalone
`report.html` from surface to export (0027) by giving the estate scanner
report a live view, reading `data/estate.json` at request time
(`estate_report.read_estate`, never cached). Registering a genuinely new
module here, rather than only flipping a `legacy` one, is the first real
proof of the claim Task 1's UAT line makes -- "a new module is one
registration plus one view file" -- ahead of that line's own throwaway-tab
walk.
"""
from __future__ import annotations

from . import estate_report, estate_time
from .module_contract import (
    STATUS_LEGACY,
    STATUS_REGISTRY,
    ModuleDescriptor,
)

#: Order is the tab strip's left-to-right order. Spaced by ten so an eighth
#: module can land between two existing tabs without renumbering the file --
#: a renumbering diff hides the actual change inside noise.
MODULES: list[ModuleDescriptor] = [
    ModuleDescriptor(
        id="queue", label="Review queue", order=10,
        status=STATUS_LEGACY, requires=("vault",)),
    ModuleDescriptor(
        id="docs", label="Documents", order=20,
        status=STATUS_LEGACY, requires=("estate",)),
    ModuleDescriptor(
        id="search", label="Search", order=30,
        status=STATUS_LEGACY, requires=("estate",)),
    ModuleDescriptor(
        id="time", label="Time", order=40,
        status=STATUS_REGISTRY, requires=("estate",),
        router=estate_time.router, view="time.js"),
    ModuleDescriptor(
        id="report", label="Estate report", order=45,
        status=STATUS_REGISTRY, requires=("estate",),
        router=estate_report.router, view="report.js"),
    ModuleDescriptor(
        id="board", label="Docs board", order=50,
        status=STATUS_LEGACY, requires=("repo_docs",)),
    ModuleDescriptor(
        id="uat", label="UAT sidebar", order=60,
        status=STATUS_LEGACY, requires=("repo_docs",)),
    ModuleDescriptor(
        # Two requirements, and only one of them is knowable up front: the
        # transcript store is on disk or it is not, LM Studio is a probe at
        # use. Declaring both is honest; only the first can degrade the tab.
        id="curator", label="Knowledge Curator", order=70,
        status=STATUS_LEGACY, requires=("transcripts", "lm_studio")),
]

BY_ID = {m.id: m for m in MODULES}


def ordered() -> list[ModuleDescriptor]:
    """Every module, tab-strip order. Sorted here rather than trusted from the
    literal above, so a mis-ordered registration is a cosmetic non-event
    instead of a UI bug (the auditor still fails duplicate `order` values)."""
    return sorted(MODULES, key=lambda m: (m.order, m.id))


def registered() -> list[ModuleDescriptor]:
    """The modules that contribute routes and a view -- what `create_app`
    iterates. Grows as Task 2 flips each `legacy` entry over."""
    return [m for m in ordered() if m.status == STATUS_REGISTRY]
