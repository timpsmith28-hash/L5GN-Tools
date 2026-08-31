"""Read-only pin verification (DECISIONS 0045): a pin records origin, the
anchor commit where one exists, the date and host it was taken on, and the
content hash of a pinned artefact. Verification REPORTS; it never repairs
(0045 clause 2), and an unresolvable anchor is a violation, not a silent pass
(0045 clause 3) -- the same bar `auditor_uat_stamp` already holds for its own
commit resolution, reused here rather than reinvented.

This module only reads. Writing or bumping a pin is `run.py pin bump` --
0045 clause 4: reading a pin is read-only and may live in `l5gntools/`
(`hashlib` is stdlib; 0034 clause 1 untouched); writing is not a scanner.

Pin file format (Task 1, `COWORK_BRIEF_pin_mechanism.md`): the first line is
a plain `sha256sum`-compatible line, so `sha256sum -c <pin file>` keeps
working by hand exactly as `config/README.md` already documents for
`config/mcf_conversation_map.tsv.sha256`. An optional second line, prefixed
`#` (ignored by `sha256sum -c` and by a plain read), carries the rest of
0045's field set as `key=value` pairs:

    <hex sha256>  <repo-relative artefact path>
    # pin: origin=local anchor=<sha> date=YYYY-MM-DD host=<hostname>

`origin=local` (0045 clause 1) is the value for an untracked file native to
this repo; a future cross-repo pin uses `origin=<repo>:<path>`, per 0043's
citation rule. A pin with no comment line is still a valid pin -- just
missing the optional fields; nothing here rewrites one to add them.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from l5gntools.common import TOOLKIT_ROOT, is_git_repo, run_git

_HASH_LINE = re.compile(r"^([0-9a-f]{64})\s+(\S+)\s*$")
_COMMENT_LINE = re.compile(r"^#\s*pin:\s*(.*)$")
_FIELD = re.compile(r"(\w+)\s*=\s*(\S+)")

#: Every state `verify_pin` can return, and what it means. `matches` and
#: `artefact-absent` are informational per 0045 clause 5 ("working ahead of a
#: pin is a normal state, not an error") and, for a hand-carried artefact
#: like the conversation map, per `config/README.md` (a fresh checkout has no
#: map at all -- that is documented, not a defect). Every other state carries
#: at least one finding.
STATES = (
    "matches",              # hash matches; anchor absent or resolves
    "mismatch",             # artefact present, hash differs
    "artefact-absent",      # pin exists, artefact does not (normal for a
                             # hand-carried artefact on a fresh checkout)
    "unpinned",              # artefact exists, no pin file at all
    "absent",                # neither pin nor artefact exists -- nothing to check
    "pin-malformed",         # pin file exists but its hash line doesn't parse
    "anchor-unresolvable",   # anchor= is set, git is available, sha doesn't resolve
    "git-unavailable",       # anchor= is set but there's no git to ask -- skip
)


@dataclass
class PinRecord:
    sha256: str
    artefact_path: str          # as recorded in the pin file (repo-relative)
    origin: str | None = None
    anchor: str | None = None
    date: str | None = None
    host: str | None = None


@dataclass
class PinCheck:
    state: str
    pin_path: Path
    artefact_path: Path
    recorded_hash: str | None
    actual_hash: str | None
    findings: list[str] = field(default_factory=list)


def parse_pin_file(path: Path) -> PinRecord | None:
    """Parse a pin file at ``path``.

    Returns ``None`` when the file is missing, unreadable, or its first line
    is not a well-formed ``sha256sum``-style hash line -- callers distinguish
    "no pin" from "malformed pin" themselves via ``path.is_file()``, since
    this function alone can't tell those apart from its return value.
    """
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines:
        return None
    m = _HASH_LINE.match(lines[0])
    if not m:
        return None
    record = PinRecord(sha256=m.group(1), artefact_path=m.group(2))
    for line in lines[1:]:
        cm = _COMMENT_LINE.match(line.strip())
        if not cm:
            continue
        fields = {k.lower(): v for k, v in _FIELD.findall(cm.group(1))}
        record.origin = fields.get("origin")
        record.anchor = fields.get("anchor")
        record.date = fields.get("date")
        record.host = fields.get("host")
        break
    return record


#: 0056 clause 3's unconditional field set. `anchor` is deliberately absent:
#: clause 3 requires it "where one exists", which is a caller's fact, not this
#: record's -- see :func:`missing_metadata`.
REQUIRED_FIELDS = ("origin", "date", "host")


def missing_metadata(record: "PinRecord | None", anchor_expected: bool) -> list[str]:
    """Which of 0056 clause 3's fields ``record`` fails to carry, sorted.

    **One definition, two readers, deliberately.** The checker
    (`auditor_conversation_map_pin`) asks whether a pin is complete; the writer
    (`run.py pin bump`) asks whether there is anything left to write. Those must
    be the same question or the estate acquires a rule its own remedy cannot
    satisfy -- which is exactly what happened on 2026-08-31: the auditor demanded
    clause 3's fields, `pin bump` short-circuited on hash equality alone, and the
    printed remedy ran to completion while changing nothing. A hash-only pin was
    therefore permanently unfixable through the sanctioned path.

    So the field list lives here, in the read-only mechanism both sides already
    import, and neither restates it. This is not the rule's *enforcement* (0052
    keeps that in the checker that cites 0056); it is the rule's *definition*,
    and two copies of a definition is the failure mode this whole session was
    cataloguing.

    ``anchor_expected`` is the caller's answer to clause 3's "where one exists":
    true where git is available and an anchor could have been recorded, false
    where its absence is unknowable rather than wrong.

    ``None`` -- a missing or malformed pin -- reports nothing here. That is
    `verify_pin`'s finding to make, and reporting it twice would double-count.
    """
    if record is None:
        return []
    missing = [f for f in REQUIRED_FIELDS if not getattr(record, f, None)]
    if anchor_expected and not record.anchor:
        missing.append("anchor")
    return sorted(missing)


def hash_file(path: Path) -> str:
    """The sha256 hex digest of ``path``'s bytes. Public so `run.py pin bump`
    (the only sanctioned writer, per 0045 clause 4) can compute a fresh pin
    without reaching into this module's internals."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_pin(pin_path: Path, artefact_path: Path, commit_exists=None) -> PinCheck:
    """Check ``artefact_path`` against the pin recorded at ``pin_path``.

    ``commit_exists`` is the sha-resolver, injected so a tester can drive
    this without a real repository -- the same shape as
    ``auditor_uat_stamp.check``'s ``commit_exists``. ``None`` means "git
    unavailable": the anchor check is skipped (state ``git-unavailable``),
    never failed outright.

    Never writes to either path. A mismatch is reported with both hashes and
    both files are left exactly as found (0045 clause 2).
    """
    record = parse_pin_file(pin_path)

    if record is None:
        if pin_path.is_file():
            return PinCheck("pin-malformed", pin_path, artefact_path, None, None,
                             [f"{pin_path}: pin file present but its first line "
                              f"is not a well-formed sha256sum-style hash line"])
        if artefact_path.is_file():
            return PinCheck("unpinned", pin_path, artefact_path, None, None,
                             [f"{artefact_path}: exists with no pin recorded "
                              f"at {pin_path}"])
        return PinCheck("absent", pin_path, artefact_path, None, None, [])

    if not artefact_path.is_file():
        return PinCheck("artefact-absent", pin_path, artefact_path,
                         record.sha256, None, [])

    actual = hash_file(artefact_path)
    if actual != record.sha256:
        return PinCheck("mismatch", pin_path, artefact_path, record.sha256, actual, [
            f"{artefact_path}: HASH MISMATCH against pin {pin_path}. "
            f"Recorded: {record.sha256}  Actual: {actual}. Per DECISIONS 0045 "
            f"clause 2 this is reported, not repaired -- the artefact is left "
            f"exactly as found; re-pin deliberately with `run.py pin bump` "
            f"once the drift is understood."])

    if record.anchor:
        if commit_exists is None:
            return PinCheck("git-unavailable", pin_path, artefact_path,
                             record.sha256, actual, [])
        if not commit_exists(record.anchor):
            return PinCheck("anchor-unresolvable", pin_path, artefact_path,
                             record.sha256, actual, [
                f"{pin_path}: anchor '{record.anchor}' does not resolve to a "
                f"commit in this repository. Per DECISIONS 0045 clause 3 this "
                f"is a violation, not a silent pass."])

    return PinCheck("matches", pin_path, artefact_path, record.sha256, actual, [])


def commit_exists_resolver(root: Path = TOOLKIT_ROOT):
    """A ``commit_exists`` resolver bound to ``root``, or ``None`` when
    ``root`` isn't a git checkout at all -- mirrors
    ``auditor_uat_stamp``'s degrade-to-skip outside a checkout: an absent
    git is not evidence of a bad pin.
    """
    if not is_git_repo(root):
        return None

    def _resolve(sha: str) -> bool:
        return run_git(root, "cat-file", "-t", f"{sha}^{{commit}}") == "commit"

    return _resolve


def format_pin_line(sha256: str, artefact_rel_path: str) -> str:
    """The first, sha256sum-compatible line of a pin file."""
    return f"{sha256}  {artefact_rel_path}"


def format_pin_comment(*, origin: str, anchor: str | None, date: str, host: str) -> str:
    """The second, metadata-carrying comment line of a pin file. ``anchor``
    may be ``None`` when no commit anchors the pin (an untracked artefact
    with no repo history of its own yet)."""
    parts = [f"origin={origin}"]
    if anchor:
        parts.append(f"anchor={anchor}")
    parts.append(f"date={date}")
    parts.append(f"host={host}")
    return "# pin: " + " ".join(parts)
