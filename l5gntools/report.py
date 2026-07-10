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
from .common import DATA_DIR, ESTATE_ROOT, TOOLKIT_ROOT, now_iso, write_json
from .registry import SCANNERS


def _cached(relative_name: str):
    p = (DATA_DIR / relative_name)
    if p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
    return None


def _scan_one_project(proj: Path, per_project: list, resume: bool) -> dict:
    entry: dict = {"name": proj.name}
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
    estate_level = [m for m in SCANNERS if m.ESTATE_LEVEL]

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

    estate = {
        "generated_at": now_iso(),
        "toolkit_version": __version__,
        "estate_root": str(ESTATE_ROOT),
        "projects": projects_out,
        "estate": estate_out,
    }
    write_json("estate.json", estate)
    return estate


def render_html(estate: dict) -> Path:
    payload = json.dumps(estate, default=str)
    html = _TEMPLATE.replace("/*__DATA__*/", payload)
    dest = TOOLKIT_ROOT / "report.html"
    dest.write_text(html, encoding="utf-8")
    return dest


def build_all(projects: list[Path], resume: bool = True) -> tuple[Path, Path]:
    estate = build_estate(projects, resume=resume, with_estate=True)
    report = render_html(estate)
    return DATA_DIR / "estate.json", report


def scan_subset(projects: list[Path], resume: bool = True) -> None:
    """Per-project scan only (no estate roll-up, no render). Warms the cache in
    chunks so a later full build assembles quickly."""
    build_estate(projects, resume=resume, with_estate=False)


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
</style></head>
<body>
<h1>L5GN Estate Report</h1>
<div class="sub" id="meta"></div>
<div class="tabs" id="tabs"></div>
<div id="views"></div>
<script>
const DATA = /*__DATA__*/;
const esc=s=>String(s==null?'':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function pill(t,c){return '<span class="pill '+c+'">'+esc(t)+'</span>';}
function table(h,rows){let s='<table><thead><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>';s+=rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('');return s+'</tbody></table>';}
document.getElementById('meta').textContent =
  'Generated '+DATA.generated_at+'  |  toolkit v'+DATA.toolkit_version+'  |  '+DATA.projects.length+' projects  |  '+DATA.estate_root;
const views={};
function addTab(id,label,render){
  const t=document.createElement('div');t.className='tab';t.textContent=label;t.onclick=()=>select(id);
  document.getElementById('tabs').append(t);
  const v=document.createElement('div');v.className='view';document.getElementById('views').append(v);
  views[id]={tab:t,view:v,render,done:false};
}
function select(id){for(const k in views){const on=k==id;views[k].tab.classList.toggle('active',on);views[k].view.classList.toggle('active',on);if(on&&!views[k].done){views[k].render(views[k].view);views[k].done=true;}}}

addTab('status','Git Status',v=>{
  const rows=((DATA.estate.estate_status||{}).rows||[]).map(r=>{
    if(!r.is_git) return ['<b>'+esc(r.project)+'</b>',pill('not git','muted'),'','','','',''];
    const dirty=r.dirty_files>200?pill(r.dirty_files,'bad'):r.dirty_files>0?pill(r.dirty_files,'warn'):pill('clean','ok');
    return ['<b>'+esc(r.project)+'</b>','<code>'+esc(r.latest_hash)+'</code>',esc((r.latest_date||'').slice(0,10)),esc(r.branch),'<span class="num">'+r.commit_count+'</span>',dirty,esc((r.latest_subject||'').slice(0,70))];
  });
  v.innerHTML=table(['Project','Latest','Date','Branch','Commits','Working tree','Subject'],rows);
});
addTab('code','Code Inventory',v=>{
  const rows=DATA.projects.map(p=>{const w=p.workspace_scanner||{};return ['<b>'+esc(p.name)+'</b>','<span class="num">'+(w.py_files!=null?w.py_files:'')+'</span>','<span class="num">'+(w.classes!=null?w.classes:'')+'</span>','<span class="num">'+(w.functions!=null?w.functions:'')+'</span>',esc((w.top_classes||[]).slice(0,8).join(', '))];});
  v.innerHTML=table(['Project','.py files','Classes','Functions','Sample classes'],rows);
});
addTab('docs','Docs',v=>{
  const rows=DATA.projects.map(p=>{const d=p.doc_census||{};return ['<b>'+esc(p.name)+'</b>','<span class="num">'+(d.doc_count||0)+'</span>',d.has_readme?pill('yes','ok'):pill('no','bad'),d.has_claude_md?pill('yes','ok'):pill('no','muted'),'<span class="num">'+(d.adr_files||0)+'</span>'];});
  v.innerHTML=table(['Project','Docs','README','CLAUDE.md','ADR files'],rows);
});
addTab('hygiene','Hygiene',v=>{
  const rows=DATA.projects.map(p=>{const b=p.bloat_audit||{},e=p.env_scanner||{};
    const flags=(b.flags||[]).map(f=>pill(f,'warn')).join(' ')||pill('clean','ok');
    const sec=(e.secret_suspects||[]).length;const secpill=sec?pill(sec+' suspect file(s)','bad'):pill('none','ok');
    return ['<b>'+esc(p.name)+'</b>',b.has_gitignore?pill('yes','ok'):pill('no','bad'),'<span class="num">'+(b.tracked_bloat_paths||0)+'</span>',flags,secpill];});
  v.innerHTML=table(['Project','.gitignore','Bloat paths','Flags','Secret suspects'],rows);
});
addTab('dupes','Duplicates',v=>{
  const d=DATA.estate.duplicate_finder||{};
  let h='<h2>Same filename across projects <span class="muted">('+(d.shared_filename_groups||0)+' groups)</span></h2>';
  h+=table(['Filename','Projects'],(d.shared_filenames||[]).map(x=>['<code>'+esc(x.filename)+'</code>',esc(x.projects.join(', '))]));
  h+='<h2>Byte-identical files across projects <span class="muted">('+(d.identical_content_groups||0)+' groups)</span></h2>';
  h+=table(['sha1','Copies','Locations'],(d.identical_content||[]).map(x=>['<code>'+esc(x.sha1)+'</code>','<span class="num">'+x.count+'</span>',esc(x.locations.join('  |  '))]));
  v.innerHTML=h;
});
addTab('todos','TODO / ADR',v=>{
  const rows=DATA.projects.map(p=>{const t=p.todo_adr_scanner||{};const tags=Object.entries(t.markers_by_tag||{}).map(kv=>kv[0]+':'+kv[1]).join(', ');return ['<b>'+esc(p.name)+'</b>','<span class="num">'+(t.marker_count||0)+'</span>',esc(tags),'<span class="num">'+(t.adr_count||0)+'</span>'];});
  v.innerHTML=table(['Project','Markers','By tag','ADRs'],rows);
});
select('status');
</script>
</body></html>
"""
