"""`answer_rate` is required, versioned, and never invented.

Doc 4 s4.1: a truncated sample casts no vote, so the pool that votes at a
token cap is smaller than N and is enriched for samples that answer fast. If
that enrichment correlates with correctness, accuracy moves while the policy
does not. The rate is what lets a reader see the difference instead of
inferring it, so it travels with every accuracy the record carries.
"""

from __future__ import annotations

import pytest

from argmax.schema import (
    ANSWER_RATE_SCHEMA_VERSION,
    SCHEMA_VERSION,
    ProblemRecord,
    problem_record_from_dict,
)

BASE = {
    "problem_id": "p1",
    "benchmark": "bench",
    "tier": "diamond",
    "domain": "physics",
    "subdomain": None,
    "n_options": 4,
    "correct_option": "A",
    "model_slug": "m1",
    "n_samples_stored": 10,
    "n_answered": 8,
    "n_truncated": 2,
    "n_no_answer": 0,
    "n_api_failure": 0,
    "answer_rate": 0.8,
    "answer_rate_by_n": {1: 1.0, 5: 1.0},
    "single_sample_accuracy": 0.5,
    "unanswered_sample_policy": "exclude",
    "vote_accuracy": {1: 0.5, 5: 0.6},
    "ci_low": {1: 0.4, 5: 0.5},
    "ci_high": {1: 0.6, 5: 0.7},
    "interval_method": "pool_bootstrap",
    "n_bootstrap": 1000,
    "mc_halfwidth": {1: 0.01, 5: 0.01},
    "n_draws": 200,
    "draw_scheme": "without_replacement",
    "seed_recipe": "recipe",
    "backfire": {1: False, 5: False},
    "peak_N": 5,
    "peak_accuracy": 0.6,
    "curve_shape": None,
}


def test_the_baseline_record_is_valid():
    record = ProblemRecord(**BASE)
    assert record.schema_version == SCHEMA_VERSION
    assert record.answer_rate == 0.8


def test_answer_rate_is_required():
    record = dict(BASE)
    record.pop("answer_rate")
    with pytest.raises(ValueError, match="answer_rate"):
        ProblemRecord(**record)


def test_the_grid_needs_a_rate_at_every_N():
    """vote_accuracy[N] is a family of accuracies, so it needs a rate per N.

    One rate for the problem would paper over the difference the field exists
    to expose.
    """
    record = dict(BASE, answer_rate_by_n={1: 1.0})
    with pytest.raises(ValueError, match="N=\\[5\\]"):
        ProblemRecord(**record)


def test_a_rate_of_one_is_published_not_omitted():
    """No omission when the rate is uninteresting: uninteresting is a
    judgement made after seeing a number the reader has not seen."""
    record = ProblemRecord(
        **dict(
            BASE,
            n_answered=10,
            n_truncated=0,
            answer_rate=1.0,
            answer_rate_by_n={1: 1.0, 5: 1.0},
        )
    )
    assert record.answer_rate == 1.0
    assert set(record.answer_rate_by_n) == set(record.vote_accuracy)


def test_the_rate_must_match_the_stored_counts():
    """It is a function of the counts, not an assertion beside them."""
    with pytest.raises(ValueError, match="does not match"):
        ProblemRecord(**dict(BASE, answer_rate=0.9))


def test_a_rate_outside_zero_to_one_is_refused():
    with pytest.raises(ValueError, match="out of range"):
        ProblemRecord(**dict(BASE, answer_rate_by_n={1: 1.4, 5: 1.0}))


# --- versioning -------------------------------------------------------------


def test_the_field_carries_the_version_that_introduced_it():
    with pytest.raises(ValueError, match="predates answer_rate"):
        ProblemRecord(**dict(BASE, schema_version=ANSWER_RATE_SCHEMA_VERSION - 1))


def test_older_records_are_refused_rather_than_backfilled():
    """The rate cannot be recovered from a table that never stored the counts.

    A default here would be a fabricated qualification on somebody else's
    accuracy, which is worse than no qualification at all.
    """
    legacy = {k: v for k, v in BASE.items() if not k.startswith("answer_rate")}
    legacy["schema_version"] = 2
    with pytest.raises(ValueError, match="unqualified"):
        problem_record_from_dict(legacy)


def test_current_records_load_through_the_branching_reader():
    record = problem_record_from_dict(dict(BASE, schema_version=SCHEMA_VERSION))
    assert record.answer_rate == 0.8


def test_a_record_with_no_version_at_all_is_refused():
    legacy = {k: v for k, v in BASE.items() if not k.startswith("answer_rate")}
    with pytest.raises(ValueError, match="predates answer_rate"):
        problem_record_from_dict(legacy)
