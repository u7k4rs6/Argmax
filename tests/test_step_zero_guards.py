"""Nothing spends money before Step 0 returns real numbers.

Each of these asserts a refusal. A refusal that stops being a refusal is how
the predecessor got a guessed token cost into a run.
"""

from __future__ import annotations

import pytest

from argmax.config import BLOCKED, is_blocked, require
from argmax.errors import (
    CapabilityMissing,
    DirtyTreeError,
    GitUnavailable,
    NoSpendCeilingSet,
    PreregTagMissing,
    SpendCeilingExceeded,
    StepZeroBlocked,
)
from argmax.sampling.ledger import Ledger, PricingSnapshot
from argmax.sampling.probe import assert_phase_supported
from argmax.sampling.spend import Projection, SpendGuard


def test_blocked_value_raises_rather_than_defaulting():
    assert is_blocked(BLOCKED)
    with pytest.raises(StepZeroBlocked) as exc:
        require(BLOCKED, "max_tokens", "configs/models/x.yaml")
    # The message says what to go and measure, not only what is missing.
    assert "p95 output tokens" in str(exc.value)


def test_none_is_also_blocked():
    with pytest.raises(StepZeroBlocked):
        require(None, "M", "configs/phases/x.yaml")


def test_no_ceiling_means_refuse_to_run(monkeypatch):
    """There is no default, because a default becomes the real limit."""
    monkeypatch.delenv("ARGMAX_SPEND_CEILING_USD", raising=False)
    with pytest.raises(NoSpendCeilingSet):
        SpendGuard()


def test_guard_aborts_when_projection_crosses_the_ceiling(monkeypatch, tmp_path):
    monkeypatch.setenv("ARGMAX_SPEND_CEILING_USD", "10")
    guard = SpendGuard(ledger=Ledger(path=tmp_path / "ledger.jsonl"))
    pricing = PricingSnapshot("snap", "2026-01-01", 1.0, 3.0)

    cheap = Projection(1_000, 500, 500, pricing)
    assert guard.check([cheap]) > 0

    expensive = Projection(10_000_000, 500, 500, pricing)
    with pytest.raises(SpendCeilingExceeded):
        guard.check([expensive])


def test_missing_capability_probe_blocks_the_phase():
    with pytest.raises(CapabilityMissing):
        assert_phase_supported("_no_such_model", ["logprobs"])


def test_confirmatory_without_a_prereg_tag_is_refused(monkeypatch):
    from argmax.sampling import runner

    monkeypatch.setattr(runner, "git_dirty", lambda: False)
    with pytest.raises(PreregTagMissing):
        runner.assert_confirmatory_preconditions("confirmatory", None)


def test_confirmatory_from_a_dirty_tree_is_refused(monkeypatch):
    from argmax.sampling import runner

    monkeypatch.setattr(runner, "git_dirty", lambda: True)
    with pytest.raises(DirtyTreeError):
        runner.assert_confirmatory_preconditions(
            "confirmatory", "argmax-prereg-p1-v1.0"
        )


def test_git_that_cannot_answer_is_a_refusal_not_a_clean_tree(monkeypatch, tmp_path):
    """No repository must not read as "no changes".

    `git status --porcelain` reports its failure on stderr and leaves stdout
    empty, so reading stdout alone made an unpacked archive, or a checkout
    without .git, indistinguishable from a clean tree. The dirty-tree refusal
    would then have passed on exactly the machines where provenance is least
    verifiable.
    """
    from argmax.sampling import runner

    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    monkeypatch.setattr(runner, "REPO_ROOT", not_a_repo)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))

    with pytest.raises(GitUnavailable):
        runner.git_dirty()
    with pytest.raises(GitUnavailable):
        runner.git_sha()
    with pytest.raises(GitUnavailable):
        runner.assert_confirmatory_preconditions(
            "confirmatory", "argmax-prereg-p1-v1.0"
        )


def test_exploratory_has_no_such_preconditions(monkeypatch):
    from argmax.sampling import runner

    monkeypatch.setattr(runner, "git_dirty", lambda: True)
    runner.assert_confirmatory_preconditions("exploratory", None)  # no raise


def test_a_phase_without_a_resolved_config_is_refused():
    """The loop exists now, and it still cannot be entered without values.

    It raised on Step 0 until the token cost was measured. The refusal that
    replaced it is narrower and does the same job: no config, no run, and
    `require` raises on any value still blocked before anything is spent.
    """
    from argmax.sampling.runner import run_phase

    with pytest.raises(NotImplementedError, match="resolved phase config"):
        run_phase("_template", "exploratory")


def test_the_template_phase_still_refuses_on_its_blocked_values():
    """configs/phases/_template.yaml keeps M blocked, so it cannot be run."""
    from argmax.config import load_phase, require

    cfg = load_phase("_template")
    with pytest.raises(StepZeroBlocked):
        require(cfg.get("M"), "M", cfg["_source"])
