"""GPQA Diamond, canonicalized to reproduce the predecessor's prompts exactly.

Reads a LOCAL csv. Nothing here touches the network: doc 3 section 5.1 says
canonicalization reads the gated source locally and writes only hashes and ids
into anything tracked, and `tests/test_no_network.py` enforces the import rule.
Use `scripts/fetch_gpqa.py` to put the file on disk.

## Why the option order is reproduced rather than chosen

Doc 2 section 7.1 makes a comparison legal only when the conditions match. The
predecessor built each problem's options with

    rng = random.Random(idx); options = [correct] + incorrect; rng.shuffle(options)

where `idx` is the csv row index, and its prompt template hashes to
`e3544f73...`, recorded in all 25,730 of its stored samples. Reproducing both
means Argmax sends **byte-identical prompts** with the answer under the same
letter, so a per-problem comparison is available and not only an aggregate one.

Any other shuffle would still be a valid experiment and would forfeit that.

## What leaves this module

`CanonicalProblem.tracked()` carries ids, hashes, labels and the answer letter.
The question and option text stay in `_prompt_payload`, which is excluded from
serialization and never persisted. The canary string is carried through so a
release can declare it.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

from argmax.datasets.canonicalize import CanonicalProblem, canonicalize
from argmax.datasets.prompts_verbatim import MAIN_PROMPT_TEMPLATE

#: Where `scripts/fetch_gpqa.py` writes the gated source. Under `data/`, which
#: is ignored wholesale, so the questions cannot reach git.
DEFAULT_CSV = Path("data/gpqa_diamond.csv")

#: The predecessor's own hash of the template, present in every stored record.
#: A mismatch means the prompts are not the ones the published numbers used.
EXPECTED_PROMPT_HASH = (
    "e3544f731c3b30d49f373585e192da39347a272fe68fd9d309e8aafc763b73c1"
)


def load_rows(path: Path = DEFAULT_CSV) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run `python scripts/fetch_gpqa.py` first; the "
            "dataset is gated and needs HF_TOKEN in .env."
        )
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def shuffled_options(row: dict[str, str], idx: int) -> tuple[list[str], str]:
    """The predecessor's ordering, reproduced exactly.

    Returns the four option texts in order and the correct letter.
    """
    correct = row["Correct Answer"].strip()
    options = [correct] + [row[f"Incorrect Answer {i}"].strip() for i in (1, 2, 3)]
    random.Random(idx).shuffle(options)
    return options, "ABCD"[options.index(correct)]


def build_prompt(question: str, options: list[str]) -> str:
    return MAIN_PROMPT_TEMPLATE.format(
        question_text=question.strip(),
        option_a=options[0],
        option_b=options[1],
        option_c=options[2],
        option_d=options[3],
    )


def load_problems(path: Path = DEFAULT_CSV) -> list[CanonicalProblem]:
    """Every Diamond problem, canonicalized with its prompt attached."""
    problems = []
    for idx, row in enumerate(load_rows(path)):
        options, correct_letter = shuffled_options(row, idx)
        question = row["Question"].strip()
        problem = canonicalize(
            {
                "question": question,
                "options": options,
                "correct": correct_letter,
                "domain": row.get("High-level domain"),
                "subdomain": row.get("Subdomain"),
            },
            benchmark="gpqa_diamond",
            tier="diamond",
        )
        object.__setattr__(
            problem,
            "_prompt_payload",
            {
                "question": question,
                "options": options,
                "prompt": build_prompt(question, options),
                "row_index": idx,
                "record_id": row.get("Record ID", ""),
                "canary": row.get("Canary String", ""),
            },
        )
        problems.append(problem)
    return problems


def prompt_for(problem: CanonicalProblem) -> str:
    return problem._prompt_payload["prompt"]
