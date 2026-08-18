"""bench_report.py -- Task 5, docs/COWORK_BRIEF_model_bench.md.

The comparison: throughput, quality, reliability and load cost side by
side, spread stated, per machine, per (model, config, prompt) -- reading
straight from the three logs Tasks 2-4 already built
(`bench_ledger.jsonl`, `bench_failures.jsonl`, `bench_load_cost.jsonl`) plus
K2's own `--out` report for quality. **This round declares no tiers** (the
brief's own words) -- this module renders the evidence and states plainly
what it does and does not support; the tier ladder itself is a separate,
later ruling that cites this report, not something this module decides.

**This module has never seen real data.** Task 0 (the control run) has not
been taken on this machine, so nothing here has been run against a
populated `bench_ledger.jsonl`. Every function is exercised in `tests/
tester_bench_report.py` against hand-built entries in the exact shapes
Tasks 2-4 already produce and K2's `_build_report` already writes -- that
proves the AGGREGATION and COMPARISON logic is correct. It does not, and
cannot, prove what a real comparison will say; that only exists once Task 0
and the candidate sweeps have actually run.

**"Indistinguishable" is a real verdict, not a missing one.** The brief:
"Two candidates indistinguishable within their spread are reported as
indistinguishable -- not tie-broken by preference." `compare_medians`
returns exactly that when two summaries' IQRs (`p25..p75`) overlap, and
refuses to call ANY verdict (not even "indistinguishable") when either side
has fewer than two repeats -- "a single run cannot carry a claim against
the control's measured spread" applies here as code, not just as prose in
the brief.

**Quality is read from K2's own report, not invented.** `quote_rejection_
rate`/`claims_extracted`/`claims_rejected` are fields `extract_claims.
_build_report` already writes to every `--out` file; `quality_from_k2_
report` reads them, unmodified, into `acceptance_rate = 1 - quote_
rejection_rate`. "Correctness where ground truth exists" (the brief's other
quality clause) is `None` on every row this round -- Task 1's Level 2
ground truth was never built (see `tests/model_bench/README.md`), and a
correctness figure with nothing to check it against would be exactly the
fabricated precision this whole brief refuses.

Stdlib only, `chronicler.pipeline` tier. Imports `ledger` (for the
production baseline) and reads the shapes `bench_ledger`/`bench_failures`/
`bench_load_cost` define, but does not import `chronicler.review`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chronicler.pipeline import bench_failures as bf
from chronicler.pipeline import bench_ledger as bl
from chronicler.pipeline import ledger


# ---------------------------------------------------------------------------
# One comparable unit's row -- everything Task 5's own decision-matrix table
# asks for: throughput, unit cost, quality, reliability, load cost.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComparisonRow:
    source: str  # "bench" | "production"
    host: str
    model_id: str
    stage: str
    cool_down_preceded: bool
    config_fingerprint: str | None
    prompt_fingerprint: str | None
    #: throughput
    n: int
    median_ms_per_token: float | None
    p25_ms_per_token: float | None
    p75_ms_per_token: float | None
    #: unit cost
    median_wall_clock_seconds: float | None
    #: quality
    acceptance_rate: float | None
    correctness_rate: float | None  # always None this round -- see module docstring
    #: reliability
    failure_counts: dict[str, int]
    failure_rate: float | None
    #: load cost
    cold_start_tax_seconds: float | None
    switch_tax_seconds: float | None
    both_resident: bool | None
    #: caveats a reader must not miss (e.g. production's "no config
    #: fingerprint, not taken over the evaluation set")
    caveats: tuple[str, ...] = field(default_factory=tuple)


def quality_from_k2_report(report: dict) -> tuple[float | None, float | None]:
    """`(acceptance_rate, correctness_rate)` from a real K2 `--out` report
    dict. `acceptance_rate` is `1 - quote_rejection_rate` when the report
    offered at least one claim (extracted or rejected); `None` when nothing
    was offered at all (never fabricated as 1.0 or 0.0 from an empty
    denominator). `correctness_rate` is always `None` -- see module
    docstring."""
    extracted = report.get("claims_extracted", 0)
    rejected = report.get("claims_rejected", 0)
    if extracted + rejected == 0:
        return None, None
    rejection_rate = report.get("quote_rejection_rate")
    if rejection_rate is None:
        return None, None
    return 1.0 - rejection_rate, None


def reliability_for_unit(failure_entries: list[dict], *, model_id: str, stage: str,
                          config_fingerprint: str, prompt_fingerprint: str,
                          successful_n: int) -> tuple[dict[str, int], float | None]:
    """`(counts_by_kind, failure_rate)` for one `(model, stage, config,
    prompt)` unit. `failure_rate` is `failures / (failures + successful_n)`
    -- `successful_n` is the caller's own count of successful measurements
    for the SAME unit (typically a `BenchSummary.n` from `bench_ledger.
    summarize`), so the denominator is real attempted units, not an
    assumption. `None` when there is no evidence at all (zero failures AND
    zero successes) -- a unit nothing was ever tried on has no rate to
    report, not a rate of 0.0."""
    counts = bf.counts_by_kind(failure_entries, model_id=model_id, stage=stage,
                                config_fingerprint=config_fingerprint,
                                prompt_fingerprint=prompt_fingerprint)
    total_failures = sum(counts.values())
    total = total_failures + successful_n
    rate = (total_failures / total) if total else None
    return counts, rate


def load_cost_for_unit(load_cost_entries: list[dict], *, model_id: str,
                        config_fingerprint: str) -> tuple[float | None, float | None, bool | None]:
    """`(cold_start_tax_seconds, switch_tax_seconds, both_resident)` for one
    `(model, config)` -- the MOST RECENT matching entry of each kind wins
    (entries are append-only and read in file order, so the last match is
    the newest measurement), never averaged across repeats silently, since
    Task 4 does not define what averaging a cold-start figure would even
    mean. `None` for anything never measured."""
    cold_tax = None
    switch_tax = None
    both_resident = None
    for e in load_cost_entries:
        if e.get("config_fingerprint") != config_fingerprint:
            continue
        kind = e.get("kind")
        if kind == "cold_start" and e.get("model_id") == model_id \
                and e.get("cold_start_tax_seconds") is not None:
            cold_tax = e["cold_start_tax_seconds"]
        elif kind == "switch" and e.get("to_model_id") == model_id \
                and e.get("switch_tax_seconds") is not None:
            switch_tax = e["switch_tax_seconds"]
        elif kind == "residency" and e.get("both_resident") is not None \
                and model_id in (e.get("model_id"), e.get("to_model_id")):
            both_resident = e["both_resident"]
    return cold_tax, switch_tax, both_resident


def build_row(*, source: str, host: str, model_id: str, stage: str, cool_down_preceded: bool,
              config_fingerprint: str | None, prompt_fingerprint: str | None,
              bench_entries: list[dict] | None = None, ledger_entries: list[dict] | None = None,
              failure_entries: list[dict] | None = None,
              load_cost_entries: list[dict] | None = None,
              k2_report: dict | None = None, caveats: tuple[str, ...] = ()) -> ComparisonRow:
    """Assemble one row. `source="bench"` reads `bl.summarize` over
    `bench_entries` (requires `config_fingerprint`/`prompt_fingerprint`).
    `source="production"` reads `ledger.summarize` over `ledger_entries`
    instead (production has no fingerprints -- both are left `None` and
    `caveats` should say why, per the brief: "shown as such and labelled
    production rather than bench")."""
    if source == "bench":
        summary = bl.summarize(bench_entries or [], model_id=model_id, stage=stage,
                                cool_down_preceded=cool_down_preceded,
                                config_fingerprint=config_fingerprint,
                                prompt_fingerprint=prompt_fingerprint)
    elif source == "production":
        summary = ledger.summarize(ledger_entries or [], model_id=model_id, stage=stage,
                                    cool_down_preceded=cool_down_preceded)
    else:
        raise ValueError(f"source must be 'bench' or 'production', got {source!r}")

    n = summary.n if summary else 0
    median_ms = summary.median_ms_per_token if summary else None
    p25 = summary.p25_ms_per_token if summary else None
    p75 = summary.p75_ms_per_token if summary else None
    median_wall = getattr(summary, "median_wall_clock_seconds", None) if summary else None

    acceptance, correctness = quality_from_k2_report(k2_report) if k2_report else (None, None)

    if source == "bench" and config_fingerprint and prompt_fingerprint:
        counts, fail_rate = reliability_for_unit(
            failure_entries or [], model_id=model_id, stage=stage,
            config_fingerprint=config_fingerprint, prompt_fingerprint=prompt_fingerprint,
            successful_n=n)
    else:
        counts, fail_rate = {k: 0 for k in bf.FAILURE_KINDS}, None

    if source == "bench" and config_fingerprint:
        cold_tax, switch_tax, both_resident = load_cost_for_unit(
            load_cost_entries or [], model_id=model_id, config_fingerprint=config_fingerprint)
    else:
        cold_tax, switch_tax, both_resident = None, None, None

    return ComparisonRow(
        source=source, host=host, model_id=model_id, stage=stage,
        cool_down_preceded=cool_down_preceded,
        config_fingerprint=config_fingerprint, prompt_fingerprint=prompt_fingerprint,
        n=n, median_ms_per_token=median_ms, p25_ms_per_token=p25, p75_ms_per_token=p75,
        median_wall_clock_seconds=median_wall,
        acceptance_rate=acceptance, correctness_rate=correctness,
        failure_counts=counts, failure_rate=fail_rate,
        cold_start_tax_seconds=cold_tax, switch_tax_seconds=switch_tax,
        both_resident=both_resident, caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Comparison -- "indistinguishable" is a real verdict, never tie-broken.
# ---------------------------------------------------------------------------

def detectable_difference_floor(control_row: ComparisonRow) -> float | None:
    """The smallest relative difference this bench can honestly claim to
    see, derived from Task 0's own control spread -- the brief's own words:
    "if the control's own p25-p75 spans 30%, the bench cannot honestly
    report a 20% difference between models." Returns `(p75-p25)/median` as
    a fraction, or `None` when the control row carries no spread yet (Task
    0 not run) -- never a default/assumed floor."""
    if control_row.median_ms_per_token in (None, 0) or control_row.p25_ms_per_token is None \
            or control_row.p75_ms_per_token is None:
        return None
    return (control_row.p75_ms_per_token - control_row.p25_ms_per_token) / control_row.median_ms_per_token


def compare_medians(a: ComparisonRow, b: ComparisonRow) -> str:
    """`"a_faster"` / `"b_faster"` / `"indistinguishable"` / `"insufficient_
    data"`. `"insufficient_data"` when either side has fewer than 2 repeats
    (`n < 2`) -- a single run cannot carry a claim against any spread, so no
    verdict is offered at all, not even "indistinguishable" (which itself
    presumes both sides HAD a measurable spread to compare). Otherwise,
    `"indistinguishable"` whenever the two IQRs (`[p25, p75]`) overlap --
    the brief's own words: "not tie-broken by preference." Only when the
    IQRs are cleanly separated does a direction get named."""
    if a.n < 2 or b.n < 2:
        return "insufficient_data"
    if None in (a.p25_ms_per_token, a.p75_ms_per_token, b.p25_ms_per_token, b.p75_ms_per_token):
        return "insufficient_data"
    overlap = a.p25_ms_per_token <= b.p75_ms_per_token and b.p25_ms_per_token <= a.p75_ms_per_token
    if overlap:
        return "indistinguishable"
    return "a_faster" if a.median_ms_per_token < b.median_ms_per_token else "b_faster"


# ---------------------------------------------------------------------------
# Rendering -- a plain markdown table, per the brief's "a rendered table."
# ---------------------------------------------------------------------------

def _fmt(v: Any, *, pct: bool = False, digits: int = 2) -> str:
    if v is None:
        return "—"
    if pct:
        return f"{v:.1%}"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def render_markdown_table(rows: list[ComparisonRow]) -> str:
    """One markdown table, one row per `(source, host, model, config,
    prompt)` unit -- every column the decision matrix asks for
    (throughput, unit cost, quality, reliability, load cost), an em-dash
    for anything not measured (never a fabricated 0 or blank cell that
    reads as "checked and found zero")."""
    header = ("| source | host | model | stage | config | prompt | n | "
              "throughput ms/tok (p25–p75) | unit cost s | acceptance | "
              "failure rate | cold-start tax s | switch tax s | 2-resident |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    lines = [header, sep]
    for r in rows:
        cfg = (r.config_fingerprint or "—")[:8]
        pf = (r.prompt_fingerprint or "—")[:8]
        throughput = (f"{_fmt(r.median_ms_per_token)} ({_fmt(r.p25_ms_per_token)}"
                      f"–{_fmt(r.p75_ms_per_token)})" if r.median_ms_per_token is not None
                      else "—")
        lines.append(
            f"| {r.source} | {r.host} | {r.model_id} | {r.stage} | {cfg} | {pf} | {r.n} | "
            f"{throughput} | {_fmt(r.median_wall_clock_seconds)} | "
            f"{_fmt(r.acceptance_rate, pct=True) if r.acceptance_rate is not None else '—'} | "
            f"{_fmt(r.failure_rate, pct=True) if r.failure_rate is not None else '—'} | "
            f"{_fmt(r.cold_start_tax_seconds)} | {_fmt(r.switch_tax_seconds)} | "
            f"{_fmt(r.both_resident)} |")
    if any(r.caveats for r in rows):
        lines.append("")
        for r in rows:
            for c in r.caveats:
                lines.append(f"> **{r.source}/{r.model_id}**: {c}")
    return "\n".join(lines)
