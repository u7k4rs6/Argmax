"""Extraction is instrumented, and the reasoning split reports its own failure.

NOTE: the ladder itself is a structural stand-in until the passes are ported
verbatim from the published self-consistency-backfire repo. These tests assert
the INSTRUMENTATION CONTRACT (which pass fired, what span it matched), which
is what doc 4 s3.6 requires and what survives the port.
"""

from __future__ import annotations

from argmax.extract.ladder import char_span_to_token_span, extract
from argmax.extract.split import split_reasoning
from argmax.schema import SplitMethod


def test_extraction_records_which_pass_fired():
    e = extract("Some working. Answer: C", n_options=4)
    assert e.extracted_answer == "C"
    assert e.extraction_pass == 1


def test_span_points_at_the_answer_in_raw_text():
    text = "Some working. Answer: C"
    e = extract(text, n_options=4)
    lo, hi = e.answer_span_chars
    assert text[lo:hi] == "C"


def test_a_letter_outside_the_option_range_is_not_an_answer():
    """n_options is per problem; J is not an answer to a 4-choice question."""
    assert extract("Answer: J", n_options=4).extracted_answer is None


def test_total_failure_is_null_not_a_guess():
    e = extract("I cannot determine this.", n_options=4)
    assert e.extracted_answer is None
    assert e.extraction_pass is None
    assert e.answer_span_chars is None


def test_extractor_version_travels_with_every_extraction():
    """The ladder will be revised; old records must stay interpretable."""
    assert extract("Answer: A", n_options=4).extractor_version


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
