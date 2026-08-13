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
from collections.abc import Iterable
from dataclasses import dataclass

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


@dataclass(frozen=True)
class Margin:
    """An answer-token margin, and whether it is a measurement or a bound.

    The provider returns the top k alternatives per token and no more. k is 5
    on Together for the models this project can reach, and 5 slots are not
    guaranteed to contain all of a problem's option letters: the first probe
    response ranked `C`, `Cc`, `A`, `D` and `'C`, with option `B` absent
    entirely.

    A missing option's logprob is at or below the smallest returned logprob,
    call it `c`, or it would have been in the top k. That single fact decides
    when censoring bites, and it bites less often than it first appears:

    - **Two or more option letters present: MEASURED.** The second-highest
      present option `p2` is itself a returned value, so `p2 >= c`, and any
      absent letter sits at or below `c`. No absent letter can outrank `p2`,
      so the runner-up is determined and the margin is exactly `p1 - p2`.
      The probe response is this case: `C`, `A` and `D` returned with `B`
      absent, and `B` cannot outrank `A` because it did not outrank the fifth
      slot.
    - **Fewer than two option letters present: RIGHT-CENSORED at `p1 - c`.**
      The runner-up is some absent letter bounded above by `c`, so the margin
      is at least `p1 - c` and its true value is unknown.

    Never imputed either way. Filling a missing letter in at `c` would
    understate the margin on exactly the problems where the model is most
    certain, which are the ones a confidence gate cares about most.

    Note this is stricter about what counts as measured than "every option
    letter appears in the top k", and less conservative about when to censor.
    The looser reading would have marked the probe response censored at 38.5
    when its margin is determined at 36.0.
    """

    value: float | None
    censored: bool
    k: int
    options_present: int
    options_missing: tuple[str, ...]

    @property
    def measured(self) -> bool:
        return self.value is not None and not self.censored


def answer_margin_vs_runner_up(
    answer_logprobs: dict[str, float] | None,
    option_letters: Iterable[str] | None = None,
) -> Margin:
    """Top option-token logprob minus the runner-up option's.

    `answer_logprobs` is the provider's top-k mapping at the answer position,
    token to logprob, verbatim. `option_letters` is the problem's option set;
    without it the censoring question cannot be asked, so the result is
    reported as censored with the options unknown rather than as measured.

    Returns a `Margin` whose value is None when logprobs were not retained.
    The gate is then unavailable, which is not the same as a margin of zero.
    """
    if not answer_logprobs:
        return Margin(None, censored=False, k=0, options_present=0, options_missing=())

    k = len(answer_logprobs)
    ordered = sorted(answer_logprobs.values(), reverse=True)

    if option_letters is None:
        # No option set to check against. The margin between the top two
        # returned tokens is not necessarily a margin between two options.
        value = ordered[0] - ordered[1] if k >= 2 else None
        return Margin(value, censored=True, k=k, options_present=0, options_missing=())

    wanted = [str(letter) for letter in option_letters]
    present = {
        letter: logprob
        for letter, logprob in answer_logprobs.items()
        if letter.strip() in wanted
    }
    missing = tuple(sorted(set(wanted) - {letter.strip() for letter in present}))

    if not present:
        return Margin(
            None, censored=True, k=k, options_present=0, options_missing=missing
        )

    top = max(present.values())
    if len(present) >= 2:
        # The runner-up is determined: any absent letter is at or below the
        # smallest returned logprob, which is at or below this one.
        runner_up = sorted(present.values(), reverse=True)[1]
        return Margin(
            top - runner_up,
            censored=False,
            k=k,
            options_present=len(present),
            options_missing=missing,
        )

    # One option letter returned. The runner-up is an absent letter bounded
    # above by the smallest returned logprob, so this is a lower bound.
    return Margin(
        top - ordered[-1],
        censored=True,
        k=k,
        options_present=len(present),
        options_missing=missing,
    )


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
