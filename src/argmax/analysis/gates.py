"""Gates, persisted per problem rather than per aggregate.

The fix for defect 2. The predecessor persisted only aggregates, which is why
a paired bootstrap for the "statistically indistinguishable" claim would have
required a full confirmatory re-run, and why the claim was cut instead.

With one row per (gate, threshold, problem, model, N), a paired bootstrap is a
groupby.
"""

from __future__ import annotations

import math
from collections import Counter

from argmax.schema import GateOutcome

GATE_VERSION = "1"


# --- gate statistics --------------------------------------------------------


def plurality_agreement(answers: list[str | None]) -> float:
    """Share of answered samples that agree with the plurality winner."""
    votes = [a for a in answers if a is not None]
    if not votes:
        return 0.0
    return max(Counter(votes).values()) / len(votes)


def answer_distribution_entropy(answers: list[str | None]) -> float:
    """Shannon entropy in nats over the answer distribution."""
    votes = [a for a in answers if a is not None]
    if not votes:
        return 0.0
    total = len(votes)
    return -sum((c / total) * math.log(c / total) for c in Counter(votes).values() if c)


def mean_token_entropy(per_token_entropies: list[float]) -> float:
    """Carried over from the predecessor for comparability."""
    return (
        sum(per_token_entropies) / len(per_token_entropies)
        if per_token_entropies
        else 0.0
    )


def answer_margin_vs_runner_up(
    answer_logprobs: dict[str, float] | None,
) -> float | None:
    """New gate, enabled by the retained logprob arrays and the answer span.

    Top answer-token logprob minus the runner-up's. Returns None when logprobs
    were not retained: the gate is unavailable, not zero.
    """
    if not answer_logprobs or len(answer_logprobs) < 2:
        return None
    ordered = sorted(answer_logprobs.values(), reverse=True)
    return ordered[0] - ordered[1]


# --- evaluation -------------------------------------------------------------


def evaluate_gate(
    *,
    gate_name: str,
    statistic: float,
    threshold: float,
    threshold_source: str,
    problem_id: str,
    model_slug: str,
    N: int,
    accuracy_if_route: float | None,
    accuracy_if_hold: float | None,
    samples_if_route: int,
    samples_if_hold: int,
) -> GateOutcome:
    """Produce one persisted row.

    `samples_consumed_under_decision` is carried because the interesting
    property of a gate that does not move accuracy may be that it reaches the
    same accuracy at fewer samples.
    """
    route = statistic >= threshold
    return GateOutcome(
        gate_name=gate_name,
        gate_version=GATE_VERSION,
        threshold=threshold,
        threshold_source=threshold_source,
        problem_id=problem_id,
        model_slug=model_slug,
        N=N,
        gate_statistic=statistic,
        decision="route" if route else "hold",
        accuracy_under_decision=accuracy_if_route if route else accuracy_if_hold,
        samples_consumed_under_decision=samples_if_route if route else samples_if_hold,
    )
