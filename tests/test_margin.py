"""The answer-token margin, and when it is a bound rather than a measurement.

The provider returns k alternatives per token. k is 5 on the models this
project can reach, and 5 slots need not contain every option letter: the first
real probe response ranked C, Cc, A, D and 'C, with option B absent.

A margin published without saying which case it is is a number that means two
different things.
"""

from __future__ import annotations

import pytest

from argmax.analysis.gates import answer_margin_vs_runner_up
from argmax.schema import ProblemRecord
from tests.test_problem_record import BASE

#: The real top-5 from configs/models/qwen2.5-7b-instruct-turbo.capabilities.json.
PROBE_RESPONSE = {"'C": -38, "A": -36, "C": 0, "Cc": -36.25, "D": -38.5}


def test_two_present_options_determine_the_runner_up():
    """B is absent, and it still cannot be the runner-up.

    Any absent letter is at or below the smallest returned logprob, and A is
    above it, so the margin is determined at 36.0 rather than bounded at 38.5.
    Treating this as censored would throw away a measurement.
    """
    margin = answer_margin_vs_runner_up(PROBE_RESPONSE, "ABCD")
    assert margin.value == 36
    assert margin.censored is False
    assert margin.measured is True
    assert margin.k == 5
    assert margin.options_present == 3
    assert margin.options_missing == ("B",)


def test_one_present_option_is_right_censored():
    """With only one option letter returned, the runner-up is unknown and
    bounded above by the fifth slot, so the margin is a lower bound."""
    single = {"C": 0.0, "Cc": -36.25, "x": -37.0, "y": -38.0, "z": -38.5}
    margin = answer_margin_vs_runner_up(single, "ABCD")
    assert margin.value == 38.5
    assert margin.censored is True
    assert margin.measured is False
    assert margin.options_missing == ("A", "B", "D")


def test_all_options_present_is_measured():
    full = {"A": -2.0, "B": -5.0, "C": 0.0, "D": -9.0, "x": -12.0}
    margin = answer_margin_vs_runner_up(full, "ABCD")
    assert margin.value == pytest.approx(2.0)
    assert margin.censored is False
    assert margin.options_missing == ()


def test_nothing_is_imputed_for_a_missing_option():
    """Filling the missing letter in at the kth value would understate the
    margin on exactly the problems where the model is most certain."""
    margin = answer_margin_vs_runner_up(PROBE_RESPONSE, "ABCD")
    imputed = 0 - (-38.5)
    assert margin.value != imputed


def test_absent_logprobs_are_unavailable_not_zero():
    margin = answer_margin_vs_runner_up(None, "ABCD")
    assert margin.value is None
    assert margin.k == 0
    assert margin.measured is False


def test_without_an_option_set_the_margin_is_censored():
    """The gap between the top two returned tokens is not necessarily a gap
    between two options, so it is not reported as a measured margin."""
    margin = answer_margin_vs_runner_up(PROBE_RESPONSE)
    assert margin.censored is True
    assert margin.options_present == 0


def test_k_travels_with_every_margin():
    for logprobs in (PROBE_RESPONSE, {"C": 0.0, "x": -1.0}):
        assert answer_margin_vs_runner_up(logprobs, "ABCD").k == len(logprobs)


# --- the record refuses a margin that cannot be interpreted -----------------


def test_a_stored_margin_without_its_flag_is_refused():
    with pytest.raises(ValueError, match="answer_margin_censored"):
        ProblemRecord(**dict(BASE, answer_margin_vs_runner_up=2.0, answer_margin_k=5))


def test_a_stored_margin_without_k_is_refused():
    with pytest.raises(ValueError, match="answer_margin_k"):
        ProblemRecord(
            **dict(BASE, answer_margin_vs_runner_up=2.0, answer_margin_censored=False)
        )


def test_a_complete_margin_is_accepted():
    record = ProblemRecord(
        **dict(
            BASE,
            answer_margin_vs_runner_up=36.0,
            answer_margin_censored=False,
            answer_margin_k=5,
        )
    )
    assert record.answer_margin_k == 5


# --- provider logprob shapes -----------------------------------------------
#
# Together returns two shapes and which one arrives is a property of the model.
# Reading only one does not raise on the other: it yields no alternatives, and
# every margin in the run comes back null. Qwen3.5-9B is the model that found
# this, after 148 probe samples had already been paid for.


def _flat(alternatives: dict[str, float]) -> dict:
    return {"tokens": [" B"], "top_logprobs": [alternatives]}


def _nested(alternatives: dict[str, float]) -> dict:
    return {
        "content": [
            {
                "token": " B",
                "logprob": max(alternatives.values()),
                "top_logprobs": [
                    {"token": t, "logprob": lp} for t, lp in alternatives.items()
                ],
            }
        ]
    }


ALTS = {" B": 0.0, " A": -22.32, " X": -23.93, " C": -25.71, " b": -26.79}


def test_both_provider_shapes_yield_the_same_alternatives():
    from argmax.extract.ladder import top_alternatives_at

    assert top_alternatives_at(_flat(ALTS), 0) == ALTS
    assert top_alternatives_at(_nested(ALTS), 0) == ALTS


def test_both_provider_shapes_yield_the_same_margin():
    """The failure mode was a silently null margin, not a wrong one."""
    from argmax.analysis.gates import answer_margin_vs_runner_up
    from argmax.extract.ladder import top_alternatives_at

    margins = [
        answer_margin_vs_runner_up(top_alternatives_at(shape(ALTS), 0), "ABCD")
        for shape in (_flat, _nested)
    ]
    assert margins[0].value == margins[1].value
    assert not margins[0].censored and not margins[1].censored
    # B, A and C present, X and b are not option letters
    assert margins[0].options_present == 3
    assert abs(margins[0].value - 22.32) < 1e-9


def test_out_of_range_and_absent_positions_are_none_not_empty():
    from argmax.extract.ladder import top_alternatives_at

    assert top_alternatives_at(_nested(ALTS), 5) is None
    assert top_alternatives_at(_flat(ALTS), 5) is None
    assert top_alternatives_at(None, 0) is None
    assert top_alternatives_at({}, 0) is None
