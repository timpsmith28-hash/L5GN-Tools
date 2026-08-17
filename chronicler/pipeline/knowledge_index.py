"""knowledge_index.py -- K1, COWORK_BRIEF_knowledge_curator.md.

Loads the RATIFIED ``config/mcf_conversation_map.tsv`` (K0's output, once a
human has checked it -- this module never derives the map itself), joins it
against the real Cowork transcript store on this machine (exact, on
``session_id`` == the ``local_<uuid>`` conversation id -- never on `cwd`,
never re-derived from title text), globs each mapped project's
``*KNOWLEDGE*.md`` files reusing ``doc_census``'s existing rule, and writes
``data/knowledge_curator/knowledge_index.json``.

Reuses ``local_transcripts.py`` for discovery/parsing/grouping and
``bootstrap_conversation_map.discover_conversations`` for the Cowork-store
walk -- no second discoverer. Read-only: never writes into the transcript
store, the map, or any project's files.

Usage:
    python3 knowledge_index.py [--map PATH] [--host HOST] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_PIPE = Path(__file__).resolve().parent
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))
import local_transcripts as lt  # noqa: E402
import bootstrap_conversation_map as k0  # noqa: E402

_REPO_ROOT = _PIPE.parent.parent  # chronicler/pipeline -> chronicler -> L5GN-Tools
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from l5gntools.scanners.doc_census import classify_doc_type  # noqa: E402
from l5gntools.common import iter_files  # noqa: E402
from l5gntools import config as l5gn_config  # noqa: E402
from chronicler.review import curator_data as _cd  # noqa: E402

DEFAULT_MAP = Path("config/mcf_conversation_map.tsv")
DEFAULT_OUT = Path("data/knowledge_curator/knowledge_index.json")


# ---------------------------------------------------------------------------
# The ratified map
# ---------------------------------------------------------------------------

@dataclass
class MapRow:
    session_id: str
    local_folder: str
    project_id: str
    conversation_name: str
    notes: str = ""


def load_map(path: Path) -> list[MapRow]:
    """The RESOLVED join of record (DECISIONS 0046 clause 2) -- delegates
    to ``curator_data.resolved_map_rows``, the one place recency resolution
    happens, rather than re-reading the TSV itself. This module used to
    open the file with its own ``csv.DictReader`` loop, independent of
    ``curator_data`` entirely; that was the second implementation 0046
    clause 2 named directly ("two implementations of the join of record is
    one more than can be kept correct"). ``match_claims.py`` imports this
    function too, so fixing it here fixes both consumers.

    A blank ``session_id`` is still excluded here defensively, though
    ``resolved_map_rows`` already drops blank keys itself."""
    rows: list[MapRow] = []
    for rec in _cd.resolved_map_rows(path):
        sid = (rec.get("session_id") or "").strip()
        if not sid:
            continue
        rows.append(MapRow(
            session_id=sid,
            local_folder=(rec.get("local_folder") or "").strip(),
            project_id=(rec.get("project_id") or "").strip(),
            conversation_name=(rec.get("conversation_name") or "").strip(),
            notes=(rec.get("notes") or "").strip(),
        ))
    return rows


# ---------------------------------------------------------------------------
# Project folder resolution
# ---------------------------------------------------------------------------

def mcf_root(host: str | None = None) -> Path | None:
    """The configured root tagged ``scope: "mcf"`` (DECISIONS 0012) -- never
    guessed at from folder nesting. None if this machine has no such root
    (e.g. the personal rig)."""
    for entry in l5gn_config.estate_roots_tagged(host):
        if entry.get("scope") == "mcf":
            return entry["path"]
    return None


def project_dir_for(local_folder: str, root: Path | None) -> Path | None:
    """The mapped project's folder on disk. The curated map's
    ``local_folder`` is expected to already be the ratified, resolved label
    (brief: folder/label inconsistencies get resolved once, explicitly, at
    ratification time, not fuzzy-matched here) -- this only strips a
    leading root-name segment (``"MCF/PricingModel"`` -> ``"PricingModel"``)
    and joins the rest under the configured mcf-scoped root."""
    if root is None or not local_folder:
        return None
    parts = local_folder.replace("\\", "/").split("/")
    if parts and parts[0].lower() == root.name.lower():
        parts = parts[1:]
    if not parts:
        return None
    return root.joinpath(*parts)


def knowledge_files(project_dir: Path) -> list[str]:
    """``*KNOWLEDGE*.md`` under ``project_dir``, relative paths, sorted --
    reuses ``doc_census.classify_doc_type``'s existing rule (0026: stem
    contains ``_knowledge`` case-insensitively, unanchored). Never a second
    rule invented here."""
    out: list[str] = []
    for path in iter_files(project_dir, suffixes=(".md",)):
        relpath = str(path.relative_to(project_dir)).replace("\\", "/")
        if classify_doc_type(relpath) == "knowledge":
            out.append(relpath)
    return sorted(out)


# ---------------------------------------------------------------------------
# Title-prefix sanity check -- report only, never resolve (brief).
# ---------------------------------------------------------------------------

def title_disagreement(row: MapRow, conv) -> str | None:
    top_level = [s for s in conv.sessions if not s.is_sidechain]
    if not top_level or not row.conversation_name:
        return None
    title = (top_level[0].title or "").strip()
    curated = row.conversation_name.strip()
    if not title:
        return None
    if title.casefold() == curated.casefold():
        return None
    prefix_len = min(20, len(curated))
    if prefix_len and title.casefold().startswith(curated.casefold()[:prefix_len]):
        return None
    return f"curated name {curated!r} vs conversation title {title!r}"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_index(map_rows: list[MapRow], conversations_by_id: dict, root: Path | None) -> dict:
    projects: dict[str, dict] = {}
    label_disagreements: list[dict] = []

    for row in map_rows:
        proj = projects.setdefault(row.project_id, {
            "project_id": row.project_id,
            "local_folder": row.local_folder,
            "conversations": [],
            "knowledge_files": [],
        })
        proj["conversations"].append(row.session_id)

        conv = conversations_by_id.get(row.session_id)
        if conv is not None:
            disagreement = title_disagreement(row, conv)
            if disagreement:
                label_disagreements.append({
                    "session_id": row.session_id,
                    "project_id": row.project_id,
                    "disagreement": disagreement,
                })

    # Three-state resolution per project, per K1: no mapping / mapped but
    # folder absent on this machine / present but unreadable. A project that
    # resolves cleanly and simply has zero KNOWLEDGE*.md files is NOT
    # unresolved -- it is included with an empty list (K1's own rule) so K4
    # can tell "no knowledge file yet" apart from "couldn't even look".
    unresolved: list[dict] = []
    for proj in projects.values():
        project_dir = project_dir_for(proj["local_folder"], root)
        if project_dir is None:
            proj["knowledge_files"] = []
            unresolved.append({
                "project_id": proj["project_id"], "state": "no mapping",
                "detail": "no mcf-scoped root configured on this machine, or "
                          "local_folder is blank -- cannot resolve a directory at all",
            })
            continue
        if not project_dir.is_dir():
            proj["knowledge_files"] = []
            unresolved.append({
                "project_id": proj["project_id"], "state": "mapped but folder absent on this machine",
                "detail": str(project_dir),
            })
            continue
        try:
            proj["knowledge_files"] = knowledge_files(project_dir)
        except OSError as exc:
            proj["knowledge_files"] = []
            unresolved.append({
                "project_id": proj["project_id"], "state": "present but unreadable",
                "detail": f"{project_dir}: {exc}",
            })

    mapped_ids = {r.session_id for r in map_rows}
    on_disk_ids = set(conversations_by_id)
    mapped_but_absent_on_disk = sorted(mapped_ids - on_disk_ids)
    present_not_mapped = sorted(on_disk_ids - mapped_ids)

    return {
        "projects": sorted(projects.values(), key=lambda p: p["project_id"]),
        "unresolved": unresolved,
        "label_disagreements": label_disagreements,
        "mapped_but_absent_on_disk": mapped_but_absent_on_disk,
        "present_not_mapped": present_not_mapped,
    }


def write_index(index: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, indent=2, sort_keys=False), encoding="utf-8")


def _print_report(index: dict) -> None:
    print(f"projects mapped:            {len(index['projects'])}")
    no_kf = sum(1 for p in index["projects"] if not p["knowledge_files"])
    print(f"projects with no KNOWLEDGE*.md: {no_kf}")
    print(f"unresolved project dirs:    {len(index['unresolved'])}")
    for u in index["unresolved"]:
        print(f"    [{u['state']}] {u['project_id']}: {u['detail']}")
    print(f"label disagreements:        {len(index['label_disagreements'])}")
    for d in index["label_disagreements"]:
        print(f"    {d['session_id']}: {d['disagreement']}")
    print(f"mapped but absent on disk:  {len(index['mapped_but_absent_on_disk'])}")
    for sid in index["mapped_but_absent_on_disk"]:
        print(f"    {sid}")
    print(f"present on disk, not mapped: {len(index['present_not_mapped'])}")
    for sid in index["present_not_mapped"]:
        print(f"    {sid}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--host", help="census as if run on this hostname")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    map_rows = load_map(args.map)
    conversations, access_errors = k0.discover_conversations(args.host)
    if access_errors:
        print("** filesystem access errors while discovering the store -- "
              "reconciliation below is NOT proof of a complete population **",
              file=sys.stderr)
        for e in access_errors:
            print(f"   {e}", file=sys.stderr)
    conversations_by_id = {c.conversation_id: c for c in conversations}
    root = mcf_root(args.host)

    index = build_index(map_rows, conversations_by_id, root)
    write_index(index, args.out)
    _print_report(index)
    print(f"\nknowledge index written: {args.out}")


if __name__ == "__main__":
    main()
