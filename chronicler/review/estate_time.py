"""The time dimension of the estate (brief, Task 4).

Every figure here is already on disk in ``estate.json`` -- ``git_summary`` for
the span, ``git_deep_history`` for the per-author and per-day tallies -- and
the report has never rendered any of it. This module joins it into three views:
a per-project span, an estate-wide timeline on one shared axis, and the delta
against the previous build.

**Absence is reported, never interpolated.** Four folders on the work estate and
two on the personal have no git history at all, and a project with no history
returns ``has_history: False`` with the reason. It does not get a span invented
from file mtimes. That rule is written in blood: ``build_activity``'s
``Path("")`` defect produced a plausible activity window for a directory it had
never actually looked at, and a fabricated window is worse than an absent one
because nobody audits a number that looks reasonable.

Read-only, stdlib-only. The build delta reuses
:func:`l5gntools.scanners.estate_diff.diff_history` rather than growing a second
diff -- it is already the tested answer to "what changed", and two diffs that
disagree would be worse than either alone.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from l5gntools import config
from l5gntools.common import DATA_DIR
from l5gntools.scanners import estate_diff

from .estate_data import parse_timestamp


def _canonical_author(name: str, aliases: dict) -> str:
    """Fold a git author string to its canonical identity via
    ``config/authors.json``. An unmapped name is returned unchanged -- an
    unrecognised contributor is a real contributor, not an error."""
    if not name:
        return "(unknown)"
    return aliases.get(str(name).lower(), name)


def _contributors(project: dict, aliases: dict) -> list[dict]:
    """Per-author commit counts, folded through the alias map.

    ``git_deep_history.commits_by_author`` is already aliased by the scanner;
    folding again is idempotent and covers the case where the snapshot predates
    an alias being added to ``authors.json``.
    """
    deep = project.get("git_deep_history") or {}
    tally: dict[str, int] = {}
    by_author = deep.get("commits_by_author") or {}
    if isinstance(by_author, dict):
        for name, count in by_author.items():
            canonical = _canonical_author(name, aliases)
            tally[canonical] = tally.get(canonical, 0) + int(count or 0)
    if not tally:
        # No deep history: the summary still names the most recent author. One
        # known contributor with an unknown count is stated as exactly that.
        summary = project.get("git_summary") or {}
        latest = summary.get("latest_author")
        if latest:
            return [{"author": _canonical_author(latest, aliases), "commits": None,
                     "note": "latest commit only -- no deep history in this build"}]
        return []
    return [{"author": a, "commits": c}
            for a, c in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0].lower()))]


def project_span(project: dict, aliases: dict | None = None) -> dict:
    """One project's place in time, or an honest statement that it has none."""
    aliases = aliases if aliases is not None else config.author_aliases()
    name = project.get("name") or ""
    summary = project.get("git_summary") or {}
    deep = project.get("git_deep_history") or {}
    base = {"project": name, "is_git": bool(summary.get("is_git"))}

    if not summary.get("is_git"):
        return {**base, "has_history": False,
                "reason": "not a git repository -- no commit history to read"}

    first = parse_timestamp(summary.get("first_commit_date"))
    last = parse_timestamp(summary.get("latest_date"))
    if first is None or last is None:
        return {**base, "has_history": False,
                "reason": "a git repository with no readable commit dates "
                          "(empty repo, or an unborn branch)"}

    span_days = max(0.0, (last - first).total_seconds() / 86400.0)
    return {
        **base,
        "has_history": True,
        "branch": summary.get("branch"),
        "first_commit": summary.get("first_commit_date"),
        "last_commit": summary.get("latest_date"),
        "first_commit_epoch": first.timestamp(),
        "last_commit_epoch": last.timestamp(),
        "span_days": round(span_days, 2),
        "commit_count": summary.get("commit_count"),
        "deep_commit_count": deep.get("total_commits"),
        "deep_truncated": bool(deep.get("truncated")),
        "latest_hash": summary.get("latest_hash"),
        "latest_subject": summary.get("latest_subject"),
        "dirty_files": summary.get("dirty_files"),
        "contributors": _contributors(project, aliases),
        "commits_by_day": deep.get("commits_by_day") or {},
    }


def estate_timeline(snapshot: dict) -> dict:
    """Every project on one shared axis, so the lineage is visible.

    ``offset`` and ``width`` are fractions of the estate's whole span, computed
    here rather than in the browser: the axis is the claim being made, and a
    claim the tester can check should not live in a ``<script>`` tag.

    Projects with no history are returned in ``without_history`` -- listed, not
    hidden, and with no position on the axis.
    """
    aliases = config.author_aliases()
    spans, absent = [], []
    for project in snapshot.get("projects", []):
        if not isinstance(project, dict):
            continue
        span = project_span(project, aliases)
        (spans if span["has_history"] else absent).append(span)

    if not spans:
        return {"has_axis": False, "projects": [], "without_history": absent,
                "note": "No project in this build has readable git history."}

    axis_start = min(s["first_commit_epoch"] for s in spans)
    axis_end = max(s["last_commit_epoch"] for s in spans)
    total = axis_end - axis_start

    for span in spans:
        if total > 0:
            span["offset"] = (span["first_commit_epoch"] - axis_start) / total
            span["width"] = (span["last_commit_epoch"] - span["first_commit_epoch"]) / total
        else:
            # Every commit at the same instant: one point, not a bar. Saying
            # width 1.0 here would draw a full-width span for a single moment.
            span["offset"], span["width"] = 0.0, 0.0

    spans.sort(key=lambda s: (s["first_commit_epoch"], s["project"].lower()))
    absent.sort(key=lambda s: s["project"].lower())
    return {
        "has_axis": True,
        "axis_start_epoch": axis_start,
        "axis_end_epoch": axis_end,
        "axis_start": datetime.fromtimestamp(axis_start, timezone.utc).isoformat(),
        "axis_end": datetime.fromtimestamp(axis_end, timezone.utc).isoformat(),
        "axis_span_days": round((axis_end - axis_start) / 86400.0, 2),
        "projects": spans,
        "without_history": absent,
    }


def _snapshot_stamp(history_dir: Path, filename: str | None) -> dict:
    """The identity of one snapshot file: its timestamp and the toolkit commit
    that produced it. The brief asks for the comparison to name both builds
    plainly, and a filename alone does not say which commit built it."""
    stamp = {"file": filename, "generated_at": None,
             "toolkit_commit": None, "toolkit_dirty": None}
    if not filename:
        return stamp
    path = Path(history_dir) / filename
    if not path.exists():
        return stamp
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return stamp
    if isinstance(data, dict):
        stamp["generated_at"] = data.get("generated_at")
        stamp["toolkit_commit"] = data.get("toolkit_commit")
        stamp["toolkit_dirty"] = data.get("toolkit_dirty")
    return stamp


def build_delta(history_dir=None) -> dict:
    """What changed since the previous build.

    Delegates the comparison to the existing ``estate_diff`` scanner and adds
    the identity of each side, so the surface can state exactly which two
    builds are on screen. When fewer than two snapshots exist the scanner
    returns ``insufficient_history`` and that is passed through unchanged --
    "not enough history to compare" is a true answer.
    """
    history = Path(history_dir) if history_dir else (DATA_DIR / "history")
    result = estate_diff.diff_history(history)
    result["from_build"] = _snapshot_stamp(history, result.get("from_snapshot"))
    result["to_build"] = _snapshot_stamp(history, result.get("to_snapshot"))
    result["history_dir"] = str(history)
    return result


# ---- the module's own routes (COWORK_BRIEF_unified_app.md, Task 1) ----------
# The Time tab is the one tab migrated onto the descriptor registry in the
# commit that lands it. Its router lives beside its logic rather than in
# `app.py`, which is the whole claim being tested: a module declares itself.
#
# The FastAPI import is INSIDE the factory on purpose. `modules.py` imports
# this file to reference the factory, `auditor_module_contract` imports
# `modules.py`, and `verify.py` must stay green on a machine with no web stack
# (DECISIONS 0034's consequence paragraph). A top-level `from fastapi import
# APIRouter` here would make the gate depend on the app tier's dependencies,
# which is precisely the coupling 0034 clause 3 exists to prevent.
#
# Note what is NOT here: no `_need_estate()`. This module declares
# `requires=("estate",)` in `modules.py` and `create_app` gates the whole
# router once from that declaration. The routes state what they return and
# nothing else.

def router(ctx):
    """Build this module's APIRouter. `ctx` is a `module_contract.AppContext`."""
    from fastapi import APIRouter

    api = APIRouter()

    @api.get("/api/estate/timeline")
    def estate_timeline_route():
        return estate_timeline(ctx.estate.snapshot)

    @api.get("/api/estate/changes")
    def estate_changes_route():
        """What moved since the previous build. Names both snapshots by
        timestamp and toolkit commit, because "what changed" is meaningless
        without saying changed *between what and what*."""
        return build_delta()

    return api
