"""estate_diff -- what changed across the estate since the previous snapshot.

Read-only consumer of the per-run trail that ``build`` deposits in
``data/history/``. It compares the two most recent ``estate-YYYY-MM-DD.json``
snapshots and reports, per project:

* moved git HEADs, with the specific new commits (from ``git_deep_history``)
* documentation deltas -- added / removed / changed ``.md`` files
  (``smelt-gateway``'s ``wiki_shards`` changes are surfaced separately)
* projects that appeared or disappeared

This is the deterministic "what happened last sync" feed the knight consumes.
It never walks live repos and never writes -- the only writer is the runner via
``common.write_json``. Excluded from ``build`` (``SKIP_IN_BUILD``) because it
consumes the very snapshot build produces.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..common import DATA_DIR
from ..contract import SAFE

NAME = "estate_diff"
DESCRIPTION = "Diff the two most recent estate snapshots: moved HEADs, new commits, doc deltas."
ESTATE_LEVEL = True
SAFETY = SAFE
SKIP_IN_BUILD = True  # consumes build's output; run it separately, after build


def _history_dir() -> Path:
    return DATA_DIR / "history"


def _recent_snapshots(limit: int = 2) -> list[Path]:
    """The most recent snapshot files, oldest-first. Names sort chronologically."""
    hist = _history_dir()
    if not hist.exists():
        return []
    snaps = sorted(hist.glob("estate-*.json"))
    return snaps[-limit:]


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _projects_by_name(snapshot: dict) -> dict[str, dict]:
    return {p.get("name", ""): p for p in snapshot.get("projects", []) if p.get("name")}


def _doc_signatures(project: dict) -> dict[str, tuple]:
    """path -> (bytes, words, headings) for every markdown doc in doc_census."""
    census = project.get("doc_census") or {}
    sigs: dict[str, tuple] = {}
    for d in census.get("docs", []):
        sigs[d.get("path", "")] = (d.get("bytes"), d.get("words"), d.get("headings"))
    return sigs


def _git_diff(prev: dict, curr: dict) -> dict | None:
    """Detect a moved HEAD and enumerate the new commits, or None if unchanged."""
    prev_gs = prev.get("git_summary") or {}
    curr_gs = curr.get("git_summary") or {}
    prev_head = prev_gs.get("latest_hash")
    curr_head = curr_gs.get("latest_hash")
    if not curr_gs.get("is_git", prev_gs.get("is_git")):
        return None
    if prev_head == curr_head:
        return None

    prev_hashes = {c.get("hash") for c in (prev.get("git_deep_history") or {}).get("commits", [])}
    new_commits = [
        {"hash": c.get("hash"), "date": c.get("date"), "subject": c.get("subject")}
        for c in (curr.get("git_deep_history") or {}).get("commits", [])
        if c.get("hash") not in prev_hashes
    ]
    return {
        "from_head": prev_head,
        "to_head": curr_head,
        "new_commit_count": len(new_commits),
        "new_commits": new_commits,
    }


def _doc_diff(prev: dict, curr: dict) -> dict:
    prev_sigs = _doc_signatures(prev)
    curr_sigs = _doc_signatures(curr)
    added = sorted(set(curr_sigs) - set(prev_sigs))
    removed = sorted(set(prev_sigs) - set(curr_sigs))
    changed = sorted(p for p in (set(prev_sigs) & set(curr_sigs))
                     if prev_sigs[p] != curr_sigs[p])
    return {"added": added, "removed": removed, "changed": changed}


def _is_wiki_shard(path: str) -> bool:
    return "wiki_shards" in path.replace("\\", "/").split("/")


def scan_estate(projects: list[Path]) -> dict:  # noqa: ARG001 -- reads snapshots, not live repos
    snaps = _recent_snapshots(2)
    if len(snaps) < 2:
        return {
            "status": "insufficient_history",
            "snapshots_available": len(snaps),
            "note": "Need at least two build snapshots in data/history/ to diff.",
        }

    prev_path, curr_path = snaps[-2], snaps[-1]
    prev, curr = _load(prev_path), _load(curr_path)
    prev_p = _projects_by_name(prev)
    curr_p = _projects_by_name(curr)

    projects_added = sorted(set(curr_p) - set(prev_p))
    projects_removed = sorted(set(prev_p) - set(curr_p))

    changed: list[dict] = []
    wiki_shard_changes: list[dict] = []
    for name in sorted(set(prev_p) & set(curr_p)):
        git = _git_diff(prev_p[name], curr_p[name])
        docs = _doc_diff(prev_p[name], curr_p[name])
        has_doc_change = any(docs.values())
        if not git and not has_doc_change:
            continue

        entry: dict = {"project": name}
        if git:
            entry["git"] = git
        if has_doc_change:
            entry["docs"] = docs
        changed.append(entry)

        shard_hits = {
            k: [p for p in v if _is_wiki_shard(p)]
            for k, v in docs.items()
        }
        if any(shard_hits.values()):
            wiki_shard_changes.append({"project": name, **shard_hits})

    total_new_commits = sum(
        c["git"]["new_commit_count"] for c in changed if "git" in c
    )

    return {
        "status": "ok",
        "from_snapshot": prev_path.name,
        "to_snapshot": curr_path.name,
        "from_generated_at": prev.get("generated_at"),
        "to_generated_at": curr.get("generated_at"),
        "summary": {
            "projects_changed": len(changed),
            "projects_added": len(projects_added),
            "projects_removed": len(projects_removed),
            "new_commits": total_new_commits,
        },
        "projects_added": projects_added,
        "projects_removed": projects_removed,
        "changed": changed,
        "wiki_shard_changes": wiki_shard_changes,
    }
