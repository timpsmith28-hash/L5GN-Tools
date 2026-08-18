"""auditor_uat_sheet_readable -- a sheet the board can count, the sidebar must read.

`uat_sidebar.sheet_view` returns two answers about the same file in one
response: `sheet_boxes`, from `docs_board._count_checkboxes`, and `sections`,
from `parse_sheet`'s `_ITEM`. Nothing made them agree.

They did not. Six walk-sheets parsed as **zero items** while the board reported
5, 16, 18, 22, 22 and 64 open items on them, and one dropped 66 of its 85 --
silently, because a line `_ITEM` does not match is skipped rather than
reported. A sheet holding 64 unwalked checks rendered as an empty list, and
nothing anywhere said so.

This does not check that a sheet is well-formed; sheets are frozen when
written and several legitimate dialects exist. It checks that the two counts
**agree**, which is the property that was actually violated -- and it fails
loudly, because the failure it exists to catch is a parser reporting nothing
and being believed.

Imports only `chronicler.review.uat_sidebar`, which is stdlib-only at module
level (it re-exports `_count_checkboxes` from `docs_board` rather than keeping
a second copy), so this auditor runs with no web stack installed -- DECISIONS
0034's consequence paragraph requires that of the gate.
"""
from __future__ import annotations

from pathlib import Path

from chronicler.review.uat_sidebar import _count_checkboxes, parse_sheet

_DOCS = Path(__file__).resolve().parent.parent / "docs"


def check(path: Path) -> list[str]:
    """Findings for one sheet. Empty when the two counts agree."""
    boxes = _count_checkboxes(path)
    expected = boxes["done"] + boxes["open"]
    parsed = sum(len(sec["items"]) for sec in parse_sheet(path)["sections"])
    if parsed == expected:
        return []
    empty = " The sidebar renders this sheet as an empty list." if parsed == 0 else ""
    return [f"docs/{path.name}: the board counts {expected} checkbox item(s); "
            f"the UAT sidebar parses {parsed}.{empty} Widen `_ITEM` in "
            f"chronicler/review/uat_sidebar.py to cover this sheet's shape -- "
            f"do not edit the sheet, it is frozen (docs/README.md section 2)."]


def run() -> list[str]:
    if not _DOCS.is_dir():
        return []
    out: list[str] = []
    for path in sorted(_DOCS.glob("UAT_*.md")):
        if path.name.endswith("_results.md"):
            continue
        out.extend(check(path))
    return out
