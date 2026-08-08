"""tester_curator_findings: Task 4's findings rendering and, load-bearingly,
containment against TRANSCRIPT paths -- not just markdown/estate-root paths.

The brief calls this out explicitly: existing containment testers
(tester_estate_data, tester_docs_board) only ever exercised the estate-root
and repo-root anchors. This module adds a THIRD anchor (the Cowork
transcript store, Obstacle 2), reusing `estate_data.resolve_contained` --
and reusing it is exactly what this tester has to prove, by exercising the
same two failure shapes those testers already cover, against this new
anchor: a resolved path outside the root, and a traversal attempt through
the identifier.

Findings-rendering coverage is against fixtures only (K2/K4/K1 shapes
handmade to match the real schemas read in extract_claims.py/
match_claims.py/knowledge_index.py) -- never against real pipeline output,
which does not exist in this sandbox (see COWORK_REPORT_curator_tab.md).
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from chronicler.review import curator_findings as cf
from chronicler.review.estate_data import DocumentRefused


# ---------------------------------------------------------------------------
# Minimal duck-typed stand-ins for local_transcripts.Conversation/ParsedSession
# -- only the attributes read_transcript_window/unmapped_local_folders touch.
# ---------------------------------------------------------------------------

@dataclass
class _FakeSession:
    path: Path
    messages: list = field(default_factory=list)


@dataclass
class _FakeConversation:
    conversation_id: str
    sessions: list
    real_time: str | None = "2026-08-01T00:00:00Z"
    real_time_source: str | None = "last_message_timestamp"
    cowork_project_dir: str | None = "Foo"


def run() -> list[str]:
    v: list[str] = []

    # --- claims_by_outcome: the exact one-line bucket, nothing recomputed --
    matches = {"claims": [
        {"outcome": "gap", "project_id": "Foo", "claim_text": "a", "quoted_source": "q",
         "conversation_id": "c1", "real_time": "2026-08-01T00:00:00Z"},
        {"outcome": "captured", "project_id": "Foo", "claim_text": "b", "quoted_source": "q2",
         "conversation_id": "c2", "real_time": "2026-08-01T00:00:00Z"},
    ]}
    by_outcome = cf.claims_by_outcome(matches)
    if len(by_outcome.get("gap", [])) != 1 or len(by_outcome.get("captured", [])) != 1:
        v.append(f"curator_findings: claims_by_outcome bucketed wrong: {by_outcome}")

    # --- gaps: per project, omitted (not zero) for a project with no KF ----
    knowledge_index = {"projects": [
        {"project_id": "Foo", "knowledge_files": ["KNOWLEDGE.md"]},
        {"project_id": "Bar", "knowledge_files": []},
    ]}
    by_outcome2 = {"gap": [
        {"project_id": "Foo", "claim_text": "g1", "quoted_source": "q", "conversation_id": "c1",
         "real_time": "2026-08-01T00:00:00Z"},
        {"project_id": "Bar", "claim_text": "g2", "quoted_source": "q", "conversation_id": "c2",
         "real_time": "2026-08-01T00:00:00Z"},
    ]}
    gaps = cf.gaps_by_project(by_outcome2, knowledge_index)
    if "Bar" in gaps:
        v.append("curator_findings: a project with no knowledge file must be "
                 "OMITTED from gaps, not shown as zero")
    if "Foo" not in gaps or len(gaps["Foo"]) != 1:
        v.append(f"curator_findings: Foo's gap wrongly dropped or miscounted: {gaps}")

    # --- run_health always reads even when everything is missing -----------
    health = cf.run_health(None, None, None)
    if health["excluded_no_timestamp_count"] != 0 or health["unmapped_folders_count"] != 0:
        v.append("curator_findings: run_health must degrade to zeroes, not raise, "
                 "when nothing is on disk")

    # --- superseded: two dated quoted blocks, interval, never a judgement --
    by_outcome3 = {"superseded": [{
        "project_id": "Foo", "claim_text": "old claim", "quoted_source": "old quote",
        "conversation_id": "c1", "real_time": "2026-06-01T00:00:00",
        "supersedes": {"newer_claim_text": "new claim", "newer_quoted_source": "new quote",
                       "newer_conversation_id": "c9", "newer_real_time": "2026-08-01T00:00:00"},
    }]}
    sup = cf.superseded(by_outcome3)
    if len(sup) != 1 or sup[0]["interval_days"] != 61:
        v.append(f"curator_findings: superseded interval wrong: {sup}")
    if "not judged" not in sup[0]["note"] and "NOT judged" not in sup[0]["note"]:
        v.append("curator_findings: superseded card must explicitly say "
                 "ordering has not judged which claim is better reasoned")

    # --- the superseded-ordering-flag write is deliberately NOT built -------
    try:
        cf.flag_superseded_ordering()
        v.append("curator_findings: flag_superseded_ordering must not be "
                 "silently implemented -- this round treats Task 4 read-only")
    except NotImplementedError:
        pass

    # ======================================================================
    # Containment against TRANSCRIPT paths -- the tester the brief calls out
    # by name as likely missing from the existing suite.
    # ======================================================================
    with tempfile.TemporaryDirectory() as tmp:
        store_root = Path(tmp) / "cowork_store"
        conv_dir = store_root / "proj" / "local_abc123"
        conv_dir.mkdir(parents=True)
        transcript = conv_dir / "session.jsonl"
        transcript.write_text('{"role": "user", "content": "hello"}\n', encoding="utf-8")

        conv = _FakeConversation(conversation_id="local_abc123",
                                 sessions=[_FakeSession(path=transcript)])
        conversations_by_id = {"local_abc123": conv}

        # --- the happy path: inside the declared root, resolves and reads --
        result = cf.read_transcript_window("local_abc123", conversations_by_id,
                                           roots=[store_root])
        if result["conversation_id"] != "local_abc123":
            v.append("curator_findings: a legitimate transcript read failed unexpectedly")

        # --- traversal attempt THROUGH THE IDENTIFIER ------------------------
        # There is no path parameter to attack -- the only caller-supplied
        # value is the identifier string. A crafted one that names no real
        # conversation in the in-memory map must resolve to nothing, exactly
        # like estate_data.document_id's unknown-id case.
        try:
            cf.read_transcript_window("../../../../etc/passwd", conversations_by_id,
                                      roots=[store_root])
            v.append("curator_findings: a traversal-shaped identifier must be "
                     "refused, not resolved -- it names no real conversation")
        except DocumentRefused as exc:
            if exc.reason != "unknown_conversation":
                v.append(f"curator_findings: wrong refusal reason for a bad "
                         f"identifier: {exc.reason}")

        # --- a resolved path OUTSIDE the declared transcript-store root -----
        # A conversation whose (fake, injected) file genuinely lives outside
        # the allowlisted root -- e.g. a symlink or a misrecorded path. Check
        # two must catch what check one let through.
        outside_dir = Path(tmp) / "not_the_store"
        outside_dir.mkdir()
        outside_file = outside_dir / "session.jsonl"
        outside_file.write_text('{"role": "user", "content": "hi"}\n', encoding="utf-8")
        evil_conv = _FakeConversation(conversation_id="local_evil",
                                      sessions=[_FakeSession(path=outside_file)])
        evil_map = {"local_evil": evil_conv}
        try:
            cf.read_transcript_window("local_evil", evil_map, roots=[store_root])
            v.append("curator_findings: a path resolving OUTSIDE the transcript "
                     "store root must be refused")
        except DocumentRefused as exc:
            if exc.reason != "outside_transcript_store":
                v.append(f"curator_findings: wrong refusal reason for an "
                         f"outside-root path: {exc.reason}")

        # --- no anchor configured refuses, never passes everything ----------
        try:
            cf.read_transcript_window("local_abc123", conversations_by_id, roots=[])
            v.append("curator_findings: an empty anchor set must refuse, not "
                     "read everything")
        except DocumentRefused as exc:
            if exc.reason != "no_transcript_store_configured":
                v.append(f"curator_findings: wrong refusal reason for no "
                         f"configured store: {exc.reason}")

        # --- bounded window: never the whole transcript ----------------------
        many_lines = "\n".join(
            f'{{"role": "user", "content": "msg {i}"}}' for i in range(50)) + "\n"
        transcript.write_text(many_lines, encoding="utf-8")
        windowed = cf.read_transcript_window("local_abc123", conversations_by_id,
                                             roots=[store_root], max_messages=5)
        if len(windowed["message_window"]) > 5:
            v.append("curator_findings: the transcript window must be bounded, "
                     "not the whole transcript")

        # --- honest refusal: missing file -------------------------------------
        missing_conv = _FakeConversation(conversation_id="local_missing",
                                         sessions=[_FakeSession(path=conv_dir / "gone.jsonl")])
        try:
            cf.read_transcript_window("local_missing", {"local_missing": missing_conv},
                                      roots=[store_root])
            v.append("curator_findings: a missing transcript file must be refused honestly")
        except DocumentRefused as exc:
            if exc.reason != "not_a_file":
                v.append(f"curator_findings: wrong refusal for a missing file: {exc.reason}")

        # --- honest refusal: oversized file -----------------------------------
        big_conv_dir = store_root / "proj" / "local_big"
        big_conv_dir.mkdir(parents=True)
        big_file = big_conv_dir / "session.jsonl"
        big_file.write_bytes(b"x" * (cf.MAX_TRANSCRIPT_FILE_BYTES + 1))
        big_conv = _FakeConversation(conversation_id="local_big", sessions=[_FakeSession(path=big_file)])
        try:
            cf.read_transcript_window("local_big", {"local_big": big_conv}, roots=[store_root])
            v.append("curator_findings: an oversized transcript must be refused")
        except DocumentRefused as exc:
            if exc.reason != "oversized":
                v.append(f"curator_findings: wrong refusal for an oversized file: {exc.reason}")

        # --- honest refusal: binary file --------------------------------------
        bin_conv_dir = store_root / "proj" / "local_bin"
        bin_conv_dir.mkdir(parents=True)
        bin_file = bin_conv_dir / "session.jsonl"
        bin_file.write_bytes(b"\xff\xfe\x00\x01not valid utf-8 \x80\x81")
        bin_conv = _FakeConversation(conversation_id="local_bin", sessions=[_FakeSession(path=bin_file)])
        try:
            cf.read_transcript_window("local_bin", {"local_bin": bin_conv}, roots=[store_root])
            v.append("curator_findings: a non-UTF-8 transcript must be refused as binary")
        except DocumentRefused as exc:
            if exc.reason != "binary":
                v.append(f"curator_findings: wrong refusal for a binary file: {exc.reason}")

    return v
