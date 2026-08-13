"""Five-pass answer extraction.

    !!! PORT REQUIRED BEFORE ANY ANALYSIS !!!

    Doc 2 s5.5 specifies that the ladder is COPIED FROM THE PUBLISHED
    `self-consistency-backfire` REPO VERBATIM, then instrumented. That repo is
    not present in this checkout, so the pass bodies below are a structural
    stand-in with the same ladder shape, NOT the verbatim passes.

    Comparability with the published results depends on these being the same
    regexes in the same order. Replace each `_pass_*` body with the published
    implementation before running analysis that is meant to be compared, and
    bump EXTRACTOR_VERSION when you do.

What IS final here is the instrumentation contract: every extraction records
which pass fired and the span it matched. `answer_span_chars` and
`answer_span_tokens` are what make final-answer margin analysis possible at
all: per-token logprobs without a span pointing at the answer token are an
undifferentiated array.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: Bump whenever a pass body changes. Old records must stay interpretable, so
#: the version travels with every extraction rather than being assumed.
EXTRACTOR_VERSION = "0.0.0-structural-stand-in"

LETTERS = "ABCDEFGHIJ"


@dataclass(frozen=True)
class Extraction:
    extracted_answer: str | None
    extraction_pass: int | None  # 1..5, or None when every pass failed
    answer_span_chars: tuple[int, int] | None
    extractor_version: str = EXTRACTOR_VERSION


def _hit(
    match: re.Match[str] | None, group: int = 1
) -> tuple[str, tuple[int, int]] | None:
    if match is None:
        return None
    return match.group(group).upper(), (match.start(group), match.end(group))


# --- the ladder -------------------------------------------------------------
# Ordered most explicit to least. Later passes are progressively more
# permissive, which is why the pass index is recorded: a corpus that resolves
# mostly on pass 5 is a different measurement from one that resolves on pass 1,
# and the difference is invisible in the answer alone.

_P1 = re.compile(r"(?i)\banswer\s*[:\-]?\s*\(?([A-J])\)?\b")
_P2 = re.compile(
    r"(?i)\b(?:the\s+)?(?:correct\s+)?(?:option|choice)\s*(?:is)?\s*\(?([A-J])\)?\b"
)
_P3 = re.compile(r"\\boxed\{\s*\(?([A-J])\)?\s*\}")
_P4 = re.compile(r"(?m)^\s*\(?([A-J])\)?\s*[.)]?\s*$")
_P5 = re.compile(r"\b([A-J])\b")


def _pass_1(text: str):
    """Explicit 'Answer: X'."""
    return _hit(_P1.search(text))


def _pass_2(text: str):
    """'The correct option is X'."""
    return _hit(_P2.search(text))


def _pass_3(text: str):
    r"""LaTeX \boxed{X}."""
    return _hit(_P3.search(text))


def _pass_4(text: str):
    """A bare letter alone on the final line."""
    matches = list(_P4.finditer(text))
    return _hit(matches[-1]) if matches else None


def _pass_5(text: str):
    """Last standalone letter anywhere. The permissive fallback."""
    matches = list(_P5.finditer(text))
    return _hit(matches[-1]) if matches else None


_LADDER = (_pass_1, _pass_2, _pass_3, _pass_4, _pass_5)


def extract(raw_text: str, n_options: int) -> Extraction:
    """Run the ladder over stored raw text.

    Only the visible answer region should be passed in for reasoning models:
    the hidden chain routinely names every option while thinking, and pass 5
    would happily return one of those. Split first, then extract.
    """
    valid = set(LETTERS[:n_options])
    for index, pass_fn in enumerate(_LADDER, start=1):
        hit = pass_fn(raw_text)
        if hit is None:
            continue
        letter, span = hit
        if letter not in valid:
            continue  # a letter outside the option range is not an answer
        return Extraction(
            extracted_answer=letter,
            extraction_pass=index,
            answer_span_chars=span,
        )
    return Extraction(
        extracted_answer=None, extraction_pass=None, answer_span_chars=None
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
