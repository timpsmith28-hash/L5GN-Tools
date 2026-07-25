"""todo_adr_scanner -- sweeps TODO/FIXME markers and ADR status for a project.

Scope discipline (`COWORK_BRIEF_scanner_bugfixes.md` Task A): every content walk
goes through the shared :class:`~l5gntools.scanners._scope.Scope`, so the scanner
never reads a gitignored, vendored or data/chat path. The motivating bug was this
scanner mining 298 "TODO"-shaped substrings out of a gitignored
``raw_claude_files/conversations.json`` -- inflating the report until it truncated
mid-write, *and* reaching into exactly the personal chat content the estate is
built to wall off. It now scans source and doc files only, and reports what it
skipped and why.

Marker output is capped honestly (Task B): `markers` may be a bounded slice, but
`truncated` and `marker_count` always carry the true figure -- never a silent cut.
"""
from __future__ import annotations

from ..contract import SAFE

import re
from pathlib import Path

from ..common import capped, iter_files, rel
from ._scope import Scope

NAME = "todo_adr_scanner"
DESCRIPTION = "Collects TODO/FIXME/HACK markers and an ADR status census."
ESTATE_LEVEL = False
SAFETY = SAFE

_MARKER = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s-]*(.{0,120})")
_ADR_STATUS = re.compile(r"(?i)^\s*(?:\*\*)?status(?:\*\*)?\s*[:=]\s*(.+)$", re.MULTILINE)
_ADR_TITLE = re.compile(r"^#\s+(.*)", re.MULTILINE)
_CODE_SUFFIXES = (".py", ".sh", ".js", ".ts", ".html", ".css", ".json", ".md")

#: Honest ceiling on the emitted marker list. A well-scoped project sits in the
#: low tens; this is the safety net against a single pathological source blowing
#: the report past what the renderer can emit (Task B).
MARKER_CAP = 500

# --- Decision records (governance Task B; bugfix Task C) ---------------------
# An append-only DECISIONS.md is ONE file holding MANY entries (`## NNNN — title`)
# -- count entries, not files. Each entry declares a status; the tier count is the
# defensibility signal ("this project's decisions are 80% CONFIRMED/accepted").
_DECISION_ENTRY = re.compile(r"(?m)^##\s+(\d+)\b.*$")
_DECISION_STATUS = re.compile(r"(?i)status(?:\*\*)?\s*[:=]\s*\*{0,2}\s*([A-Za-z]+)")
# The two status vocabularies this estate uses: WizForge's CONFIRMED/ASSUMED/
# PENDING and the trinity's accepted/superseded. Unknown words are counted as
# 'other' rather than force-fit into a tier.
_TIER_MAP = {
    "confirmed": "CONFIRMED", "assumed": "ASSUMED", "pending": "PENDING",
    "accepted": "accepted", "superseded": "superseded",
}
# "Open questions / Open decisions" sections hold pending design decisions
# wherever they appear (both r141 docs carry one). Their list items count PENDING.
_OPEN_HEADING = re.compile(r"(?im)^#{1,6}\s+open\s+(?:questions|decisions)\b")
_ANY_HEADING = re.compile(r"(?m)^#{1,6}\s")
_LIST_ITEM = re.compile(r"(?m)^\s*(?:[-*+]|\d+\.)\s+\S")


def parse_decisions(text: str) -> tuple[int, dict]:
    """`(entry_count, {tier: count})` for a DECISIONS.md-style log. Pure."""
    entries = list(_DECISION_ENTRY.finditer(text))
    tiers: dict[str, int] = {}
    for i, m in enumerate(entries):
        end = entries[i + 1].start() if i + 1 < len(entries) else len(text)
        s = _DECISION_STATUS.search(text[m.end():end])
        tier = _TIER_MAP.get(s.group(1).lower()) if s else None
        key = tier or "other"
        tiers[key] = tiers.get(key, 0) + 1
    return len(entries), tiers


def parse_open_questions(text: str) -> tuple[int, int]:
    """`(#open-questions sections, #list items within them)`. Pure. Counts the
    section's list items without parsing the prose."""
    sections = items = 0
    for m in _OPEN_HEADING.finditer(text):
        body = text[m.end():]
        nl = body.find("\n")
        body = body[nl + 1:] if nl >= 0 else ""
        nxt = _ANY_HEADING.search(body)
        section = body[:nxt.start()] if nxt else body
        sections += 1
        items += len(_LIST_ITEM.findall(section))
    return sections, items


def scan(target: Path) -> dict:
    target = Path(target)
    scope = Scope(target)
    markers: list[dict] = []
    for path in iter_files(target, suffixes=_CODE_SUFFIXES):
        if scope.skip(path):
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

    # Decision records: DECISIONS.md entries (root + docs/), tier-counted, plus
    # any "Open questions/decisions" section anywhere, folded into PENDING.
    decisions_count = 0
    decision_tiers: dict[str, int] = {}
    for dpath in (target / "DECISIONS.md", target / "docs" / "DECISIONS.md"):
        if dpath.is_file():
            c, tiers = parse_decisions(dpath.read_text(encoding="utf-8", errors="ignore"))
            decisions_count += c
            for k, val in tiers.items():
                decision_tiers[k] = decision_tiers.get(k, 0) + val

    open_sections = open_items = 0
    for path in iter_files(target, suffixes=(".md",)):
        if scope.skip(path):
            continue
        try:
            s, it = parse_open_questions(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        open_sections += s
        open_items += it
    if open_items:
        decision_tiers["PENDING"] = decision_tiers.get("PENDING", 0) + open_items

    kept, truncated, true_count = capped(markers, MARKER_CAP)
    return {
        "project": target.name,
        "marker_count": true_count,
        "markers_by_tag": by_tag,
        "markers": kept,
        "truncated": truncated,
        "marker_cap": MARKER_CAP,
        "adr_count": len(adrs),
        "adrs": adrs,
        # Decision-record census: both conventions side by side (Task B.3).
        "decisions_count": decisions_count,
        "decision_tiers": decision_tiers,
        "open_questions": {"sections": open_sections, "items": open_items},
        "scope": scope.report(),
    }
