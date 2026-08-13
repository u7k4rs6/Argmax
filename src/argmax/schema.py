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
#:
#: 3: `ProblemRecord` carries `answer_rate` and `answer_rate_by_n`, both
#: required (doc 4 s4 and s4.1). A truncated sample casts no vote, so the pool
#: that votes at a token cap is smaller than N and is enriched for samples that
#: answer fast. Every accuracy therefore travels with the rate that qualifies
#: it. Records written at version 2 or earlier have no such rate and their
#: accuracies are unqualified. That is a fact about those records and it is not
#: backfilled: the rate cannot be recovered from a table that never stored the
#: counts it is computed from.
#: 4: `ProblemRecord` carries `answer_margin_censored` and `answer_margin_k`
#: beside the margin. The provider returns k alternatives per token and k slots
#: need not contain every option letter, so a margin is a measurement when they
#: all appear and a lower bound when one does not. A version 3 record's margin
#: does not say which it is.
SCHEMA_VERSION = 4

#: The version at which `answer_rate` became required. Readers branch here.
ANSWER_RATE_SCHEMA_VERSION = 3


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

    #: n_answered / n_samples_stored. Required, and published beside every
    #: accuracy this record carries, including when it reads 1.0. See doc 4
    #: s4.1: the pool that votes is not a random subset of the pool that was
    #: drawn, it is the subset that finished answering inside the token cap.
    answer_rate: float
    #: The same quantity per grid point: the mean fraction of the N drawn
    #: samples that cast a vote, averaged over the subsample draws. Under the
    #: `exclude` policy this is 1.0 at every N by construction, because the
    #: pool is pre-filtered, and it is still published at every N rather than
    #: omitted as uninteresting. Under `score_as_wrong` it varies.
    answer_rate_by_n: dict[int, float]

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
    #: The margin never travels without its censoring flag and its k. The
    #: provider returns k alternatives per token, and k slots need not contain
    #: every option letter; when one is missing the margin is a lower bound,
    #: not a measurement. A margin published without that distinction is a
    #: number that silently means two different things. See doc 4 s4.1 for the
    #: same argument applied to accuracy and its answer rate.
    answer_margin_vs_runner_up: float | None = None
    answer_margin_censored: bool | None = None
    answer_margin_k: int | None = None
    answer_entropy: float | None = None

    logprob_coverage: float = 1.0

    @model_validator(mode="after")
    def _answer_rate_is_versioned(self) -> ProblemRecord:
        """A record carrying an answer rate cannot claim a version without one.

        The version is the branch point for readers. A v2 record has no rate
        and its accuracies are unqualified; a record that claims v2 while
        carrying a rate would defeat the branch and let an unqualified
        accuracy be read as a qualified one.
        """
        if self.schema_version < ANSWER_RATE_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version {self.schema_version} predates answer_rate "
                f"(added at {ANSWER_RATE_SCHEMA_VERSION}); a record carrying "
                "the field must declare the version that introduced it"
            )
        return self

    @model_validator(mode="after")
    def _answer_rate_covers_the_grid(self) -> ProblemRecord:
        """Every accuracy on the curve has a rate at the same N.

        Doc 4 s9.1: `vote_accuracy[N]` is a family of accuracies, so it needs a
        rate per N. One rate for the problem would paper over exactly the
        difference the field exists to expose.
        """
        missing = sorted(set(self.vote_accuracy) - set(self.answer_rate_by_n))
        if missing:
            raise ValueError(
                f"vote_accuracy has no answer_rate at N={missing}: an accuracy "
                "without its rate is not reportable"
            )
        rates = [("answer_rate", self.answer_rate), *self.answer_rate_by_n.items()]
        for name, value in rates:
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"answer_rate out of range at {name}: {value}")
        return self

    @model_validator(mode="after")
    def _margin_carries_its_censoring_and_k(self) -> ProblemRecord:
        """A margin without k is not interpretable and is refused.

        k decides where the censoring point sits, so a stored margin whose k is
        unknown cannot be told apart from one measured at a different depth.
        """
        if self.answer_margin_vs_runner_up is None:
            return self
        if self.answer_margin_censored is None:
            raise ValueError(
                "answer_margin_vs_runner_up without answer_margin_censored: a "
                "bound and a measurement are different quantities"
            )
        if self.answer_margin_k is None or self.answer_margin_k < 1:
            raise ValueError(
                "answer_margin_vs_runner_up without a usable answer_margin_k; "
                "the depth the provider returned decides what the margin means"
            )
        return self

    @model_validator(mode="after")
    def _answer_rate_matches_the_counts(self) -> ProblemRecord:
        """The rate is a function of the stored counts, not an assertion."""
        if self.n_samples_stored <= 0:
            return self
        expected = self.n_answered / self.n_samples_stored
        if abs(expected - self.answer_rate) > 1e-9:
            raise ValueError(
                f"answer_rate {self.answer_rate} does not match "
                f"n_answered/n_samples_stored = {expected}"
            )
        return self


def problem_record_from_dict(record: dict[str, Any]) -> ProblemRecord:
    """Load a stored problem record, branching on `schema_version`.

    Records written before `answer_rate` existed are refused rather than
    upgraded. The rate cannot be recovered from a table that never stored the
    counts it is computed from, so a default here would be a fabricated
    qualification on somebody else's accuracy.
    """
    version = record.get("schema_version")
    if version is None or version < ANSWER_RATE_SCHEMA_VERSION:
        raise ValueError(
            f"problem record at schema_version {version} predates answer_rate "
            f"(added at {ANSWER_RATE_SCHEMA_VERSION}). Its accuracies are "
            "unqualified: the pool that voted is unknown. Rebuild it from raw "
            "rather than reading it as though it carried a rate."
        )
    return ProblemRecord.model_validate(record)


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

    #: Concurrency is deliberately NOT in `param_hash`: it changes nothing about
    #: what a sample contains. It is recorded here anyway because hosted
    #: inference is not batch invariant, so samples drawn at different
    #: concurrencies are two regimes and a reader pooling them is entitled to
    #: know. `run_id` is on every sample, so this mapping makes the regime
    #: boundary visible per sample without touching the raw store.
    #: Empty means the run predates this field, not that concurrency was zero.
    concurrency_by_model: dict[str, int] = Field(default_factory=dict)
    #: Free text for anything about this run a reader needs and no field holds,
    #: such as where a regime boundary falls.
    regime_note: str | None = None

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
