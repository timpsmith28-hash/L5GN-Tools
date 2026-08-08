/* The Time view -- the first pane to move off the hardcoded path.
 *
 * COWORK_BRIEF_unified_app.md Task 1: one tab migrated in the same commit as
 * the registry, six left as they were. This is that tab. It is a native ES
 * module loaded by the shell on first activation -- no bundler, no framework,
 * no build step (working rule; the shell imports it with a dynamic `import()`
 * and nothing compiles it on the way).
 *
 * Task 1 had the shell pass `esc`/`jget`/`degraded` into `mount()` as
 * arguments rather than importing them, specifically so Task 1 could stop at
 * one migrated tab without also building the shared-helpers module. Task 2
 * built that module (`static/shared.js`) for the rest of the split, so this
 * file now imports from it like every pane does -- the change promised in
 * that original comment, and no change to the code below it.
 *
 * Every render function here moved verbatim from index.html's inline script.
 * Nothing was rewritten in the move -- a migration that also refactors cannot
 * tell you which change broke the tab.
 */
import { esc, jget, degraded } from "../shared.js";

const fmtDate = iso => (iso ? String(iso).slice(0, 10) : "—");

function timelineHtml(tl, esc) {
  if (!tl.has_axis) {
    return `<div class="degraded">${esc(tl.note || "No history to plot.")}</div>` +
      nohistHtml(tl.without_history, esc);
  }
  return `<div class="card">
    <h3>Estate timeline — ${fmtDate(tl.axis_start)} to ${fmtDate(tl.axis_end)}
        (${tl.axis_span_days} days)</h3>
    <div class="tl-axis"><span></span><span class="ends">
      <span>${fmtDate(tl.axis_start)}</span><span>${fmtDate(tl.axis_end)}</span></span></div>
    ${tl.projects.map(p => `
      <div class="tl-row">
        <span class="tl-name" title="${esc(p.project)}">${esc(p.project)}</span>
        <span class="tl-track" title="${fmtDate(p.first_commit)} → ${fmtDate(p.last_commit)} · ${p.span_days} days · ${p.commit_count} commits">
          <span class="tl-bar${p.dirty_files ? ' dirty' : ''}"
                style="left:${(p.offset * 100).toFixed(2)}%;width:${(p.width * 100).toFixed(2)}%"></span>
        </span>
      </div>`).join("")}
  </div>` + spansHtml(tl.projects, esc) + nohistHtml(tl.without_history, esc);
}

function spansHtml(projects, esc) {
  return `<div class="card"><h3>Per project</h3>
    <table class="delta"><tr><th>project</th><th>first</th><th>last</th>
      <th>days</th><th>commits</th><th>contributors</th></tr>
    ${projects.map(p => `<tr>
      <td>${esc(p.project)}${p.dirty_files ? ` <span class="dirty" title="${p.dirty_files} dirty files at build time">●</span>` : ''}</td>
      <td>${fmtDate(p.first_commit)}</td><td>${fmtDate(p.last_commit)}</td>
      <td>${p.span_days}</td><td>${p.commit_count ?? "?"}</td>
      <td>${esc((p.contributors || []).map(c => c.commits == null ? `${c.author} (latest only)` : `${c.author} ${c.commits}`).join(", "))}</td>
    </tr>`).join("")}</table></div>`;
}

/* Absence is stated, never interpolated -- the same rule estate_time.py is
   written to, carried onto the surface that renders it. */
function nohistHtml(absent, esc) {
  if (!absent || !absent.length) return "";
  return `<div class="card"><h3>No history — stated, not guessed</h3>
    ${absent.map(p => `<div class="nohist"><strong>${esc(p.project)}</strong> — ${esc(p.reason)}</div>`).join("")}
    <div class="meta" style="margin-top:.4rem">These are not given a span from
      file mtimes. A fabricated window is worse than an absent one.</div></div>`;
}

function deltaHtml(d, esc) {
  if (d.status !== "ok") {
    return `<div class="card"><h3>What changed since the last build</h3>
      <div class="degraded">${esc(d.note || d.status)} (${d.snapshots_available ?? 0} snapshot(s) in ${esc(d.history_dir || "history")})</div></div>`;
  }
  const stamp = b => `${esc(b.file || "?")} — ${esc(b.generated_at || "undated")} @ ${esc(b.toolkit_commit || "?")}${b.toolkit_dirty ? " (dirty)" : ""}`;
  const s = d.summary || {};
  return `<div class="card">
    <h3>What changed since the last build</h3>
    <div class="meta">Comparing <strong>${stamp(d.from_build || {})}</strong>
      → <strong>${stamp(d.to_build || {})}</strong></div>
    <p class="note">${s.projects_changed} project(s) changed ·
      ${s.projects_added} added · ${s.projects_removed} removed ·
      ${s.new_commits} new commit(s)</p>
    ${d.projects_added.length ? `<div class="note">Appeared: ${esc(d.projects_added.join(", "))}</div>` : ""}
    ${d.projects_removed.length ? `<div class="note">Vanished: ${esc(d.projects_removed.join(", "))}</div>` : ""}
    ${d.changed.length ? `<table class="delta">
      <tr><th>project</th><th>git</th><th>documents</th></tr>
      ${d.changed.map(c => `<tr>
        <td>${esc(c.project)}</td>
        <td>${c.git ? `${c.git.new_commit_count} new commit(s)` : "—"}</td>
        <td>${c.docs ? esc(["added", "removed", "changed"].map(k =>
    (c.docs[k] || []).length ? `${k}: ${(c.docs[k] || []).length}` : "").filter(Boolean).join(" · ") || "—") : "—"}</td>
      </tr>`).join("")}</table>` : `<div class="empty">Nothing moved between these two builds.</div>`}
  </div>`;
}

/* The view contract: `mount(el)`, called once, the first time the tab is
   opened. `el` is the module's own pane element, created by the shell from
   the descriptor's id -- the view owns everything inside it and touches
   nothing outside it. */
export async function mount(el) {
  el.innerHTML = `<div style="max-width:68rem;margin-inline:auto">
    <div id="time-view"><div class="empty">Loading…</div></div></div>`;
  const view = el.querySelector("#time-view");
  try {
    const [tl, delta] = await Promise.all([
      jget("/api/estate/timeline"), jget("/api/estate/changes")]);
    view.innerHTML = timelineHtml(tl, esc) + deltaHtml(delta, esc);
  } catch (e) {
    degraded(view, `Time views unavailable: ${e.message}`);
  }
}
