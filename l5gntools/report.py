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
        "projects": projects_out,
        "estate": estate_out,
    }
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
  'Generated '+DATA.generated_at+'  |  toolkit v'+DATA.toolkit_version+' ('+(DATA.toolkit_commit||'nogit')+(DATA.toolkit_dirty?'-dirty':'')+')  |  '+DATA.projects.length+' projects  |  '+DATA.estate_root;
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
  const withCensus=DATA.projects.filter(p=>p.file_census);
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
