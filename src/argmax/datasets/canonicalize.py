"""Canonicalization: the step that makes votes comparable across runs.

Two properties matter more than they look:

  1. `problem_id` is a function of CONTENT, not of row order. Row order
     changes when a dataset is re-released.

  2. **Option order is frozen here and hashed.** Majority voting is over
     option letters. If option order shuffles between runs, the letters mean
     different things and the stored votes silently become incomparable.

Nothing in this module writes question or option text to disk. It reads the
gated source locally and emits ids, hashes, and labels only. See
files/03-security-and-access.md section 5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from argmax.keys import dataset_version_hash, problem_hash, problem_id

LETTERS = "ABCDEFGHIJ"


@dataclass(frozen=True)
class CanonicalProblem:
    """The tracked view of a problem. Deliberately contains no text.

    `_prompt_payload` carries the text needed to build a request. It is
    excluded from serialization and never persisted.
    """

    problem_id: str
    problem_hash: str
    benchmark: str
    tier: str
    n_options: int
    correct_option: str  # a letter, not the option's text
    domain: str | None = None
    subdomain: str | None = None

    _prompt_payload: dict[str, Any] = field(
        default_factory=dict, repr=False, compare=False
    )

    def tracked(self) -> dict[str, Any]:
        """What may be committed: ids, hashes, labels, answer letters."""
        return {
            "problem_id": self.problem_id,
            "problem_hash": self.problem_hash,
            "benchmark": self.benchmark,
            "tier": self.tier,
            "n_options": self.n_options,
            "correct_option": self.correct_option,
            "domain": self.domain,
            "subdomain": self.subdomain,
        }


def canonicalize(
    raw: dict[str, Any],
    *,
    benchmark: str,
    tier: str,
    question_key: str = "question",
    options_key: str = "options",
    correct_key: str = "correct",
) -> CanonicalProblem:
    """Freeze one problem into a comparable form.

    Option order is taken as given and frozen: it is NOT sorted, shuffled, or
    normalized here. Whatever order the canonicalizer sees becomes the
    permanent meaning of the letters, which is why the order goes into
    `problem_hash`.
    """
    question: str = raw[question_key]
    options: list[str] = list(raw[options_key])
    correct: Any = raw[correct_key]

    if len(options) > len(LETTERS):
        raise ValueError(f"{len(options)} options exceeds the letter alphabet")

    if isinstance(correct, int):
        correct_letter = LETTERS[correct]
    elif isinstance(correct, str) and correct in LETTERS[: len(options)]:
        correct_letter = correct
    elif isinstance(correct, str) and correct in options:
        correct_letter = LETTERS[options.index(correct)]
    else:
        raise ValueError(f"cannot resolve correct option from {correct!r}")

    # The hash covers the question AND the frozen option order.
    canonical = {"question": question, "options": options, "benchmark": benchmark}

    return CanonicalProblem(
        problem_id=problem_id(benchmark, question),
        problem_hash=problem_hash(canonical),
        benchmark=benchmark,
        tier=tier,
        n_options=len(options),
        correct_option=correct_letter,
        domain=raw.get("domain"),
        subdomain=raw.get("subdomain"),
        _prompt_payload={"question": question, "options": options},
    )


def assert_constant_n_options(problems: list[CanonicalProblem]) -> int:
    """`n_options` must be constant within a tier.

    The chance floor of a majority vote is a function of the option count, so
    a 4-choice hard tier compared against a 10-choice easy tier confounds
    difficulty with chance rate.
    """
    counts = {p.n_options for p in problems}
    if len(counts) != 1:
        raise ValueError(
            f"n_options is not constant within this tier: {sorted(counts)}. "
            "Comparing tiers with different option counts confounds difficulty "
            "with chance rate."
        )
    return counts.pop()


def version_hash(problems: list[CanonicalProblem]) -> str:
    """Hash over the canonicalized problem set. Stored in every manifest; a
    changed hash invalidates comparison."""
    return dataset_version_hash([p.problem_hash for p in problems])
