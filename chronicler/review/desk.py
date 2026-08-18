"""desk.py -- Phase 1, COWORK_BRIEF_desk_stale_card.md: the Decision Desk's
first card type, stale-output triage.

Built on DECISIONS 0048 (D-A: the unit of throughput is a decision, not an
artifact -- a surface that wants attention raises a card, with a fixed
anatomy) and 0049 (D-B: the toolkit invokes no frontier model; not touched
here, named because both rulings share this round's origin thread). The
working rules below are this brief's, restated at the point each is enforced
so a future reader does not have to hold the whole brief in their head to
trust one function.

**Cards are derived, never stored** (`docs_board.py`'s / `project_wizard
.board()`'s discipline, carried over unchanged): :func:`cards` recomputes the
whole card set fresh from `project_wizard.load_manifests()`, `stage_freshness`
and run markers on every call. What *is* stored is events -- sightings and
rulings, in :data:`EVENTS_PATH` -- because an event is a fact about the past,
not board state. That is the one deliberate deviation from derive-never-
store in this module, and it is confined to this file (Task 2).

**The Desk executes nothing.** There is no code path from a card to
`project_wizard.execute_with_lock` in this module. "Rebuild now" is a button
in the view that calls the wizard's own `/api/project_wizard/execute` route
directly, with the wizard's own `(repo_key, stage_key)` body -- this module
never accepts a repo path or an argv (0037, 0042; a stop condition of this
brief in its own right).

**This round reads `StageSpec.depends_on` for the first time -- to ask, never
to run.** `project_wizard`'s own brief left it "recorded, never acted on";
Trigger B below reads it to raise a question. No stage is ever executed
because of it. This widening is named here and in the round's report, per
the brief's own instruction.

**No policy engine exists in this round.** Every card's default is
`hold -- nothing runs`; an expiry only re-raises a card with an `aged`
marker. Nothing here ever acts on silence (DECISIONS 0048 clause 4).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from l5gntools.common import DATA_DIR

from . import project_wizard

#: Where the Desk's own records live -- events (sightings, findings, rulings)
#: and the trial's start marker. Neither is board state; both are records of
#: what happened or was decided, the same distinction `project_wizard`'s run
#: markers draw against its own board.
DESK_DATA_DIR: Path = DATA_DIR / "desk"
EVENTS_PATH: Path = DESK_DATA_DIR / "events.jsonl"
TRIAL_STATE_PATH: Path = DESK_DATA_DIR / "trial_state.json"

#: "N in the module, not config, until a second card type exists to justify
#: generalising" (Task 1's own instruction).
AGED_AFTER_DAYS = 3.0

#: Task 4: the trial's first week is silent -- cards are derived and sighted
#: but not shown, to measure the patrol-and-remember baseline this module
#: exists to beat.
SILENT_WEEK_DAYS = 7.0

VALID_RULINGS = frozenset({"rebuild", "snooze", "dismiss"})


class DeskRefused(ValueError):
    """Raised with a named `reason`, never a bare message -- the same shape
    `curator_control.ExecutionRefused` and `project_wizard`'s
    `ManifestValidationError` already use, so the router can turn it into a
    400 with a `reason` the view can act on rather than parsing a sentence."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


# ---------------------------------------------------------------------------
# Small, shared time helpers. UTC ISO-8601 everywhere, per the brief's
# working rules -- the same convention `project_wizard.write_run_marker`
# already uses.
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parse_iso(value: Any) -> float | None:
    """Best-effort epoch seconds from an ISO-8601 string. Returns ``None``
    rather than raising -- every caller here treats an unparsable timestamp
    as "no clock available", never as an error worth stopping a render for."""
    if not value or not isinstance(value, str):
        return None
    try:
        v = value.strip()
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def _iso_from_epoch(epoch: float | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_GENERATED_AT_RE = re.compile(r"generated_at=([0-9TZ:\-\.\+]+)")


def _extract_generated_at_epoch(status_text: str) -> float | None:
    """Pulls the `generated_at=<iso>` token out of a delegated freshness
    answer -- `estate_freshness_check.py`'s own output shape (Task 0),
    deliberately parseable for exactly this reason. The full status string is
    still what the card shows verbatim (0042 clause 7); this is a second,
    narrower read of the same string, only ever used to answer "when did this
    become observable", never to second-guess the verdict itself."""
    if not status_text:
        return None
    m = _GENERATED_AT_RE.search(status_text)
    if not m:
        return None
    return _parse_iso(m.group(1))


# ---------------------------------------------------------------------------
# Events -- append-only JSONL. The ledger's seed corpus (Phase 2 migrates
# it), not board state; the board still derives (Task 2).
# ---------------------------------------------------------------------------

def _read_events() -> list[dict]:
    if not EVENTS_PATH.is_file():
        return []
    out: list[dict] = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            # A truncated trailing line from a hard kill mid-write does not
            # invalidate the file (UAT: "the events file is valid JSONL --
            # append-only survives"). Skip it; every earlier line is intact.
            continue
    return out


def _append_event(payload: dict) -> dict:
    DESK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, sort_keys=True) + "\n"
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return payload


def append_finding(text: str, *, refs: list[str] | None = None) -> dict:
    """A human-entered finding -- never derived (Task 2). Not wired to an
    HTTP route in this round: the brief names exactly three Desk routes
    (`cards`, `rule`, `latency`) and a findings-write route is not one of
    them, so this stays an importable function for now -- a manual entry
    point (a REPL, a small seed script) rather than a fourth, undeclared
    surface. Seeding the 2026-08-15..17 Grand Walk fix list through this
    function is future work for whoever holds that walk sheet; this build
    does not fabricate that corpus."""
    if not (text or "").strip():
        raise DeskRefused("empty_finding", "a finding requires non-empty text.")
    return _append_event({
        "kind": "finding", "text": text, "source": "human",
        "ts": _utcnow_iso(), "refs": list(refs or []),
    })


def _sightings_for(events: list[dict], fingerprint: str) -> list[dict]:
    return [e for e in events if e.get("kind") == "sighting" and e.get("fingerprint") == fingerprint]


def _sync_sightings(current_cards: list[dict]) -> None:
    """Writes a `sighting` event only when a fingerprint is new, or newly
    aged -- "a render that changes nothing writes nothing" (Task 2). Runs on
    every :func:`cards` call, including during the trial's silent first week
    (Task 4: sightings are still logged then, only the view stays quiet)."""
    if not current_cards:
        return
    events = _read_events()
    now = _utcnow_iso()
    for card in current_cards:
        fp = card["fingerprint"]
        history = _sightings_for(events, fp)
        aged_now = bool(card["expiry"]["aged"])
        if not history:
            _append_event({
                "kind": "sighting", "fingerprint": fp, "card_summary": card["question"],
                "ts": now, "condition_first_observable": card["condition_first_observable"],
                "aged": aged_now,
            })
        elif aged_now and not any(h.get("aged") for h in history):
            _append_event({
                "kind": "sighting", "fingerprint": fp, "card_summary": card["question"],
                "ts": now, "condition_first_observable": card["condition_first_observable"],
                "aged": True,
            })


def rule(fingerprint: str, ruling: str, reason: str, *,
        evidence_refs: list[str] | None = None, until: str | None = None,
        known_fingerprints: frozenset[str] | None = None) -> dict:
    """Records one ruling. `known_fingerprints` -- when given -- must be a
    freshly-derived set from :func:`cards`; a fingerprint not on it is
    refused (UAT: "refuses an unknown fingerprint"). A `dismiss` without a
    reason is refused -- "the un-promotable decision" (Task 2): promotion
    detection (Phase 4) feeds on reasons, so an empty one is worse than none."""
    if ruling not in VALID_RULINGS:
        raise DeskRefused("unknown_ruling",
                          f"{ruling!r} is not one of {sorted(VALID_RULINGS)}.")
    if known_fingerprints is not None and fingerprint not in known_fingerprints:
        raise DeskRefused("unknown_fingerprint",
                          f"{fingerprint!r} is not a currently-derived card. Refused -- "
                          "rulings only land against a fingerprint the board can see right now.")
    if ruling == "dismiss" and not (reason or "").strip():
        raise DeskRefused("empty_dismiss_reason",
                          "a dismiss ruling requires a non-empty reason.")
    if ruling == "snooze" and not (until or "").strip():
        raise DeskRefused("missing_snooze_until",
                          "a snooze ruling requires an until-condition.")
    payload = {
        "kind": "ruling", "fingerprint": fingerprint, "ruling": ruling,
        "reason": reason or "", "evidence_refs": list(evidence_refs or []),
        "ts": _utcnow_iso(),
    }
    if ruling == "snooze":
        payload["until"] = until
    return _append_event(payload)


# ---------------------------------------------------------------------------
# The trial state -- Task 4. One stored timestamp: the trial's start.
# ---------------------------------------------------------------------------

def _trial_state() -> dict:
    """Reads (and, on first call only, initialises) the trial's start.

    The brief says the trial's start is "the commit date of the round's last
    task" -- a fact this module cannot know at build time, since the commit
    has not happened yet. What it initialises to instead is the first moment
    anything asks for the trial's status, which in practice is very close to
    that commit (the deploy that makes this route reachable at all). If the
    true round-closing commit date differs from `data/desk/trial_state.json`'s
    `trial_start`, that file is a plain, hand-editable JSON object -- correct
    it once, by hand, before the silent week is relied on for anything."""
    if not TRIAL_STATE_PATH.is_file():
        DESK_DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"trial_start": _utcnow_iso()}
        tmp = TRIAL_STATE_PATH.with_name(TRIAL_STATE_PATH.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, TRIAL_STATE_PATH)
        return payload
    try:
        data = json.loads(TRIAL_STATE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"trial_start": None}
    except (OSError, ValueError):
        return {"trial_start": None}


def trial_status() -> dict:
    state = _trial_state()
    start_epoch = _parse_iso(state.get("trial_start"))
    visible_epoch = (start_epoch + SILENT_WEEK_DAYS * 86400) if start_epoch is not None else None
    now = time.time()
    return {
        "trial_start": state.get("trial_start"),
        "visible_at": _iso_from_epoch(visible_epoch),
        "visible": visible_epoch is not None and now >= visible_epoch,
    }


# ---------------------------------------------------------------------------
# Evidence -- the linked-thread lookup. Best-effort and absence-tolerant on
# purpose: "where a project_link exists in the vault for this repo... absent
# otherwise and stated as absent" (Task 1). A lookup failure here must never
# take a card down with it.
# ---------------------------------------------------------------------------

def _linked_thread_evidence(repo_root: Path, db_path: Path | None) -> dict:
    if db_path is None or not Path(db_path).is_file():
        return {"available": False, "reason": "no_vault_on_this_machine"}
    try:
        from .core import connect
        conn = connect(Path(db_path))
        try:
            row = conn.execute(
                "SELECT t.title, t.updated_at FROM threads t "
                "JOIN projects p ON p.project_id = t.project_link "
                "WHERE p.repo_folder_path = ? "
                "ORDER BY t.updated_at DESC LIMIT 1",
                (str(repo_root),),
            ).fetchone()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 -- optional evidence, never fatal to a card
        return {"available": False, "reason": "lookup_failed", "detail": str(exc)}
    if row is None:
        return {"available": False, "reason": "no_project_link"}
    return {"available": True, "title": row[0], "date": row[1]}


# ---------------------------------------------------------------------------
# Card derivation -- Task 1. Fresh on every call; nothing about the card set
# itself is cached.
# ---------------------------------------------------------------------------

def _fingerprint(repo_key: str, stage_key: str, trigger_kind: str) -> str:
    """A stable hash of (repo_key, stage_key, trigger_kind) -- deliberately
    EXCLUDING timestamps, so the same standing staleness is one fingerprint
    that ages, not a new card per render (Task 1)."""
    raw = f"{repo_key}\x1f{stage_key}\x1f{trigger_kind}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _dependency_signal(manifest, stage) -> tuple[float | None, str | None]:
    """The timestamp that would make a dependent stage stale: the
    dependency's own run marker `finished_at` if one exists, else its self
    freshness's newest-output mtime (Task 1, Trigger B: "A's run marker (or
    A's output_glob newest mtime)")."""
    marker = project_wizard.read_run_marker(manifest.repo_key, stage.key)
    if marker and marker.get("finished_at"):
        epoch = _parse_iso(marker["finished_at"])
        if epoch is not None:
            return epoch, f"run marker finished_at={marker['finished_at']}"
    fr = project_wizard.stage_freshness(manifest, stage)
    if fr.get("source") == "self" and fr.get("last_built") is not None:
        return fr["last_built"], f"{stage.key}'s own output mtime"
    return None, None


def _expiry(condition_epoch: float | None) -> dict:
    now = time.time()
    age_days = (now - condition_epoch) / 86400 if condition_epoch is not None else None
    return {
        "aged_after_days": AGED_AFTER_DAYS,
        "age_days": age_days,
        "aged": age_days is not None and age_days > AGED_AFTER_DAYS,
    }


def _base_options() -> list[dict]:
    """Every card's option set. No cost estimate is attached to any option:
    `project_wizard`'s run marker does not record a duration (only
    `finished_at`), so there is no honest wall-clock figure to show -- "no
    measurement, no estimate" (0037 clause 4), stated rather than
    approximated."""
    return [
        {"id": "rebuild", "label": "Rebuild now", "cost": None,
         "cost_note": "no measurement recorded for this stage yet."},
        {"id": "snooze", "label": "Snooze", "cost": None},
        {"id": "dismiss", "label": "Dismiss", "cost": None},
    ]


def _make_card(*, manifest, stage, trigger_kind: str, trigger: dict,
              condition_epoch: float | None, db_path: Path | None) -> dict | None:
    """Assembles one card's full D-A anatomy, or returns ``None`` if any
    required field cannot be filled -- "a card without assembled evidence is
    not raised" (Task 1; DECISIONS 0048 clause 2)."""
    if condition_epoch is None:
        return None  # no honest clock -> no expiry -> the card is not raised

    freshness = project_wizard.stage_freshness(manifest, stage)
    fingerprint = _fingerprint(manifest.repo_key, stage.key, trigger_kind)
    question = (f"{manifest.repo_name} / {stage.label} ({manifest.repo_key}::{stage.key}) "
                f"looks stale -- rebuild it?")
    return {
        "fingerprint": fingerprint,
        "repo_key": manifest.repo_key,
        "repo_name": manifest.repo_name,
        "stage_key": stage.key,
        "stage_label": stage.label,
        "question": question,
        "trigger": {"kind": trigger_kind, **trigger},
        "condition_first_observable": _iso_from_epoch(condition_epoch),
        "evidence": {
            "freshness": freshness,
            "last_run": project_wizard.read_run_marker(manifest.repo_key, stage.key),
            "manifest_declaration": {
                "kind": stage.kind, "output_glob": stage.output_glob,
                "depends_on": list(stage.depends_on),
                "freshness_source": stage.freshness_source,
            },
            "linked_thread": _linked_thread_evidence(manifest.repo_root, db_path),
        },
        "options": _base_options(),
        "default": "hold",
        "expiry": _expiry(condition_epoch),
    }


def cards(allowlist: dict[str, Path] | None = None, *, db_path: Path | None = None,
         sync_sightings: bool = True) -> list[dict]:
    """Every currently-raised card, derived fresh from
    `project_wizard.load_manifests()` -- never stored (Task 1).

    Trigger A (delegated staleness): a stage whose `freshness_source` is
    `delegated` and whose command's own answer reports stale, shown verbatim
    (0042 clause 7). Trigger B (dependency staleness): a stage whose
    `depends_on` names a stage that ran (or was built) more recently than its
    own output.
    """
    loads = project_wizard.load_manifests(allowlist)
    out: list[dict] = []
    for result in loads:
        manifest = result.manifest
        if manifest is None:
            continue  # an invalid manifest blocks that repo's Project Wizard
                      # card too; the Desk raises nothing it cannot evidence.
        stage_by_key = {s.key: s for s in manifest.stages}

        # ---- Trigger A: delegated staleness -----------------------------
        for stage in manifest.stages:
            fs = stage.freshness_source or {}
            if fs.get("type") != "delegated":
                continue
            fr = project_wizard.stage_freshness(manifest, stage)
            if fr.get("error"):
                continue  # a failed delegated command is not evidence of staleness
            status = fr.get("status") or ""
            if "stale" not in status.lower():
                continue
            condition_epoch = _extract_generated_at_epoch(status)
            card = _make_card(
                manifest=manifest, stage=stage, trigger_kind="delegated",
                trigger={"delegated_status": status, "returncode": fr.get("returncode")},
                condition_epoch=condition_epoch, db_path=db_path)
            if card is not None:
                out.append(card)

        # ---- Trigger B: dependency staleness -----------------------------
        for stage in manifest.stages:
            if not stage.depends_on:
                continue
            fr = project_wizard.stage_freshness(manifest, stage)
            if fr.get("source") != "self" or fr.get("last_built") is None:
                continue  # nothing to compare a dependency against
            b_epoch = fr["last_built"]
            for dep_key in stage.depends_on:
                dep = stage_by_key.get(dep_key)
                if dep is None:
                    continue  # an unknown dependency is not evidence either way
                a_epoch, a_desc = _dependency_signal(manifest, dep)
                if a_epoch is None or a_epoch <= b_epoch:
                    continue
                card = _make_card(
                    manifest=manifest, stage=stage, trigger_kind="dependency",
                    trigger={
                        "depends_on": dep_key, "dependency_signal": a_desc,
                        "dependency_signal_at": _iso_from_epoch(a_epoch),
                        "this_stage_built_at": _iso_from_epoch(b_epoch),
                    },
                    condition_epoch=a_epoch, db_path=db_path)
                if card is not None:
                    out.append(card)

    if sync_sightings:
        _sync_sightings(out)
    return out


# ---------------------------------------------------------------------------
# The latency footer -- Task 2's decision-latency instrument. Anchored to
# `condition_first_observable`, never to first sighting (the whole point of
# the correction Task 2 records).
# ---------------------------------------------------------------------------

def latency_summary(current_cards: list[dict] | None = None) -> dict:
    """`desk.py`'s own small footer number: cards raised, ruled, median
    latency, oldest open. `current_cards` -- when given, a fresh
    :func:`cards` result -- is only used for "oldest open"; the rest reads
    purely from the events log.

    **Simplification, named rather than hidden:** "ruled" here means "at
    least one ruling event exists for this fingerprint, ever" -- there is
    only one card type in this round (Task 4's own control) and no re-open
    tracking beyond the `aged` marker, so a fingerprint that was dismissed
    once and re-raised aged later still counts as ruled for this v1 footer.
    Phase 2's ledger migration is where per-recurrence tracking belongs, not
    a home-grown addition here.
    """
    events = _read_events()
    sightings: dict[str, list[dict]] = {}
    rulings: dict[str, list[dict]] = {}
    for e in events:
        if e.get("kind") == "sighting":
            sightings.setdefault(e["fingerprint"], []).append(e)
        elif e.get("kind") == "ruling":
            rulings.setdefault(e["fingerprint"], []).append(e)

    latencies: list[float] = []
    for fp, rs in rulings.items():
        hist = sightings.get(fp) or []
        if not hist:
            continue
        first = min(hist, key=lambda h: h.get("ts") or "")
        cfo_epoch = _parse_iso(first.get("condition_first_observable"))
        if cfo_epoch is None:
            cfo_epoch = _parse_iso(first.get("ts"))  # last resort, not the design
        if cfo_epoch is None:
            continue
        for r in rs:
            r_epoch = _parse_iso(r.get("ts"))
            if r_epoch is not None and r_epoch >= cfo_epoch:
                latencies.append(r_epoch - cfo_epoch)

    oldest_open_days = None
    if current_cards:
        now = time.time()
        for card in current_cards:
            if card["fingerprint"] in rulings:
                continue
            cfo_epoch = _parse_iso(card.get("condition_first_observable"))
            if cfo_epoch is None:
                continue
            age_days = (now - cfo_epoch) / 86400
            if oldest_open_days is None or age_days > oldest_open_days:
                oldest_open_days = age_days

    return {
        "cards_raised": len(sightings),
        "cards_ruled": len(rulings),
        "median_latency_hours": (statistics.median(latencies) / 3600.0) if latencies else None,
        "oldest_open_days": oldest_open_days,
    }


# ---------------------------------------------------------------------------
# The request-body model -- MODULE level, guarded, exactly the pattern
# `project_wizard.py` documents at length above its own `ExecuteBody`: this
# file also has `from __future__ import annotations`, so a Pydantic model
# defined inside `router()` would leave an unresolved ForwardRef and FastAPI
# would silently misread the parameter as a query param instead of a body.
# ---------------------------------------------------------------------------
try:
    from pydantic import BaseModel

    class RuleBody(BaseModel):
        fingerprint: str
        ruling: str
        reason: str = ""
        evidence_refs: list[str] = []
        until: str | None = None
except ImportError:  # pydantic ships with fastapi; absent == web stack not installed
    RuleBody = None  # type: ignore


def router(ctx):
    from fastapi import APIRouter, HTTPException

    api = APIRouter()

    @api.get("/api/desk/cards")
    def desk_cards_route():
        derived = cards(db_path=ctx.db_path)
        trial = trial_status()
        if not trial["visible"]:
            # Task 4: the first week is silent. Sightings above already ran
            # (cards() always syncs them); only the response is withheld.
            return {"cards": [], "trial": trial,
                    "note": "Silent baseline week -- cards are being derived and sighted "
                            "in the background, not shown yet."}
        return {"cards": derived, "trial": trial}

    @api.post("/api/desk/rule")
    def desk_rule_route(payload: RuleBody):
        known = {c["fingerprint"] for c in cards(db_path=ctx.db_path, sync_sightings=False)}
        try:
            return rule(payload.fingerprint, payload.ruling, payload.reason,
                       evidence_refs=payload.evidence_refs, until=payload.until,
                       known_fingerprints=known)
        except DeskRefused as exc:
            raise HTTPException(status_code=400,
                                detail={"reason": exc.reason, "detail": exc.message})

    @api.get("/api/desk/latency")
    def desk_latency_route():
        return latency_summary(cards(db_path=ctx.db_path, sync_sightings=False))

    return api
