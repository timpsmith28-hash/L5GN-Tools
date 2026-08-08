/* The Review queue pane -- COWORK_BRIEF_unified_app.md Task 2.
 *
 * Moved verbatim out of the monolithic <script>. This pane stays
 * `legacy` in the module registry (its routes are still inline in
 * app.py) -- Task 2 only splits the FRONT END into ES modules; it does
 * not migrate any more backend routes than Task 1's one. So this file
 * is loaded directly by app.js (a static <script type="module"> import),
 * not through the descriptor-driven mount() path Task 1 built for the
 * Time tab -- there is no #pane-queue creation step, the markup already
 * exists in index.html.
 *
 * Its interactive handlers (selectProject, toggleAll, confirmBatch,
 * assignOther, rejectOne) are referenced by `onclick=".."` in HTML
 * strings this module itself renders into innerHTML, and the browser
 * resolves those against the global scope -- so they are attached to
 * `window` at the bottom of this file, same as every other pane. That
 * is the one deliberate seam in an otherwise faithful move: before the
 * split, every function in the old single <script> was implicitly
 * global; now each module says so explicitly, function by function.
 */
import { esc, jget } from "../shared.js";

let PROJECTS = [];
let CURRENT = null;   // selected project_id
let BATCH = [];        // current batch rows

function countLabel(counts) {
  const parts = [];
  if (counts.suggestion) parts.push(`${counts.suggestion} suggest`);
  if (counts.ambiguous) parts.push(`${counts.ambiguous} ambig`);
  if (counts.downgrade) parts.push(`${counts.downgrade} down`);
  return parts.join(" · ");
}

function navHtml() {
  if (!PROJECTS.length) return `<div class="nav-empty">Nothing pending. 🎉</div>`;
  return PROJECTS.map(p => `
    <div class="nav-item${p.project_id === CURRENT ? ' active' : ''}" data-pid="${esc(p.project_id)}" onclick="selectProject('${esc(p.project_id)}')">
      <span>${esc(p.canonical_name)}<br><span class="nav-crumb">${esc(p.hierarchy)}</span></span>
      <span class="nav-count" title="${esc(countLabel(p.counts))}">${p.total}</span>
    </div>`).join("");
}

export async function loadProjects(preserveSelection) {
  const s = document.getElementById("status");
  try {
    // jget unwraps the 503 the queue routes return on a machine with no vault,
    // so "this rig has no thread store" reads as an explanation rather than a
    // JavaScript error about .length of undefined.
    const projects = await jget("/api/queue/projects");
    PROJECTS = projects;
    document.getElementById("nav").innerHTML = navHtml();
    s.textContent = `${projects.length} project(s) with pending threads`;
    if (preserveSelection && CURRENT && projects.some(p => p.project_id === CURRENT)) {
      return; // batch already showing, counts refreshed
    }
    if (!projects.some(p => p.project_id === CURRENT)) {
      CURRENT = null;
      document.getElementById("batch").innerHTML =
        projects.length
          ? `<div class="empty">Pick a project on the left to see its pending batch.</div>`
          : `<div class="empty">Nothing pending. 🎉</div>`;
    }
  } catch (e) {
    if (e.status === 503) {
      s.innerHTML = `<span class="dirty">Review queue unavailable on this machine.</span>
        <span class="meta">${esc(String(e.message || e))}</span>`;
      document.getElementById("nav").innerHTML =
        `<div class="nav-empty">No vault here.</div>`;
      document.getElementById("batch").innerHTML =
        `<div class="degraded">This rig has no thread store, so there is nothing
          to rule on. The Documents, Search and Time tabs work regardless —
          they need only <code>data/estate.json</code>.</div>`;
      return;
    }
    s.innerHTML = `<span class="err">Failed to load projects: ${esc(String(e.message || e))}</span>`;
  }
}

// The row's OTHER scored candidate, if it has one. Viewing a project as the
// rival, the other side is the primary candidate, and vice versa. Null for
// project_link / link_downgrade rows, which only ever carry one candidate --
// so this button never offers a target relink didn't actually score.
function otherCandidate(it) {
  const other = it.is_rival ? it.candidate_project : it.rival_project;
  if (!other || other === CURRENT) return null;
  const crumb = it.is_rival ? it.candidate_hierarchy : it.rival_hierarchy;
  const known = PROJECTS.find(p => p.project_id === other);
  const name = known ? known.canonical_name
    : (crumb ? crumb.split(">").pop().trim() : other);
  return { id: other, name, crumb: crumb || other };
}

function itemHtml(it) {
  const created = it.thread_created_at ? esc(it.thread_created_at) : "undated";
  const other = otherCandidate(it);
  const otherBtn = other
    ? `<button class="small btn-other" title="Rule this thread to ${esc(other.crumb)}"
         onclick="assignOther(this,'${esc(other.id)}')">→ ${esc(other.name)}</button>`
    : "";
  return `<div class="item${it.is_rival ? ' rival' : ''}" data-thread="${esc(it.thread_id)}">
    <input type="checkbox" class="pick" ${it.is_rival ? '' : 'checked'}>
    <div class="item-body">
      <div class="row1">
        ${it.is_rival ? '<span class="badge rival">rival candidate</span>' : `<span class="badge">${esc(it.type)}</span>`}
        <span class="badge">${esc(it.account || "account?")}</span>
        <span class="badge">conf ${it.confidence == null ? "—" : Number(it.confidence).toFixed(2)}</span>
        <span class="meta">${created}</span>
      </div>
      <div class="title">${esc(it.title || "(untitled)")}</div>
      <div class="meta">thread ${esc(it.thread_id)}${it.current_link ? ` · current link: ${esc(it.current_link)} (${esc(it.current_confidence || "")})` : ""}</div>
      ${it.note ? `<div class="note">${esc(it.note)}</div>` : ""}
      ${it.snippet ? `<div class="snippet">${esc(it.snippet)}</div>` : ""}
      <div class="item-actions">
        <button class="small" onclick="rejectOne(this)">Not this project</button>
        ${otherBtn}
        <span class="result"></span>
      </div>
    </div>
  </div>`;
}

function batchHeadHtml(project) {
  return `<div id="batch-head">
    <h2>${esc(project.canonical_name)} <span style="opacity:.6;font-weight:400">— ${esc(project.hierarchy)}</span></h2>
    <div class="batch-actions">
      <label><input type="checkbox" id="select-all" checked onchange="toggleAll(this.checked)"> select all</label>
      <button class="primary" onclick="confirmBatch(this)">Confirm (accept ticked)</button>
    </div>
  </div>`;
}

async function selectProject(pid) {
  CURRENT = pid;
  document.querySelectorAll(".nav-item").forEach(el =>
    el.classList.toggle("active", el.dataset.pid === pid));
  const el = document.getElementById("batch");
  el.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    BATCH = await fetch(`/api/pending?project=${encodeURIComponent(pid)}`).then(r => r.json());
    const project = PROJECTS.find(p => p.project_id === pid) ||
      { project_id: pid, canonical_name: pid, hierarchy: pid };
    el.innerHTML = batchHeadHtml(project) +
      (BATCH.length ? BATCH.map(itemHtml).join("")
        : `<div class="empty">Nothing left in this batch. 🎉</div>`);
  } catch (e) {
    el.innerHTML = `<span class="err">Failed to load batch: ${esc(String(e))}</span>`;
  }
}

function toggleAll(checked) {
  document.querySelectorAll(".item .pick").forEach(cb => cb.checked = checked);
}

async function confirmBatch(btn) {
  const ticked = [...document.querySelectorAll(".item")]
    .filter(el => el.querySelector(".pick").checked)
    .map(el => el.dataset.thread);
  if (!ticked.length) return;
  btn.disabled = true;
  const s = document.getElementById("status");
  try {
    const res = await fetch("/api/rule/batch", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rulings: ticked.map(thread_id => ({ thread_id, project_id: CURRENT })) }),
    });
    const results = await res.json();
    if (!res.ok) throw new Error(results.detail || res.status);
    const failed = results.filter(r => !r.ok);
    const okIds = new Set(results.filter(r => r.ok).map(r => r.thread_id));
    document.querySelectorAll(".item").forEach(el => {
      if (okIds.has(el.dataset.thread)) el.remove();
    });
    s.textContent = failed.length
      ? `${okIds.size} accepted, ${failed.length} failed: ${failed.map(f => `${f.thread_id} (${f.error})`).join("; ")}`
      : `${okIds.size} accepted.`;
    await loadProjects(true);
    if (!document.querySelectorAll("#batch .item").length && CURRENT) {
      document.getElementById("batch").innerHTML =
        `<div class="empty">Nothing left in this batch. 🎉</div>`;
    }
  } catch (e) {
    s.innerHTML = `<span class="err">Batch accept failed: ${esc(String(e.message || e))}</span>`;
  } finally {
    btn.disabled = false;
  }
}

// Accept the thread against its OTHER candidate, from inside this batch.
// Uses the existing single-thread /api/rule -- same validated write, same
// project_confidence='manual', so the thread drops out of BOTH candidates'
// batches at once rather than needing a second visit to the other project.
async function assignOther(btn, pid) {
  const item = btn.closest(".item");
  const thread_id = item.dataset.thread;
  const out = item.querySelector(".result");
  btn.disabled = true; out.textContent = "…";
  try {
    const res = await fetch("/api/rule", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id, project_id: pid }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    item.remove();
    document.getElementById("status").textContent = `Ruled to ${pid}.`;
    await loadProjects(true);
    if (!document.querySelectorAll("#batch .item").length) {
      document.getElementById("batch").innerHTML =
        `<div class="empty">Nothing left in this batch. 🎉</div>`;
    }
  } catch (e) {
    out.innerHTML = `<span class="err">✗ ${esc(String(e.message || e))}</span>`;
    btn.disabled = false;
  }
}

async function rejectOne(btn) {
  const item = btn.closest(".item");
  const thread_id = item.dataset.thread;
  const out = item.querySelector(".result");
  btn.disabled = true; out.textContent = "…";
  try {
    const res = await fetch("/api/reject", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id, project_id: CURRENT }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    item.remove();
    await loadProjects(true);
    if (!document.querySelectorAll("#batch .item").length) {
      document.getElementById("batch").innerHTML =
        `<div class="empty">Nothing left in this batch. 🎉</div>`;
    }
  } catch (e) {
    out.innerHTML = `<span class="err">✗ ${esc(String(e.message || e))}</span>`;
    btn.disabled = false;
  }
}

Object.assign(window, { selectProject, toggleAll, confirmBatch, assignOther, rejectOne });
