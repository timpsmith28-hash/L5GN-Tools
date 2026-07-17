"""estate_diff: diff the two most recent snapshots -- moved HEADs with only the
NEW commits enumerated, doc add/remove/change deltas, wiki_shards surfaced
separately, and appeared/disappeared projects.

Hermetic: writes throwaway estate-YYYY-MM-DD.json snapshots into a temp history
dir and drives diff_history(dir) directly (no DATA_DIR, no live repos)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from l5gntools.scanners import estate_diff


def _doc(path: str, b: int, w: int, h: int) -> dict:
    return {"path": path, "bytes": b, "words": w, "headings": h}


def _write(history: Path, day: str, projects: list[dict]) -> None:
    (history / f"estate-{day}.json").write_text(
        json.dumps({"generated_at": f"{day}T09:00:00Z", "projects": projects}),
        encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        history = Path(td) / "history"
        history.mkdir()

        # ---- insufficient history: 0 then 1 snapshot ----
        if estate_diff.diff_history(history).get("status") != "insufficient_history":
            v.append("estate_diff: empty history should be insufficient_history")
        if estate_diff.diff_history(history)["snapshots_available"] != 0:
            v.append("estate_diff: 0 snapshots should be counted")
        _write(history, "2026-07-15", [
            {"name": "AppA",
             "git_summary": {"is_git": True, "latest_hash": "h1"},
             "git_deep_history": {"commits": [{"hash": "h1", "date": "2026-07-14", "subject": "c1"}]},
             "doc_census": {"docs": [_doc("docs/a.md", 100, 20, 2),
                                     _doc("docs/gone.md", 50, 10, 1)]}},
            {"name": "AppUnchanged",
             "git_summary": {"is_git": True, "latest_hash": "u1"},
             "doc_census": {"docs": [_doc("README.md", 10, 2, 1)]}},
            {"name": "AppOld",  # disappears next snapshot
             "git_summary": {"is_git": True, "latest_hash": "o1"},
             "doc_census": {"docs": []}},
        ])
        one = estate_diff.diff_history(history)
        if one.get("status") != "insufficient_history" or one["snapshots_available"] != 1:
            v.append(f"estate_diff: a single snapshot should still be insufficient, got {one.get('status')!r}")

        # ---- second snapshot: exercise every delta ----
        _write(history, "2026-07-16", [
            {"name": "AppA",
             "git_summary": {"is_git": True, "latest_hash": "h3"},
             "git_deep_history": {"commits": [
                 {"hash": "h1", "date": "2026-07-14", "subject": "c1"},
                 {"hash": "h2", "date": "2026-07-15", "subject": "c2"},
                 {"hash": "h3", "date": "2026-07-16", "subject": "c3"}]},
             "doc_census": {"docs": [_doc("docs/a.md", 120, 25, 3),   # changed
                                     _doc("docs/new.md", 30, 6, 1),    # added
                                     _doc("wiki_shards/s1.md", 40, 8, 1)]}},  # added shard
            {"name": "AppUnchanged",  # identical -> must NOT appear in changed
             "git_summary": {"is_git": True, "latest_hash": "u1"},
             "doc_census": {"docs": [_doc("README.md", 10, 2, 1)]}},
            {"name": "AppNew",  # appears
             "git_summary": {"is_git": True, "latest_hash": "n1"},
             "doc_census": {"docs": []}},
        ])
        out = estate_diff.diff_history(history)
        if out.get("status") != "ok":
            return v + [f"estate_diff: expected ok, got {out.get('status')!r}"]
        if out["from_snapshot"] != "estate-2026-07-15.json" or out["to_snapshot"] != "estate-2026-07-16.json":
            v.append(f"estate_diff: wrong snapshot pair {out['from_snapshot']}->{out['to_snapshot']}")

        if out["projects_added"] != ["AppNew"]:
            v.append(f"estate_diff: projects_added wrong {out['projects_added']}")
        if out["projects_removed"] != ["AppOld"]:
            v.append(f"estate_diff: projects_removed wrong {out['projects_removed']}")

        changed = {c["project"]: c for c in out["changed"]}
        if "AppUnchanged" in changed:
            v.append("estate_diff: an unchanged project must not appear in changed[]")
        if "AppA" not in changed:
            return v + ["estate_diff: AppA should be in changed[]"]
        a = changed["AppA"]

        # Only the NEW commits (h2, h3) are enumerated -- h1 was already known.
        git = a.get("git") or {}
        if git.get("from_head") != "h1" or git.get("to_head") != "h3":
            v.append(f"estate_diff: moved-HEAD endpoints wrong {git.get('from_head')}->{git.get('to_head')}")
        if git.get("new_commit_count") != 2:
            v.append(f"estate_diff: should enumerate exactly the 2 new commits, got {git.get('new_commit_count')}")
        if [c["subject"] for c in git.get("new_commits", [])] != ["c2", "c3"]:
            v.append(f"estate_diff: new commit subjects wrong {[c.get('subject') for c in git.get('new_commits', [])]}")
        if "h1" in {c["hash"] for c in git.get("new_commits", [])}:
            v.append("estate_diff: a previously-seen commit must not be re-listed as new")

        docs = a.get("docs") or {}
        if docs.get("added") != ["docs/new.md", "wiki_shards/s1.md"]:
            v.append(f"estate_diff: doc added set wrong {docs.get('added')}")
        if docs.get("removed") != ["docs/gone.md"]:
            v.append(f"estate_diff: doc removed set wrong {docs.get('removed')}")
        if docs.get("changed") != ["docs/a.md"]:
            v.append(f"estate_diff: doc changed set wrong {docs.get('changed')}")

        # wiki_shards surfaced in their OWN channel, separate from the doc list.
        shard = {w["project"]: w for w in out["wiki_shard_changes"]}
        if "AppA" not in shard:
            v.append("estate_diff: AppA wiki shard change should be surfaced separately")
        else:
            if shard["AppA"].get("added") != ["wiki_shards/s1.md"]:
                v.append(f"estate_diff: wiki shard added wrong {shard['AppA'].get('added')}")
            if shard["AppA"].get("removed") or shard["AppA"].get("changed"):
                v.append("estate_diff: non-shard doc deltas leaked into the shard channel")

        if out["summary"]["new_commits"] != 2:
            v.append(f"estate_diff: summary new_commits wrong {out['summary']['new_commits']}")
        if out["summary"]["projects_added"] != 1 or out["summary"]["projects_removed"] != 1:
            v.append(f"estate_diff: summary add/remove counts wrong {out['summary']}")

        # ---- a project that stops being a git repo yields no git delta ----
        with tempfile.TemporaryDirectory() as td2:
            h2 = Path(td2) / "history"
            h2.mkdir()
            _write(h2, "2026-07-15", [
                {"name": "P", "git_summary": {"is_git": True, "latest_hash": "x1"},
                 "doc_census": {"docs": [_doc("d.md", 1, 1, 0)]}}])
            _write(h2, "2026-07-16", [
                {"name": "P", "git_summary": {"is_git": False},
                 "doc_census": {"docs": [_doc("d.md", 1, 1, 0)]}}])
            o = estate_diff.diff_history(h2)
            # no git move (not a repo) and no doc change -> P should not be "changed".
            if any(c["project"] == "P" and "git" in c for c in o.get("changed", [])):
                v.append("estate_diff: a project that is no longer a git repo should not report a git delta")
    return v
