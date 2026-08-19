"""bench_load_cost.py -- Task 4, docs/COWORK_BRIEF_model_bench.md.

Load cost: cold start, switch cost, residency, TTL interaction -- "the
ladder's hidden tax, never yet measured" (zero true `cool_down_preceded`
entries across all 116 production measurements, per the brief's own words).
None of this touches K2/K4 -- it talks to LM Studio's OpenAI-compatible
`/v1/chat/completions` and `/v1/models` endpoints directly, the same two
endpoints `extract_claims.call_lmstudio`/`curator_control.probe_lm_studio`
already use, with the smallest request that can prove a model responded (no
extraction, no claims, no schema). There is no "K2/K4 logic" to change here
because this module never runs K2 or K4 at all -- it is a third, independent
caller of the same endpoint, exactly as the bench itself is independent of
production (Task 2's own working rule, applied to a different axis).

**Why a full round-trip stands in for "time to first token."** Task 2's
module docstring (`bench_ledger.py`) already explains why real TTFT isn't
implemented this round: `call_lmstudio` makes a plain, non-streaming
request, and adding streaming is a K2 logic change out of scope. The same
constraint applies here, by the same reasoning -- so `measure_call_latency`
requests the SMALLEST possible completion (`max_tokens=1`) rather than a
real one: with generation capped at one token, the wall-clock time from
request to full response is dominated by whatever a JIT load or prompt
processing costs, not by generation length, which is the closest
approximation to "seconds to first token" available without streaming. It
is a STATED approximation, not the real thing -- what makes the comparison
still meaningful is that `measure_cold_start`/`measure_switch_cost` always
compare it against a steady-state repeat of the SAME small request, so both
sides of every comparison carry the identical bias and it cancels out of
the difference, even though it doesn't cancel out of either raw number.

**This module cannot run itself.** Every function here makes a real network
call against a real LM Studio endpoint -- there is no LM Studio reachable
from the sandbox this module was written in (confirmed: even the connected
device's own bridge has no route to `localhost:1234` on the host it runs
inside; the request is blocked by a network allowlist before it ever
reaches the port). Every function is exercised in `tests/tester_bench_load_
cost.py` against a minimal stdlib `http.server` stand-in run for real, over
a real loopback socket, in-process -- that proves the TIMING/RESIDENCY/
ERROR-HANDLING logic is correct. What it cannot prove is how long a REAL
model load takes on this rig -- that number only exists once this module
runs against real LM Studio, which is this round's own UAT item ("Cold
start versus steady state, measured").

Stdlib only (`urllib.request`, matching `extract_claims`/`curator_control`'s
own transport choice -- no `requests`), `chronicler.pipeline` tier. Does not
import `chronicler.review` (not even for `probe_lm_studio` -- `list_loaded_
models` re-implements the same three-line `/v1/models` GET rather than
reaching into the app tier for it, same dependency-direction discipline
`ledger.py`/`bench_ledger.py`/`bench_failures.py` already state for
themselves).
"""
from __future__ import annotations

import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from l5gntools.common import DATA_DIR

DEFAULT_ENDPOINT = "http://localhost:1234"

#: Own file, own directory, alongside the bench's other two logs
#: (`bench_ledger.jsonl`, `bench_failures.jsonl`) -- a load-cost measurement
#: is neither a throughput row nor a failure, so it gets its own shape
#: rather than being force-fit into either.
DEFAULT_BENCH_LOAD_COST_PATH: Path = DATA_DIR / "model_bench" / "bench_load_cost.jsonl"

LOAD_COST_KINDS = ("cold_start", "switch", "residency")

_REQUIRED_FIELDS = ("kind", "host", "config_fingerprint")
_OPTIONAL_FIELDS = (
    "model_id", "to_model_id", "cold_seconds", "steady_seconds",
    "cold_start_tax_seconds", "switch_seconds", "switch_tax_seconds",
    "both_resident", "loaded_models", "ttl", "error",
)
_ALL_FIELDS = _REQUIRED_FIELDS + _OPTIONAL_FIELDS


# ---------------------------------------------------------------------------
# Transport -- the two endpoints this module needs, at the smallest possible
# request size. Never raises: a transport failure is a fact this module
# reports (`error`, a string), same discipline `curator_control.probe_lm_
# studio` already applies to the same endpoint.
# ---------------------------------------------------------------------------

#: Real-run evidence (2026-08-19, gemma-4-e4b, work rig): `urllib.error.
#: HTTPError`'s own `str()` is a generic `"HTTP Error 400: Bad Request"` --
#: it never includes the response BODY, which is exactly where LM Studio
#: puts the actually-useful text (`"No models loaded. Please load a model
#: in the developer page or use the 'lms load' command."`, confirmed live
#: in LM Studio's own debug log for this exact failure). Every caller of
#: this module was reading only the generic message and had no way to tell
#: "the model needs to be loaded" apart from any other 400, without going
#: to LM Studio's own log window by hand. `HTTPError` is itself a readable
#: file object (it wraps the response) -- `.read()` on it recovers the body
#: LM Studio already sent, once, before it's consumed/closed.
def _http_error_detail(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            raw = exc.read()
        except Exception:
            raw = b""
        if raw:
            try:
                text = raw.decode("utf-8", errors="replace").strip()
            except Exception:
                text = ""
            if text:
                return f"{type(exc).__name__}: HTTP {exc.code}: {text}"
    return f"{type(exc).__name__}: {exc}"


def list_loaded_models(endpoint: str = DEFAULT_ENDPOINT,
                        timeout: float = 5.0) -> tuple[list[str], str | None]:
    """`GET /v1/models` -- same endpoint, same interpretation ("the loaded
    model list") `curator_control.probe_lm_studio` already uses for it;
    re-implemented rather than imported, since that function lives in the
    app tier (see module docstring). Returns `(model_ids, error)` --
    `error` is `None` on success."""
    url = endpoint.rstrip("/") + "/v1/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        ids = [m.get("id") for m in body.get("data", [])
               if isinstance(m, dict) and m.get("id")]
        return ids, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return [], _http_error_detail(exc)


def measure_call_latency(model: str, *, endpoint: str = DEFAULT_ENDPOINT,
                          timeout: float = 120.0,
                          ttl: float | None = None) -> tuple[float | None, str | None]:
    """Wall-clock seconds for the smallest possible completion
    (`max_tokens=1`, a two-word user prompt) against `model` -- see module
    docstring for why this stands in for "seconds to first token." Returns
    `(seconds, error)`; `seconds` is `None` on any transport failure (never
    a fabricated number). `ttl`, if given, is passed through exactly as
    `extract_claims.call_lmstudio` does, so a measurement can be taken
    under a specific TTL/auto-unload setting -- part of Task 2's
    `config_fingerprint` (the brief's own words: "record the setting; it is
    part of config_fingerprint"). On a non-2xx response, `error` carries the
    real response BODY when the endpoint sent one (see `_http_error_detail`)
    -- e.g. LM Studio's `"No models loaded..."` -- not just the generic
    `HTTPError` string."""
    body: dict = {
        "model": model, "temperature": 0.0, "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }
    if ttl is not None:
        body["ttl"] = ttl
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions", data=payload, method="POST",
        headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, _http_error_detail(exc)
    return time.perf_counter() - started, None


# ---------------------------------------------------------------------------
# The three measurements Task 4 asks for.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ColdStartResult:
    model_id: str
    cold_seconds: float | None
    steady_seconds: float | None
    #: `cold_seconds - steady_seconds`; `None` if either side is missing --
    #: never guessed from one side alone.
    cold_start_tax_seconds: float | None
    error: str | None


def measure_cold_start(model: str, *, endpoint: str = DEFAULT_ENDPOINT,
                        timeout: float = 120.0, ttl: float | None = None,
                        steady_repeats: int = 3) -> ColdStartResult:
    """The FIRST call to `model` (assumed cold -- it is the CALLER's
    responsibility to ensure nothing already has it loaded; check with
    `list_loaded_models` first) against the MEDIAN of `steady_repeats`
    immediately-following calls to the same model/endpoint/ttl -- the
    brief's own definition verbatim ("seconds from request to first token
    on a model just loaded, versus steady state")."""
    cold, err = measure_call_latency(model, endpoint=endpoint, timeout=timeout, ttl=ttl)
    if cold is None:
        return ColdStartResult(model, None, None, None, err)
    steady_values = []
    for _ in range(steady_repeats):
        v, _e = measure_call_latency(model, endpoint=endpoint, timeout=timeout, ttl=ttl)
        if v is not None:
            steady_values.append(v)
    if not steady_values:
        return ColdStartResult(model, cold, None, None, "steady-state calls all failed")
    steady = statistics.median(steady_values)
    return ColdStartResult(model, cold, steady, cold - steady, None)


@dataclass(frozen=True)
class SwitchCostResult:
    from_model: str
    to_model: str
    switch_seconds: float | None
    to_model_steady_seconds: float | None
    #: `switch_seconds - to_model_steady_seconds`; `None` if either is
    #: missing.
    switch_tax_seconds: float | None
    error: str | None


def measure_switch_cost(from_model: str, to_model: str, *, endpoint: str = DEFAULT_ENDPOINT,
                         timeout: float = 120.0, ttl: float | None = None) -> SwitchCostResult:
    """Warm `from_model` with one call, then measure the FIRST call to
    `to_model` immediately after -- if the endpoint evicted `from_model` to
    make room, this call pays both the unload and the load, exactly
    "seconds to unload model A and load model B." A second, immediately-
    following call to `to_model` gives its own steady-state figure so
    `switch_tax_seconds` isolates the switch itself -- the number Task 5's
    decision matrix needs ("if moving T1->T2 mid-plan costs 90 seconds, a
    plan that alternates tiers can be slower than one that never leaves
    T2")."""
    warm, werr = measure_call_latency(from_model, endpoint=endpoint, timeout=timeout, ttl=ttl)
    if warm is None:
        return SwitchCostResult(from_model, to_model, None, None, None,
                                 f"could not warm {from_model!r}: {werr}")
    switch, serr = measure_call_latency(to_model, endpoint=endpoint, timeout=timeout, ttl=ttl)
    if switch is None:
        return SwitchCostResult(from_model, to_model, None, None, None, serr)
    steady, sterr = measure_call_latency(to_model, endpoint=endpoint, timeout=timeout, ttl=ttl)
    if steady is None:
        return SwitchCostResult(from_model, to_model, switch, None, None,
                                 f"switch measured but steady-state repeat failed: {sterr}")
    return SwitchCostResult(from_model, to_model, switch, steady, switch - steady, None)


@dataclass(frozen=True)
class ResidencyResult:
    model_a: str
    model_b: str
    #: `True`/`False` only when the probe itself succeeded; `None` if it
    #: failed -- never guessed from a missing list.
    both_resident: bool | None
    loaded_models: list
    error: str | None


def check_residency(model_a: str, model_b: str, *, endpoint: str = DEFAULT_ENDPOINT,
                     call_timeout: float = 120.0, probe_timeout: float = 5.0,
                     ttl: float | None = None) -> ResidencyResult:
    """Warm `model_a`, then `model_b`, then `GET /v1/models` -- "can two
    candidate models be VRAM-resident at once on this rig?", the brief's
    own ten-minute test, not a benchmark. `both_resident` is `True` only
    when both ids appear in the loaded list after both calls."""
    _, aerr = measure_call_latency(model_a, endpoint=endpoint, timeout=call_timeout, ttl=ttl)
    if aerr:
        return ResidencyResult(model_a, model_b, None, [], f"could not load {model_a!r}: {aerr}")
    _, berr = measure_call_latency(model_b, endpoint=endpoint, timeout=call_timeout, ttl=ttl)
    if berr:
        return ResidencyResult(model_a, model_b, None, [], f"could not load {model_b!r}: {berr}")
    loaded, perr = list_loaded_models(endpoint, timeout=probe_timeout)
    if perr:
        return ResidencyResult(model_a, model_b, None, loaded, perr)
    return ResidencyResult(model_a, model_b, (model_a in loaded and model_b in loaded),
                            loaded, None)


# ---------------------------------------------------------------------------
# Recording -- append-only, one JSON object per line, own file. `path` is
# REQUIRED everywhere, same discipline as `bench_ledger`/`bench_failures`.
# ---------------------------------------------------------------------------

def append_entry(entry: dict, path: Path) -> None:
    if entry.get("kind") not in LOAD_COST_KINDS:
        raise ValueError(
            f"load-cost entry must carry a kind from {LOAD_COST_KINDS}, got "
            f"{entry.get('kind')!r}: {entry}")
    missing = [f for f in _REQUIRED_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"load-cost entry missing required field(s) {missing}: {entry}")
    path.parent.mkdir(parents=True, exist_ok=True)
    stamped = dict(entry)
    stamped["timestamp"] = datetime.now(timezone.utc).isoformat()
    row = {k: stamped.get(k) for k in _ALL_FIELDS}
    row["timestamp"] = stamped["timestamp"]
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def load_entries(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def record_cold_start(result: ColdStartResult, *, host: str, config_fingerprint: str,
                       ttl: float | None, path: Path) -> None:
    append_entry({
        "kind": "cold_start", "host": host, "config_fingerprint": config_fingerprint,
        "model_id": result.model_id, "cold_seconds": result.cold_seconds,
        "steady_seconds": result.steady_seconds,
        "cold_start_tax_seconds": result.cold_start_tax_seconds,
        "ttl": ttl, "error": result.error,
    }, path)


def record_switch(result: SwitchCostResult, *, host: str, config_fingerprint: str,
                   ttl: float | None, path: Path) -> None:
    append_entry({
        "kind": "switch", "host": host, "config_fingerprint": config_fingerprint,
        "model_id": result.from_model, "to_model_id": result.to_model,
        "switch_seconds": result.switch_seconds,
        "steady_seconds": result.to_model_steady_seconds,
        "switch_tax_seconds": result.switch_tax_seconds,
        "ttl": ttl, "error": result.error,
    }, path)


def record_residency(result: ResidencyResult, *, host: str, config_fingerprint: str,
                      ttl: float | None, path: Path) -> None:
    append_entry({
        "kind": "residency", "host": host, "config_fingerprint": config_fingerprint,
        "model_id": result.model_a, "to_model_id": result.model_b,
        "both_resident": result.both_resident, "loaded_models": result.loaded_models,
        "ttl": ttl, "error": result.error,
    }, path)
