"""Generate `docs/_decisions_map.md` from `docs/DECISIONS.md`.

Shape is generated; rationale is authored (DECISIONS 0030). This module reads
the log and emits four views of its citation graph -- threads, spine, orphans
and status. It is stdlib-only and imports nothing from the app tier
(0034 clause 3).

**The one prohibition that matters: this module never summarises, condenses or
paraphrases an entry.** Titles and numbers only. Where an entry carries a
"What would show this wrong" section, the map links to it and does not quote a
word of it -- that section and the uncomfortable half of Consequences are the
first things a condensing pass eats, and they are why the log is worth keeping.

**Determinism is a contract.** Run twice against an unchanged log, the output
is byte-identical, so no timestamp, no commit sha and no host is emitted.
`docs/_architecture_shape.md` stamps its producing commit; this file
deliberately does not, because its acceptance check is reproducibility rather
than provenance.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_RELPATH = "docs/DECISIONS.md"
DECISIONS_MAP_RELPATH = "docs/_decisions_map.md"

#: An entry heading: `## 0025 — <title>`.
_ENTRY_RE = re.compile(r"^##[ \t]+(\d{4})[ \t]*[—–-][ \t]*(.+?)[ \t]*$", re.M)

#: A citation is a zero-padded four-digit number. `2026` in a date cannot match,
#: because every entry number starts with a zero.
_CITE_RE = re.compile(r"(?<![\w-])(0\d{3})(?![\w-])")

#: A citation carrying a repo qualifier belongs to another repo's log (0043) and
#: is not an edge in this graph. The list is explicit on purpose: an earlier cut
#: matched "any word then a space", which read `0025 and 0036` as a cross-repo
#: citation of 0036 and silently dropped a real edge. A qualifier this repo has
#: not seen is better missed loudly than guessed at -- a new one added to a log
#: entry wants adding here, and until it is, it shows up as an ordinary edge
#: rather than vanishing.
_REPO_QUALIFIERS = (
    "sfds-", "wfa-", "va-",
    "sf-data-service ", "WizForgeAnalytics ", "ValidationAutomation ",
    "PricingModel ", "SolConfig ", "TSsToAssets ", "ChurnLevelIndicator ",
    "ActivityStatements ",
)

_STATUS_RE = re.compile(r"\*\*Status:\*\*[ \t]*([^·\n]*)")
_FALSIFIER_RE = re.compile(r"^\*\*What would show this wrong", re.M)

#: Citations run from `**Builds on:**` to whichever of these opens first.
_CITE_BLOCK_END = ("**Source:**", "**Context.**", "**Context:**")


class Entry:
    __slots__ = ("num", "title", "body", "status", "cites", "cross_repo",
                 "has_falsifier", "anchor")

    def __init__(self, num: str, title: str, body: str) -> None:
        self.num = num
        self.title = title
        self.body = body
        self.status = _status_of(body)
        self.cites, self.cross_repo = _citations_of(num, body)
        self.has_falsifier = bool(_FALSIFIER_RE.search(body))
        self.anchor = _slug(f"{num} — {title}")


def _slug(heading: str) -> str:
    """GitHub's heading-anchor algorithm, as far as this log needs it."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.U)
    return re.sub(r"[\s]+", "-", s)


def _status_of(body: str) -> str:
    m = _STATUS_RE.search(body)
    if not m:
        return "(none)"
    return " ".join(m.group(1).split()) or "(none)"


def _citations_of(num: str, body: str) -> tuple[list[str], list[str]]:
    """Numbers cited by this entry, and the cross-repo ones excluded.

    The window opens at `**Builds on:**` and closes at `**Source:**` or
    `**Context.**`. An entry with no `Builds on` cites nothing -- which is what
    makes it an orphan, and 0043 is the worked example of why a `Relates to:`
    naming another repo's 0023 must not be read as an edge here.
    """
    start = body.find("**Builds on:**")
    if start == -1:
        return [], []
    window = body[start:]
    ends = [window.find(tok) for tok in _CITE_BLOCK_END]
    ends = [e for e in ends if e > 0]
    if ends:
        window = window[: min(ends)]

    cites: list[str] = []
    cross: list[str] = []
    for m in _CITE_RE.finditer(window):
        n = m.group(1)
        if n == num:
            continue
        before = window[max(0, m.start() - 24): m.start()]
        if any(before.endswith(q) for q in _REPO_QUALIFIERS):
            if n not in cross:
                cross.append(n)
            continue
        if n not in cites:
            cites.append(n)
    return cites, cross


def parse(text: str) -> list[Entry]:
    marks = list(_ENTRY_RE.finditer(text))
    entries: list[Entry] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        entries.append(Entry(m.group(1), m.group(2), text[m.end(): end]))
    return entries


def _longest_chains(entries: list[Entry]) -> tuple[dict[str, int], list[list[str]]]:
    """Depth per entry, and every maximal chain at the deepest depth.

    An edge runs from a cited entry to the entry citing it, so a chain reads in
    the order the reasoning was built. Only edges to entries that exist are
    followed; a dangling citation is reported, never traversed.
    """
    by_num = {e.num: e for e in entries}
    parents = {e.num: [c for c in e.cites if c in by_num] for e in entries}
    depth: dict[str, int] = {}

    def d(n: str, seen: frozenset[str] = frozenset()) -> int:
        if n in depth:
            return depth[n]
        if n in seen:                      # a citation cycle cannot deepen a chain
            return 0
        best = 0
        for p in parents[n]:
            best = max(best, d(p, seen | {n}) + 1)
        depth[n] = best
        return best

    for e in sorted(by_num):
        d(e)

    chains: list[list[str]] = []

    def walk(n: str, tail: list[str]) -> None:
        here = [n] + tail
        ps = [p for p in parents[n] if depth[p] == depth[n] - 1]
        if not ps:
            chains.append(here)
            return
        for p in sorted(ps):
            walk(p, here)

    if depth:
        deepest = max(depth.values())
        for n in sorted(n for n, v in depth.items() if v == deepest):
            walk(n, [])
    return depth, chains


def _merge_chains(chains: list[list[str]]) -> list[tuple[int, list[list[str]]]]:
    """Group equal-length chains and merge them position by position.

    `0037/0040` at one position means the thread runs through either. This is a
    rendering of the set of chains, not a summary of them: no chain is dropped
    and no entry is omitted, so a reader can still recover which entries sit at
    which depth. Nothing about what an entry *says* is involved.
    """
    by_len: dict[int, list[list[str]]] = defaultdict(list)
    for ch in chains:
        by_len[len(ch)].append(ch)
    out: list[tuple[int, list[list[str]]]] = []
    for ln in sorted(by_len, reverse=True):
        group = by_len[ln]
        merged = [sorted({ch[i] for ch in group}) for i in range(ln)]
        out.append((ln, merged))
    return out


def render(entries: list[Entry]) -> str:
    by_num = {e.num: e for e in entries}
    cited_by: dict[str, list[str]] = defaultdict(list)
    dangling: list[tuple[str, str]] = []
    cross: list[tuple[str, str]] = []
    for e in entries:
        for c in e.cites:
            if c in by_num:
                cited_by[c].append(e.num)
            else:
                dangling.append((e.num, c))
        for c in e.cross_repo:
            cross.append((e.num, c))

    depth, chains = _longest_chains(entries)
    orphans = [e for e in entries if not e.cites]

    def ref(n: str) -> str:
        e = by_num.get(n)
        if e is None:
            return f"`{n}` *(no such entry)*"
        return f"[`{n}`](DECISIONS.md#{e.anchor})"

    def line(n: str) -> str:
        e = by_num[n]
        f = f" · [what would show this wrong](DECISIONS.md#{e.anchor})" if e.has_falsifier else ""
        return f"- {ref(n)} — {e.title}{f}"

    L: list[str] = []
    A = L.append
    A("<!-- GENERATED by l5gntools/decisions_map.py -- DO NOT HAND-EDIT.")
    A("     Regenerate with `python run.py decisions-map` in the same commit as any")
    A("     change to docs/DECISIONS.md (DECISIONS 0030; CONVENTION_commits.md 6).")
    A("     No commit sha or timestamp is stamped here on purpose: run twice against")
    A("     an unchanged log, this file is byte-identical. -->")
    A("")
    A("# The decisions log, as a shape")
    A("")
    A("Generated, never hand-edited (**0030**). `docs/DECISIONS.md` is the authority "
      "and holds every word of the reasoning; this file holds only numbers, titles "
      "and the citation graph between them.")
    A("")
    A("**Nothing here is a summary.** No entry's context, decision, consequences or "
      "falsifier is paraphrased, condensed or quoted. Where an entry carries a "
      "*What would show this wrong* section, this file links to it and says nothing "
      "about what it says. If you are reading this instead of the log, you are "
      "reading the wrong file.")
    A("")
    A(f"**{len(entries)} entries.**")
    A("")

    A("## 1. Threads")
    A("")
    A("Chains followed through `**Builds on:**` citations, read in the order the "
      "reasoning was built. Only the deepest chains are listed; every entry's depth "
      "is the longest such chain ending at it.")
    A("")
    if chains:
        A(f"Deepest thread today: **{len(chains[0])} entries deep**, "
          f"across **{len(chains)}** distinct chains.")
        A("")
        A("Chains of equal length are merged position by position — `a/b` means the "
          "thread runs through either, not through both. Every chain is listed "
          "somewhere in the merge; none is dropped.")
        A("")
        for ln, merged in _merge_chains(chains):
            A(f"- **{ln} deep:** "
              + " → ".join("/".join(ref(n) for n in step) for step in merged))
    else:
        A("*No citations found — the log has no threads.*")
    A("")
    buckets: dict[int, list[str]] = defaultdict(list)
    for n, v in depth.items():
        buckets[v].append(n)
    A("| depth | entries |")
    A("|---|---|")
    for v in sorted(buckets):
        A(f"| {v} | " + ", ".join(ref(n) for n in sorted(buckets[v])) + " |")
    A("")

    A("## 2. Spine")
    A("")
    A("Most-cited entries — the ones the rest of the log is built on. A high count "
      "here means changing that entry moves everything that cites it.")
    A("")
    ranked = sorted(cited_by.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if ranked:
        for n, citers in ranked:
            e = by_num[n]
            f = (f" · [what would show this wrong](DECISIONS.md#{e.anchor})"
                 if e.has_falsifier else "")
            A(f"- {ref(n)} **×{len(citers)}** — {e.title}{f}")
            A("  - cited by " + ", ".join(ref(c) for c in sorted(citers)))
    else:
        A("*Nothing is cited.*")
    A("")

    A("## 3. Orphans")
    A("")
    A("Entries citing nothing. **An orphan is not a lesser entry** — several are "
      "load-bearing and are simply unreachable by following citations, which means "
      "a reader walking the graph will never arrive at them.")
    A("")
    A(f"**{len(orphans)} of {len(entries)}.**")
    A("")
    for e in orphans:
        A(line(e.num))
    A("")

    A("## 4. Status")
    A("")
    counts: dict[str, int] = defaultdict(int)
    for e in entries:
        counts[e.status] += 1
    A("| status | entries |")
    A("|---|---|")
    for s in sorted(counts):
        A(f"| {s} | {counts[s]} |")
    A("")
    proposed = [e for e in entries if e.status.startswith("proposed")]
    A(f"**{len(proposed)} proposed** — not authority, and not citable as such "
      "(`CONVENTION_decisions.md` 3):")
    A("")
    for e in proposed:
        A(line(e.num))
    A("")
    falsified = [e for e in entries if e.has_falsifier]
    A(f"**{len(falsified)} of {len(entries)} entries carry a "
      "*What would show this wrong* section.** Links only:")
    A("")
    for e in falsified:
        A(f"- {ref(e.num)} — [what would show this wrong](DECISIONS.md#{e.anchor})")
    A("")

    A("## 5. What the generator found")
    A("")
    if dangling:
        A("**Dangling citations** — a number cited that no entry carries:")
        A("")
        for src, n in sorted(set(dangling)):
            A(f"- {ref(src)} cites `{n}`, which does not exist")
    else:
        A("No dangling citations: every number cited resolves to an entry.")
    A("")
    if cross:
        A("**Cross-repo citations**, excluded from the graph (**0043**):")
        A("")
        for src, n in sorted(set(cross)):
            A(f"- {ref(src)} cites `{n}` with a repo qualifier")
    else:
        A("No cross-repo citations inside a `Builds on` window.")
    A("")
    return "\n".join(L) + "\n"


def write_decisions_map(root: Path = TOOLKIT_ROOT) -> Path:
    src = root / DECISIONS_RELPATH
    entries = parse(src.read_text(encoding="utf-8"))
    seen: dict[str, int] = defaultdict(int)
    for e in entries:
        seen[e.num] += 1
    dupes = sorted(n for n, c in seen.items() if c > 1)
    if dupes:
        raise SystemExit(
            "decisions-map: duplicate entry number(s) "
            + ", ".join(dupes)
            + " -- unrecoverable in an append-only log "
              "(CONVENTION_decisions.md 3). Nothing was written."
        )
    dest = root / DECISIONS_MAP_RELPATH
    dest.write_text(render(entries), encoding="utf-8", newline="\n")
    return dest
