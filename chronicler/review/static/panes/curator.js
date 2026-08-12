/* The Knowledge Curator pane -- COWORK_BRIEF_unified_app.md Task 2. Moved
 * verbatim. `activate()` mirrors board.js's: the old `CURATOR_LOADED` guard
 * that lived in the shell's `showPane` moves in here with the state it
 * guards, and the shell calls `activate()` unconditionally on every visit
 * to this tab. */
import { esc, jget } from "../shared.js";

let CURATOR_LOADED = false;
let CURATOR_MODELS = [];  // /v1/models loaded list, from the last preflight
let CONDUCTOR_CANDIDATES = [];  // last /conductor/candidates fetch, held for plan/preview

function showCuratorSub(name) {
  document.querySelectorAll(".curator-sub").forEach(el =>
    el.style.display = (el.id === `curator-sub-${name}` ? "block" : "none"));
  if (name === "control") loadCuratorControl();
  if (name === "findings") loadCuratorFindings();
  if (name === "coverage") loadCuratorCoverage();
  if (name === "conductor") loadCuratorConductor();
}

async function loadCurator() {
  CURATOR_LOADED = true;
  const absent = document.getElementById("curator-absent");
  const body = document.getElementById("curator-body");
  let header;
  try { header = await jget("/api/curator/header"); }
  catch (e) {
    absent.style.display = "block"; absent.textContent =
      `Curator unavailable: ${e.message}`; return;
  }
  if (header.available === false && header.reason) {
    absent.style.display = "block";
    body.style.display = "none";
    absent.textContent = header.reason === "not_work_mcf_estate"
      ? `Absent on this machine: ${header.detail}`
      : `Nothing has run here yet: ${header.detail || header.reason}`;
    return;
  }
  absent.style.display = "none";
  body.style.display = "block";
  renderCuratorHeader(header);
  showCuratorSub("k0");
  await loadCuratorK0();
}

export async function activate() {
  if (!CURATOR_LOADED) await loadCurator();
}

function renderCuratorHeader(header) {
  const rows = Object.entries(header.stages || {}).map(([k, s]) => {
    const state = s.exists ? "on disk" : (s.blocked ? "blocked" : "absent");
    const cls = s.exists ? "ok" : (s.blocked ? "" : "err");
    return `<div class="doc-row" style="cursor:default">
      <span><strong>${k}</strong> &mdash; <span class="${cls}">${state}</span>
      ${s.generated_at ? `<span class="meta"> · ${esc(s.generated_at)} (${esc(s.generated_at_source || "")})</span>` : ""}
      ${s.model_id ? `<span class="meta"> · model ${esc(s.model_id)}</span>` : ""}</span>
      ${s.blocked_reason ? `<span class="meta">${esc(s.blocked_reason)}</span>` : ""}
    </div>`;
  }).join("");
  document.getElementById("curator-header").innerHTML =
    `<div class="sub">ratified map: <strong>${header.ratified_row_count}</strong> row(s) ·
      data dir <code>${esc(header.data_dir)}</code></div>${rows}`;
}

/* -- K0: candidate cards, per-row actions only, no bulk accept -- */

async function loadCuratorK0() {
  const el = document.getElementById("curator-sub-k0");
  el.innerHTML = "<div class='empty'>Loading…</div>";
  let data;
  try { data = await jget("/api/curator/k0/candidates"); }
  catch (e) { el.innerHTML = `<span class="err">${esc(e.message)}</span>`; return; }
  const c = data.counts;
  let html = `<div class="sub">Six K0 counts, zeroes included:
    matched-pass1 <strong>${c.matched_by_pass1}</strong> ·
    matched-pass2 <strong>${c.matched_by_pass2}</strong> ·
    ambiguous-same-project <strong>${c.ambiguous_same_project}</strong> ·
    ambiguous-different-project <strong>${c.ambiguous_different_project}</strong> ·
    unmatched-sheet-rows <strong>${c.unmatched_sheet_rows}</strong> ·
    unmapped-local_*-folders <strong>${c.unmapped_local_folders_on_disk}</strong></div>`;
  if (!data.exists) {
    html += `<div class="empty">No candidate_map.tsv on this machine yet -- run K0
      (bootstrap_conversation_map.py) against the curated sheet first.</div>`;
  }
  for (const [outcome, rows] of Object.entries(data.groups)) {
    html += `<div class="doc-group-head">${esc(outcome)} (${rows.length})</div>`;
    if (!rows.length) html += `<div class="empty" style="padding:.6rem 0">none</div>`;
    for (const r of rows) html += curatorK0Card(r);
  }
  html += `<div class="doc-group-head">Unmapped local_* folders on disk (${data.unmapped_local_folders.length})</div>
    <p class="sub">If these are conversations deleted in the Cowork UI, deleting a
      conversation does not delete its transcript -- a data-retention finding
      about the work estate, not a tidy-up list.</p>`;
  for (const f of data.unmapped_local_folders) {
    html += `<div class="doc-row" style="cursor:default"><span><code>${esc(f.conversation_id)}</code>
      <span class="meta"> · ${esc(f.real_time || "unknown date")} (${esc(f.real_time_source || "?")}) ·
      ${f.message_count} message(s) · project dir ${esc(f.cowork_project_dir || "?")}</span></span></div>`;
  }
  html += `<div style="margin-top:1rem">
    <button class="small" onclick="loadCuratorStagedDiff()">Show staged diff</button>
    <div id="curator-staged-diff"></div></div>`;
  el.innerHTML = html;
}

function curatorK0Card(r) {
  const already = r.already_ratified;
  const action = r.offered_action || { action: "none" };
  const rid = `k0-${Math.random().toString(36).slice(2)}`;
  let actionsHtml = "";
  if (already) {
    actionsHtml = `<span class="ok">already ratified</span>`;
  } else if (action.action === "ratify") {
    actionsHtml = `<button class="small primary" onclick="curatorRatify('${rid}')">Ratify</button>`;
  } else if (action.action === "ratify_pair") {
    actionsHtml = `<span class="meta">${esc(action.reason)}</span>
      <button class="small primary" onclick="curatorRatify('${rid}')">Ratify (this row of the pair)</button>`;
  } else if (action.action === "hand_map_or_leave" || action.action === "hand_map_only") {
    actionsHtml = `<span class="meta">${esc(action.reason)}</span>
      <input id="${rid}-sid" placeholder="session_id, found by hand" class="small"
             style="font:inherit;padding:.2rem .4rem;border:1px solid #8886;border-radius:5px;background:transparent;color:inherit">
      <button class="small" onclick="curatorHandMap('${rid}', ${JSON.stringify(r).replace(/"/g, '&quot;')})">Hand-map & ratify</button>`;
  }
  return `<div class="item" id="${rid}" data-row='${JSON.stringify(r).replace(/'/g, "&#39;")}'>
    <div class="item-body">
      <div class="row1"><span class="badge">${esc(r.status)}</span>
        <span class="badge">${esc(r.match_pass || "no pass")}</span>
        <span class="meta">candidates: ${esc(r.candidate_count)} · matched_length: ${esc(r.matched_length || "")}</span></div>
      <div class="title">${esc(r.conversation_name || "(no name)")}</div>
      <div class="meta">local_folder ${esc(r.local_folder)} · project_id ${esc(r.project_id)}
        · session_id ${esc(r.session_id || "(none)")}</div>
      <div class="note">${esc(r.note || "")}</div>
      <div id="${rid}-evidence" class="snippet">Evidence not loaded — <a href="#" onclick="curatorLoadEvidence('${rid}');return false">show matched spans</a></div>
      <div class="item-actions">${actionsHtml}</div>
    </div>
  </div>`;
}

async function curatorLoadEvidence(rid) {
  const card = document.getElementById(rid);
  const r = JSON.parse(card.dataset.row);
  const evDiv = document.getElementById(`${rid}-evidence`);
  evDiv.textContent = "Loading evidence…";
  try {
    const params = new URLSearchParams({
      session_id: r.session_id || "",
      match_pass: r.match_pass || "", matched_length: r.matched_length || ""
    });
    const ev = await jget(`/api/curator/k0/evidence?${params}`);
    const mark = (t, span) => {
      if (t == null) return "(unavailable)";
      if (!span) return esc(t);
      return esc(t.slice(0, span[0])) + "<mark>" + esc(t.slice(span[0], span[1])) + "</mark>" + esc(t.slice(span[1]));
    };
    evDiv.innerHTML = `<div><strong>sheet opener</strong> (normalised): ${mark(ev.sheet.text, ev.sheet.span)}</div>
      <div style="margin-top:.3rem"><strong>conversation opener</strong> (normalised): ${mark(ev.conversation.text, ev.conversation.span)}</div>
      <div class="meta" style="margin-top:.3rem">machine-readable: pass=${esc(r.match_pass)} matched_length=${esc(r.matched_length)} candidates=${esc(r.candidate_count)}</div>`;
  } catch (e) { evDiv.textContent = `Evidence unavailable: ${e.message}`; }
}

async function curatorRatify(rid) {
  const card = document.getElementById(rid);
  const r = JSON.parse(card.dataset.row);
  const provenance = r.match_pass === "pass2" ? "machine-matched:pass-2" : "machine-matched:pass-1";
  try {
    const res = await fetch("/api/curator/k0/ratify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: r.session_id, local_folder: r.local_folder,
        project_id: r.project_id, conversation_name: r.conversation_name,
        provenance, note: `matched_length=${r.matched_length || ""} candidates=${r.candidate_count}`
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail && (data.detail.detail || data.detail) || res.status);
    card.querySelector(".item-actions").innerHTML =
      `<span class="ok">${esc(data.status)}</span>`;
  } catch (e) { card.querySelector(".item-actions").innerHTML += ` <span class="err">${esc(String(e.message || e))}</span>`; }
}

async function curatorHandMap(rid, r) {
  const sid = document.getElementById(`${rid}-sid`).value.trim();
  if (!sid) { alert("session_id required for a hand-mapped row"); return; }
  const provenance = r.status === "ambiguous-different-project"
    ? "human-picked:refused-collision" : "hand-mapped:no-candidate";
  const card = document.getElementById(rid);
  try {
    const res = await fetch("/api/curator/k0/ratify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sid, local_folder: r.local_folder,
        project_id: r.project_id, conversation_name: r.conversation_name,
        provenance, note: "hand-mapped from the ratification screen"
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail && (data.detail.detail || data.detail) || res.status);
    card.querySelector(".item-actions").innerHTML = `<span class="ok">${esc(data.status)}</span>`;
  } catch (e) { card.querySelector(".item-actions").innerHTML += ` <span class="err">${esc(String(e.message || e))}</span>`; }
}

async function loadCuratorStagedDiff() {
  const el = document.getElementById("curator-staged-diff");
  el.textContent = "Loading…";
  try {
    const data = await jget("/api/curator/k0/staged_diff");
    el.innerHTML = `<pre style="white-space:pre-wrap;font-size:.78rem">${esc(data.diff || "(nothing staged)")}</pre>`;
  } catch (e) { el.textContent = `unavailable: ${e.message}`; }
}

/* -- Control strip: preflight, model selection, execution, lock -- */

async function loadCuratorControl() {
  const el = document.getElementById("curator-sub-control");
  el.innerHTML = "<div class='empty'>Loading…</div>";
  let pre, table;
  try {
    pre = await jget("/api/curator/control/preflight");
    table = await jget("/api/curator/control/stage_table");
  } catch (e) { el.innerHTML = `<span class="err">${esc(e.message)}</span>`; return; }
  CURATOR_MODELS = pre.lm_studio.models || [];
  const lm = pre.lm_studio;
  let html = `<div class="doc-row" style="cursor:default"><span>
    LM Studio (${esc(lm.endpoint)}): <strong class="${lm.reachable ? 'ok' : 'err'}">${lm.reachable ? "reachable" : "NOT reachable"}</strong>
    ${lm.error ? `<span class="meta"> — ${esc(lm.error)}</span>` : ""}
    ${lm.reachable ? `<span class="meta"> — loaded: ${lm.models.map(esc).join(", ") || "(none)"}</span>` : ""}
    </span></div>
    <div class="doc-row" style="cursor:default"><span>Map ratified:
      <strong class="${pre.map_ratified ? 'ok' : 'err'}">${pre.map_ratified ? "yes" : "no"}</strong>
      (${pre.ratified_row_count} row(s))</span></div>
    <div class="doc-row" style="cursor:default"><span>Lock:
      <strong class="${pre.lock.locked ? 'err' : 'ok'}">${pre.lock.locked ? `held — ${esc(pre.lock.stage)} since ${esc(pre.lock.started_at)}` : "free"}</strong></span></div>`;

  html += `<div class="doc-group-head">Stages</div>`;
  for (const [key, spec] of Object.entries(table.stages)) {
    const exists = pre.stage_outputs_exist[key];
    html += `<div class="doc-row" style="cursor:default"><span><strong>${key}</strong> ${esc(spec.label)}
      ${spec.deterministic ? `<span class="badge">deterministic — no selector</span>` : `<span class="badge">calls a model</span>`}
      <span class="meta"> · output ${exists ? "exists" : "absent"}</span></span>
      <span>`;
    if (!spec.deterministic) {
      const opts = CURATOR_MODELS.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
      html += `<select id="model-${key}">${opts || '<option value="">(no models loaded)</option>'}</select>
        <button class="small" onclick="curatorCheckInvalidation('${key}')">Check impact</button>
        <button class="small" onclick="curatorSetModel('${key}')">Save selection</button>`;
    }
    html += ` <button class="small primary" onclick="curatorExecute('${key}')">Run</button></span></div>
      <div id="impact-${key}"></div>`;
  }
  html += `<div class="doc-group-head">K4 shortlist capability</div>
    <div class="sub">${esc(table.k4_shortlist_capability.method)} ${esc(table.k4_shortlist_capability.note)}</div>
    <div id="curator-exec-result"></div>`;
  el.innerHTML = html;
}

async function curatorCheckInvalidation(stage) {
  const div = document.getElementById(`impact-${stage}`);
  div.textContent = "Checking…";
  try {
    const data = await jget(`/api/curator/control/invalidation?stage=${stage}`);
    div.innerHTML = `<span class="meta">${esc(data.detail)}</span>`;
  } catch (e) { div.textContent = `unavailable: ${e.message}`; }
}

async function curatorSetModel(stage) {
  const sel = document.getElementById(`model-${stage}`);
  const model_id = sel.value;
  if (!model_id) return;
  try {
    await fetch("/api/curator/control/model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage, model_id })
    });
  } catch (e) { /* surfaced on next preflight load */ }
}

async function curatorExecute(stage) {
  const result = document.getElementById("curator-exec-result");
  result.textContent = `Running ${stage}…`;
  try {
    const res = await fetch("/api/curator/control/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ stage })
    });
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail || {};
      result.innerHTML = `<span class="err">Refused: ${esc(d.detail || d.reason || res.status)}</span>`;
      return;
    }
    const cls = data.state === "success" ? "ok" : (data.state === "failed" ? "err" : "");
    result.innerHTML = `<span class="${cls}">${esc(stage)}: <strong>${esc(data.state)}</strong> — ${esc(data.detail)}</span>`;
  } catch (e) { result.innerHTML = `<span class="err">${esc(String(e.message || e))}</span>`; }
}

/* -- Findings: five sections, K5's own order, nothing recomputed -- */

async function loadCuratorFindings() {
  const el = document.getElementById("curator-sub-findings");
  el.innerHTML = "<div class='empty'>Loading…</div>";
  let data;
  try { data = await jget("/api/curator/findings"); }
  catch (e) { el.innerHTML = `<span class="err">${esc(e.message)}</span>`; return; }
  const h = data.run_health;
  let html = `<div class="degraded" style="margin-bottom:.8rem">
    <strong>Run health</strong> — excluded (unresolvable timestamp): ${h.excluded_no_timestamp_count} ·
    unmapped folders: ${h.unmapped_folders_count} ·
    projects with no knowledge file: ${h.projects_no_knowledge_file_count} ·
    quote-rejection rate: ${h.quote_rejection_rate != null ? (h.quote_rejection_rate * 100).toFixed(1) + "%" : "n/a"} ·
    model ${esc(h.model_id || "n/a")} · run ${esc(h.run_timestamp || "n/a")}</div>`;

  html += `<div class="doc-group-head">1. Gaps (per project, never totalled)</div>`;
  const gapKeys = Object.keys(data.gaps_by_project);
  if (!gapKeys.length) html += `<div class="empty">none for a project with a knowledge file</div>`;
  for (const pid of gapKeys) {
    html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(pid)}</strong> — ${data.gaps_by_project[pid].length} gap(s)</span></div>`;
    for (const c of data.gaps_by_project[pid]) html += curatorClaimCard(c);
  }

  html += `<div class="doc-group-head">2. No knowledge file yet (starter list)</div>`;
  for (const [pid, clusters] of Object.entries(data.no_knowledge_file_starters)) {
    html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(pid)}</strong></span></div>`;
    for (const cl of clusters) html += `<div class="snippet">${esc(cl.example_claim_text)}
      <span class="meta"> (recurred across ${cl.conversation_count} conversation(s))</span></div>`;
  }

  html += `<div class="doc-group-head">3. Cross-project relevance (${data.cross_project.length})</div>`;
  for (const c of data.cross_project) html += curatorClaimCard(c);

  html += `<div class="doc-group-head">4. Superseded (${data.superseded.length})</div>`;
  for (const s of data.superseded) {
    html += `<div class="item"><div class="item-body">
      <div class="title">${esc(s.project_id)} — interval ${s.interval_days != null ? s.interval_days + " day(s)" : "?"}</div>
      <div class="snippet"><strong>current</strong> (${esc(s.current.real_time || "?")}, ${esc(s.current.conversation_id || "?")}):
        ${esc(s.current.claim_text || "")}<br>&gt; ${esc(s.current.quoted_source || "")}</div>
      <div class="snippet"><strong>superseded</strong> (${esc(s.superseded.real_time || "?")}, ${esc(s.superseded.conversation_id || "?")}):
        ${esc(s.superseded.claim_text || "")}<br>&gt; ${esc(s.superseded.quoted_source || "")}</div>
      <div class="meta">${esc(s.note)}</div>
    </div></div>`;
  }

  html += `<div class="doc-group-head">5. Confirmed captured</div>`;
  for (const [pid, info] of Object.entries(data.captured)) {
    html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(pid)}</strong> — ${info.count} claim(s)</span></div>`;
    for (const c of info.sample) html += `<div class="snippet">${esc(c.claim_text)}</div>`;
    if (info.more) html += `<div class="meta">…and ${info.more} more</div>`;
  }
  el.innerHTML = html;
}

function curatorClaimCard(c) {
  const shortlist = (c.shortlist || []).map(s => s.shortlist_score != null ? s.shortlist_score.toFixed(2) : "?").join(", ");
  return `<div class="item"><div class="item-body">
    <div class="title">${esc(c.claim_text)}</div>
    <div class="snippet">&gt; ${esc(c.quoted_source)}</div>
    <div class="meta">conversation ${esc(c.conversation_id)} (${esc(c.real_time || "?")}) ·
      shortlist scores: ${shortlist || "(none)"} ·
      confirm: ${c.confirm ? (c.confirm.confirmed ? "confirmed" : "not confirmed") : "no confirm call made"}
      <a href="#" onclick="curatorDrillThrough('${esc(c.conversation_id)}');return false"> · view transcript window</a></div>
    <div id="drill-${esc(c.conversation_id)}"></div>
  </div></div>`;
}

async function curatorDrillThrough(cid) {
  const div = document.getElementById(`drill-${cid}`);
  div.textContent = "Loading…";
  try {
    const data = await jget(`/api/curator/findings/transcript?conversation_id=${encodeURIComponent(cid)}`);
    div.innerHTML = `<pre style="white-space:pre-wrap;font-size:.75rem;max-height:16rem;overflow:auto">${esc(JSON.stringify(data.message_window, null, 2))}</pre>
      <span class="meta">timestamp: ${esc(data.real_time)} (${esc(data.real_time_source)})</span>`;
  } catch (e) { div.innerHTML = `<span class="err">${esc(e.message)}</span>`; }
}

/* -- Map / coverage: K1's reconciliation, reported, never resolved -- */

async function loadCuratorCoverage() {
  const el = document.getElementById("curator-sub-coverage");
  el.innerHTML = "<div class='empty'>Loading…</div>";
  let data;
  try { data = await jget("/api/curator/coverage"); }
  catch (e) { el.innerHTML = `<span class="err">${esc(e.message)}</span>`; return; }
  if (!data.available) {
    el.innerHTML = `<div class="empty">${esc(data.blocked_reason || "K1 has not run.")}</div>`;
    return;
  }
  let html = `<p class="sub">${esc(data.note)}</p>
    <div class="doc-group-head">Projects (${data.projects.length})</div>`;
  for (const p of data.projects) {
    html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(p.project_id)}</strong>
      — ${p.conversations.length} conversation(s), ${p.knowledge_files.length} knowledge file(s)</span></div>`;
  }
  html += `<div class="doc-group-head">Unresolved (${data.unresolved.length})</div>`;
  for (const u of data.unresolved) html += `<div class="doc-row" style="cursor:default"><span>
    <span class="badge">${esc(u.state)}</span> ${esc(u.project_id)} — ${esc(u.detail)}</span></div>`;
  html += `<div class="doc-group-head">Label disagreements (${data.label_disagreements.length})</div>`;
  for (const d of data.label_disagreements) html += `<div class="doc-row" style="cursor:default"><span>
    ${esc(d.session_id)} — ${esc(d.disagreement)}</span></div>`;
  html += `<div class="doc-group-head">Mapped but absent on disk (${data.mapped_but_absent_on_disk.length})</div>`;
  html += data.mapped_but_absent_on_disk.map(s => `<div class="doc-row" style="cursor:default"><span>${esc(s)}</span></div>`).join("");
  html += `<div class="doc-group-head">Present on disk, not mapped (${data.present_not_mapped.length})</div>`;
  html += data.present_not_mapped.map(s => `<div class="doc-row" style="cursor:default"><span>${esc(s)}</span></div>`).join("");
  el.innerHTML = html;
}

/* -- Conductor panel: preconditions/calibration/run state, build -> preview
 * -> approve a plan (COWORK_BRIEF_conductor_governor.md, Task 6 + the
 * execution loop). No execute button anywhere here, deliberately -- the
 * execution loop runs as `run.py conductor --plan-id ID` under an
 * operator's own terminal, never a route this pane could fire and walk
 * away from (see app.py's own comment above these routes). Approving a
 * plan here gives you the exact command to run it, nothing more. */

async function loadCuratorConductor() {
  const el = document.getElementById("curator-sub-conductor");
  el.innerHTML = "<div class='empty'>Loading…</div>";
  let pre, calib, run;
  try {
    [pre, calib, run] = await Promise.all([
      jget("/api/curator/conductor/preconditions"),
      jget("/api/curator/conductor/calibration"),
      jget("/api/curator/conductor/run"),
    ]);
  } catch (e) { el.innerHTML = `<span class="err">${esc(e.message)}</span>`; return; }

  let html = `<div class="doc-group-head">Preconditions</div>
    <div class="doc-row" style="cursor:default"><span>LM Studio:
      <strong class="${pre.lm_studio.reachable ? 'ok' : 'err'}">${pre.lm_studio.reachable ? "reachable" : "NOT reachable"}</strong>
      · map ratified: <strong class="${pre.map_ratified ? 'ok' : 'err'}">${pre.map_ratified ? "yes" : "no"}</strong>
      · calibration data: <strong class="${pre.calibration_available ? 'ok' : ''}">${pre.calibration_available ? "present" : "none recorded yet"}</strong></span></div>

    <div class="doc-group-head">Run state</div>
    <div class="doc-row" style="cursor:default"><span>Lock:
      <strong class="${run.lock.locked ? 'err' : 'ok'}">${run.lock.locked ? `held — ${esc(run.lock.stage)} since ${esc(run.lock.started_at)}${run.lock.stale ? " (STALE)" : ""}` : "free"}</strong></span></div>
    <p class="sub">${esc(run.note)}</p>`;

  html += `<div class="doc-group-head">Calibration (ledger)</div>`;
  if (!calib.available) {
    html += `<div class="empty">No models recorded yet -- calibration fills in as K2/K4 actually run.</div>`;
  } else {
    for (const [modelId, byStage] of Object.entries(calib.models)) {
      for (const [stage, parts] of Object.entries(byStage)) {
        for (const [part, s] of Object.entries(parts)) {
          if (!s) continue;
          html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(modelId)}</strong> ·
            ${esc(stage)} · ${part === "clean" ? "steady-state" : "post-cool-down"}:
            median ${s.median_ms_per_token.toFixed(1)}ms/token
            (p25 ${s.p25_ms_per_token.toFixed(1)}, p75 ${s.p75_ms_per_token.toFixed(1)},
            n=${s.n})</span></div>`;
        }
      }
    }
  }

  html += `<div class="doc-group-head">Build a plan</div>
    <div class="doc-row" style="cursor:default;flex-wrap:wrap;gap:.4rem">
      <span>policy <select id="conductor-policy">
        <option value="coverage">coverage (fewest claims first)</option>
        <option value="freshness">freshness (most changed first)</option>
        <option value="breadth">breadth (fewest conversations first)</option>
      </select></span>
      <span>stage <select id="conductor-stage"><option value="K2">K2</option><option value="K4">K4</option></select></span>
      <span>model for sizing <input id="conductor-model" placeholder="(optional) model_id" style="font:inherit;padding:.2rem .4rem;border:1px solid #8886;border-radius:5px;background:transparent;color:inherit"></span>
      <span>budget seconds <input id="conductor-budget" type="number" placeholder="(optional)" style="width:8rem;font:inherit;padding:.2rem .4rem;border:1px solid #8886;border-radius:5px;background:transparent;color:inherit"></span>
      <button class="small primary" onclick="curatorConductorPreview()">Preview plan</button>
    </div>
    <div id="conductor-candidates-note" class="sub"></div>
    <div id="conductor-preview"></div>`;

  el.innerHTML = html;
}

async function curatorConductorPreview() {
  const note = document.getElementById("conductor-candidates-note");
  const previewEl = document.getElementById("conductor-preview");
  const policy = document.getElementById("conductor-policy").value;
  const stage = document.getElementById("conductor-stage").value;
  const modelId = document.getElementById("conductor-model").value.trim();
  const budgetRaw = document.getElementById("conductor-budget").value.trim();
  note.textContent = "Loading real candidates from this machine's Curator data…";
  previewEl.innerHTML = "";
  try {
    const params = new URLSearchParams({ stage });
    if (modelId) params.set("model_id", modelId);
    const cd = await jget(`/api/curator/conductor/candidates?${params}`);
    CONDUCTOR_CANDIDATES = cd.candidates;
    note.textContent = `${cd.candidates.length} candidate project(s)` +
      (modelId ? "" : " — no model given, so every estimated_seconds is None (unbudgeted ordering only).");

    const body = {
      policy, profile_name: "default", stage,
      cool_down_seconds: 0.0, candidates: CONDUCTOR_CANDIDATES,
    };
    if (budgetRaw) body.budget_seconds = parseFloat(budgetRaw);
    const res = await fetch("/api/curator/conductor/plan/preview", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail || {};
      previewEl.innerHTML = `<span class="err">Refused: ${esc(typeof d === "string" ? d : (d.detail || d.reason || res.status))}</span>`;
      return;
    }
    renderConductorPlanPreview(data);
  } catch (e) { previewEl.innerHTML = `<span class="err">${esc(String(e.message || e))}</span>`; }
}

function renderConductorPlanPreview(plan) {
  const previewEl = document.getElementById("conductor-preview");
  let html = `<div class="doc-group-head">Plan <code>${esc(plan.plan_id)}</code> —
    ${plan.approved ? `<span class="ok">approved ${esc(plan.approved_at)}</span>` : `<span>not yet approved</span>`}</div>
    <div class="sub">policy ${esc(plan.policy)} · ${plan.step_count} step(s)
      ${plan.budget_seconds != null ? `· budget ${plan.budget_seconds}s, estimated ${plan.estimated_total_seconds}s` : "· no budget (full ordering)"}
      ${plan.remainder_count ? `· ${plan.remainder_count} project(s) left over (didn't fit the budget)` : ""}</div>`;
  for (const s of plan.steps) {
    html += `<div class="doc-row" style="cursor:default"><span><strong>${esc(s.project_id)}</strong> / ${esc(s.stage)}
      ${s.estimated_seconds != null ? `<span class="meta"> · ~${s.estimated_seconds.toFixed(0)}s</span>` : ""}</span></div>`;
  }
  if (plan.remainder.length) {
    html += `<div class="doc-group-head">Left over (${plan.remainder.length})</div>
      <div class="sub">${plan.remainder.map(esc).join(", ")}</div>`;
  }
  if (!plan.approved) {
    html += `<div style="margin-top:.6rem"><button class="small primary" onclick="curatorConductorApprove('${esc(plan.plan_id)}')">Approve this plan</button></div>`;
  } else {
    const cmd = `python run.py conductor --plan-id ${plan.plan_id}`;
    html += `<div class="doc-row" style="cursor:default"><span>Run it from a terminal on this machine:
      <code id="conductor-run-cmd">${esc(cmd)}</code>
      <button class="small" onclick="curatorConductorCopyCmd(this, ${JSON.stringify(cmd).replace(/"/g, "&quot;")})">Copy</button></span></div>`;
  }
  previewEl.innerHTML = html;
}

async function curatorConductorCopyCmd(btn, cmd) {
  const original = btn.textContent;
  try {
    await navigator.clipboard.writeText(cmd);
    btn.textContent = "Copied!";
  } catch (e) {
    // Clipboard API unavailable (non-HTTPS/non-localhost origin, or denied
    // permission) -- the command is still selectable text in the <code>
    // beside this button; this just can't do it for you.
    btn.textContent = "Copy failed — select & copy manually";
  }
  setTimeout(() => { btn.textContent = original; }, 1500);
}

async function curatorConductorApprove(planId) {
  const previewEl = document.getElementById("conductor-preview");
  try {
    const res = await fetch("/api/curator/conductor/plan/approve", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_id: planId }),
    });
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail || {};
      previewEl.innerHTML += `<div><span class="err">Refused: ${esc(typeof d === "string" ? d : (d.detail || d.reason || res.status))}</span></div>`;
      return;
    }
    renderConductorPlanPreview(data);
  } catch (e) { previewEl.innerHTML += `<div><span class="err">${esc(String(e.message || e))}</span></div>`; }
}

Object.assign(window, {
  showCuratorSub, curatorLoadEvidence, curatorRatify, curatorHandMap,
  loadCuratorStagedDiff, curatorCheckInvalidation, curatorSetModel,
  curatorExecute, curatorDrillThrough,
  curatorConductorPreview, curatorConductorApprove, curatorConductorCopyCmd,
});
