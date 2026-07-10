"""todo_adr_scanner -- sweeps TODO/FIXME markers and ADR status for a project."""
from __future__ import annotations

from ..contract import SAFE

import re
from pathlib import Path

from ..common import is_vendored, iter_files, rel

NAME = "todo_adr_scanner"
DESCRIPTION = "Collects TODO/FIXME/HACK markers and an ADR status census."
ESTATE_LEVEL = False
SAFETY = SAFE

_MARKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.{0,120})")
_ADR_STATUS = re.compile(r"(?i)^\s*(?:\*\*)?status(?:\*\*)?\s*[:=]\s*(.+)$", re.MULTILINE)
_ADR_TITLE = re.compile(r"^#\s+(.*)", re.MULTILINE)
_CODE_SUFFIXES = (".py", ".sh", ".js", ".ts", ".html", ".css", ".json", ".md")


def scan(target: Path) -> dict:
    markers: list[dict] = []
    for path in iter_files(target, suffixes=_CODE_SUFFIXES):
        if is_vendored(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            m = _MARKER.search(line)
            if m:
                markers.append({
                    "path": rel(path, target), "line": i,
                    "tag": m.group(1), "text": m.group(2).strip(),
                })

    adrs: list[dict] = []
    for adr_dir in (target / "docs" / "adr", target / "adr"):
        if not adr_dir.is_dir():
            continue
        for path in sorted(adr_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            t = _ADR_TITLE.search(text)
            s = _ADR_STATUS.search(text)
            adrs.append({
                "file": path.name,
                "title": t.group(1).strip() if t else "",
                "status": s.group(1).strip() if s else "",
            })

    by_tag: dict[str, int] = {}
    for mk in markers:
        by_tag[mk["tag"]] = by_tag.get(mk["tag"], 0) + 1

    return {
        "project": target.name,
        "marker_count": len(markers),
        "markers_by_tag": by_tag,
        "markers": markers[:300],
        "adr_count": len(adrs),
        "adrs": adrs,
    }
