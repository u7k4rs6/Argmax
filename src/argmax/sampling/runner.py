"""Phase runner: the thing that actually spends money.

Order of operations, all of it before the first request:

  1. resolve the phase config, raising StepZeroBlocked on any blocked value
  2. load each model's capability probe and refuse if a required field is
     missing
  3. construct the spend guard (raises if no ceiling is set)
  4. project cost from the probe's measured tokens, add realized spend from
     the ledger, abort if the ceiling would be crossed
  5. refuse a confirmatory run from a dirty tree or without a prereg tag

Resume is "run the same command again": the sampler consults the index of
existing sample keys and skips what is already stored.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from argmax.config import REPO_ROOT
from argmax.errors import DirtyTreeError, GitUnavailable, PreregTagMissing
from argmax.schema import Split


def _git(*args: str) -> str:
    """Run git against THIS repo and refuse to interpret a failure as an answer.

    Two failures were possible with `check=False` and a bare `.stdout.strip()`:

      1. No git, or no repository (an unpacked release archive, a container
         without the .git directory). `git status --porcelain` writes its
         error to stderr and leaves stdout empty, and an empty stdout reads as
         "no changes", so the dirty-tree refusal quietly passed.
      2. The command inherited the process working directory, so a phase
         launched from elsewhere reported some other repository's cleanliness.

    Both are fixed by pinning cwd to REPO_ROOT and raising on a non-zero exit.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # git is not installed, or REPO_ROOT is gone
        raise GitUnavailable(f"could not run git in {REPO_ROOT}: {exc}") from None
    if proc.returncode != 0:
        raise GitUnavailable(
            f"`git {' '.join(args)}` failed in {REPO_ROOT} "
            f"(exit {proc.returncode}): {proc.stderr.strip() or 'no stderr'}. "
            "Provenance cannot be recorded and cleanliness cannot be checked, "
            "so this is a refusal rather than a default."
        )
    return proc.stdout.strip()


def git_sha() -> str:
    """The commit every manifest records. Never an empty string."""
    return _git("rev-parse", "HEAD")


def git_dirty() -> bool:
    return bool(_git("status", "--porcelain"))


def assert_confirmatory_preconditions(
    split: Split | str, prereg_tag: str | None
) -> None:
    """Confirmatory work refuses to run from a dirty tree or without a tag.

    Both refusals are in code rather than in a checklist because a checklist
    is what the predecessor had.
    """
    if Split(split) != Split.confirmatory:
        return
    if git_dirty():
        raise DirtyTreeError(
            "confirmatory run from a dirty working tree; commit or stash first"
        )
    if not prereg_tag:
        raise PreregTagMissing(
            "confirmatory run without a prereg_tag. Cut an "
            "argmax-prereg-<phase>-v<major>.<minor> tag and record it in "
            "PREREGISTRATION.md first."
        )


@dataclass
class PhasePlan:
    """What a phase would do, computed before anything is spent."""

    phase_id: str
    split: Split
    model_slugs: list[str]
    benchmarks: list[str]
    n_problems: int
    M: int
    n_requests: int
    projected_usd: float
    headroom_usd: float


def run_phase(phase_id: str, split: str, cfg=None):
    """Draw the phase's samples.

    Was blocked on Step 0 until the reasoning-model token cost was measured.
    It still refuses any phase whose values are unresolved: `cfg` carries them
    and `argmax.config.require` raises on a `[BLOCKED: Step 0]` value before
    anything is spent.

    The loop itself is in `argmax.sampling.phase`, imported lazily so that this
    module stays importable on a host with no network client.

    Historical note, kept because it is the reason the refusal existed: this
    function raised until Step 0 measured p95 output tokens, cost per sample
    and the total envelope, so that it could not be run by accident against
    guessed values. Those measurements are in `notes/phase14b_token_audit.md`
    and `notes/max_tokens_estimate.md`. `max_tokens` for a REASONING model is
    still unresolved and no phase config sets one.
    """
    if cfg is None:
        raise NotImplementedError(
            "run_phase needs a resolved phase config. scripts/sample.py loads "
            "it and raises StepZeroBlocked on any value still unresolved."
        )
    from argmax.sampling.phase import run_phase as _run

    return _run(phase_id, split, cfg)
