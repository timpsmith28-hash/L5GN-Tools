/* The Estate report view -- COWORK_BRIEF_unified_app.md Task 3.
 *
 * Adapted from `l5gntools/report.py`'s `_TEMPLATE` (the standalone
 * `report.html` this view demotes from surface to export, per 0027). This
 * is NOT a verbatim move like Task 1's Time tab or Task 2's split: the
 * template was written to own the whole document (`document.body`, global
 * ids `#tabs` / `#views` / `#meta` / `#critical` / `#anomalies` /
 * `#scopebar`) because it was always a self-contained file. Inside the
 * deck those ids collide with the shell's own (`#tabs` is the module tab
 * strip in index.html) and its CSS classes (`.tab`, `.pill`, `table`)
 * would leak onto the rest of the page. Every rendering function's LOGIC
 * is unchanged; every id is renamed with an `rpt-` prefix and scoped to
 * this pane's own element, and the CSS is scoped under `.report-root` so
 * nothing here can style anything outside it.
 *
 * Data source: `GET /api/estate/report`, which re-reads `data/estate.json`
 * from disk on every request (`chronicler/review/estate_report.py`) --
 * never the cached `EstateData` object the Documents/Search/Time tabs use.
 * That is the whole point of this view existing: the exported
 * `report.html` is frozen at build time, this one is not.
 */
import { esc, jget, degraded } from "../shared.js";

const STYLE = `
.report-root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;
      --muted:#8b949e;--accent:#58a6ff;--warn:#f0883e;--bad:#f85149;--ok:#3fb950;
      font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      background:var(--bg);color:var(--fg);padding:16px;border-radius:8px;}
.report-root h2{font-size:16px;margin:24px 0 10px}
.report-root .sub{color:var(--muted);margin-bottom:18px}
.report-root .tabs{display:flex;gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);margin-bottom:16px}
.report-root .tab{padding:8px 14px;cursor:pointer;color:var(--muted);border:1px solid transparent;
     border-bottom:none;border-radius:8px 8px 0 0}
.report-root .tab.active{color:var(--fg);background:var(--panel);border-color:var(--line)}
.report-root .view{display:none} .report-root .view.active{display:block}
.report-root table{border-collapse:collapse;width:100%;margin:6px 0 18px;background:var(--panel);
      border:1px solid var(--line);border-radius:8px;overflow:hidden}
.report-root th,.report-root td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
.report-root th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.report-root tr:last-child td{border-bottom:none}
.report-root code{background:#010409;padding:1px 5px;border-radius:4px;color:var(--accent)}
.report-root .pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12px}
.report-root .pill.ok{background:rgba(63,185,80,.15);color:var(--ok)}
.report-root .pill.warn{background:rgba(240,136,62,.15);color:var(--warn)}
.report-root .pill.bad{background:rgba(248,81,73,.15);color:var(--bad)}
.report-root .muted{color:var(--muted)} .report-root .num{text-align:right;font-variant-numeric:tabular-nums}
.report-root .risk{border:1px solid var(--bad);background:rgba(248,81,73,.07);border-radius:8px;
      padding:8px 14px;margin:0 0 20px}
.report-root .risk>summary{cursor:pointer;list-style:none;display:flex;gap:12px;align-items:baseline;
      padding:4px 0;font-size:16px}
.report-root .riskbody{padding-top:6px}
.report-root .rgrp{border-top:1px solid var(--line);padding:2px 0}
.report-root .rgrp>summary{cursor:pointer;list-style:none;display:flex;gap:10px;align-items:baseline;
      padding:4px 0}
.report-root .rgrp .kids{max-height:340px;overflow:auto}
.report-root .proj{background:var(--panel);border:1px solid var(--line);border-radius:8px;
      margin:0 0 10px;padding:6px 12px}
.report-root .proj>summary{cursor:pointer;list-style:none;display:flex;gap:12px;align-items:baseline;
      padding:4px 0;font-weight:600}
.report-root .tree{margin:8px 0 4px}
.report-root .tree details{margin:0}
.report-root .tree summary{cursor:pointer;list-style:none;display:flex;gap:10px;align-items:baseline;
      padding:2px 0}
.report-root summary::-webkit-details-marker{display:none}
.report-root .tw::before{content:'\\25b8';color:var(--muted);display:inline-block;width:12px;flex:none}
.report-root details[open]>summary>.tw::before{content:'\\25be'}
.report-root .row{display:flex;gap:10px;align-items:baseline;padding:2px 0 2px 22px}
.report-root .kids{margin-left:5px;border-left:1px solid var(--line);padding-left:12px}
.report-root .nm{flex:1;min-width:0;overflow-wrap:anywhere}
.report-root .sz{color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;font-size:12px}
.report-root .massrow{padding:2px 0 2px 22px;display:flex;gap:10px;align-items:baseline;opacity:.8}
.report-root .note{color:var(--warn);font-size:12px;padding:4px 0 4px 22px}
.report-root .banner{border:1px solid var(--warn);background:rgba(240,136,62,.10);border-radius:8px;
      padding:10px 14px;margin:0 0 16px;font-size:13px}
.report-root .banner b{color:var(--warn)}
.report-root .critban{border:2px solid var(--bad);background:rgba(248,81,73,.12);border-radius:8px;
      padding:12px 16px;margin:0 0 16px;font-size:13px}
.report-root .critban b{color:var(--bad)}
.report-root .tierpill{font-weight:600}
.report-root .rpt-scopebar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 12px;font-size:13px}
.report-root .rpt-scopebar select{background:var(--panel);color:var(--fg);border:1px solid var(--line);
      border-radius:6px;padding:4px 8px;font:inherit}
.report-root .scopehon{color:var(--muted)} .report-root .scopehon .empty{color:var(--warn)}
.report-root .caveat{color:var(--warn);font-size:12px}
`;

function pill(t, c) { return '<span class="pill ' + c + '">' + esc(t) + '</span>'; }
function table(h, rows) {
  let s = '<table><thead><tr>' + h.map(x => '<th>' + x + '</th>').join('') + '</tr></thead><tbody>';
  s += rows.map(r => '<tr>' + r.map(c => '<td>' + c + '</td>').join('') + '</tr>').join('');
  return s + '</tbody></table>';
}
function fmtB(n) {
  if (n == null) return '';
  const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0, x = n;
  while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
  return (i === 0 ? x : x.toFixed(x < 10 ? 1 : 0)) + ' ' + u[i];
}
function tierPill(t) {
  const c = (t === 'raw-write-prod' || t === 'raw-write') ? 'bad'
    : t === 'guarded-write' ? 'warn' : 'muted';
  return '<span class="pill ' + c + ' tierpill">' + esc(t) + '</span>';
}

const GRID_TYPES = ['knowledge', 'adr', 'decisions', 'readme', 'claude_md', 'glossary',
  'intent', 'architecture', 'runbook', 'uat', 'plan', 'brief', 'report'];

function censusTree(c) {
  const mk = n => ({ name: n, dirs: {}, files: [], mass: [], direct: 0, dbytes: 0, collapsed: false });
  const root = mk('.');
  function node(p) {
    if (!p || p === '.') return root;
    let cur = root;
    for (const part of p.split('/')) { if (!cur.dirs[part]) cur.dirs[part] = mk(part); cur = cur.dirs[part]; }
    return cur;
  }
  (c.directories || []).forEach(d => {
    const n = node(d.path);
    n.direct = d.files; n.dbytes = d.bytes; n.ext = d.ext; n.collapsed = !!d.depth_collapsed;
  });
  (c.files || []).forEach(f => {
    const i = f.path.lastIndexOf('/');
    node(i < 0 ? '.' : f.path.slice(0, i)).files.push(f);
  });
  (c.mass || []).forEach(m => {
    if (m.partial) { const n = node(m.path); n.mass.push(Object.assign({}, m, { name: '(ignored files here)' })); return; }
    const i = m.path.lastIndexOf('/');
    node(i < 0 ? '.' : m.path.slice(0, i)).mass.push(Object.assign({}, m, { name: i < 0 ? m.path : m.path.slice(i + 1) }));
  });
  (function total(n) {
    let f = n.direct, b = n.dbytes;
    n.mass.forEach(m => { f += m.files; b += m.bytes; });
    Object.keys(n.dirs).forEach(k => { const t = total(n.dirs[k]); f += t.f; b += t.b; });
    n.tf = f; n.tb = b; return { f: f, b: b };
  })(root);
  return root;
}

function renderNode(n, label, open) {
  const kids = Object.keys(n.dirs).sort();
  let h = '<details' + (open ? ' open' : '') + '><summary><span class="tw"></span>'
    + '<span class="nm">' + esc(label) + '/</span><span class="sz">'
    + n.tf + ' files &middot; ' + fmtB(n.tb) + '</span></summary><div class="kids">';
  if (n.collapsed) h += '<div class="note">contains folded-in content from below the depth cap</div>';
  kids.forEach(k => { h += renderNode(n.dirs[k], k, false); });
  n.mass.forEach(m => {
    h += '<div class="massrow"><span class="nm muted">' + esc(m.name)
      + (m.partial ? '' : '/') + '</span><span class="sz">' + m.files + ' files &middot; ' + fmtB(m.bytes)
      + '  ' + pill(m.reason, m.reason === 'ignored' ? 'muted' : 'warn') + '</span></div>';
  });
  n.files.forEach(f => {
    const p = f.git === 'untracked' ? ' ' + pill('untracked', 'bad') : '';
    h += '<div class="row"><span class="nm">' + esc(f.name || f.path.split('/').pop()) + p
      + '</span><span class="sz">' + fmtB(f.bytes) + '</span></div>';
  });
  if (!kids.length && !n.mass.length && !n.files.length) h += '<div class="note muted">(empty)</div>';
  return h + '</div></details>';
}

/* The whole thing, built once per pane activation against one DATA payload.
   `root` is this view's own container (a child of the shell's pane element,
   never the pane element itself, so mount() can drop a fresh instance in on
   reload without fighting leftover DOM from a previous fetch). */
function renderReport(root, DATA) {
  root.innerHTML = `
    <div class="sub" id="rpt-meta"></div>
    <div id="rpt-critical"></div>
    <div id="rpt-anomalies"></div>
    <div class="rpt-scopebar" id="rpt-scopebar"></div>
    <div class="tabs" id="rpt-tabs"></div>
    <div id="rpt-views"></div>`;

  const $ = sel => root.querySelector(sel);

  $('#rpt-meta').textContent =
    'Generated ' + DATA.generated_at + '  |  toolkit v' + DATA.toolkit_version + ' ('
    + (DATA.toolkit_commit || 'nogit') + (DATA.toolkit_dirty ? '-dirty' : '') + ')  |  '
    + DATA.projects.length + ' projects  |  ' + DATA.estate_root;

  // Payload anomalies (Task B.3): a runaway or capped scanner is a visible
  // banner, not a surprise truncation. Silent when the estate is clean.
  (function () {
    const a = DATA.anomalies || []; if (!a.length) return;
    const fmt = n => { const u = ['B', 'KB', 'MB']; let i = 0, x = n; while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; } return (i ? x.toFixed(1) : x) + ' ' + u[i]; };
    const rows = a.map(x => '<code>' + esc(x.scanner) + '</code> on <b>' + esc(x.project) + '</b> &mdash; '
      + fmt(x.bytes) + (x.truncated ? ' ' + pill('capped', 'warn') : ' ' + pill('oversized', 'bad'))).join('<br>');
    $('#rpt-anomalies').innerHTML =
      '<div class="banner"><b>&#9888; Payload anomalies (' + a.length + ')</b> &mdash; a scanner emitted an '
      + 'unusually large or capped payload. Capped means honestly truncated; oversized means review the source.<br>' + rows + '</div>';
  })();

  // UNCOMMITTED-CRITICAL: the single loudest thing the report can say, at the
  // very top -- write-capable code with no commit behind it. Estate-wide.
  (function () {
    const rows = [];
    DATA.projects.forEach(p => {
      const b = p.blast_radius; if (!b || !b.uncommitted_critical) return;
      b.uncommitted_critical.forEach(c => rows.push([p.name, c]));
    });
    if (!rows.length) return;
    const rank = { 'raw-write-prod': 4, 'raw-write': 3, 'guarded-write': 2 };
    rows.sort((a, b) => (rank[b[1].tier] || 0) - (rank[a[1].tier] || 0));
    const body = rows.map(r => '<code>' + esc(r[0]) + '</code> / <code>' + esc(r[1].path) + '</code> '
      + tierPill(r[1].tier) + ' <span class="muted">' + esc(r[1].git_state) + '</span>').join('<br>');
    $('#rpt-critical').innerHTML =
      '<div class="critban"><b>&#9888; UNCOMMITTED-CRITICAL (' + rows.length + ')</b> &mdash; '
      + 'write-capable code with no commit behind it: the exact code that can mutate the '
      + 'outside world, with no provenance in version history.<br>' + body + '</div>';
  })();

  // Scope filter (governance Task A): one scan carries every scope, the VIEW
  // is filtered client-side, so switching all/l5gn/mcf never re-scans.
  let activeScope = 'all', activeView = 'status';
  function SP() { return activeScope === 'all' ? DATA.projects : DATA.projects.filter(p => ((p.scope || '(untagged)') === activeScope)); }
  function inScope(name) { return SP().some(p => p.name === name); }

  function renderScopebar() {
    const sum = DATA.scope_summary || [];
    const scopes = [...new Set(DATA.projects.map(p => p.scope || '(untagged)'))].sort();
    let opts = '<option value="all">all scopes</option>'
      + scopes.map(s => '<option value="' + esc(s) + '">' + esc(s) + '</option>').join('');
    const hon = sum.map(r => '<span>' + esc(r.scope || '(untagged)') + ': '
      + (r.state === 'empty' ? '<span class="empty">empty this run</span>'
        : ('scanned, ' + r.projects + ' project' + (r.projects === 1 ? '' : 's'))) + '</span>')
      .join(' &middot; ');
    $('#rpt-scopebar').innerHTML =
      '<label>Scope <select id="rpt-scopesel">' + opts + '</select></label>'
      + '<span class="scopehon">' + (hon || 'single scope') + '</span>'
      + '<span id="rpt-caveat" class="caveat"></span>';
    $('#rpt-scopesel').onchange = e => { activeScope = e.target.value; rescope(); };
  }
  function updateCaveat() {
    const c = $('#rpt-caveat'); if (!c) return;
    c.innerHTML = activeScope === 'all' ? '' :
      '&#9888; filtered to <b>' + esc(activeScope) + '</b> (' + SP().length
      + ' of ' + DATA.projects.length + ' projects) &mdash; summary counts reflect this view, not the whole estate.';
  }
  function rescope() { for (const k in views) { views[k].done = false; views[k].view.innerHTML = ''; } updateCaveat(); select(activeView); }

  const views = {};
  function addTab(id, label, render) {
    const t = document.createElement('div'); t.className = 'tab'; t.textContent = label; t.onclick = () => select(id);
    $('#rpt-tabs').append(t);
    const v = document.createElement('div'); v.className = 'view'; $('#rpt-views').append(v);
    views[id] = { tab: t, view: v, render, done: false };
  }
  function select(id) {
    activeView = id;
    for (const k in views) {
      const on = k == id;
      views[k].tab.classList.toggle('active', on);
      views[k].view.classList.toggle('active', on);
      if (on && !views[k].done) { views[k].render(views[k].view); views[k].done = true; }
    }
  }

  addTab('status', 'Git Status', v => {
    const rows = ((DATA.estate.estate_status || {}).rows || []).filter(r => inScope(r.project)).map(r => {
      if (!r.is_git) return ['<b>' + esc(r.project) + '</b>', pill('not git', 'muted'), '', '', '', '', ''];
      const dirty = r.dirty_files > 200 ? pill(r.dirty_files, 'bad') : r.dirty_files > 0 ? pill(r.dirty_files, 'warn') : pill('clean', 'ok');
      return ['<b>' + esc(r.project) + '</b>', '<code>' + esc(r.latest_hash) + '</code>', esc((r.latest_date || '').slice(0, 10)), esc(r.branch), '<span class="num">' + r.commit_count + '</span>', dirty, esc((r.latest_subject || '').slice(0, 70))];
    });
    v.innerHTML = table(['Project', 'Latest', 'Date', 'Branch', 'Commits', 'Working tree', 'Subject'], rows);
  });

  addTab('blast', 'Blast Radius', v => {
    const rows = SP().map(p => {
      const b = p.blast_radius || {};
      const fams = Object.entries(b.by_family || {}).sort((a, b2) => b2[1] - a[1]).map(kv => esc(kv[0]) + ':' + kv[1]).join(', ');
      const crit = (b.uncommitted_critical || []).length;
      return [b.tier_rank || 0, '<b>' + esc(p.name) + '</b>', tierPill(b.tier || 'none'),
      '<span class="num">' + (b.hit_count || 0) + '</span>', fams || '<span class="muted">—</span>',
      crit ? pill(crit + ' UNCOMMITTED-CRITICAL', 'bad') : (b.truncated ? pill('capped', 'warn') : '')];
    }).sort((a, b2) => b2[0] - a[0]).map(r => r.slice(1));
    v.innerHTML = '<div class="muted">Ranked by write blast radius &mdash; the loudest signal, '
      + 'above file size. <b>raw-write-prod</b> = an ungated production write; <b>raw-write</b> = '
      + 'ungated non-prod; <b>guarded-write</b> = a gate is present (presence only, never judged good); '
      + 'unknown target env is ranked as prod. Verdicts and paths only &mdash; no script body is shown.</div>'
      + table(['Project', 'Tier', 'Signals', 'Families', 'Alarm'], rows);
  });

  addTab('code', 'Code Inventory', v => {
    const rows = SP().map(p => {
      const w = p.workspace_scanner || {};
      return ['<b>' + esc(p.name) + '</b>', '<span class="num">' + (w.py_files != null ? w.py_files : '') + '</span>', '<span class="num">' + (w.classes != null ? w.classes : '') + '</span>', '<span class="num">' + (w.functions != null ? w.functions : '') + '</span>', esc((w.top_classes || []).slice(0, 8).join(', '))];
    });
    v.innerHTML = table(['Project', '.py files', 'Classes', 'Functions', 'Sample classes'], rows);
  });

  addTab('files', 'Files', v => {
    const withCensus = SP().filter(p => p.file_census);
    if (!withCensus.length) { v.innerHTML = '<p class="muted">No file_census data in this build. Run <code>python run.py build --fresh</code>.</p>'; return; }

    const groups = {}; const rollups = []; let riskFiles = 0, riskBytes = 0;
    withCensus.forEach(p => {
      (p.file_census.at_risk || []).forEach(a => {
        if (a.rollup) { rollups.push([p.name, a]); riskFiles += a.files; riskBytes += a.bytes; return; }
        const cut = a.path.indexOf('/');
        const dir = cut < 0 ? '(project root)' : a.path.slice(0, cut);
        const key = JSON.stringify([p.name, dir]);
        (groups[key] = groups[key] || { proj: p.name, dir: dir, files: [], bytes: 0 }).files.push(a);
        groups[key].bytes += a.bytes; riskFiles++; riskBytes += a.bytes;
      });
    });
    const glist = Object.keys(groups).map(k => groups[k]).sort((a, b) => b.files.length - a.files.length || b.bytes - a.bytes);
    const nogit = withCensus.filter(p => p.file_census.at_risk_note);

    let h = '<details class="risk" open><summary><span class="tw"></span>'
      + '<span class="nm"><b>At risk</b> &mdash; on disk, not in git</span><span class="sz">'
      + (riskFiles ? riskFiles + ' files &middot; ' + fmtB(riskBytes) + ' across ' + glist.length + ' location(s)' : 'nothing at risk') + '</span></summary><div class="riskbody">'
      + '<div class="muted">Untracked and not ignored. Delete the folder and these are gone. '
      + 'Grouped by directory and never truncated &mdash; expand a row for every path. '
      + 'A vendored tree that is wholly unprotected shows as one exact rollup.</div>';
    if (!riskFiles && !nogit.length) h += '<p>' + pill('clean', 'ok') + ' every file is tracked or deliberately ignored.</p>';
    rollups.forEach(r => {
      const a = r[1];
      h += '<div class="massrow"><span class="nm"><b>' + esc(r[0]) + '</b> / <code>' + esc(a.path)
        + '/</code> ' + pill('whole ' + a.reason + ' tree: ' + a.files + ' files', 'bad')
        + '</span><span class="sz">' + fmtB(a.bytes) + '</span></div>';
    });
    glist.forEach((g, i) => {
      h += '<details class="rgrp" data-g="' + i + '"><summary><span class="tw"></span>'
        + '<span class="nm"><b>' + esc(g.proj) + '</b> / <code>' + esc(g.dir)
        + (g.dir === '(project root)' ? '' : '/') + '</code></span><span class="sz">'
        + g.files.length + ' file' + (g.files.length === 1 ? '' : 's') + ' &middot; ' + fmtB(g.bytes)
        + '</span></summary><div class="kids" data-pending="1"></div></details>';
    });
    if (nogit.length) h += '<p>' + pill('not a git repository', 'bad') + ' ' + esc(nogit.map(p => p.name).join(', ')) + ' &mdash; no file in these is in version control at all.</p>';
    h += '</div></details>';

    withCensus.forEach((p, i) => {
      const c = p.file_census, s = c.summary || {};
      h += '<details class="proj" data-i="' + i + '"><summary><span class="tw"></span>'
        + '<span class="nm">' + esc(p.name) + '</span><span class="sz">'
        + (s.total_files || 0) + ' files &middot; ' + fmtB(s.total_bytes) + ' &middot; working set '
        + ((s.working_set || {}).files || 0) + ' &middot; mass ' + fmtB((s.mass || {}).bytes)
        + ((s.at_risk || {}).files ? '  ' + pill((s.at_risk).files + ' at risk', 'bad') : '')
        + '</span></summary><div class="tree" data-pending="1"></div></details>';
    });
    v.innerHTML = h;

    v.querySelectorAll('details.proj').forEach(d => {
      d.addEventListener('toggle', () => {
        const box = d.querySelector('.tree');
        if (!d.open || !box.dataset.pending) return;
        delete box.dataset.pending;
        const c = withCensus[+d.dataset.i].file_census;
        let inner = renderNode(censusTree(c), c.project || '.', true);
        if (c.truncated) inner = '<div class="note">Per-file listing capped at ' + c.file_cap
          + ' of ' + c.file_count + ' working-set files. Directory totals below are complete; '
          + 'the at-risk set above is complete.</div>' + inner;
        box.innerHTML = inner;
      });
    });
    v.querySelectorAll('details.rgrp').forEach(d => {
      d.addEventListener('toggle', () => {
        const box = d.querySelector('.kids');
        if (!d.open || !box.dataset.pending) return;
        delete box.dataset.pending;
        const g = glist[+d.dataset.g];
        box.innerHTML = g.files.slice().sort((a, b) => b.bytes - a.bytes).map(a =>
          '<div class="row"><span class="nm"><code>' + esc(a.path) + '</code></span>'
          + '<span class="sz">' + fmtB(a.bytes) + ' &middot; ' + esc((a.mtime || '').slice(0, 10))
          + '</span></div>').join('');
      });
    });
  });

  addTab('docs', 'Docs', v => {
    let h = '';
    const oob = (DATA.doc_anomalies || []).filter(a => inScope(a.project));
    if (oob.length) {
      const rows = oob.map(a => '<b>' + esc(a.project) + '</b> &mdash; ' + a.doc_count + ' markdown files '
        + '(estate median ' + a.median + ', flagged above ' + a.threshold + ')').join('<br>');
      h += '<div class="banner"><b>&#9888; Out-of-band document count (' + oob.length + ')</b> &mdash; '
        + 'raw doc_count, not a documentation-quality signal: a project generating far more '
        + 'markdown than the rest of the estate is worth knowing about in its own right.<br>'
        + rows + '</div>';
    }
    const rows = SP().map(p => {
      const d = p.doc_census || {};
      const gen = d.generated_count || 0;
      const genNote = gen ? ' <span class="muted">(' + gen + ' generated)</span>' : '';
      return ['<b>' + esc(p.name) + '</b>',
        '<span class="num">' + (d.authored_count != null ? d.authored_count : (d.doc_count || 0)) + '</span>' + genNote,
        '<span class="num">' + (d.classified_count || 0) + '</span>',
      (d.classified_pct || 0) + '%',
      d.has_readme ? pill('yes', 'ok') : pill('no', 'bad'),
      d.has_claude_md ? pill('yes', 'ok') : pill('no', 'muted'),
        '<span class="num">' + (d.adr_files || 0) + '</span>'];
    });
    h += table(['Project', 'Authored docs', 'Classified', 'Classified %', 'README', 'CLAUDE.md', 'ADR files'], rows);

    h += '<h2>Coverage <span class="muted">(authored documents, by type -- absence, not a score)</span></h2>';
    const gridRows = SP().map(p => {
      const tally = (p.doc_census || {}).type_tally || {};
      return ['<b>' + esc(p.name) + '</b>', ...GRID_TYPES.map(t => tally[t] ? pill(String(tally[t]), 'ok') : '<span class="muted">&mdash;</span>')];
    });
    h += table(['Project', ...GRID_TYPES.map(esc)], gridRows);
    h += '<div class="muted">Rules: knowledge = stem contains "_knowledge" (case-insensitive, '
      + 'unanchored); adr = an <code>adr</code> path segment; decisions = stem contains "DECISIONS"; '
      + 'readme/claude_md/glossary = exact filename; intent/architecture/runbook (+playbook)/uat '
      + '(+checklist)/plan (+status)/brief/report = stem contains the marker word, unanchored. '
      + '"generated" = a directory segment starts with . or _, or is output/logs/AutoFiles.</div>';
    v.innerHTML = h;
  });

  addTab('hygiene', 'Hygiene', v => {
    const rows = SP().map(p => {
      const b = p.bloat_audit || {}, e = p.env_scanner || {};
      const flags = (b.flags || []).map(f => pill(f, 'warn')).join(' ') || pill('clean', 'ok');
      const susp = (e.secret_suspects || []); const tracked = e.tracked_suspect_count || 0;
      const secpill = tracked ? pill(tracked + ' TRACKED', 'bad')
        : susp.length ? pill(susp.length + ' suspect file(s)', 'warn') : pill('none', 'ok');
      return ['<b>' + esc(p.name) + '</b>', b.has_gitignore ? pill('yes', 'ok') : pill('no', 'bad'), '<span class="num">' + (b.tracked_bloat_paths || 0) + '</span>', flags, secpill];
    });
    v.innerHTML = table(['Project', '.gitignore', 'Bloat paths', 'Flags', 'Secret suspects'], rows);
  });

  addTab('dupes', 'Duplicates', v => {
    const d = DATA.estate.duplicate_finder || {};
    const shared = (d.shared_filenames || []).map(x => {
      const ps = x.projects.filter(inScope); return ps.length >= 2 ? Object.assign({}, x, { projects: ps }) : null;
    }).filter(Boolean);
    const ident = (d.identical_content || []).map(x => {
      const locs = x.locations.filter(l => inScope(l.split('/')[0]));
      return new Set(locs.map(l => l.split('/')[0])).size >= 2 ? Object.assign({}, x, { locations: locs, count: locs.length }) : null;
    }).filter(Boolean);
    let h = '<h2>Same filename across projects <span class="muted">(' + shared.length + ' groups'
      + (activeScope === 'all' ? '' : ', filtered') + ')</span></h2>'
      + '<div class="muted">Labelled by content: <b>identical</b> = byte-for-byte copy (shared-toolkit or drift candidate); '
      + '<b>divergent</b> = same name, forked content.</div>';
    h += table(['Filename', 'Content', 'Projects'], shared.map(x => ['<code>' + esc(x.filename) + '</code>',
    x.content === 'divergent' ? pill('divergent', 'warn') : pill('identical', 'ok'), esc(x.projects.join(', '))]));
    h += '<h2>Byte-identical files across projects <span class="muted">(' + ident.length + ' groups)</span></h2>';
    h += table(['sha1', 'Copies', 'Locations'], ident.map(x => ['<code>' + esc(x.sha1) + '</code>', '<span class="num">' + x.count + '</span>', esc(x.locations.join('  |  '))]));
    v.innerHTML = h;
  });

  addTab('todos', 'TODO / ADR / Decisions', v => {
    const rows = SP().map(p => {
      const t = p.todo_adr_scanner || {};
      const tags = Object.entries(t.markers_by_tag || {}).map(kv => kv[0] + ':' + kv[1]).join(', ');
      const tiers = Object.entries(t.decision_tiers || {}).sort((a, b) => b[1] - a[1]).map(kv => esc(kv[0]) + ':' + kv[1]).join(', ');
      return ['<b>' + esc(p.name) + '</b>', '<span class="num">' + (t.marker_count || 0) + '</span>', esc(tags),
        '<span class="num">' + (t.adr_count || 0) + '</span>',
        '<span class="num">' + (t.decisions_count || 0) + '</span>', tiers || '<span class="muted">—</span>'];
    });
    v.innerHTML = table(['Project', 'Markers', 'By tag', 'ADR files', 'DECISIONS entries', 'Decision tiers'], rows);
  });

  renderScopebar();
  select('status');
}

let styleInjected = false;

export async function mount(el) {
  if (!styleInjected) {
    const style = document.createElement("style");
    style.textContent = STYLE;
    document.head.appendChild(style);
    styleInjected = true;
  }
  el.innerHTML = `<div class="report-root"><div class="empty">Loading…</div></div>`;
  const container = el.querySelector(".report-root");
  try {
    const data = await jget("/api/estate/report");
    renderReport(container, data);
  } catch (e) {
    degraded(el, `Estate report unavailable: ${e.message}`);
  }
}
