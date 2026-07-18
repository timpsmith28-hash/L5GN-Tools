# chronicler/review — the narrow write endpoint (DECISIONS 0007 stage 2)

The matching *write* surface to the Datasette read surface. It applies **human
project-link rulings** to the vault and nothing else.

## Run it (on the knight)

```bash
pip install -e .[review]          # FastAPI + uvicorn (optional extra, not in core)
python run.py review              # binds 0.0.0.0:8002 by default
python run.py review --port 8010  # override the port
```

Reachable, exactly like `serve`: `http://<knight-100.x>:8002/` from a phone on the
tailnet, `http://<knight-192.168.x>:8002/` from the LAN (the work rig). Paths come
from `CHRONICLER_DB_PATH` / `vault` / `CHRONICLER_HOME` — never hardcoded (0007 C.4).

Registry location for id-validation resolves in this order: `CHRONICLER_REGISTRY_PATH`
env → relink's derived `<github>/L5GN/.intel_sync/project_registry.json` → the repo
`config/project_registry.json`. **Set `CHRONICLER_REGISTRY_PATH` on the knight** to
sidestep the derivation fragility (see the round-2 report).

## What it does — and the one thing it guarantees

A ruling submits a **registry `id`** for a thread. The endpoint writes **exactly two
columns** on that thread:

```
threads.project_link       := <registry id>
threads.project_confidence := 'manual'
```

It **never** touches `link_evidence`, `review_queue`, message content, or any other
pipeline-owned column. That column boundary — not a lock, not a convention — is what
makes it single-writer-safe next to the pipeline: the two writers touch disjoint
column sets and cannot collide (DECISIONS 0007; INTENT §5 "one writer"). The
hermetic gate (`tests/tester_review.py`) proves this: seed a thread, apply a ruling,
assert every other column and every evidence/queue row is byte-for-byte unchanged.

`project_confidence='manual'` is also the lock: it sits at the top of relink's
authority ladder (`none < fuzzy < evidence < manual`, `manual` PROTECTED), so the
nightly relink pass skips a ruled thread forever after. The write *is* the lock.

Unknown ids and unknown threads are **rejected loudly** (HTTP 400, nothing written) —
never a silent garbage write (INTENT §5 "fail loud, never silently wrong").

Estate/account-agnostic (DECISIONS 0010): the UI does not filter or group by estate
or account, and any thread may be assigned to any project — but the thread's account
is shown per-row, informationally.

## Layout

| file | role |
|---|---|
| `core.py` | stdlib-only DB + registry logic (path resolution, pending query, `apply_ruling`, validation). No server. Hermetically tested. |
| `app.py` | thin FastAPI + StaticFiles shell over `core`. Optional deps; `available()` gates it. |
| `static/index.html` | single-file vanilla-JS UI. Functional, not polished (Tim tunes it). |

## Deliberate deviations from the vertex-3 spine (recorded)

- **No SQLAlchemy.** The write is one two-column parameterised `UPDATE`; an ORM adds
  a dependency and hides the column-scope that is the whole safety argument. Raw
  `sqlite3`, all in `core.py`, keeps it debuggable at 2am (INTENT §3).
- **No Cloudflare / public site.** Tailscale/LAN bind only (0007). Wildcard CORS is
  acceptable *only* because of that bind — do not flip it public without re-examining.

## Known follow-ups for round 3 (do not silently "fix" — these are decisions)

1. **`project_link` identifier divergence.** This endpoint stores the registry **id**
   (`crystal-spire`), per the brief. `relink.py` stores the **canonical_name**
   (`Crystal Spire`) and upserts `projects` keyed by canonical_name. So the same
   project can end up with two `projects` rows / two `project_link` spellings.
   Reconcile in round 3 (pick one identifier; simplest is to switch relink to the id).
2. **Pending `review_queue` rows linger by design.** A ruled thread drops off the UI
   via its `manual` confidence, but its `review_queue` row stays `status='pending'`
   because the endpoint must not write that pipeline-owned table. Cosmetic DB residue
   only (the read query filters it). A pipeline-owned reconciliation pass could flip
   ruled-thread queue rows to `confirmed` later, keeping single-writer clean.
