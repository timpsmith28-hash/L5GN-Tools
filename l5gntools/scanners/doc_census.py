"""doc_census -- inventory of markdown / documentation for a project."""
from __future__ import annotations

from ..contract import SAFE

import re
from pathlib import Path

from ..common import iter_files, rel

NAME = "doc_census"
DESCRIPTION = "Markdown inventory: titles, headings, sizes, README/ADR presence."
ESTATE_LEVEL = False
SAFETY = SAFE

_H1 = re.compile(r"^#\s+(.*)", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)


def scan(target: Path) -> dict:
    docs: list[dict] = []
    adr_count = 0
    has_readme = has_claude = has_glossary = False

    for path in iter_files(target, suffixes=(".md",)):
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = _H1.search(text)
        name_lower = path.name.lower()
        if name_lower.startswith("readme"):
            has_readme = True
        if name_lower == "claude.md":
            has_claude = True
        if name_lower == "glossary.md":
            has_glossary = True
        if "adr" in {p.lower() for p in path.parts}:
            adr_count += 1
        docs.append({
            "path": rel(path, target),
            "title": m.group(1).strip() if m else "",
            "headings": len(_HEADING.findall(text)),
            "words": len(text.split()),
            "bytes": len(text.encode("utf-8")),
        })

    docs.sort(key=lambda d: d["path"])
    return {
        "project": target.name,
        "doc_count": len(docs),
        "has_readme": has_readme,
        "has_claude_md": has_claude,
        "has_glossary": has_glossary,
        "adr_files": adr_count,
        "docs": docs,
    }
