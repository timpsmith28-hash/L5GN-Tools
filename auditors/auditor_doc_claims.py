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
"""
from __future__ import annotations

import re
from pathlib import Path

import verify

_ROOT = Path(__file__).resolve().parent.parent

# Matches "4 auditors + 18 hermetic testers", "4 auditors + 14 testers",
# "registers **4 auditors + 14 testers**". Optional single adjective (e.g.
# 'hermetic') before 'testers'. Case-insensitive; tolerant of markdown bold.
_CLAIM = re.compile(
    r"(\d+)\s+auditors?\s*\+\s*(\d+)\s+(?:[A-Za-z]+\s+)?testers?",
    re.IGNORECASE,
)


def find_claims(text: str) -> list[tuple[int, int, int]]:
    """Return [(auditors_claimed, testers_claimed, char_offset), ...]."""
    return [(int(m.group(1)), int(m.group(2)), m.start())
            for m in _CLAIM.finditer(text)]


def violations_in(text: str, actual_auditors: int, actual_testers: int,
                  label: str = "doc") -> list[str]:
    """Pure, file-independent check -- the testable core of run()."""
    out: list[str] = []
    for claimed_a, claimed_t, pos in find_claims(text):
        if claimed_a != actual_auditors or claimed_t != actual_testers:
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
    v: list[str] = []
    for path in _docs():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            v.append(f"{path.name}: unreadable ({exc})")
            continue
        rel = path.relative_to(_ROOT).as_posix()
        v.extend(violations_in(text, actual_auditors, actual_testers, label=rel))
    return v
