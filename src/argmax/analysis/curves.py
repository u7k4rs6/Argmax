"""Vote curves by subsampling the stored samples.

The single most important architectural decision, implemented:

    Sample once at M per problem. Derive every N in the grid by subsampling
    the stored samples. Never call the API again to get a smaller N.

Subsampling is WITHOUT REPLACEMENT, which emulates "what if I had only drawn
N". With replacement inflates agreement through duplicates.

Note the ceiling effect: at N == M, sampling without replacement yields
exactly one possible draw, so the endpoint has no subsample variance and no
CI. `vote_curve` reports that honestly by returning a degenerate interval
rather than a fabricated one. If a CI at the largest N is wanted, M must
exceed the largest grid point.

The interval reported here is SUBSAMPLE uncertainty at a fixed pool of stored
samples, not the uncertainty of having drawn only M samples from the model.
See `argmax.analysis.intervals` for why the distinction is load-bearing and
what has to happen before an interval is published as a CI on accuracy.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from argmax.analysis.intervals import mean_interval
from argmax.keys import SEED_RECIPE, subsample_seed
from argmax.schema import CurveShape, DrawScheme, UnansweredPolicy


@dataclass(frozen=True)
class CurvePoint:
    N: int
    accuracy: float
    ci_low: float
    ci_high: float
    n_draws: int
    degenerate: bool  # True at N == M: one possible draw, no subsample variance


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


def vote_curve(
    answers: list[str | None],
    correct_option: str,
    *,
    n_grid: list[int],
    problem_id: str,
    model_slug: str,
    n_draws: int = 1000,
    draw_scheme: DrawScheme = DrawScheme.without_replacement,
    unanswered_policy: UnansweredPolicy = UnansweredPolicy.exclude,
    ci: float = 0.95,
) -> list[CurvePoint]:
    """B seeded subsample draws per N; majority vote per draw; mean correctness.

    `answers` is the stored per-sample extracted answers for one problem and
    model, in storage order. None means no answer was extracted; it is NEVER
    silently treated as wrong. The policy decides, and the policy is
    pre-registered.
    """
    if unanswered_policy == UnansweredPolicy.exclude:
        pool = [a for a in answers if a is not None]
    else:
        pool = list(answers)  # None stays in and loses its vote

    M = len(pool)
    out: list[CurvePoint] = []

    for N in sorted(n_grid):
        if N > M:
            raise ValueError(
                f"grid point N={N} exceeds M={M} stored samples for "
                f"{problem_id}/{model_slug}; the curve cannot reach it"
            )
        degenerate = N == M and draw_scheme == DrawScheme.without_replacement
        draws = 1 if degenerate else n_draws

        hits: list[float] = []
        for replicate in range(draws):
            rng = random.Random(subsample_seed(problem_id, model_slug, N, replicate))
            if draw_scheme == DrawScheme.without_replacement:
                subset = rng.sample(pool, N)
            else:
                subset = [rng.choice(pool) for _ in range(N)]
            winner = majority_vote(subset, rng)
            hits.append(1.0 if winner == correct_option else 0.0)

        # Wilson on the mean of the draws. Percentiles of the draws themselves
        # are 0 and 1 for any accuracy that is not already extreme, which is
        # not a wide interval but no interval at all. The degenerate case at
        # N == M falls out of mean_interval: one draw, no spread to report,
        # and inventing one is exactly the over-claim the predecessor was
        # pushed on.
        accuracy, lo, hi = mean_interval(hits, ci)

        out.append(
            CurvePoint(
                N=N,
                accuracy=accuracy,
                ci_low=lo,
                ci_high=hi,
                n_draws=draws,
                degenerate=degenerate,
            )
        )
    return out


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


def classify_curve(points: list[CurvePoint]) -> CurveShape:
    """monotone up / monotone down / rise then fall / flat within CI.

    "Flat within CI" means every point's interval contains a value all the
    others could also take, i.e. the intervals share a common point. That is a
    statement about the curve, whereas the earlier comparison of the accuracy
    range against the total spread of all intervals was a statement about
    nothing: it read `[0, 1]` intervals off the old percentile computation and
    called every curve flat, including one climbing from 0.59 to 1.00.

    Shape is decided on the point estimates only once the intervals have
    already ruled flatness out.
    """
    if len(points) < 2:
        return CurveShape.flat_within_ci

    if max(p.ci_low for p in points) <= min(p.ci_high for p in points):
        return CurveShape.flat_within_ci

    accs = [p.accuracy for p in points]
    peak = accs.index(max(accs))
    if peak == len(accs) - 1:
        return CurveShape.monotone_up
    if peak == 0:
        return CurveShape.monotone_down
    return CurveShape.rise_then_fall


SEED_DOC = SEED_RECIPE
