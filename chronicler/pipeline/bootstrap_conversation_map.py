"""bootstrap_conversation_map.py -- K0, COWORK_BRIEF_knowledge_curator.md.

One-time bootstrap: matches a curated sheet's captured opening prompts
against the REAL local Cowork transcript store on this machine to fill in
each row's ``session_id`` (the ``local_<uuid>`` conversation folder).

Produces a **candidate map for human ratification** -- it is never applied
automatically. Once Tim ratifies it into ``config/mcf_conversation_map.tsv``
the join is exact and this script never runs again (brief: "the fragile step
never runs again").

Reuses ``local_transcripts.py`` for discovery/parsing/grouping; does not
write a second discoverer. Reads only -- touches no transcript file, no
database, and writes only the candidate TSV named by ``--out``.

Sheet input (TSV, tab-separated, UTF-8, header row required):
    local_folder        the label as recorded on the sheet (e.g. "MCF/PricingModel")
    project_id          the sheet's project slug, if already assigned (may be blank)
    conversation_name    the human title, if already assigned (may be blank)
    date                 optional ISO date (YYYY-MM-DD); used only to pair
                          same-project duplicate-opener collisions
    1st User Message     the captured opening prompt (also accepted as the
                          column name "first_message")

Usage:
    python3 bootstrap_conversation_map.py sheet.tsv --out candidate_map.tsv
    python3 bootstrap_conversation_map.py sheet.tsv --host 10280L --out candidate_map.tsv
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import local_transcripts as lt  # noqa: E402

PASS1_CAP = 200
PASS2_MIN_LEN = 60

FIRST_MESSAGE_COLUMNS = ("1st User Message", "1st User Message*", "first_message")


# ---------------------------------------------------------------------------
# Normalisation -- applied to BOTH sides before any comparison. The sheet
# text has been through a Google Sheet, so curly quotes / dash substitution
# / stray whitespace are near-certain (brief: "a raw startswith will fail on
# invisible differences and the failure will look like a missing
# conversation").
# ---------------------------------------------------------------------------

def normalize(text: str | None) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("—", "-")
    t = t.replace(" ", " ")
    t = " ".join(t.split())
    return t.casefold()


# ---------------------------------------------------------------------------
# Sheet
# ---------------------------------------------------------------------------

@dataclass
class SheetRow:
    index: int
    local_folder: str
    project_id: str
    conversation_name: str
    date: str
    first_message_raw: str
    normalized: str = field(init=False)

    def __post_init__(self) -> None:
        self.normalized = normalize(self.first_message_raw)


def load_sheet(path: Path) -> list[SheetRow]:
    rows: list[SheetRow] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, rec in enumerate(reader):
            first_message = ""
            for col in FIRST_MESSAGE_COLUMNS:
                if rec.get(col):
                    first_message = rec[col]
                    break
            rows.append(SheetRow(
                index=i,
                local_folder=(rec.get("local_folder") or "").strip(),
                project_id=(rec.get("project_id") or "").strip(),
                conversation_name=(rec.get("conversation_name") or "").strip(),
                date=(rec.get("date") or "").strip(),
                first_message_raw=first_message,
            ))
    return rows


# ---------------------------------------------------------------------------
# Store side
# ---------------------------------------------------------------------------

def discover_conversations(host: str | None = None) -> tuple[list, list[str]]:
    """Every conversation in the Cowork store on this machine, oldest and
    newest alike -- K0 needs the whole population as match candidates, not
    just the ordered/included ones. Returns (conversations, access_errors).
    K0 works the Cowork store only; CLI sessions are never MCF conversations
    (no `local_<uuid>` grouping folder exists in that store at all)."""
    cfg = lt.machine(host)
    root = cfg.get("cowork_transcripts_home")
    if not root:
        return [], []
    root = Path(root)
    if not root.is_dir():
        return [], []
    errors: list[str] = []
    sessions = [lt.parse_session(tf) for tf in lt.discover_cowork_store(root, errors)]
    return lt.group_conversations(sessions), errors


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    row: SheetRow
    session_id: str | None = None
    match_pass: str | None = None      # "pass1" | "pass2"
    matched_length: int | None = None
    candidate_count: int = 0
    status: str = "unmatched"          # matched | ambiguous-same-project | ambiguous-different-project | unmatched
    note: str = ""


def pass1_match(sheet_norm: str, conv_norm: str) -> int | None:
    """The full (200-char-capped) sheet text must literally prefix the
    conversation's real opener. Returns the matched length, or None. A short
    sheet entry (e.g. 13 chars) still matches here if it prefixes exactly --
    pass 1 has no minimum length of its own; the 32/200 figures in the brief
    describe how *discriminating* a prefix of that length is across the real
    48-row sheet, not a floor this function enforces."""
    a = sheet_norm[:PASS1_CAP]
    n = len(a)
    if n == 0 or len(conv_norm) < n:
        return None
    return n if conv_norm[:n] == a else None


def pass2_match(sheet_norm: str, conv) -> bool:
    """Full-content substring search across every user message of every file
    in `conv`. Caller enforces the >=60-char floor before calling this --
    this function does not re-check it, so it must never be called on a
    short chunk (brief: searching a 13-char string across every message
    would match any thread that merely mentions it)."""
    for sess in conv.sessions:
        for _, role, text, _, _ in sess.messages:
            if role != "user" or not text:
                continue
            if sheet_norm in normalize(text):
                return True
    return False


def _project_of(conv) -> str | None:
    return conv.cowork_project_dir


def _sort_key_for_row(row: SheetRow):
    return (row.date or "", row.index)


def _sort_key_for_conv(conv) -> str:
    return conv.real_time or ""


def _classify_ambiguous(candidates: list, conversations_by_id: dict) -> tuple[str, set]:
    projects = {_project_of(conversations_by_id[cid]) for cid in candidates}
    if len(projects) == 1:
        return "ambiguous-same-project", projects
    return "ambiguous-different-project", projects


def _run_pass(rows: list[SheetRow], conv_ids: list[str], conv_openers: dict,
              conversations_by_id: dict, pass_name: str,
              matcher) -> tuple[dict[int, MatchResult], set[str]]:
    """Shared machinery for pass 1 and pass 2: group sheet rows by identical
    normalised text (this is what a genuine sheet-side duplicate opener
    looks like), find each group's disk candidates among `conv_ids`, and
    resolve. Returns (results keyed by row.index, set of conv_ids claimed).
    """
    by_text: dict[str, list[SheetRow]] = {}
    for r in rows:
        by_text.setdefault(r.normalized, []).append(r)

    results: dict[int, MatchResult] = {}
    claimed: set[str] = set()

    for text, group_rows in by_text.items():
        candidates = [cid for cid in conv_ids if matcher(text, conv_openers[cid])]
        n_rows, n_cand = len(group_rows), len(candidates)

        if n_cand == 0:
            for r in group_rows:
                results[r.index] = MatchResult(row=r, candidate_count=0)
            continue

        if n_rows == 1 and n_cand == 1:
            r = group_rows[0]
            res = MatchResult(row=r, session_id=candidates[0], match_pass=pass_name,
                               candidate_count=1, status="matched")
            if pass_name == "pass1":
                res.matched_length = pass1_match(text, conv_openers[candidates[0]])
            results[r.index] = res
            claimed.add(candidates[0])
            continue

        # Ambiguity: either several sheet rows share this opener, several
        # disk conversations share it, or both.
        klass, projects = _classify_ambiguous(candidates, conversations_by_id)

        if klass == "ambiguous-same-project" and n_rows == n_cand and n_rows > 1:
            # Brief: "colliding candidates that resolve to the same
            # project -> accept, split by date, flag the pair."
            ordered_rows = sorted(group_rows, key=_sort_key_for_row)
            ordered_cands = sorted(candidates, key=lambda c: _sort_key_for_conv(conversations_by_id[c]))
            proj = next(iter(projects))
            for r, cid in zip(ordered_rows, ordered_cands):
                results[r.index] = MatchResult(
                    row=r, session_id=cid, match_pass=pass_name,
                    candidate_count=n_cand, status="ambiguous-same-project",
                    note=(f"{n_rows} sheet rows and {n_cand} disk conversations shared "
                          f"one opener, all in project {proj!r}; paired by date/order"),
                )
                claimed.add(cid)
            continue

        # Anything else colliding (different projects, or same project but
        # cardinality doesn't pair cleanly) is refused, not guessed -- 0011's
        # lesson: a generator writing an identity nobody ratified is how a
        # second generation of junk grows back.
        note = (f"{n_rows} sheet row(s), {n_cand} disk candidate(s), "
                f"project(s) {sorted(p or '(unknown)' for p in projects)}; refused")
        for r in group_rows:
            results[r.index] = MatchResult(
                row=r, match_pass=pass_name, candidate_count=n_cand,
                status=klass, note=note,
            )

    return results, claimed


def match(rows: list[SheetRow], conversations: list) -> list[MatchResult]:
    conversations_by_id = {c.conversation_id: c for c in conversations}
    conv_openers = {cid: normalize(lt.first_user_message(c) or "")
                     for cid, c in conversations_by_id.items()}
    all_conv_ids = list(conversations_by_id)

    # --- Pass 1 ---------------------------------------------------------
    pass1_results, pass1_claimed = _run_pass(
        rows, all_conv_ids, conv_openers, conversations_by_id, "pass1",
        lambda text, opener: pass1_match(text, opener) is not None,
    )

    # Only rows pass 1 found ZERO candidates for proceed to pass 2. A row
    # pass 1 flagged ambiguous is refused permanently (brief: colliding
    # candidates are accepted-and-paired or refused, never retried) --
    # retrying it in pass 2 could silently resolve an ambiguity pass 1
    # explicitly declined to guess at.
    unresolved_rows = [r for r in rows if pass1_results[r.index].status == "unmatched"]
    unmatched_conv_ids = [cid for cid in all_conv_ids if cid not in pass1_claimed]

    # Rows below the pass-2 floor never reach it -- reported unmatched with
    # the reason named, not silently guessed at.
    eligible_for_pass2 = [r for r in unresolved_rows if len(r.normalized) >= PASS2_MIN_LEN]
    too_short = [r for r in unresolved_rows if len(r.normalized) < PASS2_MIN_LEN]

    # --- Pass 2 -----------------------------------------------------------
    # Full-content substring search, not a prefix match against a single
    # opener string, so this does not reuse `_run_pass`'s (text, opener)
    # matcher shape -- it needs the whole conversation (every message of
    # every file) to search within.
    pass2_results: dict[int, MatchResult] = {}
    pass2_claimed: set[str] = set()
    by_text: dict[str, list[SheetRow]] = {}
    for r in eligible_for_pass2:
        by_text.setdefault(r.normalized, []).append(r)
    for text, group_rows in by_text.items():
        candidates = [cid for cid in unmatched_conv_ids
                      if cid not in pass2_claimed
                      and pass2_match(text, conversations_by_id[cid])]
        n_rows, n_cand = len(group_rows), len(candidates)
        if n_cand == 0:
            for r in group_rows:
                pass2_results[r.index] = MatchResult(row=r, match_pass="pass2", candidate_count=0)
            continue
        if n_rows == 1 and n_cand == 1:
            r = group_rows[0]
            pass2_results[r.index] = MatchResult(
                row=r, session_id=candidates[0], match_pass="pass2",
                candidate_count=1, status="matched",
            )
            pass2_claimed.add(candidates[0])
            continue
        klass, projects = _classify_ambiguous(candidates, conversations_by_id)
        note = (f"{n_rows} sheet row(s), {n_cand} disk candidate(s) in pass 2, "
                f"project(s) {sorted(p or '(unknown)' for p in projects)}; refused")
        for r in group_rows:
            pass2_results[r.index] = MatchResult(
                row=r, match_pass="pass2", candidate_count=n_cand, status=klass, note=note,
            )

    for r in too_short:
        pass2_results[r.index] = MatchResult(
            row=r, match_pass=None, candidate_count=0, status="unmatched",
            note=f"only {len(r.normalized)} normalised chars (<{PASS2_MIN_LEN}); "
                 f"never reaches pass 2, reported unmatched",
        )

    merged: dict[int, MatchResult] = {}
    for r in rows:
        if r.index in pass1_results and pass1_results[r.index].status != "unmatched":
            merged[r.index] = pass1_results[r.index]
        elif r.index in pass2_results:
            merged[r.index] = pass2_results[r.index]
        elif r.index in pass1_results:
            merged[r.index] = pass1_results[r.index]
        else:
            merged[r.index] = MatchResult(row=r, status="unmatched", note="no candidates in pass 1 or 2")

    return [merged[r.index] for r in rows]


# ---------------------------------------------------------------------------
# Report + output
# ---------------------------------------------------------------------------

def six_counts(results: list[MatchResult], all_conv_ids: list[str]) -> dict[str, int]:
    matched_pass1 = sum(1 for r in results if r.status == "matched" and r.match_pass == "pass1")
    matched_pass2 = sum(1 for r in results if r.status == "matched" and r.match_pass == "pass2")
    ambiguous_same = sum(1 for r in results if r.status == "ambiguous-same-project")
    ambiguous_diff = sum(1 for r in results if r.status == "ambiguous-different-project")
    unmatched = sum(1 for r in results if r.status == "unmatched")
    claimed = {r.session_id for r in results if r.session_id}
    unmapped_folders = len([cid for cid in all_conv_ids if cid not in claimed])
    return {
        "matched_by_pass1": matched_pass1,
        "matched_by_pass2": matched_pass2,
        "ambiguous_same_project": ambiguous_same,
        "ambiguous_different_project": ambiguous_diff,
        "unmatched_sheet_rows": unmatched,
        "unmapped_local_folders_on_disk": unmapped_folders,
    }


def write_candidate_map(results: list[MatchResult], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow([
            "session_id", "local_folder", "project_id", "conversation_name",
            "match_pass", "matched_length", "candidate_count", "status", "note",
        ])
        for r in results:
            w.writerow([
                r.session_id or "", r.row.local_folder, r.row.project_id,
                r.row.conversation_name, r.match_pass or "",
                r.matched_length if r.matched_length is not None else "",
                r.candidate_count, r.status, r.note,
            ])


def _print_report(counts: dict[str, int], unmapped_ids: list[str]) -> None:
    print("K0 bootstrap -- candidate map (NOT applied; ratify before committing)")
    for key, value in counts.items():
        print(f"  {key:32s} {value}")
    print(f"\n  {len(unmapped_ids)} local_* folder(s) present on disk, not claimed by any row:")
    for cid in sorted(unmapped_ids):
        print(f"    {cid}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet", type=Path, help="curated sheet TSV, with a 1st User Message column")
    ap.add_argument("--out", type=Path, default=Path("data/knowledge_curator/candidate_map.tsv"))
    ap.add_argument("--host", help="census as if run on this hostname")
    args = ap.parse_args()

    rows = load_sheet(args.sheet)
    conversations, access_errors = discover_conversations(args.host)
    if access_errors:
        print("** filesystem access errors while discovering the store -- results below "
              "are NOT proof of a complete population **", file=sys.stderr)
        for e in access_errors:
            print(f"   {e}", file=sys.stderr)

    results = match(rows, conversations)
    all_conv_ids = [c.conversation_id for c in conversations]
    counts = six_counts(results, all_conv_ids)
    claimed = {r.session_id for r in results if r.session_id}
    unmapped_ids = [cid for cid in all_conv_ids if cid not in claimed]

    write_candidate_map(results, args.out)
    _print_report(counts, unmapped_ids)
    print(f"\ncandidate map written: {args.out}")


if __name__ == "__main__":
    main()
