"""Locked prompt templates for the compute elasticity pilot.

Templates are frozen after Phase 2. Hash mismatch raises RuntimeError
to guard against accidental edits.
"""

from __future__ import annotations

import hashlib

# ---------------------------------------------------------------------------
# Main inference prompt (locked §4.1)
# ---------------------------------------------------------------------------
MAIN_PROMPT_TEMPLATE: str = (
    "You are a helpful AI assistant solving a graduate-level multiple-choice question.\n"
    "\n"
    "Question: {question_text}\n"
    "\n"
    "Options:\n"
    "A) {option_a}\n"
    "B) {option_b}\n"
    "C) {option_c}\n"
    "D) {option_d}\n"
    "\n"
    "Think through this step by step, then provide your final answer in the format\n"
    '"Answer: X" where X is one of A, B, C, or D.\n'
)

# ---------------------------------------------------------------------------
# Pass-5 LLM scorer prompt (locked §4.2)
# ---------------------------------------------------------------------------
PASS5_SCORER_TEMPLATE: str = (
    "You are evaluating a student's answer to a multiple-choice question.\n"
    "\n"
    "Question: {question_text}\n"
    "\n"
    "Options:\n"
    "A) {option_a}\n"
    "B) {option_b}\n"
    "C) {option_c}\n"
    "D) {option_d}\n"
    "\n"
    "Correct answer: {ground_truth}\n"
    "\n"
    "Student's response:\n"
    "{full_response}\n"
    "\n"
    "Did the student arrive at the correct answer? Respond with exactly one word:\n"
    '- "CORRECT" if the student\'s final reasoning concludes with the correct answer\n'
    '- "INCORRECT" if the student\'s final reasoning concludes with a wrong answer\n'
    '- "TRULY_UNPARSEABLE" if no final answer can be determined from the response\n'
)

# ---------------------------------------------------------------------------
# Hashes — computed once; verified on every import after Phase 2 lock.
# ---------------------------------------------------------------------------
PROMPT_TEMPLATE_HASH: str = hashlib.sha256(
    MAIN_PROMPT_TEMPLATE.encode("utf-8")
).hexdigest()

PASS5_SCORER_HASH: str = hashlib.sha256(
    PASS5_SCORER_TEMPLATE.encode("utf-8")
).hexdigest()

# Locked expected hashes (set at Phase 2 pre-registration).
_LOCKED_PROMPT_HASH: str = (
    "e3544f731c3b30d49f373585e192da39347a272fe68fd9d309e8aafc763b73c1"
)
_LOCKED_SCORER_HASH: str = (
    "0ca0b0f97745fcb58756e9b0a42b4c2e2ff298eb92c6e3e35096567c34e0f303"
)

if _LOCKED_PROMPT_HASH and PROMPT_TEMPLATE_HASH != _LOCKED_PROMPT_HASH:
    raise RuntimeError(
        f"Main prompt template has been modified. "
        f"Expected hash {_LOCKED_PROMPT_HASH!r}, got {PROMPT_TEMPLATE_HASH!r}. "
        "Unlock requires re-tagging preregistration.md."
    )

if _LOCKED_SCORER_HASH and PASS5_SCORER_HASH != _LOCKED_SCORER_HASH:
    raise RuntimeError(
        f"Pass-5 scorer template has been modified. "
        f"Expected hash {_LOCKED_SCORER_HASH!r}, got {PASS5_SCORER_HASH!r}. "
        "Unlock requires re-tagging preregistration.md."
    )


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------
def render_prompt(
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
) -> str:
    """Render the locked main inference prompt."""
    return MAIN_PROMPT_TEMPLATE.format(
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
    )


def render_pass5_prompt(
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    ground_truth: str,
    full_response: str,
) -> str:
    """Render the locked Pass-5 LLM scorer prompt."""
    return PASS5_SCORER_TEMPLATE.format(
        question_text=question_text,
        option_a=option_a,
        option_b=option_b,
        option_c=option_c,
        option_d=option_d,
        ground_truth=ground_truth,
        full_response=full_response,
    )
