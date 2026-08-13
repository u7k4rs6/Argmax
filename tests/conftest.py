"""Shared fixtures, and the skip registry.

Tests run OFFLINE against recorded fixture responses. No API key in CI.

## Why skips are counted

A skipped test is a test that did not run, and a suite that quietly grows
skips is a suite that quietly stops checking things. Everything skipped here
is skipped for one reason, that the data it checks does not exist before Step
0, and every one of those reasons is named below.

The default run must produce EXACTLY the skips registered for it. A third skip
fails the run loudly rather than scrolling past as an `s`.
"""

from __future__ import annotations

from typing import Any

import pytest

from argmax.schema import OutcomeClass, Sample, SplitMethod

#: nodeid -> the exact reason that skip is allowed to give.
#:
#: Adding a row here is a deliberate act: it says a test cannot run yet and
#: names what would make it runnable. Removing the condition is what closes
#: the row, not deleting it.
EXPECTED_SKIPS: dict[str, str] = {
    # The default suite. pytest collects test_*.py only, so falsification.py
    # is not in this run; `make verify` runs it on its own.
    # No longer skips: the margin-v1 run created a raw store, so this test
    # runs and fails, because derive.py is still blocked. Left registered so
    # that a future skip of it is not mistaken for the old condition.
    "tests/test_recompute.py::test_derived_rebuilds_byte_identically": (
        "no raw store yet (pre-Step 0)"
    ),
    "tests/test_recompute.py::test_nothing_is_derived_only": (
        "no derived tables yet (pre-Step 0)"
    ),
    # No longer skips: margin-v1 produced derived artifacts, so this now runs
    # over them. Row kept so a future skip is not mistaken for the old
    # condition.
    "tests/test_answer_rate_pairing.py::test_the_published_artifacts_pair": (
        "no derived artifacts yet (pre-Step 0)"
    ),
    # `make verify`, run as `pytest tests/falsification.py`.
    "tests/falsification.py::test_every_registered_claim_resolves_to_backing_rows": (
        "no claims registered yet (pre-Step 0)"
    ),
    "tests/falsification.py::test_thresholds_are_literal_values_in_the_registry": (
        "no thresholds registered yet (pre-Step 0)"
    ),
    "tests/falsification.py::test_stored_verdicts_match_recomputed_verdicts": (
        "no stored verdicts yet (pre-Step 0)"
    ),
    "tests/falsification.py::test_manifest_grid_fits_M": "no runs yet (pre-Step 0)",
}

#: What the default `pytest` invocation must produce, exactly.
EXPECTED_DEFAULT_SKIP_COUNT = 1

_OBSERVED: list[tuple[str, str]] = []


def _skip_reason(report: pytest.TestReport) -> str:
    """The reason string out of a skip report, however it was raised."""
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:
        return str(longrepr[2]).removeprefix("Skipped: ").strip()
    return str(longrepr)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.skipped and report.when in ("setup", "call"):
        _OBSERVED.append((report.nodeid, _skip_reason(report)))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run when the skips are not the ones that were signed off.

    Two failures are caught here. An unregistered skip, which is a test that
    stopped running without anybody saying so. And, on the default run, a
    count that is not exactly the registered one, which catches a registered
    test starting to skip in a run where it was supposed to execute.
    """
    problems: list[str] = []

    for nodeid, reason in _OBSERVED:
        expected = EXPECTED_SKIPS.get(nodeid)
        if expected is None:
            problems.append(f"unregistered skip: {nodeid} ({reason})")
        elif expected != reason:
            problems.append(
                f"{nodeid} skipped for an unregistered reason: "
                f"{reason!r}, expected {expected!r}"
            )

    # Only the whole-suite invocation is held to the exact count. A run
    # narrowed to one file or filtered with -k or -m legitimately produces
    # fewer, so the count is checked when pytest fell back to `testpaths` and
    # nothing was filtered out. `config.args` is the path list, not the flags:
    # checking the raw argv would let `pytest -q` slip past as "not default".
    config = session.config
    is_default_run = (
        list(config.args) == list(config.getini("testpaths"))
        and not config.option.keyword
        and not config.option.markexpr
    )
    if is_default_run and len(_OBSERVED) != EXPECTED_DEFAULT_SKIP_COUNT:
        problems.append(
            f"the default suite skipped {len(_OBSERVED)} tests, expected "
            f"exactly {EXPECTED_DEFAULT_SKIP_COUNT}: "
            f"{sorted(n for n, _ in _OBSERVED)}"
        )

    if problems:
        session.exitstatus = 1
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            reporter.write_sep("=", "skip registry", red=True)
            for problem in problems:
                reporter.write_line(problem, red=True)
            reporter.write_line(
                "Every skip must be registered in tests/conftest.py with the "
                "reason it gives. A skipped test is a test that did not run."
            )


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
