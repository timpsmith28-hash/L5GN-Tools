"""tester_bench_load_cost: Task 4's load-cost measurements --
`chronicler.pipeline.bench_load_cost`. Runs a minimal stdlib `http.server`
stand-in for LM Studio over a REAL loopback socket (in-process, on a
high, unlikely-to-collide port) and proves the timing/residency/error-
handling logic against it -- this is the closest a hermetic gate test can
get to proving the module's HTTP behaviour is correct; it cannot prove how
long a real model load takes on real hardware (see the module's own
docstring on that point -- that is this round's UAT item, not a gate test).

Not fully hermetic in the strictest sense (it binds a real socket), but
confined to 127.0.0.1 and torn down in a `finally`, matching this repo's
existing pattern for `tester_serve.py`/similar network-adjacent testers.
"""
from __future__ import annotations

import http.server
import json
import tempfile
import threading
import time
from pathlib import Path

from chronicler.pipeline import bench_load_cost as blc

_PORT = 18391
_LOAD_DELAY = 0.2


def _make_handler(state: dict):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/v1/models":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                with state["lock"]:
                    data = [{"id": m} for m in state["resident"]]
                self.wfile.write(json.dumps({"data": data}).encode())
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            model = body.get("model")
            if model == "not-actually-loaded":
                # Real-run evidence (2026-08-19): LM Studio's actual body on
                # this failure -- a plain-text 400, not JSON -- confirming
                # _http_error_detail must not assume the body parses as JSON.
                msg = ("No models loaded. Please load a model in the "
                       "developer page or use the 'lms load' command.")
                self.send_response(400)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(msg.encode())
                return
            with state["lock"]:
                resident = state["resident"]
                was_resident = model in resident
                if not was_resident:
                    if len(resident) >= state["capacity"]:
                        resident.pop(0)  # evict least-recently-used
                    resident.append(model)
                else:
                    resident.remove(model)
                    resident.append(model)
            if not was_resident:
                time.sleep(_LOAD_DELAY)  # simulated cold-load cost
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "choices": [{"message": {"content": "x"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            }).encode())

    return Handler


def run() -> list[str]:
    v: list[str] = []
    state = {"resident": [], "capacity": 1, "lock": threading.Lock()}
    srv = http.server.HTTPServer(("127.0.0.1", _PORT), _make_handler(state))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.15)
    endpoint = f"http://127.0.0.1:{_PORT}"

    try:
        # --- list_loaded_models: empty at start, honest error on a dead port
        ids, err = blc.list_loaded_models(endpoint)
        if ids != [] or err is not None:
            v.append(f"list_loaded_models on an empty server should return ([], None): "
                     f"{(ids, err)}")
        bad_ids, bad_err = blc.list_loaded_models("http://127.0.0.1:1", timeout=1.0)
        if bad_ids != [] or bad_err is None:
            v.append(f"list_loaded_models against an unreachable port should return "
                     f"([], <error string>), never raise or fabricate a list: "
                     f"{(bad_ids, bad_err)}")

        # --- measure_call_latency: a real loopback round trip
        secs, lerr = blc.measure_call_latency("model-a", endpoint=endpoint)
        if lerr is not None or secs is None or secs < 0:
            v.append(f"measure_call_latency against a real server should succeed with a "
                     f"non-negative duration: {(secs, lerr)}")

        # --- error surfacing: a non-2xx response's BODY (the actually
        #     useful text, e.g. LM Studio's "No models loaded...") must
        #     reach the caller, not just HTTPError's generic "Bad Request"
        _, body_err = blc.measure_call_latency("not-actually-loaded", endpoint=endpoint)
        if body_err is None or "No models loaded" not in body_err:
            v.append(f"measure_call_latency on a 400 with a real body should surface that "
                     f"body's text (e.g. 'No models loaded'), not just a generic HTTPError "
                     f"string: {body_err!r}")

        # --- cold start: first call to a genuinely cold model must be
        #     measurably slower than the steady-state median that follows
        state["resident"].clear()
        cold = blc.measure_cold_start("model-b", endpoint=endpoint, steady_repeats=3)
        if cold.error is not None:
            v.append(f"measure_cold_start against a real server should not error: {cold}")
        elif cold.cold_seconds < _LOAD_DELAY * 0.5:
            v.append(f"a genuinely cold first call should be roughly LOAD_DELAY seconds, "
                     f"not near-instant: {cold}")
        elif cold.steady_seconds >= _LOAD_DELAY * 0.5:
            v.append(f"steady-state repeats (model already resident) should be near-instant, "
                     f"not paying the load cost again: {cold}")
        elif cold.cold_start_tax_seconds <= 0:
            v.append(f"cold_start_tax_seconds should be positive when cold really is slower "
                     f"than steady state: {cold}")

        # --- switch cost: capacity 1, so switching TO model-b evicts model-a,
        #     and the switch itself should cost more than model-b's own
        #     steady-state repeat
        state["capacity"] = 1
        state["resident"].clear()
        sw = blc.measure_switch_cost("model-a", "model-b", endpoint=endpoint)
        if sw.error is not None:
            v.append(f"measure_switch_cost against a real server should not error: {sw}")
        elif sw.switch_tax_seconds is None or sw.switch_tax_seconds <= 0:
            v.append(f"switching into a just-evicted-competitor model should cost more than "
                     f"that model's own steady-state repeat: {sw}")

        # --- residency: capacity 1 -> NOT both resident; capacity 2 -> both,
        #     and the probe must reflect it, never guessed
        state["capacity"] = 1
        state["resident"].clear()
        res_low = blc.check_residency("model-a", "model-b", endpoint=endpoint)
        if res_low.error is not None or res_low.both_resident is not False:
            v.append(f"at capacity 1, two candidates should NOT both be resident: {res_low}")

        state["capacity"] = 2
        state["resident"].clear()
        res_high = blc.check_residency("model-a", "model-b", endpoint=endpoint)
        if res_high.error is not None or res_high.both_resident is not True:
            v.append(f"at capacity 2, two candidates SHOULD both be resident: {res_high}")

        # a probe against an unreachable endpoint must report both_resident
        # as None (unknown), never False (which would misreport "checked,
        # and they don't fit" when nothing was actually checked)
        res_unreachable = blc.check_residency("model-a", "model-b",
                                               endpoint="http://127.0.0.1:1", call_timeout=1.0)
        if res_unreachable.both_resident is not None or res_unreachable.error is None:
            v.append(f"a residency check against an unreachable endpoint must report "
                     f"both_resident=None with an error, never False: {res_unreachable}")

        # --- recording: kind enforcement, round-trip, and it lands in a
        #     file separate from the ledger/failures logs -----------------
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "load_cost.jsonl"
            blc.record_cold_start(cold, host="h", config_fingerprint="cf", ttl=None, path=p)
            blc.record_switch(sw, host="h", config_fingerprint="cf", ttl=None, path=p)
            blc.record_residency(res_high, host="h", config_fingerprint="cf", ttl=None, path=p)
            entries = blc.load_entries(p)
            if len(entries) != 3:
                v.append(f"3 record_* calls should append exactly 3 lines: {entries}")
            kinds = {e.get("kind") for e in entries}
            if kinds != set(blc.LOAD_COST_KINDS):
                v.append(f"the recorded kinds should cover exactly LOAD_COST_KINDS "
                         f"({blc.LOAD_COST_KINDS}), got {sorted(kinds)}")
            try:
                blc.append_entry({"kind": "not_a_real_kind", "host": "h",
                                   "config_fingerprint": "cf"}, p)
                v.append("append_entry accepted a kind not in LOAD_COST_KINDS")
            except ValueError:
                pass
            try:
                blc.append_entry({"kind": "cold_start"}, p)
                v.append("append_entry accepted an entry missing required fields")
            except ValueError:
                pass

        if blc.DEFAULT_BENCH_LOAD_COST_PATH.name == "bench_ledger.jsonl":
            v.append("bench_load_cost's default path must not coincide with "
                     "bench_ledger's -- a load-cost row is not a throughput row")

    finally:
        srv.shutdown()

    return v
