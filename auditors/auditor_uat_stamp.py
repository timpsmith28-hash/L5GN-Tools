"""auditor_uat_stamp -- fail the gate when an acceptance claim has no provenance.

`verify.py` answers "does the code work". It cannot answer "does the code do what
was asked" -- that is a human walking the UAT, and no auditor will ever judge it.
But the *claim* that a UAT was walked is an artifact, and an artifact can be
checked for where it came from.

The motivating incident: a round-3 results log asserted a gate state ("5 auditors
and 18 testers") that matched no version of this tree -- 18 was a stale number
recovered from an archived HANDOFF, laundered back into a live doc by a thread
that had read the archive. Nothing could tell whether that meant the walking
machine was on a different commit or the number was invented, because the
document carried no commit at all. Every scan output already stamps
`toolkit_git_info()`; the one document asserting "this was tested" did not.

So: any `UAT_*_results.md` in core `docs/` must carry a stamp naming the commit
it was walked against.

    <!-- uat: commit=48ce16d dirty=false host=l5gn-castle walked=2026-07-21 gate=5a/23t -->

Checked, in order:

  1. the stamp exists and parses,
  2. `commit` resolves to a real object in this repository,
  3. `gate`, if present, matches `verify.py`'s registered counts.

Deliberately NOT checked: whether the walk passed, whether the commit is an
ancestor of HEAD (a UAT walked on a branch is still a walked UAT), or anything
about the prose. This polices the origin of the claim, not the claim.

Not hermetic in the strict sense -- it shells out to `git` via
`l5gntools.common.run_git`, as `tester_common` already does. Outside a git
checkout (a tarball, a stale export) every check degrades to a skip rather than a
false failure: an absent git is not evidence of a bad stamp.

Scope: `docs/UAT_*_results.md`. Non-recursive, so `docs/archive/` is exempt for
the same reason it is exempt from `auditor_doc_claims` -- an archived log is
frozen testimony about a commit that has long since stopped being HEAD.
"""
from __future__ import annotations

import re
from pathlib import Path

import verify
from l5gntools.common import run_git

_ROOT = Path(__file__).resolve().parent.parent

# <!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<date> gate=<Na/Mt> -->
_STAMP = re.compile(r"<!--\s*uat:\s*(?P<body>[^>]*?)\s*-->", re.IGNORECASE)
_FIELD = re.compile(r"(\w+)\s*=\s*(\S+)")
_GATE = re.compile(r"^(\d+)a/(\d+)t$", re.IGNORECASE)

REQUIRED_FIELDS = ("commit", "walked")


def parse_stamp(text: str) -> dict | None:
    """The first uat stamp in ``text`` as a field dict, or None if absent."""
    m = _STAMP.search(text)
    if not m:
        return None
    return {k.lower(): v for k, v in _FIELD.findall(m.group("body"))}


def _git_available() -> bool:
    return bool(run_git(_ROOT, "rev-parse", "--git-dir"))


def _commit_exists(sha: str) -> bool:
    """True when ``sha`` names a real commit object in this repository."""
    return run_git(_ROOT, "cat-file", "-t", f"{sha}^{{commit}}") == "commit"


def check(text: str, label: str, actual_auditors: int, actual_testers: int,
          commit_exists=None) -> list[str]:
    """Pure, file-independent check -- the testable core of run().

    ``commit_exists`` is the SHA-resolver, injected so the tester can drive this
    without a repository. ``None`` means "git unavailable": the SHA check is
    skipped, everything else still applies.
    """
    stamp = parse_stamp(text)
    if stamp is None:
        return [f"{label}: no uat stamp -- a results log must name the commit it "
                f"was walked against: <!-- uat: commit=<sha> walked=<date> -->"]
    out: list[str] = []
    for field in REQUIRED_FIELDS:
        if not stamp.get(field):
            out.append(f"{label}: uat stamp is missing '{field}='")

    sha = stamp.get("commit")
    if sha and commit_exists is not None and not commit_exists(sha):
        out.append(f"{label}: uat stamp names commit '{sha}', which is not a "
                   f"commit in this repository")

    gate = stamp.get("gate")
    if gate:
        g = _GATE.match(gate)
        if not g:
            out.append(f"{label}: uat stamp gate='{gate}' is malformed "
                       f"(expected e.g. gate=5a/23t)")
        elif (int(g.group(1)), int(g.group(2))) != (actual_auditors, actual_testers):
            out.append(f"{label}: uat stamp claims gate {g.group(1)} auditors + "
                       f"{g.group(2)} testers but verify.py registers "
                       f"{actual_auditors} auditors + {actual_testers} testers")
    return out


def _logs() -> list[Path]:
    docs = _ROOT / "docs"
    if not docs.is_dir():
        return []
    return sorted(docs.glob("UAT_*_results.md"))


def run() -> list[str]:
    actual_auditors = len(verify.AUDITORS)
    actual_testers = len(verify.TESTERS)
    resolver = _commit_exists if _git_available() else None
    v: list[str] = []
    for path in _logs():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            v.append(f"{path.name}: unreadable ({exc})")
            continue
        rel = path.relative_to(_ROOT).as_posix()
        v.extend(check(text, rel, actual_auditors, actual_testers, resolver))
    return v
