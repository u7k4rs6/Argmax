"""The interval a curve point reports must be an interval.

These are regression tests for a defect that reached working code: both
`vote_curve` and `compare_at_budget` reported the 2.5th and 97.5th percentiles
of their per-draw 0/1 outcomes as a CI, which is [0.0, 1.0] for every accuracy
that is not already extreme. The number had a name and a column and meant
nothing, which is the class of failure this repo exists to prevent.
"""

from __future__ import annotations

import pytest

from argmax.analysis.curves import classify_curve, vote_curve
from argmax.analysis.intervals import mean_interval, wilson_interval
from argmax.analysis.matched_compute import StoredSample, compare_at_budget
from argmax.schema import CurveShape


def test_interval_brackets_the_mean_and_is_not_the_whole_range():
    lo, hi = wilson_interval(600, 1000)
    assert lo < 0.6 < hi
    assert hi - lo < 0.1, "an interval on 1000 draws that wide is not an interval"


def test_interval_narrows_as_draws_increase():
    """B is a Monte Carlo knob: more replicates buy a tighter interval."""
    narrow = wilson_interval(600, 1000)
    wide = wilson_interval(6, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_all_hits_does_not_claim_certainty():
    """Wilson rather than the normal approximation, which collapses to a point
    at p = 1 and asserts certainty that ten draws cannot support."""
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0
    assert lo < 1.0


def test_no_draws_is_no_information():
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_single_draw_is_degenerate_rather_than_fabricated():
    mean, lo, hi = mean_interval([1.0])
    assert (mean, lo, hi) == (1.0, 1.0, 1.0)


def test_successes_outside_the_draw_count_is_a_bug_not_a_clamp():
    with pytest.raises(ValueError):
        wilson_interval(11, 10)


# --- the two call sites -----------------------------------------------------

# 6 correct, 4 wrong: single-sample accuracy 0.6, and voting climbs from there.
ANSWERS = ["A"] * 6 + ["B"] * 4


def test_vote_curve_reports_a_real_interval():
    points = vote_curve(
        ANSWERS,
        "A",
        n_grid=[1, 3, 5],
        problem_id="p1",
        model_slug="m1",
        n_draws=500,
    )
    for p in points:
        assert p.ci_low <= p.accuracy <= p.ci_high
        assert (p.ci_low, p.ci_high) != (0.0, 1.0), (
            f"N={p.N} reported the full range as its CI"
        )


def test_a_rising_curve_is_not_classified_flat():
    """The old spread test read [0, 1] intervals and called this flat.

    Accuracy climbs from about 0.59 at N=1 to 1.00 at N=9. A classifier that
    calls that flat is worse than no classifier, because it is quotable.
    """
    points = vote_curve(
        ANSWERS,
        "A",
        n_grid=[1, 3, 5, 9],
        problem_id="p1",
        model_slug="m1",
        n_draws=500,
    )
    assert points[0].accuracy < points[-1].accuracy
    assert classify_curve(points) == CurveShape.monotone_up


def test_a_genuinely_flat_curve_is_still_called_flat():
    """A coin-flip problem: voting cannot move it, and the intervals overlap."""
    points = vote_curve(
        ["A", "B"] * 8,
        "A",
        n_grid=[1, 3, 5],
        problem_id="p2",
        model_slug="m1",
        n_draws=500,
    )
    assert classify_curve(points) == CurveShape.flat_within_ci


def test_matched_compute_reports_a_real_interval():
    samples = [
        StoredSample(extracted_answer=a, completion_tokens=100, max_tokens=512)
        for a in ANSWERS
    ]
    row = compare_at_budget(
        samples,
        "A",
        budget_tokens=300,
        strategy_id="short_many",
        problem_id="p1",
        model_slug="m1",
        n_draws=500,
    )
    assert row.ci_low <= row.accuracy_under_strategy <= row.ci_high
    assert (row.ci_low, row.ci_high) != (0.0, 1.0)
