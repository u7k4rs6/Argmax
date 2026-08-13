"""Subsampling behaviour, including the ceiling effect.

The curve is the object under study, so its edge cases are tested rather than
assumed.
"""

from __future__ import annotations

import pytest

from argmax.analysis.curves import single_sample_accuracy, vote_curve
from argmax.keys import subsample_seed
from argmax.schema import DrawScheme, UnansweredPolicy

ANSWERS = ["A", "A", "A", "B", "B", "C", "A", "B"]


def _curve(**kw):
    return vote_curve(
        ANSWERS,
        "A",
        n_grid=kw.pop("n_grid", [1, 3, 5]),
        problem_id="p1",
        model_slug="m1",
        n_draws=kw.pop("n_draws", 200),
        **kw,
    )


def test_curve_is_reproducible():
    assert [p.accuracy for p in _curve()] == [p.accuracy for p in _curve()]


def test_seed_is_independent_of_iteration_order():
    """Seed derives from (problem_id, model_slug, N, replicate), so the same
    point has the same seed regardless of the order points are computed in."""
    assert subsample_seed("p1", "m1", 5, 3) == subsample_seed("p1", "m1", 5, 3)
    assert subsample_seed("p1", "m1", 5, 3) != subsample_seed("p1", "m1", 5, 4)
    assert subsample_seed("p1", "m1", 5, 3) != subsample_seed("p2", "m1", 5, 3)


def test_endpoint_at_N_equals_M_is_degenerate_and_says_so():
    """Subsampling without replacement at N == M yields exactly one possible
    draw, so the endpoint has no subsample variance and no CI.

    The predecessor reported a bare point estimate here. Reporting a bare
    point estimate is acceptable; INVENTING an interval is not.
    """
    points = _curve(n_grid=[len(ANSWERS)])
    end = points[-1]
    assert end.degenerate is True
    assert end.n_draws == 1
    assert end.ci_low == end.ci_high == end.accuracy


def test_grid_point_beyond_M_is_refused():
    with pytest.raises(ValueError, match="exceeds M"):
        _curve(n_grid=[len(ANSWERS) + 1])


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


def test_with_replacement_is_available_but_not_the_default():
    """Recorded as a choice; never left to a library default."""
    default = _curve(n_grid=[3])
    assert default[0].degenerate is False
    with_repl = _curve(n_grid=[3], draw_scheme=DrawScheme.with_replacement)
    assert with_repl[0].n_draws == 200
