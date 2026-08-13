"""Monte Carlo convergence. This module reports no confidence interval.

There are two sources of variation in a vote curve and conflating them is how
a curve gets called flat:

  1. **Monte Carlo noise.** Only `B` subsample draws were taken instead of all
     `C(M, N)` of them. This shrinks as `B` grows and `B` is free. It is not
     uncertainty about the world, it is a statement about how long the
     computation ran.

  2. **Sampling uncertainty.** Only `M` samples were drawn from the model.
     This does not shrink with more computation. It is the uncertainty worth
     reporting, and `argmax.analysis.bootstrap` is where it is estimated.

An earlier version of this code reported (1) as a confidence interval, which
is both too narrow to be the honest interval and, when computed as percentiles
of 0/1 draw outcomes, degenerate at `[0, 1]`. Now (1) is a **convergence
check** with no interval in its vocabulary: it asks whether `B` is large
enough that Monte Carlo noise cannot move the conclusion, and raises `B` until
it is.

The check compares the Wilson half-width on `B` draws against the effect being
resolved. An absolute floor is required as well as a relative one, because a
genuinely null effect would otherwise demand infinite precision and the loop
would never terminate.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

from argmax.errors import MonteCarloNotConverged

#: Monte Carlo noise must be at most this fraction of the effect being
#: resolved. A tenth means the noise cannot plausibly flip a comparison whose
#: true difference is the observed one.
DEFAULT_TOLERANCE = 0.1

#: The floor, in accuracy units. Against a null effect the relative rule asks
#: for infinite precision, so precision below this absolute level is accepted
#: as converged and the effect is reported as indistinguishable from zero.
DEFAULT_FLOOR = 0.01

#: Doubling stops here. Hitting the cap is an error rather than a shrug: it
#: means the requested resolution is not reachable and the analysis parameters
#: need a decision, not a silently noisier answer.
DEFAULT_MAX_DRAWS = 64_000


def _z(level: float) -> float:
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")
    return NormalDist().inv_cdf(1.0 - (1.0 - level) / 2.0)


def halfwidth(successes: float, n: int, level: float = 0.95) -> float:
    """Wilson half-width for a proportion estimated from `n` draws.

    Wilson rather than the normal approximation because draws here are
    routinely all-hit or all-miss on easy and impossible problems, where the
    normal half-width collapses to zero and claims a precision that `n` draws
    cannot support.
    """
    if n <= 0:
        return 1.0
    if successes < 0 or successes > n:
        raise ValueError(f"successes={successes} outside [0, {n}]")
    z = _z(level)
    p = successes / n
    denom = 1.0 + z * z / n
    return (z / denom) * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)


@dataclass(frozen=True)
class ConvergenceReport:
    """What `B` ended up being, and why that was enough."""

    n_draws: int
    halfwidth: float
    effect_size: float
    required: float
    converged: bool

    def describe(self) -> str:
        return (
            f"B={self.n_draws}, halfwidth={self.halfwidth:.4f}, "
            f"effect={self.effect_size:.4f}, required<={self.required:.4f}"
        )


def required_halfwidth(
    effect_size: float,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    floor: float = DEFAULT_FLOOR,
) -> float:
    return max(tolerance * abs(effect_size), floor)


def check(
    successes: float,
    n_draws: int,
    effect_size: float,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    floor: float = DEFAULT_FLOOR,
    level: float = 0.95,
) -> ConvergenceReport:
    """Is `n_draws` enough to resolve `effect_size`? No interval is returned."""
    hw = halfwidth(successes, n_draws, level)
    req = required_halfwidth(effect_size, tolerance=tolerance, floor=floor)
    return ConvergenceReport(
        n_draws=n_draws,
        halfwidth=hw,
        effect_size=abs(effect_size),
        required=req,
        converged=hw <= req,
    )


def exact(
    effect_size: float,
    n_draws: int,
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    floor: float = DEFAULT_FLOOR,
) -> ConvergenceReport:
    """A report for a quantity with no Monte Carlo noise at all.

    Subsampling without replacement at `N == M` admits exactly one subsample,
    so every draw is the same draw and the noise is zero rather than small.
    Wilson would report a positive half-width there, which is not a
    conservative approximation but a wrong one: it would send the doubling
    loop chasing precision on a deterministic number.
    """
    return ConvergenceReport(
        n_draws=n_draws,
        halfwidth=0.0,
        effect_size=abs(effect_size),
        required=required_halfwidth(effect_size, tolerance=tolerance, floor=floor),
        converged=True,
    )


def converge(
    estimate,
    effect_size,
    *,
    start_draws: int = 200,
    max_draws: int = DEFAULT_MAX_DRAWS,
    tolerance: float = DEFAULT_TOLERANCE,
    floor: float = DEFAULT_FLOOR,
    level: float = 0.95,
    label: str = "",
) -> tuple[float, ConvergenceReport]:
    """Raise `B` by doubling until Monte Carlo noise cannot move the answer.

    `estimate(n_draws)` returns the mean hit rate over that many draws.
    `effect_size(mean)` returns the effect that mean is being compared against,
    as a callable because the effect is usually a difference involving the
    estimate itself.

    Returns the converged estimate and the report. Raises rather than
    returning a noisy answer at the cap: an analysis that cannot resolve its
    own effect needs a decision about `B` or about the grid, and swallowing
    that here would hide it.
    """
    n = start_draws
    while True:
        mean = estimate(n)
        report = check(
            mean * n,
            n,
            effect_size(mean),
            tolerance=tolerance,
            floor=floor,
            level=level,
        )
        if report.converged:
            return mean, report
        if n >= max_draws:
            raise MonteCarloNotConverged(
                f"{label or 'estimate'} did not converge at the cap: "
                f"{report.describe()}. Raise max_draws, widen the tolerance "
                "deliberately, or accept that this effect is not resolvable "
                "at this grid."
            )
        n = min(n * 2, max_draws)
