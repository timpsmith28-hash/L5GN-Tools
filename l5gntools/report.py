"""Aggregate every scanner into one data file and a self-contained HTML viewer.

Outputs (all under L5GN-Tools/data, never in a scanned folder):
* data/<tool>/<project>.json  -- full per-project detail
* data/<tool>.json            -- estate-level tool output
* data/estate.json            -- the single feed the viewer consumes
* report.html                 -- self-contained viewer (data embedded)
"""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import __version__
from .common import (DATA_DIR, ESTATE_ROOT, TOOLKIT_ROOT, now_iso,
                     toolkit_git_info, write_json)
from .registry import SCANNERS
from .scanners import doc_census


#: A single (project, scanner) payload larger than this is called out in the
#: report as an anomaly. Not fatal -- a large `file_census.at_risk` is legitimate
#: -- but "298 markers from one project" is a signal, not a detail
#: (`COWORK_BRIEF_scanner_bugfixes.md` Task B.3).
PAYLOAD_ANOMALY_BYTES = 500_000

#: Marker the HTML template uses to embed the data feed. The self-check re-reads
#: the written report and confirms the block between this and the following line
#: still parses as JSON -- catching the truncated-mid-write failure class.
_DATA_OPEN = "const DATA = "
_DATA_CLOSE = ";\nconst esc="


def scope_summary(estate: dict) -> list[dict]:
    """Per-root scope honesty (governance Task A / D1).

    For each configured root: how many projects were scanned under its scope, and
    whether it was **scanned** (non-empty) or resolved to **empty** this run. A
    root listed but yielding zero projects must read as "empty this run", not as
    "zero projects exist" -- the work run's bug was labelling both the same and
    letting a reader conclude L5GN had no projects.
    """
    by_scope: dict[str, int] = {}
    for p in estate.get("projects", []):
        s = p.get("scope") or "(untagged)"
        by_scope[s] = by_scope.get(s, 0) + 1

    out: list[dict] = []
    seen: set[str] = set()
    for root in estate.get("roots", []):
        scope = root.get("scope")
        n = by_scope.get(scope, 0) if scope else 0
        out.append({"path": root.get("path"), "scope": scope, "projects": n,
                    "state": "scanned" if n > 0 else "empty"})
        if scope:
            seen.add(scope)
    # Scopes present in the data but with no matching declared root (e.g. legacy
    # sibling discovery) still get a row, so the selector has something honest.
    for s, n in sorted(by_scope.items()):
        if s not in seen and s != "(untagged)":
            out.append({"path": None, "scope": s, "projects": n, "state": "scanned"})
    return out


def _payload_audit(projects_out: list[dict], estate_out: dict) -> list[dict]:
    """Per-(project, scanner) size census. Flags oversized payloads and any
    scanner that hit its honest cap, so a runaway is visible in the report rather
    than only discovered when the whole feed fails to render."""
    anomalies: list[dict] = []

    def consider(project: str, scanner: str, payload) -> None:
        if not isinstance(payload, dict):
            return
        size = len(json.dumps(payload, default=str))
        truncated = bool(payload.get("truncated"))
        if size > PAYLOAD_ANOMALY_BYTES or truncated:
            anomalies.append({
                "project": project, "scanner": scanner, "bytes": size,
                "truncated": truncated,
            })

    for entry in projects_out:
        name = entry.get("name", "?")
        for key, val in entry.items():
            if key in ("name", "path", "scope"):
                continue
            consider(name, key, val)
    for key, val in (estate_out or {}).items():
        consider("(estate)", key, val)
    anomalies.sort(key=lambda a: -a["bytes"])
    return anomalies


def extract_embedded_data(html: str) -> str:
    """The JSON string the HTML viewer will parse, pulled back out of the written
    page. Raises ValueError if the markers are gone -- itself a broken report."""
    try:
        start = html.index(_DATA_OPEN) + len(_DATA_OPEN)
        end = html.index(_DATA_CLOSE, start)
    except ValueError as exc:
        raise ValueError("report.html: data markers not found -- template broken "
                         "or output truncated before the script body") from exc
    return html[start:end]


def validate_report(estate_text: str, html_text: str,
                    anomalies: list[dict] | None = None) -> list[str]:
    """Pure self-check: both the data feed and the report's embedded copy must be
    valid JSON. Returns human-readable violations (empty == clean). The testable
    core of :func:`_self_validate`.

    On a parse failure it names the largest payload from ``anomalies`` as the
    likely culprit -- the best available attribution for a truncated feed."""
    problems: list[str] = []
    try:
        json.loads(estate_text)
    except ValueError as exc:
        problems.append(f"data/estate.json does not parse: {exc}")
    culprit = ""
    if anomalies:
        top = anomalies[0]
        culprit = (f" -- largest payload is {top['scanner']} on {top['project']} "
                   f"({top['bytes']} bytes); suspect it first")
    try:
        json.loads(extract_embedded_data(html_text))
    except ValueError as exc:
        problems.append(f"report.html embedded DATA does not parse: {exc}{culprit}")
    return problems


def _self_validate(data_path: Path, report_path: Path,
                   anomalies: list[dict] | None) -> None:
    """Re-read what was just written and fail loud if it is not parseable JSON.
    A report you cannot parse fails its own job (Task B.2)."""
    problems = validate_report(
        data_path.read_text(encoding="utf-8"),
        report_path.read_text(encoding="utf-8"),
        anomalies,
    )
    if problems:
        raise RuntimeError("report self-check FAILED (the emitted governance "
                           "artifact is broken):\n  - " + "\n  - ".join(problems))


def _cached(relative_name: str):
    p = (DATA_DIR / relative_name)
    if p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
    return None


def _scan_one_project(proj: Path, per_project: list, resume: bool) -> dict:
    # `path` and `scope` are deposited facts, not decoration: the consumer builds
    # the project registry from this file and must never reach back to the
    # producer's disk to work out where a project lived or which root it sat
    # under (the mesh doctrine -- producers deposit facts, consumers read them).
    # `scope` comes from the producer's config root tag, so a flat estate needs no
    # folder reorg to be classifiable (DECISIONS 0012 / Task C.3).
    from . import config
    entry: dict = {
        "name": proj.name,
        "path": str(proj),
        "scope": config.scope_for_path(proj),
    }
    for mod in per_project:
        rel_name = f"{mod.NAME}/{proj.name}.json"
        data = _cached(rel_name) if resume else None
        if data is None:
            data = mod.scan(proj)
            write_json(rel_name, data)
        entry[mod.NAME] = data
    print(f"  scanned {proj.name}", flush=True)
    return entry


def build_estate(projects: list[Path], resume: bool = True,
                 with_estate: bool = True) -> dict:
    per_project = [m for m in SCANNERS if not m.ESTATE_LEVEL]
    # Some estate tools (e.g. estate_diff) consume the snapshots build produces,
    # so they must not run *inside* build -- they'd diff a stale pair.
    estate_level = [m for m in SCANNERS
                    if m.ESTATE_LEVEL and not getattr(m, "SKIP_IN_BUILD", False)]

    # Per-project scanning is I/O-bound on the mount, so run projects in
    # parallel threads (writes go to distinct files -- safe).
    projects_out: list[dict] = [{} for _ in projects]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_scan_one_project, p, per_project, resume): i
                   for i, p in enumerate(projects)}
        for fut in futures:
            projects_out[futures[fut]] = fut.result()

    estate_out: dict = {}
    if not with_estate:
        return {"projects": projects_out, "estate": estate_out}
    for mod in estate_level:
        rel_name = f"{mod.NAME}.json"
        data = _cached(rel_name) if resume else None
        if data is None:
            data = mod.scan_estate(projects)
            write_json(rel_name, data)
        estate_out[mod.NAME] = data

    from . import config as _config
    _git = toolkit_git_info()
    _machine = _config.machine()
    estate = {
        "generated_at": now_iso(),
        "toolkit_version": __version__,
        "toolkit_commit": _git["commit"],
        "toolkit_dirty": _git["dirty"],
        "estate_root": str(ESTATE_ROOT),
        # Who produced this bundle and under which tagged roots. The consumer
        # reads these instead of assuming a folder layout -- the layout differs on
        # every machine and matching one has never held. Named `estate_name`, not
        # `estate`: `estate` already means "the estate-level scan map" to the HTML
        # viewer, estate_diff and consume, and a key that means two things
        # depending on config is the kind of thing that bites at 2am.
        "estate_name": _machine.get("estate"),
        "producer_host": _machine.get("_hostname"),
        "roots": [{"path": str(e["path"]), "scope": e.get("scope")}
                  for e in _config.estate_roots_tagged()],
        # Oversized / capped scanner payloads, surfaced so a runaway is a visible
        # line in the report rather than a silent truncation (Task B.3).
        "anomalies": _payload_audit(projects_out, estate_out),
        # Task D (doc_provenance_coverage): a project's raw doc_count wildly out
        # of scale with the rest of the estate -- a payload/scale signal, kept
        # separate from `anomalies` (bytes-based) because the unit and the
        # question it answers are both different.
        "doc_anomalies": doc_census.out_of_band(projects_out),
        "projects": projects_out,
        "estate": estate_out,
    }
    # Per-root scope honesty, computed after projects so it can count them.
    estate["scope_summary"] = scope_summary(estate)
    write_json("estate.json", estate)
    _archive_snapshot(estate)
    return estate


def _archive_snapshot(estate: dict) -> None:
    """Deposit a dated copy of this build into data/history/ so estate_diff has
    a per-run trail to compare against. Append-only: never overwrites a prior
    day (same day rebuilds refresh that day's snapshot, which is fine)."""
    day = (estate.get("generated_at") or now_iso())[:10]
    snapshot_name = f"estate-{day}.json"
    write_json(f"history/{snapshot_name}", estate)
    write_json("history/latest.json", {
        "snapshot": snapshot_name,
        "generated_at": estate.get("generated_at"),
    })


def render_html(estate: dict) -> Path:
    payload = json.dumps(estate, default=str)
    html = _TEMPLATE.replace("/*__DATA__*/", payload)
    dest = TOOLKIT_ROOT / "report.html"
    dest.write_text(html, encoding="utf-8")
    return dest


def build_all(projects: list[Path], resume: bool = True) -> tuple[Path, Path]:
    estate = build_estate(projects, resume=resume, with_estate=True)
    report = render_html(estate)
    data_path = DATA_DIR / "estate.json"
    # Re-read from disk and confirm both artifacts parse. A truncated write looks
    # like a finished report until you try to use it -- so fail loud here instead.
    _self_validate(data_path, report, estate.get("anomalies"))
    return data_path, report


def scan_subset(projects: list[Path], resume: bool = True) -> None:
    """Per-project scan only (no estate roll-up, no render). Warms the cache in
    chunks so a later full build assembles quickly."""
    build_estate(projects, resume=resume, with_estate=False)


# --- architecture_census renderer (COWORK_BRIEF_architecture_census.md Task 3,
# DECISIONS 0030) ---------------------------------------------------------
#
# `architecture_census.census()` (a *scanner*, read-only, stdlib-only,
# `write_json`-only) emits facts. Turning those facts into prose-adjacent
# markdown is a deliberately separate step living here instead: a scanner
# that wrote into docs/ would break `auditor_readonly`, and this module is
# not in `registry.SCANNERS` so it is never asked to be read-only in that
# sense. `auditor_architecture_current` (Task 4) calls
# `render_architecture_shape` on a freshly-scanned payload and diffs the
# result against the committed file -- it never calls `write_architecture_
# shape`, which is the one function here allowed to touch disk.

ARCHITECTURE_SHAPE_RELPATH = "docs/_architecture_shape.md"

_DO_NOT_EDIT = (
    "<!-- GENERATED by l5gntools/scanners/architecture_census.py + "
    "l5gntools/report.py:render_architecture_shape -- DO NOT HAND-EDIT.\n"
    "     Regenerate with `python run.py render-architecture` after any "
    "change to routes, schema, scanners, the gate or the dependency wall.\n"
    "     Producing commit: {commit} -->\n"
)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |",
            "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _fmt_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else ""
    return str(value).replace("|", "\\|")


def render_architecture_shape(data: dict) -> str:
    """Pure function: `architecture_census.census()`'s payload -> the exact
    text of `docs/_architecture_shape.md`. Takes data, not a path and not a
    live scan, so the auditor and the human-run generator exercise the same
    function against payloads they each produced themselves -- neither one
    calls the other's I/O."""
    sections = data["sections"]
    commit = data.get("provenance", {}).get("commit") or "(unknown)"

    out: list[str] = [_DO_NOT_EDIT.format(commit=commit)]
    out.append("# The toolkit's own shape\n")
    out.append(
        "Generated, never hand-edited (DECISIONS 0030). `docs/ARCHITECTURE.md` "
        "keeps the rationale -- why the boundaries sit where they do -- and "
        "cites this document for shape: which modules exist, what the gate "
        "runs, which routes require what, which tables a module writes, the "
        "schema's shape, and the dependency wall. Every fact below was read "
        "from the tree by `l5gntools/scanners/architecture_census.py`; none "
        "of it was asserted.\n")

    # --- 1. Scanners ---------------------------------------------------
    out.append("## 1. Scanners\n")
    out.append(f"{len(sections['scanners'])} registered in `l5gntools/registry.py`.\n")
    rows = [[_fmt_cell(s["name"]), _fmt_cell(s["module"]),
            "estate" if s["estate_level"] else "project", _fmt_cell(s["safety"]),
            _fmt_cell(s["description"])]
           for s in sorted(sections["scanners"], key=lambda s: s["name"])]
    out.append(_md_table(["name", "module", "scope", "safety", "description"], rows) + "\n")

    # --- 2. Gate composition --------------------------------------------
    gate = sections["gate"]
    out.append("## 2. Gate composition\n")
    out.append(f"`verify.py`: **{gate['auditor_count']} auditors**, "
               f"**{gate['tester_count']} testers**.\n")
    out.append("Auditors:\n")
    for name in gate["auditors"]:
        out.append(f"- `{name}`")
    out.append("")
    out.append("Testers:\n")
    for name in gate["testers"]:
        out.append(f"- `{name}`")
    out.append("")

    # --- 3. Route table ---------------------------------------------------
    out.append("## 3. Route table -- `chronicler/review/app.py`\n")
    out.append(f"{len(sections['routes'])} routes declared directly in this file "
               "(routes contributed by a module's own router via "
               "`app.include_router` are not in this table -- they are not "
               "decorated in `app.py` itself).\n")
    rows = [[r["method"], f"`{r['path']}`", r["requires"]]
           for r in sorted(sections["routes"], key=lambda r: (r["path"] or "", r["method"]))]
    out.append(_md_table(["method", "path", "requires"], rows) + "\n")

    # --- 4. Write targets, per module ------------------------------------
    out.append("## 4. Write targets, per module\n")
    out.append(
        "Every module under `l5gntools/` or `chronicler/` that opens a "
        "connection or issues `.execute()`/`.executemany()`/`.executescript()` "
        "against one. `writes` is the set of tables a static `INSERT`/`UPDATE`/"
        "`DELETE`/`REPLACE` verb names; `unresolved_write_lines` names lines "
        "where a write is real but the target table is not a literal (an "
        "f-string, a module constant, a file read) -- reported, never "
        "silently dropped or guessed at.\n")
    wt = sorted(sections["write_targets"], key=lambda m: m["module"])
    rows = [[f"`{m['module']}`", _fmt_cell(sorted(m["writes"])),
            _fmt_cell(m["unresolved_write_lines"])]
           for m in wt]
    out.append(_md_table(["module", "writes", "unresolved_write_lines"], rows) + "\n")
    core = next((m for m in wt if m["module"] == "chronicler/review/core.py"), None)
    if core is not None:
        out.append(
            f"**The review endpoint** (`chronicler/review/core.py`) writes "
            f"`{{{', '.join(sorted(core['writes']))}}}` -- `review_queue` is "
            "not in that set. `ARCHITECTURE.md` §5 names `review_queue` as "
            "the endpoint's write target; the tree disagrees (finding A4, "
            "`investigation/2026-08-02_architecture-drift_claude_2-response.md`).\n")

    # --- 5. Schema shape ---------------------------------------------------
    schema = sections["schema"]
    out.append("## 5. Schema shape\n")
    for key, label in (("schema_sql", "schema.sql"), ("schema_frozen_sql", "schema_frozen.sql")):
        entry = schema[key]
        tables = entry["tables"] or {}
        out.append(f"### `{entry['path']}` -- {len(tables)} table(s)\n")
        for tname in sorted(tables):
            cols = ", ".join(f"{c['name']}" + (" PK" if c["pk"] else "")
                             for c in tables[tname])
            out.append(f"- **{tname}**: {cols}")
        out.append("")
    delta = schema["delta"]
    out.append("### Delta (`schema_frozen.sql` vs `schema.sql`)\n")
    out.append(f"- only in `schema_frozen.sql`: {_fmt_cell(delta['only_in_schema_frozen']) or '(none)'}")
    out.append(f"- only in `schema.sql`: {_fmt_cell(delta['only_in_schema']) or '(none)'}\n")
    if "render_log" in delta["only_in_schema_frozen"]:
        out.append(
            "`render_log` is present in `schema_frozen.sql` and absent from "
            "`schema.sql` -- a from-scratch build (`db.py` builds from "
            "`schema.sql`) has no `render_log` table until `render_md.py` "
            "creates it on first use (finding A12, "
            "`investigation/2026-08-02_architecture-drift_claude_2-response.md`).\n")

    # --- 6. Dependency wall -------------------------------------------------
    dw = sections["dependency_wall"]
    out.append("## 6. Dependency wall\n")
    out.append("Declared extras (`pyproject.toml`):\n")
    for extra, pkgs in sorted(dw["declared_extras"].items()):
        out.append(f"- `{extra}`: {_fmt_cell(pkgs) or '(none)'}")
    out.append("")
    rows = [[s["subsystem"], _fmt_cell(s["extras"]), _fmt_cell(s["declared_packages"]),
            _fmt_cell(s["third_party_imports_found"]), _fmt_cell(s["undeclared"]),
            _fmt_cell(s["unused_extras"])]
           for s in sorted(dw["subsystems"], key=lambda s: s["subsystem"])]
    out.append(_md_table(["subsystem", "extras", "declared", "imported",
                          "undeclared", "unused_extras"], rows) + "\n")

    # --- unparsed -----------------------------------------------------------
    out.append("## Unparsed\n")
    if data["unparsed"]:
        rows = [[f"`{u['module']}`", _fmt_cell(u["reason"])]
               for u in sorted(data["unparsed"], key=lambda u: u["module"])]
        out.append(_md_table(["module", "reason"], rows) + "\n")
    else:
        out.append("None -- every source file this census attempted to parse, parsed.\n")

    out.append(f"---\n\n_Provenance: toolkit commit `{commit}`"
               f"{', dirty working tree' if data['provenance'].get('dirty') else ''}._\n")
    return "\n".join(out) + "\n"


def write_architecture_shape(root: Path = TOOLKIT_ROOT) -> Path:
    """The human-run generator (Task 4: "It reports; the human runs the
    generator" -- the auditor never writes). Regenerates
    `data/architecture_census.json` and the rendered doc from the same scan,
    so the two can never drift from each other on disk."""
    from .scanners import architecture_census

    data = architecture_census.census(root)
    write_json("architecture_census.json", data)
    text = render_architecture_shape(data)
    dest = root / ARCHITECTURE_SHAPE_RELPATH
    dest.write_text(text, encoding="utf-8")
    return dest


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>L5GN Estate Report</title>
<style>
  :root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;
        --muted:#8b949e;--accent:#58a6ff;--warn:#f0883e;--bad:#f85149;--ok:#3fb950;}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
       background:var(--bg);color:var(--fg);padding:24px;}
  h1{font-size:22px;margin:0 0 4px} h2{font-size:16px;margin:24px 0 10px}
  .sub{color:var(--muted);margin-bottom:18px}
  .tabs{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin-bottom:16px}
  .tab{padding:8px 14px;cursor:pointer;color:var(--muted);border:1px solid transparent;
       border-bottom:none;border-radius:8px 8px 0 0}
  .tab.active{color:var(--fg);background:var(--panel);border-color:var(--line)}
  .view{display:none} .view.active{display:block}
  table{border-collapse:collapse;width:100%;margin:6px 0 18px;background:var(--panel);
        border:1px solid var(--line);border-radius:8px;overflow:hidden}
  th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
  th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
  tr:last-child td{border-bottom:none}
  code{background:#010409;padding:1px 5px;border-radius:4px;color:var(--accent)}
  .pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12px}
  .pill.ok{background:rgba(63,185,80,.15);color:var(--ok)}
  .pill.warn{background:rgba(240,136,62,.15);color:var(--warn)}
  .pill.bad{background:rgba(248,81,73,.15);color:var(--bad)}
  .muted{color:var(--muted)} .num{text-align:right;font-variant-numeric:tabular-nums}
  /* --- file census tree (Task D). Native <details> does the collapsing, so
     there is no toggle script to go wrong and no framework to fetch. --- */
  .risk{border:1px solid var(--bad);background:rgba(248,81,73,.07);border-radius:8px;
        padding:8px 14px;margin:0 0 20px}
  .risk>summary{cursor:pointer;list-style:none;display:flex;gap:12px;align-items:baseline;
                padding:4px 0;font-size:16px}
  .riskbody{padding-top:6px}
  .rgrp{border-top:1px solid var(--line);padding:2px 0}
  .rgrp>summary{cursor:pointer;list-style:none;display:flex;gap:10px;align-items:baseline;
                padding:4px 0}
  .rgrp .kids{max-height:340px;overflow:auto}
  .proj{background:var(--panel);border:1px solid var(--line);border-radius:8px;
        margin:0 0 10px;padding:6px 12px}
  .proj>summary{cursor:pointer;list-style:none;display:flex;gap:12px;align-items:baseline;
                padding:4px 0;font-weight:600}
  .tree{margin:8px 0 4px}
  .tree details{margin:0}
  .tree summary{cursor:pointer;list-style:none;display:flex;gap:10px;align-items:baseline;
                padding:2px 0}
  summary::-webkit-details-marker{display:none}
  .tw::before{content:'\25b8';color:var(--muted);display:inline-block;width:12px;flex:none}
  details[open]>summary>.tw::before{content:'\25be'}
  .row{display:flex;gap:10px;align-items:baseline;padding:2px 0 2px 22px}
  .kids{margin-left:5px;border-left:1px solid var(--line);padding-left:12px}
  .nm{flex:1;min-width:0;overflow-wrap:anywhere}
  .sz{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;font-size:12px}
  .massrow{padding:2px 0 2px 22px;display:flex;gap:10px;align-items:baseline;opacity:.8}
  .note{color:var(--warn);font-size:12px;padding:4px 0 4px 22px}
  .banner{border:1px solid var(--warn);background:rgba(240,136,62,.10);border-radius:8px;
          padding:10px 14px;margin:0 0 16px;font-size:13px}
  .banner b{color:var(--warn)}
  .critban{border:2px solid var(--bad);background:rgba(248,81,73,.12);border-radius:8px;
           padding:12px 16px;margin:0 0 16px;font-size:13px}
  .critban b{color:var(--bad)}
  .tierpill{font-weight:600}
  #scopebar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 12px;font-size:13px}
  #scopebar select{background:var(--panel);color:var(--fg);border:1px solid var(--line);
                   border-radius:6px;padding:4px 8px;font:inherit}
  .scopehon{color:var(--muted)} .scopehon .empty{color:var(--warn)}
  .caveat{color:var(--warn);font-size:12px}
  .exportban{border:2px solid var(--accent);background:rgba(88,166,255,.10);border-radius:8px;
             padding:10px 14px;margin:0 0 16px;font-size:13px}
  .exportban b{color:var(--accent)}
</style></head>
<body>
<h1>L5GN Estate Report</h1>
<div class="exportban"><b>Frozen export, not the live surface.</b> This file's data was
  embedded at build time and does not change until the next
  <code>python run.py build</code>. The live, always-current version of this report is a
  tab in the deck (<code>python run.py review</code>) -- reads <code>data/estate.json</code>
  fresh on every visit (COWORK_BRIEF_unified_app.md Task 3). This export exists because a
  file you can email or open with no application installed is a different, still useful,
  artefact (0027).</div>
<div class="sub" id="meta"></div>
<div id="critical"></div>
<div id="anomalies"></div>
<div id="scopebar"></div>
<div class="tabs" id="tabs"></div>
<div id="views"></div>
<script>
const DATA = /*__DATA__*/;
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function pill(t,c){return '<span class="pill '+c+'">'+esc(t)+'</span>';}
function table(h,rows){let s='<table><thead><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>';s+=rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('');return s+'</tbody></table>';}
document.getElementById('meta').textContent =
  'Generated '+DATA.generated_at+'  |  toolkit v'+DATA.toolkit_version+' ('+(DATA.toolkit_commit||'nogit')+(DATA.toolkit_dirty?'-dirty':'')+')  |  '+DATA.projects.length+' projects  |  '+DATA.estate_root;
// Payload anomalies (Task B.3): a runaway or capped scanner is a visible banner,
// not a surprise truncation. Silent when the estate is clean.
(function(){const a=DATA.anomalies||[];if(!a.length)return;
  const fmt=n=>{const u=['B','KB','MB'];let i=0,x=n;while(x>=1024&&i<u.length-1){x/=1024;i++;}return (i?x.toFixed(1):x)+' '+u[i];};
  const rows=a.map(x=>'<code>'+esc(x.scanner)+'</code> on <b>'+esc(x.project)+'</b> &mdash; '
    +fmt(x.bytes)+(x.truncated?' '+pill('capped','warn'):' '+pill('oversized','bad'))).join('<br>');
  document.getElementById('anomalies').innerHTML=
    '<div class="banner"><b>&#9888; Payload anomalies ('+a.length+')</b> &mdash; a scanner emitted an '
    +'unusually large or capped payload. Capped means honestly truncated; oversized means review the source.<br>'+rows+'</div>';})();
// --- Blast radius (Task A/B) ------------------------------------------------
function tierPill(t){const c=(t==='raw-write-prod'||t==='raw-write')?'bad'
  :t==='guarded-write'?'warn':'muted';
  return '<span class="pill '+c+' tierpill">'+esc(t)+'</span>';}
// UNCOMMITTED-CRITICAL: the single loudest thing the report can say, at the very
// top -- write-capable code with no commit behind it. Estate-wide, not scoped.
(function(){const rows=[];
  DATA.projects.forEach(p=>{const b=p.blast_radius;if(!b||!b.uncommitted_critical)return;
    b.uncommitted_critical.forEach(c=>rows.push([p.name,c]));});
  if(!rows.length)return;
  const rank={'raw-write-prod':4,'raw-write':3,'guarded-write':2};
  rows.sort((a,b)=>(rank[b[1].tier]||0)-(rank[a[1].tier]||0));
  const body=rows.map(r=>'<code>'+esc(r[0])+'</code> / <code>'+esc(r[1].path)+'</code> '
    +tierPill(r[1].tier)+' <span class="muted">'+esc(r[1].git_state)+'</span>').join('<br>');
  document.getElementById('critical').innerHTML=
    '<div class="critban"><b>&#9888; UNCOMMITTED-CRITICAL ('+rows.length+')</b> &mdash; '
    +'write-capable code with no commit behind it: the exact code that can mutate the '
    +'outside world, with no provenance in version history.<br>'+body+'</div>';})();
// --- Scope filter (governance Task A) ---------------------------------------
// One scan carries every scope; the *view* is filtered client-side, so switching
// between all / l5gn / mcf never re-scans. Choice held in memory only.
let activeScope='all', activeView='status';
function SP(){return activeScope==='all'?DATA.projects
  :DATA.projects.filter(p=>((p.scope||'(untagged)')===activeScope));}
function inScope(name){return SP().some(p=>p.name===name);}
function renderScopebar(){
  const sum=DATA.scope_summary||[];
  const scopes=[...new Set(DATA.projects.map(p=>p.scope||'(untagged)'))].sort();
  let opts='<option value="all">all scopes</option>'
    +scopes.map(s=>'<option value="'+esc(s)+'">'+esc(s)+'</option>').join('');
  // D1 scope honesty: each root reads scanned-N or empty-this-run, never "zero".
  const hon=sum.map(r=>'<span>'+esc(r.scope||'(untagged)')+': '
    +(r.state==='empty'?'<span class="empty">empty this run</span>'
      :('scanned, '+r.projects+' project'+(r.projects===1?'':'s')))+'</span>')
    .join(' &middot; ');
  document.getElementById('scopebar').innerHTML=
    '<label>Scope <select id="scopesel">'+opts+'</select></label>'
    +'<span class="scopehon">'+(hon||'single scope')+'</span>'
    +'<span id="caveat" class="caveat"></span>';
  document.getElementById('scopesel').onchange=e=>{activeScope=e.target.value;rescope();};
}
function updateCaveat(){
  // D2: counts are not comparable across scope views. When a filter is active,
  // say so, because a count dropping is the filter narrowing, not a cleanup.
  const c=document.getElementById('caveat');if(!c)return;
  c.innerHTML=activeScope==='all'?'':
    '&#9888; filtered to <b>'+esc(activeScope)+'</b> ('+SP().length
    +' of '+DATA.projects.length+' projects) &mdash; summary counts reflect this view, not the whole estate.';
}
function rescope(){for(const k in views){views[k].done=false;views[k].view.innerHTML='';}
  updateCaveat();select(activeView);}
const views={};
function addTab(id,label,render){
  const t=document.createElement('div');t.className='tab';t.textContent=label;t.onclick=()=>select(id);
  document.getElementById('tabs').append(t);
  const v=document.createElement('div');v.className='view';document.getElementById('views').append(v);
  views[id]={tab:t,view:v,render,done:false};
}
function select(id){activeView=id;for(const k in views){const on=k==id;views[k].tab.classList.toggle('active',on);views[k].view.classList.toggle('active',on);if(on&&!views[k].done){views[k].render(views[k].view);views[k].done=true;}}}

addTab('status','Git Status',v=>{
  const rows=((DATA.estate.estate_status||{}).rows||[]).filter(r=>inScope(r.project)).map(r=>{
    if(!r.is_git) return ['<b>'+esc(r.project)+'</b>',pill('not git','muted'),'','','','',''];
    const dirty=r.dirty_files>200?pill(r.dirty_files,'bad'):r.dirty_files>0?pill(r.dirty_files,'warn'):pill('clean','ok');
    return ['<b>'+esc(r.project)+'</b>','<code>'+esc(r.latest_hash)+'</code>',esc((r.latest_date||'').slice(0,10)),esc(r.branch),'<span class="num">'+r.commit_count+'</span>',dirty,esc((r.latest_subject||'').slice(0,70))];
  });
  v.innerHTML=table(['Project','Latest','Date','Branch','Commits','Working tree','Subject'],rows);
});
addTab('blast','Blast Radius',v=>{
  const rows=SP().map(p=>{const b=p.blast_radius||{};
    const fams=Object.entries(b.by_family||{}).sort((a,b2)=>b2[1]-a[1])
      .map(kv=>esc(kv[0])+':'+kv[1]).join(', ');
    const crit=(b.uncommitted_critical||[]).length;
    return [b.tier_rank||0,'<b>'+esc(p.name)+'</b>',tierPill(b.tier||'none'),
      '<span class="num">'+(b.hit_count||0)+'</span>',fams||'<span class="muted">—</span>',
      crit?pill(crit+' UNCOMMITTED-CRITICAL','bad'):(b.truncated?pill('capped','warn'):'')];})
    .sort((a,b2)=>b2[0]-a[0]).map(r=>r.slice(1));
  v.innerHTML='<div class="muted">Ranked by write blast radius &mdash; the loudest signal, '
    +'above file size. <b>raw-write-prod</b> = an ungated production write; <b>raw-write</b> = '
    +'ungated non-prod; <b>guarded-write</b> = a gate is present (presence only, never judged good); '
    +'unknown target env is ranked as prod. Verdicts and paths only &mdash; no script body is shown.</div>'
    +table(['Project','Tier','Signals','Families','Alarm'],rows);
});
addTab('code','Code Inventory',v=>{
  const rows=SP().map(p=>{const w=p.workspace_scanner||{};return ['<b>'+esc(p.name)+'</b>','<span class="num">'+(w.py_files!=null?w.py_files:'')+'</span>','<span class="num">'+(w.classes!=null?w.classes:'')+'</span>','<span class="num">'+(w.functions!=null?w.functions:'')+'</span>',esc((w.top_classes||[]).slice(0,8).join(', '))];});
  v.innerHTML=table(['Project','.py files','Classes','Functions','Sample classes'],rows);
});
// --- Files tab: the file census, browsable (Task D) -------------------------
// The at-risk set renders FIRST and outside the tree: "untracked and not
// ignored" is the thing worth seeing before anything else, and burying it
// inside a collapsed folder would be the same as not reporting it.
function fmtB(n){if(n==null)return '';const u=['B','KB','MB','GB','TB'];let i=0,x=n;
  while(x>=1024&&i<u.length-1){x/=1024;i++;}
  return (i===0?x:x.toFixed(x<10?1:0))+' '+u[i];}
function censusTree(c){
  const mk=n=>({name:n,dirs:{},files:[],mass:[],direct:0,dbytes:0,collapsed:false});
  const root=mk('.');
  function node(p){
    if(!p||p==='.')return root;
    let cur=root;
    for(const part of p.split('/')){if(!cur.dirs[part])cur.dirs[part]=mk(part);cur=cur.dirs[part];}
    return cur;
  }
  (c.directories||[]).forEach(d=>{const n=node(d.path);
    n.direct=d.files;n.dbytes=d.bytes;n.ext=d.ext;n.collapsed=!!d.depth_collapsed;});
  (c.files||[]).forEach(f=>{const i=f.path.lastIndexOf('/');
    node(i<0?'.':f.path.slice(0,i)).files.push(f);});
  (c.mass||[]).forEach(m=>{
    if(m.partial){const n=node(m.path);n.mass.push(Object.assign({},m,{name:'(ignored files here)'}));return;}
    const i=m.path.lastIndexOf('/');
    node(i<0?'.':m.path.slice(0,i)).mass.push(Object.assign({},m,{name:i<0?m.path:m.path.slice(i+1)}));
  });
  (function total(n){let f=n.direct,b=n.dbytes;
    n.mass.forEach(m=>{f+=m.files;b+=m.bytes;});
    Object.keys(n.dirs).forEach(k=>{const t=total(n.dirs[k]);f+=t.f;b+=t.b;});
    n.tf=f;n.tb=b;return {f:f,b:b};})(root);
  return root;
}
function renderNode(n,label,open){
  const kids=Object.keys(n.dirs).sort();
  let h='<details'+(open?' open':'')+'><summary><span class="tw"></span>'
       +'<span class="nm">'+esc(label)+'/</span><span class="sz">'
       +n.tf+' files &middot; '+fmtB(n.tb)+'</span></summary><div class="kids">';
  if(n.collapsed)h+='<div class="note">contains folded-in content from below the depth cap</div>';
  kids.forEach(k=>{h+=renderNode(n.dirs[k],k,false);});
  // Tier 3 rows: one line, never expandable -- there is nothing behind them.
  n.mass.forEach(m=>{h+='<div class="massrow"><span class="nm muted">'+esc(m.name)
    +(m.partial?'':'/')+'</span><span class="sz">'+m.files+' files &middot; '+fmtB(m.bytes)
    +'  '+pill(m.reason,m.reason==='ignored'?'muted':'warn')+'</span></div>';});
  n.files.forEach(f=>{const p=f.git==='untracked'?' '+pill('untracked','bad'):'';
    h+='<div class="row"><span class="nm">'+esc(f.name||f.path.split('/').pop())+p
      +'</span><span class="sz">'+fmtB(f.bytes)+'</span></div>';});
  if(!kids.length&&!n.mass.length&&!n.files.length)h+='<div class="note muted">(empty)</div>';
  return h+'</div></details>';
}
addTab('files','Files',v=>{
  const withCensus=SP().filter(p=>p.file_census);
  if(!withCensus.length){v.innerHTML='<p class="muted">No file_census data in this build. '
    +'Run <code>python run.py build --fresh</code>.</p>';return;}

  // The at-risk set is grouped by project + top-level directory. On a real
  // estate it runs to thousands of files concentrated in a handful of places
  // (one directory accounted for 3,599 of 3,673 in the first real build), and a
  // 3,673-row table is a list nobody reads -- which is the same failure as not
  // reporting it. Grouping is presentation only: every path is still here,
  // one expand away, and every count is exact.
  const groups={}; const rollups=[]; let riskFiles=0, riskBytes=0;
  withCensus.forEach(p=>{(p.file_census.at_risk||[]).forEach(a=>{
    if(a.rollup){rollups.push([p.name,a]);riskFiles+=a.files;riskBytes+=a.bytes;return;}
    const cut=a.path.indexOf('/');
    const dir=cut<0?'(project root)':a.path.slice(0,cut);
    const key=JSON.stringify([p.name,dir]);
    (groups[key]=groups[key]||{proj:p.name,dir:dir,files:[],bytes:0}).files.push(a);
    groups[key].bytes+=a.bytes; riskFiles++; riskBytes+=a.bytes;
  });});
  const glist=Object.keys(groups).map(k=>groups[k])
    .sort((a,b)=>b.files.length-a.files.length||b.bytes-a.bytes);
  const nogit=withCensus.filter(p=>p.file_census.at_risk_note);

  let h='<details class="risk" open><summary><span class="tw"></span>'
    +'<span class="nm"><b>At risk</b> &mdash; on disk, not in git</span><span class="sz">'
    +(riskFiles?riskFiles+' files &middot; '+fmtB(riskBytes)+' across '+glist.length+' location(s)'
              :'nothing at risk')+'</span></summary><div class="riskbody">'
    +'<div class="muted">Untracked and not ignored. Delete the folder and these are gone. '
    +'Grouped by directory and never truncated &mdash; expand a row for every path. '
    +'A vendored tree that is wholly unprotected shows as one exact rollup.</div>';
  if(!riskFiles&&!nogit.length)
    h+='<p>'+pill('clean','ok')+' every file is tracked or deliberately ignored.</p>';
  rollups.forEach(r=>{const a=r[1];
    h+='<div class="massrow"><span class="nm"><b>'+esc(r[0])+'</b> / <code>'+esc(a.path)
      +'/</code> '+pill('whole '+a.reason+' tree: '+a.files+' files','bad')
      +'</span><span class="sz">'+fmtB(a.bytes)+'</span></div>';});
  glist.forEach((g,i)=>{
    h+='<details class="rgrp" data-g="'+i+'"><summary><span class="tw"></span>'
      +'<span class="nm"><b>'+esc(g.proj)+'</b> / <code>'+esc(g.dir)
      +(g.dir==='(project root)'?'':'/')+'</code></span><span class="sz">'
      +g.files.length+' file'+(g.files.length===1?'':'s')+' &middot; '+fmtB(g.bytes)
      +'</span></summary><div class="kids" data-pending="1"></div></details>';});
  if(nogit.length)h+='<p>'+pill('not a git repository','bad')+' '
    +esc(nogit.map(p=>p.name).join(', '))+' &mdash; no file in these is in version control at all.</p>';
  h+='</div></details>';

  withCensus.forEach((p,i)=>{const c=p.file_census,s=c.summary||{};
    h+='<details class="proj" data-i="'+i+'"><summary><span class="tw"></span>'
      +'<span class="nm">'+esc(p.name)+'</span><span class="sz">'
      +(s.total_files||0)+' files &middot; '+fmtB(s.total_bytes)+' &middot; working set '
      +((s.working_set||{}).files||0)+' &middot; mass '+fmtB((s.mass||{}).bytes)
      +((s.at_risk||{}).files?'  '+pill((s.at_risk).files+' at risk','bad'):'')
      +'</span></summary><div class="tree" data-pending="1"></div></details>';});
  v.innerHTML=h;

  // Build each tree on first expand: eleven full trees up front is a lot of DOM
  // for a page whose whole point is that it opens instantly from a file:// URL.
  v.querySelectorAll('details.proj').forEach(d=>{
    d.addEventListener('toggle',()=>{
      const box=d.querySelector('.tree');
      if(!d.open||!box.dataset.pending)return;
      delete box.dataset.pending;
      const c=withCensus[+d.dataset.i].file_census;
      let inner=renderNode(censusTree(c),c.project||'.',true);
      if(c.truncated)inner='<div class="note">Per-file listing capped at '+c.file_cap
        +' of '+c.file_count+' working-set files. Directory totals below are complete; '
        +'the at-risk set above is complete.</div>'+inner;
      box.innerHTML=inner;
    });
  });
  // Same lazy contract for an at-risk group: one of them holds thousands of
  // rows, and paying for it before anyone clicks would undo the point.
  v.querySelectorAll('details.rgrp').forEach(d=>{
    d.addEventListener('toggle',()=>{
      const box=d.querySelector('.kids');
      if(!d.open||!box.dataset.pending)return;
      delete box.dataset.pending;
      const g=glist[+d.dataset.g];
      box.innerHTML=g.files.slice().sort((a,b)=>b.bytes-a.bytes).map(a=>
        '<div class="row"><span class="nm"><code>'+esc(a.path)+'</code></span>'
        +'<span class="sz">'+fmtB(a.bytes)+' &middot; '+esc((a.mtime||'').slice(0,10))
        +'</span></div>').join('');
    });
  });
});
// --- Docs tab: provenance-honest coverage (0026, doc_provenance_coverage) ---
// Every ratio here is authored/classified over AUTHORED documents only, with
// the generated count always shown beside it -- never a percentage over a
// denominator full of machine output (Task B). The grid (Task C) is coverage,
// not a score: no total column, no rank, no colour implying pass/fail.
const GRID_TYPES=['knowledge','adr','decisions','readme','claude_md','glossary',
  'intent','architecture','runbook','uat','plan','brief','report'];
addTab('docs','Docs',v=>{
  let h='';
  const oob=(DATA.doc_anomalies||[]).filter(a=>inScope(a.project));
  if(oob.length){
    const rows=oob.map(a=>'<b>'+esc(a.project)+'</b> &mdash; '+a.doc_count+' markdown files '
      +'(estate median '+a.median+', flagged above '+a.threshold+')').join('<br>');
    h+='<div class="banner"><b>&#9888; Out-of-band document count ('+oob.length+')</b> &mdash; '
      +'raw doc_count, not a documentation-quality signal: a project generating far more '
      +'markdown than the rest of the estate is worth knowing about in its own right.<br>'
      +rows+'</div>';
  }
  const rows=SP().map(p=>{const d=p.doc_census||{};
    const gen=d.generated_count||0;
    const genNote=gen?' <span class="muted">('+gen+' generated)</span>':'';
    return ['<b>'+esc(p.name)+'</b>',
      '<span class="num">'+(d.authored_count!=null?d.authored_count:(d.doc_count||0))+'</span>'+genNote,
      '<span class="num">'+(d.classified_count||0)+'</span>',
      (d.classified_pct||0)+'%',
      d.has_readme?pill('yes','ok'):pill('no','bad'),
      d.has_claude_md?pill('yes','ok'):pill('no','muted'),
      '<span class="num">'+(d.adr_files||0)+'</span>'];});
  h+=table(['Project','Authored docs','Classified','Classified %','README','CLAUDE.md','ADR files'],rows);

  // Coverage grid (Task C): project x document type, ticks and blanks over
  // authored documents only. No total, no rank -- see the note above.
  h+='<h2>Coverage <span class="muted">(authored documents, by type -- absence, not a score)</span></h2>';
  const gridRows=SP().map(p=>{const tally=(p.doc_census||{}).type_tally||{};
    return ['<b>'+esc(p.name)+'</b>',...GRID_TYPES.map(t=>tally[t]?pill(String(tally[t]),'ok'):'<span class="muted">&mdash;</span>')];});
  h+=table(['Project',...GRID_TYPES.map(esc)],gridRows);
  h+='<div class="muted">Rules: knowledge = stem contains "_knowledge" (case-insensitive, '
    +'unanchored); adr = an <code>adr</code> path segment; decisions = stem contains "DECISIONS"; '
    +'readme/claude_md/glossary = exact filename; intent/architecture/runbook (+playbook)/uat '
    +'(+checklist)/plan (+status)/brief/report = stem contains the marker word, unanchored. '
    +'"generated" = a directory segment starts with . or _, or is output/logs/AutoFiles.</div>';
  v.innerHTML=h;
});
addTab('hygiene','Hygiene',v=>{
  const rows=SP().map(p=>{const b=p.bloat_audit||{},e=p.env_scanner||{};
    const flags=(b.flags||[]).map(f=>pill(f,'warn')).join(' ')||pill('clean','ok');
    const susp=(e.secret_suspects||[]);const tracked=e.tracked_suspect_count||0;
    // TRACKED (committed secret) is the alarm -- surface it distinctly.
    const secpill=tracked?pill(tracked+' TRACKED','bad')
      :susp.length?pill(susp.length+' suspect file(s)','warn'):pill('none','ok');
    return ['<b>'+esc(p.name)+'</b>',b.has_gitignore?pill('yes','ok'):pill('no','bad'),'<span class="num">'+(b.tracked_bloat_paths||0)+'</span>',flags,secpill];});
  v.innerHTML=table(['Project','.gitignore','Bloat paths','Flags','Secret suspects'],rows);
});
addTab('dupes','Duplicates',v=>{
  const d=DATA.estate.duplicate_finder||{};
  // Estate-level data: filter each group to projects/locations in the active scope.
  const shared=(d.shared_filenames||[]).map(x=>{
    const ps=x.projects.filter(inScope);return ps.length>=2?Object.assign({},x,{projects:ps}):null;
  }).filter(Boolean);
  const ident=(d.identical_content||[]).map(x=>{
    const locs=x.locations.filter(l=>inScope(l.split('/')[0]));
    return new Set(locs.map(l=>l.split('/')[0])).size>=2?Object.assign({},x,{locations:locs,count:locs.length}):null;
  }).filter(Boolean);
  let h='<h2>Same filename across projects <span class="muted">('+shared.length+' groups'
    +(activeScope==='all'?'':', filtered')+')</span></h2>'
    +'<div class="muted">Labelled by content: <b>identical</b> = byte-for-byte copy (shared-toolkit or drift candidate); '
    +'<b>divergent</b> = same name, forked content.</div>';
  h+=table(['Filename','Content','Projects'],shared.map(x=>['<code>'+esc(x.filename)+'</code>',
    x.content==='divergent'?pill('divergent','warn'):pill('identical','ok'),esc(x.projects.join(', '))]));
  h+='<h2>Byte-identical files across projects <span class="muted">('+ident.length+' groups)</span></h2>';
  h+=table(['sha1','Copies','Locations'],ident.map(x=>['<code>'+esc(x.sha1)+'</code>','<span class="num">'+x.count+'</span>',esc(x.locations.join('  |  '))]));
  v.innerHTML=h;
});
addTab('todos','TODO / ADR / Decisions',v=>{
  const rows=SP().map(p=>{const t=p.todo_adr_scanner||{};
    const tags=Object.entries(t.markers_by_tag||{}).map(kv=>kv[0]+':'+kv[1]).join(', ');
    // Both decision conventions side by side: adr/NNNN files and DECISIONS.md
    // entries, the latter tier-counted (governance Task B).
    const tiers=Object.entries(t.decision_tiers||{})
      .sort((a,b)=>b[1]-a[1]).map(kv=>esc(kv[0])+':'+kv[1]).join(', ');
    return ['<b>'+esc(p.name)+'</b>','<span class="num">'+(t.marker_count||0)+'</span>',esc(tags),
      '<span class="num">'+(t.adr_count||0)+'</span>',
      '<span class="num">'+(t.decisions_count||0)+'</span>',tiers||'<span class="muted">—</span>'];});
  v.innerHTML=table(['Project','Markers','By tag','ADR files','DECISIONS entries','Decision tiers'],rows);
});
renderScopebar();
select('status');
</script>
</body></html>
"""
