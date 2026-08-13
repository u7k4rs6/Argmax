"""Instrumentation around the copied five-pass ladder.

The ladder itself is `scoring_verbatim.py`, copied byte for byte from
`self-consistency-backfire` at tag `backfire-prereg-v1.0`. See PROVENANCE.md.
Nothing here changes which answer that ladder returns or which pass it fires.
Everything here is what doc 4 s3.6 requires and the original did not record:

  - `extraction_pass`, which rung fired
  - `answer_span_chars`, where in `raw_text` the answer letter sits
  - `answer_span_tokens`, the same span mapped onto the stored logprob array
  - `extractor_version`, so old records stay interpretable when this changes

`answer_span_tokens` is the field that makes final-answer margin analysis
possible at all. Per-token logprobs without a span pointing at the answer
token are an undifferentiated array. It is also the reason the span is
re-derived rather than taken from the ladder: the published implementation
uses `findall`, which returns strings and throws the offsets away.

## How the span is re-derived without changing behaviour

The ladder decides. Instrumentation then replays the same regex over the same
slice, with the same "last match wins" rule, and reports where that match
landed. If the replay disagrees with the ladder about the letter, the span is
dropped rather than the answer: an absent span is a missing measurement, and a
changed answer is a changed experiment.

Extraction runs offline over stored raw text, so the ladder can be revised and
re-run at zero cost. It must never run inside the sampler.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from argmax.extract.scoring_verbatim import (
    _PASS1,
    _PASS2,
    _PASS3,
    _PASS4,
    ANSWER_CHOICES,
    extract_answer,
)

#: Identifies the ladder AND the instrumentation, separately. The left side is
#: the source of the passes; the right side is this wrapper. Bump the right
#: side when the instrumentation changes and the left side only when the
#: copied ladder is replaced, which is a different and much larger event.
EXTRACTOR_VERSION = "scb@backfire-prereg-v1.0:f3754c7+argmax-instr-1"

#: The copied ladder is hard-coded to A-D. A tier with a different option
#: count cannot be scored by it, and pretending otherwise silently
#: under-extracts on the options it has never heard of.
LADDER_N_OPTIONS = len(ANSWER_CHOICES)

#: The verbatim `extract_answer` returns 5 to mean "every regex pass failed,
#: the caller may now invoke the LLM scorer". Argmax never invokes it: doc 2
#: s5.5 puts extraction offline, and an extractor that can call an API is an
#: extractor that can spend credits during analysis. Doc 4 s3.6 wants null
#: when no pass fired, so 5 maps to None here.
_LADDER_EXHAUSTED = 5


@dataclass(frozen=True)
class Extraction:
    extracted_answer: str | None
    extraction_pass: int | None  # 1..4, or None when the ladder was exhausted
    answer_span_chars: tuple[int, int] | None
    extractor_version: str = EXTRACTOR_VERSION
    #: What the copied ladder actually returned, before the mapping above.
    #: Kept so that a pass distribution can be compared against the published
    #: one without reconstructing the mapping.
    verbatim_pass_number: int | None = None


def _last_span(
    pattern: re.Pattern[str], text: str, offset: int
) -> tuple[str, int, int] | None:
    """Last match of `pattern` in `text`, as (letter, start, end) in the original.

    Last, not first, because that is what `findall()[-1]` does in the copied
    ladder.
    """
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    m = matches[-1]
    return m.group(1).upper(), offset + m.start(1), offset + m.end(1)


def _last_line_offset(response: str) -> tuple[str, int] | None:
    """The last non-empty line, stripped, and where its stripped text starts.

    The copied ladder strips each line before matching, so an offset computed
    against the unstripped line would point at the wrong character whenever
    the line is indented.
    """
    cursor = 0
    found: tuple[str, int] | None = None
    for raw_line in response.splitlines(keepends=True):
        stripped = raw_line.strip()
        if stripped:
            found = (stripped, cursor + (len(raw_line) - len(raw_line.lstrip())))
        cursor += len(raw_line)
    return found


def _span_for_pass(response: str, pass_number: int) -> tuple[str, int, int] | None:
    """Replay the rung that fired, over exactly the slice it ran on."""
    if pass_number == 1:
        tail = response[-200:]
        return _last_span(_PASS1, tail, max(0, len(response) - 200))
    if pass_number == 2:
        return _last_span(_PASS2, response, 0)
    if pass_number == 3:
        line = _last_line_offset(response)
        if line is None:
            return None
        text, offset = line
        return _last_span(_PASS3, text, offset)
    if pass_number == 4:
        tail = response[-500:]
        return _last_span(_PASS4, tail, max(0, len(response) - 500))
    return None


def extract(raw_text: str, n_options: int) -> Extraction:
    """Run the copied ladder over stored raw text and record what it did.

    Only the visible answer region should be passed in for reasoning models:
    the hidden chain routinely names every option while thinking, and the
    permissive later passes would happily return one of those. Split first,
    then extract.
    """
    if n_options != LADDER_N_OPTIONS:
        raise ValueError(
            f"the copied ladder is hard-coded to {LADDER_N_OPTIONS} options "
            f"(A-D) and cannot score an {n_options}-option problem. Scoring it "
            "anyway would silently under-extract. See PROVENANCE.md; a wider "
            "ladder is a new extractor version, not a parameter."
        )

    result = extract_answer(raw_text)

    if result.answer is None:
        return Extraction(
            extracted_answer=None,
            extraction_pass=None,
            answer_span_chars=None,
            verbatim_pass_number=result.pass_number,
        )

    span = _span_for_pass(raw_text, result.pass_number)
    if span is not None and span[0] != result.answer:
        # The replay disagrees with the ladder. Report the answer the ladder
        # chose and no span at all: a wrong span pointing into the logprob
        # array is worse than an absent one, because the margin analysis it
        # feeds would look complete.
        span = None

    return Extraction(
        extracted_answer=result.answer,
        extraction_pass=(
            None if result.pass_number == _LADDER_EXHAUSTED else result.pass_number
        ),
        answer_span_chars=None if span is None else (span[1], span[2]),
        verbatim_pass_number=result.pass_number,
    )


def char_span_to_token_span(
    logprobs_raw: dict[str, Any] | None, char_span: tuple[int, int] | None
) -> tuple[int, int] | None:
    """Map a character span onto the stored logprob token array.

    Returns None when logprobs were not retained: an absent span is honest,
    an invented one is not.
    """
    if logprobs_raw is None or char_span is None:
        return None
    tokens = logprobs_raw.get("content") or logprobs_raw.get("tokens") or []
    if not tokens:
        return None

    lo_char, hi_char = char_span
    cursor = 0
    lo_tok = hi_tok = None
    for i, tok in enumerate(tokens):
        text = tok.get("token", "") if isinstance(tok, dict) else str(tok)
        start, end = cursor, cursor + len(text)
        if lo_tok is None and end > lo_char:
            lo_tok = i
        if start < hi_char:
            hi_tok = i + 1
        cursor = end
    if lo_tok is None or hi_tok is None:
        return None
    return (lo_tok, hi_tok)
