"""chronicler.review -- the narrow write endpoint (DECISIONS 0007 stage 2).

The read surface (Datasette, 0007 stage 1) made the corpus queryable; this is the
matching *write* surface for human project-link rulings. It is deliberately the
smallest thing that can be single-writer-safe:

  * It writes **exactly two columns** on `threads` -- `project_link` and
    `project_confidence='manual'` -- and nothing else pipeline-owned. That column
    boundary (not a lock, not a convention) is what makes it safe to run alongside
    the pipeline: they touch disjoint column sets and so cannot collide
    (DECISIONS 0007, INTENT 5 "one writer").
  * The write *core* (`core.py`) is stdlib-only and independently testable without
    booting a server -- the hermetic gate exercises it directly. The HTTP/UI layer
    (`app.py`, FastAPI + uvicorn + StaticFiles) is an OPTIONAL extra, mounted only
    when those deps are present, exactly like Datasette is for `serve`.

Scope this round: project-link rulings only (`project_link` / `link_ambiguous` /
`link_downgrade` queue rows). Not thread_grouping, close_suggestion, or
reconciliation_gap -- those stay read-only via Datasette (round-2 brief, Task C).
"""
