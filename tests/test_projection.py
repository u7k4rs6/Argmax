"""Calibration of cost projections made from k problems.

Two projections underestimated before this module existed. The failure is not
arithmetic, it is that a k-problem probe inherits between-problem variance and
reads it as if it were sampling noise.
"""

from __future__ import annotations

import pytest

from argmax.analysis.projection import (
    heterogeneity_ratio,
    projection_error,
)


def test_a_homogeneous_set_needs_no_uplift():
    """Identical problems: every probe is exact, so the uplift is zero."""
    e = projection_error([600.0] * 198, 8, trials=2000, seed=1)
    assert e.median == pytest.approx(0.0)
    assert e.p5 == pytest.approx(0.0)
    assert e.uplift_for_95pct_coverage == pytest.approx(0.0)


def test_uplift_falls_as_k_rises():
    """More problems, less between-problem variance in the estimate.

    This is the property that makes the probe design decision, and it is the
    one a projection from 8 problems ignores.
    """
    means = [100.0 + 40.0 * ((i * 37) % 23) for i in range(198)]
    uplifts = [
        projection_error(means, k, trials=4000, seed=3).uplift_for_95pct_coverage
        for k in (4, 8, 16, 32)
    ]
    assert uplifts == sorted(uplifts, reverse=True)
    assert all(u > 0 for u in uplifts)


def test_uplift_covers_the_fifth_percentile_exactly():
    """The uplift is defined so a p5 projection lands on the truth."""
    means = [100.0 + 40.0 * ((i * 37) % 23) for i in range(198)]
    e = projection_error(means, 8, trials=8000, seed=5)
    assert (1 + e.p5) * (1 + e.uplift_for_95pct_coverage) == pytest.approx(1.0)


def test_drawing_the_whole_set_is_exact():
    means = [float(i) for i in range(1, 51)]
    e = projection_error(means, 50, trials=200, seed=7)
    assert e.median == pytest.approx(0.0)
    assert e.fraction_underestimating == 0.0


def test_heterogeneity_ratio_is_one_under_the_null():
    """Per-problem means spread exactly as sampling noise predicts."""
    import random
    import statistics

    rng = random.Random(11)
    m = 64
    groups = [[rng.gauss(600, 200) for _ in range(m)] for _ in range(4000)]
    means = [statistics.mean(g) for g in groups]
    variances = [statistics.variance(g) for g in groups]
    assert heterogeneity_ratio(means, variances, m) == pytest.approx(1.0, abs=0.1)


def test_k_outside_the_set_is_refused():
    with pytest.raises(ValueError):
        projection_error([1.0, 2.0], 3)
    with pytest.raises(ValueError):
        projection_error([1.0, 2.0], 0)
