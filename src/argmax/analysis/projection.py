"""Calibration of cost projections made from a probe of k problems.

A projection is made by drawing k problems, measuring mean completion length
on them, and multiplying up to the full problem set. Two such projections have
now underestimated: the margin-v1 phase by 5.4 percent on a broad basis, and
the margin-v2 cap probe by 13.8 percent from 8 problems.

The reason is that **completion length is a per-problem property**. Its
between-problem variance sits far above a homogeneous null, so a k-problem
probe inherits that variance, not the sampling noise of its k * m draws.
Taking more samples per problem shrinks the second and leaves the first
untouched. This module measures the first directly by resampling the 198
per-problem means the v1 store already contains.

No network, no writes. Pure functions over a list of per-problem means.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectionError:
    """The distribution of projection error at one probe size."""

    k: int
    trials: int
    median: float
    p5: float
    p95: float
    fraction_underestimating: float
    #: Multiply a k-problem projection by this so it covers the truth 95
    #: percent of the time. Derived from the 5th percentile, because a
    #: projection that is too low is the one that stops a run mid-flight.
    uplift_for_95pct_coverage: float


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("no values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return sorted_values[int(pos)]
    return sorted_values[lo] + (pos - lo) * (sorted_values[hi] - sorted_values[lo])


def projection_error(
    per_problem_means: list[float],
    k: int,
    *,
    trials: int = 20000,
    seed: int = 0,
    with_replacement: bool = False,
) -> ProjectionError:
    """Resample k problems, project, and compare against the full-set mean.

    `with_replacement` False matches how a probe actually runs: k distinct
    problems drawn from the set. The full-set mean is the truth being
    estimated, so error is `projection / truth - 1`.
    """
    if k < 1 or k > len(per_problem_means):
        raise ValueError(f"k={k} outside 1..{len(per_problem_means)}")
    truth = sum(per_problem_means) / len(per_problem_means)
    if truth <= 0:
        raise ValueError("full-set mean must be positive")

    rng = random.Random(seed)
    errors: list[float] = []
    for _ in range(trials):
        if with_replacement:
            drawn = [rng.choice(per_problem_means) for _ in range(k)]
        else:
            drawn = rng.sample(per_problem_means, k)
        errors.append((sum(drawn) / k) / truth - 1.0)
    errors.sort()

    p5 = _quantile(errors, 0.05)
    # A projection at the 5th percentile is low by (1 + p5). Multiplying by
    # 1 / (1 + p5) lifts that case exactly onto the truth, so 95 percent of
    # projections then land at or above it.
    uplift = 1.0 / (1.0 + p5) - 1.0
    return ProjectionError(
        k=k,
        trials=trials,
        median=_quantile(errors, 0.5),
        p5=p5,
        p95=_quantile(errors, 0.95),
        fraction_underestimating=sum(1 for e in errors if e < 0) / len(errors),
        uplift_for_95pct_coverage=uplift,
    )


def heterogeneity_ratio(
    per_problem_means: list[float], per_problem_variances: list[float], m: int
) -> float:
    """Observed between-problem variance over the homogeneous null's.

    Under a homogeneous null every problem shares one length distribution, so
    the variance of per-problem means at m samples each is within-problem
    variance over m. The ratio is how much more spread there is than sampling
    noise alone accounts for. A ratio near 1 would mean a probe's error really
    is sampling noise and more samples per problem would fix it.
    """
    n = len(per_problem_means)
    if n < 2 or not per_problem_variances:
        raise ValueError("need at least two problems and their variances")
    grand = sum(per_problem_means) / n
    observed = sum((x - grand) ** 2 for x in per_problem_means) / (n - 1)
    within = sum(per_problem_variances) / len(per_problem_variances)
    expected = within / m
    if expected <= 0:
        raise ValueError("within-problem variance is zero")
    return observed / expected
