/* The shell -- COWORK_BRIEF_unified_app.md Task 2.
 *
 * Everything that used to be the monolithic inline <script> in index.html
 * now lives here plus `shared.js` plus one file per pane in `panes/` and
 * `views/`. This file keeps only what is genuinely shell-level: the
 * build stamp, the module registry (Task 1: /api/modules, the tab strip,
 * degradation), the hash router, and boot().
 *
 * Panes are imported for their side effect of attaching their DOM-facing
 * handlers to `window` (see each pane file's own header comment for why).
 * `queue` and `docs` load eagerly on boot regardless of which tab is
 * active, exactly as the old script did; the rest lazy-load the first
 * time their tab is shown, via each pane's own `activate()`.
 */
import { esc, jget, ago, degraded } from "./shared.js";
import { loadProjects as loadQueueProjects } from "./panes/queue.js";
import { loadEstateProjects } from "./panes/docs.js";
import "./panes/search.js";
import "./panes/uat.js";
import { activate as activateBoard } from "./panes/board.js";
import { activate as activateCurator } from "./panes/curator.js";

/* ---- the module registry, client side (Task 1) ----
   MODULES is whatever /api/modules said, including each module's resolved
   degradation. The strip is drawn from it; a registered module's pane is
   created from it; a legacy module's pane is the markup already in
   index.html. */
let MODULES = [];
const MOUNTED = {};   // module id -> true once its view module has run

function moduleById(id) { return MODULES.find(m => m.id === id) || null; }

function currentHash() {
  return (location.hash || "").replace(/^#/, "");
}

async function loadModules() {
  const tabs = document.getElementById("tabs");
  let payload;
  try { payload = await jget("/api/modules"); }
  catch (e) {
    // No strip means no way to reach any pane, so say so where the strip was.
    tabs.innerHTML = `<div class="degraded">Module registry unavailable: ${esc(e.message)}</div>`;
    return;
  }
  MODULES = payload.modules || [];
  tabs.innerHTML = MODULES.map(m => {
    // A degraded tab is still a tab you can open -- it opens onto the named
    // cause. Hiding it would make a missing dependency look like a missing
    // feature, which is the class of "plausible wrong answer" INTENT §5 names.
    const why = (m.unmet || []).map(u => u.detail).join(" · ");
    return `<div class="tab${m.available ? "" : " unmet"}" data-pane="${esc(m.id)}"` +
      `${m.available ? "" : ` title="${esc(why)}"`}>${esc(m.label)}` +
      `${m.available ? "" : ' <span aria-hidden="true">◦</span>'}</div>`;
  }).join("");
  tabs.querySelectorAll(".tab").forEach(t =>
    t.addEventListener("click", () => showPane(t.dataset.pane)));
  // A registered module owns its pane element; the shell only creates it.
  for (const m of MODULES) {
    if (m.view && !document.getElementById(`pane-${m.id}`)) {
      const sec = document.createElement("section");
      sec.id = `pane-${m.id}`;
      sec.className = "pane";
      document.body.appendChild(sec);
    }
  }
  // Deep-link / reload: a hash naming a real module wins over the default
  // first tab, so "reload lands where you were" holds from the very first
  // paint, not just for clicks made after boot.
  const wanted = currentHash();
  if (wanted && MODULES.some(m => m.id === wanted)) showPane(wanted);
  else if (MODULES.length) showPane(MODULES[0].id);
}

/* A module whose declared requirements are absent renders the named cause.
   Not empty, not an error page, not a route-level 503 the user has to read a
   network tab to find -- the descriptor said what it needed, so the pane can
   say what is missing. */
function declaredDegraded(el, m) {
  const causes = (m.unmet || []).map(u =>
    `<li><strong>${esc(u.requirement)}</strong> — ${esc(u.detail)}</li>`).join("");
  el.innerHTML = `<div class="degraded" style="max-width:68rem;margin-inline:auto">
    <strong>${esc(m.label)}</strong> is unavailable on this machine because it
    declares requirements that are not met here:
    <ul style="margin:.4rem 0 0">${causes}</ul></div>`;
}

async function mountModule(m) {
  const el = document.getElementById(`pane-${m.id}`);
  if (!el || MOUNTED[m.id]) return;
  MOUNTED[m.id] = true;
  if (!m.available) { declaredDegraded(el, m); return; }
  try {
    // Native ES module, resolved from the descriptor's `view` filename. No
    // bundler, no import map: the shell knows the directory, the descriptor
    // knows the file, and neither accepts a path from anywhere else.
    const mod = await import(`/views/${m.view}`);
    await mod.mount(el);
  } catch (e) {
    degraded(el, `${m.label}: view failed to load — ${e.message}`);
  }
}

function showPane(name) {
  document.querySelectorAll(".tab").forEach(t =>
    t.classList.toggle("active", t.dataset.pane === name));
  document.querySelectorAll(".pane").forEach(p =>
    p.classList.toggle("active", p.id === `pane-${name}`));
  // Reload-lands-where-you-were: reflect the active pane in the URL without
  // adding a history entry per tab click (replaceState, not a hash write --
  // the latter would also fire `hashchange`, and the handler below would
  // call showPane again for no reason).
  if (currentHash() !== name) history.replaceState(null, "", `#${name}`);
  const m = moduleById(name);
  if (m && m.view) mountModule(m);
  // The panes still on the old path own their own lazy-load guard now
  // (board.js / curator.js `activate()`), the same idea as `mountModule`'s
  // `MOUNTED` flag applied to a module that never got a descriptor `view`.
  if (name === "board") activateBoard();
  if (name === "curator") activateCurator();
}

window.showPane = showPane;

// Back/forward and a typed-in #hash both fire this -- not a click, so it does
// not go through the tab strip's own listener.
window.addEventListener("hashchange", () => {
  const name = currentHash();
  if (name && moduleById(name)) showPane(name);
});

/* ---- the build stamp: staleness, stated ---- */

async function loadStamp() {
  const el = document.getElementById("stamp");
  try {
    const h = await jget("/api/estate/header");
    if (!h.available) {
      el.innerHTML = `<span class="stale">No estate build on this machine</span>
        <span class="k">·</span><span>${esc(h.reason || "")} — run <code>python run.py build</code>.
        Estate views are unavailable; the review queue is unaffected.</span>`;
      return;
    }
    // Anything over 24h reads as stale. Not a threshold with a theory behind
    // it -- just the point past which "today's build" stops being true.
    const stale = (h.age_seconds ?? 0) > 86400;
    el.innerHTML = `
      <span class="k">build</span><strong>${esc(h.generated_at || "?")}</strong>
      <span class="${stale ? 'stale' : ''}">(${esc(ago(h.age_seconds))}${stale ? ' — STALE' : ''})</span>
      <span class="k">·</span><span class="k">commit</span><code>${esc(h.toolkit_commit || "?")}</code>
      ${h.toolkit_dirty ? '<span class="dirty">toolkit dirty at build time</span>' : ''}
      <span class="k">·</span><span class="k">estate</span>${esc(h.estate_name || "?")}
      <span class="k">·</span>${h.project_count} projects,
      ${h.authored_document_count} authored docs
      ${(h.warnings || []).length ? `<span class="k">·</span><span class="dirty">${h.warnings.length} warning(s): ${esc(h.warnings.join("; "))}</span>` : ''}`;
  } catch (e) {
    el.innerHTML = `<span class="err">Build stamp unavailable: ${esc(String(e.message || e))}</span>`;
  }
}

/* ---- boot ---- */

// The queue half may be absent (no vault on this machine) without stopping the
// estate half, and vice versa -- which is the whole point of the preflight
// split. So each loader reports its own gap and neither aborts the other.
async function boot() {
  // The strip first: until /api/modules answers there is no tab to click, and
  // a module's declared degradation is part of that answer rather than
  // something each loader discovers for itself.
  await loadModules();
  loadStamp();
  loadEstateProjects();
  try {
    await loadQueueProjects();
  } catch (e) { /* loadQueueProjects reports into #status itself */ }
}

boot();
