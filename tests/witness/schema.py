"""Witness output schema (DECISIONS 0031, COWORK_BRIEF_ui_witness.md Task 6).

One JSON record per witness run, shaped like a future 0022 ledger row from
the start so the eventual migration to that ledger is a move, not a rewrite:
one row per run, `ran_at`, `host`, `commit`, `fixture`, the sheet id, and the
per-item observations.

Per-item outcome is `matched` / `diverged` / `error` -- not pass/fail. This is
structural, not decoration: a shape with no field anywhere that can express a
pass cannot be used to rubber-stamp one, which makes clause 2 of DECISIONS
0031 unavailable rather than merely forbidden. Any field named `passed`, `ok`
or `result` is a defect in this module.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES: tuple[str, ...] = ("matched", "diverged", "error")

_FORBIDDEN_FIELDS = {"passed", "ok", "result"}


@dataclass
class Observation:
    """One item's witness observation. `outcome` is mechanical: `matched` the
    rendered state met the expected state, `diverged` it did not (names what
    diverged in `detail`), `error` the witness itself could not complete the
    check (a crash, a missing selector) -- distinct from `diverged` because a
    witness that cannot run is not evidence the surface is wrong.
    """

    id: str
    outcome: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(
                f"witness outcome {self.outcome!r} not in {OUTCOMES!r} -- "
                f"the schema has no word for 'passed' on purpose (0031 clause 2)")


@dataclass
class WitnessRun:
    """One run of a witness suite against one fixture, at one commit."""

    sheet: str
    ran_at: str
    host: str
    commit: str
    dirty: bool
    fixture: str
    items: list[Observation] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        for forbidden in _FORBIDDEN_FIELDS:
            if forbidden in d or any(forbidden in it for it in d.get("items", [])):
                raise ValueError(
                    f"witness record carries a {forbidden!r} field -- clause 2 "
                    f"of DECISIONS 0031 requires this be structurally impossible")
        return d

    def write(self, root: Path) -> Path:
        """Write to `data/witness/<sheet>.json`. Never `docs/` -- witness
        output is derivable (same commit, same fixture, same answer, forever)
        and does not earn a place in `docs/` per `docs/README.md` §1."""
        out_dir = Path(root) / "data" / "witness"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{self.sheet}.json"
        out.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        return out


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(root: Path, sheet: str) -> dict | None:
    """Read `data/witness/<sheet>.json` back. Returns None if absent or
    unreadable -- the caller (the results-log citation) is responsible for
    reporting that absence visibly, never for treating it as equivalent to
    silence (0031 Task 6: a missing artefact must not produce a results log
    that looks complete)."""
    p = Path(root) / "data" / "witness" / f"{sheet}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
