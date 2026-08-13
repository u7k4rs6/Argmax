"""Schema conformance, and the integrity rules from doc 4 s9.

These are the tests that would have caught the predecessor's defects at write
time rather than at analysis time.
"""

from __future__ import annotations

import pytest

from argmax.persist.validate import check_required_fields, validate_record
from argmax.schema import REQUIRED_SAMPLE_FIELDS, Sample
from tests.conftest import make_sample_dict


def test_baseline_record_is_valid(sample_dict):
    assert validate_record(sample_dict) == []


@pytest.mark.parametrize("field", sorted(REQUIRED_SAMPLE_FIELDS))
def test_every_required_field_is_required(field):
    """Dropping any R field must be detected."""
    record = make_sample_dict()
    record.pop(field)
    assert field in check_required_fields(record)


def test_is_correct_is_never_coerced_to_false():
    """A missing answer is null, never wrong.

    Whether unanswered samples are excluded or scored as wrong is a
    pre-registered ANALYSIS decision, not a write-time default.
    """
    record = make_sample_dict(extracted_answer=None, is_correct=False)
    problems = validate_record(record)
    assert any("never wrong" in p or "is_correct" in p for p in problems)


def test_null_is_correct_with_no_answer_is_fine():
    record = make_sample_dict(
        extracted_answer=None,
        is_correct=None,
        extraction_pass=None,
        answer_span_chars=None,
    )
    assert validate_record(record) == []


def test_usage_raw_is_kept_whole():
    """A provider field this schema does not name must survive the round trip.

    Selecting fields at write time is how defect 1 happened.
    """
    usage = {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "some_future_reasoning_counter": 4096,
    }
    s = Sample.model_validate(make_sample_dict(usage_raw=usage))
    assert s.usage_raw == usage


def test_response_extras_captures_unnamed_fields():
    extras = {"vendor_specific_thing": {"a": 1}}
    s = Sample.model_validate(make_sample_dict(response_extras=extras))
    assert s.response_extras == extras


def test_unknown_top_level_field_is_rejected():
    """extra="forbid": a typo'd field name must not silently vanish."""
    with pytest.raises(ValueError):
        Sample.model_validate(make_sample_dict(extracted_anwser="C"))


def test_span_must_point_inside_raw_text():
    record = make_sample_dict(answer_span_chars=[0, 10_000])
    assert validate_record(record) != []


def test_truncation_is_data_not_an_error():
    """A truncated sample with no visible answer is a first-class result."""
    record = make_sample_dict(
        finish_reason="length",
        truncated=True,
        hit_ceiling=True,
        outcome_class="truncated_no_answer",
        raw_text="thinking and thinking and",
        extracted_answer=None,
        extraction_pass=None,
        answer_span_chars=None,
        is_correct=None,
    )
    assert validate_record(record) == []


def test_error_fields_only_on_api_failure():
    record = make_sample_dict(error_type="http_500")
    assert validate_record(record) != []


def test_logprob_coverage_must_be_declared():
    record = make_sample_dict()
    record.pop("logprob_coverage")
    problems = validate_record(record)
    assert any("logprob_coverage" in p for p in problems)
