"""The estate report as a live view -- COWORK_BRIEF_unified_app.md Task 3.

`l5gntools/report.py`'s `render_html()` bakes the whole `data/estate.json`
payload into `report.html` once, at build time. That is problem #2 in the
brief, named directly: "the only estate surface that cannot answer 'what is
true now', and it is the first thing anyone opens." 0027 already authorises
the fix -- a local surface may read its source at render time instead of
serving a captured summary -- and this route is exactly that: it re-reads
`data/estate.json` from disk on every request.

Deliberately NOT the `EstateData` object `app.py` already builds and passes
around (`chronicler/review/estate_data.py`): that one is loaded ONCE at
process start (its own docstring says so), which is right for its job --
resolving document ids against a stable in-memory catalogue -- and wrong for
this one. A deck left running across a `python run.py build` must show the
new numbers without a restart, which is the whole point of demoting
`report.html` from surface to export.

`l5gntools/report.py` and the standalone `report.html` build are UNCHANGED
by this module -- 0027's export/view split, not a replacement. The exported
file remains what you can hand to someone with no application installed.
"""
from __future__ import annotations

import json
from pathlib import Path

from l5gntools.common import DATA_DIR

ESTATE_JSON: Path = DATA_DIR / "estate.json"


def read_estate() -> dict | None:
    """The current `data/estate.json`, or None if it has never been built.

    No caching anywhere in this call -- every invocation re-reads the file
    from disk. That is not an oversight to optimise away later; it is the
    behaviour Task 3's UAT line asks for verbatim: "The report view changes
    when data/estate.json changes, with no rebuild."
    """
    if not ESTATE_JSON.is_file():
        return None
    return json.loads(ESTATE_JSON.read_text(encoding="utf-8"))


def router(ctx):
    """Build this module's APIRouter. `ctx` is a `module_contract.AppContext`.

    FastAPI is imported inside the factory, same discipline as
    `estate_time.router` -- this file must stay importable (and therefore
    auditable by `verify.py`) on a machine with no web stack installed
    (DECISIONS 0034's consequence paragraph).
    """
    from fastapi import APIRouter, HTTPException

    api = APIRouter()

    @api.get("/api/estate/report")
    def estate_report_route():
        data = read_estate()
        if data is None:
            # 503, not 404: the route is correct, the dependency it needs
            # (a build) is not present on this machine -- same convention
            # as every other `_need_*` gate in app.py.
            raise HTTPException(status_code=503, detail={
                "available": False, "reason": "estate_absent",
                "detail": "No data/estate.json on this machine. Run "
                          "`python run.py build`."})
        return data

    return api
