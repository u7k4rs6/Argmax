"""Intervals for a mean over Bernoulli draws.

There was a real defect here, and it is worth stating plainly because it is
the exact failure mode this repo exists to catch: a number that reaches the
paper and means nothing.

Both `curves.vote_curve` and `matched_compute.compare_at_budget` produce a
list of per-draw outcomes, each 0.0 or 1.0, and reported a "CI" by taking the
2.5th and 97.5th percentiles OF THAT LIST. Percentiles of a 0/1 list are 0 and
1 for every accuracy between 0.025 and 0.975, so every interval came out as
[0.0, 1.0]. It was not a wide interval; it was not an interval at all. It also
poisoned `classify_curve`, which measured "flat within CI" against that spread
and therefore called every curve flat.

The quantity wanted is an interval on the MEAN of the draws, not the spread of
the draws. Wilson gives it in closed form, needs no extra RNG, and behaves at
the edges where the normal approximation does not.

## What this interval is, and what it is not

**It is** the uncertainty introduced by taking a finite number `B` of
subsample draws from a FIXED pool of stored samples. It shrinks as `B` grows,
and `B` is free: it is a Monte Carlo knob, not a measurement.

**It is not** the uncertainty in accuracy arising from having drawn only `M`
samples from the model. That interval is strictly wider and would require
resampling the pool itself.

The distinction is load-bearing for two reasons. Doc 2 section 7 says
reproducibility claims are a reviewer target and must be stated precisely; the
same applies here. And the endpoint behaviour depends on it: at `N == M` there
is exactly one possible subsample, so this interval collapses to a point,
which is the honest report of subsample variance and would be wrong for
finite-`M` variance. Anything published as a confidence interval on accuracy
needs the wider one, computed by resampling the stored pool.
"""

from __future__ import annotations

from statistics import NormalDist


def z_for(ci: float) -> float:
    """Two-sided normal quantile. `ci=0.95` -> 1.959964."""
    if not 0.0 < ci < 1.0:
        raise ValueError(f"ci must be in (0, 1), got {ci}")
    return NormalDist().inv_cdf(1.0 - (1.0 - ci) / 2.0)


def wilson_interval(successes: float, n: int, ci: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Chosen over the normal approximation because the draws here are routinely
    all-hit or all-miss on easy and impossible problems, where the normal
    interval degenerates to a point at 0 or 1 and asserts certainty that is not
    there.

    `n == 0` returns the full range: no draws is no information, and the honest
    report of no information is [0, 1].
    """
    if n <= 0:
        return (0.0, 1.0)
    if successes < 0 or successes > n:
        raise ValueError(f"successes={successes} outside [0, {n}]")

    z = z_for(ci)
    p = successes / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return (max(0.0, center - half), min(1.0, center + half))


def mean_interval(hits: list[float], ci: float = 0.95) -> tuple[float, float, float]:
    """`(mean, ci_low, ci_high)` for a list of 0/1 draw outcomes.

    A single draw yields a degenerate interval rather than a fabricated one:
    one observation carries no information about spread, and inventing an
    interval there is the over-claim the predecessor was pushed on.
    """
    if not hits:
        return (0.0, 0.0, 1.0)
    mean = sum(hits) / len(hits)
    if len(hits) == 1:
        return (mean, mean, mean)
    lo, hi = wilson_interval(sum(hits), len(hits), ci)
    return (mean, lo, hi)
