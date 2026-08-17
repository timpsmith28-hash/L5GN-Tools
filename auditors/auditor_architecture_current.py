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
"""
from __future__ import annotations

import difflib
import tempfile
from pathlib import Path

from l5gntools.common import TOOLKIT_ROOT
from l5gntools.report import ARCHITECTURE_SHAPE_RELPATH, render_architecture_shape
from l5gntools.scanners.architecture_census import census


def run() -> list[str]:
    v: list[str] = []
    committed_path = TOOLKIT_ROOT / ARCHITECTURE_SHAPE_RELPATH
    if not committed_path.exists():
        return [f"{ARCHITECTURE_SHAPE_RELPATH} does not exist -- run "
                "`python run.py render-architecture` and commit it"]

    fresh_text = render_architecture_shape(census(TOOLKIT_ROOT))
    committed_text = committed_path.read_text(encoding="utf-8")

    if fresh_text == committed_text:
        return v

    # Written to a temp location (never over the committed file) purely so a
    # human re-running this by hand has a path to `diff` against directly,
    # in addition to the diff printed below.
    with tempfile.NamedTemporaryFile(
            mode="w", suffix="_architecture_shape.md", delete=False,
            encoding="utf-8") as tmp:
        tmp.write(fresh_text)
        tmp_path = tmp.name

    diff = "\n".join(difflib.unified_diff(
        committed_text.splitlines(), fresh_text.splitlines(),
        fromfile=f"committed:{ARCHITECTURE_SHAPE_RELPATH}",
        tofile=f"regenerated:{tmp_path}", lineterm=""))
    v.append(
        f"{ARCHITECTURE_SHAPE_RELPATH} is stale -- regenerate with "
        f"`python run.py render-architecture` and commit it. Fresh render "
        f"written to {tmp_path} for inspection. Diff:\n{diff}")
    return v
