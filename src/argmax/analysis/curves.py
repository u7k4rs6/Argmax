"""Vote curves, and the paired differences that decide their shape.

The single most important architectural decision, implemented:

    Sample once at M per problem. Derive every N in the grid by subsampling
    the stored samples. Never call the API again to get a smaller N.

Subsampling is WITHOUT REPLACEMENT, which emulates "what if I had only drawn
N". With replacement inflates agreement through duplicates.

## Two layers, only one of which is a confidence interval

  - **Monte Carlo**, `argmax.analysis.convergence`: only `B` of the `C(M, N)`
    possible subsamples are drawn. Reported as a converged half-width, never
    as an interval. `B` is raised until this noise cannot move the answer.

  - **Pool bootstrap**, `argmax.analysis.bootstrap`: only `M` samples were
    drawn from the model. This is the reported CI, and it is the only thing
    in this codebase called a CI.

## Shape is decided on paired differences, not on overlapping intervals

Accuracy at different `N` comes from the same pool of `M` stored samples, so
the estimates are strongly correlated. Asking whether two marginal intervals
overlap is the overlapping-CI fallacy: it is far more conservative than the
paired test and it is biased toward calling curves flat. On this study a false
flat is a missed backfire, which is the effect the whole thing exists to
measure.

So the differences are formed inside each bootstrap replicate, where both
quantities see the same resampled pool:

    vote_acc(N) - single_sample_acc          for every N in the grid
    vote_acc(N) - vote_acc(N')               for adjacent grid points

and the interval is taken over the distribution of those differences. Flat
means the interval contains zero.

The per-replicate differences are persisted, not just the interval. Defect 2
in the published study was this same hole from the other side: aggregates were
kept, per-problem outcomes were not, and the paired bootstrap it needed became
impossible without a full confirmatory re-run.

## Cost

Each bootstrap replicate reruns the Monte Carlo layer, so the work is roughly
`n_bootstrap * n_draws` subsample draws per problem. The defaults are chosen
for a real run; tests pass much smaller values.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from argmax.analysis import convergence
from argmax.analysis.bootstrap import (
    DEFAULT_LEVEL,
    DEFAULT_N_BOOTSTRAP,
    Interval,
    confidence_interval,
)
from argmax.keys import SEED_RECIPE, subsample_seed
from argmax.schema import CurveShape, DrawScheme, PairedDifference, UnansweredPolicy

VS_SINGLE = "vs_single"
ADJACENT = "adjacent"


def majority_vote(answers: list[str | None], rng: random.Random) -> str | None:
    """Plurality with a RANDOM tie-break.

    Deterministic tie-breaks (first-seen, alphabetical) bias toward whichever
    option the model happens to emit first, and that bias is invisible in the
    aggregate. The rng is seeded from content, so this stays reproducible.
    """
    votes = [a for a in answers if a is not None]
    if not votes:
        return None
    counts = Counter(votes)
    top = max(counts.values())
    winners = sorted(k for k, v in counts.items() if v == top)
    return winners[0] if len(winners) == 1 else rng.choice(winners)


def single_sample_accuracy(
    answers: list[str | None],
    correct_option: str,
    *,
    unanswered_policy: UnansweredPolicy = UnansweredPolicy.exclude,
) -> float | None:
    if unanswered_policy == UnansweredPolicy.exclude:
        pool = [a for a in answers if a is not None]
    else:
        pool = list(answers)
    if not pool:
        return None
    return sum(1.0 for a in pool if a == correct_option) / len(pool)


# --- the vectorised core ----------------------------------------------------


def _encode(pool: list[str | None], correct_option: str) -> tuple[np.ndarray, int, int]:
    """Answers to integer codes. `-1` is "no answer", which never wins a vote.

    An unanswered sample under `score_as_wrong` occupies a slot in the
    subsample and casts no vote, which is what the scalar implementation does
    and what the policy means.
    """
    options = sorted({a for a in pool if a is not None} | {correct_option})
    index = {opt: i for i, opt in enumerate(options)}
    codes = np.array([index[a] if a is not None else -1 for a in pool], dtype=np.int16)
    return codes, len(options), index[correct_option]


def _winner_hits(
    counts: np.ndarray, correct_idx: int, rng: np.random.Generator
) -> np.ndarray:
    """Plurality winner per row, random tie-break, as 0/1 hits.

    The jitter is bounded below 0.5 so it can only reorder exact ties, never
    promote a lower count. Ties then resolve uniformly, matching
    `majority_vote`.
    """
    total = counts.sum(axis=1)
    jitter = rng.random(counts.shape) * 0.5
    winner = np.argmax(counts + jitter, axis=1)
    return ((winner == correct_idx) & (total > 0)).astype(np.float64)


def _grid_hits(
    codes: np.ndarray,
    n_options: int,
    correct_idx: int,
    n_grid: list[int],
    n_draws: int,
    rng: np.random.Generator,
    draw_scheme: DrawScheme,
) -> dict[int, np.ndarray]:
    """Per-draw 0/1 outcomes for every grid point.

    Without replacement the draws are NESTED: one permutation per replicate,
    and the grid points read prefixes of it. Nesting is common random numbers
    across `N`, which cancels Monte Carlo noise out of the adjacent-pair
    differences instead of adding two independent noises together.
    """
    M = len(codes)
    out: dict[int, np.ndarray] = {}

    if draw_scheme == DrawScheme.without_replacement:
        order = np.argsort(rng.random((n_draws, M)), axis=1)
        drawn = codes[order]
        onehot = (
            drawn[:, :, None] == np.arange(n_options, dtype=np.int16)[None, None, :]
        )
        cum = np.cumsum(onehot, axis=1, dtype=np.int32)
        for N in n_grid:
            out[N] = _winner_hits(cum[:, N - 1, :], correct_idx, rng)
        return out

    for N in n_grid:
        drawn = codes[rng.integers(0, M, size=(n_draws, N))]
        onehot = (
            drawn[:, :, None] == np.arange(n_options, dtype=np.int16)[None, None, :]
        )
        out[N] = _winner_hits(onehot.sum(axis=1, dtype=np.int32), correct_idx, rng)
    return out


# --- results ----------------------------------------------------------------


@dataclass(frozen=True)
class CurvePoint:
    N: int
    accuracy: float
    ci_low: float  # pool bootstrap; the only CI in this codebase
    ci_high: float
    mc_halfwidth: float  # Monte Carlo noise, a convergence statistic
    n_draws: int
    n_bootstrap: int
    degenerate: bool  # N == M without replacement: one possible subsample


@dataclass(frozen=True)
class PairedComparison:
    """One comparison, its interval, and every replicate behind it."""

    comparison: str  # VS_SINGLE | ADJACENT
    N: int
    N_other: int | None
    difference: float
    interval: Interval
    replicates: list[float] = field(repr=False, default_factory=list)

    @property
    def flat(self) -> bool:
        """Indistinguishable from no change at this level."""
        return self.interval.contains_zero()

    def rows(self, problem_id: str, model_slug: str) -> list[PairedDifference]:
        """One persisted row per replicate. Aggregates alone are defect 2."""
        return [
            PairedDifference(
                problem_id=problem_id,
                model_slug=model_slug,
                comparison=self.comparison,
                N=self.N,
                N_other=self.N_other,
                replicate=i,
                difference=d,
            )
            for i, d in enumerate(self.replicates)
        ]


@dataclass(frozen=True)
class CurveResult:
    problem_id: str
    model_slug: str
    points: list[CurvePoint]
    comparisons: list[PairedComparison]
    shape: CurveShape | None
    single_sample_accuracy: float
    n_draws: int
    n_bootstrap: int
    draw_scheme: DrawScheme
    seed_recipe: str = SEED_RECIPE

    def rows(self) -> list[PairedDifference]:
        return [
            row
            for c in self.comparisons
            for row in c.rows(self.problem_id, self.model_slug)
        ]

    def backfire_significant(self) -> dict[int, bool]:
        """A drop against single sampling that the paired interval excludes zero for.

        Distinct from doc 4's `backfire[N]`, which is the bare point-estimate
        comparison. Both are kept: the bare one for comparability with the
        published definition, this one for a claim anybody can defend.
        """
        return {
            c.N: (c.interval.high < 0.0)
            for c in self.comparisons
            if c.comparison == VS_SINGLE
        }


# --- the estimator ----------------------------------------------------------


def vote_curve(
    answers: list[str | None],
    correct_option: str,
    *,
    n_grid: list[int],
    problem_id: str,
    model_slug: str,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    start_draws: int = 200,
    max_draws: int = convergence.DEFAULT_MAX_DRAWS,
    bootstrap_draws: int | None = None,
    draw_scheme: DrawScheme = DrawScheme.without_replacement,
    unanswered_policy: UnansweredPolicy = UnansweredPolicy.exclude,
    level: float = DEFAULT_LEVEL,
    tolerance: float = convergence.DEFAULT_TOLERANCE,
    floor: float = convergence.DEFAULT_FLOOR,
) -> CurveResult:
    """The curve, its intervals, and the paired differences that shape it.

    `answers` is the stored per-sample extracted answers for one problem and
    model, in storage order. None means no answer was extracted; it is NEVER
    silently treated as wrong. The policy decides, and the policy is
    pre-registered.
    """
    if unanswered_policy == UnansweredPolicy.exclude:
        pool = [a for a in answers if a is not None]
    else:
        pool = list(answers)

    M = len(pool)
    grid = sorted(n_grid)
    if not grid:
        raise ValueError("empty N grid")
    if grid[-1] > M:
        raise ValueError(
            f"grid point N={grid[-1]} exceeds M={M} stored samples for "
            f"{problem_id}/{model_slug}; the curve cannot reach it"
        )

    codes, n_options, correct_idx = _encode(pool, correct_option)
    single_acc = float((codes == correct_idx).mean())
    degenerate = {
        N: (N == M and draw_scheme == DrawScheme.without_replacement) for N in grid
    }

    # 1. Point estimates on the stored pool, with B raised until Monte Carlo
    #    noise cannot move any comparison on the grid.
    n_draws = start_draws
    while True:
        rng = np.random.default_rng(subsample_seed(problem_id, model_slug, 0, 0))
        hits = _grid_hits(
            codes, n_options, correct_idx, grid, n_draws, rng, draw_scheme
        )
        accuracy = {N: float(h.mean()) for N, h in hits.items()}
        reports = {
            N: (
                convergence.exact(
                    accuracy[N] - single_acc,
                    n_draws,
                    tolerance=tolerance,
                    floor=floor,
                )
                if degenerate[N]
                else convergence.check(
                    accuracy[N] * n_draws,
                    n_draws,
                    accuracy[N] - single_acc,
                    tolerance=tolerance,
                    floor=floor,
                    level=level,
                )
            )
            for N in grid
        }
        if all(r.converged for r in reports.values()):
            break
        if n_draws >= max_draws:
            worst = max(reports.values(), key=lambda r: r.halfwidth - r.required)
            raise convergence.MonteCarloNotConverged(
                f"{problem_id}/{model_slug} did not converge at the cap: "
                f"{worst.describe()}. Raise max_draws, widen the tolerance "
                "deliberately, or accept that this effect is not resolvable "
                "at this grid."
            )
        n_draws = min(n_draws * 2, max_draws)

    # 2. Pool bootstrap. Both quantities in every difference see the same
    #    resampled pool, which is what makes the difference paired.
    #
    #    Cost is n_bootstrap * inner_draws subsample draws per problem. Passing
    #    a smaller `bootstrap_draws` buys speed by leaving Monte Carlo noise
    #    inside each replicate, which ADDS variance to the bootstrap
    #    distribution and therefore widens the reported interval. That is
    #    conservative rather than anti-conservative, but it is a deliberate
    #    trade and it is recorded rather than defaulted.
    inner_draws = n_draws if bootstrap_draws is None else bootstrap_draws
    boot_acc: dict[int, list[float]] = {N: [] for N in grid}
    boot_single: list[float] = []
    for b in range(n_bootstrap):
        rng_pool = np.random.default_rng(
            subsample_seed(problem_id, f"{model_slug}:pool", 0, b)
        )
        resampled = codes[rng_pool.integers(0, M, size=M)]
        boot_single.append(float((resampled == correct_idx).mean()))

        rng_mc = np.random.default_rng(
            subsample_seed(problem_id, f"{model_slug}:mc", n_draws, b)
        )
        hits_b = _grid_hits(
            resampled, n_options, correct_idx, grid, inner_draws, rng_mc, draw_scheme
        )
        for N in grid:
            boot_acc[N].append(float(hits_b[N].mean()))

    points = [
        CurvePoint(
            N=N,
            accuracy=accuracy[N],
            ci_low=confidence_interval(boot_acc[N], level).low,
            ci_high=confidence_interval(boot_acc[N], level).high,
            mc_halfwidth=reports[N].halfwidth,
            n_draws=n_draws,
            n_bootstrap=n_bootstrap,
            degenerate=degenerate[N],
        )
        for N in grid
    ]

    comparisons: list[PairedComparison] = []
    for N in grid:
        reps = [boot_acc[N][b] - boot_single[b] for b in range(n_bootstrap)]
        comparisons.append(
            PairedComparison(
                comparison=VS_SINGLE,
                N=N,
                N_other=None,
                difference=accuracy[N] - single_acc,
                interval=confidence_interval(reps, level),
                replicates=reps,
            )
        )
    for lo, hi in zip(grid, grid[1:], strict=False):
        reps = [boot_acc[hi][b] - boot_acc[lo][b] for b in range(n_bootstrap)]
        comparisons.append(
            PairedComparison(
                comparison=ADJACENT,
                N=hi,
                N_other=lo,
                difference=accuracy[hi] - accuracy[lo],
                interval=confidence_interval(reps, level),
                replicates=reps,
            )
        )

    return CurveResult(
        problem_id=problem_id,
        model_slug=model_slug,
        points=points,
        comparisons=comparisons,
        shape=classify_curve(comparisons),
        single_sample_accuracy=single_acc,
        n_draws=n_draws,
        n_bootstrap=n_bootstrap,
        draw_scheme=draw_scheme,
    )


def classify_curve(comparisons: list[PairedComparison]) -> CurveShape | None:
    """Shape from the paired differences, not from overlapping marginals.

    Flat means every difference on the curve, against single sampling and
    between adjacent grid points, has an interval containing zero. A curve is
    only called flat when nothing on it moved, rather than when two wide
    marginal intervals happened to touch.

    Returns None when the significant moves form a pattern doc 4's four labels
    cannot express, such as a fall then a rise. Recording null is honest;
    forcing it into `rise_then_fall` is not, and `curve_shape` is nullable for
    exactly this reason.
    """
    if not comparisons:
        return None
    if all(c.flat for c in comparisons):
        return CurveShape.flat_within_ci

    moves = [
        (c.N_other, c.N, 1 if c.difference > 0 else -1)
        for c in comparisons
        if c.comparison == ADJACENT and not c.flat
    ]
    if not moves:
        # Nothing moved between adjacent points, but something moved against
        # single sampling: the whole curve sits off the baseline without a
        # trend along the grid.
        return CurveShape.flat_within_ci

    signs = [s for _, _, s in sorted(moves, key=lambda m: m[1])]
    if all(s > 0 for s in signs):
        return CurveShape.monotone_up
    if all(s < 0 for s in signs):
        return CurveShape.monotone_down

    first_negative = next(i for i, s in enumerate(signs) if s < 0)
    if all(s > 0 for s in signs[:first_negative]) and all(
        s < 0 for s in signs[first_negative:]
    ):
        return CurveShape.rise_then_fall
    return None
