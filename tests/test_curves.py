"""Subsampling, paired differences, and what "flat" is allowed to mean.

The curve is the object under study, so its edge cases are tested rather than
assumed. The load-bearing test here is
`test_paired_difference_finds_a_backfire_the_overlap_test_misses`: it pins the
reason the shape rule changed.

Test parameters are small on purpose. `n_bootstrap` and `start_draws` are much
lower than the analysis defaults, and `floor` is looser, because each
bootstrap replicate reruns the whole Monte Carlo layer.
"""

from __future__ import annotations

import pytest

from argmax.analysis.curves import (
    ADJACENT,
    VS_SINGLE,
    classify_curve,
    single_sample_accuracy,
    vote_curve,
)
from argmax.errors import MonteCarloNotConverged
from argmax.keys import subsample_seed
from argmax.schema import CurveShape, DrawScheme, PairedDifference, UnansweredPolicy

# 64 stored samples, the accuracy chosen per case. Majority voting amplifies
# whichever side of 0.5 the model sits on, so these are the two regimes the
# study is about.
STRONG = ["A"] * 51 + ["B"] * 13  # 0.797: voting helps
BACKFIRE = ["A"] * 20 + ["B"] * 44  # 0.312: voting hurts
COINFLIP = ["A", "B"] * 32  # 0.5: voting cannot move it

FAST = {"n_bootstrap": 200, "start_draws": 200, "floor": 0.02}


def _curve(answers, grid=(1, 5, 17), **kw):
    return vote_curve(
        list(answers),
        "A",
        n_grid=list(grid),
        problem_id="p1",
        model_slug="m1",
        **{**FAST, **kw},
    )


def test_curve_is_reproducible():
    a = _curve(STRONG)
    b = _curve(STRONG)
    assert [p.accuracy for p in a.points] == [p.accuracy for p in b.points]
    assert [c.difference for c in a.comparisons] == [
        c.difference for c in b.comparisons
    ]


def test_seed_is_independent_of_iteration_order():
    """Seed derives from (problem_id, model_slug, N, replicate), so the same
    point has the same seed regardless of the order points are computed in."""
    assert subsample_seed("p1", "m1", 5, 3) == subsample_seed("p1", "m1", 5, 3)
    assert subsample_seed("p1", "m1", 5, 3) != subsample_seed("p1", "m1", 5, 4)
    assert subsample_seed("p1", "m1", 5, 3) != subsample_seed("p2", "m1", 5, 3)


def test_grid_point_beyond_M_is_refused():
    with pytest.raises(ValueError, match="exceeds M"):
        _curve(STRONG, grid=(1, 65))


# --- the reason the shape rule changed --------------------------------------


def test_paired_difference_finds_a_backfire_the_overlap_test_misses():
    """The overlapping-CI fallacy, demonstrated on the effect being studied.

    Accuracy at different N comes from the same pool of M samples, so the
    estimates are strongly correlated and the paired difference is far tighter
    than either marginal. Asking whether the marginals overlap therefore calls
    this curve flat, and calling a backfire flat is a false negative on the
    one effect the study exists to measure.
    """
    result = _curve(BACKFIRE)

    marginals_overlap = max(p.ci_low for p in result.points) <= min(
        p.ci_high for p in result.points
    )
    assert marginals_overlap, (
        "this fixture is supposed to be one the overlap test cannot resolve"
    )

    drop = next(
        c for c in result.comparisons if c.comparison == VS_SINGLE and c.N == 17
    )
    assert drop.difference < 0
    assert drop.interval.high < 0, "the paired interval must exclude zero"
    assert not drop.flat

    assert result.shape == CurveShape.monotone_down
    assert result.backfire_significant()[17] is True


def test_a_real_gain_is_called_a_gain():
    result = _curve(STRONG)
    assert result.shape == CurveShape.monotone_up
    gain = next(
        c for c in result.comparisons if c.comparison == VS_SINGLE and c.N == 17
    )
    assert gain.interval.low > 0
    assert result.backfire_significant()[17] is False


def test_a_curve_that_cannot_move_is_flat():
    """At p = 0.5 voting has nothing to amplify, and flat is the right answer."""
    result = _curve(COINFLIP)
    assert result.shape == CurveShape.flat_within_ci
    assert all(c.flat for c in result.comparisons)


def test_flat_requires_every_difference_to_contain_zero():
    """One significant move is enough to stop a curve being flat, which is the
    opposite of the old rule, where one wide marginal made everything flat."""
    result = _curve(STRONG)
    assert any(not c.flat for c in result.comparisons)
    assert result.shape != CurveShape.flat_within_ci


def test_an_unclassifiable_shape_is_null_not_forced():
    """Doc 4 names four shapes. A fall then a rise is none of them, and
    curve_shape is nullable so it can say so."""

    class _Fake:
        def __init__(self, N, other, diff):
            self.comparison = ADJACENT
            self.N = N
            self.N_other = other
            self.difference = diff
            self.flat = False

    assert classify_curve([_Fake(3, 1, -0.2), _Fake(9, 3, +0.2)]) is None


# --- persistence ------------------------------------------------------------


def test_per_replicate_differences_are_persisted_not_just_the_interval():
    """Defect 2 was keeping the aggregate and discarding the rows."""
    result = _curve(STRONG)
    rows = result.rows()

    assert all(isinstance(r, PairedDifference) for r in rows)
    assert len(rows) == len(result.comparisons) * result.n_bootstrap

    kinds = {r.comparison for r in rows}
    assert kinds == {VS_SINGLE, ADJACENT}

    vs_single_17 = [r for r in rows if r.comparison == VS_SINGLE and r.N == 17]
    assert len(vs_single_17) == result.n_bootstrap
    assert all(r.N_other is None for r in vs_single_17)
    assert {r.replicate for r in vs_single_17} == set(range(result.n_bootstrap))

    adjacent = [r for r in rows if r.comparison == ADJACENT and r.N == 17]
    assert all(r.N_other == 5 for r in adjacent)


def test_the_interval_is_recoverable_from_the_stored_rows():
    """The rows are the artifact; the interval must be a function of them."""
    from argmax.analysis.bootstrap import confidence_interval

    result = _curve(STRONG)
    comparison = next(
        c for c in result.comparisons if c.comparison == VS_SINGLE and c.N == 5
    )
    rows = [
        r.difference for r in result.rows() if r.comparison == VS_SINGLE and r.N == 5
    ]
    recomputed = confidence_interval(rows, comparison.interval.level)
    assert (recomputed.low, recomputed.high) == (
        comparison.interval.low,
        comparison.interval.high,
    )


# --- the two layers ---------------------------------------------------------


def test_monte_carlo_noise_is_driven_below_the_effect_it_must_resolve():
    result = _curve(STRONG)
    for point in result.points:
        assert point.mc_halfwidth <= FAST["floor"] or point.degenerate


def test_draws_are_raised_until_converged():
    """B is a knob, not a measurement, so it is turned rather than reported."""
    result = _curve(STRONG, start_draws=50, floor=0.02)
    assert result.n_draws > 50


def test_a_cap_that_cannot_resolve_the_effect_raises():
    """Better a refusal than a noisy number that looks like a result."""
    with pytest.raises(MonteCarloNotConverged):
        _curve(STRONG, start_draws=8, max_draws=8, floor=0.0001)


def test_endpoint_at_N_equals_M_has_no_monte_carlo_noise_but_still_has_a_CI():
    """Subsampling without replacement at N == M admits one subsample, so the
    Monte Carlo layer is exactly zero there.

    The pool bootstrap is not: a different M samples would have produced a
    different endpoint. The old code conflated the two and reported the
    endpoint as having no interval at all.

    The coin-flip pool is used because it is where the endpoint genuinely
    varies. On a lopsided pool every resampled world votes the same way and
    the bootstrap interval collapses to a point, which is a real answer rather
    than a missing one.
    """
    result = _curve(COINFLIP, grid=(1, 64))
    end = result.points[-1]
    assert end.degenerate is True
    assert end.mc_halfwidth == 0.0
    assert end.ci_low < end.ci_high


def test_with_replacement_is_available_but_not_the_default():
    """Recorded as a choice; never left to a library default."""
    assert _curve(STRONG, grid=(5,)).points[0].degenerate is False
    other = _curve(STRONG, grid=(5,), draw_scheme=DrawScheme.with_replacement)
    assert other.draw_scheme == DrawScheme.with_replacement


# --- policy -----------------------------------------------------------------


def test_unanswered_policy_changes_the_answer_and_is_explicit():
    """The two policies must actually differ, so that choosing one is a real
    decision rather than a formality."""
    answers = ["A", None, None, "B"]
    excl = single_sample_accuracy(
        answers, "A", unanswered_policy=UnansweredPolicy.exclude
    )
    wrong = single_sample_accuracy(
        answers, "A", unanswered_policy=UnansweredPolicy.score_as_wrong
    )
    assert excl == pytest.approx(0.5)
    assert wrong == pytest.approx(0.25)


def test_unanswered_samples_occupy_a_slot_but_cast_no_vote():
    """Under score_as_wrong a missing answer is not a vote for anything; it
    takes up one of the N samples and loses it."""
    answers = ["A"] * 20 + [None] * 44
    result = vote_curve(
        answers,
        "A",
        n_grid=[5],
        problem_id="p1",
        model_slug="m1",
        unanswered_policy=UnansweredPolicy.score_as_wrong,
        **FAST,
    )
    assert result.single_sample_accuracy == pytest.approx(20 / 64)
    # A majority of five where most slots are empty still resolves to A
    # whenever any A is drawn, so voting helps here rather than hurting.
    assert result.points[0].accuracy > result.single_sample_accuracy
