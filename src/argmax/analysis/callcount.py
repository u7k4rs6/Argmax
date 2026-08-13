"""Few-sample estimation of the optimal call count, and its baselines.

Thread A, reformulated: does an estimator that infers per-problem difficulty
from `k` samples predict the call count that a full run measures as best?

## What this implements, and what it does not

This is a **reconstruction** of the estimator described in arXiv:2608.11403's
Positioning section, which characterises Chen et al. 2024 as attributing the
rise-then-fall majority-vote curve "to a mixture of easy and hard queries within
a task (more calls help the easy ones and hurt the hard ones)" and using "that
structure to estimate, from a small number of samples, the call count that
maximizes aggregate performance". Chen et al.'s own code is not available to
this project. The mechanism reconstructed here is:

  1. from `k` samples per problem, estimate that problem's answer distribution
  2. predict its majority-vote accuracy at every grid point from that estimate
  3. average the per-problem predictions to get a predicted aggregate curve
  4. take the grid point maximising it

That is the mixture structure doing the work: heterogeneity across problems is
what makes the predicted aggregate curve turn over, and a model with a single
pooled rate cannot produce that shape.

**The estimator is given ground-truth labels for its `k` samples.** A
deploy-time signal would not have them. Granting them makes this the strongest
form of the method, so a failure here is a failure a fortiori: if labelled
few-sample estimation cannot beat a naive labelled baseline, the verifier-free
version cannot either. Recorded as a deliberate choice, not an oversight.

## Baselines

Every estimator is scored against three, fixed before any comparison:

  - `always_max`: the largest grid point, which is what fixed-budget voting does
  - `always_one`: no voting at all
  - `naive_within_k`: the best grid point measurable inside `k` samples, with no
    mixture model and no extrapolation beyond what those samples show

`naive_within_k` is the one that matters. It gets the same labelled `k` samples
and differs only in refusing to model per-problem structure, so the difference
between it and the estimator is what the mixture structure buys.

## Ties

Every argmax over the grid resolves ties to the **smallest** N. Two call counts
that measure equally well are not equally good: the cheaper one is better, and a
tie-break preferring the larger would flatter any method that guesses high. The
grid is ascending and `max` keeps the first maximum, so this is the behaviour
rather than a special case, and a test pins it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: The published grid.
GRID = (1, 2, 4, 8, 16, 32, 64)

#: What `naive_within_k` does when its best measurable N is the largest it can
#: measure, meaning the data are still improving where they run out. Frozen on
#: exploratory data; see notes/thread_a.md.
BOUNDARY_RULES = ("stay", "extrapolate_to_max")


def _plurality_hits(
    counts: np.ndarray, correct_idx: int, rng: np.random.Generator
) -> np.ndarray:
    """Plurality winner per row with a uniform random tie-break, as 0/1 hits.

    The jitter is bounded below 0.5 so it reorders exact ties and never
    promotes a lower count, which is the same rule `curves.majority_vote` uses.
    """
    total = counts.sum(axis=1)
    jitter = rng.random(counts.shape) * 0.5
    winner = np.argmax(counts + jitter, axis=1)
    return ((winner == correct_idx) & (total > 0)).astype(np.float64)


def vote_accuracy_point(
    codes: np.ndarray,
    correct_idx: int,
    n_options: int,
    grid: tuple[int, ...],
    n_draws: int,
    rng: np.random.Generator,
) -> dict[int, float]:
    """Measured majority-vote accuracy per grid point, from a stored pool.

    Subsampling is without replacement and nested: one permutation per draw,
    with the grid points reading prefixes of it, matching `curves._grid_hits`.
    A test asserts the two agree.
    """
    M = len(codes)
    order = np.argsort(rng.random((n_draws, M)), axis=1)
    drawn = codes[order]
    onehot = drawn[:, :, None] == np.arange(n_options, dtype=np.int16)[None, None, :]
    cum = np.cumsum(onehot, axis=1, dtype=np.int32)
    return {
        N: float(_plurality_hits(cum[:, min(N, M) - 1, :], correct_idx, rng).mean())
        for N in grid
    }


def predicted_curve_from_counts(
    counts: np.ndarray,
    correct_idx: int,
    grid: tuple[int, ...],
    alpha: float,
    n_draws: int,
    rng: np.random.Generator,
) -> dict[int, float]:
    """Predicted majority-vote accuracy at each N from an estimated distribution.

    `counts` is the option histogram of the `k` observed samples. `alpha` is
    add-alpha smoothing, without which a problem whose k samples all agree is
    predicted to be certain at every N, which at k=4 is most problems.
    """
    p = counts + alpha
    p = p / p.sum()
    out = {}
    for N in grid:
        draws = rng.multinomial(N, p, size=n_draws)
        out[N] = float(_plurality_hits(draws, correct_idx, rng).mean())
    return out


@dataclass(frozen=True)
class Prediction:
    """One method's answer, per problem and aggregate."""

    name: str
    n_hat_aggregate: int
    n_hat_per_problem: dict[str, int] = field(default_factory=dict)


def estimate_chen(
    observed: dict[str, np.ndarray],
    correct: dict[str, int],
    n_options: int,
    *,
    grid: tuple[int, ...] = GRID,
    alpha: float,
    n_draws: int,
    seed: int,
) -> Prediction:
    """The reconstruction: per-problem distributions, averaged into a curve."""
    rng = np.random.default_rng(seed)
    per_problem: dict[str, int] = {}
    aggregate = dict.fromkeys(grid, 0.0)

    for pid, counts in observed.items():
        curve = predicted_curve_from_counts(
            counts, correct[pid], grid, alpha, n_draws, rng
        )
        per_problem[pid] = max(grid, key=lambda N: curve[N])
        for N in grid:
            aggregate[N] += curve[N]

    n = len(observed)
    aggregate = {N: v / n for N, v in aggregate.items()}
    return Prediction(
        name="chen",
        n_hat_aggregate=max(grid, key=lambda N: aggregate[N]),
        n_hat_per_problem=per_problem,
    )


def estimate_naive_within_k(
    sampled: dict[str, np.ndarray],
    correct: dict[str, int],
    n_options: int,
    k: int,
    *,
    grid: tuple[int, ...] = GRID,
    boundary_rule: str,
    n_draws: int,
    seed: int,
) -> Prediction:
    """Best grid point measurable inside k samples, no per-problem model.

    Measures the aggregate vote accuracy at each `N <= k` by subsampling the
    same k labelled samples, then takes the argmax. When that argmax sits at
    the largest measurable N, the data are still improving where they stop, and
    `boundary_rule` decides what to do about it.
    """
    if boundary_rule not in BOUNDARY_RULES:
        raise ValueError(f"unknown boundary_rule {boundary_rule!r}")

    rng = np.random.default_rng(seed)
    measurable = tuple(N for N in grid if k >= N)
    aggregate = dict.fromkeys(measurable, 0.0)
    per_problem: dict[str, int] = {}

    for pid, codes in sampled.items():
        curve = vote_accuracy_point(
            codes, correct[pid], n_options, measurable, n_draws, rng
        )
        best = max(measurable, key=lambda N: curve[N])
        if best == measurable[-1] and boundary_rule == "extrapolate_to_max":
            best = grid[-1]
        per_problem[pid] = best
        for N in measurable:
            aggregate[N] += curve[N]

    n = len(sampled)
    aggregate = {N: v / n for N, v in aggregate.items()}
    best = max(measurable, key=lambda N: aggregate[N])
    if best == measurable[-1] and boundary_rule == "extrapolate_to_max":
        best = grid[-1]
    return Prediction(
        name="naive_within_k", n_hat_aggregate=best, n_hat_per_problem=per_problem
    )


def constant_baseline(name: str, value: int, problems: list[str]) -> Prediction:
    return Prediction(
        name=name,
        n_hat_aggregate=value,
        n_hat_per_problem=dict.fromkeys(problems, value),
    )


# --- scoring ----------------------------------------------------------------


def aggregate_regret(
    truth: dict[int, float], n_hat: int, grid: tuple[int, ...] = GRID
) -> float:
    """Accuracy points given up by choosing `n_hat` instead of the best N.

    `truth` is the measured aggregate curve, so this is the quantity that
    matters: not whether the estimator named the right N, but what it cost.
    """
    return max(truth[N] for N in grid) - truth[n_hat]


def grid_distance(n_hat: int, n_star: int) -> float:
    """Distance in grid steps. The grid is geometric, so log2 is the metric."""
    return abs(float(np.log2(n_hat)) - float(np.log2(n_star)))


def per_problem_regret(
    truth_by_problem: dict[str, dict[int, float]],
    n_hat_by_problem: dict[str, int],
    grid: tuple[int, ...] = GRID,
) -> float:
    values = [
        max(curve[N] for N in grid) - curve[n_hat_by_problem[pid]]
        for pid, curve in truth_by_problem.items()
    ]
    return float(np.mean(values))


def per_problem_regret_terms(
    truth_by_problem: dict[str, dict[int, float]],
    a: dict[str, int],
    b: dict[str, int],
    grid: tuple[int, ...] = GRID,
) -> np.ndarray:
    """Per-problem paired difference in regret between two methods.

    Returned per problem rather than averaged, because the resolution
    calculation needs the spread and the sign, not the mean.
    """
    out = []
    for pid, curve in truth_by_problem.items():
        best = max(curve[N] for N in grid)
        out.append((best - curve[a[pid]]) - (best - curve[b[pid]]))
    return np.array(out, dtype=float)
