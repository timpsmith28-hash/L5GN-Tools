"""Generate `docs/_conformance_map.md` from `docs/DECISIONS.md` and
`docs/CONVENTION_*.md`.

Shape is generated; rationale is authored (**0030**). This module reports what
each rule-bearing document declares about its own subject and its own reader.
It is stdlib-only and imports nothing from the app tier (0034 clause 3).

The convention is `docs/CONVENTION_conformance.md` and it is the authority.

**This is a non-gating surface** (**0031**, and 0060 clause 7). It reports and
never repairs (**0045** clause 2): it adds no field to any ruling, edits no
convention, and touches no accepted entry's body. The only thing in this
arrangement that may go red is `auditors/auditor_rule_subjects.py`.

**Determinism is a contract**, as it is for `decisions_map`: run twice against
an unchanged tree and the output is byte-identical, so no timestamp, no commit
sha and no host is emitted. The acceptance check is reproducibility, not
provenance.

## Four classes, not three, and why

`COWORK_BRIEF_conformance_reader.md` names three -- declared-and-checked,
declared-and-unchecked, subject-not-enumerable. Building it found that **0060
clause 8 mandates a fourth**: existing rules "acquire declared subjects when
something next touches them, or when the clause-4 sweep reaches them", which
describes a rule that has **not yet declared** and is neither of the other
three.

Collapsing *undeclared* into *subject-not-enumerable* would be the exact
substitution 0060 clause 2 refuses. *Not declared* is a fact about a document;
*cannot be enumerated* is a claim about the rule, and only a person who has
tried can make it. Recording seventy-one rules as unenforceable because nobody
has written a `**Subject:**` line yet would inflate the count that 0060's
second falsifier reads as a health signal, and would make the estate look
principled where it is merely behind.

**So `undeclared` is reported as its own class and the brief's three-way split
is recorded as wrong rather than quietly satisfied.**

## What it reads, and what it cannot

A rule declares its subject with a `**Subject:**` field and its reader with a
`**Reader:**` field, in an entry's metadata block or a convention's header.
**Field presence is all this module reads.** It does not judge whether a
declared subject is a good one, and it does not verify that a declared reader
exists or actually reads that rule -- both need a person, and
`CONVENTION_conformance.md` §10 says so rather than implying coverage this does
not have.
"""
from __future__ import annotations

import re
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
DECISIONS_RELPATH = "docs/DECISIONS.md"
CONFORMANCE_MAP_RELPATH = "docs/_conformance_map.md"

#: An entry heading: `## 0060 — <title>`. Same shape decisions_map uses.
_ENTRY_RE = re.compile(r"^##[ \t]+(\d{4})[ \t]*[—–-][ \t]*(.+?)[ \t]*$", re.M)

#: A declaration runs to the end of its paragraph, not the end of its line.
#: Capturing one line cut wrapped declarations mid-sentence and produced map
#: entries that read as finished sentences and were not. It stops at a blank
#: line, at the ` · **Field:**` separator the log's metadata blocks use, or at
#: end of text -- so a field inside an entry's metadata paragraph does not
#: swallow the fields beside it.
_DECL_END = r"(?=\n[ \t]*\n|·[ \t]*\*\*[A-Z]|\Z)"
_SUBJECT_RE = re.compile(r"\*\*Subject:\*\*[ \t]*(.+?)" + _DECL_END, re.S)
_READER_RE = re.compile(r"\*\*Reader:\*\*[ \t]*(.+?)" + _DECL_END, re.S)

#: Values recording 0060 clause 2's outcome. Matched on the field's own line
#: only; the phrase in a later paragraph is prose, not a declaration.
_NOT_ENUMERABLE_RE = re.compile(
    r"\b(?:not[\s-]enumerable|subject-not-enumerable|unenforceable)\b",
    re.IGNORECASE,
)

#: How far into a convention the header is taken to run. A declaration below
#: this is not a header field; it is a mention.
CONVENTION_HEAD_LINES = 40

DECLARED_CHECKED = "declared-and-checked"
DECLARED_UNCHECKED = "declared-and-unchecked"
NOT_ENUMERABLE = "subject-not-enumerable"
UNDECLARED = "undeclared"

#: Report order: the two states that represent work done, then the two that
#: represent work outstanding. Ordering is fixed so the output is stable.
CLASSES = (DECLARED_CHECKED, DECLARED_UNCHECKED, NOT_ENUMERABLE, UNDECLARED)

CLASS_GLOSS = {
    DECLARED_CHECKED:
        "declares a subject and names a reader",
    DECLARED_UNCHECKED:
        "declares a subject; no reader named (0060 cl.4's second half, "
        "stated rather than silent)",
    NOT_ENUMERABLE:
        "declares that its subject cannot be enumerated (0060 cl.2) -- a "
        "permitted outcome, not a defect",
    UNDECLARED:
        "carries no subject declaration; predates 0060 and is inside cl.8's "
        "carve-out. NOT the same as not-enumerable: nobody has tried yet",
}


class Rule:
    __slots__ = ("kind", "ident", "title", "subject", "reader")

    def __init__(self, kind: str, ident: str, title: str,
                 subject: str | None, reader: str | None) -> None:
        self.kind = kind          # "ruling" | "convention"
        self.ident = ident
        self.title = title
        self.subject = subject
        self.reader = reader

    @property
    def classification(self) -> str:
        if self.subject is None:
            return UNDECLARED
        if _NOT_ENUMERABLE_RE.search(self.subject):
            return NOT_ENUMERABLE
        return DECLARED_CHECKED if self.reader else DECLARED_UNCHECKED


#: How much of a declared value is echoed in the map. The map is an index, not
#: a copy: a declaration longer than this is shown abbreviated so a reader can
#: see it was made, and goes to the document to read it.
VALUE_ECHO_CHARS = 90


def _field(text: str, pattern: re.Pattern[str]) -> str | None:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _echo(value: str) -> str:
    """One line of a declared value, abbreviated visibly rather than silently.

    A `**Subject:**` or `**Reader:**` field routinely runs past the line it
    starts on. Cutting at the newline produced entries that read as finished
    sentences and were not -- an abbreviation that does not look like one is
    worse than no echo at all.
    """
    flat = " ".join(value.split())
    if len(flat) <= VALUE_ECHO_CHARS:
        return flat
    return flat[:VALUE_ECHO_CHARS].rstrip() + " […]"


def _sentence_case(text: str) -> str:
    """Upper-case the first character and leave every other one alone.

    ``str.capitalize()`` lower-cases the remainder, which silently flattened
    the emphasised NOT in the `undeclared` gloss -- the word that stops that
    class being read as `subject-not-enumerable`.
    """
    return text[:1].upper() + text[1:] if text else text


def _entry_heads(text: str) -> list[tuple[str, str, str]]:
    """`(number, title, metadata block)` for each entry in the log.

    The metadata block runs from the heading to the entry's Context section,
    which is where every entry in this log carries its fields and the only
    place a declaration counts.
    """
    out: list[tuple[str, str, str]] = []
    marks = list(_ENTRY_RE.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        head, _, _ = body.partition("\n\n**Context")
        out.append((m.group(1), m.group(2).strip(), head))
    return out


def read_rules(root: Path | None = None) -> list[Rule]:
    """Every rule-bearing document, in report order: rulings then conventions."""
    root = root or TOOLKIT_ROOT
    rules: list[Rule] = []

    log = root / DECISIONS_RELPATH
    if log.is_file():
        text = log.read_text(encoding="utf-8")
        for num, title, head in _entry_heads(text):
            rules.append(Rule("ruling", num, title,
                              _field(head, _SUBJECT_RE),
                              _field(head, _READER_RE)))

    docs = root / "docs"
    if docs.is_dir():
        for path in sorted(docs.glob("CONVENTION_*.md")):
            head = "\n".join(
                path.read_text(encoding="utf-8").splitlines()[:CONVENTION_HEAD_LINES]
            )
            rules.append(Rule("convention", path.name, path.name,
                              _field(head, _SUBJECT_RE),
                              _field(head, _READER_RE)))
    return rules


def _slug(text: str) -> str:
    keep = [c.lower() if c.isalnum() else ("-" if c in " -—–" else "")
            for c in text]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def render(rules: list[Rule]) -> str:
    counts = {c: 0 for c in CLASSES}
    for r in rules:
        counts[r.classification] += 1
    total = len(rules)
    rulings = sum(1 for r in rules if r.kind == "ruling")
    conventions = total - rulings

    L: list[str] = []
    L.append("<!-- GENERATED by l5gntools/conformance_map.py -- DO NOT "
             "HAND-EDIT.")
    L.append("     Regenerate with `python run.py conformance-map` in the same "
             "commit as the change that moved it (DECISIONS 0030).")
    L.append("     Deterministic by contract: no timestamp, commit or host is "
             "stamped, so an unchanged tree renders byte-identically. -->")
    L.append("")
    L.append("# What the estate declares about its own rules")
    L.append("")
    L.append("Generated, never hand-edited (**0030**). The authorities are "
             "`docs/DECISIONS.md` and `docs/CONVENTION_*.md`; the convention is "
             "`docs/CONVENTION_conformance.md`.")
    L.append("")
    L.append("**This surface reports and never gates** (**0031**, 0060 cl.7). "
             "The only thing here that can go red is "
             "`auditors/auditor_rule_subjects.py`, and it guards the forward "
             "boundary only.")
    L.append("")
    L.append("**Nothing below is a judgement about whether a rule is obeyed.** "
             "This reads what each document *declares*. A rule with a declared "
             "subject and a named reader may still be broken, and this map "
             "would not know.")
    L.append("")

    # 0060 clause 3: the denominator, and how it was derived.
    L.append("## The denominator, and how it was derived")
    L.append("")
    L.append(f"**{total}** rule-bearing documents: **{rulings}** entries in "
             f"`docs/DECISIONS.md`, counted by their `## NNNN —` headings, and "
             f"**{conventions}** files matching `docs/CONVENTION_*.md`.")
    L.append("")
    L.append("Derived by reading those two sources at render time, never from "
             "a stored count. **A figure computed over a substituted subject "
             "is a defect rather than an approximation** (0060 cl.3), and the "
             "worked instance that rule came from is in this map: 0057 cl.7 "
             "binds only conventions *adopted from another estate*, which is "
             "not the same set as every convention.")
    L.append("")
    L.append("**A declaration is a field, and field presence is all that is "
             "read.** Whether a declared subject is a *good* subject, and "
             "whether a named reader really reads that rule, both need a "
             "person; `CONVENTION_conformance.md` §10 says so.")
    L.append("")

    L.append("## Counts")
    L.append("")
    L.append("| classification | count | what it means |")
    L.append("|---|---|---|")
    for c in CLASSES:
        L.append(f"| `{c}` | **{counts[c]}** | {CLASS_GLOSS[c]} |")
    L.append(f"| **total** | **{total}** | |")
    L.append("")
    L.append("**Four classes, where "
             "`COWORK_BRIEF_conformance_reader.md` named three.** 0060 clause 8 "
             "mandates the fourth: a rule that has not yet declared is neither "
             "declared nor shown to be unenumerable. **`undeclared` is a "
             "backlog; `subject-not-enumerable` is a finding.** Merging them "
             "would report the estate as principled where it is merely behind, "
             "and would corrupt the count 0060's second falsifier reads.")
    L.append("")

    for c in CLASSES:
        members = [r for r in rules if r.classification == c]
        L.append(f"## `{c}` — {len(members)} of {total}")
        L.append("")
        L.append(f"{_sentence_case(CLASS_GLOSS[c])}.")
        L.append("")
        if not members:
            L.append("*None.*")
            L.append("")
            continue
        for r in members:
            if r.kind == "ruling":
                anchor = _slug(f"{r.ident} — {r.title}")
                line = f"- [`{r.ident}`](DECISIONS.md#{anchor}) — {r.title}"
            else:
                line = f"- [`{r.ident}`]({r.ident}) — convention"
            if r.subject and c != NOT_ENUMERABLE:
                line += f" · **subject:** {_echo(r.subject)}"
            if r.reader:
                line += f" · **reader:** {_echo(r.reader)}"
            L.append(line)
        L.append("")

    L.append("## What this map cannot tell you")
    L.append("")
    L.append("- **Whether any rule is obeyed.** Out of scope by the brief that "
             "built this, and it is a different reader per rule.")
    L.append("- **Whether a declared subject is honest.** A plausible subject "
             "that is not the rule's real one passes mechanically. That is what "
             "0060's first falsifier is set to measure.")
    L.append("- **Whether a named reader exists.** The field is read, not "
             "resolved.")
    L.append("- **Anything about work-estate rulings.** They are behind the "
             "wall (**0051**) and are not in the denominator above. This map "
             "covers this repo, and says so rather than presenting a "
             "personal-estate view as the whole picture.")
    return "\n".join(L) + "\n"


def write_conformance_map(root: Path | None = None) -> Path:
    root = root or TOOLKIT_ROOT
    dest = root / CONFORMANCE_MAP_RELPATH
    dest.write_text(render(read_rules(root)), encoding="utf-8", newline="\n")
    return dest
