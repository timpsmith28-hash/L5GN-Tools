"""auditor_architecture_current -- refuses a stale `docs/_architecture_shape.md`.

`architecture_census` (the scanner) and `report.render_architecture_shape`
(the renderer) are read-only and can be re-run any time, but nothing forced
that to happen before a commit -- which is exactly how `ARCHITECTURE.md`
went stale in the first place (`docs/COWORK_BRIEF_architecture_census.md`,
DECISIONS 0030). This is the lockfile pattern applied to that generated
document: regenerate to a temp location, diff against what is actually
committed, fail with the diff printed on any difference.

**Reports; never writes.** This auditor never touches
`docs/_architecture_shape.md`. A gate that silently fixes what it audits
cannot be trusted to audit -- the human runs
`python run.py render-architecture`, this auditor only checks that they did.

**The do-not-edit header's own commit line is excluded from the diff.** The
brief asks the render to name "the producing commit" -- but the commit that
*adds or updates* the file necessarily gets a new SHA the moment it is
made, so a render generated and then committed always names its own
*parent*, not itself; comparing that line literally would make this
auditor RED on the very commit that lands a correct regeneration. This is
the identical shape to `census()`'s own "no wall-clock inside the compared
payload" rule (the provenance block sits outside the compared region) --
applied here to the one line in the render that is provenance about the
*commit*, not about the *content*. Everything else in the file is compared
in full.
"""
from __future__ import annotations

import difflib
import re
import tempfile
from pathlib import Path

from l5gntools.common import TOOLKIT_ROOT
from l5gntools.report import ARCHITECTURE_SHAPE_RELPATH, render_architecture_shape
from l5gntools.scanners.architecture_census import census

_COMMIT_LINE = re.compile(r"Producing commit: \S+ -->")


def _mask_commit_line(text: str) -> str:
    return _COMMIT_LINE.sub("Producing commit: <redacted-for-diff> -->", text, count=1)


def run() -> list[str]:
    v: list[str] = []
    committed_path = TOOLKIT_ROOT / ARCHITECTURE_SHAPE_RELPATH
    if not committed_path.exists():
        return [f"{ARCHITECTURE_SHAPE_RELPATH} does not exist -- run "
                "`python run.py render-architecture` and commit it"]

    fresh_text = render_architecture_shape(census(TOOLKIT_ROOT))
    committed_text = committed_path.read_text(encoding="utf-8")

    if _mask_commit_line(fresh_text) == _mask_commit_line(committed_text):
        return v

    # Written to a temp location (never over the committed file) purely so a
    # human re-running this by hand has a path to `diff` against directly,
    # in addition to the diff printed below.
    with tempfile.NamedTemporaryFile(
            mode="w", suffix="_architecture_shape.md", delete=False,
            encoding="utf-8") as tmp:
        tmp.write(fresh_text)
        tmp_path = tmp.name

    # Diffed with the commit line masked on both sides -- that line is
    # excluded from the red/green decision above, so it should not show up
    # as noise in the printed diff either. The temp file on disk still
    # carries the real, unmasked regeneration.
    diff = "\n".join(difflib.unified_diff(
        _mask_commit_line(committed_text).splitlines(),
        _mask_commit_line(fresh_text).splitlines(),
        fromfile=f"committed:{ARCHITECTURE_SHAPE_RELPATH}",
        tofile=f"regenerated:{tmp_path}", lineterm=""))
    v.append(
        f"{ARCHITECTURE_SHAPE_RELPATH} is stale -- regenerate with "
        f"`python run.py render-architecture` and commit it. Fresh render "
        f"written to {tmp_path} for inspection. Diff:\n{diff}")
    return v
