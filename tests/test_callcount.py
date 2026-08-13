"""The call-count estimator and its baselines.

The load-bearing test is `test_measured_curve_agrees_with_the_curves_module`:
two independent implementations of majority vote over a stored pool must
produce the same numbers, or one of them is wrong and the whole of Thread A
rests on which.
"""

from __future__ import annotations

import numpy as np
import pytest

from argmax.analysis.callcount import (
    GRID,
    aggregate_regret,
    constant_baseline,
    estimate_chen,
    estimate_naive_within_k,
    grid_distance,
    per_problem_regret_terms,
    predicted_curve_from_counts,
    vote_accuracy_point,
)
from argmax.analysis.curves import vote_curve


def test_measured_curve_agrees_with_the_curves_module():
    """Same estimand, two implementations, agreeing to Monte Carlo noise."""
    answers = ["A"] * 40 + ["B"] * 24
    codes = np.array([0] * 40 + [1] * 24, dtype=np.int16)

    mine = vote_accuracy_point(codes, 0, 2, (1, 4, 16), 4000, np.random.default_rng(1))
    theirs = vote_curve(
        answers,
        "A",
        n_grid=[1, 4, 16],
        problem_id="p",
        model_slug="m",
        n_bootstrap=50,
        start_draws=4000,
        floor=0.05,
    )
    for point in theirs.points:
        assert mine[point.N] == pytest.approx(point.accuracy, abs=0.03)


def test_a_certain_problem_predicts_improvement_with_N():
    """A problem the model gets right 80 percent of the time should be
    predicted to improve with more votes."""
    counts = np.array([8.0, 2.0, 0.0, 0.0])
    curve = predicted_curve_from_counts(
        counts, 0, GRID, alpha=0.5, n_draws=2000, rng=np.random.default_rng(0)
    )
    assert curve[64] > curve[1]


def test_a_wrong_problem_predicts_decline_with_N():
    """The backfire case: most mass on a wrong option, so voting entrenches it."""
    counts = np.array([2.0, 8.0, 0.0, 0.0])
    curve = predicted_curve_from_counts(
        counts, 0, GRID, alpha=0.5, n_draws=2000, rng=np.random.default_rng(0)
    )
    assert curve[64] < curve[1]


def test_smoothing_changes_a_unanimous_problem():
    """Without smoothing, k unanimous samples predict certainty at every N,
    which at k=4 is most problems."""
    counts = np.array([4.0, 0.0, 0.0, 0.0])
    hard = predicted_curve_from_counts(
        counts, 0, (1, 64), alpha=0.0, n_draws=500, rng=np.random.default_rng(0)
    )
    soft = predicted_curve_from_counts(
        counts, 0, (1, 64), alpha=1.0, n_draws=500, rng=np.random.default_rng(0)
    )
    assert hard[1] == 1.0
    assert soft[1] < 1.0


def test_the_estimator_returns_a_grid_point():
    observed = {
        "p1": np.array([6.0, 2.0, 0.0, 0.0]),
        "p2": np.array([1.0, 7.0, 0.0, 0.0]),
    }
    correct = {"p1": 0, "p2": 0}
    pred = estimate_chen(observed, correct, 4, alpha=0.5, n_draws=500, seed=3)
    assert pred.n_hat_aggregate in GRID
    assert set(pred.n_hat_per_problem) == {"p1", "p2"}


def test_naive_cannot_name_an_N_it_could_not_measure():
    """With k=4 and the stay rule, nothing above 4 is reachable."""
    sampled = {"p1": np.array([0, 0, 0, 1], dtype=np.int16)}
    pred = estimate_naive_within_k(
        sampled, {"p1": 0}, 4, k=4, boundary_rule="stay", n_draws=200, seed=1
    )
    assert pred.n_hat_aggregate <= 4


def test_ties_resolve_to_the_cheaper_call_count():
    """A problem the model always gets right measures 1.0 at every N. The
    smallest N is the right answer there, and a tie-break preferring the larger
    would flatter any method that guesses high."""
    sampled = {p: np.array([0, 0, 0, 0], dtype=np.int16) for p in ("p1", "p2")}
    pred = estimate_naive_within_k(
        sampled,
        dict.fromkeys(sampled, 0),
        4,
        k=4,
        boundary_rule="extrapolate_to_max",
        n_draws=200,
        seed=1,
    )
    assert pred.n_hat_aggregate == 1


def test_the_boundary_rule_is_the_only_route_above_k():
    # Three right and one wrong: voting over all four beats a single sample,
    # so the argmax lands on the boundary and the rule decides what happens.
    sampled = {p: np.array([0, 0, 0, 1], dtype=np.int16) for p in ("p1", "p2")}
    correct = dict.fromkeys(sampled, 0)
    stay = estimate_naive_within_k(
        sampled, correct, 4, k=4, boundary_rule="stay", n_draws=200, seed=1
    )
    jump = estimate_naive_within_k(
        sampled,
        correct,
        4,
        k=4,
        boundary_rule="extrapolate_to_max",
        n_draws=200,
        seed=1,
    )
    assert stay.n_hat_aggregate == 4
    assert jump.n_hat_aggregate == 64


def test_an_unknown_boundary_rule_is_refused():
    with pytest.raises(ValueError, match="boundary_rule"):
        estimate_naive_within_k(
            {"p": np.array([0], dtype=np.int16)},
            {"p": 0},
            4,
            k=1,
            boundary_rule="guess",
            n_draws=10,
            seed=1,
        )


# --- scoring ---------------------------------------------------------------


def test_regret_is_zero_at_the_measured_optimum():
    truth = {1: 0.30, 2: 0.32, 4: 0.35, 8: 0.34, 16: 0.33, 32: 0.32, 64: 0.31}
    assert aggregate_regret(truth, 4) == pytest.approx(0.0)
    assert aggregate_regret(truth, 64) == pytest.approx(0.04)


def test_grid_distance_counts_steps_not_calls():
    assert grid_distance(64, 64) == 0
    assert grid_distance(32, 64) == 1
    assert grid_distance(1, 64) == 6


def test_paired_terms_have_one_entry_per_problem_and_keep_their_sign():
    truth = {
        "p1": {1: 0.5, 64: 0.2},
        "p2": {1: 0.1, 64: 0.6},
    }
    a = {"p1": 1, "p2": 1}
    b = {"p1": 64, "p2": 64}
    terms = per_problem_regret_terms(truth, a, b, grid=(1, 64))
    assert len(terms) == 2
    assert terms[0] < 0  # a is better on p1
    assert terms[1] > 0  # a is worse on p2


def test_constant_baselines_are_constant():
    pred = constant_baseline("always_max", 64, ["p1", "p2"])
    assert pred.n_hat_aggregate == 64
    assert set(pred.n_hat_per_problem.values()) == {64}
