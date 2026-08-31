"""auditor_conversation_map_pin -- fail the gate when a conversation map's
committed fingerprint (DECISIONS 0040 clause 4) has drifted from the map on
disk, carries an anchor that does not resolve, is missing entirely, or records
less than 0056 clause 3 requires.

0040 clause 4 committed `config/mcf_conversation_map.tsv.sha256` beside the
untracked map and said plainly, in `config/README.md`: "Nothing checks this
yet." This auditor is DECISIONS 0045 applied to that gap -- pins verified
read-only, reported never repaired (0045 clause 2). See `l5gntools/pin.py` for
the mechanism and `run.py pin bump` for the only sanctioned writer; this
auditor never touches either file.

## Driven by the pattern, not by a path (0056 clause 1)

Until 2026-08-31 this module bound `ARTEFACT` and `PIN_FILE` to
`config/mcf_conversation_map.tsv` as module-level constants. Two maps existed.
`personal_conversation_map.tsv` had no pin, and **this check structurally could
not see the instance that violated the rule it exists to enforce** -- 0056's
own Context calls that out by name, and its clause 1 is the general remedy:

    A check enforcing a pattern rule is driven by the pattern.

`PATTERN` below is the same glob `.gitignore` already uses for these files,
copied deliberately rather than paraphrased. A second map now inherits the
check by existing, which is what 0040 clause 4 meant when it wrote the
`.gitignore` half as a pattern "so the next source's map inherits the rule
rather than having to remember it".

## What passes, and why each one earns it

The map itself travels by hand (`config/README.md`'s "authored here, on the
gaming/dev rig, copied outward manually") and is absent on a fresh checkout or
a machine that was never handed a copy. That is the documented normal state,
not a defect -- `artefact-absent` and `absent` pass clean, same as 0045 clause
5's "working ahead of a pin is a normal state, not an error". `git-unavailable`
also passes clean, mirroring `auditor_uat_stamp`'s degrade-to-skip outside a
checkout: an absent git is not evidence of a bad pin.

Everything else fails: a real hash mismatch, an anchor that doesn't resolve, a
malformed pin file, a map that exists with no pin recorded for it at all (0040
clause 4 requires one; 0056 clause 2 restates it as a violation rather than an
absence), and a pin carrying only a hash (0056 clause 3).

## Metadata completeness lives here, not in `pin.py` (0056 clause 3)

`pin.py`'s docstring records that "a pin with no comment line is still a valid
pin -- just missing the optional fields". That is the *mechanism's* view and it
stays true: `verify_pin` parses and reports, and it is not this ruling's job to
make `pin.py` refuse. 0056 clause 3 is the *rule* -- "a hash-only pin is
incomplete under 0040 clause 4 and is reported as incomplete rather than
accepted as passing" -- and 0052 puts a rule's enforcement in the checker that
cites it, not in the shared library it borrows. So the completeness check is
layered on top of `verify_pin` here.

`anchor` is required only "where one exists" (clause 3's own wording). Read
operationally: where a resolver is available, git is present, `HEAD` resolved
when the pin was taken, and an anchor could have been recorded -- so its
absence is a finding. Where git is unavailable this auditor cannot tell an
anchorless pin from an unanchorable one, and says nothing rather than guessing.
"""
from __future__ import annotations

from pathlib import Path

from l5gntools import pin
from l5gntools.common import TOOLKIT_ROOT

#: The subject, as the ruling defines it. Same glob `.gitignore` carries for
#: these files (`/config/*conversation_map.tsv`), deliberately not narrowed.
CONFIG_DIR = TOOLKIT_ROOT / "config"
PATTERN = "*conversation_map.tsv"
PIN_SUFFIX = ".sha256"

#: States that are not a violation -- see module docstring for why each one
#: earns that.
CLEAN_STATES = frozenset({"matches", "artefact-absent", "absent", "git-unavailable"})

#: 0056 clause 3's field set is defined once, in `l5gntools/pin.py`, and read
#: from there by this checker AND by `run.py pin bump`. Two copies is how the
#: rule and its own remedy drifted apart on the day this check landed.
REQUIRED_PIN_FIELDS = pin.REQUIRED_FIELDS


def subjects(config_dir: Path) -> list[tuple[Path, Path]]:
    """Every `(artefact, pin_file)` pair the pattern covers, sorted.

    The union of maps on disk and pins on disk, deliberately: a pin whose
    artefact is absent is a normal hand-carried state that still has an anchor
    worth resolving, and a map whose pin is absent is exactly the violation
    0056 clause 2 names. Taking only one side would drop one of them.
    """
    found: set[Path] = set(config_dir.glob(PATTERN))
    for pin_file in config_dir.glob(PATTERN + PIN_SUFFIX):
        found.add(pin_file.with_suffix(""))
    return sorted((a, a.with_name(a.name + PIN_SUFFIX)) for a in found)


def check_metadata(pin_file: Path, commit_exists=None) -> list[str]:
    """0056 clause 3: a pin records when and where it was taken, not only what.

    The completeness question is asked through `pin.missing_metadata`, the same
    function `run.py pin bump` asks before deciding it has nothing to write, so
    this check cannot demand a field the sanctioned writer will not produce.
    """
    record = pin.parse_pin_file(pin_file)
    missing = pin.missing_metadata(record, anchor_expected=commit_exists is not None)
    if not missing:
        return []
    return [f"{pin_file}: pin records only a hash line; missing "
            f"{', '.join(missing)}. DECISIONS 0056 clause 3 -- a pin "
            f"carries origin, anchor where one exists, date, and the host that "
            f"took it, so that a consumer holding a stale copy can read the "
            f"remedy (be re-handed a copy from that host) off the failure "
            f"alone (clause 4). Re-take it with `python run.py pin bump "
            f"config/{pin_file.with_suffix('').name} --apply` on the authoring "
            f"host -- `pin bump` refuses anywhere else (0053 clause 5)."]


def check(artefact: Path, pin_file: Path, commit_exists=None) -> list[str]:
    """The whole check for ONE pair, against explicit paths and an injected
    resolver -- the testable core of run()."""
    result = pin.verify_pin(pin_file, artefact, commit_exists)
    if result.state not in CLEAN_STATES:
        return result.findings or [
            f"{artefact}: pin state {result.state!r} carried no finding "
            f"(bug in the checker itself)"]
    if result.state == "absent":
        return []                      # nothing on either side to be incomplete
    return check_metadata(pin_file, commit_exists)


def run() -> list[str]:
    resolver = pin.commit_exists_resolver()
    findings: list[str] = []
    for artefact, pin_file in subjects(CONFIG_DIR):
        findings.extend(check(artefact, pin_file, resolver))
    return findings
