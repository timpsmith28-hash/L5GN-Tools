/* The shell's shared helpers -- COWORK_BRIEF_unified_app.md Task 2.
 *
 * These were four loose globals at the top of the old monolithic
 * <script> (esc, jget, degraded, ago), defined once and used by every
 * pane because every pane's code shared one script's top-level scope.
 * Splitting the shell into ES modules removes that shared scope, so
 * anything more than one file needs moves here and is imported instead.
 *
 * Nothing here changed in the move -- same bodies, same behaviour. A
 * split that also rewrote the escaping function would make an escaping
 * bug indistinguishable from a split bug.
 */

export function esc(s) {
  return (s ?? "").replace(/[&<>"]/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

// A JSON error body from FastAPI is {detail: {...}}; unwrap to the sentence
// the server actually wrote rather than showing "[object Object]".
export async function jget(url) {
  const res = await fetch(url);
  let body = null;
  try { body = await res.json(); } catch (e) { /* non-JSON error page */ }
  if (!res.ok) {
    const d = body && body.detail;
    const msg = (d && (d.detail || d.reason)) || (typeof d === "string" ? d : res.status);
    const err = new Error(msg);
    err.reason = d && d.reason;
    err.status = res.status;
    throw err;
  }
  return body;
}

export function degraded(el, msg) {
  el.innerHTML = `<div class="degraded">${esc(msg)}</div>`;
}

export function ago(seconds) {
  if (seconds == null) return "unknown age";
  const h = seconds / 3600;
  if (h < 1) return `${Math.round(seconds / 60)} min old`;
  if (h < 48) return `${h.toFixed(1)} h old`;
  return `${(h / 24).toFixed(1)} days old`;
}
