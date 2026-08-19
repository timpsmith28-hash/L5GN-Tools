"""run_bench_sweep.py -- the driver that was missing from Tasks 1-5:
actually runs K1/K2/K3/K4 over the pinned Level 1 eval set for a given
candidate model, and wires the results into bench_ledger.py /
bench_failures.py / bench_load_cost.py. Lives outside the `chronicler`
package on purpose (see "Why this isn't in chronicler/pipeline/" below) --
it is a benchmarking harness, not a pipeline stage.

**No K2/K4 logic is changed to build this.** Every stage below runs the
real, unmodified `extract_claims.py`/`match_claims.py`/`knowledge_index.py`/
`corpus_index.py` scripts as real subprocesses, exactly the scripts
production already runs -- this file only chooses WHICH map/cache/output
paths they see and reads their stderr timing lines, the same contract
`curator_control.run_stage`'s `on_timing_line` callback already uses.

**Everything here writes under `data/model_bench/`, never anywhere
production reads.** The bench conversation map, K1/K3's per-sweep outputs,
K2/K4's claims/matches/caches, and the three bench logs (ledger, failures,
load-cost) all live under `DATA_DIR / "model_bench"`. Nothing here ever
opens `config/mcf_conversation_map.tsv`, `data/knowledge_curator/`, or
`data/calibration_ledger.jsonl` for writing. `--host`'s ratified map (the
one `curator_control.run_stage` would auto-inject) is never touched either
-- this script builds its OWN map from `eval_set_level1.json`, deliberately
bypassing the ratified-map/estate-resolution machinery so a bench run can
never accidentally scan (or be scanned against) the real corpus.

**Why this isn't in `chronicler/pipeline/`.** `curator_control.py` (the
thing that already knows how to stream a stage's stderr and call
`on_timing_line`) lives in `chronicler/review` -- the app tier. Pipeline
modules may never import review-tier code (the dependency-direction rule
`bench_ledger.py`/`bench_failures.py`/`bench_load_cost.py` all state for
themselves). Rather than import `curator_control` from here and break that
rule, or duplicate `chronicler.review`-tier orchestration INSIDE
`chronicler.pipeline`, this script sits beside `synthesis_case_studies/`'s
own scanners in `tests/model_bench/` -- a benchmarking tool that imports
`chronicler.pipeline.*` (bench_ledger, bench_failures, bench_load_cost,
extract_claims.prompt_fingerprint) the same way `tests/tester_*.py` already
does, and re-implements the small, pure `classify_outcome` triage
(success/skipped/failed/blocked) inline rather than importing it from
`curator_control` for the same reason.

**Caching would silently defeat repeated measurement.** K2 has no
`--no-cache` flag; K4 does but this script does not rely on it either --
every repeat gets its OWN `--cache` path (never reused), so every repeat is
a genuinely cold call to LM Studio, never a cache hit standing in for one.

Usage:
    # once, before any model: builds the bench map + runs K1/K3 (both
    # deterministic, no model, shared across every candidate and repeat)
    python run_bench_sweep.py prep --host gaming-rig

    # Task 0 -- the control run, gemma-4 against itself, 3+ repeats
    python run_bench_sweep.py run --model "gemma-4" --host gaming-rig \\
        --repeats 3 --context-length 8192 --quantisation Q4_K_M \\
        --cool-down-preceded false

    # a candidate sweep
    python run_bench_sweep.py run --model "Gemma 4 E2B Instruct" \\
        --host gaming-rig --repeats 3 --context-length 8192 \\
        --quantisation Q4_K_M --cool-down-preceded false

    # load-cost between two models (run this BETWEEN two `run` calls when
    # you switch which model is loaded in LM Studio)
    python run_bench_sweep.py switch-cost --from-model "gemma-4" \\
        --to-model "Gemma 4 E2B Instruct" --host gaming-rig \\
        --context-length 8192 --quantisation Q4_K_M

Requires the repo root as cwd (same as every other pipeline script here).
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from l5gntools.common import DATA_DIR  # noqa: E402
from chronicler.pipeline import bench_ledger as bl  # noqa: E402
from chronicler.pipeline import bench_failures as bf  # noqa: E402
from chronicler.pipeline import bench_load_cost as blc  # noqa: E402
from chronicler.pipeline import bootstrap_conversation_map as k0  # noqa: E402
from chronicler.pipeline import extract_claims  # noqa: E402

_PIPE = _REPO_ROOT / "chronicler" / "pipeline"
BENCH_DIR = DATA_DIR / "model_bench"
EVAL_SET_PATH = Path(__file__).resolve().parent / "eval_set_level1.json"

BENCH_MAP_PATH = BENCH_DIR / "bench_conversation_map.tsv"
K1_OUT = BENCH_DIR / "bench_knowledge_index.json"
K3_OUT = BENCH_DIR / "bench_corpus_index.json"

#: `DEFAULT_ENDPOINT` here is a BASE url (no path) -- correct as-is for
#: `bench_load_cost`'s functions (`measure_call_latency`/`list_loaded_
#: models`/etc, which append `/v1/chat/completions` or `/v1/models`
#: themselves). K2/K4 (`extract_claims.py`/`match_claims.py`) do NOT append
#: any path -- they POST to the literal `--endpoint` string, exactly as
#: `curator_control.chat_completions_endpoint`'s own docstring warns
#: ("passing the base straight through POSTs to `/` and LM Studio answers
#: 'Unexpected endpoint or method'"), confirmed live 2026-08-18 (every K2
#: call failed with `KeyError: 'choices'` -- LM Studio's log showed `POST
#: to /`, `Unexpected endpoint or method`). `_chat_completions_endpoint`
#: below is the same fix, re-derived here rather than imported (see module
#: docstring on staying out of the `chronicler.review` app tier) -- apply
#: it ONLY when building K2/K4's `--endpoint` argv, never for
#: `bench_load_cost` calls, which want the base url.
DEFAULT_ENDPOINT = "http://localhost:1234"


def _chat_completions_endpoint(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/v1/chat/completions"):
        return endpoint
    return endpoint + "/v1/chat/completions"


#: Real-run evidence (2026-08-19, phi3, `context_length=4096`): K2 was never
#: told this sweep's `--context-length` -- `run_one_repeat`'s `k2_argv`
#: omitted `--max-window-tokens` entirely, so `extract_claims.build_windows`
#: packed every window up to its own hardcoded `DEFAULT_MAX_WINDOW_TOKENS`
#: (8000) regardless of what candidate model was actually being swept.
#: `filter_oversized_conversations` only screens a conversation's largest
#: SINGLE MESSAGE against `context_length` -- it has no way to catch a
#: multi-message WINDOW that fits under 8000 but not under a smaller
#: candidate's real limit, because K2 was never asked to build to that
#: limit in the first place. Result: all 3 repeats died identically on
#: window 0 of the first remaining conversation (`HTTP 400`), even though
#: the 9 genuinely-unsplittable conversations had already been excluded.
#:
#: The fix is wiring, not a K2 logic change: `--max-window-tokens` already
#: exists as a first-class `extract_claims.py` CLI flag (`DEFAULT_MAX_
#: WINDOW_TOKENS`, see that module) -- this sweep simply never passed it.
#: `_WINDOW_OUTPUT_RESERVE` mirrors `bench_failures.classify_window_by_
#: size`'s own default `reserved_for_output=512`, so the budget K2 is told
#: to build to and the proactive/reactive overflow checks agree on how much
#: headroom a reply needs -- kept in sync deliberately, not re-derived from
#: a shared constant, since the two modules do not import each other.
#:
#: This changes behaviour for context_length values ABOVE 8000 too, not
#: just below it: gemma-4-e4b's completed run (`context_length=32768`)
#: implicitly used the 8000-token default the whole time, never the ~32256
#: this fix would now compute -- so its window count/timing is not
#: comparable to a fresh run made after this fix without re-running it
#: under the same corrected flag.
_WINDOW_OUTPUT_RESERVE = 512

#: Real-run evidence (2026-08-19, phi3, `context_length=4096`, AFTER the
#: `--max-window-tokens` wiring fix above): windows were correctly capped
#: to 3584 approx-tokens (4096 - 512), yet LM Studio's own error still
#: reported real requests of 7006 and 5439 tokens on two different
#: shuffled-order first-windows -- both far over 4096 despite the cap.
#: `extract_claims.approx_token_count` is a stdlib-only `len(text) // 4`
#: heuristic (see its own docstring -- "never trusted for anything that
#: needs to be exact"), tuned for English prose; this eval set's real
#: content (code/log/markdown-heavy transcripts) tokenizes considerably
#: denser than that. Backing out `SYSTEM_PROMPT`'s own ~362-approx-token
#: cost (`extract_claims.SYSTEM_PROMPT`, sent on every call) from each
#: observed real total gives real/approx ratios of roughly (7006-362)/3584
#: = 1.85x and (5439-362)/3584 = 1.42x for these two windows -- i.e. the
#: 4-chars/token assumption underestimates this content's real token count
#: by up to ~1.9x. `_APPROX_TOKEN_SAFETY_FACTOR` below derates the window
#: budget by more than that worst-observed ratio, with headroom, since two
#: data points is not a proof, only real evidence pointing at a real gap.
#: This is a bench-tier compensating correction, not a K2 fix --
#: `approx_token_count`'s heuristic itself is untouched; only the ceiling
#: this sweep tells K2 to build windows to is adjusted for what that
#: heuristic is now known to under-report on this eval set.
_SYSTEM_PROMPT_RESERVE_TOKENS = 400
_APPROX_TOKEN_SAFETY_FACTOR = 2.0


def _effective_max_window_tokens(context_length: int | None) -> int | None:
    """The approx-token ceiling to hand K2 (`--max-window-tokens`) and to
    compare a conversation's largest single message against (in place of
    raw `context_length`) so that a REAL request built from that many
    approx-tokens, plus `SYSTEM_PROMPT`'s real cost, plus the model's
    reply, stays under `context_length` even given `approx_token_count`'s
    observed ~1.9x worst-case undercount on this eval set. Returns `None`
    unchanged when `context_length` itself is `None` -- same "never guess
    a limit we weren't told" rule the rest of this file follows."""
    if context_length is None:
        return None
    budget = context_length - _WINDOW_OUTPUT_RESERVE - _SYSTEM_PROMPT_RESERVE_TOKENS
    return max(1, int(budget / _APPROX_TOKEN_SAFETY_FACTOR))


# ---------------------------------------------------------------------------
# Step 1 of Step 0's driver: the bench-scoped conversation map
# ---------------------------------------------------------------------------

#: Confirmed live, 2026-08-18, against the real bench map: K0/K1's own
#: `discover_conversations` calls `local_transcripts.discover_cowork_store`
#: ONLY (`bootstrap_conversation_map.py`'s own docstring: "K0 works the
#: Cowork store only; CLI sessions are never MCF conversations") --
#: extract_claims.py/match_claims.py inherit the same limitation, since
#: they call the identical `k0.discover_conversations`. The 2 `cli:`-store
#: conversations in `eval_set_level1.json` (`cli:430c5135...`,
#: `cli:e99b862f...`) can therefore NEVER resolve on disk for a K1/K2/K4
#: run, no matter what `cowork_transcripts_home` points at -- this is a
#: structural pipeline boundary, not a config problem. Excluded by default
#: (`include_cli=False`) so `prep`'s report reads clean (0 absent) rather
#: than 2 permanently-expected failures every run. Pass `include_cli=True`
#: only once/if that boundary is deliberately revisited for bench purposes
#: specifically (flagged as a real idea, not yet built: K2/K4 would need
#: their OWN CLI-store discovery path, which is a K2/K4 logic change and
#: therefore out of scope for the current round's stop condition).
EXCLUDED_CLI_IDS: tuple[str, ...] = ("cli:430c5135-77f6-4d9d-b5cc-a581a322deaf",
                                     "cli:e99b862f-7bf6-48c1-b903-704170868389")


#: Real-run evidence (2026-08-18, gemma-4-e4b, `context_length=32768`): one
#: eval-set conversation contains a single message so large (an embedded
#: raw model-completion/log paste, not a windowing artefact) that K2's
#: `build_windows` -- which by design NEVER splits a single message across
#: a window boundary, see that function's own docstring -- hands it to LM
#: Studio as one un-splittable window anyway, and the endpoint hard-rejects
#: it (`HTTP 400: request (79115 tokens) exceeds the available context size
#: (32768 tokens)`). This is deterministic, not transient: the same
#: conversation fails identically on every repeat, and because K2's own
#: `main()` never catches this (see `post_json_with_retry`'s docstring --
#: retries exhaust, then it re-raises), it takes down the whole K2
#: subprocess, which per `run_one_repeat` skips K4 and abandons the rest of
#: that repeat's already-completed work.
#:
#: Fixing this INSIDE K2 (a hard-split fallback in `build_windows`, or a
#: catch-and-continue around the model call) would be a K2 logic change --
#: this file's own module docstring states none is made this round. The
#: equivalent-effect fix that respects that boundary: keep the offending
#: conversation out of K2's hands in the first place, filtered here, at the
#: bench-map-building step, using the exact same "does the largest single
#: message fit in this candidate's context?" check `bench_failures.
#: classify_window_by_size` already defines for the reactive (post-failure)
#: case -- applied here proactively instead.
def _largest_message_tokens(conv) -> int:
    """The same per-message accounting `extract_claims.build_windows` does
    (never splits a message, so THIS is the true per-window floor a
    conversation can be reduced to) -- re-derived here via K2's own public/
    semi-public helpers (`_strip_wrapper_noise`, `approx_token_count`) so
    the estimate matches K2's real accounting exactly, rather than drifting
    from a second, differently-tuned token-counting heuristic."""
    largest = 0
    for sess in conv.sessions:
        for _, _role, text, _ts, _uuid in sess.messages:
            if not text:
                continue
            stripped = extract_claims._strip_wrapper_noise(text)
            if not stripped.strip():
                continue
            largest = max(largest, extract_claims.approx_token_count(stripped))
    return largest


def filter_oversized_conversations(ids: list[str], *, host: str | None,
                                    context_length: int | None) -> tuple[list[str], list[dict]]:
    """Drops any `ids` entry whose largest single message cannot fit this
    candidate's `context_length` no matter how K2 windows it -- see the
    constant comment above for why this lives here instead of inside K2.
    Returns `(kept_ids, excluded)`; `excluded` is `[{conversation_id,
    largest_message_tokens}, ...]`, always reported by the caller, never
    silently dropped (same discipline `EXCLUDED_CLI_IDS` already gets in
    `build_bench_map`'s own printed report).

    `context_length is None` (not yet known/configured for this run) is a
    no-op -- returns `ids` unchanged, `[]` excluded -- this check never
    guesses a limit it wasn't told, same rule `classify_window_by_size`
    itself states. A conversation this function can't resolve on disk
    (absent from the discovered store) is left in `ids` untouched -- that's
    a separate, already-handled "mapped but absent on disk" concern, not
    this function's to judge."""
    if context_length is None or not ids:
        return ids, []
    conversations, _errors = k0.discover_conversations(host)
    by_id = {c.conversation_id: c for c in conversations}
    #: `_effective_max_window_tokens` already bakes in the reply reserve,
    #: the system-prompt reserve, and the approx-token safety factor (see
    #: its own docstring) -- so it's passed to `classify_window_by_size`
    #: as the ceiling directly, with `reserved_for_output=0` to avoid
    #: double-reserving the same headroom twice.
    effective_budget = _effective_max_window_tokens(context_length)
    kept: list[str] = []
    excluded: list[dict] = []
    for cid in ids:
        conv = by_id.get(cid)
        if conv is None:
            kept.append(cid)
            continue
        largest = _largest_message_tokens(conv)
        if bf.classify_window_by_size(largest, effective_budget,
                                       reserved_for_output=0) == "context_overflow":
            excluded.append({"conversation_id": cid, "largest_message_tokens": largest})
        else:
            kept.append(cid)
    return kept, excluded


def build_bench_map(eval_set_path: Path = EVAL_SET_PATH, out_path: Path = BENCH_MAP_PATH,
                     *, order: list[str] | None = None, include_cli: bool = False,
                     host: str | None = None, context_length: int | None = None) -> Path:
    """Writes a MapRow-shaped TSV (session_id, local_folder, project_id,
    conversation_name, notes -- exactly `knowledge_index.MapRow`'s fields)
    containing the eval set's conversations. `local_folder` is left blank --
    K1/K2/K4 resolve conversation CONTENT via `local_transcripts` discovery
    + membership in this map's `session_id` set, not via `local_folder`
    (that field only matters for K1's *KNOWLEDGE*.md file-reading, which
    this bench round has no use for). `order`, if given, is a list of
    conversation_ids controlling row order -- pass a shuffled copy of the
    eval set's ids between repeats to satisfy Task 0/2's "vary the order
    between runs" requirement; omit for the eval set's own pinned order.

    By default this is 17 conversations, not 19 -- see `EXCLUDED_CLI_IDS`.
    Confirmed correct against the real backup, 2026-08-18: the remaining 17
    all resolved (`mapped but absent on disk: 0`).

    `host`/`context_length`, if both given, additionally run every
    remaining id through `filter_oversized_conversations` -- a conversation
    whose largest single message can never fit `context_length` (K2 will
    never split one message across a window, so a 400 there is
    deterministic, not transient; see that function's own comment) is
    dropped from the map before K2 ever sees it, and reported on stdout the
    same way `EXCLUDED_CLI_IDS` already is. Omit either (or both) to skip
    this check entirely -- e.g. `prep`'s map build has no candidate model
    yet, so no `context_length` to check against."""
    eval_set = json.loads(eval_set_path.read_text(encoding="utf-8"))
    conversations = {c["conversation_id"]: c for c in eval_set["conversations"]}
    if not include_cli:
        for excluded in EXCLUDED_CLI_IDS:
            conversations.pop(excluded, None)
    ids = order if order is not None else list(conversations)
    ids = [cid for cid in ids if include_cli or cid not in EXCLUDED_CLI_IDS]
    unknown = set(ids) - set(conversations)
    if unknown:
        raise ValueError(f"order contains ids not in the eval set (in scope): {sorted(unknown)}")

    ids, oversized = filter_oversized_conversations(ids, host=host, context_length=context_length)
    if oversized:
        print(f"WARNING: {len(oversized)} conversation(s) excluded from this bench map -- "
              f"largest single message exceeds context_length={context_length}, and K2 never "
              "splits a message across a window, so this would be a deterministic HTTP 400 "
              f"every repeat: {oversized}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        f.write("session_id\tlocal_folder\tproject_id\tconversation_name\tnotes\n")
        for cid in ids:
            c = conversations[cid]
            title = (c.get("title") or "").replace("\t", " ").replace("\n", " ")
            f.write(f"{cid}\t\t{c.get('project', '')}\t{title}\tmodel_bench eval_set_level1\n")
    return out_path


def shuffled_order(eval_set_path: Path = EVAL_SET_PATH, *, seed: int,
                    include_cli: bool = False) -> list[str]:
    """A reproducible-per-seed shuffle of the eval set's conversation ids --
    pass a different `seed` per repeat (e.g. the repeat index) so 'varied
    order' is recorded and reproducible, not a silent, unrecorded shuffle
    each run. `include_cli` defaults to matching `build_bench_map`'s own
    default (False, 17 ids) -- keep these two in sync or a shuffled order
    built here can reference an id `build_bench_map` silently dropped."""
    eval_set = json.loads(eval_set_path.read_text(encoding="utf-8"))
    ids = [c["conversation_id"] for c in eval_set["conversations"]
           if include_cli or c["conversation_id"] not in EXCLUDED_CLI_IDS]
    rng = random.Random(seed)
    rng.shuffle(ids)
    return ids


# ---------------------------------------------------------------------------
# Generic stage runner -- curator_control.run_stage's streaming contract,
# re-implemented here (not imported -- see module docstring) for a plain
# argv this script builds itself.
# ---------------------------------------------------------------------------

def classify_outcome_simple(returncode: int | None, text: str) -> tuple[str, str]:
    """As `curator_control.classify_outcome` -- duplicated here (small,
    pure, config-free) rather than imported, to keep this script out of the
    app tier. See module docstring."""
    lowered = text.lower()
    if returncode is None:
        return "blocked", "did not run"
    if returncode == 0 and "skip" in lowered:
        return "skipped", "no input available"
    if returncode == 0:
        return "success", "completed"
    return "failed", f"exit {returncode}"


class SimpleOutcome:
    """Duck-typed `.state`/`.stdout_tail`, exactly what `bench_failures.
    classify_stage_outcome` needs -- deliberately NOT `curator_control.
    StageOutcome` (that would be an app-tier import)."""

    def __init__(self, state: str, detail: str, returncode: int | None, stdout_tail: str):
        self.state = state
        self.detail = detail
        self.returncode = returncode
        self.stdout_tail = stdout_tail


#: TIMING/TIMING_WINDOW/TIMING_CLAIM lines, exactly as curator_control.py's
#: own `_TIMING_KIND_RE`/`_TIMING_KIND_NAMES` classify them -- duplicated
#: here (two constants, no logic) rather than imported, so this script
#: stays out of the `chronicler.review` app tier entirely, per the module
#: docstring's dependency-direction discussion.
import re as _re
_TIMING_KIND_RE = _re.compile(r"^(TIMING_WINDOW|TIMING_CLAIM|TIMING)\b")
_TIMING_KIND_NAMES = {"TIMING_WINDOW": "window", "TIMING_CLAIM": "claim", "TIMING": "conversation"}


def _line_timing_kind(line: str) -> str | None:
    m = _TIMING_KIND_RE.match(line)
    return _TIMING_KIND_NAMES[m.group(1)] if m else None


def run_stage_subprocess(script_name: str, argv: list[str], *, on_timing_line=None) -> SimpleOutcome:
    """Spawn `script_name` under `chronicler/pipeline/` with `argv`, stream
    its merged stdout+stderr, fire `on_timing_line(kind, ms_per_token,
    line)` for every TIMING/TIMING_WINDOW/TIMING_CLAIM line. `ms_per_token`
    comes from `bench_ledger.parse_timing_line` (already built, already
    tested against real line text) rather than a second parser here."""
    script_path = _PIPE / script_name
    proc = subprocess.Popen([sys.executable, str(script_path), *argv], cwd=str(_REPO_ROOT),
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines: list[str] = []
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        lines.append(line)
        print(line)
        if on_timing_line is not None:
            kind = _line_timing_kind(line)
            if kind is not None:
                parsed = bl.parse_timing_line(line)
                on_timing_line(kind, parsed.get("generation_ms_per_token"), line)
    returncode = proc.wait()
    text = "\n".join(lines)
    state, detail = classify_outcome_simple(returncode, text)
    return SimpleOutcome(state, detail, returncode, "\n".join(lines[-10:]))


# ---------------------------------------------------------------------------
# K1 / K3 -- deterministic, no model, run ONCE and shared across every
# candidate model and every repeat (the map doesn't change per model).
# ---------------------------------------------------------------------------

def run_k1_k3(*, host: str | None = None) -> None:
    print("== K1: knowledge_index (bench-scoped) ==")
    k1_argv = ["--map", str(BENCH_MAP_PATH), "--out", str(K1_OUT)]
    if host:
        k1_argv += ["--host", host]
    outcome = run_stage_subprocess("knowledge_index.py", k1_argv)
    if outcome.state != "success":
        raise RuntimeError(f"K1 did not succeed: {outcome.state} -- {outcome.detail}\n{outcome.stdout_tail}")

    print("== K3: corpus_index (bench-scoped) ==")
    k3_argv = ["--index", str(K1_OUT), "--out", str(K3_OUT),
               "--cache", str(BENCH_DIR / "bench_corpus_cache.json")]
    if host:
        k3_argv += ["--host", host]
    outcome = run_stage_subprocess("corpus_index.py", k3_argv)
    if outcome.state != "success":
        raise RuntimeError(f"K3 did not succeed: {outcome.state} -- {outcome.detail}\n{outcome.stdout_tail}")


# ---------------------------------------------------------------------------
# K2 / K4 for one repeat of one model
# ---------------------------------------------------------------------------

def run_one_repeat(*, model_id: str, repeat_index: int, host: str, endpoint: str,
                    config_fingerprint: str,
                    map_path: Path, cool_down: float = 0.0, model_ttl: float | None = None,
                    context_length: int | None = None) -> None:
    """Runs K2 then K4 once, feeding both into bench_ledger.jsonl and
    (on any failure) bench_failures.jsonl. `repeat_index` names this run's
    slot for `position_in_session` and keeps every repeat's cache/output
    files distinct (never reused -- see module docstring on caching).
    `cool_down_preceded` is NOT a parameter here on purpose -- bench_ledger's
    feeder reads it straight off each real TIMING line's own
    `cool_down_preceded=...` field (K2/K4 compute it themselves from
    whether a `--cool-down` sleep actually happened), which is more
    trustworthy than a caller-supplied guess passed in from outside."""
    tag = f"{model_id.replace(' ', '_')}_r{repeat_index}"
    claims_out = BENCH_DIR / f"claims_{tag}.json"
    claims_cache = BENCH_DIR / f"cache_k2_{tag}.json"
    matches_out = BENCH_DIR / f"matches_{tag}.json"
    matches_cache = BENCH_DIR / f"cache_k4_{tag}.json"

    ledger_feed = bl.make_bench_ledger_feeder(
        bl.DEFAULT_BENCH_LEDGER_PATH, stage="K2", host=host,
        config_fingerprint=config_fingerprint, position_in_session=repeat_index)

    print(f"== K2: extract_claims -- {model_id} repeat {repeat_index} ==")
    k2_argv = ["--map", str(map_path), "--model", model_id,
               "--endpoint", _chat_completions_endpoint(endpoint),
               "--cache", str(claims_cache), "--out", str(claims_out),
               "--cool-down", str(cool_down)]
    if model_ttl is not None:
        k2_argv += ["--model-ttl", str(model_ttl)]
    if host:
        k2_argv += ["--host", host]
    effective_max_window_tokens = _effective_max_window_tokens(context_length)
    if effective_max_window_tokens is not None:
        k2_argv += ["--max-window-tokens", str(effective_max_window_tokens)]
    k2_outcome = run_stage_subprocess("extract_claims.py", k2_argv, on_timing_line=ledger_feed)
    _record_stage_failure(k2_outcome, model_id=model_id, stage="K2", host=host,
                           config_fingerprint=config_fingerprint,
                           position_in_session=repeat_index, context_length=context_length,
                           report_path=claims_out)

    if k2_outcome.state != "success":
        print(f"K2 did not succeed ({k2_outcome.state}) -- skipping K4 for this repeat.")
        return

    ledger_feed_k4 = bl.make_bench_ledger_feeder(
        bl.DEFAULT_BENCH_LEDGER_PATH, stage="K4", host=host,
        config_fingerprint=config_fingerprint, position_in_session=repeat_index)

    print(f"== K4: match_claims -- {model_id} repeat {repeat_index} ==")
    k4_argv = ["--claims", str(claims_out), "--corpus", str(K3_OUT), "--map", str(map_path),
               "--model", model_id, "--endpoint", _chat_completions_endpoint(endpoint),
               "--out", str(matches_out),
               "--cache", str(matches_cache), "--cool-down", str(cool_down)]
    if model_ttl is not None:
        k4_argv += ["--model-ttl", str(model_ttl)]
    k4_outcome = run_stage_subprocess("match_claims.py", k4_argv, on_timing_line=ledger_feed_k4)
    _record_stage_failure(k4_outcome, model_id=model_id, stage="K4", host=host,
                           config_fingerprint=config_fingerprint,
                           position_in_session=repeat_index, context_length=context_length,
                           report_path=matches_out)


def _record_stage_failure(outcome: SimpleOutcome, *, model_id: str, stage: str, host: str,
                           config_fingerprint: str, position_in_session: int,
                           context_length: int | None, report_path: Path) -> None:
    """Whole-stage crash -> bench_failures via classify_stage_outcome.
    Per-conversation parse failures inside an otherwise-successful stage
    (K2's own `--out` report) are a SEPARATE, finer signal -- read the
    report and classify each `parse_failed` conversation too, per
    `bench_failures.classify_conversation_result`."""
    fp = extract_claims.prompt_fingerprint()
    kind = bf.classify_stage_outcome(outcome)
    if kind is not None:
        bf.record_failure({
            "kind": kind, "model_id": model_id, "stage": stage, "host": host,
            "config_fingerprint": config_fingerprint, "prompt_fingerprint": fp,
            "position_in_session": position_in_session,
            "detail": outcome.detail,
        }, bf.DEFAULT_BENCH_FAILURES_PATH)
        return

    if outcome.state != "success" or not report_path.is_file():
        return
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for conv in report.get("conversations", []):
        ckind = bf.classify_conversation_result(conv, context_length=context_length)
        if ckind is not None:
            bf.record_failure({
                "kind": ckind, "model_id": model_id, "stage": stage, "host": host,
                "config_fingerprint": config_fingerprint, "prompt_fingerprint": fp,
                "position_in_session": position_in_session,
                "conversation_id": conv.get("conversation_id"),
                "detail": f"conversation-level parse_failed in {report_path.name}",
            }, bf.DEFAULT_BENCH_FAILURES_PATH)


# ---------------------------------------------------------------------------
# A full sweep -- N repeats, order varied, for one model
# ---------------------------------------------------------------------------

#: Real-run evidence (2026-08-19, gemma-4-e4b, work rig): a warm-up failure
#: is not always the transient "other apps competing for RAM" case
#: `extract_claims.py`'s own `DEFAULT_RETRIES` comment describes -- LM
#: Studio also returns exactly this wording when Just-in-Time model
#: loading is off (or no model is marked for autoload) and nothing has
#: `lms load`-ed the model yet. That condition will not resolve itself: it
#: fails identically on the warm-up call AND on every one of K2's real
#: calls after it, so "proceed anyway" just burns through `repeats` worth
#: of guaranteed-identical crashes (confirmed live: 3 repeats, 3 identical
#: `HTTP 400` traces, ~20 minutes, zero real measurements). `bench_load_
#: cost._http_error_detail` now surfaces the real response body (previously
#: just a generic `"HTTP Error 400: Bad Request"`, which this marker check
#: could never have matched) -- these markers are that body's own wording,
#: matched case-insensitively so a future LM Studio version's exact
#: casing/phrasing changes don't silently stop tripping this.
_MODEL_NOT_LOADED_MARKERS = ("no models loaded", "load a model in the developer page",
                             "lms load")


def _ensure_warm(model_id: str, *, endpoint: str, ttl: float | None) -> None:
    """Make sure `model_id` is already resident before repeat 0's real
    timing window starts. `sweep()` used to rely on LM Studio's own
    just-in-time load firing silently on the first `/v1/chat/completions`
    call inside `run_one_repeat` -- fine as long as a `switch-cost`/
    `cold-start` call happened first in the same session (per the
    runbook's ordering), but a `run` invoked cold with nothing warming it
    first would bake load time into repeat 0's numbers with no record of
    it. This makes that first call explicit and out-of-band: it is thrown
    away, never written to `bench_ledger.jsonl`/`bench_load_cost.jsonl`,
    so it cannot be mistaken for a real measurement.

    Raises `RuntimeError` -- loudly, before a single repeat starts -- when
    the failure's own body text says the model isn't loaded and won't be
    (see `_MODEL_NOT_LOADED_MARKERS`); any other warm-up failure is still
    treated as possibly transient and only warned about, same as before."""
    loaded, err = blc.list_loaded_models(endpoint)
    if err:
        print(f"WARNING: could not confirm loaded-model list ({err}) -- "
              "warming up anyway, just in case.")
    elif model_id in loaded:
        print(f"{model_id!r} already resident -- skipping warm-up call.")
        return
    print(f"Warming up {model_id!r} (not yet resident) before repeat 0 "
          "so its timing window doesn't include a cold JIT load...")
    seconds, werr = blc.measure_call_latency(model_id, endpoint=endpoint, ttl=ttl)
    if werr:
        lowered = werr.lower()
        if any(m in lowered for m in _MODEL_NOT_LOADED_MARKERS):
            raise RuntimeError(
                f"LM Studio will not load {model_id!r}: {werr}\n"
                "This is not transient -- it will fail identically on every repeat. "
                "In LM Studio: load the model yourself first (Developer tab, or "
                f"`lms load {model_id}` in a terminal), or turn on Just-in-Time "
                "model loading in the server settings so a request can load it "
                "automatically, then re-run.")
        print(f"WARNING: warm-up call failed ({werr}) -- proceeding to sweep anyway; "
              "repeat 0 may still be contaminated by load time.")
    else:
        print(f"Warm-up call done in {seconds:.2f}s (discarded, not logged).")


def sweep(*, model_id: str, host: str, endpoint: str, repeats: int,
          config_settings: dict, cool_down_preceded: bool, cool_down: float = 0.0,
          model_ttl: float | None = None) -> None:
    config_fingerprint = bl.build_config_fingerprint(config_settings)
    context_length = config_settings.get("context_length")
    _ensure_warm(model_id, endpoint=endpoint, ttl=model_ttl)
    for r in range(repeats):
        order = shuffled_order(seed=r) if r > 0 else None  # repeat 0 keeps the pinned order
        map_path = build_bench_map(order=order,
                                    out_path=BENCH_DIR / f"bench_map_r{r}.tsv",
                                    host=host, context_length=context_length)
        run_one_repeat(model_id=model_id, repeat_index=r, host=host, endpoint=endpoint,
                        config_fingerprint=config_fingerprint,
                        map_path=map_path,
                        cool_down=cool_down, model_ttl=model_ttl,
                        context_length=context_length)
    print(f"\nSweep done: {model_id}, {repeats} repeat(s), "
          f"config_fingerprint={config_fingerprint}")
    print("NOTE: cool_down_preceded above is what you TOLD this sweep, not independently "
          "verified against LM Studio's own state -- make sure it matches what you actually did.")


# ---------------------------------------------------------------------------
# Load cost between two models
# ---------------------------------------------------------------------------

def switch_cost(*, from_model: str, to_model: str, host: str, endpoint: str,
                 config_settings: dict, ttl: float | None = None) -> None:
    config_fingerprint = bl.build_config_fingerprint(config_settings)
    result = blc.measure_switch_cost(from_model, to_model, endpoint=endpoint, ttl=ttl)
    blc.record_switch(result, host=host, config_fingerprint=config_fingerprint, ttl=ttl,
                       path=blc.DEFAULT_BENCH_LOAD_COST_PATH)
    print(f"switch {from_model} -> {to_model}: "
          f"switch_seconds={result.switch_seconds} steady={result.to_model_steady_seconds} "
          f"tax={result.switch_tax_seconds} error={result.error}")


def cold_start(*, model_id: str, host: str, endpoint: str, config_settings: dict,
                ttl: float | None = None) -> None:
    config_fingerprint = bl.build_config_fingerprint(config_settings)
    loaded, err = blc.list_loaded_models(endpoint)
    if err:
        print(f"WARNING: could not confirm loaded-model list ({err}) -- proceeding anyway.")
    elif model_id in loaded:
        print(f"WARNING: {model_id!r} is already in the loaded list {loaded} -- "
              "this will not measure a real cold start. Unload it in LM Studio first.")
    result = blc.measure_cold_start(model_id, endpoint=endpoint, ttl=ttl)
    blc.record_cold_start(result, host=host, config_fingerprint=config_fingerprint, ttl=ttl,
                           path=blc.DEFAULT_BENCH_LOAD_COST_PATH)
    print(f"cold start {model_id}: cold={result.cold_seconds} steady={result.steady_seconds} "
          f"tax={result.cold_start_tax_seconds} error={result.error}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _config_settings_from_args(args) -> dict:
    settings = {}
    if args.context_length is not None:
        settings["context_length"] = args.context_length
    if args.quantisation is not None:
        settings["quantisation"] = args.quantisation
    if args.gpu_offload_layers is not None:
        settings["gpu_offload_layers"] = args.gpu_offload_layers
    if args.kv_cache_type is not None:
        settings["kv_cache_type"] = args.kv_cache_type
    if args.flash_attention is not None:
        settings["flash_attention"] = args.flash_attention
    if args.batch_size is not None:
        settings["batch_size"] = args.batch_size
    if args.model_ttl is not None:
        settings["ttl_seconds"] = args.model_ttl
    return settings


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prep", help="build the bench map + run K1/K3 once")
    p_prep.add_argument("--host")

    def _add_config_args(p):
        p.add_argument("--context-length", type=int, default=None)
        p.add_argument("--quantisation", default=None)
        p.add_argument("--gpu-offload-layers", type=int, default=None)
        p.add_argument("--kv-cache-type", default=None)
        p.add_argument("--flash-attention", default=None)
        p.add_argument("--batch-size", type=int, default=None)

    p_run = sub.add_parser("run", help="sweep one model over N repeats")
    p_run.add_argument("--model", required=True)
    p_run.add_argument("--host", required=True)
    p_run.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p_run.add_argument("--repeats", type=int, default=3)
    p_run.add_argument("--cool-down", type=float, default=0.0)
    p_run.add_argument("--model-ttl", type=float, default=None)
    p_run.add_argument("--cool-down-preceded", choices=["true", "false"], required=True,
                        help="did a real cool-down actually precede this sweep's first call? "
                             "no default -- state what actually happened.")
    _add_config_args(p_run)

    p_switch = sub.add_parser("switch-cost", help="measure switch cost between two models")
    p_switch.add_argument("--from-model", required=True)
    p_switch.add_argument("--to-model", required=True)
    p_switch.add_argument("--host", required=True)
    p_switch.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p_switch.add_argument("--model-ttl", type=float, default=None)
    _add_config_args(p_switch)

    p_cold = sub.add_parser("cold-start", help="measure cold start for one model "
                                                "(unload it in LM Studio first)")
    p_cold.add_argument("--model", required=True)
    p_cold.add_argument("--host", required=True)
    p_cold.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    p_cold.add_argument("--model-ttl", type=float, default=None)
    _add_config_args(p_cold)

    args = ap.parse_args()

    if args.command == "prep":
        build_bench_map()
        print(f"bench map scoped to 17/19 eval-set conversations -- "
              f"{len(EXCLUDED_CLI_IDS)} cli:-store id(s) excluded (K0/K1's discovery "
              f"is Cowork-store only, a structural limit, not a config fix): "
              f"{list(EXCLUDED_CLI_IDS)}")
        run_k1_k3(host=args.host)
        print(f"prep done -- map: {BENCH_MAP_PATH}, K1: {K1_OUT}, K3: {K3_OUT}")
        return

    if args.command == "run":
        config_settings = _config_settings_from_args(args)
        sweep(model_id=args.model, host=args.host, endpoint=args.endpoint,
              repeats=args.repeats, config_settings=config_settings,
              cool_down_preceded=(args.cool_down_preceded == "true"),
              cool_down=args.cool_down, model_ttl=args.model_ttl)
        return

    if args.command == "switch-cost":
        config_settings = _config_settings_from_args(args)
        switch_cost(from_model=args.from_model, to_model=args.to_model, host=args.host,
                    endpoint=args.endpoint, config_settings=config_settings, ttl=args.model_ttl)
        return

    if args.command == "cold-start":
        config_settings = _config_settings_from_args(args)
        cold_start(model_id=args.model, host=args.host, endpoint=args.endpoint,
                   config_settings=config_settings, ttl=args.model_ttl)
        return


if __name__ == "__main__":
    main()
