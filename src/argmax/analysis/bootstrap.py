"""The pool bootstrap. This is the only confidence interval in the codebase.

Everything reported as a CI comes from here. The Monte Carlo layer in
`argmax.analysis.convergence` produces no interval and never will: keeping two
things named CI is how the narrow one ends up in a paper claiming to be the
wide one.

## What is resampled

The stored samples themselves. `M` completions were drawn from the model for a
problem; a different `M` would have given different answers, and that is the
uncertainty a reader cares about. Each bootstrap replicate resamples those `M`
answers with replacement and recomputes the whole statistic on the resampled
pool.

Resampling with replacement here is not the same act as the `with_replacement`
draw scheme the architecture warns about. That warning is about pretending a
with-replacement subsample of size `N` is what `N` model draws would have
looked like, which inflates agreement through duplicates. This is the standard
nonparametric bootstrap of the empirical distribution, used to estimate the
sampling distribution of a statistic, and the subsampling inside each replicate
remains without replacement.

## Why the interval must be on the difference

Accuracy at different `N` is computed from the same `M` stored samples, so the
estimates are strongly correlated. Comparing two marginal intervals and calling
the curve flat when they overlap is the overlapping-CI fallacy: the paired
difference is much tighter than either marginal, and the overlap test is biased
toward flat. On this study that bias points directly at the effect being
measured, since a false "flat" is a missed backfire.

So the difference is recomputed inside each bootstrap replicate and the
interval is taken over the distribution of differences. Flat means that
interval contains zero.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_N_BOOTSTRAP = 1000
DEFAULT_LEVEL = 0.95


@dataclass(frozen=True)
class Interval:
    """A reported confidence interval, and the replicates it came from.

    `n_replicates` travels with the interval because a percentile interval
    from too few replicates is a lattice, not a continuum, and the reader
    needs to know which.
    """

    low: float
    high: float
    level: float
    n_replicates: int

    def contains_zero(self) -> bool:
        return self.low <= 0.0 <= self.high


def confidence_interval(
    values: Sequence[float], level: float = DEFAULT_LEVEL
) -> Interval:
    """Percentile interval over bootstrap replicates.

    Percentile rather than normal-approximation because the statistics here
    (vote accuracy, differences of vote accuracies) are bounded, discrete and
    routinely skewed against a bound.
    """
    if not values:
        raise ValueError("no bootstrap replicates: an interval over nothing")
    ordered = sorted(values)
    n = len(ordered)
    if n == 1:
        return Interval(ordered[0], ordered[0], level, 1)
    tail = (1.0 - level) / 2.0
    lo_i = max(0, int(tail * n))
    hi_i = min(n - 1, int((1.0 - tail) * n))
    return Interval(ordered[lo_i], ordered[hi_i], level, n)
