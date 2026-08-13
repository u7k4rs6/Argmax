"""The pre-release leakage check.

The scenario under test is the one that actually happens: nothing in the repo
ever wrote question text, and the raw store contains it anyway, because a
model restated the question before answering it.
"""

from __future__ import annotations

import gzip
import json

import pytest

from argmax.persist.leakage import (
    GPQA_CANARY,
    LeakageDetected,
    assert_canary_present,
    assert_no_leakage,
    fingerprints,
    scan,
    tokenize,
)

QUESTION = (
    "A thin uniform rod of mass m and length L rotates about an axis through "
    "one end perpendicular to the rod. What is its moment of inertia about "
    "that axis?"
)

INNOCENT = (
    "The model considered several approaches and settled on the second one "
    "after checking the units."
)


def _record(text: str) -> str:
    return json.dumps({"raw_text": text, "finish_reason": "stop"})


def test_a_response_that_restates_the_question_is_caught(tmp_path):
    """The prompt-echo case: doc 3 s5.1's reason the check exists."""
    marks = fingerprints([QUESTION])
    store = tmp_path / "raw"
    store.mkdir()
    echo = f"Restating the problem: {QUESTION} I will now solve it. Answer: B"
    (store / "p1.jsonl").write_text(_record(echo), encoding="utf-8")

    report = scan([store], marks)
    assert not report.clean
    assert report.hits[0].line == 1


def test_gzipped_raw_files_are_scanned_not_skipped(tmp_path):
    """The raw store is JSONL gzipped at rest (doc 4 s7)."""
    marks = fingerprints([QUESTION])
    path = tmp_path / "p1.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        fh.write(_record(QUESTION))

    report = scan([path], marks)
    assert report.hits, "a gzipped raw file must be read, not passed over"


def test_ordinary_completions_do_not_trip_it(tmp_path):
    marks = fingerprints([QUESTION])
    path = tmp_path / "p2.jsonl"
    path.write_text(_record(INNOCENT), encoding="utf-8")

    report = scan([path], marks)
    assert report.clean


def test_reformatted_echo_still_trips_it(tmp_path):
    """Casing, punctuation and JSON escaping differ between the dataset file
    and a model restating it. None of that makes it less of an echo.

    The line breaks matter: JSON stores each one as the two characters `\\n`,
    whose `n` tokenizes as a word wedged between the real ones unless the
    escapes are stripped first.
    """
    marks = fingerprints([QUESTION])
    mangled = QUESTION.upper().replace(",", "").replace(" ", "\n  ")
    path = tmp_path / "p3.jsonl"
    path.write_text(json.dumps({"raw_text": mangled}), encoding="utf-8")

    report = scan([path], marks)
    assert report.hits


def test_an_unreadable_format_is_reported_not_assumed_clean(tmp_path):
    """Absence is data. "No hits" and "no evidence" are different claims."""
    marks = fingerprints([QUESTION])
    (tmp_path / "table.parquet").write_bytes(b"PAR1\x00\x01")

    report = scan([tmp_path], marks)
    assert not report.hits
    assert not report.clean, "a file that could not be scanned must fail the check"
    assert "not a text format" in report.unscanned[0][1]
    with pytest.raises(LeakageDetected):
        assert_no_leakage(report)


def test_the_report_never_contains_the_leaked_text(tmp_path):
    """A leakage report that quotes the leak is the leak."""
    marks = fingerprints([QUESTION])
    path = tmp_path / "p4.jsonl"
    path.write_text(_record(QUESTION), encoding="utf-8")
    report = scan([path], marks)

    rendered = report.summary()
    try:
        assert_no_leakage(report)
    except LeakageDetected as exc:
        rendered += str(exc)

    words = tokenize(QUESTION)
    for i in range(len(words) - 4):
        assert " ".join(words[i : i + 5]) not in tokenize_join(rendered)


def tokenize_join(text: str) -> str:
    return " ".join(tokenize(text))


def test_fingerprints_are_hashes_of_the_questions(tmp_path):
    """What the check holds in memory is hashes; the text is consumed."""
    marks = fingerprints([QUESTION])
    assert marks
    assert all(len(m) == 64 and m.isalnum() for m in marks)
    assert QUESTION[:40].lower() not in " ".join(marks)


def test_short_questions_produce_no_fingerprints():
    """A question shorter than the window yields nothing, which is why the
    CLI refuses to run against an empty fingerprint set."""
    assert fingerprints(["too short"], 10) == set()


def test_release_readme_must_carry_the_canary(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Argmax raw sample store\n", encoding="utf-8")
    with pytest.raises(LeakageDetected, match="canary"):
        assert_canary_present(readme)

    readme.write_text(f"# Argmax raw store\n\n{GPQA_CANARY}\n", encoding="utf-8")
    assert_canary_present(readme)


def test_missing_release_readme_is_a_refusal(tmp_path):
    with pytest.raises(LeakageDetected):
        assert_canary_present(tmp_path / "nope.md")
