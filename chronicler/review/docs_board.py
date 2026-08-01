"""The docs board: ``docs/``'s lifecycle, derived and rendered (COWORK brief:
the docs board, slice 1 of two).

``docs/README.md`` §2/§3 already defines a lifecycle -- brief → report →
walk-sheet → results log → archived -- and every transition in it is derivable
**mechanically**, from filenames and existence. Nothing new needs to be
recorded here; it needs to be *rendered*. So this module records nothing.

Four rules govern the module, and each is load-bearing:

  * **Derived, never stored.** There is no board state file, no column
    assignment on disk, no cache. :func:`board` walks ``docs/`` on every call
    and returns a fresh answer. A stored board is a status board, and
    ``docs/README.md`` §5 retires those *by class* because they demonstrably
    rot -- shipping one inside the tool that renders the convention would be a
    fine joke and a bad idea.

  * **Read-only.** This module opens files for reading and nothing else. Task 4
    (staging a ``git mv``, per DECISIONS 0028) is deliberately **not** in this
    slice: the board ships read-only. There is no writer here to disable.

  * **No second path resolver.** Every read goes through
    :func:`estate_data.resolve_contained`, the same gate the estate documents
    use, differing only in its anchor -- see :data:`_ANCHORS`.

  * **Report the convention; never enforce it.** Where the filesystem is
    inconsistent, the board's job is to *show* the inconsistency, not to
    normalise it away. The two known cases are named in ``FINDING_*`` below.

## What the board can and cannot know

The columns are a function of which files exist:

===================  ==========================================================
in flight            a brief, no report
built, not walked    a brief and a report, no results log
walked               a results log exists
archived             the files live in ``docs/archive/``
===================  ==========================================================

**Archivable is deliberately not a column.** It is not derivable: it requires a
human saying the UAT was actually walked (``docs/README.md`` §3 route 1, and
§6, which is honest that this is a convention no gate will ever enforce). A
results log proves a walk was *recorded*, never that it *passed*. Inventing an
``archivable`` status from file existence would be the board asserting the one
thing the filesystem cannot support.

## Card kinds -- because not everything is a pair

A brief and its report form a pair, and pairs are the unit of archiving. Three
shapes on disk are not pairs, and each gets a kind of its own rather than being
forced into one and rendered broken:

``pair``
    A brief, anchored. Its report may not exist yet -- that is the *in flight*
    column, not a defect.

``walk_only``
    A walk-sheet (and usually a results log) with **no brief**. A legitimate
    shape: ``UAT_work_rig_solo`` is a walk of an existing build on a second
    machine, not a build round, so there was never a brief to write. It is on
    the board, as itself.

``unmatched``
    An **archived** file that anchors no brief-plus-report pair by filename.
    ``docs/archive/`` predates the current naming convention in places:
    ``COWORK_ROUND_1/2/3_REPORT.md`` will not pair with
    ``COWORK_BRIEF_build_round_1/2/3.md`` however hard you squint at the stems,
    and ``chronicler_system_design.md``,
    ``WORKSHEET_registry_ratification_2026-07-25.md``,
    ``HANDOFF_final_2026-07-18.md`` and ``NEXT_SESSION_PLAN_final.md`` pair with
    nothing at all -- the last two by design, being retired *by class* (§5).

    These are **cards, not drops.** An archived file that fell out of the
    pairing logic silently would be indistinguishable from one the pairing
    logic never saw, which is how a bug hides. The unmatched count is published
    on the column for exactly that reason: it is a number that should change
    only when ``archive/`` changes, so a pairing regression shows up as a count
    moving on its own.

## Disposition comes from the stamp, not the filename

Every archived file carries an ``ARCHIVED`` stamp declaring its disposition --
``completed pair``, ``superseded``, ``retired``, ``recovered historical
brief``. That declaration is the archivist's judgement, made with the body
read, and it is authoritative. The board parses it and does not second-guess
it: ``COWORK_BRIEF_chronicler_alignment.md`` is stamped *completed pair* while
pairing mechanically as ``unmatched``, and both facts are true -- its partner
is an investigation doc whose filename simply does not carry the stem. The card
shows the stamp's word and the mechanical result side by side rather than
picking a winner.

**Unstamped is a different thing from unmatched**, and conflating them would
lose the more interesting one. Unmatched is a statement about naming.
*Unstamped* -- a file in ``archive/`` with no stamp at all -- is a breach of the
convention in §3, i.e. a finding: something was moved without being stamped,
and a cold reader has no way to know what in the body to stop trusting. It is
reported in ``findings``, never as a card kind.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .estate_data import (REPO_ROOT, DocumentRefused, document_id,
                          resolve_contained)

#: The board's containment anchor: this repository, and nothing else.
#:
#: Slice 1's resolver is anchored to ``config.estate_roots()``, which is the
#: right boundary for estate documents and the wrong one here. The toolkit sits
#: inside a configured root on the gaming rig (and has since ``6dd70f1``) and
#: sits outside one on the work rig; a board anchored to the estate roots would
#: therefore render card bodies on one machine and refuse them on the other,
#: for a directory it reaches by construction. ``REPO_ROOT`` is derived from
#: ``__file__``, so this is structural: not a config knob, not widenable, and
#: not something a machine can be misconfigured out of.
_ANCHORS: tuple[Path, ...] = (REPO_ROOT,)

DOCS_DIRNAME = "docs"
ARCHIVE_DIRNAME = "archive"

#: The board's synthetic "project" for :func:`estate_data.document_id`. The
#: board never accepts a filesystem path from a caller, for the same reason the
#: estate routes do not (0027 condition 3): a render-time reader with a path
#: parameter is a file-disclosure bug waiting for a bad bind. A card body is
#: addressed by a digest that resolves only against the catalogue the board
#: just built, so an unlisted file has no identifier to ask for.
_BOARD_NS = "__docs_board__"

#: Read cap for a card body, matching the estate reader's cap. A markdown file
#: in ``docs/`` at this size is pathological; say so rather than hang the tab.
MAX_DOC_BYTES: int = 2 * 1024 * 1024

#: How far into a file the stamp parsers look. Generous: two archived results
#: logs carry a multi-line ``uat`` comment *above* the ARCHIVED stamp, so a
#: tight window would read them as unstamped and manufacture a finding.
_HEAD_LINES = 60

# --- filename → (role, stem) --------------------------------------------------

_BRIEF = re.compile(r"^COWORK_BRIEF_(?P<stem>.+)\.md$")
_REPORT = re.compile(r"^COWORK_REPORT_(?P<stem>.+)\.md$")
#: The pre-convention report shape, e.g. ``COWORK_ROUND_1_REPORT.md``. Matched
#: so the file is *classified* rather than dumped in the unclassified bucket --
#: it still will not pair, because its stem (``round_1``) is genuinely not the
#: brief's stem (``build_round_1``). Recognising the shape and still failing to
#: pair is the honest outcome; rewriting one stem into the other to force a
#: match would be the board inventing history.
_REPORT_LEGACY = re.compile(r"^COWORK_(?P<stem>.+)_REPORT\.md$")
_RESULTS = re.compile(r"^UAT_(?P<stem>.+)_results\.md$")
_WALK = re.compile(r"^UAT_(?P<stem>.+)\.md$")

#: Core ``docs/*.md`` that are not lifecycle documents and are **deliberately
#: not on the board**, each with the reason it is off. They are maintained or
#: never-maintained, not *finished*, so they have no column to be in: the
#: trinity and the playbooks are edited in place forever (§1), runbooks and the
#: spec are reference, and ``investigation/`` is a separate lifecycle entirely
#: (§4) that never graduates. Listed rather than silently skipped -- "the board
#: does not show ARCHITECTURE.md" should be a visible decision, not an
#: absence a reader has to notice.
_OFF_BOARD_REASONS = {
    "README.md": "maintained — the convention itself (§1)",
    "INTENT.md": "trinity, maintained indefinitely (§1)",
    "ARCHITECTURE.md": "trinity, maintained indefinitely (§1)",
    "DECISIONS.md": "trinity, append-only, never archivable (§1)",
    "KNIGHT_PLAYBOOK.md": "maintained operator runbook (§1)",
    "PRODUCER_PLAYBOOK.md": "maintained operator runbook (§1)",
    "SOLO_PLAYBOOK.md": "maintained operator runbook (§1)",
    "SPEC_Chronicler.md": "reference spec, maintained until executed (§1)",
}
_OFF_BOARD_PREFIX = {
    "RUNBOOK_": "reference runbook — not a lifecycle document",
}

#: Dispositions ``docs/README.md`` §3 defines. Matched as a *prefix* of the
#: stamp's disposition field so a stamp that elaborates
#: (``SUPERSEDED — do NOT run as a task list``) is still classified, with its
#: full text preserved beside the classification. Longest first, so
#: ``recovered historical brief`` is not swallowed by a shorter sibling.
_DISPOSITIONS = (
    "recovered historical design",
    "recovered historical brief",
    "completed round record",
    "completed pair",
    "superseded",
    "retired",
)

_ARCHIVED_STAMP = re.compile(r"\*\*ARCHIVED\*\*\s*(?P<body>.*)")
_GATE_FROZEN = re.compile(r"<!--\s*gate-frozen:\s*(?P<body>[^>]*?)\s*-->", re.I)
_UAT_STAMP = re.compile(r"<!--\s*uat:\s*(?P<body>[^>]*?)\s*-->", re.I)
_FIELD = re.compile(r"(\w+)\s*=\s*(\S+)")

#: A checkbox line. ``[x]`` and ``[~]`` both count as done -- ``~`` is the
#: house spelling for "walked, with a caveat recorded", which is a walked item.
_CHECK = re.compile(r"^\s*[-*]\s*\[(?P<mark>[ xX~])\]")

FINDING_UNSTAMPED = "unstamped_archive_file"
FINDING_EVIDENCE_IN_RESULTS = "checkbox_evidence_in_results_log"
FINDING_STRADDLE = "stem_split_across_core_and_archive"
FINDING_MIXED_DISPOSITION = "members_stamped_with_different_dispositions"


def _classify(name: str) -> tuple[str | None, str]:
    """``filename`` → ``(role, stem)``. ``role`` is ``None`` for a file that is
    not a lifecycle document, in which case the stem is the filename itself so
    it can still stand as a card of one in ``archive/``.

    Order matters: ``_RESULTS`` is tried before ``_WALK`` because
    ``UAT_x_results.md`` also matches ``UAT_<stem>.md`` with stem
    ``x_results``, and ``_REPORT`` before ``_REPORT_LEGACY`` for the same
    reason in the other direction.
    """
    for role, pattern in (("brief", _BRIEF), ("report", _REPORT),
                          ("results", _RESULTS), ("walk", _WALK),
                          ("report_legacy", _REPORT_LEGACY)):
        m = pattern.match(name)
        if m:
            return role, m.group("stem")
    return None, name


def _read_head(path: Path, lines: int = _HEAD_LINES) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return [next(handle, "") for _ in range(lines)]
    except OSError:
        return []


def _parse_archived_stamp(head: list[str]) -> dict | None:
    """The ``> **ARCHIVED** YYYY-MM-DD · <disposition> · <pair status>`` stamp.

    Returns ``None`` when there is no stamp at all -- which is a finding, not a
    card kind. The disposition is reported *both* classified (matched against
    ``docs/README.md`` §3's list) and raw, because a stamp that says more than
    the vocabulary allows is saying something the archivist meant.
    """
    for line in head:
        m = _ARCHIVED_STAMP.search(line)
        if not m:
            continue
        parts = [p.strip() for p in m.group("body").split("·")]
        date = parts[0] if parts else ""
        raw = parts[1] if len(parts) > 1 else ""
        pair_status = parts[2] if len(parts) > 2 else ""
        low = raw.lower()
        classified = next((d for d in _DISPOSITIONS if low.startswith(d)), None)
        return {"date": date, "disposition": classified,
                "disposition_raw": raw, "pair_status": pair_status}
    return None


def _parse_markers(head: list[str]) -> dict:
    """``gate-frozen`` and ``uat`` markers. Presence and fields only -- whether
    a ``commit=`` resolves is ``auditor_doc_claims``' and
    ``auditor_uat_stamp``' job, and the board does not re-litigate the gate."""
    text = "".join(head)
    out: dict = {"gate_frozen": None, "uat": None}
    m = _GATE_FROZEN.search(text)
    if m:
        out["gate_frozen"] = dict(_FIELD.findall(m.group("body")))
    m = _UAT_STAMP.search(text)
    if m:
        out["uat"] = dict(_FIELD.findall(m.group("body")))
    return out


def _count_checkboxes(path: Path) -> dict:
    """``- [ ]`` against ``- [x]`` / ``- [~]``, counted and not interpreted."""
    done = open_ = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                m = _CHECK.match(line)
                if not m:
                    continue
                if m.group("mark") == " ":
                    open_ += 1
                else:
                    done += 1
    except OSError:
        return {"done": 0, "open": 0, "readable": False}
    return {"done": done, "open": open_, "readable": True}


def _member(path: Path, role: str, archived: bool, rel: str) -> dict:
    head = _read_head(path)
    entry = {
        "id": document_id(_BOARD_NS, rel),
        "role": role,
        "name": path.name,
        "rel": rel,
        "archived": archived,
        "bytes": path.stat().st_size if path.is_file() else None,
        **_parse_markers(head),
    }
    if archived:
        entry["stamp"] = _parse_archived_stamp(head)
    if role in ("walk", "results"):
        entry["checkboxes"] = _count_checkboxes(path)
    return entry


def _collect(directory: Path, archived: bool, relroot: Path) -> dict[str, list[dict]]:
    """Every ``*.md`` in one directory, grouped by stem."""
    groups: dict[str, list[dict]] = {}
    if not directory.is_dir():
        return groups
    for path in sorted(directory.glob("*.md")):
        role, stem = _classify(path.name)
        if not archived and role is None:
            continue  # off-board; enumerated separately with its reason
        rel = path.relative_to(relroot).as_posix()
        groups.setdefault(stem, []).append(
            _member(path, role or "other", archived, rel))
    return groups


def _card(stem: str, members: list[dict], archived: bool) -> dict:
    roles = {m["role"] for m in members}
    has_brief = "brief" in roles
    has_report = bool(roles & {"report", "report_legacy"})
    has_results = "results" in roles
    has_walk = "walk" in roles
    flags: list[str] = []

    # --- kind ---------------------------------------------------------------
    if archived:
        # In archive/, a pair is a pair only if both halves are present *by
        # filename*. Everything else is unmatched -- including an archived
        # brief whose report exists under a pre-convention name. That is the
        # point of the kind: it records that the naming did not carry, not
        # that the work was never done.
        kind = "pair" if (has_brief and has_report) else (
            "walk_only" if (has_walk and not has_brief and not has_report)
            else "unmatched")
    elif has_brief:
        kind = "pair"
    elif has_walk:
        kind = "walk_only"
    else:
        kind = "unmatched"

    # --- column -------------------------------------------------------------
    if archived:
        column = "archived"
    elif has_results:
        column = "walked"
    elif has_report:
        column = "built_not_walked"
    else:
        column = "in_flight"

    walk = next((m for m in members if m["role"] == "walk"), None)
    results = next((m for m in members if m["role"] == "results"), None)
    walk_boxes = (walk or {}).get("checkboxes") or {"done": 0, "open": 0}
    res_boxes = (results or {}).get("checkboxes") or {"done": 0, "open": 0}

    # The checkbox-convention finding, surfaced and NOT normalised. A card
    # that is walked, whose walk-sheet has zero ticks and whose results log
    # has some, was walked with the evidence recorded in the results log
    # instead of against the sheet. `doc_provenance_coverage` and
    # `repo_tier_producers` both read 0-done for this reason. The board says
    # so on the card; it does not add the ticks, and nobody should. The
    # convention being applied two ways is the finding -- a board that
    # papered over it would destroy the only signal that it is.
    if (has_results and walk_boxes["done"] == 0 and walk_boxes["open"] > 0
            and res_boxes["done"] > 0):
        flags.append(FINDING_EVIDENCE_IN_RESULTS)

    # --- disposition, from the stamp ----------------------------------------
    disposition = None
    unstamped: list[str] = []
    if archived:
        seen: list[str] = []
        for m in members:
            stamp = m.get("stamp")
            if stamp is None:
                unstamped.append(m["name"])
                continue
            label = stamp.get("disposition") or stamp.get("disposition_raw") or ""
            if label and label not in seen:
                seen.append(label)
        if len(seen) == 1:
            disposition = seen[0]
        elif len(seen) > 1:
            # Not an error: a pair's walk-sheet and results log are stamped
            # `completed pair (walk-sheet)` / `(results)`, which classify the
            # same. Genuinely different words are worth showing.
            disposition = "mixed"
            flags.append(FINDING_MIXED_DISPOSITION)
        if unstamped:
            flags.append(FINDING_UNSTAMPED)

    return {
        "key": stem,
        "kind": kind,
        "column": column,
        # A stem that is a whole filename (a pre-convention single in archive/)
        # keeps its extension in `key` -- the key must stay stable and unique --
        # but sheds it for display.
        "title": (stem[:-3] if stem.endswith(".md") else stem).replace("_", " "),
        "members": sorted(members, key=lambda m: (
            {"brief": 0, "report": 1, "report_legacy": 1,
             "walk": 2, "results": 3}.get(m["role"], 4), m["name"])),
        "has": {"brief": has_brief, "report": has_report,
                "walk": has_walk, "results": has_results},
        "open_items": walk_boxes["open"],
        "done_items": walk_boxes["done"],
        "results_items": {"done": res_boxes["done"], "open": res_boxes["open"]},
        "disposition": disposition,
        "unstamped": unstamped,
        "flags": flags,
    }


def _off_board(docs_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not docs_dir.is_dir():
        return out
    for path in sorted(docs_dir.glob("*.md")):
        role, _ = _classify(path.name)
        if role is not None:
            continue
        reason = _OFF_BOARD_REASONS.get(path.name)
        if reason is None:
            reason = next((r for p, r in _OFF_BOARD_PREFIX.items()
                           if path.name.startswith(p)),
                          "not a lifecycle document — no column applies")
        out.append({"name": path.name, "reason": reason})
    return out


#: Column order and the action each card offers. Actions are a function of the
#: column and nothing else. **Read-only in this slice**: the walked column's
#: "UAT ratified?" control (Task 3) and the archivable column's "Prepare
#: archive" (Task 4) are deliberately absent rather than present-and-disabled.
#: A greyed-out button is a promise; an absent one is an honest surface.
COLUMNS: tuple[dict, ...] = (
    {"key": "in_flight", "label": "In flight",
     "hint": "A brief with no report. Open the brief; the work is elsewhere.",
     "action": "open_brief"},
    {"key": "built_not_walked", "label": "Built, not walked",
     "hint": "Built and gate-green. Only a human walking the sheet closes the "
             "pair (docs/README.md §3).",
     "action": "open_walk_sheet"},
    {"key": "walked", "label": "Walked",
     "hint": "A results log exists. Walked is not archivable — that needs a "
             "human ruling, which this slice does not collect.",
     "action": "open_results"},
    {"key": "archived", "label": "Archived",
     "hint": "Retired and stamped. Read-only history.",
     "action": "show_stamp"},
)


def board(repo_root: Path | None = None) -> dict:
    """Derive the whole board. Walks the filesystem; stores nothing.

    ``repo_root`` exists so a tester can drive this against a fixture tree. It
    is **not** a request parameter and no route passes one through -- the
    containment anchor stays :data:`_ANCHORS`, derived from ``__file__``, so a
    caller cannot point the board at another tree.
    """
    root = Path(repo_root) if repo_root else REPO_ROOT
    docs_dir = root / DOCS_DIRNAME
    archive_dir = docs_dir / ARCHIVE_DIRNAME

    core_groups = _collect(docs_dir, archived=False, relroot=root)
    arch_groups = _collect(archive_dir, archived=True, relroot=root)

    findings: list[dict] = []
    cards: list[dict] = []
    for stem, members in core_groups.items():
        cards.append(_card(stem, members, archived=False))
    for stem, members in arch_groups.items():
        card = _card(stem, members, archived=True)
        cards.append(card)
        for name in card["unstamped"]:
            # Distinct from `unmatched`, and the more serious of the two: a
            # file was moved into archive/ without a stamp, so a cold reader
            # has nothing telling them what in the body to stop trusting.
            findings.append({
                "kind": FINDING_UNSTAMPED, "file": f"docs/archive/{name}",
                "detail": "In docs/archive/ with no ARCHIVED stamp. "
                          "docs/README.md §3 requires one on every archived "
                          "file; a cold read has no way to know what in this "
                          "body is still true."})

    straddling = sorted(set(core_groups) & set(arch_groups))
    for stem in straddling:
        findings.append({
            "kind": FINDING_STRADDLE, "file": stem,
            "detail": "Files with this stem exist in both docs/ and "
                      "docs/archive/. A pair archives together (§2); half a "
                      "pair in each place is a partial move to finish or undo."})

    for card in cards:
        if FINDING_EVIDENCE_IN_RESULTS in card["flags"]:
            findings.append({
                "kind": FINDING_EVIDENCE_IN_RESULTS, "file": card["key"],
                "detail": "Walked, but the walk-sheet reads 0 done and the "
                          "results log carries the ticks. The convention is "
                          "being applied two ways. Reported, not normalised — "
                          "do not tick the sheet to make this go away."})

    cards.sort(key=lambda c: (c["column"], c["key"]))
    columns = []
    for spec in COLUMNS:
        in_col = [c for c in cards if c["column"] == spec["key"]]
        entry = {**spec, "count": len(in_col), "cards": in_col}
        if spec["key"] == "archived":
            # Published on the column, not buried on the cards: this number
            # moves only when archive/ moves, so a pairing regression shows up
            # here as a count changing on its own. A pot of dropped files
            # could hide a bug; a counted pot cannot.
            entry["unmatched_count"] = sum(1 for c in in_col
                                           if c["kind"] == "unmatched")
            entry["walk_only_count"] = sum(1 for c in in_col
                                           if c["kind"] == "walk_only")
            entry["file_count"] = sum(len(c["members"]) for c in in_col)
        columns.append(entry)

    return {
        "root": str(root),
        "columns": columns,
        "off_board": _off_board(docs_dir),
        "findings": findings,
        "persisted": False,
        "actions_enabled": False,
        "note": "Read-only. Ratification (Task 3) and staging (Task 4) are not "
                "in this slice, so no card offers an archive action.",
    }


def read_card_document(doc_id: str, repo_root: Path | None = None) -> dict:
    """Read one card's document from disk **at render time** (0027), by opaque
    identifier -- never by a path from the caller.

    Two independent checks, both enforced, exactly as the estate reader does
    them and for the same reasons:

      1. the identifier must resolve against the catalogue this call rebuilds,
         so a traversal attempt arrives as an id that is a digest of nothing;
      2. the resolved path is re-verified inside :data:`_ANCHORS` immediately
         before the file is opened, via the shared
         :func:`estate_data.resolve_contained` gate.

    Check 2 is not redundant. A file could be listed and still resolve outside
    the repo -- a symlink in ``docs/`` pointing at ``~/.ssh``, say. Check 1
    passes for it; check 2 is what refuses it, after ``realpath``.
    """
    root = Path(repo_root) if repo_root else REPO_ROOT
    anchors = (root,) if repo_root else _ANCHORS
    catalogue: dict[str, str] = {}
    docs_dir = root / DOCS_DIRNAME
    for directory in (docs_dir, docs_dir / ARCHIVE_DIRNAME):
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            rel = path.relative_to(root).as_posix()
            catalogue[document_id(_BOARD_NS, rel)] = rel

    rel = catalogue.get(str(doc_id))
    if rel is None:
        raise DocumentRefused(
            "unknown_document",
            "No board document with that identifier. The board addresses "
            "documents by digest, never by path.")

    path = resolve_contained(
        root.joinpath(*rel.split("/")), anchors,
        outside_reason="outside_repo_root",
        no_anchor_reason="no_repo_anchor",
        boundary="this repository",
        no_anchor_detail="The board has no containment anchor, which cannot "
                         "happen for a real run — REPO_ROOT is derived from "
                         "__file__, not configured.")
    if not path.is_file():
        raise DocumentRefused(
            "not_a_file", f"{rel} was listed but is not a readable file now.")
    try:
        size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(MAX_DOC_BYTES)
    except OSError as exc:
        raise DocumentRefused("unreadable", f"Could not read {rel}: {exc}")
    truncated = size > MAX_DOC_BYTES
    return {
        "id": str(doc_id), "rel": rel, "name": rel.rsplit("/", 1)[-1],
        "text": text, "bytes_on_disk": size, "truncated": truncated,
        "note": (f"Truncated at {MAX_DOC_BYTES} bytes of {size}."
                 if truncated else None),
    }
