"""No published accuracy travels without its answer rate.

Doc 4 s9.1. The failure this guards against looks like a clean result: an
accuracy computed over a pool that lost a third of its samples to truncation
reads exactly like one computed over a complete pool. The rate is what tells
them apart, so it is published with the number, always, and the suite fails
when it is not.
"""

from __future__ import annotations

import json

import pytest

from argmax.persist.pairing import (
    AccuracyUnpaired,
    assert_paired,
    check_mapping,
    is_accuracy_key,
    is_rate_key,
    scan,
)


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- what counts as an accuracy ---------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["accuracy", "single_sample_accuracy", "vote_accuracy", "accuracy_under_strategy"],
)
def test_accuracy_names_are_recognised(name):
    assert is_accuracy_key(name)


@pytest.mark.parametrize("name", ["accurate_count", "n_answered", "ci_low"])
def test_other_names_are_not_accuracies(name):
    assert not is_accuracy_key(name)


@pytest.mark.parametrize("name", ["answer_rate", "answer_rate_by_n"])
def test_rate_names_are_recognised(name):
    assert is_rate_key(name)


# --- the rule ---------------------------------------------------------------


def test_an_accuracy_without_a_rate_fails():
    problems = check_mapping({"problem_id": "p", "accuracy": 0.42}, "row")
    assert problems and "no answer_rate" in problems[0]


def test_an_accuracy_with_a_rate_passes():
    assert check_mapping({"accuracy": 0.42, "answer_rate": 0.8}, "row") == []


def test_a_rate_of_one_is_not_an_omission():
    """Publishing 1.0000 is the rule, not an exception to it. "Uninteresting"
    is a judgement made after seeing a number the reader has not seen."""
    assert check_mapping({"accuracy": 0.42, "answer_rate": 1.0}, "row") == []


def test_a_record_with_no_accuracy_is_out_of_scope():
    assert check_mapping({"n_answered": 8, "answer_rate": 0.8}, "row") == []


def test_a_per_N_accuracy_needs_a_rate_at_every_N():
    """The voting pool at N=64 and at N=4 can differ, which is the point."""
    problems = check_mapping(
        {
            "vote_accuracy": {"1": 0.5, "4": 0.6, "16": 0.7},
            "answer_rate_by_n": {"1": 1.0, "4": 1.0},
        },
        "row",
    )
    assert problems and "N=[16]" in problems[0]


def test_a_per_N_accuracy_with_full_coverage_passes():
    assert (
        check_mapping(
            {
                "vote_accuracy": {"1": 0.5, "4": 0.6},
                "answer_rate_by_n": {"1": 1.0, "4": 0.9},
            },
            "row",
        )
        == []
    )


def test_a_scalar_rate_does_not_cover_a_per_N_accuracy():
    """One rate for the problem would paper over the per-N difference."""
    problems = check_mapping(
        {"vote_accuracy": {"1": 0.5, "4": 0.6}, "answer_rate": 0.8}, "row"
    )
    assert problems and "per N" in problems[0]


# --- artifacts on disk ------------------------------------------------------


def test_a_table_artifact_is_scanned(tmp_path):
    _write(tmp_path / "curves.json", [{"accuracy": 0.4}, {"accuracy": 0.5}])
    report = scan([tmp_path])
    assert report.n_in_scope == 1
    assert len(report.problems) == 2
    assert not report.clean


def test_a_parquet_table_is_scanned(tmp_path):
    polars = pytest.importorskip("polars")
    frame = polars.DataFrame({"accuracy": [0.4, 0.5], "answer_rate": [1.0, 0.8]})
    frame.write_parquet(tmp_path / "curves.parquet")
    assert scan([tmp_path]).clean

    bad = polars.DataFrame({"accuracy": [0.4]})
    bad.write_parquet(tmp_path / "bad.parquet")
    assert not scan([tmp_path]).clean


def test_a_figure_without_a_manifest_fails(tmp_path):
    """What a figure plots cannot be read from the image. Unscanned is not
    clean, for the same reason it is not in the leakage check."""
    (tmp_path / "curve.png").write_bytes(b"\x89PNG not really")
    report = scan([tmp_path])
    assert not report.clean
    assert "no sidecar manifest" in report.unscanned[0][1]


def test_a_figure_panel_plotting_accuracy_needs_a_rate(tmp_path):
    (tmp_path / "curve.png").write_bytes(b"\x89PNG not really")
    _write(
        tmp_path / "curve.png.manifest.json",
        {"panels": [{"accuracy": "vote_accuracy", "caption": "curve"}]},
    )
    report = scan([tmp_path])
    assert report.n_in_scope == 1
    assert report.problems


def test_a_figure_panel_with_its_rate_passes(tmp_path):
    (tmp_path / "curve.png").write_bytes(b"\x89PNG not really")
    _write(
        tmp_path / "curve.png.manifest.json",
        {"panels": [{"accuracy": "vote_accuracy", "answer_rate": "answer_rate_by_n"}]},
    )
    assert scan([tmp_path]).clean


def test_assert_paired_refuses_and_says_why(tmp_path):
    _write(tmp_path / "curves.json", [{"accuracy": 0.4}])
    with pytest.raises(AccuracyUnpaired, match="s4.1"):
        assert_paired(scan([tmp_path]))


def test_assert_paired_is_silent_when_everything_pairs(tmp_path):
    _write(tmp_path / "curves.json", [{"accuracy": 0.4, "answer_rate": 1.0}])
    assert_paired(scan([tmp_path]))


# --- the published tree -----------------------------------------------------


def test_the_published_artifacts_pair():
    """The check that matters, run over what this repo actually publishes."""
    from argmax.config import DATA
    from argmax.persist.pairing import iter_artifacts

    derived = DATA / "derived"
    # Emptiness is judged by the same rule the scanner uses, so that a file the
    # scanner ignores cannot make this test think there is something to check.
    if not derived.exists() or not any(iter_artifacts(derived)):
        pytest.skip("no derived artifacts yet (pre-Step 0)")
    assert_paired(scan([derived]))
