"""Separating hidden reasoning from the visible answer.

Getting this split right is the whole reason Step 0 exists. The phase 14b
probe died on truncation before a visible answer, and the token budget needed
to avoid that is the number the cost model turns on.

`split_ok` is false when the opening delimiter appears with no close, which is
exactly the truncated-mid-thought case. That is a measurement, not an error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from argmax.sampling.probe import REASONING_DELIMITERS
from argmax.schema import SplitMethod


@dataclass(frozen=True)
class ReasoningSplit:
    split_method: SplitMethod
    split_ok: bool
    reasoning_text: str | None
    answer_text: str | None


def split_reasoning(
    body_message: dict[str, Any],
    raw_text: str,
    *,
    delivery: str,
    delimiter: list[str] | None = None,
) -> ReasoningSplit:
    """Split according to what the capability probe recorded for this model.

    `delivery` comes from the probe rather than from a guess, so a model whose
    reasoning arrives in a dedicated field is never parsed for delimiters and
    vice versa.
    """
    if delivery == "api_field":
        reasoning = body_message.get("reasoning") or body_message.get(
            "reasoning_content"
        )
        return ReasoningSplit(
            split_method=SplitMethod.api_field,
            split_ok=reasoning is not None,
            reasoning_text=reasoning,
            answer_text=raw_text,
        )

    if delivery == "delimiter":
        pairs = [tuple(delimiter)] if delimiter else REASONING_DELIMITERS
        for open_d, close_d in pairs:
            if open_d not in raw_text:
                continue
            head, _, rest = raw_text.partition(open_d)
            if close_d not in rest:
                # Opened and never closed: truncated mid-thought. Everything
                # after the opener is reasoning and there is no visible answer.
                return ReasoningSplit(
                    split_method=SplitMethod.delimiter,
                    split_ok=False,
                    reasoning_text=rest,
                    answer_text=None,
                )
            reasoning, _, tail = rest.partition(close_d)
            return ReasoningSplit(
                split_method=SplitMethod.delimiter,
                split_ok=True,
                reasoning_text=reasoning,
                answer_text=(head + tail),
            )
        # The probe said delimiter, but this completion has none. Not an
        # error: a short completion may simply not have opened one.
        return ReasoningSplit(
            split_method=SplitMethod.delimiter,
            split_ok=True,
            reasoning_text=None,
            answer_text=raw_text,
        )

    return ReasoningSplit(
        split_method=SplitMethod.none,
        split_ok=True,
        reasoning_text=None,
        answer_text=raw_text,
    )
