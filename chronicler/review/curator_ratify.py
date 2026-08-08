"""curator_ratify.py -- Task 2, COWORK_BRIEF_curator_tab.md.

The K0 ratification screen's logic: render ``candidate_map.tsv`` as
per-candidate cards grouped by outcome (all six K0 counts, including the
zeroes), compute the evidence display (normalised text with the matched span
marked), and append a ratified row to ``config/mcf_conversation_map.tsv``,
staged and never committed -- per DECISIONS 0033.

Every rule below is load-bearing and tester-proven, not merely documented:

  * **Per-row actions only.** Every public "ratify" function here takes
    exactly one candidate (or, for a same-project collision, exactly the
    two rows that collision paired) -- there is no list parameter anywhere
    in this module that could become a bulk-accept, because there is
    nowhere to put one.
  * **Never edits or removes an existing row.** ``append_ratified_row`` is a
    pure byte-append (opened ``"a"``, never ``"r+"`` or a rewrite), so there
    is no code path in this module that can touch a byte already on disk.
  * **Provenance is permanent.** Every appended row's ``notes`` field carries
    a machine-parseable ``[provenance:...]`` tag recording how the row was
    arrived at -- machine-matched by which pass, human-picked from a refused
    collision, or hand-mapped with no candidate at all (0033).
  * **Staged, never committed.** ``stage_ratified_map`` runs exactly
    ``git add -- config/mcf_conversation_map.tsv``, matching 0033's
    code-declared path allowlist. Nothing here calls ``git commit``.
  * **Honours K0's own refusal rules rather than re-litigating them**: a
    different-project collision is not offered a "ratify" action by this
    module at all -- see :func:`row_action`.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from l5gntools.common import run_git

from .curator_data import (CANDIDATE_MAP_PATH, RATIFIED_MAP_PATH,
                            RATIFIED_MAP_HEADER, _load_tsv_rows,
                            ratified_map_rows)

_PIPE = Path(__file__).resolve().parents[2] / "chronicler" / "pipeline"
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

#: 0033's provenance vocabulary -- the only tags this module ever writes.
#: A row resting on the operator's memory (hand-mapped) or a refused
#: collision (human-picked) says so permanently, in the file itself.
PROV_PASS1 = "machine-matched:pass-1"
PROV_PASS2 = "machine-matched:pass-2"
PROV_HUMAN_PICKED = "human-picked:refused-collision"
PROV_HAND_MAPPED = "hand-mapped:no-candidate"
PROVENANCE_TAGS = (PROV_PASS1, PROV_PASS2, PROV_HUMAN_PICKED, PROV_HAND_MAPPED)

#: K0's own outcome vocabulary, straight from bootstrap_conversation_map.py's
#: MatchResult.status -- reproduced here as constants only for readability,
#: never redefined or re-derived from anything but the TSV's own `status`
#: column.
STATUS_MATCHED = "matched"
STATUS_AMBIG_SAME = "ambiguous-same-project"
STATUS_AMBIG_DIFF = "ambiguous-different-project"
STATUS_UNMATCHED = "unmatched"

SIX_COUNT_KEYS = (
    "matched_by_pass1", "matched_by_pass2", "ambiguous_same_project",
    "ambiguous_different_project", "unmatched_sheet_rows",
    "unmapped_local_folders_on_disk",
)

PASS2_MIN_LEN = 60  # mirrors bootstrap_conversation_map.PASS2_MIN_LEN


class RatifyError(ValueError):
    """A ratify attempt that is refused. ``reason`` is a stable tag."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


# ---------------------------------------------------------------------------
# Evidence: normalisation + matched-span marking (reuses K0's own normalize())
# ---------------------------------------------------------------------------

def _normalize():
    import bootstrap_conversation_map as k0  # local import: optional heavy dep
    return k0.normalize


def evidence_spans(sheet_text: str | None, conv_text: str | None,
                    match_pass: str | None, matched_length: int | None) -> dict:
    """Normalise both sides (K0's own ``normalize()``, never a second
    normaliser) and locate the matched span in each, so the card can mark it
    visually. Returns ``{"sheet": {"text", "span"}, "conversation": {"text",
    "span"}}`` -- ``span`` is ``[start, end]`` in the *normalised* text, or
    ``None`` if it cannot be located (e.g. one side is unavailable).

    Pass 1 is a literal prefix match, so the span is always
    ``[0, matched_length)`` on both sides. Pass 2 is a full-content substring
    search, so the sheet's span is the whole normalised sheet text and the
    conversation's span is wherever that text is literally found inside the
    (longer) conversation opener -- re-located here with a plain substring
    search, never re-run through the model or re-scored.
    """
    normalize = _normalize()
    sheet_norm = normalize(sheet_text) if sheet_text is not None else None
    conv_norm = normalize(conv_text) if conv_text is not None else None

    sheet_span = None
    conv_span = None
    if sheet_norm is not None and conv_norm is not None:
        if match_pass == "pass1" and matched_length:
            n = min(matched_length, len(sheet_norm), len(conv_norm))
            sheet_span = [0, n]
            conv_span = [0, n]
        elif match_pass == "pass2":
            idx = conv_norm.find(sheet_norm)
            sheet_span = [0, len(sheet_norm)]
            conv_span = [idx, idx + len(sheet_norm)] if idx >= 0 else None

    return {
        "sheet": {"text": sheet_norm, "span": sheet_span},
        "conversation": {"text": conv_norm, "span": conv_span},
    }


# ---------------------------------------------------------------------------
# Cards: candidate_map.tsv grouped by outcome, six counts including zeroes
# ---------------------------------------------------------------------------

def six_counts(candidate_rows: list[dict], unmapped_folder_count: int) -> dict:
    """The six K0 counts, tallied from the TSV's own ``status``/``match_pass``
    columns -- a count of rows already on disk, never a recomputed match."""
    counts = {k: 0 for k in SIX_COUNT_KEYS}
    for r in candidate_rows:
        status = r.get("status", "")
        mpass = r.get("match_pass", "")
        if status == STATUS_MATCHED and mpass == "pass1":
            counts["matched_by_pass1"] += 1
        elif status == STATUS_MATCHED and mpass == "pass2":
            counts["matched_by_pass2"] += 1
        elif status == STATUS_AMBIG_SAME:
            counts["ambiguous_same_project"] += 1
        elif status == STATUS_AMBIG_DIFF:
            counts["ambiguous_different_project"] += 1
        elif status == STATUS_UNMATCHED:
            counts["unmatched_sheet_rows"] += 1
    counts["unmapped_local_folders_on_disk"] = unmapped_folder_count
    return counts


def row_action(row: dict) -> dict:
    """What the UI may offer for one candidate row, honouring K0's own rules
    rather than re-litigating them (brief, Task 2).

    * matched                       -> ratify (single row)
    * ambiguous-same-project        -> ratify_pair (offered on the GROUP,
                                        not the row -- see group_candidates)
    * ambiguous-different-project   -> NO ratify action at all: pick-one-by-
                                        hand (hand-map, with the refused-
                                        collision provenance) or leave unmatched
    * unmatched, below pass-2 floor -> says why it never reached pass 2
    * unmatched, at/above the floor -> hand-map only (no machine candidate)
    """
    status = row.get("status", "")
    if status == STATUS_MATCHED:
        return {"action": "ratify", "reason": None}
    if status == STATUS_AMBIG_SAME:
        return {"action": "ratify_pair", "reason":
                "Same-project collision: ratify as a pair, split by date."}
    if status == STATUS_AMBIG_DIFF:
        return {"action": "hand_map_or_leave", "reason":
                "Different-project collision: K0 refuses to guess. Pick one "
                "by hand (human-picked, refused-collision provenance) or "
                "leave unmatched."}
    # unmatched
    sheet_text = row.get("_sheet_text_normalized_len")
    too_short = False
    note = row.get("note", "")
    if "never reaches pass 2" in note or "<60" in note:
        too_short = True
    if too_short:
        return {"action": "hand_map_only", "reason":
                "Below the 60-character pass-2 floor -- never reached pass 2."}
    return {"action": "hand_map_only", "reason":
            "No machine candidate in pass 1 or pass 2."}


def candidate_cards(candidate_rows: list[dict], ratified_ids: set[str]) -> list[dict]:
    """One card per candidate row, each carrying its offered action. A row
    whose session_id is already ratified is marked ``already_ratified`` and
    offered no action -- re-ratifying is a no-op the UI must not invite."""
    cards = []
    for r in candidate_rows:
        sid = (r.get("session_id") or "").strip()
        already = bool(sid) and sid in ratified_ids
        action = {"action": "none", "reason": "Already ratified."} if already else row_action(r)
        cards.append({**r, "already_ratified": already, "offered_action": action})
    return cards


def group_by_outcome(cards: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {
        STATUS_MATCHED: [], STATUS_AMBIG_SAME: [], STATUS_AMBIG_DIFF: [],
        STATUS_UNMATCHED: [],
    }
    for c in cards:
        groups.setdefault(c.get("status", STATUS_UNMATCHED), []).append(c)
    return groups


# ---------------------------------------------------------------------------
# Unmapped local_* folders -- the retention finding, not a tidy-up list
# ---------------------------------------------------------------------------

def unmapped_local_folders(conversations, claimed_ids: set[str]) -> list[dict]:
    """Every ``local_<uuid>`` conversation on disk not claimed by any
    candidate/ratified row -- date and message count per folder, per the
    brief's framing: if these are conversations deleted in the Cowork UI,
    deleting a conversation does not delete its transcript. A data-retention
    finding about the work estate, not a tidy-up list.
    """
    out = []
    for conv in conversations:
        cid = getattr(conv, "conversation_id", None)
        if cid is None or cid in claimed_ids:
            continue
        msg_count = sum(len(s.messages) for s in conv.sessions)
        out.append({
            "conversation_id": cid,
            "real_time": conv.real_time,
            "real_time_source": conv.real_time_source,
            "message_count": msg_count,
            "cowork_project_dir": conv.cowork_project_dir,
        })
    out.sort(key=lambda e: e["real_time"] or "")
    return out


# ---------------------------------------------------------------------------
# Staging -- 0033's one map-specific allowlist entry
# ---------------------------------------------------------------------------

def _validate_new_row(row: dict) -> None:
    for field in RATIFIED_MAP_HEADER:
        if field not in row:
            raise RatifyError("missing_field", f"row is missing required field {field!r}")
    if not row["session_id"].strip():
        raise RatifyError("blank_session_id", "session_id must not be blank")
    if not row.get("notes", "").strip().startswith("[provenance:"):
        raise RatifyError(
            "missing_provenance",
            "0033 requires every staged row to record its provenance "
            "permanently in the file -- notes must start with a "
            "[provenance:...] tag.")
    tag = row["notes"].split("]", 1)[0] + "]"
    tagged = tag[len("[provenance:"):-1]
    if tagged not in PROVENANCE_TAGS:
        raise RatifyError("unknown_provenance", f"unrecognised provenance tag {tagged!r}")


def build_row(*, session_id: str, local_folder: str, project_id: str,
              conversation_name: str, provenance: str, note: str = "") -> dict:
    """Assemble one ratified-map row with its provenance tag permanently
    embedded in ``notes`` (there is no dedicated provenance column in the
    existing, already-shipped schema -- widening it would be a header edit
    this module refuses to make; the tag is the least invasive way to keep
    0033's promise inside the current column set)."""
    if provenance not in PROVENANCE_TAGS:
        raise RatifyError("unknown_provenance", f"unrecognised provenance tag {provenance!r}")
    tagged_note = f"[provenance:{provenance}]" + (f" {note}" if note else "")
    return {
        "session_id": session_id, "local_folder": local_folder,
        "project_id": project_id, "conversation_name": conversation_name,
        "notes": tagged_note,
    }


def _row_line(row: dict) -> str:
    return "\t".join(row[f] for f in RATIFIED_MAP_HEADER)


def append_ratified_row(row: dict, path: Path | None = None) -> dict:
    """Append exactly one row to the ratified map. Pure append -- opens the
    file in ``"a"`` mode and nothing else, so there is no code path here that
    can rewrite a byte already on disk (the stop condition this function
    exists to make impossible, not merely avoid).

    Refuses (writes nothing) if the session_id is already present -- ratifying
    an already-ratified row is a no-op, never a silent duplicate and never an
    edit of the existing one.
    """
    _validate_new_row(row)
    p = Path(path) if path else RATIFIED_MAP_PATH

    existing = _load_tsv_rows(p) if p.exists() else []
    existing_ids = {r.get("session_id", "").strip() for r in existing}
    if row["session_id"].strip() in existing_ids:
        return {"status": "already_ratified", "session_id": row["session_id"]}

    needs_header = not p.exists() or p.stat().st_size == 0
    with p.open("a", encoding="utf-8", newline="") as f:
        if needs_header:
            f.write("\t".join(RATIFIED_MAP_HEADER) + "\n")
        else:
            # Guard against a file with no trailing newline -- appending
            # straight onto the last line would corrupt it, which reads as
            # an edit of an existing row even though no byte of it was
            # touched by intent. Never happens for a file this module wrote
            # itself; guarded for a hand-edited or foreign file.
            with p.open("rb") as rf:
                rf.seek(0, 2)
                if rf.tell() > 0:
                    rf.seek(-1, 2)
                    if rf.read(1) != b"\n":
                        f.write("\n")
        f.write(_row_line(row) + "\n")

    return {"status": "appended", "session_id": row["session_id"], "row": row}


def append_ratified_pair(row_a: dict, row_b: dict, path: Path | None = None) -> list[dict]:
    """Same-project collision: ratify as a pair, split by date -- exactly the
    two rows K0's own pairing produced, appended one after the other. Still
    per-candidate (one collision group), never a bulk action: there is no
    path from here to a third row without a third explicit call."""
    r1 = append_ratified_row(row_a, path)
    r2 = append_ratified_row(row_b, path)
    return [r1, r2]


def stage_ratified_map(repo_root: Path) -> str:
    """``git add -- config/mcf_conversation_map.tsv``, and only that path --
    0033's allowlist entry, declared here in code. Never ``git add -A``,
    never ``git commit``."""
    run_git(repo_root, "add", "--", "config/mcf_conversation_map.tsv")
    return "config/mcf_conversation_map.tsv"


def staged_diff(repo_root: Path) -> str:
    """``git diff --staged`` for the map only -- what the tab shows must be
    exactly what a terminal ``git diff --staged`` would show, per the brief."""
    return run_git(repo_root, "diff", "--staged", "--", "config/mcf_conversation_map.tsv")
