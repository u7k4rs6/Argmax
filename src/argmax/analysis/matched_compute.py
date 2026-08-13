"""Matched-compute comparison, as a function rather than a description.

The fix for defect 3, and the one that requires the most discipline, because
the failure mode is a fluent sentence rather than a missing file. A
matched-compute baseline was never implemented in the predecessor, yet prose
describing one reached the submitted draft; every real comparison was flat
N=64.

Given a total token budget T for a problem, compare the strategies achievable
at that budget:

    many short samples  |  fewer long samples  |  one very long sample

using STORED usage data, not planned token counts. Every sentence in the paper
that claims a compute-matched comparison must resolve to a row produced here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from argmax.analysis import convergence
from argmax.analysis.bootstrap import DEFAULT_N_BOOTSTRAP, confidence_interval
from argmax.analysis.curves import majority_vote
from argmax.keys import subsample_seed
from argmax.schema import BudgetMatched


@dataclass(frozen=True)
class StoredSample:
    """The fields of a stored sample this computation needs."""

    extracted_answer: str | None
    completion_tokens: int
    max_tokens: int


def _fill_budget(
    samples: list[StoredSample],
    correct_option: str,
    *,
    budget_tokens: int,
    strategy_id: str,
    problem_id: str,
    model_slug: str,
    n_draws: int,
    seed_tag: str,
) -> tuple[list[float], list[int], list[int]]:
    """Greedily fill the budget in a random order, `n_draws` times."""
    hits: list[float] = []
    consumed_per_draw: list[int] = []
    used_per_draw: list[int] = []

    for replicate in range(n_draws):
        rng = random.Random(
            subsample_seed(
                problem_id,
                f"{model_slug}:{strategy_id}:{seed_tag}",
                budget_tokens,
                replicate,
            )
        )
        order = rng.sample(samples, len(samples))
        spent = 0
        chosen: list[str | None] = []
        for s in order:
            if spent + s.completion_tokens > budget_tokens:
                continue
            spent += s.completion_tokens
            chosen.append(s.extracted_answer)
        if not chosen:
            continue  # the budget does not admit even one stored sample
        winner = majority_vote(chosen, rng)
        hits.append(1.0 if winner == correct_option else 0.0)
        consumed_per_draw.append(spent)
        used_per_draw.append(len(chosen))

    return hits, consumed_per_draw, used_per_draw


def compare_at_budget(
    samples: list[StoredSample],
    correct_option: str,
    *,
    budget_tokens: int,
    strategy_id: str,
    problem_id: str,
    model_slug: str,
    n_draws: int = 1000,
    max_draws: int = convergence.DEFAULT_MAX_DRAWS,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    bootstrap_draws: int | None = None,
    claim_ids: list[str] | None = None,
) -> BudgetMatched:
    """Greedily fill the budget with stored samples and vote over what fits.

    `tokens_actually_consumed` comes from the stored usage block, so a
    strategy that planned 4 samples but consumed the budget in 3 is reported
    as 3. The plan is not the measurement.
    """
    if not samples:
        raise ValueError(f"no stored samples for {problem_id}/{model_slug}")

    hits, consumed_per_draw, used_per_draw = _fill_budget(
        samples,
        correct_option,
        budget_tokens=budget_tokens,
        strategy_id=strategy_id,
        problem_id=problem_id,
        model_slug=model_slug,
        n_draws=n_draws,
        seed_tag="point",
    )

    if not hits:
        return BudgetMatched(
            problem_id=problem_id,
            model_slug=model_slug,
            budget_tokens=budget_tokens,
            strategy_id=strategy_id,
            n_samples_used=0,
            max_tokens_per_sample=max(s.max_tokens for s in samples),
            tokens_actually_consumed=0,
            accuracy_under_strategy=None,
            ci_low=None,
            ci_high=None,
            claim_ids=claim_ids or [],
        )

    # Monte Carlo noise is a convergence statistic, not an interval, and B is
    # raised until it is small rather than reported alongside a noisy answer.
    # No cross-strategy effect is visible from inside one call, so the
    # absolute floor is the requirement: resolve this strategy's accuracy
    # below `floor` and let the caller compare strategies.
    state: dict[str, list] = {
        "hits": hits,
        "consumed": consumed_per_draw,
        "used": used_per_draw,
    }

    def estimate(n: int) -> float:
        h, c, u = _fill_budget(
            samples,
            correct_option,
            budget_tokens=budget_tokens,
            strategy_id=strategy_id,
            problem_id=problem_id,
            model_slug=model_slug,
            n_draws=n,
            seed_tag="point",
        )
        state["hits"], state["consumed"], state["used"] = h, c, u
        return sum(h) / len(h)

    accuracy, mc = convergence.converge(
        estimate,
        lambda _mean: 0.0,
        start_draws=n_draws,
        max_draws=max_draws,
        label=f"{problem_id}/{model_slug} strategy {strategy_id} at "
        f"budget {budget_tokens}",
    )
    hits, consumed_per_draw, used_per_draw = (
        state["hits"],
        state["consumed"],
        state["used"],
    )

    # The reported CI is the pool bootstrap: a different M stored samples
    # would have filled the budget with different completions.
    #
    # Cost is n_bootstrap * inner_draws budget fills. A smaller
    # `bootstrap_draws` leaves Monte Carlo noise inside each replicate, which
    # widens the interval rather than narrowing it.
    inner_draws = mc.n_draws if bootstrap_draws is None else bootstrap_draws
    boot: list[float] = []
    for b in range(n_bootstrap):
        rng = random.Random(
            subsample_seed(problem_id, f"{model_slug}:{strategy_id}:pool", 0, b)
        )
        resampled = [rng.choice(samples) for _ in samples]
        boot_hits, _, _ = _fill_budget(
            resampled,
            correct_option,
            budget_tokens=budget_tokens,
            strategy_id=strategy_id,
            problem_id=problem_id,
            model_slug=model_slug,
            n_draws=inner_draws,
            seed_tag=f"boot{b}",
        )
        if boot_hits:
            boot.append(sum(boot_hits) / len(boot_hits))

    interval = confidence_interval(boot) if boot else None
    lo = None if interval is None else interval.low
    hi = None if interval is None else interval.high

    return BudgetMatched(
        problem_id=problem_id,
        model_slug=model_slug,
        budget_tokens=budget_tokens,
        strategy_id=strategy_id,
        n_samples_used=round(sum(used_per_draw) / len(used_per_draw)),
        max_tokens_per_sample=max(s.max_tokens for s in samples),
        tokens_actually_consumed=round(sum(consumed_per_draw) / len(consumed_per_draw)),
        accuracy_under_strategy=accuracy,
        ci_low=lo,
        ci_high=hi,
        claim_ids=claim_ids or [],
    )
