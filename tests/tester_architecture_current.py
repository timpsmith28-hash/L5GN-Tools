"""tester_architecture_current -- `auditor_architecture_current`'s own pure
logic: the commit-line mask that keeps the lockfile check from going RED on
the very commit that lands a correct regeneration (see that auditor's
docstring for why the mask exists at all), and that the auditor is
otherwise GREEN against this checkout's actually-committed render.
"""
from __future__ import annotations

from auditors import auditor_architecture_current as aac


def _check_mask() -> list[str]:
    v: list[str] = []
    a = "line one\nProducing commit: abc1234 -->\nline three\n"
    b = "line one\nProducing commit: def5678 -->\nline three\n"
    if aac._mask_commit_line(a) != aac._mask_commit_line(b):
        v.append("auditor_architecture_current: masking two texts that "
                 "differ ONLY in the producing-commit SHA should make them "
                 "equal")
    c = "line one\nProducing commit: abc1234 -->\nline THREE CHANGED\n"
    if aac._mask_commit_line(a) == aac._mask_commit_line(c):
        v.append("auditor_architecture_current: masking must not hide a "
                 "real content difference outside the commit line")
    return v


def _check_green_on_real_repo() -> list[str]:
    # A meta-check: this auditor should read GREEN against whatever is
    # actually committed at gate-run time (the same invariant `verify.py`
    # itself enforces by running every auditor) -- run directly here too so
    # a regression is attributed to this file, not read as "the whole gate
    # is red" with no pointer back to the cause.
    violations = aac.run()
    if violations:
        return [f"auditor_architecture_current: expected GREEN against the "
                f"committed render, got: {violations!r}"]
    return []


def run() -> list[str]:
    v: list[str] = []
    v.extend(_check_mask())
    v.extend(_check_green_on_real_repo())
    return v
