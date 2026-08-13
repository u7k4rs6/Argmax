"""5-pass answer extraction pipeline and LLM-based scorer (Pass 5).

Passes 1-4 are pure-regex; Pass 5 calls an LLM and is only invoked when
all regex passes fail. All API calls live in scripts/, not here.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pilot.sampling import APIClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex passes (locked §4.3)
# ---------------------------------------------------------------------------
_PASS1 = re.compile(r"(?i)answer[:\s]+([A-D])\b")
_PASS2 = re.compile(r"\\boxed\{([A-D])\}")
_PASS3 = re.compile(r"\b([A-D])\b")
_PASS4 = re.compile(r"\b([A-D])\b")

ANSWER_CHOICES = frozenset("ABCD")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Outcome of extract_answer."""

    answer: str | None  # one of A/B/C/D, or None if unparseable
    pass_number: int  # 1-5; 5 means LLM scorer; 6 means all failed


@dataclass(frozen=True, slots=True)
class ScoredSample:
    """A sample with its extracted answer and correctness flag."""

    full_response: str
    extracted_answer: str | None
    extraction_pass: int
    correct: bool
    ground_truth: str


# ---------------------------------------------------------------------------
# Extract answer (passes 1-4)
# ---------------------------------------------------------------------------
def extract_answer(response: str) -> ExtractionResult:
    """Apply passes 1-4 in order; return on first match.

    Returns (answer, pass_number) where answer is one of A/B/C/D or None.
    None means all regex passes failed; caller must invoke Pass 5 if needed.
    """
    # Pass 1: "Answer: X" in last 200 chars
    tail200 = response[-200:]
    matches = _PASS1.findall(tail200)
    if matches:
        return ExtractionResult(answer=matches[-1].upper(), pass_number=1)

    # Pass 2: \boxed{X} anywhere
    matches = _PASS2.findall(response)
    if matches:
        return ExtractionResult(answer=matches[-1].upper(), pass_number=2)

    # Pass 3: bare letter on last non-empty line
    lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
    if lines:
        matches = _PASS3.findall(lines[-1])
        if matches:
            return ExtractionResult(answer=matches[-1].upper(), pass_number=3)

    # Pass 4: bare letter in last 500 chars
    tail500 = response[-500:]
    matches = _PASS4.findall(tail500)
    if matches:
        return ExtractionResult(answer=matches[-1].upper(), pass_number=4)

    return ExtractionResult(answer=None, pass_number=5)


# ---------------------------------------------------------------------------
# Pass 5: LLM scorer
# ---------------------------------------------------------------------------
async def pass5_score(
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    ground_truth: str,
    full_response: str,
    api_client: APIClient,
) -> bool:
    """Invoke the LLM scorer; return True if the student's answer is correct."""
    from pilot.prompts import render_pass5_prompt

    prompt = render_pass5_prompt(
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
        ground_truth=ground_truth,
        full_response=full_response,
    )
    completion = await api_client.complete(
        prompt=prompt,
        temperature=0.0,
        seed_hex="00000000",
    )
    verdict = completion.text.strip().upper()
    if verdict == "CORRECT":
        return True
    if verdict in ("INCORRECT", "TRULY_UNPARSEABLE"):
        return False
    logger.warning("Pass-5 scorer returned unexpected verdict: %r", verdict)
    return False


# ---------------------------------------------------------------------------
# Score a single sample dict
# ---------------------------------------------------------------------------
async def score_sample(
    sample_dict: dict[str, Any],
    ground_truth: str,
    api_client: APIClient | None = None,
) -> ScoredSample:
    """Extract answer from a raw sample and determine correctness.

    Calls Pass 5 only when passes 1-4 fail and api_client is provided.
    Conservative scoring: unresolved → incorrect.
    """
    full_response: str = sample_dict.get("full_response", "")
    extraction = extract_answer(full_response)

    if extraction.answer is not None:
        return ScoredSample(
            full_response=full_response,
            extracted_answer=extraction.answer,
            extraction_pass=extraction.pass_number,
            correct=extraction.answer == ground_truth.upper(),
            ground_truth=ground_truth,
        )

    # Pass 5 path
    if api_client is not None:
        correct = await pass5_score(
            question_text=sample_dict.get("question_text", ""),
            option_a=sample_dict.get("option_a", ""),
            option_b=sample_dict.get("option_b", ""),
            option_c=sample_dict.get("option_c", ""),
            option_d=sample_dict.get("option_d", ""),
            ground_truth=ground_truth,
            full_response=full_response,
            api_client=api_client,
        )
        return ScoredSample(
            full_response=full_response,
            extracted_answer=None,
            extraction_pass=5,
            correct=correct,
            ground_truth=ground_truth,
        )

    # Conservative: all passes failed, no LLM fallback
    logger.debug("All passes failed for sample; scoring as incorrect.")
    return ScoredSample(
        full_response=full_response,
        extracted_answer=None,
        extraction_pass=6,
        correct=False,
        ground_truth=ground_truth,
    )
