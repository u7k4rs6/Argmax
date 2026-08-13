"""Matched compute is a function, not a description.

Defect 3 in the published study was prose describing a compute-matched
baseline that was never implemented; every real comparison was flat N=64. The
rows produced here are what a claim of that kind has to resolve to.

The interval is the pool bootstrap, the same one the curves report, for the
same reason: percentiles of the per-draw 0/1 outcomes are 0 and 1, and a
matched-compute table of [0, 1] intervals compares nothing.
"""

from __future__ import annotations

import pytest

from argmax.analysis.matched_compute import StoredSample, compare_at_budget
from argmax.errors import MonteCarloNotConverged

ANSWERS = ["A"] * 24 + ["B"] * 8  # 0.75


def _samples(tokens: int = 100, answers: list[str] | None = None):
    return [
        StoredSample(extracted_answer=a, completion_tokens=tokens, max_tokens=512)
        for a in (answers or ANSWERS)
    ]


FAST = {"n_draws": 200, "n_bootstrap": 100, "bootstrap_draws": 50}


def _row(**kw):
    return compare_at_budget(
        _samples(kw.pop("tokens", 100), kw.pop("answers", None)),
        "A",
        budget_tokens=kw.pop("budget_tokens", 500),
        strategy_id="short_many",
        problem_id="p1",
        model_slug="m1",
        **{**FAST, **kw},
    )


def test_the_interval_is_not_the_whole_range():
    row = _row()
    assert row.ci_low <= row.accuracy_under_strategy <= row.ci_high
    assert (row.ci_low, row.ci_high) != (0.0, 1.0)


def test_more_budget_buys_more_samples():
    """The point of the comparison: what a token budget can actually buy."""
    small = _row(budget_tokens=300)
    large = _row(budget_tokens=900)
    assert small.n_samples_used < large.n_samples_used
    assert small.tokens_actually_consumed < large.tokens_actually_consumed


def test_consumption_comes_from_the_stored_tokens_not_the_plan():
    """A strategy that planned four samples and consumed three is reported as
    three."""
    row = _row(budget_tokens=350, tokens=100)
    assert row.n_samples_used == 3
    assert row.tokens_actually_consumed == 300


def test_a_budget_too_small_for_one_sample_is_recorded_not_dropped():
    """Absence is data: the row exists and says nothing was affordable."""
    row = _row(budget_tokens=50, tokens=100)
    assert row.n_samples_used == 0
    assert row.accuracy_under_strategy is None
    assert row.ci_low is None and row.ci_high is None


def test_claim_ids_travel_with_the_row():
    """No sentence describing a compute-matched comparison may exist without a
    claim_id resolving to rows here."""
    row = _row(claim_ids=["C1"])
    assert row.claim_ids == ["C1"]


def test_a_cap_that_cannot_resolve_the_estimate_is_refused():
    with pytest.raises(MonteCarloNotConverged):
        _row(n_draws=8, max_draws=8)


def test_no_stored_samples_is_an_error_not_an_empty_row():
    with pytest.raises(ValueError, match="no stored samples"):
        compare_at_budget(
            [],
            "A",
            budget_tokens=500,
            strategy_id="short_many",
            problem_id="p1",
            model_slug="m1",
        )
