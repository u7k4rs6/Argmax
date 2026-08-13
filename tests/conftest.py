"""Shared fixtures.

Tests run OFFLINE against recorded fixture responses. No API key in CI.
"""

from __future__ import annotations

from typing import Any

import pytest

from argmax.schema import OutcomeClass, Sample, SplitMethod


def make_sample_dict(**overrides: Any) -> dict[str, Any]:
    """A minimal conforming raw record. Override a field to break it on purpose."""
    base: dict[str, Any] = {
        "schema_version": 1,
        "sample_key": "0" * 64,
        "run_id": "run-test",
        "split": "exploratory",
        "benchmark": "testbench",
        "benchmark_version_hash": "1" * 64,
        "problem_id": "2" * 32,
        "problem_hash": "3" * 64,
        "sample_index": 0,
        "model_requested": "vendor/model-x",
        "model_returned": "vendor/model-x",
        "param_hash": "4" * 64,
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 512,
        "seed": 0,
        "stop": [],
        "prompt_hash": "5" * 64,
        "prompt_template_id": "tmpl-v1",
        "request_timestamp_utc": "2026-01-01T00:00:00+00:00",
        "attempt_count": 1,
        "latency_ms": 1200,
        "raw_text": "Reasoning here. Answer: C",
        "finish_reason": "stop",
        "usage_raw": {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
        },
        "logprobs_raw": None,
        "response_extras": {},
        "split_method": SplitMethod.none.value,
        "split_ok": True,
        "truncated": False,
        "hit_ceiling": False,
        "outcome_class": OutcomeClass.answered.value,
        "extractor_version": "test",
        "extraction_pass": 1,
        "extracted_answer": "C",
        "answer_span_chars": [23, 24],
        "is_correct": True,
        "pricing_snapshot_id": "snap-test",
        "cost_usd_est": 0.0001,
        "logprob_coverage": 1.0,
    }
    base.update(overrides)
    return base


@pytest.fixture
def sample_dict() -> dict[str, Any]:
    return make_sample_dict()


@pytest.fixture
def sample(sample_dict: dict[str, Any]) -> Sample:
    return Sample.model_validate(sample_dict)
