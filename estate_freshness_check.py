#!/usr/bin/env python3
"""estate_freshness_check.py -- Trigger A's data source, COWORK_BRIEF_desk_stale_card.md Task 0.

A small, honest command that answers the same freshness question the deck's
own build stamp answers (`chronicler/review/estate_data.py`'s `EstateData
.header()`, mirrored client-side by `static/app.js`'s `loadStamp()` -- "over
24h reads as stale"), so this checkout's `wizforge.manifest.json` has a real
`freshness_source: delegated` stage to point Project Wizard's Trigger A at,
instead of one built just to exercise it (see the brief's Task 0: "this
module would render empty forever" without it).

Reads `data/estate.json`'s own `generated_at` field -- the same field
`EstateData.header()` reads -- rather than the file's mtime, so rewriting the
same content twice does not "refresh" this reading if nothing actually
changed.

Deliberately does not import anything from `chronicler.review` or `l5gntools`.
This runs as a literal, standalone argv entry in a manifest command (0042
clause 4), spawned as its own subprocess by `project_wizard.stage_freshness`
-- keeping it dependency-free means it never breaks because the review
package's import surface changed, and it stays readable by a human deciding
whether to trust a delegated answer (0042 clause 7's whole point).

Prints exactly one line to stdout, and that line is shown verbatim on the
Desk's card -- never re-derived into a second, Desk-computed staleness number
(the same discipline `stage_freshness` already applies to any delegated
source). Includes `generated_at=<iso>` in that line on purpose: it is the
Desk's only way to answer *when* the staleness became observable
(`condition_first_observable`, COWORK_BRIEF_desk_stale_card.md Task 2)
without inventing a second clock -- parsed back out of this same verbatim
string, never carried out-of-band.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ESTATE_JSON = Path(__file__).resolve().parent / "data" / "estate.json"
#: Matches `static/app.js`'s `loadStamp()` threshold exactly -- not a new
#: number, the same one, so "STALE" means the same thing on every surface.
STALE_AFTER_SECONDS = 86400


def main() -> int:
    if not ESTATE_JSON.is_file():
        print("no data/estate.json on this machine -- run `python run.py build`")
        return 0
    try:
        snap = json.loads(ESTATE_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"data/estate.json unreadable: {exc}")
        return 0

    generated_at = snap.get("generated_at")
    if not generated_at:
        print("data/estate.json has no generated_at field")
        return 0

    try:
        parsed = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        print(f"data/estate.json generated_at is unparsable: {generated_at!r}")
        return 0

    age_seconds = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())
    hours = age_seconds / 3600
    verdict = "STALE" if age_seconds > STALE_AFTER_SECONDS else "fresh"
    print(f"{hours:.1f}h old (generated_at={generated_at}) -- {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
