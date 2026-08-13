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

from argmax.analysis.curves import majority_vote
from argmax.analysis.intervals import mean_interval
from argmax.keys import subsample_seed
from argmax.schema import BudgetMatched


@dataclass(frozen=True)
class StoredSample:
    """The fields of a stored sample this computation needs."""

    extracted_answer: str | None
    completion_tokens: int
    max_tokens: int


def compare_at_budget(
    samples: list[StoredSample],
    correct_option: str,
    *,
    budget_tokens: int,
    strategy_id: str,
    problem_id: str,
    model_slug: str,
    n_draws: int = 1000,
    claim_ids: list[str] | None = None,
) -> BudgetMatched:
    """Greedily fill the budget with stored samples and vote over what fits.

    `tokens_actually_consumed` comes from the stored usage block, so a
    strategy that planned 4 samples but consumed the budget in 3 is reported
    as 3. The plan is not the measurement.
    """
    if not samples:
        raise ValueError(f"no stored samples for {problem_id}/{model_slug}")

    hits: list[float] = []
    consumed_per_draw: list[int] = []
    used_per_draw: list[int] = []

    for replicate in range(n_draws):
        rng = random.Random(
            subsample_seed(
                problem_id, f"{model_slug}:{strategy_id}", budget_tokens, replicate
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

    # Wilson on the mean of the draws, for the reason given in
    # argmax.analysis.intervals: percentiles of a 0/1 list are 0 and 1, so the
    # interval this used to report was [0, 1] for every strategy at every
    # budget, and a matched-compute table of [0, 1] intervals compares nothing.
    accuracy, lo, hi = mean_interval(hits)

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
