"""auditor_conversation_map_pin -- fail the gate when the conversation map's
committed fingerprint (DECISIONS 0040 clause 4) has drifted from the map on
disk, carries an anchor that does not resolve, or exists with no pin at all.

0040 clause 4 committed `config/mcf_conversation_map.tsv.sha256` beside the
untracked map and said plainly, in `config/README.md`: "Nothing checks this
yet." This auditor is DECISIONS 0045 applied to that gap -- one pin,
verified read-only, reported never repaired (0045 clause 2). See
`l5gntools/pin.py` for the mechanism and `run.py pin bump` for the only
sanctioned writer; this auditor never touches either file.

The map itself travels by hand (`config/README.md`'s "authored here, on the
gaming/dev rig, copied outward manually") and is absent on a fresh checkout
or a machine that was never handed a copy. That is the documented normal
state, not a defect -- `artefact-absent` and `absent` pass clean, same as
0045 clause 5's "working ahead of a pin is a normal state, not an error."
`git-unavailable` also passes clean, mirroring `auditor_uat_stamp`'s
degrade-to-skip outside a checkout: an absent git is not evidence of a bad
pin.

Everything else fails: a real hash mismatch, an anchor that doesn't resolve,
a malformed pin file, or a map that exists with no pin recorded for it at
all (0040 clause 4 requires one).
"""
from __future__ import annotations

from pathlib import Path

from l5gntools import pin
from l5gntools.common import TOOLKIT_ROOT

ARTEFACT = TOOLKIT_ROOT / "config" / "mcf_conversation_map.tsv"
PIN_FILE = TOOLKIT_ROOT / "config" / "mcf_conversation_map.tsv.sha256"

#: States that are not a violation -- see module docstring for why each one
#: earns that.
CLEAN_STATES = frozenset({"matches", "artefact-absent", "absent", "git-unavailable"})


def check(artefact: Path, pin_file: Path, commit_exists=None) -> list[str]:
    """The whole check, against explicit paths and an injected resolver --
    the testable core of run()."""
    result = pin.verify_pin(pin_file, artefact, commit_exists)
    if result.state in CLEAN_STATES:
        return []
    return result.findings or [
        f"{artefact}: pin state {result.state!r} carried no finding "
        f"(bug in the checker itself)"]


def run() -> list[str]:
    return check(ARTEFACT, PIN_FILE, pin.commit_exists_resolver())
