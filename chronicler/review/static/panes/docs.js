/* The Documents pane -- COWORK_BRIEF_unified_app.md Task 2. Moved verbatim.
 * `selectDocProject` and `openDoc` are called from this file's own
 * generated markup (onclick) and from search.js's jumpToDoc, so both
 * are exported for the direct call and attached to `window` for the
 * inline handlers -- the same dual exposure every cross-pane function
 * in this split needs. */
import { esc, jget, degraded } from "../shared.js";

export let ESTATE_PROJECTS = [];
export let DOC_PROJECT = null;

export async function loadEstateProjects() {
  const nav = document.getElementById("doc-nav");
  try {
    ESTATE_PROJECTS = await jget("/api/estate/projects");
  } catch (e) {
    degraded(nav, `Documents unavailable: ${e.message}`);
    return;
  }
  const scope = document.getElementById("scope");
  ESTATE_PROJECTS.forEach(p => {
    const o = document.createElement("option");
    o.value = p.project; o.textContent = p.project;
    scope.appendChild(o);
  });
  // A project with zero authored documents is listed and disabled rather than
  // hidden: "Armory has nothing written down" is a finding, not an absence.
  nav.innerHTML = ESTATE_PROJECTS.map(p => `
    <div class="nav-item${p.authored_count ? '' : ' nav-empty-proj'}"
         data-proj="${esc(p.project)}"
         ${p.authored_count ? `onclick="selectDocProject('${esc(p.project)}')"` : ''}
         style="${p.authored_count ? '' : 'opacity:.45;cursor:default'}"
         title="${p.authored_count} authored, ${p.generated_count ?? 0} generated">
      <span>${esc(p.project)}${p.has_knowledge ? ' <span class="badge" style="border-color:#1a7f37;color:#1a7f37">knowledge</span>' : ''}
        <br><span class="nav-crumb">${p.is_git ? 'git' : 'no git'} · ${p.generated_count ?? 0} generated</span></span>
      <span class="nav-count">${p.authored_count}</span>
    </div>`).join("");
}

export async function selectDocProject(project) {
  DOC_PROJECT = project;
  document.querySelectorAll("#doc-nav .nav-item").forEach(el =>
    el.classList.toggle("active", el.dataset.proj === project));
  const pane = document.getElementById("doc-pane");
  pane.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    const data = await jget(`/api/estate/documents?project=${encodeURIComponent(project)}`);
    pane.innerHTML = `<div class="doc-groups">` + data.groups.map(g => `
      <div class="doc-group-head ${g.doc_type === 'knowledge' ? 'knowledge' : ''}">${esc(g.doc_type)} · ${g.count}</div>
      ${g.documents.map(d => `
        <div class="doc-row" data-id="${esc(d.id)}" onclick="openDoc('${esc(d.id)}')">
          <span>${esc(d.title || d.path)}<br><span class="meta">${esc(d.path)}</span></span>
          <span class="p">${d.words ?? "?"} w</span>
        </div>`).join("")}`).join("") +
      `</div><div id="doc-view" style="margin-top:1rem;display:none"></div>`;
  } catch (e) {
    degraded(pane, `Could not list documents: ${e.message}`);
  }
}

export async function openDoc(docId) {
  document.querySelectorAll(".doc-row").forEach(el =>
    el.classList.toggle("active", el.dataset.id === docId));
  const view = document.getElementById("doc-view");
  if (!view) return;
  view.style.display = "block";
  view.innerHTML = `<div class="empty">Reading from disk…</div>`;
  try {
    const d = await jget(`/api/estate/document?doc_id=${encodeURIComponent(docId)}`);
    view.innerHTML = `<div class="doc-head">
        <div><strong>${esc(d.title || d.path)}</strong>
          <div class="meta">${esc(d.project)} · ${esc(d.path)} · ${esc(d.doc_type)}
            · ${d.bytes_on_disk} bytes on disk now</div></div>
        <div class="meta">read at render time (0027) · not cached</div>
      </div>
      ${d.truncated ? `<div class="degraded" style="margin-bottom:.6rem">${esc(d.note)}</div>` : ''}
      <pre></pre>`;
    // textContent, not innerHTML: the document is text and stays text.
    view.querySelector("pre").textContent = d.text;
    view.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    view.innerHTML = `<div class="degraded"><strong>Refused${e.reason ? ` (${esc(e.reason)})` : ''}:</strong>
      ${esc(String(e.message || e))}</div>`;
  }
}

Object.assign(window, { selectDocProject, openDoc });
