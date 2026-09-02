"""auditor_rule_subjects -- fail the gate when a rule that 0060 binds carries
neither a declared subject nor an explicit record that its subject cannot be
enumerated.

**One class of claim**, in `auditor_doc_claims`' pattern and to its standard:
*every rule bound by 0060 declares the subject it binds* (0060 clause 1), or is
recorded `not enumerable` (clause 2). Nothing else. It is **not** a checker of
whether any rule is *obeyed* -- that is a different reader per rule and is out
of scope for the round that built this (`COWORK_BRIEF_conformance_reader.md`).

The convention is `docs/CONVENTION_conformance.md` and it is the authority.
Where it and this docstring disagree, it wins and this file is amended
(**0052** clause 2).

## The declaration is mechanical, never prose

A rule declares its subject with a `**Subject:**` field -- in a DECISIONS
entry's metadata block, or in a convention's header. The auditor reads the
field's *presence*, not its wording. **It does not decide whether a subject is
a good one**, because deciding that requires reading prose, and 0060 clause 2
says a classification that needs prose read to it resolves to
`subject-not-enumerable` rather than to somebody's judgement in the moment.

A field whose value says the subject cannot be enumerated -- `not enumerable`,
`subject-not-enumerable`, `unenforceable` -- satisfies the rule as fully as a
declared subject does. **That is clause 2 working and not a loophole**: a rule
with no honest escape hatch gets given a plausible subject instead of an
accurate one, and 0060's second falsifier watches for exactly that.

## The clause 8 carve-out, stated rather than applied silently

0060 clause 8 binds rules made from its own drafting forward and **does not
retroactively invalidate anything**. Backdating a subject onto an accepted
entry would edit a frozen body, which `CONVENTION_decisions.md` §4 forbids.

So the carve-out is a **fixed set, named in code** -- 0060 clause 1's second
form, and 0033's precedent that a confinement lives in code where a reviewer
reads it rather than in config where it can be widened quietly. Everything in
that set classifies **undeclared without going red**; everything outside it
must declare.

`run()` prints the carve-out on every run rather than leaving it to be
discovered from this docstring, which is **0056** clause 1's second half: a
check that narrows its subject states in its own output that it has done so.

## What this auditor cannot see

Stated because **0048** clause 4 says a check that cannot fail trains the eye
past it, and this one can only fail in a narrow band:

  * It cannot tell a dishonest subject from an honest one. A plausible
    `**Subject:**` that is not the rule's real subject passes mechanically.
  * It does not check §2's reader declaration, §4's round trip, §5's
    denominators, §6's placement or §7's report-never-repair. Those are
    unchecked, and `docs/CONVENTION_conformance.md` §10 says so.
  * While the carve-out holds every rule in the tree, **this auditor's only
    live subject is rules written from now on.** That is a real and deliberate
    narrowness, and it is why the generated map (0060 clause 4) exists: the map
    reports the whole estate; this auditor guards only the forward boundary.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

#: `## 0060 — A rule declares the subject it binds, ...`
_ENTRY = re.compile(r"^## (\d{4}) — (.*?)$", re.MULTILINE)

#: `**Subject:** every rule-bearing document in this repo` -- the field, in an
#: entry's metadata block or a convention's header. Value captured so the
#: not-enumerable forms below can be recognised; never otherwise interpreted.
_SUBJECT = re.compile(r"\*\*Subject:\*\*\s*(?P<value>[^\n]*)", re.IGNORECASE)

#: Values that record clause 2's outcome. Matched on the field's first line
#: only -- a mention of the phrase in a later paragraph is prose, not a
#: declaration.
_NOT_ENUMERABLE = re.compile(
    r"\b(?:not[\s-]enumerable|subject-not-enumerable|unenforceable)\b",
    re.IGNORECASE,
)

#: 0060 clause 8's carve-out, half one: every entry in `docs/DECISIONS.md` at
#: the moment 0060 was ratified. 0060 is itself inside the set -- it was
#: drafted before the rule it makes existed, and its body froze at acceptance
#: on 2026-09-01, so no sanctioned writer can add a field to it. A checker
#: demanding what no writer can produce is the mode-5 defect 0060 clause 5
#: forbids, and it would be built into the auditor that clause names.
LAST_PREDATING_ENTRY = 60

#: 0060 clause 8's carve-out, half two: every convention in `docs/` at that
#: same moment. Named rather than globbed, because a glob would silently
#: absorb each new convention into the exemption and the auditor would never
#: fire again.
PREDATING_CONVENTIONS = frozenset({
    "CONVENTION_briefs.md",
    "CONVENTION_commits.md",
    "CONVENTION_config.md",
    "CONVENTION_conversation_map.md",
    "CONVENTION_decisions.md",
    "CONVENTION_design_thread_restart.md",
    "CONVENTION_docs.md",
    "CONVENTION_gitignore.md",
    "CONVENTION_project_process.md",
    "CONVENTION_project_registry.md",
    "CONVENTION_skills.md",
})

CARVE_OUT_NOTE = (
    f"auditor_rule_subjects: 0060 cl.8 carve-out in force -- "
    f"DECISIONS 0001-{LAST_PREDATING_ENTRY:04d} and "
    f"{len(PREDATING_CONVENTIONS)} conventions predating 0060 classify as "
    f"undeclared WITHOUT going red. Live subject: entries "
    f"{LAST_PREDATING_ENTRY + 1:04d}+ and conventions added since. "
    f"The whole-estate picture is docs/_conformance_map.md, not this check."
)


def declaration_in(block: str) -> tuple[bool, bool]:
    """Return ``(declared, not_enumerable)`` for one rule's header text.

    ``declared`` is the field's presence -- the only thing this auditor reads.
    ``not_enumerable`` says the declared value records clause 2's outcome, and
    is reported rather than acted on: both states satisfy the rule.
    """
    m = _SUBJECT.search(block)
    if not m:
        return False, False
    return True, bool(_NOT_ENUMERABLE.search(m.group("value")))


def _entry_blocks(text: str) -> list[tuple[int, str, str]]:
    """Split `docs/DECISIONS.md` into ``(number, title, metadata block)``.

    The metadata block is everything from the heading to the first blank line
    after the `**Date:**` paragraph -- where every entry in the log carries its
    fields, and the only place a `**Subject:**` field counts.
    """
    out: list[tuple[int, str, str]] = []
    marks = list(_ENTRY.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        head, _, _ = body.partition("\n\n**Context")
        out.append((int(m.group(1)), m.group(2).strip(), head))
    return out


def violations_in_log(text: str, last_predating: int = LAST_PREDATING_ENTRY
                      ) -> list[str]:
    """Pure, file-independent check over the decisions log."""
    out: list[str] = []
    for number, title, head in _entry_blocks(text):
        if number <= last_predating:
            continue
        declared, _ = declaration_in(head)
        if not declared:
            out.append(
                f"docs/DECISIONS.md: {number:04d} carries no '**Subject:**' "
                f"field -- 0060 cl.1 requires a declared subject, cl.2 permits "
                f"'not enumerable', and cl.8 exempts only "
                f"0001-{last_predating:04d} ({title[:48]})"
            )
    return out


def violations_in_convention(text: str, label: str, head_lines: int = 40
                             ) -> list[str]:
    """Pure, file-independent check over one convention's header."""
    head = "\n".join(text.splitlines()[:head_lines])
    declared, _ = declaration_in(head)
    if declared:
        return []
    return [
        f"{label}: carries no '**Subject:**' field in its first {head_lines} "
        f"lines -- 0060 cl.1 requires a declared subject and cl.2 permits "
        f"'not enumerable'; this convention is not in the cl.8 carve-out"
    ]


def run() -> list[str]:
    print(CARVE_OUT_NOTE)
    v: list[str] = []

    log = _ROOT / "docs" / "DECISIONS.md"
    if not log.is_file():
        # 0050: a source that cannot be reached reads as unknown, never as
        # clear. An absent log is reported, not passed over.
        v.append("docs/DECISIONS.md: not found -- cannot classify any ruling")
    else:
        try:
            v.extend(violations_in_log(log.read_text(encoding="utf-8")))
        except OSError as exc:
            v.append(f"docs/DECISIONS.md: unreadable ({exc})")

    docs = _ROOT / "docs"
    if docs.is_dir():
        for path in sorted(docs.glob("CONVENTION_*.md")):
            if path.name in PREDATING_CONVENTIONS:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                v.append(f"docs/{path.name}: unreadable ({exc})")
                continue
            v.extend(violations_in_convention(text, f"docs/{path.name}"))

    return v
