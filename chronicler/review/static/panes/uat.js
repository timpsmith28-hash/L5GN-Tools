/* The UAT sidebar pane -- COWORK_BRIEF_unified_app.md Task 2. Moved verbatim.
 *
 * `loadUatSheet` is called both from this pane's own "Open sheet" button
 * and from board.js's `walkIt` (a card's "Walk it" button, cross-pane) --
 * so it is attached to `window` like every other DOM-facing handler here,
 * and board.js reaches it the same way the rest of this split reaches
 * across pane boundaries: `window.loadUatSheet()`, not an ES import,
 * because the call is a UI action dispatch, not a data dependency. */
import { esc, jget } from "../shared.js";

// Session-scoped, in-memory only (brief Task 2): a plain JS object, never
// localStorage. Reloading this tab or losing the session loses these notes --
// that is the contract, and #uat-warn / the pane's sub-line say so. Only the
// emit call in Task 3 writes anything to disk.
let UAT_STEM = null;
let UAT_VIEW = null;
const UAT_ENTRIES = {};  // id -> {verdict, evidence}

const UAT_VERDICT_LABEL = {
  walked: "walked (evidence)", deferred: "deferred", blocked: "blocked",
  not_applicable: "not applicable",
};

const UAT_LAYER_LABEL = { G: "gate", W: "witness", H: "human" };

function uatItemHtml(it) {
  const e = UAT_ENTRIES[it.id] || { verdict: "", evidence: "" };
  const prior = (UAT_VIEW.prior_entries || {})[it.id];
  // A prior verdict is shown as a badge whether or not it has been resumed
  // into this session -- "already in the results log" must be visible from
  // the item view itself, not just from the sheet-level counts up top.
  const priorBadge = prior
    ? `<span class="badge" title="${esc(prior.evidence || "")}">already recorded: ${esc(UAT_VERDICT_LABEL[prior.verdict] || prior.verdict)}</span>` : "";
  // The [G]/[W]/[H] layer marker (DECISIONS 0031) decides, on emit, whether
  // this item lands under Machine-verified or Human ruling -- and until this
  // badge existed, that split was only visible in the emitted results log,
  // never on the surface where the walker actually marks the sheet. A missing
  // marker is itself worth showing: it defaults to Human ruling on emit (see
  // build_results_body), so it is labelled "unmarked", not left blank.
  const layer = it.layer;
  const layerBadge = layer
    ? `<span class="badge layer-${esc(layer)}" title="DECISIONS 0031: ${esc(UAT_LAYER_LABEL[layer] || layer)} layer">[${esc(layer)}] ${esc(UAT_LAYER_LABEL[layer] || layer)}</span>`
    : `<span class="badge layer-none" title="No [G]/[W]/[H] marker on this item -- defaults to Human ruling on emit (DECISIONS 0031)">unmarked</span>`;
  const opts = [`<option value=""${e.verdict ? "" : " selected"}>— pick a verdict —</option>`]
    .concat(Object.entries(UAT_VERDICT_LABEL).map(([v, label]) =>
      `<option value="${v}"${e.verdict === v ? " selected" : ""}>${esc(label)}</option>`));
  return `<div class="uat-item" data-id="${esc(it.id)}">
    <div class="row1">
      <span class="id">${esc(it.id)}</span>
      <span class="badge">${esc(it.state)}</span>
      ${layerBadge}
      <span>${esc(it.text)}</span>
      ${priorBadge}
    </div>
    ${it.sheet_note ? `<div class="sheet-note">sheet note: ${esc(it.sheet_note)}</div>` : ""}
    <select onchange="uatSetVerdict('${esc(it.id)}', this.value)">${opts.join("")}</select>
    <textarea placeholder="Evidence — paste terminal output verbatim, or write the verdict's reason. Deferred/blocked need a reason to emit."
              onblur="uatSetEvidence('${esc(it.id)}', this.value)">${esc(e.evidence)}</textarea>
    <div class="verr" style="display:none"></div>
  </div>`;
}

function uatSetVerdict(id, verdict) {
  const e = UAT_ENTRIES[id] || { verdict: "", evidence: "" };
  e.verdict = verdict;
  delete e._resumed;  // an active choice, even re-picking the same verdict --
  // eligible for submission again, see uatCollectEntries.
  UAT_ENTRIES[id] = e;
}

function uatSetEvidence(id, text) {
  const e = UAT_ENTRIES[id] || { verdict: "", evidence: "" };
  e.evidence = text;
  delete e._resumed;
  UAT_ENTRIES[id] = e;
}

function uatRenderView() {
  const el = document.getElementById("uat-view");
  const v = UAT_VIEW;
  const warn = v.note
    ? `<div id="uat-warn">${esc(v.note)}</div>` : "";
  const priorCount = Object.keys(v.prior_entries || {}).length;
  // Unmissable, not a footnote: a results log already existing is the single
  // most important fact about opening this sheet, so it gets its own banner
  // -- same treatment as the unticked-but-walked warning above it, not just a
  // clause in the counts line.
  const existing = v.results_exists
    ? `<div id="uat-warn">A results log already exists at
        <code>${esc(v.results_rel)}</code> (<b>${v.results_boxes.done}</b> done /
        <b>${v.results_boxes.open}</b> open). Emitting again will offer to
        <b>append</b> a new walk section — it is never overwritten.
        ${priorCount
      ? ` <button class="small" onclick="uatResume()">Resume — load
              ${priorCount} previously recorded verdict(s) into this
              session</button>`
      : ""}
      </div>`
    : "";
  const boxes = `<div class="sub">sheet <b>${v.sheet_boxes.done}</b> done /
    <b>${v.sheet_boxes.open}</b> open</div>`;
  const sections = v.sections.map(sec => `
    <div class="uat-sec"><h3>${esc(sec.label)}</h3>
      ${sec.items.length ? sec.items.map(uatItemHtml).join("")
      : `<div class="sub">No items in this section.</div>`}
    </div>`).join("");
  el.innerHTML = existing + warn + boxes + sections + `
    <div id="uat-bar">
      <button class="primary" onclick="uatEmit()">Emit results log</button>
      <span id="uat-emit-status" class="sub"></span>
    </div>`;
}

// Load prior verdicts back into the session so a half-walked sheet is never a
// blank slate on reopen. Never clobbers an entry already touched THIS
// session -- resuming is for picking up where a past walk left off, not for
// silently overwriting evidence you are actively editing right now.
function uatResume() {
  const prior = UAT_VIEW.prior_entries || {};
  let loaded = 0;
  for (const [id, e] of Object.entries(prior)) {
    if (UAT_ENTRIES[id]) continue;
    // _resumed: shown and editable, but NOT resubmitted on emit unless you
    // actually touch it -- resuming is for picking up where you left off,
    // not for re-printing everything already on record into a new section.
    UAT_ENTRIES[id] = { verdict: e.verdict, evidence: e.evidence || "", _resumed: true };
    loaded++;
  }
  uatRenderView();
  const status = document.getElementById("uat-emit-status");
  if (status) status.textContent = `Resumed ${loaded} verdict(s) from the results log.`;
}

async function loadUatSheet() {
  const stem = document.getElementById("uat-stem").value.trim();
  const el = document.getElementById("uat-view");
  if (!stem) { return; }
  if (stem !== UAT_STEM) {
    // Switching sheets drops the in-memory notes for the old one -- session-
    // scoped means scoped to the sheet you are actually looking at, not a
    // silent carry-over that would let one sheet's evidence bleed into another.
    Object.keys(UAT_ENTRIES).forEach(k => delete UAT_ENTRIES[k]);
  }
  UAT_STEM = stem;
  el.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    UAT_VIEW = await jget(`/api/uat/sheet?stem=${encodeURIComponent(stem)}`);
    uatRenderView();
  } catch (e) {
    el.innerHTML = `<div class="degraded">Refused${e.reason ? ` (${esc(e.reason)})` : ""}:
      ${esc(String(e.message || e))}</div>`;
  }
}

function uatCollectEntries() {
  // Only items given an actual verdict are submitted -- an item nobody
  // touched this session is not "not applicable", it is simply not yet walked
  // and stays off the emitted log entirely (it can be walked in a later pass).
  // A resumed-but-untouched entry (loaded by uatResume, never edited) is also
  // excluded: it is already on record from a past walk, and re-submitting it
  // unchanged would print it again into a new appended section for no reason.
  return Object.entries(UAT_ENTRIES)
    .filter(([, e]) => e.verdict && !e._resumed)
    .map(([id, e]) => ({ id, verdict: e.verdict, evidence: e.evidence || "" }));
}

async function uatEmit(mode) {
  const status = document.getElementById("uat-emit-status");
  const entries = uatCollectEntries();
  document.querySelectorAll(".uat-item").forEach(el => {
    el.classList.remove("err");
    el.querySelector(".verr").style.display = "none";
  });
  if (!entries.length) {
    status.innerHTML = `<span class="err">Nothing has a verdict yet.</span>`;
    return;
  }
  status.textContent = "Emitting…";
  try {
    const res = await fetch("/api/uat/emit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stem: UAT_STEM, entries, mode: mode || null }),
    });
    const data = await res.json();
    if (!res.ok) {
      const d = data.detail;
      if (typeof d === "string" && d.includes(":")) {
        // "id: message" per-item validation errors from validate_entries.
        d.split("; ").forEach(msg => {
          const id = msg.split(":")[0].trim();
          const item = document.querySelector(`.uat-item[data-id="${CSS.escape(id)}"]`);
          if (item) {
            item.classList.add("err");
            const v = item.querySelector(".verr");
            v.textContent = msg; v.style.display = "block";
          }
        });
        status.innerHTML = `<span class="err">Fix the flagged item(s) and re-emit.</span>`;
        return;
      }
      throw new Error((d && (d.detail || d.reason)) || res.status);
    }
    if (data.status === "exists") {
      status.innerHTML = `<span class="dirty">${esc(data.detail)}</span>
        <button class="small" onclick="uatEmit('append')">Append a new walk section</button>`;
      return;
    }
    status.innerHTML = `<span class="ok">${data.status === "appended"
      ? "Appended to" : "Emitted"} <code>${esc(data.rel)}</code> — staged,
      not committed (0028). Reload the Docs board tab: this card moves to
      Walked because the results log now exists, not because anything here
      flipped a flag.</span>`;
  } catch (e) {
    status.innerHTML = `<span class="err">Emit failed: ${esc(String(e.message || e))}</span>`;
  }
}

Object.assign(window, {
  uatSetVerdict, uatSetEvidence, uatResume, loadUatSheet, uatEmit,
});
