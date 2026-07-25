"""tester_report_selfcheck -- honest caps and report self-validation
(COWORK_BRIEF_scanner_bugfixes.md Task B).

Two guarantees:
* `common.capped` truncates a list *honestly* -- a bounded slice, but always the
  true count and a truncated flag.
* `report.validate_report` parses both the data feed and the report's embedded
  copy, so a truncated-mid-write report fails loud instead of reading as complete.
  The oversized/capped payload audit names the likely culprit.
"""
from __future__ import annotations

import json

from l5gntools.common import capped
from l5gntools.report import (_DATA_CLOSE, _DATA_OPEN, _payload_audit,
                              validate_report)


def _html(payload_str: str, *, whole: bool = True) -> str:
    """A minimal report page carrying an embedded DATA block. ``whole=False``
    truncates before the close marker -- the mid-write failure the check exists
    to catch."""
    head = "<html><body><script>\n" + _DATA_OPEN + payload_str
    if whole:
        return head + _DATA_CLOSE + "s=>s;\n</script></body></html>"
    return head[: len(head) - len(payload_str) // 2]  # cut mid-payload, no close


def run() -> list[str]:
    v: list[str] = []

    # --- honest truncation ---------------------------------------------------
    kept, truncated, count = capped(list(range(10)), 4)
    if kept != [0, 1, 2, 3] or not truncated or count != 10:
        v.append(f"capped: dishonest truncation -> {(kept, truncated, count)}")
    kept, truncated, count = capped([1, 2], 5)
    if kept != [1, 2] or truncated or count != 2:
        v.append(f"capped: flagged an un-truncated list -> {(kept, truncated, count)}")

    # --- a well-formed report passes ----------------------------------------
    estate = {"projects": [{"name": "P"}], "estate": {}, "anomalies": []}
    payload = json.dumps(estate)
    good = validate_report(payload, _html(payload))
    if good:
        v.append(f"validate_report: flagged a valid report -> {good}")

    # --- a truncated embedded block fails loud, with a culprit ---------------
    anomalies = [{"project": "Chronicler", "scanner": "todo_adr_scanner",
                  "bytes": 999999, "truncated": False}]
    bad = validate_report(payload, _html(payload, whole=False), anomalies)
    if not bad:
        v.append("validate_report: a truncated report.html passed the self-check")
    elif not any("todo_adr_scanner" in p for p in bad):
        v.append(f"validate_report: did not name the likely culprit -> {bad}")

    # --- malformed data feed is caught --------------------------------------
    if not validate_report("{not json", _html(payload)):
        v.append("validate_report: a malformed estate.json passed the self-check")

    # --- payload audit flags oversized + capped -----------------------------
    big = "x" * 600_000
    projects_out = [
        {"name": "Huge", "big_scanner": {"blob": big}},
        {"name": "Capped", "todo_adr_scanner": {"markers": [], "truncated": True}},
        {"name": "Fine", "small_scanner": {"ok": 1}},
    ]
    anomalies = _payload_audit(projects_out, {})
    flagged = {(a["project"], a["scanner"]) for a in anomalies}
    if ("Huge", "big_scanner") not in flagged:
        v.append("payload_audit: did not flag an oversized payload")
    if ("Capped", "todo_adr_scanner") not in flagged:
        v.append("payload_audit: did not flag a capped (truncated) payload")
    if any(p == "Fine" for p, _ in flagged):
        v.append("payload_audit: flagged a normal payload")
    return v
