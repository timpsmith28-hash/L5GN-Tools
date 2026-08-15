"""The UAT sidebar (COWORK brief: uat_sidebar, slice 2 of two).

The board (slice 1) renders the lifecycle; it is read-only. This module is the
one action the *built, not walked* column gains: walk a sheet's items, record a
verdict and its evidence per item, and emit a stamped results log that moves
the card to *walked* on the next board load -- because that column is derived
from file existence (`docs_board.py`), never from a flag this module sets.

Four rules carried over from the brief, and load-bearing:

  * **Never computes a pass.** A verdict is chosen by a human (walked /
    deferred / blocked / not applicable); nothing here inspects evidence text
    and grades it.
  * **In-progress state is session-scoped.** This module holds nothing between
    requests -- the UI keeps the working notes in memory and says so. Only
    Task 3's emit call writes to disk.
  * **Staged, never committed** (DECISIONS 0028). Emitting a results log
    stages it with `git add`; nothing here runs `git commit`.
  * **An existing results log is never silently overwritten.** Emitting again
    either appends a new walk section or refuses, per the caller's choice --
    the first call always tells the caller which results log already exists.

Vocabulary mirrors `archive/UAT_cowork_run_2026-07-24_results.md`: a verdict
maps to one evidence tag, `[EVIDENCE]` / `[DEFERRED]` / `[BLOCKED]` / `[N/A]`,
carried onto the emitted line so a cold read of the results log needs no
legend lookup back to this module.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from l5gntools.common import run_git, toolkit_git_info
from l5gntools.config import hostname

from .docs_board import _count_checkboxes  # same package; avoids a second
                                            # implementation of the checkbox
                                            # count the board already owns.
from .estate_data import REPO_ROOT, DocumentRefused, resolve_contained

DOCS_DIRNAME = "docs"

#: A walk-sheet stem is a bare identifier -- never a path. This is the only
#: input this module accepts from a caller for *which* sheet to open, so it is
#: validated before it ever touches a filesystem call (same shape as the
#: board's opaque document ids, for the same reason: no route here accepts a
#: path).
_STEM = re.compile(r"^[A-Za-z0-9_\-]+$")

VERDICTS: tuple[str, ...] = ("walked", "deferred", "blocked", "not_applicable")
_REASON_REQUIRED = {"deferred", "blocked"}
_TAG = {"walked": "EVIDENCE", "deferred": "DEFERRED",
        "blocked": "BLOCKED", "not_applicable": "N/A"}

#: A section header: `#`, `##`, `###` all count. Sections nest one level in
#: practice (`## A · label`, `## Part 0 ▸ label`) -- the sidebar does not need
#: to distinguish heading depth, only to group items under the nearest one.
_SECTION = re.compile(r"^#{1,3}\s+(?P<label>.+?)\s*$")
#: An item line: `- [ ] **<id>** text`, with an optional layer marker between
#: the checkbox and the id -- `- [ ] [W] **B7.** ...` (DECISIONS 0031, the
#: gate/witness/walk-sheet assignment rule). The id is whatever sits between
#: the bold markers -- `A1`, `2.1`, `0.4`, `E7` all match, because the sheets
#: we have actually use all three shapes (see UAT_docs_board.md,
#: UAT_work_rig_solo.md).
_ITEM = re.compile(
    r"^\s*[-*]\s*\[(?P<mark>[ xX~])\]\s*(?:\[(?P<layer>[GWH])\]\s*)?"
    r"\*\*(?P<id>[^*]+)\*\*\s*(?P<text>.*)$")

#: The inverse of `build_results_body`'s per-item shape, for resuming a walk
#: already partly recorded in an emitted results log:
#:   - **<id>** <text>
#:     [TAG] <inline evidence>
#: or, for pasted multi-line output:
#:   - **<id>** <text>
#:     [TAG]
#:     ```
#:     <evidence, one line per source line>
#:     ```
_RESULT_ITEM = re.compile(r"^- \*\*(?P<id>[^*]+)\*\*\s")
_RESULT_TAG = re.compile(
    r"^\s*\[(?P<tag>EVIDENCE|DEFERRED|BLOCKED|N/A)\](?:\s(?P<inline>.*))?$")
_TAG_TO_VERDICT = {v: k for k, v in _TAG.items()}


def _safe_stem(stem: str) -> str:
    if not stem or not _STEM.match(stem):
        raise DocumentRefused(
            "bad_stem",
            "Not a valid walk-sheet stem. The sidebar addresses a sheet by "
            "its UAT_<stem>.md name component, never by a path.")
    return stem


def sheet_path(root: Path, stem: str) -> Path:
    return root / DOCS_DIRNAME / f"UAT_{stem}.md"


def results_path(root: Path, stem: str) -> Path:
    return root / DOCS_DIRNAME / f"UAT_{stem}_results.md"


def _resolve(path: Path, root: Path) -> Path:
    """Re-verify containment immediately before a read/write, exactly as the
    board's `read_card_document` does -- a listed name is not yet a checked
    path (0027 condition 3)."""
    return resolve_contained(
        path, (root,), outside_reason="outside_repo_root",
        no_anchor_reason="no_repo_anchor", boundary="this repository")


# --- Task 1: read a walk-sheet as items --------------------------------------

def parse_sheet(path: Path) -> dict:
    """A ``UAT_<x>.md`` as ``{"sections": [...], "readable": bool}``.

    Each section is ``{"label": str, "items": [...]}``; each item is
    ``{"id", "state" ("open"/"caveat"/"done"), "text", "sheet_note"}``. A
    continuation line under an item (the "-- *evidence...*" convention several
    sheets use) is folded into ``sheet_note`` rather than dropped -- that prose
    is often the most useful line on the sheet, and the sidebar is not the
    place to discard it.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"sections": [], "readable": False}

    sections: list[dict] = []
    cur: dict | None = None
    cur_item: dict | None = None
    for line in text.splitlines():
        sm = _SECTION.match(line)
        if sm:
            cur = {"label": sm.group("label"), "items": []}
            sections.append(cur)
            cur_item = None
            continue
        im = _ITEM.match(line)
        if im:
            if cur is None:
                cur = {"label": "(preamble)", "items": []}
                sections.append(cur)
            mark = im.group("mark")
            state = "open" if mark == " " else ("caveat" if mark in "~" else "done")
            cur_item = {"id": im.group("id").strip(), "state": state,
                        "text": im.group("text").strip(),
                        "layer": im.group("layer"), "_note": []}
            cur["items"].append(cur_item)
            continue
        if not line.strip():
            cur_item = None
            continue
        if cur_item is not None and line[:1].isspace():
            cur_item["_note"].append(line.strip(" \t*—-"))

    for sec in sections:
        for it in sec["items"]:
            it["sheet_note"] = " ".join(n for n in it.pop("_note") if n)
    return {"sections": sections, "readable": True}


def parse_results_log(path: Path) -> dict[str, dict]:
    """Read a previously emitted ``UAT_<x>_results.md`` back into
    ``{id: {"verdict", "evidence"}}``, so a walk can be **resumed** rather than
    started blind every time the sidebar is opened.

    If the same id appears more than once (an appended walk revisited an item
    -- e.g. it was deferred, then later actually walked), the **last**
    occurrence wins: sections are appended in walk order, so the last one is
    the freshest verdict. Earlier occurrences are not discarded from the file
    -- this only affects what is offered back into a session.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out: dict[str, dict] = {}
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        m = _RESULT_ITEM.match(lines[i])
        if not m:
            i += 1
            continue
        iid = m.group("id").strip()
        i += 1
        if i >= n:
            break
        tm = _RESULT_TAG.match(lines[i])
        if not tm:
            continue  # not our shape (e.g. hand-edited log); skip this item
        tag = tm.group("tag")
        verdict = _TAG_TO_VERDICT.get(tag)
        if verdict is None:
            i += 1
            continue
        inline = tm.group("inline")
        i += 1
        if inline is not None:
            evidence = inline
        elif i < n and lines[i].strip() == "```":
            i += 1
            collected: list[str] = []
            while i < n and lines[i].strip() != "```":
                # Undo the two-space indent build_results_body adds per line.
                collected.append(lines[i][2:] if lines[i][:2] == "  " else lines[i])
                i += 1
            i += 1  # past closing fence
            evidence = "\n".join(collected)
        else:
            evidence = ""
        out[iid] = {"verdict": verdict, "evidence": evidence}
    return out


def sheet_view(root: Path, stem: str) -> dict:
    """Everything Task 1/2's UI needs for one sheet: the parsed items, the
    checkbox counts on both the sheet and (if present) its results log, and
    the unticked-but-walked finding the board already surfaces -- shown here
    too, on the item view, per the board's ruling that an unticked sheet does
    not mean unwalked (UAT_docs_board_results.md, finding B1/B2).
    """
    root = Path(root)
    stem = _safe_stem(stem)
    sp = _resolve(sheet_path(root, stem), root)
    if not sp.is_file():
        raise DocumentRefused(
            "no_sheet", f"No walk-sheet docs/UAT_{stem}.md in this repository.")
    parsed = parse_sheet(sp)
    rp_raw = results_path(root, stem)
    rp = _resolve(rp_raw, root) if rp_raw.is_file() else rp_raw
    results_exists = rp.is_file()

    sheet_boxes = _count_checkboxes(sp)
    results_boxes = _count_checkboxes(rp) if results_exists else {"done": 0, "open": 0}
    evidence_in_results = bool(
        results_exists and sheet_boxes["done"] == 0 and sheet_boxes["open"] > 0
        and results_boxes["done"] > 0)
    # Resume support: what was already recorded, so opening the sidebar on a
    # half-walked sheet is never a blank slate. Read-only -- this does not
    # change what emit does; it only offers prior verdicts back to the caller.
    prior_entries = parse_results_log(rp) if results_exists else {}

    return {
        "stem": stem,
        "sheet_rel": f"{DOCS_DIRNAME}/UAT_{stem}.md",
        "results_rel": f"{DOCS_DIRNAME}/UAT_{stem}_results.md",
        "results_exists": results_exists,
        "sheet_boxes": sheet_boxes,
        "results_boxes": results_boxes,
        "evidence_in_results_log": evidence_in_results,
        "sections": parsed["sections"],
        "verdicts": list(VERDICTS),
        "prior_entries": prior_entries,
        "note": (
            "This sheet reads 0 done, but its results log already carries "
            "ticks -- it was walked with the evidence recorded there instead "
            "of on the sheet. Not untouched work; see the results log "
            "alongside before treating any item here as unwalked."
            if evidence_in_results else None),
    }


# --- Task 2: record verdicts and evidence ------------------------------------

def validate_entries(entries: list[dict]) -> list[str]:
    """Pure validation, no filesystem: a deferred/blocked entry must carry a
    reason in its evidence box. Returns human-readable errors, empty if none.
    """
    errors: list[str] = []
    for e in entries:
        iid = e.get("id") or "?"
        verdict = e.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{iid}: unknown verdict {verdict!r}")
            continue
        if verdict in _REASON_REQUIRED and not (e.get("evidence") or "").strip():
            errors.append(
                f"{iid}: '{verdict}' requires a reason recorded in the "
                f"evidence box -- the useful line in every existing log is "
                f"the one saying why, not just that.")
    return errors


# --- Task 3: emit the results log, stamped -----------------------------------

def stamp_fields() -> dict:
    """commit/dirty from the toolkit's own git state (the same helper every
    scan output already stamps with), host from this machine, walked=today.
    No `gate=` field -- deliberate, per docs/README.md §3 and this brief."""
    info = toolkit_git_info()
    return {
        "commit": info["commit"] or "unknown",
        "dirty": bool(info["dirty"]),
        "host": hostname(),
        "walked": date.today().isoformat(),
    }


def _uat_comment(stamp: dict) -> str:
    return (f"<!-- uat: commit={stamp['commit']} "
            f"dirty={'true' if stamp['dirty'] else 'false'} "
            f"host={stamp['host']} walked={stamp['walked']} -->")


def witness_citation_line(root: Path, stem: str, current_commit: str) -> tuple[str, dict]:
    """A visible prose line citing the witness run backing this sheet's
    machine-verified section -- **never an HTML comment** (DECISIONS 0031
    Task 6: a comment beside the uat stamp would eventually be read as a
    second stamp). Points at a run that happened elsewhere; it carries enough
    to re-derive the result (artefact path, fixture, commit, when it ran),
    never the result itself.

    Returns ``(line, items)`` where ``items`` maps item id ->
    ``{"outcome", "detail"}``. If no artefact exists this is reported in the
    line itself, never silently omitted (0031 Task 6: a missing artefact must
    not produce a results log that looks complete).
    """
    path = root / "data" / "witness" / f"{stem}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, ValueError):
        record = None

    if record is None:
        return (
            f"_No witness artefact found at `data/witness/{stem}.json` for this "
            f"sheet. The machine-verified section below has no witness "
            f"observations to cite -- reported here, not silently omitted._",
            {},
        )

    witness_commit = record.get("commit")
    stale = bool(witness_commit) and witness_commit != current_commit
    stale_note = (
        f" **Stale**: the witness ran at commit `{witness_commit}`, this walk "
        f"is at `{current_commit}`." if stale else "")
    line = (
        f"Machine-verified items below are cited from a witness run: "
        f"`data/witness/{stem}.json`, fixture `{record.get('fixture', '?')}`, "
        f"commit `{witness_commit or '?'}`, ran {record.get('ran_at', '?')} on "
        f"`{record.get('host', '?')}`. Re-run the witness at that commit "
        f"against that fixture to re-derive these observations.{stale_note}")
    items = {
        it["id"]: {"outcome": it.get("outcome"), "detail": it.get("detail", "")}
        for it in record.get("items", []) if "id" in it
    }
    return line, items


def build_results_body(root: Path, stem: str, sheet_rel: str, sections: list[dict],
                       entries_by_id: dict, stamp: dict) -> str:
    """The body markdown for a *new* results log (no stamp comment -- the
    caller prepends that, so an append can keep the ORIGINAL stamp rather than
    overwrite it with today's).

    If any item on the sheet carries a `[G]`/`[W]`/`[H]` layer marker
    (DECISIONS 0031's assignment rule), the log splits into a
    **Machine-verified** section (`[G]`/`[W]` items, cited from a witness run,
    no human verdict field) and a **Human ruling** section (`[H]` items only,
    exactly as long as Tim's judgement is required). A sheet with no markers
    at all keeps the original flat-by-section shape unchanged.
    """
    title = stem.replace("_", " ")
    lines: list[str] = []
    lines.append(f"# Results log — {title} (walked {stamp['walked']}, {stamp['host']})")
    lines.append("")
    lines.append(f"Partner to `{sheet_rel}`.")
    lines.append("")
    lines.append(
        "This log records a verdict and its evidence per item -- never a "
        "computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` "
        "deferred, with a reason · `[BLOCKED]` blocked, with a reason · "
        "`[N/A]` not applicable.")
    lines.append("")
    lines.append("---")
    lines.append("")

    has_layers = any(it.get("layer") for sec in sections for it in sec["items"])
    not_walked: list[tuple[str, str, str, str]] = []
    any_items = False

    def _item_lines(it: dict, e: dict) -> list[str]:
        tag = _TAG[e["verdict"]]
        evidence = (e.get("evidence") or "").strip()
        out = [f"- **{it['id']}** {it['text']}"]
        # Pasted terminal output must survive verbatim -- a fenced block,
        # never a paraphrase, and never re-wrapped.
        if "\n" in evidence:
            out.append(f"  [{tag}]")
            out.append("  ```")
            for ln in evidence.splitlines():
                out.append(f"  {ln}")
            out.append("  ```")
        else:
            out.append(f"  [{tag}] {evidence}".rstrip())
        out.append("")
        return out

    if not has_layers:
        for sec in sections:
            sec_items = [it for it in sec["items"] if it["id"] in entries_by_id]
            if not sec_items:
                continue
            any_items = True
            lines.append(f"## {sec['label']}")
            lines.append("")
            for it in sec_items:
                e = entries_by_id[it["id"]]
                lines.extend(_item_lines(it, e))
                if e["verdict"] != "walked":
                    not_walked.append(
                        (it["id"], it["text"], _TAG[e["verdict"]],
                         (e.get("evidence") or "").strip()))
    else:
        witness_line, witness_items = witness_citation_line(root, stem, stamp["commit"])
        machine_entered = [
            it for sec in sections for it in sec["items"]
            if it.get("layer") in ("G", "W") and it["id"] in entries_by_id]
        # A [G]/[W] item never given a UI verdict still belongs here if the
        # witness has an observation for it -- its status comes from the
        # witness/gate, never from a human picking a verdict.
        machine_witness_only = [
            it for sec in sections for it in sec["items"]
            if it.get("layer") in ("G", "W") and it["id"] in witness_items
            and it["id"] not in entries_by_id]
        # An item with NO marker at all (the rule couldn't place it -- see
        # DECISIONS 0031's "unplaceable case" stop condition) defaults into
        # Human ruling rather than vanishing from the log: an entered verdict
        # must never be silently dropped just because a marker is missing.
        human_entered = [
            it for sec in sections for it in sec["items"]
            if it.get("layer") in ("H", None) and it["id"] in entries_by_id]

        lines.append("## Machine-verified")
        lines.append("")
        lines.append(witness_line)
        lines.append("")
        machine_all = machine_entered + machine_witness_only
        if machine_all:
            any_items = True
            for it in machine_all:
                obs = witness_items.get(it["id"])
                lines.append(f"- **{it['id']}** {it['text']}")
                if obs:
                    detail = f" — {obs['detail']}" if obs.get("detail") else ""
                    lines.append(f"  [{obs['outcome']}]{detail}")
                else:
                    lines.append(
                        "  [no witness observation] not present in the cited "
                        "witness artefact for this item id")
                lines.append("")
        else:
            lines.append("_No `[G]`/`[W]` items were recorded on this walk._")
            lines.append("")

        lines.append("## Human ruling")
        lines.append("")
        if human_entered:
            any_items = True
            for it in human_entered:
                e = entries_by_id[it["id"]]
                lines.extend(_item_lines(it, e))
                if e["verdict"] != "walked":
                    not_walked.append(
                        (it["id"], it["text"], _TAG[e["verdict"]],
                         (e.get("evidence") or "").strip()))
        else:
            lines.append("_No `[H]` items were recorded on this walk._")
            lines.append("")

    if not any_items:
        lines.append("_No items were recorded on this walk._")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Not walked, and why")
    lines.append("")
    if not_walked:
        for iid, text, tag, ev in not_walked:
            lines.append(f"- **{iid}** [{tag}] {text} — {ev}")
    else:
        lines.append(
            "Everything recorded on this walk carries a `[EVIDENCE]` verdict "
            "or a witness observation.")
    lines.append("")
    return "\n".join(lines)


def stage_file(root: Path, rel: str) -> None:
    """`git add` the emitted file. Never `git add -A`, never `git commit` --
    DECISIONS 0028 confines this module to staging one named file."""
    run_git(root, "add", "--", rel)


def emit_results_log(root: Path, stem: str, entries: list[dict],
                     mode: str | None = None) -> dict:
    """Emit ``docs/UAT_<stem>_results.md``, staged.

    ``mode`` is ``None`` for a first attempt: if a results log already exists,
    this returns ``status="exists"`` and writes nothing, so the caller can ask
    the human whether to append or refuse. ``mode="append"`` adds a new walk
    section under the ORIGINAL stamp (testimony is not edited -- the golden
    close-out preserved a superseded first pass rather than editing it).
    ``mode="new"`` requires the file not exist (a race guard, not a normal path).
    """
    root = Path(root)
    stem = _safe_stem(stem)
    errors = validate_entries(entries)
    if errors:
        raise ValueError("; ".join(errors))

    rp = results_path(root, stem)
    exists = rp.is_file()
    rel = f"{DOCS_DIRNAME}/UAT_{stem}_results.md"

    if exists and mode not in ("append",):
        return {
            "status": "exists", "rel": rel,
            "detail": "A results log already exists for this sheet. Testimony "
                      "is not silently overwritten -- append a new walk "
                      "section, or refuse.",
        }
    if not exists and mode == "append":
        # append with nothing to append to: fall through to a fresh emit.
        mode = None

    view = sheet_view(root, stem)
    entries_by_id = {e["id"]: e for e in entries}

    if exists:
        prior = _resolve(rp, root).read_text(encoding="utf-8", errors="replace")
        # Keep the file's ORIGINAL stamp line(s) -- never rewritten -- and
        # append a dated section under a fresh stamp for THIS walk, so a cold
        # read still knows which commit produced which section.
        stamp = stamp_fields()
        addendum_body = build_results_body(
            root, stem, view["sheet_rel"], view["sections"], entries_by_id, stamp)
        # Drop the addendum's own title line (the file already has one); keep
        # everything from "Partner to" onward as a fresh dated block.
        addendum = "\n".join(addendum_body.splitlines()[2:])
        text = (prior.rstrip("\n") + "\n\n---\n\n"
                f"## Additional walk — {stamp['walked']}, {stamp['host']} "
                f"({_uat_comment(stamp)})\n\n" + addendum + "\n")
        status = "appended"
    else:
        stamp = stamp_fields()
        body = build_results_body(
            root, stem, view["sheet_rel"], view["sections"], entries_by_id, stamp)
        text = _uat_comment(stamp) + "\n\n" + body
        status = "created"

    out_path = root / DOCS_DIRNAME / f"UAT_{stem}_results.md"
    out_path.write_text(text, encoding="utf-8")
    stage_file(root, rel)
    return {"status": status, "rel": rel, "staged": True, "stamp": stamp}
