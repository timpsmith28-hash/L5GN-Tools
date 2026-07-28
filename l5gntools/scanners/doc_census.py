"""doc_census -- inventory of markdown / documentation for a project.

Two questions layered on top of the plain inventory (DECISIONS 0026, brief
`COWORK_BRIEF_doc_provenance_coverage.md`):

* **What kind of document is this?** (Task A) -- a cheap, explicit,
  path-and-name classification into the load-bearing shapes both estates
  already use, never inferred from prose. A classifier that reads content is
  the large check that rots; a filename convention is the small one that
  always runs (`auditor_doc_claims`'s own reasoning, reused here on purpose).
* **Was this document written, or produced?** (Task B) -- `provenance`.
  Every ratio in this module is computed over ``authored`` documents only,
  with the ``generated`` count reported beside it, never dropped. A ratio
  computed over a denominator full of machine output measures nothing, and
  the personal estate's two vault/citadel projects are the proof: 646 of its
  824 documents are generated output, and counting them as undocumented prose
  would be the false report, not the true one.

Both rules are **path-and-name only**, per the working rule that content is
never read to decide provenance or type -- the H1/heading/word scan below
remains, but nothing downstream of it feeds a classification decision.
"""
from __future__ import annotations

from ..contract import SAFE

import re
import statistics
from pathlib import Path

from ..common import iter_files, rel
from ._scope import Scope

NAME = "doc_census"
DESCRIPTION = "Markdown inventory: titles, headings, sizes, type and provenance."
ESTATE_LEVEL = False
SAFETY = SAFE

_H1 = re.compile(r"^#\s+(.*)", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)

# --- Task A: document type -----------------------------------------------
#
# Ordered rules, first match wins. Structural (path-based) rules are tried
# before filename rules; within filename rules, the more specific convention
# (knowledge, decisions) is tried before the general shapes so a document
# named e.g. "DECISIONS_BRIEF.md" is not swallowed by the wrong bucket.
#
# Each predicate is stated as the one sentence it is: a filename or path
# substring test, nothing more.
_ADR_SEGMENT = "adr"
_KNOWLEDGE_MARKER = "_knowledge"          # 0026: unanchored, case-insensitive
_TYPE_MARKERS: tuple[tuple[str, str], ...] = (
    # (doc_type, uppercase substring the stem must contain)
    ("decisions", "DECISIONS"),
    ("intent", "INTENT"),
    ("architecture", "ARCHITECTURE"),
    ("runbook", "RUNBOOK"),
    ("runbook", "PLAYBOOK"),
    ("uat", "UAT"),
    ("uat", "CHECKLIST"),
    ("plan", "PLAN"),
    ("plan", "STATUS"),
    ("brief", "BRIEF"),
    ("report", "REPORT"),
)
#: The load-bearing types the Task C coverage grid asks about. `unclassified`
#: is deliberately excluded -- it is "ordinary prose", not a gap.
GRID_TYPES: tuple[str, ...] = (
    "knowledge", "adr", "decisions", "readme", "claude_md", "glossary",
    "intent", "architecture", "runbook", "uat", "plan", "brief", "report",
)


def classify_doc_type(relpath: str) -> str:
    """The document's shape, by filename and path alone (Task A, 0026).

    One sentence each:
    - ``adr``: an ``adr`` path segment (the existing ``adr_files`` rule, kept).
    - ``knowledge``: stem contains ``_knowledge`` case-insensitively, unanchored.
    - ``claude_md`` / ``readme`` / ``glossary``: the existing exact-name rules.
    - ``decisions`` / ``intent`` / ``architecture`` / ``runbook`` (playbook too)
      / ``uat`` (checklist too) / ``plan`` (status too) / ``brief`` / ``report``:
      stem contains the marker word, case-insensitive, unanchored.
    - ``unclassified``: none of the above -- not a failure state.
    """
    parts = relpath.split("/")
    name = parts[-1]
    name_lower = name.lower()
    stem = name[:-3] if name_lower.endswith(".md") else name
    stem_upper = stem.upper()

    if any(p.lower() == _ADR_SEGMENT for p in parts[:-1]):
        return "adr"
    if _KNOWLEDGE_MARKER in stem.lower():
        return "knowledge"
    if name_lower == "claude.md":
        return "claude_md"
    if name_lower.startswith("readme"):
        return "readme"
    if name_lower == "glossary.md":
        return "glossary"
    for doc_type, marker in _TYPE_MARKERS:
        if marker in stem_upper:
            return doc_type
    return "unclassified"


# --- Task B: provenance ----------------------------------------------------
#
# Candidate rule, verified against both estates before shipping (brief Task
# B): a document is `generated` if any directory segment (not the filename
# itself) begins with `.` or `_`, or is one of a short explicit list earned by
# a real project on this estate rather than assumed in the abstract.
#
# Verified 2026-07-28 against the personal estate's real `data/estate.json`
# (824 docs): the dot/underscore rule alone catches 694, the explicit list
# adds 40 more (734 total) -- all of it landing exactly on the five projects
# named in the brief's evidence table (CID 341/358, Armory_v4 286/288,
# Crystal-Spire 53/97, Armory_v2 21/27, Archive 24/25), and zero elsewhere.
# `AutoFiles` earns its place by one project alone (L5GN-Archive) -- it does
# not generalise the way the underscore/dot convention does, and is kept
# because it is real, not hypothetical.
_GENERATED_DIR_NAMES = frozenset({"output", "logs", "AutoFiles"})


def classify_provenance(relpath: str) -> str:
    """``authored`` or ``generated``, by directory segment alone (Task B)."""
    for seg in relpath.split("/")[:-1]:
        if seg.startswith(".") or seg.startswith("_"):
            return "generated"
        if seg in _GENERATED_DIR_NAMES:
            return "generated"
    return "authored"


def scan(target: Path) -> dict:
    scope = Scope(target)
    docs: list[dict] = []
    type_tally: dict[str, int] = {}
    generated_count = 0

    for path in iter_files(target, suffixes=(".md",)):
        if scope.skip(path):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        m = _H1.search(text)
        relpath = rel(path, target)
        doc_type = classify_doc_type(relpath)
        provenance = classify_provenance(relpath)
        if provenance == "authored":
            type_tally[doc_type] = type_tally.get(doc_type, 0) + 1
        else:
            generated_count += 1
        docs.append({
            "path": relpath,
            "title": m.group(1).strip() if m else "",
            "headings": len(_HEADING.findall(text)),
            "words": len(text.split()),
            "bytes": len(text.encode("utf-8")),
            "doc_type": doc_type,
            "provenance": provenance,
        })

    docs.sort(key=lambda d: d["path"])
    doc_count = len(docs)
    authored_count = doc_count - generated_count
    # "Classified" means authored AND typed -- generated documents are excluded
    # from both the numerator and the denominator so the ratio stays honest
    # (0026: counts always beside the ratio, and the ratio never over a
    # denominator full of machine output).
    classified_count = sum(n for t, n in type_tally.items() if t != "unclassified")
    classified_pct = (round(100 * classified_count / authored_count, 1)
                       if authored_count else 0.0)

    return {
        "project": target.name,
        "doc_count": doc_count,
        "authored_count": authored_count,
        "generated_count": generated_count,
        "classified_count": classified_count,
        "classified_pct": classified_pct,
        "type_tally": type_tally,
        # Kept for existing consumers (report.py's Docs tab, estate_diff):
        # each is now the authored-only count of that Task A type, so a
        # generated project's tree does not inflate them.
        "has_readme": bool(type_tally.get("readme")),
        "has_claude_md": bool(type_tally.get("claude_md")),
        "has_glossary": bool(type_tally.get("glossary")),
        "adr_files": type_tally.get("adr", 0),
        "docs": docs,
        "scope": scope.report(),
    }


# --- Task D: out-of-band document count ------------------------------------
#
# Threshold relative to the estate, not a hardcoded number (brief Task D):
# a project's raw `doc_count` (all provenance -- this is a payload/scale
# signal, not a governance one) is flagged when it exceeds
# `OUT_OF_BAND_MULTIPLIER` times the estate's median `doc_count`. The median
# is only meaningful with at least `OUT_OF_BAND_MIN_PROJECTS` projects; below
# that, no flag is raised rather than one computed from noise.
#
# Chosen and verified against the personal estate's real numbers
# (doc_counts [1, 9, 19, 25, 27, 97, 288, 358], median 26): 3x the median
# (78) flags exactly Crystal-Spire (97), Armory_v4 (288) and CID (358) --
# the three projects the brief's own evidence table calls out as the ones
# worth surfacing, and none of the small projects.
OUT_OF_BAND_MULTIPLIER = 3.0
OUT_OF_BAND_MIN_PROJECTS = 3


def out_of_band(projects: list[dict]) -> list[dict]:
    """Projects whose `doc_census.doc_count` is wildly out of scale with the
    rest of the estate. Each entry in ``projects`` is a per-project report
    dict as assembled by `report.build_estate` (i.e. carries a `doc_census`
    key, not the raw scan result)."""
    counts = [(p.get("name", "?"), (p.get("doc_census") or {}).get("doc_count", 0))
              for p in projects]
    counts = [(name, n) for name, n in counts if n]
    if len(counts) < OUT_OF_BAND_MIN_PROJECTS:
        return []
    median = statistics.median(n for _, n in counts)
    threshold = median * OUT_OF_BAND_MULTIPLIER
    return [{"project": name, "doc_count": n, "median": median,
              "threshold": threshold}
            for name, n in counts if n > threshold]
