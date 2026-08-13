"""Failure modes that must be loud.

Each of these corresponds to a way the predecessor lost work. They are
exceptions rather than warnings because every one of them is cheaper to hit at
startup than at analysis time, after the credits are spent.
"""


class ArgmaxError(RuntimeError):
    """Base for every Argmax failure."""


class StepZeroBlocked(ArgmaxError):
    """A value required to run is still `[BLOCKED: Step 0]`.

    Raised instead of substituting a default. Guessing the token cost is
    precisely how the predecessor acquired a pooled-versus-confirmatory
    mismatch that cost four revision rounds.
    """

    def __init__(self, field: str, source: str, unblocked_by: str = "") -> None:
        msg = f"{field} is [BLOCKED: Step 0] in {source}"
        if unblocked_by:
            msg += f"; unblocked by: {unblocked_by}"
        super().__init__(msg)
        self.field = field
        self.source = source


class SpendCeilingExceeded(ArgmaxError):
    """Projected + realized spend would cross ARGMAX_SPEND_CEILING_USD."""


class NoSpendCeilingSet(ArgmaxError):
    """ARGMAX_SPEND_CEILING_USD is unset.

    There is no default, because a default becomes the real limit.
    """


class CapabilityMissing(ArgmaxError):
    """A phase requires an instrumentation field the model does not return.

    This is the direct fix for the predecessor's permanent loss of
    final-answer margin analysis: that hole was discovered at analysis time,
    after the samples were paid for.
    """


class DirtyTreeError(ArgmaxError):
    """Confirmatory work attempted from a dirty working tree."""


class GitUnavailable(ArgmaxError):
    """git could not answer whether the tree is clean, or what commit this is.

    Raised rather than defaulting to "clean" and an empty SHA. A refusal that
    silently stops refusing when git is missing, or when the pipeline is run
    from an unpacked archive that was never a repository, is not a refusal;
    and a manifest recording `git_sha: ""` claims provenance it does not have.
    """


class PreregTagMissing(ArgmaxError):
    """Confirmatory work attempted without a prereg tag in the manifest."""


class MonteCarloNotConverged(ArgmaxError):
    """More subsample draws are needed before the answer means anything.

    Raised instead of returning an estimate whose Monte Carlo noise is large
    against the effect it is meant to resolve. The number of draws is free to
    raise, so a noisy estimate here is a choice, and it is one nobody should
    make silently.
    """


class SchemaViolation(ArgmaxError):
    """A record is missing a required field or has the wrong type."""
