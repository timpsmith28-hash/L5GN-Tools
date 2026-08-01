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

    class RulingBatch(BaseModel):
        # Task 4: bulk accept. A flat list, not a dict, so batch order is the
        # UI's check-off order and per-thread results (below) line up with it.
        rulings: list[Ruling]

    class Rejection(BaseModel):
        # DECISIONS 0024: "not this project" for one (thread, candidate) pair.
        thread_id: str
        project_id: str
except ImportError:  # pydantic ships with fastapi; absent == web stack not installed
    Ruling = None  # type: ignore
    RulingBatch = None  # type: ignore
    Rejection = None  # type: ignore


def available() -> bool:
    """True iff the optional web stack (fastapi + uvicorn) is importable."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
        return True
    except ImportError:
        return False


def _connect(db_path: Path) -> sqlite3.Connection:
    # Delegates to core.connect -> l5gntools.dbsafe, so the endpoint cannot open
    # the vault with weaker settings than the pipeline does (DECISIONS 0014). This
    # used to be a local sqlite3.connect with only foreign_keys set -- one of the
    # paths that bypassed the shared helper.
    return core.connect(db_path)


def create_app(db_path: Path | None, registry: dict, account_clause: str,
               estate=None, index=None, vault_unavailable=None):
    """Build the FastAPI app. `registry` is the pre-loaded id->entry map so id
    validation never depends on a file read mid-request. `account_clause` is
    the estate wall's SQL clause (DECISIONS 0025), resolved ONCE by the caller
    from the running machine's declared estate (`core.account_clause_for_estate`)
    and closed over here -- every read route passes it straight through to
    core.py, which never re-derives it from config itself.

    `estate` (an `estate_data.EstateData`) and `index` (a
    `doc_search.DocumentIndex`) back the local deck's document and time views.
    Either half may be absent: `db_path is None` with a `vault_unavailable`
    means this machine has no vault and the queue routes degrade, while an
    unavailable `estate` means no build snapshot and the estate routes degrade.
    Both halves absent is a legitimate (if useless) state and still serves --
    the surface says what it hasn't got rather than refusing to start.
    """
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles

    # The estate wall, made structural rather than argued. `account_clause` is
    # the ONLY thing scoping thread reads to one estate, so a vault served
    # without one would be a surface rendering every estate's threads at once
    # -- exactly the co-rendered case 0023 gates. `run.py` disables the vault
    # half when the clause cannot be resolved; this refuses to build an app
    # where that pairing was got wrong, so the failure is a startup crash and
    # never a silent wall breach.
    if db_path is not None and not account_clause:
        raise ValueError(
            "refusing to serve vault routes with no estate clause: thread "
            "reads are scoped by `account_clause` alone (DECISIONS 0023/0025). "
            "Pass db_path=None to degrade the queue half instead.")

    app = FastAPI(title="Chronicler review", docs_url="/api/docs")
    # Tailscale/LAN-only bind makes wildcard CORS acceptable (0007).
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"],
                       allow_headers=["*"])

    def _need_vault():
        """503 with the reason, for a queue route on a machine with no vault.
        503 rather than 404: the route exists and is correct, the dependency
        it needs is not present here."""
        if db_path is None:
            detail = (vault_unavailable.as_dict() if vault_unavailable is not None
                      else {"available": False, "reason": "vault_absent",
                            "detail": "No vault on this machine."})
            raise HTTPException(status_code=503, detail=detail)

    def _need_estate():
        """503 with the reason, for an estate route with no build snapshot."""
        if estate is None or not estate.available:
            reason = getattr(estate, "reason", None) or "estate_absent"
            raise HTTPException(status_code=503, detail={
                "available": False, "reason": reason,
                "detail": "No estate build on this machine. Run `python run.py "
                          "build` to produce data/estate.json."})

    @app.get("/api/registry")
    def get_registry():
        _need_vault()
        # Sorted program -> project -> repo, and each entry carries its own
        # breadcrumb, so the picker can render the hierarchy for context while
        # still allowing a ruling at any tier (DECISIONS 0012).
        tier_order = {"program": 0, "project": 1, "repo": 2}

        def _key(e):
            # Sort by breadcrumb so children sit directly under their parent,
            # then by tier so a program precedes its own projects. Uniform key
            # shape for every entry -- a mixed key raises on the first compare.
            return ((e.get("hierarchy") or e["canonical_name"]).lower(),
                    tier_order.get(e.get("tier"), 9),
                    e["canonical_name"].lower())

        return [
            {"id": e["id"], "canonical_name": e["canonical_name"],
             "tier": e.get("tier"), "hierarchy": e.get("hierarchy"),
             "program": e.get("program"), "project": e.get("project"),
             "is_sub": e["is_sub"], "estate": e["estate"],
             "account_scope": e["account_scope"]}
            for e in sorted(registry.values(), key=_key)
        ]

    @app.get("/api/pending")
    def get_pending(project: str | None = None):
        _need_vault()
        # `project` filters to one candidate's batch (Task 2) -- a thread whose
        # RIVAL is this project is included too (is_rival=True), never dropped.
        conn = _connect(db_path)
        try:
            return core.pending_rulings(conn, project_id=project, registry=registry,
                                        account_clause=account_clause)
        finally:
            conn.close()

    @app.get("/api/queue/projects")
    def get_queue_by_project():
        _need_vault()
        # The deck's left-hand nav: per candidate project, counts split by type.
        # Thin shell over core.queue_by_project -- no DB logic here.
        conn = _connect(db_path)
        try:
            return core.queue_by_project(conn, registry=registry,
                                         account_clause=account_clause)
        finally:
            conn.close()

    @app.post("/api/rule")
    def post_rule(ruling: Ruling):
        _need_vault()
        conn = _connect(db_path)
        try:
            return core.apply_ruling(conn, ruling.thread_id, ruling.project_id, registry)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            conn.close()

    @app.post("/api/rule/batch")
    def post_rule_batch(batch: RulingBatch):
        _need_vault()
        # Task 4: bulk accept. One validated write per thread inside one
        # transaction (core.apply_ruling_batch); per-thread results returned
        # so a partial failure (one bad id) is visible, never swallowed.
        conn = _connect(db_path)
        try:
            pairs = [(r.thread_id, r.project_id) for r in batch.rulings]
            return core.apply_ruling_batch(conn, pairs, registry)
        finally:
            conn.close()

    @app.post("/api/reject")
    def post_reject(rejection: Rejection):
        _need_vault()
        # DECISIONS 0024: "not this project". Writes ONLY review_rulings --
        # review_queue is never touched by this endpoint.
        conn = _connect(db_path)
        try:
            return core.apply_rejection(conn, rejection.thread_id, rejection.project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        finally:
            conn.close()

    # ---- estate routes: the local deck (0027) --------------------------------
    # Every one of these is read-only and needs no vault. They are what makes a
    # plain producer rig -- estate build, no vault -- a useful surface.

    @app.get("/api/estate/header")
    def estate_header():
        # Deliberately NOT behind _need_estate(): the header is how the UI
        # learns there is no build. Refusing to serve the explanation of a
        # missing thing is how you get a blank page and no idea why.
        if estate is None:
            return {"available": False, "reason": "estate_absent"}
        return estate.header()

    @app.get("/api/estate/projects")
    def estate_projects():
        _need_estate()
        return estate.projects()

    @app.get("/api/estate/documents")
    def estate_documents(project: str):
        """One project's authored documents, grouped by doc_type, knowledge
        first. Generated documents are not in the catalogue at all, so they
        cannot be listed here and have no identifier to request."""
        _need_estate()
        return {"project": project, "groups": estate.documents_for(project)}

    @app.get("/api/estate/document")
    def estate_document(doc_id: str):
        """Render one document, read from disk at request time (0027).

        Note the parameter: `doc_id`, never a path. There is no route on this
        surface that accepts a filesystem path, which is the whole security
        story -- a traversal attempt is simply an identifier that resolves to
        nothing, and even a resolving identifier is re-checked for containment
        inside the configured estate roots before the file is opened.
        """
        _need_estate()
        from .estate_data import DocumentRefused
        try:
            return estate.read_document(doc_id)
        except DocumentRefused as exc:
            # 404 for an unknown id (nothing to disclose about what exists),
            # 403 for a refusal that means "exists but you may not read it".
            status = 404 if exc.reason == "unknown_document" else 403
            raise HTTPException(status_code=status,
                                detail={"reason": exc.reason, "detail": exc.message})

    @app.get("/api/estate/search")
    def estate_search(q: str, project: str | None = None, limit: int = 60):
        _need_estate()
        if index is None:
            raise HTTPException(status_code=503, detail={
                "reason": "index_absent",
                "detail": "The document index was not built for this process."})
        return index.search(q, project=project, limit=limit)

    @app.get("/api/estate/search/status")
    def estate_search_status():
        if index is None:
            return {"engine": None, "notice": "No document index in this process.",
                    "indexed": 0, "skipped": 0, "persisted": False}
        return index.status()

    @app.get("/api/estate/timeline")
    def estate_timeline_route():
        _need_estate()
        from . import estate_time
        return estate_time.estate_timeline(estate.snapshot)

    @app.get("/api/estate/changes")
    def estate_changes():
        """What moved since the previous build. Names both snapshots by
        timestamp and toolkit commit, because "what changed" is meaningless
        without saying changed *between what and what*."""
        _need_estate()
        from . import estate_time
        return estate_time.build_delta()

    # ---- the docs board (0027 read-time; 0028 staging is NOT in this slice) --
    # Neither route is gated. The board derives from `docs/` in this checkout,
    # which needs no vault, no estate build and no configured root -- so
    # gating it behind either half would refuse to render a directory the
    # process is sitting inside. That is the preflight split's rule applied
    # honestly, not an exception to it.

    @app.get("/api/docs/board")
    def docs_board_route():
        """The whole board, recomputed from `docs/` on every call.

        Nothing is cached between requests, which is not an optimisation
        oversight: a cached board is a stored board, and a stored board is the
        status board `docs/README.md` §5 retires by class. Reloading the page
        after a `git mv` shows the move.
        """
        from . import docs_board
        return docs_board.board()

    @app.get("/api/docs/document")
    def docs_board_document(doc_id: str):
        """One card's document, read from disk at request time.

        `doc_id`, never a path -- the same rule as `/api/estate/document`, and
        the containment check behind it is literally the same function, run
        against this repository instead of the estate roots.
        """
        from . import docs_board
        from .estate_data import DocumentRefused
        try:
            return docs_board.read_card_document(doc_id)
        except DocumentRefused as exc:
            status = 404 if exc.reason == "unknown_document" else 403
            raise HTTPException(status_code=status,
                                detail={"reason": exc.reason, "detail": exc.message})

    @app.get("/api/health")
    def health():
        # Both halves reported separately -- this endpoint is how you tell a
        # degraded surface from a broken one at a glance.
        return JSONResponse({
            "ok": True,
            "vault": ({"available": True, "db": str(db_path),
                       "registry_ids": len(registry)} if db_path is not None
                      else (vault_unavailable.as_dict() if vault_unavailable is not None
                            else {"available": False, "reason": "vault_absent"})),
            "estate": ({"available": bool(estate.available),
                        "reason": estate.reason,
                        "generated_at": estate.header().get("generated_at"),
                        "authored_documents": len(estate.documents)}
                       if estate is not None
                       else {"available": False, "reason": "estate_absent"}),
            "search": (index.status() if index is not None else None),
            # Always available: it depends on this checkout, nothing else.
            "docs_board": {"available": True, "read_only": True},
        })

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")
    return app


def run(db_path: Path | None, registry: dict, host: str, port: int,
        account_clause: str, estate=None, index=None, vault_unavailable=None) -> int:
    """Boot uvicorn. Returns a process return code."""
    import uvicorn
    app = create_app(db_path, registry, account_clause, estate=estate,
                     index=index, vault_unavailable=vault_unavailable)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
