"""Two layers of variation, one of which is not a confidence interval.

Monte Carlo noise shrinks with compute and says nothing about the world. The
pool bootstrap does not shrink with compute and is the only interval reported.
Keeping both under the name CI is how the narrow one ends up in a paper
claiming to be the wide one, so the separation is asserted here, including in
the naming.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from argmax.analysis import convergence
from argmax.analysis.bootstrap import Interval, confidence_interval
from argmax.errors import MonteCarloNotConverged

SRC = Path(__file__).resolve().parents[1] / "src" / "argmax"


# --- the Monte Carlo layer --------------------------------------------------


def test_halfwidth_shrinks_with_draws():
    assert convergence.halfwidth(600, 1000) < convergence.halfwidth(6, 10)


def test_all_hits_does_not_claim_certainty():
    """Wilson rather than the normal approximation, which collapses to zero
    half-width at p = 1 and asserts a precision ten draws cannot support."""
    assert convergence.halfwidth(10, 10) > 0.0


def test_no_draws_is_no_information():
    assert convergence.halfwidth(0, 0) == 1.0


def test_successes_outside_the_draw_count_is_a_bug_not_a_clamp():
    with pytest.raises(ValueError):
        convergence.halfwidth(11, 10)


def test_a_null_effect_is_held_to_the_floor_not_to_infinity():
    """A relative rule alone would demand infinite precision against a zero
    effect and the doubling loop would never terminate."""
    assert convergence.required_halfwidth(0.0) == convergence.DEFAULT_FLOOR
    assert convergence.required_halfwidth(1.0) == pytest.approx(
        convergence.DEFAULT_TOLERANCE
    )


def test_convergence_is_a_verdict_not_an_interval():
    report = convergence.check(600, 1000, effect_size=0.5)
    assert report.converged is True
    assert not hasattr(report, "ci_low")
    assert not hasattr(report, "ci_high")


def test_a_deterministic_quantity_has_zero_noise():
    """At N == M there is one possible subsample, so the noise is zero rather
    than small, and Wilson's positive half-width there is wrong."""
    report = convergence.exact(0.2, n_draws=100)
    assert report.halfwidth == 0.0
    assert report.converged is True


def test_converge_raises_draws_until_the_effect_is_resolvable():
    seen: list[int] = []

    def estimate(n: int) -> float:
        seen.append(n)
        return 0.6

    mean, report = convergence.converge(
        estimate, lambda m: m - 0.5, start_draws=10, max_draws=100_000
    )
    assert mean == 0.6
    assert seen[0] == 10 and seen[-1] > 10
    assert report.converged


def test_converge_refuses_at_the_cap():
    """Better a refusal than a noisy number that looks like a result."""
    with pytest.raises(MonteCarloNotConverged):
        convergence.converge(
            lambda n: 0.5, lambda m: 0.0, start_draws=4, max_draws=8, floor=1e-6
        )


# --- the reported interval --------------------------------------------------


def test_interval_knows_whether_it_contains_zero():
    assert Interval(-0.1, 0.2, 0.95, 100).contains_zero()
    assert not Interval(0.05, 0.2, 0.95, 100).contains_zero()


def test_interval_over_nothing_is_refused():
    with pytest.raises(ValueError):
        confidence_interval([])


def test_percentile_interval_brackets_the_bulk():
    values = [i / 1000 for i in range(1001)]
    ci = confidence_interval(values)
    assert ci.low == pytest.approx(0.025, abs=0.005)
    assert ci.high == pytest.approx(0.975, abs=0.005)
    assert ci.n_replicates == 1001


# --- the naming rule --------------------------------------------------------


def _definitions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    ]


def test_only_the_bootstrap_module_defines_something_called_an_interval():
    """One thing in this codebase is named CI, and it is the pool bootstrap.

    Record FIELDS may still be called ci_low and ci_high, because doc 4 names
    them that way. This is about definitions: functions and classes that
    produce an interval.
    """
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "bootstrap.py":
            continue
        for name in _definitions(path):
            lowered = name.lower()
            if "confidence" in lowered or lowered.endswith("interval"):
                offenders.append(f"{path.relative_to(SRC)}:{name}")
    assert not offenders, (
        f"a second thing named like a confidence interval: {offenders}. "
        "The Monte Carlo layer reports convergence, not an interval."
    )
