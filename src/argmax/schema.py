"""The stored record types.

This module is the implementation of files/04-data-and-instrumentation-spec.md.
Every field here exists because its absence cost the predecessor a specific
analysis. Three defects trace to fields nobody decided to write:

  1. only a mean entropy scalar was retained instead of per-token logprob
     arrays, permanently foreclosing final-answer margin analysis
  2. per-problem gate outcomes were never persisted, so a paired bootstrap
     would have needed a full confirmatory re-run and the claim was deleted
  3. a matched-compute baseline was never implemented, yet prose describing
     one reached the submitted draft

Rules that the field list encodes:

  - Store raw, derive later. Any field computable from a stored raw response
    is derived and may be recomputed. Any field not stored is gone.
  - Nothing is derived-only. Derived tables rebuild identically from raw.
  - Absence is data. Truncated, unparseable and failed samples get records.
  - Verbatim blocks (`usage_raw`, `logprobs_raw`, `response_extras`) are never
    filtered at write time. Selecting fields at write time is how defect 1
    happened.

Adding a field is cheap: bump SCHEMA_VERSION and make readers branch on it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: 2: the reported interval on a derived record changed meaning. In version 1,
#: `ProblemRecord.ci_low/ci_high` were percentiles of the Monte Carlo draws. In
#: version 2 they are the pool bootstrap, the Monte Carlo layer reports a
#: convergence half-width instead, and the paired differences that decide curve
#: shape are persisted per replicate as `PairedDifference`. A reader that does
#: not branch on this will compare two different quantities and see a trend.
SCHEMA_VERSION = 2


class Split(StrEnum):
    exploratory = "exploratory"
    confirmatory = "confirmatory"


class ModelClass(StrEnum):
    non_reasoning = "non_reasoning"
    reasoning = "reasoning"


class OutcomeClass(StrEnum):
    """The four outcomes that are easy to collapse and expensive to collapse.

    `truncated_no_answer` is a first-class result, not an error. The phase 14b
    probe was abandoned because reasoning models exhausted the output budget
    on hidden chain of thought. That is a finding about the cost model. It is
    counted, flagged and reported, never retried into oblivion and never
    scored as incorrect without the flag travelling alongside.
    """

    answered = "answered"
    no_answer_visible = "no_answer_visible"
    truncated_no_answer = "truncated_no_answer"
    api_failure = "api_failure"


#: Outcomes that are data. `api_failure` is not data; it is a recorded gap.
DATA_OUTCOMES = frozenset(
    {
        OutcomeClass.answered,
        OutcomeClass.no_answer_visible,
        OutcomeClass.truncated_no_answer,
    }
)


class SplitMethod(StrEnum):
    api_field = "api_field"
    delimiter = "delimiter"
    none = "none"


class DrawScheme(StrEnum):
    """Subsample without replacement: emulates "what if I had only drawn N".

    With replacement inflates agreement through duplicates. Recorded in the
    manifest; never left to a library default.
    """

    without_replacement = "without_replacement"
    with_replacement = "with_replacement"


class UnansweredPolicy(StrEnum):
    """Pre-registered, decided once, applied everywhere, recorded in manifest."""

    exclude = "exclude"
    score_as_wrong = "score_as_wrong"


class CurveShape(StrEnum):
    monotone_up = "monotone_up"
    monotone_down = "monotone_down"
    rise_then_fall = "rise_then_fall"
    flat_within_ci = "flat_within_ci"


class Strict(BaseModel):
    """Reject unknown fields everywhere except the verbatim passthrough blocks."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class Sample(Strict):
    """One JSON object per line, per API call.

    Required fields are non-default; the schema test fails without them.
    """

    # --- 3.1 identity and provenance ---
    schema_version: int = Field(default=SCHEMA_VERSION)
    sample_key: str
    run_id: str
    split: Split
    benchmark: str
    benchmark_version_hash: str
    problem_id: str
    problem_hash: str  # includes frozen option order
    sample_index: int

    # --- 3.2 request ---
    model_requested: str
    model_returned: str  # asserted equal to requested; recorded when it is not
    param_hash: str
    temperature: float | None
    top_p: float | None
    max_tokens: int
    seed: int | None
    stop: list[str]
    prompt_hash: str  # prompt TEXT is never stored; see doc 3 s5
    prompt_template_id: str
    request_timestamp_utc: str
    attempt_count: int
    latency_ms: int | None = None

    # --- 3.3 response, verbatim ---
    raw_text: str  # complete completion, unmodified, unstripped
    finish_reason: str  # provider value, NOT normalized
    usage_raw: dict[str, Any]  # the ENTIRE usage block, verbatim
    api_response_id: str | None = None
    logprobs_raw: dict[str, Any] | None = None
    response_extras: dict[str, Any] = Field(default_factory=dict)

    # --- 3.4 reasoning split ---
    split_method: SplitMethod
    split_ok: bool  # false when an opening delimiter has no close, which is
    # exactly the truncated-mid-thought case
    reasoning_text: str | None = None
    answer_text: str | None = None
    reasoning_tokens: int | None = None
    reasoning_tokens_est: int | None = None
    reasoning_tokens_est_method: str | None = None  # recorded, never silently
    # swapped

    # --- 3.5 truncation and outcome ---
    truncated: bool  # finish_reason == "length"
    hit_ceiling: bool  # completion_tokens >= max_tokens; kept separate because
    # providers disagree about finish_reason
    outcome_class: OutcomeClass
    error_type: str | None = None
    error_message: str | None = None

    # --- 3.6 extraction (written by the offline extractor) ---
    extractor_version: str
    extraction_pass: int | None = None  # which of the five ladder passes fired
    extracted_answer: str | None = None
    answer_span_chars: tuple[int, int] | None = None
    answer_span_tokens: tuple[int, int] | None = None
    is_correct: bool | None = None

    # --- 3.7 cost ---
    pricing_snapshot_id: str
    cost_usd_est: float

    # --- retention bookkeeping (doc 4 s7) ---
    logprob_coverage: float = 1.0  # < 1.0 wherever hidden-reasoning logprobs
    # were subsampled. Silent partial coverage
    # would be defect 1 in a new costume.

    @model_validator(mode="after")
    def _no_coercion(self) -> Sample:
        """`is_correct` is never coerced to false for a missing answer.

        Whether unanswered samples are excluded or scored as wrong is a
        pre-registered analysis decision applied downstream, not a write-time
        default.
        """
        if self.extracted_answer is None and self.is_correct is False:
            raise ValueError(
                "is_correct=False with extracted_answer=None: "
                "a missing answer is null, never wrong"
            )
        if (
            self.error_type is not None
            and self.outcome_class != OutcomeClass.api_failure
        ):
            raise ValueError("error_type set on a non-api_failure record")
        return self

    @model_validator(mode="after")
    def _span_integrity(self) -> Sample:
        """A span must point inside the array it indexes."""
        for name, span, limit in (
            ("answer_span_chars", self.answer_span_chars, len(self.raw_text)),
            ("answer_span_tokens", self.answer_span_tokens, None),
        ):
            if span is None:
                continue
            lo, hi = span
            if lo < 0 or hi < lo:
                raise ValueError(f"{name} is not a valid range: {span}")
            if limit is not None and hi > limit:
                raise ValueError(f"{name} ends past the array it indexes: {span}")
        return self


class ProblemRecord(Strict):
    """Derived, per problem per model. Rebuildable from samples, persisted anyway
    because it is what analysis and figures read."""

    schema_version: int = Field(default=SCHEMA_VERSION)

    problem_id: str
    benchmark: str
    tier: str
    domain: str | None
    subdomain: str | None
    n_options: int
    correct_option: str
    model_slug: str

    n_samples_stored: int
    n_answered: int
    n_truncated: int
    n_no_answer: int
    n_api_failure: int

    single_sample_accuracy: float | None
    unanswered_sample_policy: UnansweredPolicy  # recorded, not assumed

    # vote_accuracy and its CI, keyed by N in the grid.
    #
    # ci_low/ci_high are the POOL BOOTSTRAP: the uncertainty of having drawn
    # only M samples from the model. That is the only thing this codebase
    # calls a CI. Monte Carlo noise, from taking B subsample draws rather than
    # all C(M, N) of them, is not an interval and is reported as
    # mc_halfwidth below.
    vote_accuracy: dict[int, float]
    ci_low: dict[int, float]
    ci_high: dict[int, float]
    interval_method: str  # "pool_bootstrap"
    n_bootstrap: int
    mc_halfwidth: dict[int, float]
    n_draws: int
    draw_scheme: DrawScheme
    seed_recipe: str

    backfire: dict[int, bool]  # vote_accuracy[N] < single_sample_accuracy
    # The same question asked of the paired difference: does the interval on
    # vote_accuracy[N] - single_sample_accuracy exclude zero on the low side?
    # `backfire` above is the published point-estimate definition, kept for
    # comparability; this one is the claim that can be defended.
    backfire_significant: dict[int, bool] = Field(default_factory=dict)
    peak_N: int | None
    peak_accuracy: float | None
    curve_shape: CurveShape | None

    # carried over from the predecessor for comparability
    plurality_agreement: float | None = None
    mean_token_entropy: float | None = None

    # new, enabled by retained logprobs; computed over the ANSWER SPAN only
    # rather than the whole completion. This is the analysis the published
    # paper could not run.
    answer_token_logprob_mean: float | None = None
    answer_margin_vs_runner_up: float | None = None
    answer_entropy: float | None = None

    logprob_coverage: float = 1.0


class PairedDifference(Strict):
    """One row per (problem, model, comparison, N, bootstrap replicate).

    The per-replicate paired differences behind every curve-shape claim.
    Persisted in full rather than summarised, for the same reason gate
    outcomes are: defect 2 was keeping the aggregate and discarding the rows,
    which turned a paired bootstrap into a full confirmatory re-run and got
    the claim deleted instead.

    With these rows a different level, a different multiple-comparison
    correction, or a paired test across problems is a groupby.

    `comparison` is `vs_single` (vote_accuracy[N] minus single_sample_accuracy)
    or `adjacent` (vote_accuracy[N] minus vote_accuracy[N_other], N_other the
    previous grid point). Both are formed INSIDE a bootstrap replicate, where
    the two quantities share a resampled pool; differencing two independently
    computed marginals instead would throw away the pairing that makes the
    comparison tight.
    """

    problem_id: str
    model_slug: str
    comparison: str  # "vs_single" | "adjacent"
    N: int
    N_other: int | None
    replicate: int
    difference: float


class GateOutcome(Strict):
    """One row per (gate, threshold, problem, model, N). The fix for defect 2.

    With these rows a paired bootstrap is a groupby, not a re-run.
    """

    gate_name: str
    gate_version: str
    threshold: float
    threshold_source: str  # "preregistered" | "exploratory"

    problem_id: str
    model_slug: str
    N: int

    gate_statistic: float  # the raw value compared against the threshold
    decision: str  # "route" | "hold"
    accuracy_under_decision: float | None
    # included because the interesting property of a gate that does not move
    # accuracy may be that it reaches the same accuracy at fewer samples
    samples_consumed_under_decision: int


class BudgetMatched(Strict):
    """One row per (problem, model, total token budget T, strategy).

    The fix for defect 3, and the one that requires the most discipline,
    because the failure mode is a fluent sentence rather than a missing file.

    Rule: no sentence in any draft may describe a compute-matched comparison
    unless a claim_id in that sentence resolves to rows here.
    """

    problem_id: str
    model_slug: str
    budget_tokens: int
    strategy_id: str
    n_samples_used: int
    max_tokens_per_sample: int
    tokens_actually_consumed: int  # from stored usage_raw, not from the plan
    accuracy_under_strategy: float | None
    ci_low: float | None
    ci_high: float | None
    claim_ids: list[str]


class RunManifest(Strict):
    """One per run, at runs/<run_id>/manifest.json.

    What a reviewer asking "what exactly did you run" is handed. It should
    answer that question without opening a single script.
    """

    run_id: str
    phase_id: str
    split: Split
    started_utc: str
    ended_utc: str | None

    git_sha: str
    git_dirty: bool
    lockfile_hash: str

    dataset_version_hash: str
    prompt_template_id: str
    extractor_version: str

    params_by_model: dict[str, dict[str, Any]]
    param_hash_by_model: dict[str, str]
    capabilities_id_by_model: dict[str, str]
    model_string_requested: dict[str, str]
    model_string_returned: dict[str, str]

    pricing_snapshot_id: str
    prereg_tag: str | None  # required and non-null when split == confirmatory

    unanswered_sample_policy: UnansweredPolicy
    draw_scheme: DrawScheme
    n_grid: list[int]
    M: int
    logprob_subsample_fraction: float | None = None

    realized_cost_usd: float = 0.0
    counts_by_outcome_class: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _confirmatory_needs_tag(self) -> RunManifest:
        if self.split == Split.confirmatory and not self.prereg_tag:
            raise ValueError("confirmatory run without a prereg_tag")
        return self

    @model_validator(mode="after")
    def _grid_fits_M(self) -> RunManifest:
        """A CI at the endpoint requires M > max(grid).

        Subsampling without replacement at N == M yields exactly one possible
        draw, so the endpoint has no subsample variance and no CI. The
        predecessor hit this and reported a bare point estimate. This is a
        warning-level fact rather than an error: a bare endpoint is a legal
        choice, but it must be a deliberate one, so it is asserted against the
        manifest by tests/falsification.py rather than silently allowed here.
        """
        if self.n_grid and max(self.n_grid) > self.M:
            raise ValueError(
                f"n_grid tops out at {max(self.n_grid)} but only M={self.M} "
                "samples are stored; the curve cannot reach its own endpoint"
            )
        return self


#: Fields marked R in doc 4 s3. tests/test_schema.py asserts every raw record
#: carries all of them with the right type.
REQUIRED_SAMPLE_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "sample_key",
        "run_id",
        "split",
        "benchmark",
        "benchmark_version_hash",
        "problem_id",
        "problem_hash",
        "sample_index",
        "model_requested",
        "model_returned",
        "param_hash",
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
        "stop",
        "prompt_hash",
        "prompt_template_id",
        "request_timestamp_utc",
        "attempt_count",
        "raw_text",
        "finish_reason",
        "usage_raw",
        "split_method",
        "split_ok",
        "truncated",
        "hit_ceiling",
        "outcome_class",
        "extraction_pass",
        "extractor_version",
        "pricing_snapshot_id",
        "cost_usd_est",
    }
)
