"""Verdicts, and the thresholds they were decided against.

A verdict is stored WITH its threshold and the tag that fixed it. The
falsification suite then asserts both: the verdict, and the threshold value
itself. A regenerated result whose threshold was quietly edited must fail
loudly rather than pass against a moved line.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum

from argmax.schema import Split


class Outcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class Direction(StrEnum):
    greater = "greater"  # statistic must exceed the threshold
    less = "less"


@dataclass(frozen=True)
class Verdict:
    hypothesis_id: str
    statistic_name: str
    statistic: float
    threshold: float
    direction: Direction
    outcome: Outcome
    split: Split
    prereg_tag: str
    git_sha: str

    def to_dict(self) -> dict:
        return {
            k: str(v) if isinstance(v, StrEnum) else v for k, v in asdict(self).items()
        }


def decide(
    *,
    hypothesis_id: str,
    statistic_name: str,
    statistic: float,
    threshold: float,
    direction: Direction,
    split: Split | str,
    prereg_tag: str,
    git_sha: str,
) -> Verdict:
    """PASS/FAIL on confirmatory only.

    Exploratory data cannot produce a verdict: that is the whole point of the
    split. Calling this with the exploratory split is a bug, not a shortcut.
    """
    if Split(split) != Split.confirmatory:
        raise ValueError(
            f"verdicts are decided on the confirmatory split only; got split={split}"
        )
    if not prereg_tag:
        raise ValueError("a verdict without a prereg tag is not a verdict")

    passed = (
        statistic > threshold
        if direction == Direction.greater
        else statistic < threshold
    )
    return Verdict(
        hypothesis_id=hypothesis_id,
        statistic_name=statistic_name,
        statistic=statistic,
        threshold=threshold,
        direction=Direction(direction),
        outcome=Outcome.PASS if passed else Outcome.FAIL,
        split=Split(split),
        prereg_tag=prereg_tag,
        git_sha=git_sha,
    )
