"""auditor_doc_claims -- fail the gate when a machine-checkable documented claim
contradicts the code.

The estate's whole purpose is catching drift between what is *said* and what is
*done*, yet nothing checked the docs against the code -- HANDOFF once claimed 18
testers when `verify.py` had 14, and only a cold read caught it. This auditor
closes that self-referential gap.

Narrow and mechanical by design (COWORK brief Task D): it checks exactly ONE
class of claim -- the compound gate count "N auditors + M testers" -- against
`verify.py`'s registered `AUDITORS` / `TESTERS` lists, which are the single
unambiguous source of truth for those numbers. It deliberately does NOT parse
prose. A small auditor that always runs beats a large one that rots; extend only
to claims with one authoritative source.

The compound "N auditors + M testers" pattern is specific enough that narrative
mentions of a *past* count -- e.g. "HANDOFF once claimed 18 testers when
verify.py had 14" -- are not matched: only a present-tense assertion of BOTH
counts together, in that order, trips it.

Docs scanned: `README.md` and every `docs/*.md`.

## gate-frozen: claims about a finished doc are history, not a present claim

The auditor's job is claims about the *current* tree. A doc that has already
declared itself finished and frozen to a specific commit is testimony about
that moment, not a live assertion -- the auditor already ignores past-tense
narrative mentions (see above); this extends the same principle to a whole
file rather than a single sentence, via an explicit marker instead of prose
sniffing:

    <!-- gate-frozen: commit=<sha> -->

Placed in the first ~15 lines of a doc, it exempts that file's "N auditors +
M testers" claims from the live-count diff. The marker must earn the
exemption -- it is not a free pass:

  * `commit=` is required and must resolve to a real commit in this repo (the
    same SHA-resolver seam `auditor_uat_stamp` uses -- injected, so the
    tester stays hermetic and git-absence degrades to "can't verify" rather
    than a false failure, never a free exemption).
  * A malformed marker (no `commit=` key) is itself a violation, not a
    silent exemption -- you cannot fake-freeze a doc by writing garbage.
  * A handful of docs are *maintained*, not finished, and may never carry
    this marker at all (`NEVER_FREEZE` below) -- their claims are
    present-tense by definition, same list `docs-archivist` refuses to
    archive (docs/README.md §1); keep the two in sync.
"""
from __future__ import annotations

import re
from pathlib import Path

import verify
from l5gntools.common import run_git

_ROOT = Path(__file__).resolve().parent.parent

# Matches "4 auditors + 18 hermetic testers", "4 auditors + 14 testers",
# "registers **4 auditors + 14 testers**", "6 auditors + **37** testers"
# (bold wrapped around the digits themselves, not just the whole phrase).
# Optional single adjective (e.g. 'hermetic') before 'testers'.
# Case-insensitive; tolerant of markdown bold in either position.
_CLAIM = re.compile(
    r"(\d+)\s+auditors?\s*\+\s*\*{0,2}(\d+)\*{0,2}\s+(?:[A-Za-z]+\s+)?testers?",
    re.IGNORECASE,
)

# <!-- gate-frozen: commit=<sha> -->
_MARKER = re.compile(r"<!--\s*gate-frozen:\s*(?P<body>[^>]*?)\s*-->", re.IGNORECASE)
_FIELD = re.compile(r"(\w+)\s*=\s*(\S+)")

# Docs that are *maintained*, not finished -- their claims are present-tense
# by definition, so a gate-frozen marker in any of them is itself a
# violation. Mirrors the docs-archivist skill's never-archive list
# (docs/README.md §1: "Never treat a trinity file ... as a candidate. They
# are maintained, not finished.") -- keep the two lists in sync; if one
# changes, check the other.
#
# KNIGHT_PLAYBOOK.md / PRODUCER_PLAYBOOK.md archived to docs/archive/ under
# DECISIONS 0036 (COWORK_BRIEF_unified_app.md Task 6) -- removed from this
# set because they no longer live at a docs/*.md path this auditor scans;
# docs/archive/ is exempt by design (see docs/README.md §3, "why the
# auditor stops at the archive door").
NEVER_FREEZE = frozenset({
    "README.md",
    "docs/README.md",
    "docs/INTENT.md",
    "docs/ARCHITECTURE.md",
    "docs/DECISIONS.md",
})


def find_claims(text: str) -> list[tuple[int, int, int]]:
    """Return [(auditors_claimed, testers_claimed, char_offset), ...]."""
    return [(int(m.group(1)), int(m.group(2)), m.start())
            for m in _CLAIM.finditer(text)]


def find_frozen_marker(text: str) -> dict[str, str] | None:
    """Return the gate-frozen marker's fields as a dict if one appears in the
    first ~15 lines of ``text``, else None. A marker with no 'commit' key
    parses to a dict missing that key -- callers must check for it, that is
    the malformed case, not an absent marker."""
    head = "\n".join(text.splitlines()[:15])
    m = _MARKER.search(head)
    if not m:
        return None
    return dict(_FIELD.findall(m.group("body")))


def _git_available() -> bool:
    return bool(run_git(_ROOT, "rev-parse", "--git-dir"))


def _commit_exists(sha: str) -> bool:
    """True when ``sha`` names a real commit object in this repository."""
    return run_git(_ROOT, "cat-file", "-t", f"{sha}^{{commit}}") == "commit"


def violations_in(text: str, actual_auditors: int, actual_testers: int,
                  label: str = "doc", commit_exists=None) -> list[str]:
    """Pure, file-independent check -- the testable core of run().

    ``commit_exists`` is the SHA-resolver, injected so the tester can drive
    this without a repository (mirrors `auditor_uat_stamp.check`). ``None``
    means "git unavailable": the SHA-resolution check is skipped (a marker
    with a syntactically present sha still earns its exemption), everything
    else still applies.
    """
    out: list[str] = []
    marker = find_frozen_marker(text)
    frozen_sha: str | None = None
    if marker is not None:
        if label in NEVER_FREEZE:
            out.append(
                f"{label}: gate-frozen marker not allowed -- this doc is "
                f"maintained, not finished (docs/README.md §1)"
            )
        sha = marker.get("commit")
        if not sha:
            out.append(
                f"{label}: gate-frozen marker is malformed -- 'commit=' is "
                f"required"
            )
        elif commit_exists is not None and not commit_exists(sha):
            out.append(
                f"{label}: gate-frozen marker names commit '{sha}', which "
                f"is not a commit in this repository"
            )
        elif label not in NEVER_FREEZE:
            frozen_sha = sha

    for claimed_a, claimed_t, pos in find_claims(text):
        if claimed_a != actual_auditors or claimed_t != actual_testers:
            if frozen_sha is not None:
                continue  # history, not a present-tense claim -- exempt
            line = text.count("\n", 0, pos) + 1
            out.append(
                f"{label}:{line}: doc claims '{claimed_a} auditors + "
                f"{claimed_t} testers' but verify.py registers "
                f"{actual_auditors} auditors + {actual_testers} testers"
            )
    return out


def _docs() -> list[Path]:
    paths: list[Path] = []
    readme = _ROOT / "README.md"
    if readme.is_file():
        paths.append(readme)
    docs = _ROOT / "docs"
    if docs.is_dir():
        paths.extend(sorted(docs.glob("*.md")))
    return paths


def run() -> list[str]:
    actual_auditors = len(verify.AUDITORS)
    actual_testers = len(verify.TESTERS)
    resolver = _commit_exists if _git_available() else None
    v: list[str] = []
    for path in _docs():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            v.append(f"{path.name}: unreadable ({exc})")
            continue
        rel = path.relative_to(_ROOT).as_posix()
        v.extend(violations_in(text, actual_auditors, actual_testers,
                               label=rel, commit_exists=resolver))
    return v
