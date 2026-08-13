"""Instrumentation adds fields and changes nothing.

The ladder is the copied one (PROVENANCE.md). These tests assert two separate
things: that the instrumentation contract of doc 4 s3.6 is honoured, and that
the wrapper returns exactly what the verbatim function returns. The second is
the one that protects comparability with the published numbers.
"""

from __future__ import annotations

import pytest

from argmax.extract.ladder import char_span_to_token_span, extract
from argmax.extract.scoring_verbatim import extract_answer
from argmax.extract.split import split_reasoning
from argmax.schema import SplitMethod

#: Inputs chosen to reach every rung, including the ones that only differ in
#: which slice of the text they read.
CORPUS = [
    "Some working. Answer: C",
    "Answer: c",
    r"the algebra gives \boxed{B}, therefore",
    "long reasoning\nthen a bare letter\nD",
    "Option A looks right.\nI conclude with prose only.",
    "   B   ",
    "I cannot determine this.",
    "",
    "answer: A and later answer: D",
    "A" * 300 + "\nfinal thought with no letter",
]


@pytest.mark.parametrize("text", CORPUS, ids=range(len(CORPUS)))
def test_wrapper_never_changes_the_ladder_verdict(text: str):
    """Same answer, same rung, for every input. This is the whole point."""
    verbatim = extract_answer(text)
    wrapped = extract(text, n_options=4)

    assert wrapped.extracted_answer == verbatim.answer
    assert wrapped.verbatim_pass_number == verbatim.pass_number


@pytest.mark.parametrize("text", CORPUS, ids=range(len(CORPUS)))
def test_span_points_at_the_answer_it_reports(text: str):
    """A span that does not contain the reported letter is worse than none."""
    e = extract(text, n_options=4)
    if e.answer_span_chars is None:
        return
    lo, hi = e.answer_span_chars
    assert text[lo:hi].upper() == e.extracted_answer


def test_extraction_records_which_pass_fired():
    e = extract("Some working. Answer: C", n_options=4)
    assert e.extracted_answer == "C"
    assert e.extraction_pass == 1


def test_a_span_is_produced_for_every_rung_that_fires():
    """Instrumentation that only works on rung 1 would leave the hard cases,
    which are exactly the ones the margin analysis is about, unmeasured."""
    for text, expected_pass in (
        ("Answer: C", 1),
        (r"so \boxed{B} follows", 2),
        ("reasoning\nD", 3),
        ("Option A looks right.\nI conclude with prose only.", 4),
    ):
        e = extract(text, n_options=4)
        assert e.extraction_pass == expected_pass
        assert e.answer_span_chars is not None, f"no span at pass {expected_pass}"


def test_indented_last_line_still_gets_a_correct_span():
    """The ladder strips the line before matching; the offset must account for
    that or the span points at the indentation."""
    text = "working\n\n      C   "
    e = extract(text, n_options=4)
    lo, hi = e.answer_span_chars
    assert text[lo:hi] == "C"


def test_ladder_exhausted_is_null_not_five():
    """Pass 5 in the copied ladder means the LLM scorer, which never runs here.

    Doc 4 s3.6 wants null when no pass fired. The raw value is kept alongside
    so a pass distribution stays comparable with the published one.
    """
    e = extract("I cannot determine this.", n_options=4)
    assert e.extracted_answer is None
    assert e.extraction_pass is None
    assert e.verbatim_pass_number == 5
    assert e.answer_span_chars is None


def test_a_tier_the_ladder_cannot_score_is_refused():
    """The published passes are hard-coded to A-D. A 10-option tier scored by
    them would silently never return E through J."""
    with pytest.raises(ValueError, match="hard-coded"):
        extract("Answer: J", n_options=10)


def test_extractor_version_names_both_the_ladder_and_the_wrapper():
    """The ladder will be revised; old records must stay interpretable."""
    version = extract("Answer: A", n_options=4).extractor_version
    assert "backfire-prereg-v1.0" in version
    assert "argmax-instr" in version


# --- reasoning split, unchanged ---------------------------------------------


def test_unclosed_delimiter_is_a_failed_split_not_an_error():
    """Exactly the truncated-mid-thought case: opened and never closed."""
    s = split_reasoning({}, "<think>reasoning that never fin", delivery="delimiter")
    assert s.split_method == SplitMethod.delimiter
    assert s.split_ok is False
    assert s.answer_text is None


def test_closed_delimiter_splits_cleanly():
    s = split_reasoning({}, "<think>work</think>Answer: B", delivery="delimiter")
    assert s.split_ok is True
    assert s.reasoning_text == "work"
    assert s.answer_text == "Answer: B"


def test_api_field_split_uses_the_field():
    s = split_reasoning(
        {"reasoning": "hidden chain"}, "Answer: B", delivery="api_field"
    )
    assert s.split_method == SplitMethod.api_field
    assert s.reasoning_text == "hidden chain"


def test_token_span_is_none_when_logprobs_were_not_retained():
    """An absent span is honest; an invented one is not."""
    assert char_span_to_token_span(None, (0, 1)) is None


def test_token_span_indexes_the_stored_array():
    logprobs = {"content": [{"token": "Answer"}, {"token": ":"}, {"token": " C"}]}
    span = char_span_to_token_span(logprobs, (8, 10))
    assert span is not None
    lo, hi = span
    assert 0 <= lo < hi <= len(logprobs["content"])
