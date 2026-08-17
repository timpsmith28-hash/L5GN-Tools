"""tester_run_banner: the app startup banner's reachability line (correctness
sweep, finding 4).

Hermetic and stdlib-only. `run_dispatcher._reachability_line` is a pure
function pulled out of `_cmd_app` specifically so this claim is testable
without binding a real server: the banner must never advertise a tailnet/LAN
URL for a bind that DECISIONS 0025 has already restricted to loopback, and it
must never print an unfilled `<knight-...>` placeholder when it does have
something real to say.
"""
from __future__ import annotations

import run as run_dispatcher  # the top-level dispatcher script, run.py


def run() -> list[str]:
    v: list[str] = []

    def _loopback(host: str) -> bool:
        return host in ("127.0.0.1", "::1", "localhost")

    # --- loopback bind: no URL claim, no placeholder ------------------------
    # The line is allowed to name "tailnet"/"LAN" in prose explaining they are
    # NOT reachable -- the bug was printing a URL that implied otherwise, not
    # the words themselves. So this checks for the URL shape, not the words.
    line = run_dispatcher._reachability_line("app", "127.0.0.1", 54553, _loopback)
    if "http://" in line or "<knight" in line:
        v.append(f"run: a loopback-only bind must not print a reachable URL "
                 f"(tailnet or LAN), got: {line!r}")
    if "loopback" not in line:
        v.append(f"run: a loopback-only bind should say so plainly, got: {line!r}")

    # --- non-loopback bind: the real reachability claim, no placeholders ---
    line2 = run_dispatcher._reachability_line("app", "0.0.0.0", 54553, _loopback)
    if "tailnet" not in line2 or "LAN" not in line2:
        v.append(f"run: a non-loopback bind should still advertise tailnet/LAN "
                 f"reachability, got: {line2!r}")
    if str(54553) not in line2:
        v.append(f"run: the reachability line must carry the real port, got: {line2!r}")

    return v
