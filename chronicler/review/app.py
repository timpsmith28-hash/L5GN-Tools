"""HTTP + static-UI shell over review/core.py.

Modelled on the l5gn-mesh-vertex-3 spine (FastAPI + uvicorn + StaticFiles) but
stripped to the tailnet: no Cloudflare, no public site (0007 -- that layer was
vertex-3's finicky part and is entirely separable). Deviations from vertex-3,
deliberate and recorded:

  * No SQLAlchemy. The write is a single two-column parameterised UPDATE; an ORM
    would add a dependency and a layer of indirection for zero benefit and make
    the single-writer column-scope harder to see. Raw sqlite3 keeps the write
    path auditable at a glance (INTENT 3 "could I debug this at 2am", 5 minimal
    deps). All DB logic lives in core.py and is stdlib-only + hermetically tested.
  * CORSMiddleware allow_origins=['*'] is acceptable ONLY because the bind is
    Tailscale/LAN-only (0007). Recorded here so nobody flips it public without
    re-examining.

FastAPI + uvicorn are an OPTIONAL extra (`pip install -e .[review]`), never in the
stdlib-only core. `available()` reports absence; `run.py review` skips loudly.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import core

# The request-body model must live at MODULE level (not inside create_app) so
# pydantic can resolve it when FastAPI builds the route schema -- a closure-local
# model leaves an unresolved ForwardRef and FastAPI misreads it as a query param.
# Guarded so importing this module without the optional web stack still succeeds
# (run.py imports it before checking available() to skip loudly).
try:
    from pydantic import BaseModel

    class Ruling(BaseModel):
        thread_id: str
        project_id: str
except ImportError:  # pydantic ships with fastapi; absent == web stack not installed
    Ruling = None  # type: ignore


def available() -> bool:
    """True iff the optional web stack (fastapi + uvicorn) is importable."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        return True
    except ImportError:
        return False


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def create_app(db_path: Path, registry: dict):
    """Build the FastAPI app. `registry` is the pre-loaded id->entry map so id
    validation never depends on a file read mid-request."""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="Chronicler review", docs_url="/api/docs")
    # Tailscale/LAN-only bind makes wildcard CORS acceptable (0007).
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"],
                       allow_headers=["*"])

    @app.get("/api/registry")
    def get_registry():
        return [
            {"id": e["id"], "canonical_name": e["canonical_name"],
             "is_sub": e["is_sub"], "estate": e["estate"],
             "account_scope": e["account_scope"]}
            for e in sorted(registry.values(),
                            key=lambda e: (e["is_sub"], e["canonical_name"].lower()))
        ]

    @app.get("/api/pending")
    def get_pending():
        conn = _connect(db_path)
        try:
            return core.pending_rulings(conn)
        finally:
            conn.close()

    @app.post("/api/rule")
    def post_rule(ruling: Ruling):
        conn = _connect(db_path)
        try:
            return core.apply_ruling(conn, ruling.thread_id, ruling.project_id, registry)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            conn.close()

    @app.get("/api/health")
    def health():
        return JSONResponse({"ok": True, "db": str(db_path),
                             "registry_ids": len(registry)})

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")
    return app


def run(db_path: Path, registry: dict, host: str, port: int) -> int:
    """Boot uvicorn. Returns a process return code."""
    import uvicorn
    app = create_app(db_path, registry)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
