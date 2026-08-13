"""The copied ladder stays byte-identical to what the published results used.

`src/argmax/extract/scoring_verbatim.py` is a copy of `pilot/scoring.py` from
`self-consistency-backfire` at tag `backfire-prereg-v1.0`. Comparability with
the published numbers is a claim about bytes, not about intent, so it is
asserted rather than described. See PROVENANCE.md.

If one of these fails, the fix is never to update the constant. It is to
restore the file, or to record a deliberate divergence in PROVENANCE.md and
bump the extractor version so old records stay interpretable.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VERBATIM = REPO / "src" / "argmax" / "extract" / "scoring_verbatim.py"
PROVENANCE = REPO / "PROVENANCE.md"

#: Recorded at copy time, 2026-08-13. Also in PROVENANCE.md.
EXPECTED_SHA256 = "f22e15c8cd1d6ed5a4b58fd5a289fcb688e3dd91564a7935d7203bf58c6bafec"
SOURCE_TAG = "backfire-prereg-v1.0"
SOURCE_TAG_SHA = "32ed32f6fc00c1b98124aeb3d3068fcec6e081d4"
SOURCE_HEAD_SHA = "a7f168e685b2eecf4793e2b635a6c801b6192d91"


def test_copied_ladder_is_unmodified():
    digest = hashlib.sha256(VERBATIM.read_bytes()).hexdigest()
    assert digest == EXPECTED_SHA256, (
        "the verbatim ladder changed. A formatter, a linter or an edit has "
        "broken the only property that made copying it worth doing."
    )


def test_provenance_records_both_shas_and_the_tag():
    """The tag and the source HEAD are both recorded, per the copy instruction."""
    text = PROVENANCE.read_text(encoding="utf-8")
    for token in (SOURCE_TAG, SOURCE_TAG_SHA, SOURCE_HEAD_SHA, EXPECTED_SHA256):
        assert token in text, f"PROVENANCE.md does not record {token}"


def test_the_published_quirks_are_still_there():
    """Passes 3 and 4 share a regex, and every pass takes the last match.

    Both look like defects and neither is one to fix here: correcting them
    changes which pass index fires and makes the pass distribution
    incomparable with the published one.
    """
    from argmax.extract import scoring_verbatim as sv

    assert sv._PASS3.pattern == sv._PASS4.pattern == r"\b([A-D])\b"
    assert sv._PASS1.pattern == r"(?i)answer[:\s]+([A-D])\b"
    assert sv._PASS2.pattern == r"\\boxed\{([A-D])\}"
    assert frozenset("ABCD") == sv.ANSWER_CHOICES


@pytest.mark.parametrize(
    ("text", "answer", "pass_number"),
    [
        ("The answer: C", "C", 1),
        (r"so \boxed{B} follows", "B", 2),
        ("reasoning\nD", "D", 3),
        # Pass 3 looks at the last non-empty line only, so a letter above it
        # falls through to pass 4, which reads the last 500 characters.
        ("Option A looks right.\nI conclude with prose only.", "A", 4),
        ("no letters here at all", None, 5),
    ],
)
def test_ladder_behaviour_is_pinned(text: str, answer: str | None, pass_number: int):
    """Pins each rung, so a change in behaviour fails here and not in a curve."""
    from argmax.extract.scoring_verbatim import extract_answer

    result = extract_answer(text)
    assert (result.answer, result.pass_number) == (answer, pass_number)


def test_argmax_never_reaches_the_api_calling_functions():
    """`pass5_score` and `score_sample` came along with the verbatim copy.

    One issues an API call, which an offline extractor must never do. The
    other scores an unresolved sample as `correct=False`, which is the
    coercion doc 4 s3.6 forbids and which is visibly present in the
    predecessor's stored data. Neither may be reachable from Argmax code.
    """
    forbidden = {"pass5_score", "score_sample"}
    src = REPO / "src" / "argmax"
    offenders: list[str] = []

    for path in src.rglob("*.py"):
        if path == VERBATIM:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden:
                offenders.append(f"{path.relative_to(src)}:{node.lineno} {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in forbidden:
                offenders.append(f"{path.relative_to(src)}:{node.lineno} {node.attr}")

    assert not offenders, (
        f"Argmax code references the unused verbatim functions: {offenders}"
    )
