"""Witness harness: boots the review server against a FIXTURE root only,
never the operator's live estate (COWORK_BRIEF_ui_witness.md Task 3 -- "the
single most important constraint in the brief").

**Never imported by `verify.py`.** This module imports `uvicorn` and (inside
`witness_*` suites) `playwright`, neither of which may reach the gate. Keep
this package off every `AUDITORS`/`TESTERS` entry in `verify.py`, and never
import it from anything `verify.py` does import.
"""
from __future__ import annotations

import contextlib
import socket
import threading
import time
from pathlib import Path

from l5gntools.common import toolkit_git_info
from l5gntools.config import hostname


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def fixture_server(fixture_root: Path):
    """Serve the review app with `chronicler.review.estate_data.REPO_ROOT`
    pointed at `fixture_root` for the duration of the `with` block, then
    restored -- including on a crash.

    The UAT sidebar routes (`/api/uat/sheet`, `/api/uat/emit`) resolve
    `REPO_ROOT` fresh from the module attribute on every request (see
    `chronicler/review/app.py`), rather than closing over it at app-creation
    time. Patching the attribute here is therefore enough to redirect the
    whole UAT surface at a fixture tree without adding a fixture-root
    parameter to `create_app` itself -- no production code changes for a
    detail only the witness needs.
    """
    import uvicorn
    from chronicler.review import app as review_app
    from chronicler.review import estate_data

    fixture_root = Path(fixture_root).resolve()
    original_root = estate_data.REPO_ROOT
    estate_data.REPO_ROOT = fixture_root
    try:
        app = review_app.create_app(None, {}, None, estate=None, index=None)
        port = _free_port()
        config = uvicorn.Config(app, host="127.0.0.1", port=port,
                                log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.time() + 10
        while not getattr(server, "started", False) and time.time() < deadline:
            time.sleep(0.05)
        if not getattr(server, "started", False):
            raise RuntimeError("witness fixture server did not start within 10s")
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=5)
    finally:
        estate_data.REPO_ROOT = original_root


def commit_stamp() -> dict:
    """Same provenance the sidebar's own `stamp_fields()` uses -- host and the
    toolkit's own git state, so a witness record and a uat stamp are directly
    comparable."""
    info = toolkit_git_info()
    return {
        "commit": info["commit"] or "unknown",
        "dirty": bool(info["dirty"]),
        "host": hostname(),
    }
