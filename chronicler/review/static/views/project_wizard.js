/* The Project Wizard view -- Task 3, COWORK_BRIEF_project_wizard.md.
 *
 * One card per (repo_key, stage_key), grouped by repo, read from
 * GET /api/project_wizard/board on every activation -- the server derives
 * the whole board fresh from every allowlisted repo's manifest on every
 * call (chronicler/review/project_wizard.py's own "derived, never stored"
 * rule), and this view does the same: no client-side cache between loads,
 * a manual "Refresh" re-fetches rather than re-deriving anything locally.
 *
 * Manual only, v1: every card offers exactly one action -- "Run" -- and
 * running one stage never triggers another. There is no "refresh then
 * rebuild" button anywhere in this pane, on purpose (Tim's decision,
 * COWORK_BRIEF_project_wizard.md's working rules).
 */
import { esc, jget, degraded } from "../shared.js";

const STYLE = `
.pw-root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;
      --muted:#8b949e;--accent:#58a6ff;--warn:#f0883e;--bad:#f85149;--ok:#3fb950;
      font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      background:var(--bg);color:var(--fg);padding:16px;border-radius:8px;}
.pw-root h2{font-size:16px;margin:0 0 4px}
.pw-root .sub{color:var(--muted);margin-bottom:16px}
.pw-root .toolbar{display:flex;gap:10px;align-items:center;margin-bottom:14px}
.pw-root button{background:var(--panel);color:var(--fg);border:1px solid var(--line);
      border-radius:6px;padding:5px 12px;font:inherit;cursor:pointer}
.pw-root button:hover:not(:disabled){border-color:var(--accent)}
.pw-root button:disabled{opacity:.5;cursor:default}
.pw-root .repo{background:var(--panel);border:1px solid var(--line);border-radius:8px;
      padding:10px 14px;margin:0 0 14px}
.pw-root .repo h3{margin:0 0 2px;font-size:14px}
.pw-root .repo .path{color:var(--muted);font-size:12px;margin-bottom:8px}
.pw-root .stage{border-top:1px solid var(--line);padding:8px 0;display:flex;
      gap:12px;align-items:center;flex-wrap:wrap}
.pw-root .stage:first-of-type{border-top:none}
.pw-root .stage-main{flex:1;min-width:220px}
.pw-root .stage-label{font-weight:600}
.pw-root .stage-meta{color:var(--muted);font-size:12px;margin-top:2px}
.pw-root .pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12px}
.pw-root .pill.ok{background:rgba(63,185,80,.15);color:var(--ok)}
.pw-root .pill.warn{background:rgba(240,136,62,.15);color:var(--warn)}
.pw-root .pill.bad{background:rgba(248,81,73,.15);color:var(--bad)}
.pw-root .pill.muted{background:rgba(139,148,158,.15);color:var(--muted)}
.pw-root .err{color:var(--bad);font-size:13px;white-space:pre-wrap}
.pw-root .stream{background:#010409;border:1px solid var(--line);border-radius:6px;
      padding:8px 10px;font:12px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;
      color:var(--muted);white-space:pre-wrap;max-height:160px;overflow:auto;margin-top:6px}
`;

function pill(text, cls) { return `<span class="pill ${cls}">${esc(text)}</span>`; }

function outcomePill(marker) {
  if (!marker) return pill("never run", "muted");
  const cls = { success: "ok", failed: "bad", blocked: "warn", skipped: "muted" }[marker.state] || "muted";
  return pill(`${marker.state} — ${marker.finished_at || "?"}`, cls);
}

function freshnessLine(f) {
  if (!f) return "freshness unknown";
  if (f.source === "delegated") {
    if (f.error) return `delegated: error — ${esc(f.error)}`;
    return `delegated: ${esc(f.status || "no status returned")}`;
  }
  if (f.last_built == null) return "self: no output found yet";
  const d = new Date(f.last_built * 1000);
  return `self: last built ${esc(d.toISOString())}`;
}

function lockLine(lock) {
  if (!lock || !lock.locked) return "";
  const stale = lock.stale ? ` <span class="pill warn">stale — ${esc((lock.stale_reasons || []).join("; "))}</span>` : "";
  return `<div class="stage-meta">locked — started ${esc(lock.started_at || "?")}${stale}</div>`;
}

/* The last run's stdout tail / error text, keyed by "repoKey::stageKey" --
 * kept OUTSIDE the DOM the board re-renders on every load(). A run's own
 * outcome used to be written straight into the stage's `.stream` element
 * and then immediately wiped: `runStage`'s `finally` block always called
 * `load(view)` to re-derive the board (correct -- the board must be
 * re-read fresh, never patched in place), but `load()` itself opens with
 * `view.innerHTML = "Loading…"` before the new fetch even starts, so the
 * just-written outcome was overwritten before anyone could read it --
 * looked like the button did nothing but flicker. Keeping the text here
 * and re-injecting it in `stageHtml()` on every render survives the
 * board's own "derived, never stored" refresh instead of fighting it.
 */
const LAST_OUTCOME = {};

function stageHtml(repoKey, s) {
  const running = s.lock && s.lock.locked && !s.lock.stale;
  const outcomeText = LAST_OUTCOME[`${repoKey}::${s.key}`];
  return `<div class="stage" data-repo="${esc(repoKey)}" data-stage="${esc(s.key)}">
    <div class="stage-main">
      <div class="stage-label">${esc(s.label)} <span class="pill muted">${esc(s.kind)}</span></div>
      <div class="stage-meta">${esc(freshnessLine(s.freshness))}</div>
      <div class="stage-meta">${outcomePill(s.last_run)}</div>
      ${!s.cwd_ok ? `<div class="err">blocked: ${esc(s.cwd_error || "cwd escapes repo root")}</div>` : ""}
      ${lockLine(s.lock)}
      <div class="stream" style="${outcomeText ? "" : "display:none"}">${outcomeText ? esc(outcomeText) : ""}</div>
    </div>
    <button class="run-btn" ${(!s.cwd_ok || running) ? "disabled" : ""}>
      ${running ? "running…" : "Run"}
    </button>
  </div>`;
}

function repoHtml(r) {
  if (!r.ok) {
    return `<div class="repo"><h3>${esc(r.repo_key)}</h3>
      <div class="path">${esc(r.repo_root)}</div>
      <div class="err">${esc(r.error)}</div></div>`;
  }
  return `<div class="repo">
    <h3>${esc(r.repo_name)} <span class="pill muted">${esc(r.repo_key)}</span></h3>
    <div class="path">${esc(r.repo_root)}</div>
    ${r.stages.map(s => stageHtml(r.repo_key, s)).join("")}
  </div>`;
}

async function runStage(view, btn, repoKey, stageKey) {
  const key = `${repoKey}::${stageKey}`;
  const stream = btn.closest(".stage").querySelector(".stream");
  btn.disabled = true;
  btn.textContent = "running…";
  stream.style.display = "block";
  stream.textContent = "starting…";
  try {
    const res = await fetch("/api/project_wizard/execute", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_key: repoKey, stage_key: stageKey }),
    });
    const body = await res.json();
    if (!res.ok) {
      const d = body && body.detail;
      throw new Error((d && (d.detail || d.reason)) || res.status);
    }
    LAST_OUTCOME[key] = `[${body.state}] ${body.detail || ""}\n${body.stdout_tail || ""}`.trim();
  } catch (e) {
    LAST_OUTCOME[key] = `error: ${e.message}`;
  } finally {
    // Re-derive the whole board -- never patched in place. LAST_OUTCOME
    // survives this because it lives outside the DOM load() replaces; see
    // its own comment above.
    await load(view);
  }
}

async function load(view) {
  view.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    const data = await jget("/api/project_wizard/board");
    if (!data.repos.length) {
      view.innerHTML = `<div class="empty">No repos configured for this machine in
        config/project_wizard.allow.json. Manual only, v1 -- widening the allowlist
        is a reviewed, committed edit.</div>`;
      return;
    }
    view.innerHTML = data.repos.map(repoHtml).join("");
    view.querySelectorAll(".run-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const stageEl = btn.closest(".stage");
        runStage(view, btn, stageEl.dataset.repo, stageEl.dataset.stage);
      });
    });
  } catch (e) {
    degraded(view, `Project Wizard unavailable: ${e.message}`);
  }
}

/* The view contract: `mount(el)`, called once, the first time the tab is
   opened. */
export async function mount(el) {
  el.innerHTML = `<style>${STYLE}</style>
    <div class="pw-root">
      <h2>Project Wizard</h2>
      <div class="sub">Every allowlisted repo's declared, runnable stages. One
        click runs one stage; nothing chains automatically (manual only, v1).</div>
      <div class="toolbar"><button id="pw-refresh">Refresh</button></div>
      <div id="pw-board"><div class="empty">Loading…</div></div>
    </div>`;
  const view = el.querySelector("#pw-board");
  el.querySelector("#pw-refresh").addEventListener("click", () => load(view));
  await load(view);
}
