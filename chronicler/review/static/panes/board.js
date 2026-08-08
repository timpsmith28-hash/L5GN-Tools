/* The Docs board pane -- COWORK_BRIEF_unified_app.md Task 2. Moved verbatim.
 *
 * `activate()` is this pane's half of the shell's lazy-load contract: the
 * old script guarded a bare `loadBoard()` call with a `BOARD_LOADED`
 * module-local flag inside `showPane`. That flag cannot live in the shell
 * anymore -- it is this pane's own state -- so the guard moves in here and
 * the shell calls `activate()` unconditionally every time the Docs board
 * tab is shown, exactly like Task 1's `mountModule` does for a registered
 * module's `MOUNTED` flag. Same idea, applied to a still-legacy pane. */
import { esc, jget, degraded } from "../shared.js";

let BOARD_LOADED = false;

// Actions are a function of the column and nothing else. The two write-side
// actions the brief describes (a "UAT ratified?" control on `walked`, and
// "Prepare archive" on an archivable card) are ABSENT here, not disabled: this
// slice ships read-only, and a greyed-out button is a promise the surface
// cannot keep. `archivable` is not a column at all, because it is not
// derivable -- it needs a human saying the walk happened.
const BOARD_ACTIONS = {
  open_brief: "open the brief — the work is elsewhere",
  open_walk_sheet: "walk it — records a verdict, never computes one",
  open_results: "open the results log — walked ≠ archivable",
  show_stamp: "read-only history; the stamp is below",
};

function boxes(c) {
  // Both counts, always, even when one is zero. A card that reads 0/19 is
  // saying something, and it is not "no work was done" -- see the flag.
  const bits = [`<span class="items">walk-sheet <b>${c.done_items}</b> done /
    <b>${c.open_items}</b> open</span>`];
  const r = c.results_items || { done: 0, open: 0 };
  if (r.done || r.open)
    bits.push(`<span class="items">results log <b>${r.done}</b> done /
      <b>${r.open}</b> open</span>`);
  return bits.join("<br>");
}

function cardHtml(c, action) {
  const kindTag = c.kind === "pair" ? "" :
    `<span class="kind ${esc(c.kind)}">${esc(c.kind.replace("_", " "))}</span>`;
  const files = (c.members || []).map(m => `
    <a onclick="openBoardDoc('${esc(m.id)}')" title="${esc(m.rel)}">
      <span class="role">${esc(m.role)}</span>${esc(m.name)}</a>`).join("");
  const marks = (c.members || []).filter(m => m.gate_frozen || m.uat).map(m => {
    const bits = [];
    if (m.gate_frozen) bits.push(`gate-frozen@${esc(m.gate_frozen.commit || "?")}`);
    if (m.uat) bits.push(`uat commit=${esc(m.uat.commit || "?")} walked=${esc(m.uat.walked || "?")}`);
    return `<div class="disp">${esc(m.name)}: ${bits.join(" · ")}</div>`;
  }).join("");
  const disp = c.disposition
    ? `<div class="disp">stamped <b>${esc(c.disposition)}</b>${
      c.kind === "unmatched"
        ? ` — but pairs with nothing by filename, so the board calls it
              unmatched. Both are true; the stamp is the archivist's judgement,
              the kind is what the names carry.` : ""}</div>` : "";
  const flags = (c.flags || []).map(f => `<div class="flag">${esc(
    f === "checkbox_evidence_in_results_log"
      ? "Walked, but the ticks are in the results log, not the sheet. Shown, not normalised — do not tick the sheet to clear this."
      : f === "unstamped_archive_file"
        ? "In archive/ with no ARCHIVED stamp (§3). Unstamped, which is a finding — not the same thing as unmatched."
        : f === "members_stamped_with_different_dispositions"
          ? "This card's files carry different dispositions in their stamps."
          : f)}</div>`).join("");
  // "Walk it" only on the built_not_walked column, and only opens the item
  // view -- it never submits anything itself. The stem is the card's key.
  const walkBtn = c.column === "built_not_walked"
    ? `<button class="small" style="margin-top:.4rem" onclick="walkIt('${esc(c.key)}')">Walk it</button>`
    : "";
  return `<div class="card">
    <div class="ttl">${esc(c.title)} ${kindTag}</div>
    <div class="files">${files}</div>
    ${(c.open_items || c.done_items || (c.results_items && (c.results_items.done || c.results_items.open))) ? `<div>${boxes(c)}</div>` : ""}
    ${disp}${marks}${flags}
    <div class="action">${esc(action || "")}</div>
    ${walkBtn}
  </div>`;
}

function walkIt(stem) {
  window.showPane("uat");
  document.getElementById("uat-stem").value = stem;
  window.loadUatSheet();
}

export async function loadBoard() {
  const el = document.getElementById("board-view");
  let b;
  try { b = await jget("/api/docs/board"); }
  catch (e) { degraded(el, `Docs board unavailable: ${e.message}`); return; }

  el.innerHTML = b.columns.map(col => {
    // The unmatched count rides on the COLUMN, not just the cards. A pot of
    // archived files that quietly stopped pairing would otherwise look like a
    // smaller archive; a published count changes on its own when pairing
    // breaks, which is the only way that bug is visible without reading 45
    // filenames by hand.
    const subs = [];
    if (col.key === "archived") {
      subs.push(`${col.file_count} files`);
      subs.push(`<b>${col.unmatched_count} unmatched</b>`);
      if (col.walk_only_count) subs.push(`${col.walk_only_count} walk-only`);
    }
    return `<div class="board-col">
      <div class="col-head">
        <div class="t"><span>${esc(col.label)}</span><span class="n">${col.count}</span></div>
        <span class="hint">${esc(col.hint)}</span>
        ${subs.length ? `<span class="sub-count">${subs.join(" · ")}</span>` : ""}
      </div>
      ${col.cards.map(c => cardHtml(c, BOARD_ACTIONS[col.action])).join("")
        || `<div class="empty">Nothing in this column.</div>`}
    </div>`;
  }).join("");

  const fnd = document.getElementById("board-findings");
  fnd.innerHTML = (b.findings || []).length
    ? `<div class="fnd"><b>${b.findings.length} finding(s)</b> — the board's first
        job is exposing these, not correcting them.</div>` +
    b.findings.map(f => `<div class="fnd"><b>${esc(f.file)}</b> —
        ${esc(f.detail)}</div>`).join("")
    : `<div class="sub">No findings: every archived file is stamped and every
        walked pair records its evidence on its own sheet.</div>`;

  const off = document.getElementById("board-off");
  off.innerHTML = `<details><summary>${b.off_board.length} document(s)
    deliberately not on the board</summary><ul>` +
    b.off_board.map(o => `<li><code>${esc(o.name)}</code> — ${esc(o.reason)}</li>`)
      .join("") + `</ul></details>`;
  BOARD_LOADED = true;
}

export async function activate() {
  if (!BOARD_LOADED) await loadBoard();
}

async function openBoardDoc(id) {
  const el = document.getElementById("board-doc");
  el.innerHTML = `<div class="empty">Reading from disk…</div>`;
  try {
    const d = await jget(`/api/docs/document?doc_id=${encodeURIComponent(id)}`);
    el.innerHTML = `<h3 style="margin:.8rem 0 .3rem">${esc(d.rel)}</h3>
      ${d.truncated ? `<div class="fnd">${esc(d.note)}</div>` : ""}<pre></pre>`;
    // textContent, never innerHTML: document text cannot become markup, which
    // is the same call slice 1 made for estate documents and the same reason.
    el.querySelector("pre").textContent = d.text;
    el.scrollTop = 0;
    // `nearest` scrolls the page only if the header is actually off-screen --
    // clicking a card near the top should not yank the view around.
    document.getElementById("board-top")
      .scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    el.innerHTML = `<div class="fnd">Refused: ${esc(String(e.message || e))}</div>`;
  }
}

Object.assign(window, { openBoardDoc, walkIt });
