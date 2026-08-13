"""Schema conformance and the integrity checks from doc 4 s9.

These are importable so that both the test suite and the pipeline itself can
run them; a check that only lives in a test does not protect a live run.
"""

from __future__ import annotations

from typing import Any

from argmax.errors import SchemaViolation
from argmax.schema import REQUIRED_SAMPLE_FIELDS, Sample


def check_required_fields(record: dict[str, Any]) -> list[str]:
    """Return the required keys missing from a raw record."""
    return sorted(REQUIRED_SAMPLE_FIELDS - record.keys())


def check_no_coercion(record: dict[str, Any]) -> str | None:
    """No record may have is_correct == False with extracted_answer == null."""
    if record.get("extracted_answer") is None and record.get("is_correct") is False:
        return "is_correct=False with extracted_answer=None"
    return None


def check_span_integrity(record: dict[str, Any]) -> str | None:
    """answer_span_tokens must index inside the stored logprob array."""
    span = record.get("answer_span_tokens")
    if span is None:
        return None
    logprobs = record.get("logprobs_raw")
    if not logprobs:
        return "answer_span_tokens set but no logprobs_raw stored"
    tokens = logprobs.get("content") or logprobs.get("tokens") or []
    lo, hi = span
    if lo < 0 or hi > len(tokens) or hi < lo:
        return f"answer_span_tokens {span} outside logprob array of {len(tokens)}"
    return None


def check_coverage_honesty(record: dict[str, Any]) -> str | None:
    """Partial logprob coverage must be declared, never inferred.

    Silent partial coverage would be defect 1 in a new costume.
    """
    coverage = record.get("logprob_coverage")
    if coverage is None:
        return "logprob_coverage absent"
    if not 0.0 <= float(coverage) <= 1.0:
        return f"logprob_coverage out of range: {coverage}"
    return None


CHECKS = (
    check_no_coercion,
    check_span_integrity,
    check_coverage_honesty,
)


def validate_record(record: dict[str, Any]) -> list[str]:
    """Every problem with one raw record, as a list of messages."""
    problems = [f"missing required field: {f}" for f in check_required_fields(record)]
    for check in CHECKS:
        msg = check(record)
        if msg:
            problems.append(msg)
    try:
        Sample.model_validate(record)
    except ValueError as exc:
        problems.append(str(exc))
    return problems


def assert_valid(record: dict[str, Any]) -> None:
    problems = validate_record(record)
    if problems:
        raise SchemaViolation("; ".join(problems))
