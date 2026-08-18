/* The Desk view -- Phase 1, COWORK_BRIEF_desk_stale_card.md Task 3.
 *
 * One card per (repo, stage, trigger), read from GET /api/desk/cards on
 * every activation. The server derives the whole card set fresh on every
 * call (chronicler/review/desk.py's own "derived, never stored" rule); this
 * view does the same -- no client-side cache between loads.
 *
 * "Rebuild now" calls the wizard's OWN execute route directly
 * (/api/project_wizard/execute, same body the Project Wizard pane already
 * uses) and then records the ruling separately via POST /api/desk/rule. This
 * view has no execution path of its own -- every stop condition in the
 * brief about that is enforced server-side, but the client mirrors it so a
 * reviewer can see it at a glance: nothing here posts a repo path or an argv
 * anywhere except through the wizard's existing route.
 */
import { esc, jget, degraded } from "../shared.js";

const STYLE = `
.dk-root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;
      --muted:#8b949e;--accent:#58a6ff;--warn:#f0883e;--bad:#f85149;--ok:#3fb950;
      font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
      background:var(--bg);color:var(--fg);padding:16px;border-radius:8px;}
.dk-root h2{font-size:16px;margin:0 0 4px}
.dk-root .sub{color:var(--muted);margin-bottom:10px}
.dk-root .footer{color:var(--muted);font-size:12px;margin-bottom:16px}
.dk-root .toolbar{display:flex;gap:10px;align-items:center;margin-bottom:14px}
.dk-root button{background:var(--panel);color:var(--fg);border:1px solid var(--line);
      border-radius:6px;padding:5px 12px;font:inherit;cursor:pointer}
.dk-root button:hover:not(:disabled){border-color:var(--accent)}
.dk-root button:disabled{opacity:.5;cursor:default}
.dk-root .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
      padding:12px 16px;margin:0 0 14px}
.dk-root .card.aged{border-color:var(--warn)}
.dk-root .question{font-weight:600;font-size:15px;margin-bottom:6px}
.dk-root .pill{display:inline-block;padding:1px 8px;border-radius:20px;font-size:12px;margin-right:6px}
.dk-root .pill.ok{background:rgba(63,185,80,.15);color:var(--ok)}
.dk-root .pill.warn{background:rgba(240,136,62,.15);color:var(--warn)}
.dk-root .pill.bad{background:rgba(248,81,73,.15);color:var(--bad)}
.dk-root .pill.muted{background:rgba(139,148,158,.15);color:var(--muted)}
.dk-root details{margin-top:8px}
.dk-root summary{cursor:pointer;color:var(--accent);font-size:13px}
.dk-root .evidence{font-size:12px;color:var(--muted);white-space:pre-wrap;margin-top:6px;
      background:#010409;border:1px solid var(--line);border-radius:6px;padding:8px 10px}
.dk-root .actions{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
.dk-root .reason{flex:1;min-width:220px;background:var(--bg);color:var(--fg);
      border:1px solid var(--line);border-radius:6px;padding:5px 8px;font:inherit}
.dk-root .default-line{color:var(--muted);font-size:12px;margin-top:6px}
.dk-root .empty{color:var(--muted);padding:20px 0}
.dk-root .err{color:var(--bad);font-size:13px;white-space:pre-wrap}
`;

function pill(text, cls) { return `<span class="pill ${cls}">${esc(text)}</span>`; }

function triggerLine(t) {
  if (t.kind === "delegated") {
    return `Trigger: delegated freshness answered — ${esc(t.delegated_status || "")}`;
  }
  return `Trigger: ${esc(t.depends_on)} ran more recently than this stage's own output — ` +
    `${esc(t.dependency_signal || "")} at ${esc(t.dependency_signal_at || "?")}, ` +
    `this stage last built ${esc(t.this_stage_built_at || "never")}`;
}

function linkedThreadLine(lt) {
  if (!lt) return "linked thread: unknown";
  if (!lt.available) return `linked thread: absent (${esc(lt.reason || "unavailable")})`;
  return `linked thread: “${esc(lt.title || "untitled")}” — ${esc(lt.date || "?")}`;
}

function evidenceBlock(card) {
  const e = card.evidence;
  const lines = [
    triggerLine(card.trigger),
    `freshness: ${esc(JSON.stringify(e.freshness))}`,
    `last run: ${esc(JSON.stringify(e.last_run))}`,
    `manifest declares: ${esc(JSON.stringify(e.manifest_declaration))}`,
    linkedThreadLine(e.linked_thread),
  ];
  return lines.join("\n");
}

function cardHtml(card) {
  const aged = card.expiry.aged;
  const ageText = card.expiry.age_days != null
    ? `${card.expiry.age_days.toFixed(1)}d old (ages at ${card.expiry.aged_after_days}d)`
    : "age unknown";
  return `<div class="card${aged ? " aged" : ""}" data-fp="${esc(card.fingerprint)}">
    <div class="question">${esc(card.question)}</div>
    ${pill(card.trigger.kind, "muted")}${aged ? pill("aged", "warn") : ""}
    ${pill(ageText, aged ? "warn" : "muted")}
    <details>
      <summary>Evidence</summary>
      <div class="evidence">${evidenceBlock(card)}</div>
    </details>
    <div class="default-line">Default: ${esc(card.default)} — nothing runs unless you click.
      Re-raises "aged" after ${card.expiry.aged_after_days} days unruled.</div>
    <div class="actions">
      <button class="dk-btn" data-action="rebuild">Rebuild now</button>
      <button class="dk-btn" data-action="snooze">Snooze</button>
      <button class="dk-btn" data-action="dismiss">Dismiss</button>
      <input class="reason" placeholder="reason (required to dismiss; until-condition for snooze)" />
    </div>
    <div class="msg" style="display:none"></div>
  </div>`;
}

async function ruleFingerprint(fingerprint, ruling, reason, until) {
  const res = await fetch("/api/desk/rule", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fingerprint, ruling, reason: reason || "", until: until || null }),
  });
  const body = await res.json();
  if (!res.ok) {
    const d = body && body.detail;
    throw new Error((d && (d.detail || d.reason)) || res.status);
  }
  return body;
}

async function handleAction(view, cardEl, action, card) {
  const msg = cardEl.querySelector(".msg");
  const reasonInput = cardEl.querySelector(".reason");
  const reason = reasonInput.value;
  msg.style.display = "block";
  try {
    if (action === "rebuild") {
      msg.textContent = "rebuilding…";
      const res = await fetch("/api/project_wizard/execute", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_key: card.repo_key, stage_key: card.stage_key }),
      });
      const outcome = await res.json();
      if (!res.ok) {
        const d = outcome && outcome.detail;
        throw new Error((d && (d.detail || d.reason)) || res.status);
      }
      await ruleFingerprint(card.fingerprint, "rebuild",
        reason || `rebuilt via card: ${outcome.state}`, null);
      msg.textContent = `rebuilt — ${outcome.state}`;
    } else if (action === "snooze") {
      if (!reason.trim()) { msg.textContent = "snooze needs an until-condition in the box above."; return; }
      await ruleFingerprint(card.fingerprint, "snooze", "snoozed via card", reason);
      msg.textContent = "snoozed";
    } else if (action === "dismiss") {
      if (!reason.trim()) { msg.textContent = "dismiss needs a reason in the box above."; return; }
      await ruleFingerprint(card.fingerprint, "dismiss", reason, null);
      msg.textContent = "dismissed";
    }
  } catch (e) {
    msg.textContent = `error: ${e.message}`;
    return;
  }
  // Re-derive the whole board -- never patched in place, same discipline as
  // the Project Wizard pane's runStage().
  await load(view);
}

async function load(view) {
  view.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    const data = await jget("/api/desk/cards");
    const footer = data.trial
      ? (data.trial.visible
          ? `trial started ${esc(data.trial.trial_start || "?")}`
          : `silent baseline week — cards visible from ${esc(data.trial.visible_at || "?")}`)
      : "";
    let latencyLine = "";
    try {
      const lat = await jget("/api/desk/latency");
      latencyLine = ` · ${lat.cards_ruled} cards ruled` +
        (lat.median_latency_hours != null ? `, median ${lat.median_latency_hours.toFixed(1)}h` : "") +
        (lat.oldest_open_days != null ? `, oldest open ${lat.oldest_open_days.toFixed(1)}d` : "");
    } catch (e) { /* footer is best-effort */ }

    if (!data.cards.length) {
      view.innerHTML = `<div class="empty">${esc(data.note || "No cards raised right now.")}</div>` +
        `<div class="footer">${footer}${latencyLine}</div>`;
      return;
    }
    view.innerHTML = data.cards.map(cardHtml).join("") +
      `<div class="footer">${footer}${latencyLine}</div>`;
    view.querySelectorAll(".card").forEach(cardEl => {
      const fp = cardEl.dataset.fp;
      const card = data.cards.find(c => c.fingerprint === fp);
      cardEl.querySelectorAll(".dk-btn").forEach(btn => {
        btn.addEventListener("click", () => handleAction(view, cardEl, btn.dataset.action, card));
      });
    });
  } catch (e) {
    degraded(view, `Desk unavailable: ${e.message}`);
  }
}

/* The view contract: `mount(el)`, called once, the first time the tab is
   opened. */
export async function mount(el) {
  el.innerHTML = `<style>${STYLE}</style>
    <div class="dk-root">
      <h2>Desk</h2>
      <div class="sub">Stale-output triage. A card is a finding with a question attached —
        the default is always "hold, nothing runs" until you click.</div>
      <div class="toolbar"><button id="dk-refresh">Refresh</button></div>
      <div id="dk-cards"><div class="empty">Loading…</div></div>
    </div>`;
  const view = el.querySelector("#dk-cards");
  el.querySelector("#dk-refresh").addEventListener("click", () => load(view));
  await load(view);
}
