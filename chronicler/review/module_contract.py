"""The UI module contract -- what a deck module must declare to be discovered.

This is to `chronicler/review/modules.py` what `l5gntools/contract.py` is to
`l5gntools/registry.py`: the registry is the flat list of what exists, this
file is the shape every entry must satisfy and the vocabulary it draws on. The
split is deliberate and copied on purpose -- an auditor that imported only the
registry could prove membership but not conformance, and one file holding both
would let a descriptor quietly redefine the shape it is checked against.

**Stdlib-only, and it must stay that way.** Nothing here imports FastAPI. A
descriptor's `router` is a *factory* that is called at app-build time and does
its own `from fastapi import APIRouter` inside; that keeps `modules.py`
importable -- and therefore auditable by `verify.py` -- on a machine with no
web stack installed, which DECISIONS 0034's consequence paragraph requires of
the gate ("`verify.py` must keep proving it with no web stack present, or (1)
is decorative").

## `requires` -- degradation declared, not coded per route

The deck already degrades by hand in several places: `_need_vault()`,
`_need_estate()`, `_need_curator_estate()`, each spelled out again at every
route that needs it. A module instead *declares* what it needs, `create_app`
resolves those declarations once against the running machine, and a module
whose requirements are absent is gated in one place with a named cause. The
route bodies stop carrying the question.

A requirement is only in the vocabulary below if the app can answer it. The one
exception is `lm_studio`, which is answered by *trying it* (a probe on every
page load would be a network call in a health check), so it resolves to
`available: None` -- "not probed here, checked when a stage runs". Unknown is
not the same as absent, and only a definite False degrades a module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

#: Every requirement a module may declare, and the sentence shown when it is
#: missing. A `requires` entry outside this map is a gate failure, not a
#: free-text note -- the vocabulary is closed so the resolver can never be
#: handed a question it has no answer for.
REQUIREMENTS: dict[str, str] = {
    "vault": "the Chronicler vault (chronicler.db) on this machine",
    "estate": "an estate build (data/estate.json) -- run `python run.py build`",
    "repo_docs": "this repository's own docs/ directory",
    "transcripts": "the local transcript store (DECISIONS 0032)",
    "lm_studio": "a running LM Studio endpoint (probed when a stage runs)",
}

#: A module whose routes come from its own router factory and whose pane is an
#: ES module the shell loads. The shape this round is moving towards.
STATUS_REGISTRY = "registry"
#: A module still declared here for the tab strip, but whose routes remain
#: inline in `app.py` and whose pane remains markup in `index.html`. Six of
#: seven are deliberately left this way in the commit that lands the registry:
#: if the two shapes could not coexist, the descriptor would be wrong and the
#: round would have found that out for the price of one tab.
STATUS_LEGACY = "legacy"
ALLOWED_STATUS = frozenset({STATUS_REGISTRY, STATUS_LEGACY})

#: Keys every descriptor carries. `auditor_module_contract` reads this list;
#: adding a field here makes it required of every registration at once.
DESCRIPTOR_FIELDS = ("id", "label", "order", "status", "requires", "router", "view")

#: Where a migrated module's browser-side view lives. Walked by the auditor so
#: an orphan view file (a `.js` with no registration) is a gate failure rather
#: than dead weight nobody notices.
VIEWS_DIR = Path(__file__).resolve().parent / "static" / "views"


@dataclass(frozen=True)
class ModuleDescriptor:
    """One deck module, declared in code.

    `router` is a factory, not a router: it takes an :class:`AppContext` and
    returns a `fastapi.APIRouter`. Called once, inside `create_app`, so this
    module never imports the web stack and a descriptor can be read (and
    audited) without one.

    `view` is a filename inside :data:`VIEWS_DIR`, not a path and not a URL --
    the same discipline as `/api/estate/document`'s `doc_id`: the shell
    resolves it, nothing accepts a caller-supplied path.
    """

    id: str
    label: str
    order: int
    status: str
    requires: tuple[str, ...] = ()
    router: Callable | None = None
    view: str | None = None


@dataclass(frozen=True)
class AppContext:
    """What a router factory is given, and what capabilities are resolved from.

    Exactly the arguments `create_app` already took, gathered into one object
    so a new module's factory signature never has to change when an eighth
    dependency appears. Nothing here is mutated after construction; the app is
    built once, per DECISIONS 0025's rule that the estate clause is resolved
    once by the caller and closed over, never re-derived mid-request.
    """

    db_path: Path | None = None
    registry: dict = field(default_factory=dict)
    account_clause: str = ""
    estate: object | None = None
    index: object | None = None
    vault_unavailable: object | None = None
    curator: object | None = None
    curator_estate_gap: str | None = None


def capabilities(ctx: AppContext) -> dict[str, dict]:
    """Resolve every requirement in the vocabulary against this machine, once.

    `available` is True, False, or None -- None meaning "not determinable
    without doing the work" (see the module docstring on `lm_studio`). Each
    answer carries a `detail` sentence, because a tab that says only
    "unavailable" sends you to the logs, and the whole point of hoisting
    degradation into data is that the surface can say *why* on its own face.
    """
    vault_detail = None
    if ctx.vault_unavailable is not None:
        vault_detail = getattr(ctx.vault_unavailable, "detail", None)

    estate_ok = ctx.estate is not None and bool(getattr(ctx.estate, "available", False))
    estate_reason = getattr(ctx.estate, "reason", None) if ctx.estate is not None else "estate_absent"

    if ctx.curator_estate_gap:
        from .curator_data import CURATOR_ESTATE_GAP_REASON
        transcripts = {"available": False, "reason": CURATOR_ESTATE_GAP_REASON,
                       "detail": ctx.curator_estate_gap}
    elif ctx.curator is None:
        transcripts = {"available": False, "reason": "curator_absent",
                       "detail": "No data/knowledge_curator/ on this machine yet."}
    else:
        transcripts = {"available": True, "reason": None,
                       "detail": REQUIREMENTS["transcripts"]}

    return {
        "vault": {
            "available": ctx.db_path is not None,
            "reason": None if ctx.db_path is not None else "vault_absent",
            "detail": vault_detail or ("Vault at " + str(ctx.db_path) if ctx.db_path
                                       else "No vault on this machine."),
        },
        "estate": {
            "available": estate_ok,
            "reason": None if estate_ok else (estate_reason or "estate_absent"),
            "detail": REQUIREMENTS["estate"] if not estate_ok
                      else "Estate build present.",
        },
        # True by construction: the board and the sidebar derive from the
        # checkout this process is running inside. Gating it on a vault or a
        # build would refuse to render a directory we are standing in.
        "repo_docs": {"available": True, "reason": None,
                      "detail": REQUIREMENTS["repo_docs"]},
        "transcripts": transcripts,
        "lm_studio": {"available": None, "reason": "not_probed",
                      "detail": REQUIREMENTS["lm_studio"]},
    }


def describe(descriptor: ModuleDescriptor) -> dict:
    """The JSON-safe half of a descriptor -- what `/api/modules` may return.

    The router factory is a Python callable and is deliberately absent: the
    browser gets what it needs to draw a tab and load a view, and nothing that
    would tempt anyone into addressing server internals by name from the UI.
    """
    return {
        "id": descriptor.id,
        "label": descriptor.label,
        "order": descriptor.order,
        "status": descriptor.status,
        "requires": list(descriptor.requires),
        "view": descriptor.view,
    }


def unmet(descriptor: ModuleDescriptor, caps: dict[str, dict]) -> list[dict]:
    """The declared requirements this machine definitely has not got.

    `available is None` (unknown) is NOT unmet. A tab that greys itself out
    because a probe was skipped is a surface lying about the machine.
    """
    out: list[dict] = []
    for name in descriptor.requires:
        cap = caps.get(name)
        if cap is None:
            out.append({"requirement": name, "reason": "unknown_requirement",
                        "detail": f"{name!r} is not in the requirement vocabulary."})
        elif cap.get("available") is False:
            out.append({"requirement": name,
                        "reason": cap.get("reason") or "unavailable",
                        "detail": cap.get("detail") or REQUIREMENTS.get(name, name)})
    return out


def resolve(descriptor: ModuleDescriptor, caps: dict[str, dict]) -> dict:
    """One module as the shell sees it: its description plus its degradation."""
    gaps = unmet(descriptor, caps)
    return {**describe(descriptor), "available": not gaps, "unmet": gaps}
