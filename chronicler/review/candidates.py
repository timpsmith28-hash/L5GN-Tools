"""candidates.py -- the adapter COWORK_REPORT_conductor_governor.md's Task
4' report flagged as not built: turns real Curator data (the ratified map,
K1's `knowledge_index.json`, K2's `claims.json` and its cache) plus the
calibration ledger (Task 2) into `planner.ProjectCandidate` objects.

**Every field here is either a real count from disk, or `None`.** Nothing
is guessed to fill a gap -- a project's `estimated_seconds` stays `None`
unless BOTH a calibration measurement AND the real conversation text
needed to size the work are available; `build_plan` already refuses a
budgeted plan built from candidates carrying `None`, which is the correct
behaviour here, not a defect to work around.

**Breadth is proxied by conversation count, not message count.**
`knowledge_index.json` records which conversations belong to a project,
not how large each one is -- getting real message counts would mean
re-parsing every transcript, duplicating work K0/K2 already do elsewhere.
Conversation count is a real, honest number; it is a coarser breadth
signal than raw messages, and this module says so rather than pretending
otherwise.

Lives in the app tier (needs nothing from `chronicler.review` itself, but
sits beside `conductor_panel.py`/`planner.py` as the third piece of the
same layer, and a future route would call it the same way).
"""
from __future__ import annotations

from collections import defaultdict

from chronicler.pipeline import extract_claims as k2
from chronicler.pipeline import ledger as led

from . import planner as pl


def candidates_from_curator(*, map_rows: list, claims_report: dict | None,
                             knowledge_index: dict | None, k2_cache: dict | None = None,
                             conversations: list | None = None,
                             ledger_entries: list | None = None,
                             model_id: str | None = None, stage: str = "K2") -> list[pl.ProjectCandidate]:
    """Build one `ProjectCandidate` per project named in `map_rows` (the
    ratified join surface -- the same universe K2/K4 themselves scope
    against).

    ``map_rows`` is ``curator_data.ratified_map_rows()``'s own shape --
    plain dicts with (at least) ``session_id``/``project_id`` keys, the
    same TSV-row dicts K0/K1/every other reader of the ratified map
    already uses. Not objects, not a bespoke row type.

    ``claims_report`` / ``knowledge_index`` are the parsed JSON bodies of
    `claims.json` / `knowledge_index.json` (either may be `None` -- that
    stage simply hasn't run yet, and the fields it would have fed default
    to 0, never guessed).

    ``k2_cache`` + ``conversations`` (the REAL `local_transcripts.
    Conversation` objects, e.g. from `bootstrap_conversation_map.
    discover_conversations`) are both required together to compute
    ``changed_conversations`` and ``estimated_seconds`` -- omit either and
    both stay at their honest defaults (0 and `None` respectively) rather
    than a partial, misleading computation.

    ``ledger_entries`` + ``model_id`` are both required to produce
    ``estimated_seconds`` at all -- no calibration data for the selected
    model means every candidate's estimate stays `None`, exactly `ledger.
    summarize`'s own "no measurements, no estimate" rule."""
    session_to_project = {row["session_id"]: row["project_id"] for row in map_rows}
    project_ids = sorted({row["project_id"] for row in map_rows})

    # --- claim_count: claims.json's conversations, summed per project via
    #     the ratified session->project join (the SAME join K4 uses) -------
    claim_counts: dict[str, int] = defaultdict(int)
    if claims_report:
        for conv_entry in claims_report.get("conversations", []):
            proj = session_to_project.get(conv_entry.get("conversation_id"))
            if proj:
                claim_counts[proj] += len(conv_entry.get("claims", []))

    # --- breadth proxy: conversation count. knowledge_index.json first (it
    #     already resolved project membership); falls back to map_rows
    #     directly if K1 hasn't run yet -- never zero just because K1 is
    #     behind ------------------------------------------------------------
    conv_counts: dict[str, int] = defaultdict(int)
    if knowledge_index:
        for proj in knowledge_index.get("projects", []):
            conv_counts[proj["project_id"]] = len(proj.get("conversations", []))
    else:
        for row in map_rows:
            conv_counts[row["project_id"]] += 1

    # --- changed_conversations + estimated_seconds: need REAL conversation
    #     objects, since sizing the work requires the actual transcript
    #     text, and knowing what changed requires K2's own cache-identity
    #     check (reused directly, not reimplemented) ------------------------
    changed_counts: dict[str, int] = defaultdict(int)
    pending_tokens: dict[str, int] = defaultdict(int)  # tokens of conversations NOT yet cached
    if conversations is not None and k2_cache is not None:
        for conv in conversations:
            proj = session_to_project.get(conv.conversation_id)
            if not proj:
                continue
            sources = k2.source_identity(conv)
            cached = k2_cache.get(conv.conversation_id)
            is_changed = cached is None or cached.get("sources") != sources
            if is_changed:
                changed_counts[proj] += 1
                pending_tokens[proj] += k2.approx_token_count(k2.full_transcript_text(conv))

    calibration: led.CalibrationSummary | None = None
    if ledger_entries is not None and model_id is not None:
        calibration = led.summarize(ledger_entries, model_id=model_id, stage=stage,
                                     cool_down_preceded=False)

    candidates: list[pl.ProjectCandidate] = []
    for project_id in project_ids:
        estimated_seconds = None
        if calibration is not None and project_id in pending_tokens:
            # ms/token * tokens / 1000 = seconds, over exactly the work this
            # project would ACTUALLY cost (the changed conversations only --
            # an unchanged one is a cache hit, K2/K4 never re-call the model
            # for it, so it costs nothing to include in a re-run).
            estimated_seconds = (calibration.median_ms_per_token
                                  * pending_tokens[project_id] / 1000.0)
        candidates.append(pl.ProjectCandidate(
            project_id=project_id,
            claim_count=claim_counts.get(project_id, 0),
            changed_conversations=changed_counts.get(project_id, 0),
            message_count=conv_counts.get(project_id, 0),
            estimated_seconds=estimated_seconds,
        ))
    return candidates
