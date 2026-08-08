"""curator_findings.py -- Task 4, COWORK_BRIEF_curator_tab.md.

Renders K5's five sections (gaps, no-knowledge-file-yet, cross-project,
superseded, captured) from K2/K4's own JSON output, in K5's own emission
order -- **nothing here recomputes a finding**. Grouping-by-outcome is the
one-line dict-bucket `compile_report.py` itself does before building its
markdown sections; the "no knowledge file yet" clustering is literally
`compile_report.cluster_claims`, imported and called, never re-implemented.

Also Task 4's drill-through: an opaque `conversation_id` resolved against an
in-memory conversation map (built the same read-only way K0/K1 build it),
containment-checked against a **newly declared allowlisted transcript-store
root** using the SAME `resolve_contained` gate `estate_data.py` and
`docs_board.py` already use -- this module adds an anchor, not a second
resolver.

Nothing in this module writes, with the one narrow exception the brief
explicitly names and then tells the builder to skip if in doubt: the
superseded-ordering-flag. **This build skips it** -- see
`flag_superseded_ordering` below for the reasoning, recorded inline and
repeated in the COWORK_REPORT.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .estate_data import DocumentRefused, resolve_contained

_PIPE = Path(__file__).resolve().parents[2] / "chronicler" / "pipeline"
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))

MAX_TRANSCRIPT_MESSAGES = 20     # a bounded window, never the whole transcript
MAX_TRANSCRIPT_FILE_BYTES = 2 * 1024 * 1024


def _compile_report():
    import compile_report as k5  # noqa: local import, optional heavy deps
    return k5


# ---------------------------------------------------------------------------
# Run health -- always above the findings
# ---------------------------------------------------------------------------

def run_health(claims_report: dict | None, matches_report: dict | None,
               knowledge_index: dict | None) -> dict:
    """The caveats a thin run must not let the findings below outrank.
    Every field here is a direct read of something K1/K2 already recorded --
    no filtering, no scoring, no judgement."""
    claims_report = claims_report or {}
    matches_report = matches_report or {}
    knowledge_index = knowledge_index or {}
    projects = knowledge_index.get("projects", [])
    no_kf_projects = [p["project_id"] for p in projects if not p.get("knowledge_files")]
    return {
        "excluded_no_timestamp": list(
            claims_report.get("conversations_excluded_no_timestamp", [])),
        "excluded_no_timestamp_count": len(
            claims_report.get("conversations_excluded_no_timestamp", [])),
        "unmapped_folders": list(knowledge_index.get("present_not_mapped", [])),
        "unmapped_folders_count": len(knowledge_index.get("present_not_mapped", [])),
        "projects_no_knowledge_file": no_kf_projects,
        "projects_no_knowledge_file_count": len(no_kf_projects),
        "quote_rejection_rate": claims_report.get("quote_rejection_rate"),
        "claims_rejected": claims_report.get("claims_rejected"),
        "claims_extracted": claims_report.get("claims_extracted"),
        "conversations_scanned": claims_report.get("conversations_scanned"),
        "model_id": matches_report.get("model_id") or claims_report.get("model_id"),
        "run_timestamp": matches_report.get("run_timestamp") or claims_report.get("run_timestamp"),
    }


# ---------------------------------------------------------------------------
# The five sections, K5's own emission order, K5's own grouping
# ---------------------------------------------------------------------------

def claims_by_outcome(matches_report: dict | None) -> dict[str, list[dict]]:
    """The exact one-line bucket compile_report.compile_report() builds
    before rendering markdown -- reproduced verbatim (not re-derived: K4's
    `outcome` field is read as-is) so the JSON view and the markdown report
    are guaranteed to bucket identically."""
    out: dict[str, list[dict]] = {}
    for c in (matches_report or {}).get("claims", []):
        out.setdefault(c["outcome"], []).append(c)
    return out


def gaps_by_project(by_outcome: dict, knowledge_index: dict | None) -> dict:
    """Per project, never totalled -- a project with no knowledge file shows
    NO entry at all (not zero), matching K5's own `has_kf` filter exactly."""
    knowledge_index = knowledge_index or {}
    has_kf = {p["project_id"] for p in knowledge_index.get("projects", [])
              if p.get("knowledge_files")}
    gaps = [c for c in by_outcome.get("gap", []) if c["project_id"] in has_kf]
    out: dict[str, list[dict]] = {}
    for c in gaps:
        out.setdefault(c["project_id"], []).append(c)
    return out


def no_knowledge_file_starters(by_outcome: dict, knowledge_index: dict | None) -> dict:
    """K5's own `cluster_claims`, called -- not re-implemented -- per project
    that has no knowledge file at all."""
    k5 = _compile_report()
    knowledge_index = knowledge_index or {}
    no_kf_projects = [p["project_id"] for p in knowledge_index.get("projects", [])
                       if not p.get("knowledge_files")]
    all_claims = [c for claims in by_outcome.values() for c in claims]
    out: dict[str, list[dict]] = {}
    for pid in no_kf_projects:
        proj_claims = [c for c in all_claims if c["project_id"] == pid]
        out[pid] = (k5.cluster_claims(proj_claims)[:k5.RECURRENCE_TOP_N]
                    if proj_claims else [])
    return out


def cross_project(by_outcome: dict) -> list[dict]:
    return list(by_outcome.get("cross-project", []))


def superseded(by_outcome: dict) -> list[dict]:
    """Two dated quoted blocks per entry, current above superseded, interval
    stated -- presentational only (a date subtraction), never a judgement of
    which claim is better reasoned. K4 already recorded both halves
    (`quoted_source` and `supersedes.newer_*`); this only pairs them for
    display."""
    from datetime import datetime
    out = []
    for c in by_outcome.get("superseded", []):
        newer = c.get("supersedes") or {}
        interval_days = None
        try:
            older_dt = datetime.fromisoformat((c.get("real_time") or "")[:19])
            newer_dt = datetime.fromisoformat((newer.get("newer_real_time") or "")[:19])
            interval_days = (newer_dt - older_dt).days
        except ValueError:
            pass
        out.append({
            "project_id": c["project_id"],
            "superseded": {"claim_text": c["claim_text"], "quoted_source": c["quoted_source"],
                            "real_time": c.get("real_time"), "conversation_id": c["conversation_id"]},
            "current": {"claim_text": newer.get("newer_claim_text"),
                        "quoted_source": newer.get("newer_quoted_source"),
                        "real_time": newer.get("newer_real_time"),
                        "conversation_id": newer.get("newer_conversation_id")},
            "interval_days": interval_days,
            "note": ("Ordering picked the newer statement as current. This has "
                     "NOT judged which claim is better reasoned -- recency is "
                     "the whole rule (DECISIONS 0032)."),
        })
    return out


def captured(by_outcome: dict, sample_n: int | None = None) -> dict:
    k5 = _compile_report()
    n = sample_n if sample_n is not None else k5.CAPTURED_SAMPLE_N
    items = by_outcome.get("captured", [])
    out: dict[str, dict] = {}
    by_project: dict[str, list] = {}
    for c in items:
        by_project.setdefault(c["project_id"], []).append(c)
    for pid, claims in by_project.items():
        out[pid] = {"count": len(claims), "sample": claims[:n],
                    "more": max(0, len(claims) - n)}
    return out


def flag_superseded_ordering(*args, **kwargs):
    """**Deliberately not implemented in this round.**

    The brief allows a narrow write here ("flag ordering as wrong") but its
    own stop-condition list is stricter than its task text, and says: if in
    doubt, treat Task 4 as fully read-only and skip the affordance, noting
    the deviation. This build is in doubt -- the flag would be a THIRD write
    path in a brief that names exactly two (staging the map, invoking a
    stage) as the whole of what this round is allowed to touch, and
    "triage state across runs" is explicitly out of scope in the very next
    paragraph. A structured "this ordering looks wrong" flag is one honest
    reading away from becoming exactly that triage state. Skipped; recorded
    in COWORK_REPORT_curator_tab.md, not silently dropped.
    """
    raise NotImplementedError(
        "not built this round -- see this function's docstring and "
        "COWORK_REPORT_curator_tab.md's Task 4 section.")


# ---------------------------------------------------------------------------
# Drill-through -- opaque id, in-memory map, the ONE containment resolver
# ---------------------------------------------------------------------------

def transcript_store_roots(host: str | None = None) -> list[Path]:
    """The Cowork local transcript store, declared as an allowlisted read
    root for THIS module only (Obstacle 2). Reads the same config key K0/K1
    already read (`cowork_transcripts_home`) -- no new config surface, no
    guessed path."""
    from l5gntools.config import machine
    cfg = machine(host)
    root = cfg.get("cowork_transcripts_home")
    return [Path(root)] if root else []


def build_conversation_map(host: str | None = None):
    """The in-memory map a drill-through identifier resolves against --
    K0's own `discover_conversations`, called read-only. Never a second
    discoverer."""
    import bootstrap_conversation_map as k0
    conversations, access_errors = k0.discover_conversations(host)
    return {c.conversation_id: c for c in conversations}, access_errors


def _session_files(conv) -> list[Path]:
    return [s.path for s in conv.sessions]


def read_transcript_window(conversation_id: str, conversations_by_id: dict,
                            host: str | None = None,
                            max_messages: int = MAX_TRANSCRIPT_MESSAGES,
                            roots: list[Path] | None = None) -> dict:
    """A bounded window of one conversation's transcript, never the whole
    thing. **Check one**: the id must resolve in the in-memory map (built
    from real discovery, so a crafted id that names no real conversation
    resolves to nothing -- the same shape as `estate_data.document_id`).
    **Check two**: every resolved file path is re-verified inside
    :func:`transcript_store_roots` via the SAME `resolve_contained` gate
    `estate_data.py` defines -- not a second implementation of it.
    """
    conv = conversations_by_id.get(conversation_id)
    if conv is None:
        raise DocumentRefused(
            "unknown_conversation",
            "No conversation with that identifier is in this machine's "
            "discovered store. The drill-through addresses a conversation by "
            "an id resolved against the live discovery, never by a path.")

    # `roots` is a testability override ONLY -- app.py's route never passes
    # one, so production always resolves the real configured store
    # (transcript_store_roots). A tester supplies a temp-dir root so
    # containment is proven without touching real machine config.
    if roots is None:
        roots = transcript_store_roots(host)
    files = _session_files(conv)
    if not files:
        raise DocumentRefused("no_files", "This conversation has no transcript files recorded.")

    # Earliest file first (matches local_transcripts.earliest_session's
    # ordering intent): the window is the conversation's opening, not an
    # arbitrary file.
    path = sorted(files, key=lambda p: str(p))[0]
    resolved = resolve_contained(
        path, roots, outside_reason="outside_transcript_store",
        no_anchor_reason="no_transcript_store_configured",
        boundary="this machine's configured transcript store",
        no_anchor_detail="No cowork_transcripts_home configured for this "
                         "machine -- there is no allowlisted root to read a "
                         "transcript from.")

    if not resolved.is_file():
        raise DocumentRefused("not_a_file", "That transcript file is not readable now.")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise DocumentRefused("unreadable", f"Could not stat that transcript: {exc}")
    if size > MAX_TRANSCRIPT_FILE_BYTES:
        raise DocumentRefused(
            "oversized",
            f"That transcript file is {size} bytes, over the "
            f"{MAX_TRANSCRIPT_FILE_BYTES}-byte cap for a drill-through read. "
            "Refused rather than hung.")
    try:
        text = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise DocumentRefused("binary", "That transcript file is not valid UTF-8 text.")
    except OSError as exc:
        raise DocumentRefused("unreadable", f"Could not read that transcript: {exc}")

    import json as _json
    lines = text.splitlines()[:max_messages * 4]  # generous cap before JSON parse
    messages: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = _json.loads(line)
        except ValueError:
            continue
        messages.append(rec)
        if len(messages) >= max_messages:
            break

    return {
        "conversation_id": conversation_id, "file": str(resolved),
        "real_time": conv.real_time, "real_time_source": conv.real_time_source,
        "message_window": messages, "windowed": len(lines) < text.count("\n") + 1
        if lines else False,
        "truncated_to": max_messages,
    }
