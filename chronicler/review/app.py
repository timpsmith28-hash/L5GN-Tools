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

from . import core, module_contract, modules

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

    class UatEntry(BaseModel):
        # One item's verdict + evidence (uat_sidebar Task 2). `evidence` is
        # free text -- including pasted terminal output, which must survive
        # verbatim, so nothing here trims or reformats it.
        id: str
        verdict: str
        evidence: str = ""

    class UatEmit(BaseModel):
        # Task 3: emit the stamped results log. `mode` is None for a first
        # attempt (the caller finds out here if a log already exists),
        # "append" to add a new walk section under the original stamp.
        stem: str
        entries: list[UatEntry]
        mode: str | None = None

    # ---- Curator tab (COWORK_BRIEF_curator_tab.md) ----------------------
    class CuratorRatifyRow(BaseModel):
        # One K0 candidate row's fields, exactly as curator_ratify.build_row
        # needs them. `provenance`/`note` are never inferred -- the caller
        # (the UI, after a human reads the evidence) states them explicitly.
        session_id: str
        local_folder: str
        project_id: str
        conversation_name: str
        provenance: str
        note: str = ""

    class CuratorRatifyPair(BaseModel):
        row_a: CuratorRatifyRow
        row_b: CuratorRatifyRow

    class CuratorModelSelect(BaseModel):
        stage: str
        model_id: str

    class CuratorExecute(BaseModel):
        # The ONLY field an execute request carries -- a stage key, checked
        # against curator_control.EXECUTION_ALLOWLIST. No argv, no path, no
        # flag is ever accepted here (Task 3's whole security story).
        stage: str

    # ---- Task 6 (COWORK_BRIEF_conductor_governor.md): the conductor panel.
    # A plan is BUILT from these inputs, never accepted as free-form JSON --
    # the line planner.py's own docstring draws against CID's
    # chain_builder.py stays drawn here too: no field on this model lets a
    # caller supply a step, an argv, or anything that reaches a subprocess.
    class ConductorCandidate(BaseModel):
        project_id: str
        claim_count: int = 0
        changed_conversations: int = 0
        message_count: int = 0
        estimated_seconds: float | None = None

    class ConductorPlanPreview(BaseModel):
        policy: str
        profile_name: str = "default"
        stage: str = "K2"
        budget_seconds: float | None = None
        cool_down_seconds: float = 0.0
        plan_id: str | None = None
        candidates: list[ConductorCandidate]

    class ConductorPlanApprove(BaseModel):
        # The ONLY field an approve request carries -- a plan_id naming a
        # plan already built and saved by this server, never a plan body a
        # caller could supply and have accepted as-is (0037 clause 1).
        plan_id: str
except ImportError:  # pydantic ships with fastapi; absent == web stack not installed
    Ruling = None  # type: ignore
    RulingBatch = None  # type: ignore
    Rejection = None  # type: ignore
    UatEntry = None  # type: ignore
    UatEmit = None  # type: ignore
    CuratorRatifyRow = None  # type: ignore
    CuratorRatifyPair = None  # type: ignore
    CuratorModelSelect = None  # type: ignore
    CuratorExecute = None  # type: ignore
    ConductorCandidate = None  # type: ignore
    ConductorPlanPreview = None  # type: ignore
    ConductorPlanApprove = None  # type: ignore


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
               estate=None, index=None, vault_unavailable=None,
               curator=None, curator_estate_gap: str | None = None,
               machine: dict | None = None):
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

    `curator` (a `curator_data.Curator`) is the third half (COWORK_BRIEF_
    curator_tab.md, Task 1): the Knowledge Curator tab's read-only data layer,
    plus the ratification/control/findings routes below it. It is
    estate-labelled by construction (0032: MCF-scoped, work estate only), so
    `curator_estate_gap`, when set, disables every curator route with the
    stated reason -- the tab must render an absence, not curator data, on a
    machine whose declared estate is not work/MCF (stop condition). Passing
    `curator=None` (no data/knowledge_curator/ at all) is a separate, legal
    state from `curator_estate_gap` (wrong machine) -- both degrade the same
    routes, for different reasons, and both are reported as such.

    `machine` is the config dict (`l5gntools.config.machine()`) the caller
    already resolved, threaded through only so Datasette's sub-app (Task 3,
    `datasette_mount.build_asgi_app`) can take its own read snapshot via the
    same config-driven path resolution every other snapshot in this estate
    uses (DECISIONS 0007 consequence (a): never hardcode the DB path).
    """
    from fastapi import Depends, FastAPI, HTTPException
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

    # ---- the module registry (COWORK_BRIEF_unified_app.md, Task 1) ---------
    # Every route above this line is declared inline, the old way, and stays
    # that way this round. Below it, modules that have been migrated onto the
    # descriptor registry contribute their own routers and the tab strip is
    # served as data. Both shapes run in one process on purpose: if they could
    # not coexist the descriptor would be wrong, and one tab is the cheapest
    # place to find that out.
    ctx = module_contract.AppContext(
        db_path=db_path, registry=registry, account_clause=account_clause,
        estate=estate, index=index, vault_unavailable=vault_unavailable,
        curator=curator, curator_estate_gap=curator_estate_gap)
    caps = module_contract.capabilities(ctx)

    def _gate(descriptor):
        """One 503 for a whole module, built from its declared `requires`.

        This is the `_need_vault()` / `_need_estate()` pattern hoisted out of
        the route bodies and into data: the module says what it needs, this
        resolves it once at app-build time, and the routes below carry no
        availability question at all. The status is still 503 and the body
        still names the cause -- the route exists and is correct, its
        dependency is not present on this machine.
        """
        gaps = module_contract.unmet(descriptor, caps)

        def dependency():
            if gaps:
                raise HTTPException(status_code=503, detail={
                    "available": False,
                    "reason": gaps[0]["reason"],
                    "module": descriptor.id,
                    "unmet": gaps,
                    "detail": "; ".join(g["detail"] for g in gaps)})

        return dependency

    for descriptor in modules.registered():
        app.include_router(descriptor.router(ctx),
                           dependencies=[Depends(_gate(descriptor))])

    @app.get("/api/modules")
    def get_modules():
        """The tab strip, as data.

        Returns what the browser needs to draw a tab and load a view, plus
        each module's resolved degradation with a named cause -- so a module
        whose requirements are absent renders as declared-degraded rather than
        as an empty pane or an error page. Router factories are Python
        callables and are not in this response; nothing here addresses server
        internals by name.
        """
        return {
            "capabilities": caps,
            "modules": [module_contract.resolve(d, caps) for d in modules.ordered()],
        }

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

    # ---- the UAT sidebar (0028: this is the one write this slice performs) --
    # Both routes are ungated for the same reason the board routes are: this
    # is this repository's own `docs/`, needing no vault and no estate build.

    @app.get("/api/uat/sheet")
    def uat_sheet(stem: str):
        """One walk-sheet's items, plus the unticked-but-walked finding for
        this stem, if any (docs_board's B1/B2, surfaced here on the item
        view too). Read-only; records nothing."""
        from . import uat_sidebar
        from .estate_data import DocumentRefused, REPO_ROOT
        try:
            return uat_sidebar.sheet_view(REPO_ROOT, stem)
        except DocumentRefused as exc:
            status = 404 if exc.reason in ("no_sheet", "bad_stem") else 403
            raise HTTPException(status_code=status,
                                detail={"reason": exc.reason, "detail": exc.message})

    @app.post("/api/uat/emit")
    def uat_emit(payload: UatEmit):
        """Task 3: emit `docs/UAT_<stem>_results.md`, staged (0028) and never
        committed. Refuses (rather than overwrites) an existing log unless
        `mode="append"` is given explicitly."""
        from . import uat_sidebar
        from .estate_data import DocumentRefused, REPO_ROOT
        entries = [e.dict() for e in payload.entries]
        try:
            return uat_sidebar.emit_results_log(REPO_ROOT, payload.stem, entries,
                                                mode=payload.mode)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except DocumentRefused as exc:
            status = 404 if exc.reason in ("no_sheet", "bad_stem") else 403
            raise HTTPException(status_code=status,
                                detail={"reason": exc.reason, "detail": exc.message})

    # ---- the Knowledge Curator tab (COWORK_BRIEF_curator_tab.md) -----------
    # Estate-labelled by construction (0032): every route below is gated on
    # `curator_estate_gap` FIRST, before anything else, so a machine whose
    # declared estate is not work/MCF gets a stated absence and never curator
    # data -- the stop condition this gate exists to make structurally true,
    # not merely documented. This is also what keeps a populated Chronicler
    # strip from ever co-rendering with a populated Curator strip (case 0023):
    # the two are gated on disjoint conditions (account_clause vs
    # curator_estate_gap) and neither route family reads the other's data.
    def _need_curator_estate():
        if curator_estate_gap:
            raise HTTPException(status_code=503, detail={
                "available": False, "reason": "not_work_mcf_estate",
                "detail": curator_estate_gap})

    @app.get("/api/curator/header")
    def curator_header():
        # Deliberately NOT behind _need_curator_estate() in the sense of a
        # blanket 503 with no body: the header is how the tab learns WHY it
        # is absent, same reasoning as estate_header() above. On the wrong
        # machine this returns available=False and no stage data at all.
        if curator_estate_gap:
            return {"available": False, "reason": "not_work_mcf_estate",
                    "detail": curator_estate_gap}
        if curator is None:
            return {"available": False, "reason": "curator_absent",
                    "detail": "No data/knowledge_curator/ on this machine yet."}
        return curator.header()

    @app.get("/api/curator/k0/candidates")
    def curator_k0_candidates(host: str | None = None):
        _need_curator_estate()
        from . import curator_ratify as ratify
        from .curator_data import CANDIDATE_MAP_PATH, ratified_map_rows, _load_tsv_rows
        candidate_path = curator.data_dir / "candidate_map.tsv" if curator else CANDIDATE_MAP_PATH
        ratified_path = curator.ratified_map_path if curator else None
        candidate_rows = _load_tsv_rows(candidate_path)
        ratified_ids = {r.get("session_id", "").strip() for r in ratified_map_rows(ratified_path)}
        claimed = ratified_ids | {r.get("session_id", "").strip()
                                    for r in candidate_rows if r.get("session_id")}
        conversations = []
        access_errors = []
        try:
            import bootstrap_conversation_map as k0  # noqa
            conversations, access_errors = k0.discover_conversations(host)
        except Exception:  # noqa: BLE001 -- store discovery is best-effort here
            pass
        cards = ratify.candidate_cards(candidate_rows, ratified_ids)
        groups = ratify.group_by_outcome(cards)
        unmapped = ratify.unmapped_local_folders(conversations, claimed)
        counts = ratify.six_counts(candidate_rows, len(unmapped))
        return {
            "candidate_path": str(candidate_path), "exists": candidate_path.is_file(),
            "counts": counts, "groups": groups,
            "unmapped_local_folders": unmapped,
            "access_errors": access_errors,
            "ratified_row_count": len(ratified_ids),
        }

    @app.get("/api/curator/k0/evidence")
    def curator_k0_evidence(session_id: str, sheet_text: str | None = None,
                            match_pass: str | None = None, matched_length: int | None = None,
                            host: str | None = None):
        _need_curator_estate()
        from . import curator_ratify as ratify
        conv_text = None
        try:
            from . import curator_findings
            conversations_by_id, _ = curator_findings.build_conversation_map(host)
            conv = conversations_by_id.get(session_id)
            if conv is not None:
                import local_transcripts as lt  # noqa
                conv_text = lt.first_user_message(conv)
        except Exception:  # noqa: BLE001 -- evidence is best-effort, never a 500
            conv_text = None
        return ratify.evidence_spans(sheet_text, conv_text, match_pass, matched_length)

    @app.post("/api/curator/k0/ratify")
    def curator_k0_ratify(payload: CuratorRatifyRow):
        _need_curator_estate()
        from . import curator_ratify as ratify
        from .estate_data import REPO_ROOT
        try:
            row = ratify.build_row(**payload.dict())
            result = ratify.append_ratified_row(row)
            if result["status"] == "appended":
                ratify.stage_ratified_map(REPO_ROOT)
            return result
        except ratify.RatifyError as exc:
            raise HTTPException(status_code=400, detail={"reason": exc.reason, "detail": exc.message})

    @app.post("/api/curator/k0/ratify_pair")
    def curator_k0_ratify_pair(payload: CuratorRatifyPair):
        _need_curator_estate()
        from . import curator_ratify as ratify
        from .estate_data import REPO_ROOT
        try:
            row_a = ratify.build_row(**payload.row_a.dict())
            row_b = ratify.build_row(**payload.row_b.dict())
            results = ratify.append_ratified_pair(row_a, row_b)
            if any(r["status"] == "appended" for r in results):
                ratify.stage_ratified_map(REPO_ROOT)
            return {"results": results}
        except ratify.RatifyError as exc:
            raise HTTPException(status_code=400, detail={"reason": exc.reason, "detail": exc.message})

    @app.get("/api/curator/k0/staged_diff")
    def curator_k0_staged_diff():
        _need_curator_estate()
        from . import curator_ratify as ratify
        from .estate_data import REPO_ROOT
        return {"diff": ratify.staged_diff(REPO_ROOT)}

    @app.get("/api/curator/control/preflight")
    def curator_control_preflight():
        _need_curator_estate()
        from . import curator_control as ctl
        from .curator_data import Curator as _Curator
        c = curator or _Curator()
        return ctl.preflight(c)

    @app.get("/api/curator/control/stage_table")
    def curator_control_stage_table():
        _need_curator_estate()
        from . import curator_control as ctl
        return {
            "stages": {k: {"label": v["label"], "deterministic": v["deterministic"],
                           "model_stage": v["model_stage"]}
                       for k, v in ctl.STAGE_TABLE.items()},
            "model_selectable_stages": list(ctl.MODEL_SELECTABLE_STAGES),
            "k4_shortlist_capability": ctl.shortlist_capability(),
            "allowlist": sorted(ctl.EXECUTION_ALLOWLIST),
        }

    @app.get("/api/curator/control/models")
    def curator_control_models():
        _need_curator_estate()
        from . import curator_control as ctl
        return {"selections": ctl.get_curator_models()}

    @app.post("/api/curator/control/model")
    def curator_control_set_model(payload: CuratorModelSelect):
        _need_curator_estate()
        from . import curator_control as ctl
        try:
            return ctl.set_curator_model(payload.stage, payload.model_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.get("/api/curator/control/invalidation")
    def curator_control_invalidation(stage: str):
        _need_curator_estate()
        from . import curator_control as ctl
        if stage == "K2":
            return ctl.k2_model_change_impact()
        if stage == "K4":
            return ctl.k4_model_change_impact()
        raise HTTPException(status_code=400, detail=f"{stage!r} has no cache-invalidation report")

    @app.post("/api/curator/control/execute")
    def curator_control_execute(payload: CuratorExecute):
        _need_curator_estate()
        from . import curator_control as ctl
        from dataclasses import asdict
        try:
            outcome = ctl.execute_with_lock(payload.stage)
            return asdict(outcome)
        except ctl.ExecutionRefused as exc:
            status = 409 if exc.reason == "already_running" else 400
            raise HTTPException(status_code=status, detail={"reason": exc.reason, "detail": exc.message})

    @app.get("/api/curator/control/lock")
    def curator_control_lock():
        _need_curator_estate()
        from . import curator_control as ctl
        return ctl.lock_status()

    # ---- Task 6 (COWORK_BRIEF_conductor_governor.md): the conductor panel.
    # No execution route lives here -- there is no execution loop yet
    # (conductor_panel.run_state says so plainly). These four routes are the
    # panel's read/plan-build/approve surface only.
    @app.get("/api/curator/conductor/preconditions")
    def curator_conductor_preconditions():
        _need_curator_estate()
        from . import conductor_panel as cp
        from .curator_data import Curator as _Curator
        c = curator or _Curator()
        return cp.preconditions(c)

    @app.get("/api/curator/conductor/calibration")
    def curator_conductor_calibration():
        _need_curator_estate()
        from . import conductor_panel as cp
        return cp.calibration_state()

    @app.get("/api/curator/conductor/run")
    def curator_conductor_run():
        _need_curator_estate()
        from . import conductor_panel as cp
        return cp.run_state()

    @app.post("/api/curator/conductor/plan/preview")
    def curator_conductor_plan_preview(payload: ConductorPlanPreview):
        _need_curator_estate()
        from . import conductor_panel as cp
        from . import planner as pl
        candidates = [
            pl.ProjectCandidate(
                project_id=c.project_id, claim_count=c.claim_count,
                changed_conversations=c.changed_conversations,
                message_count=c.message_count, estimated_seconds=c.estimated_seconds,
            )
            for c in payload.candidates
        ]
        try:
            spec = pl.build_plan(
                candidates, policy=payload.policy, profile_name=payload.profile_name,
                stage=payload.stage, budget_seconds=payload.budget_seconds,
                cool_down_seconds=payload.cool_down_seconds, plan_id=payload.plan_id,
            )
            spec.validate()
            pl.PlanRegistry().save(spec)
        except pl.PlanValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return cp.plan_preview(spec)

    @app.post("/api/curator/conductor/plan/approve")
    def curator_conductor_plan_approve(payload: ConductorPlanApprove):
        _need_curator_estate()
        from . import conductor_panel as cp
        from . import planner as pl
        reg = pl.PlanRegistry()
        reg.load_all()
        spec = reg.get(payload.plan_id)
        if spec is None:
            raise HTTPException(status_code=404, detail=f"no plan '{payload.plan_id}' on record "
                                 "-- build one via /plan/preview first.")
        approved = pl.approve(spec)
        reg.save(approved)
        return cp.plan_preview(approved)

    @app.get("/api/curator/findings")
    def curator_findings_route():
        _need_curator_estate()
        from . import curator_findings as cf
        from .curator_data import _load_json, K1_INDEX_PATH, K2_CLAIMS_PATH, K4_MATCHES_PATH
        data_dir = curator.data_dir if curator else K1_INDEX_PATH.parent
        claims_report = _load_json(data_dir / "claims.json")
        matches_report = _load_json(data_dir / "matches.json")
        knowledge_index = _load_json(data_dir / "knowledge_index.json")
        by_outcome = cf.claims_by_outcome(matches_report)
        return {
            "run_health": cf.run_health(claims_report, matches_report, knowledge_index),
            "gaps_by_project": cf.gaps_by_project(by_outcome, knowledge_index),
            "no_knowledge_file_starters": cf.no_knowledge_file_starters(by_outcome, knowledge_index),
            "cross_project": cf.cross_project(by_outcome),
            "superseded": cf.superseded(by_outcome),
            "captured": cf.captured(by_outcome),
        }

    @app.get("/api/curator/findings/transcript")
    def curator_findings_transcript(conversation_id: str, host: str | None = None):
        _need_curator_estate()
        from . import curator_findings as cf
        from .estate_data import DocumentRefused as _DR
        try:
            conversations_by_id, _ = cf.build_conversation_map(host)
            return cf.read_transcript_window(conversation_id, conversations_by_id, host)
        except _DR as exc:
            status = 404 if exc.reason == "unknown_conversation" else 403
            raise HTTPException(status_code=status, detail={"reason": exc.reason, "detail": exc.message})

    @app.get("/api/curator/coverage")
    def curator_coverage():
        _need_curator_estate()
        from .curator_data import Curator as _Curator
        c = curator or _Curator()
        return c.coverage()

    # ---- Datasette, mounted (COWORK_BRIEF_unified_app.md Task 3) -----------
    # Built once, here, at app-construction time -- not per-request -- so the
    # snapshot it reads has exactly the staleness contract `run.py serve` used
    # to have: fresh as of the moment the process started, refreshed by
    # restarting it. See `datasette_mount`'s module docstring for the verdict
    # (mount, not drop) and why 0013's snapshot-never-live rule is unchanged
    # by moving from a second process to a sub-app of this one.
    from . import datasette_mount
    _datasette_ds, _datasette_note = datasette_mount.build_datasette(machine)
    _datasette_app = _datasette_ds.app() if _datasette_ds is not None else None

    @app.get("/api/health")
    def health():
        # Every half reported separately -- this endpoint is how you tell a
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
            "curator": ({"available": False, "reason": "not_work_mcf_estate",
                        "detail": curator_estate_gap} if curator_estate_gap
                       else (curator.header() if curator is not None
                             else {"available": False, "reason": "curator_absent"})),
            "datasette": ({"available": True, "mounted_at": datasette_mount.MOUNT_PATH,
                          "note": _datasette_note}
                         if _datasette_app is not None
                         else {"available": False, "reason": _datasette_note}),
        })

    # Mounted BEFORE the static catch-all below: a `Mount("/", ...)` matches
    # every path, so anything meant to answer under its own prefix has to be
    # registered ahead of it or it is never reached.
    if _datasette_app is not None:
        app.mount(datasette_mount.MOUNT_PATH, _datasette_app, name="datasette")

        # `Mount()` does not forward this app's ASGI lifespan into the
        # sub-app (proved by hand, see `datasette_mount`'s docstring) --
        # without this, Datasette's own database registration never runs
        # and every route under /db 404s with "Database not found" despite
        # the snapshot having loaded cleanly. `on_event` is deprecated in
        # newer FastAPI in favour of a lifespan context manager, but this
        # app has no lifespan of its own yet and one on_event handler is a
        # smaller diff than introducing one for a single startup call.
        @app.on_event("startup")
        async def _start_datasette():
            await _datasette_ds.invoke_startup()

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")
    return app


def run(db_path: Path | None, registry: dict, host: str, port: int,
        account_clause: str, estate=None, index=None, vault_unavailable=None,
        curator=None, curator_estate_gap: str | None = None,
        machine: dict | None = None) -> int:
    """Boot uvicorn. Returns a process return code."""
    import uvicorn
    app = create_app(db_path, registry, account_clause, estate=estate,
                     index=index, vault_unavailable=vault_unavailable,
                     curator=curator, curator_estate_gap=curator_estate_gap,
                     machine=machine)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
