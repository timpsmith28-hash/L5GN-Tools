"""auditor_authors_declaration -- fail the gate when `config/local.json`
declares artefact authorship, which 0054 clause 6 puts in the tracked file only.

**One class of claim**, in `auditor_doc_claims`' pattern and to its standard:
*no host section in the untracked overlay carries an `authors` key.* Nothing
else. It does not check whether the declarations in `config/machines.json` are
correct, complete, or shipped -- those are different readers and none of them
exists.

## Why a rule already enforced by structure still wants a reader

`l5gntools/config.py`'s `_tracked_entry` is `machine()`'s layer stack with
`local.json` removed, so an overlay declaration is not outranked -- it is
unreadable. That is the strong form and it landed on 2026-08-31.

**Unreadable is silent.** A key that does nothing is indistinguishable from a
key that works, so the failure it leaves is a person declaring authorship,
getting none, and being told by `run.py pin bump` that the artefact has no
author -- a config gap message for what is really a mis-filed declaration.
`config.machine()` now raises on it (0054 clause 8, `OverlayAuthorshipError`),
which catches it at run time on the machine that has it.

This auditor is the part that catches it **in the gate, before it ships**, and
it is what 0054 clause 6 declares as its reader under **0060** clause 4. Until
this file existed, clause 6 was a rule with no reader that could go red --
which `docs/CONVENTION_conformance.md` §7 says is worse than no reader at all.

## The invariant lives in one place

The predicate is `config._overlay_authorship`, called here rather than
reimplemented -- **0060** clause 6: where a rule's subject spans two components,
the reader lives in the gate and a copy of the rule in both is not a mechanism.
If the loader's idea of "declares authorship" ever changes, this moves with it.

## Absent, malformed and present are three answers, not two

`config._load` returns `{}` for a missing file *and* for unparsable JSON, which
is right for a loader and wrong for a reader: it would let a corrupt overlay
pass as a clean one. So this reads the file itself.

  * **absent** -- no overlay on this checkout. Clear, not unknown; the file is
    gitignored and a fresh clone has none.
  * **unparsable** -- reported as a violation. **0050**: a source that cannot be
    read is unknown, never fresh, and an unknown overlay cannot be said to
    carry no authorship.
  * **present and parsable** -- checked.

## What this cannot see

Stated because **0048** clause 4 says a check that cannot fail trains the eye
past it, and this one fires in a narrow band:

  * It does not check the second half of `config/machines.json`'s own contract
    -- that a real host section there carries `authors` *and nothing else*.
    That is a second claim class and belongs in a second reader, not bolted on
    here.
  * It cannot tell a correct `authors` list from a wrong one. A host declaring
    an artefact it does not really author passes mechanically, and
    `run.py pin bump`'s refusal is what rests on that being true.
  * It reads one machine's checkout. An overlay sitting on another rig,
    unshipped and undeclared, is invisible here -- which is the same
    unshippability clause 6 is about, and is why the rule exists rather than a
    convention asking nicely.
"""
from __future__ import annotations

import json
from pathlib import Path

from l5gntools import config

_ROOT = Path(__file__).resolve().parent.parent

REMEDY = ("move each 'authors' list into config/machines.json under the same "
          "hostname and delete it from config/local.json")


def violations_in_overlay(text: str, label: str = "config/local.json"
                          ) -> list[str]:
    """Pure, file-independent check over one overlay's JSON text."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        return [f"{label}: unparsable JSON ({exc}) -- an overlay that cannot be "
                f"read cannot be said to carry no authorship (0050); fix the "
                f"file so 0054 cl.6 can be checked against it"]
    if not isinstance(data, dict):
        return [f"{label}: top level is {type(data).__name__}, not an object -- "
                f"0054 cl.6 cannot be checked against it"]

    offenders = config._overlay_authorship(data)
    if not offenders:
        return []
    return [f"{label}: host {host!r} declares 'authors' -- 0054 cl.6 puts "
            f"authorship in the tracked file only, and nothing reads it here, "
            f"so this declaration is inert rather than an override. Remedy: "
            f"{REMEDY}." for host in offenders]


def run() -> list[str]:
    overlay = _ROOT / "config" / "local.json"
    if not overlay.exists():
        # Gitignored by design; a fresh clone has none. Absent is clear, not
        # unknown -- there is no overlay to declare anything.
        return []
    try:
        text = overlay.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"config/local.json: unreadable ({exc}) -- reported rather than "
                f"passed over (0050)"]
    if not text.strip():
        return []
    return violations_in_overlay(text)
