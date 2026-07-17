"""set_substantive: recompute threads.substantive from message counts, with the
boundary at exactly SUBSTANTIVE_MIN_MESSAGES and full idempotency.

Hermetic & in-process: seed a temp sqlite with threads+messages and monkeypatch
the module's get_connection so it never touches the real vault DB."""
from __future__ import annotations

import contextlib
import io
import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _seed(db: Path, threads: dict[str, tuple[int, object]]) -> None:
    """threads maps thread_id -> (message_count, initial_substantive)."""
    c = sqlite3.connect(str(db))
    c.executescript(
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, substantive INTEGER);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT);"
    )
    mid = 0
    for tid, (count, initial) in threads.items():
        c.execute("INSERT INTO threads VALUES(?,?)", (tid, initial))
        for _ in range(count):
            mid += 1
            c.execute("INSERT INTO messages VALUES(?,?)", (f"m{mid}", tid))
    c.commit()
    c.close()


def _subs(db: Path) -> dict[str, int]:
    c = sqlite3.connect(str(db))
    try:
        return {tid: sub for tid, sub in c.execute(
            "SELECT thread_id, substantive FROM threads")}
    finally:
        c.close()


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPELINE) not in sys.path:
        sys.path.insert(0, str(_PIPELINE))
    import set_substantive  # noqa: E402 -- deferred until sys.path is primed

    cut = set_substantive.SUBSTANTIVE_MIN_MESSAGES
    if cut != 4:
        v.append(f"set_substantive: expected the frozen cut to be 4, got {cut}")

    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "chronicler.db"
        _seed(db, {
            "exactly_cut": (4, None),   # boundary: exactly 4 -> substantive
            "just_under": (3, None),    # 3 -> fragment
            "well_over": (7, None),     # comfortably substantive
            "empty": (0, None),         # no messages -> fragment
            "stale_true": (2, 1),       # was marked substantive, now only 2 -> reset to 0
            "stale_false": (5, 0),      # was marked fragment, now 5 -> promoted to 1
        })

        orig = set_substantive.get_connection
        set_substantive.get_connection = lambda *a, **k: _conn(db)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                set_substantive.run()
            got = _subs(db)
            expect = {"exactly_cut": 1, "just_under": 0, "well_over": 1,
                      "empty": 0, "stale_true": 0, "stale_false": 1}
            if got != expect:
                v.append(f"set_substantive: recompute wrong. got {got} expected {expect}")

            # Idempotency: a second pass changes nothing.
            with contextlib.redirect_stdout(io.StringIO()):
                set_substantive.run()
            if _subs(db) != expect:
                v.append("set_substantive: a second run should be a no-op (not idempotent)")
        finally:
            set_substantive.get_connection = orig
    return v


def _conn(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn
