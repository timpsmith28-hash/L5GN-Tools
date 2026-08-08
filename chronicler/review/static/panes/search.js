/* The Search pane -- COWORK_BRIEF_unified_app.md Task 2. Moved verbatim.
 *
 * `jumpToDoc` crosses into the Documents pane (switch tabs, then load a
 * project and open a document there). It calls `window.showPane` (the
 * shell, app.js) and imports `selectDocProject`/`openDoc` directly from
 * docs.js -- an ordinary ES import, not a window lookup, because those
 * two are this pane's actual dependency rather than a handler the DOM
 * needs to find by name. */
import { esc, jget } from "../shared.js";
import { selectDocProject, openDoc, DOC_PROJECT } from "./docs.js";

// The server marks matches with \x02 / \x03 rather than HTML, so the highlight
// is applied here AFTER escaping -- a document containing "<script>" cannot
// smuggle markup through a snippet.
function snippetHtml(s) {
  return esc(s).replace(/\x02/g, "<mark>").replace(/\x03/g, "</mark>");
}

async function runSearch() {
  const q = document.getElementById("q").value.trim();
  const project = document.getElementById("scope").value;
  const out = document.getElementById("search-results");
  const st = document.getElementById("search-status");
  if (!q) { out.innerHTML = ""; st.textContent = ""; return; }
  out.innerHTML = `<div class="empty">Searching…</div>`;
  try {
    const url = `/api/estate/search?q=${encodeURIComponent(q)}` +
      (project ? `&project=${encodeURIComponent(project)}` : "");
    const r = await jget(url);
    const bits = [`${r.count} result(s)`, `engine: ${r.engine}`,
      project ? `scope: ${project}` : "scope: whole estate"];
    st.innerHTML = esc(bits.join(" · ")) +
      (r.notice ? `<br><span class="dirty">${esc(r.notice)}</span>` : "") +
      (r.error ? `<br><span class="err">${esc(r.error)}</span>` : "");
    out.innerHTML = r.results.length ? r.results.map(h => `
      <div class="hit ${h.is_knowledge ? 'knowledge' : ''}" onclick="jumpToDoc('${esc(h.project)}','${esc(h.id)}')">
        <div class="row1">
          <span class="badge">${esc(h.doc_type)}</span>
          <span class="badge">${esc(h.project)}</span>
          <span class="title">${esc(h.title || h.path)}</span>
        </div>
        <div class="meta">${esc(h.path)}</div>
        <div class="snippet">${snippetHtml(h.snippet)}</div>
      </div>`).join("")
      : `<div class="empty">Nothing matched. That is itself a finding if you
           are sure you wrote it down.</div>`;
  } catch (e) {
    st.innerHTML = `<span class="err">Search failed: ${esc(String(e.message || e))}</span>`;
    out.innerHTML = "";
  }
}

async function jumpToDoc(project, docId) {
  window.showPane("docs");
  if (DOC_PROJECT !== project) await selectDocProject(project);
  openDoc(docId);
}

Object.assign(window, { runSearch, jumpToDoc });
