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


# --- markdown, doc 4 s9.1.1 -------------------------------------------------
#
# The artifact scan above stayed green while a note published per-problem
# accuracies by length quintile with no answer rates. The rule was never
# scoped to notes, and the number that would have shown whether that table's
# shape was a truncation artifact was the missing one.

from pathlib import Path  # noqa: E402

from argmax.persist.pairing import (  # noqa: E402
    PairingReport,
    check_markdown,
    iter_markdown_tables,
)

REPO = Path(__file__).resolve().parents[1]


def _check(text, tmp_path):
    path = tmp_path / "note.md"
    path.write_text(text, encoding="utf-8")
    report = PairingReport()
    check_markdown(path, report)
    return report


def test_a_markdown_accuracy_column_without_a_rate_fails(tmp_path):
    report = _check(
        "| bin | accuracy |\n|---|---|\n| a | 0.4441 |\n| b | 0.2218 |\n", tmp_path
    )
    assert report.problems and "no answer_rate" in report.problems[0]


def test_a_markdown_accuracy_column_with_a_rate_passes(tmp_path):
    report = _check(
        "| bin | accuracy | answer_rate |\n|---|---|---|\n"
        "| a | 0.4441 | 0.9819 |\n| b | 0.2218 | 1.0000 |\n",
        tmp_path,
    )
    assert not report.problems
    assert report.n_in_scope == 1


def test_a_rate_elsewhere_in_the_document_is_not_a_match(tmp_path):
    """The reader must not have to perform a join."""
    report = _check(
        "The answer rate over these problems is 0.9943.\n\n"
        "| bin | accuracy |\n|---|---|\n| a | 0.4441 |\n",
        tmp_path,
    )
    assert report.problems


def test_a_bin_label_column_is_not_an_accuracy(tmp_path):
    """`accuracy bin` with range cells is a stratifier, not a reported value.

    The whole cell must parse. Reading only its first token would score
    "0.000 to 0.125" as the accuracy 0.0.
    """
    report = _check(
        "| accuracy bin | problems |\n|---|---|\n"
        "| 0.000 to 0.125 | 42 |\n| 0.125 to 0.250 | 19 |\n",
        tmp_path,
    )
    assert not report.problems
    assert report.n_in_scope == 0


def test_percent_cells_are_read_as_accuracies(tmp_path):
    report = _check(
        "| bin | accuracy |\n|---|---|\n| a | 44.4% |\n| b | 22.2% |\n", tmp_path
    )
    assert report.problems


def test_tables_are_found_with_their_line_numbers(tmp_path):
    text = "intro\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\ntail\n"
    tables = list(iter_markdown_tables(text))
    assert len(tables) == 1
    line_no, header, body = tables[0]
    assert line_no == 3
    assert header == ["a", "b"]
    assert body == [["1", "2"]]


def test_every_markdown_file_in_the_repo_pairs():
    """The enforcement, over notes, files and the repository root."""
    report = PairingReport()
    # A WALK, not a list of remembered directories. notes/ was missed once and
    # paper/ twice under the old allow-list default; see argmax.repo.
    from argmax.repo import iter_documents

    paths = list(iter_documents(REPO))
    for path in paths:
        check_markdown(path, report)
    assert len(paths) >= 15, "the markdown scan is covering almost nothing"
    assert not report.problems, "\n".join(report.problems)


# --- the scan default itself ------------------------------------------------
#
# notes/ was missed once, paper/ twice. Three misses, one cause: an allow-list
# of remembered directories. These tests assert the inverted default holds.


def test_the_scan_walks_the_repo_rather_than_a_list_of_directories():
    from argmax.repo import iter_documents

    found = {p.relative_to(REPO).parts[0] for p in iter_documents(REPO)}
    # every directory that has ever held an authored document
    for expected in ("notes", "files", "paper"):
        assert expected in found, f"{expected}/ is not being scanned"


def test_a_new_directory_of_documents_is_scanned_without_being_registered(tmp_path):
    """The property the allow-list did not have."""
    from argmax.repo import iter_documents

    novel = tmp_path / "somewhere_nobody_listed"
    novel.mkdir()
    (novel / "note.md").write_text("# hi", encoding="utf-8")
    assert [p.name for p in iter_documents(tmp_path)] == ["note.md"]


def test_every_exclusion_carries_a_reason():
    """An exclusion without a stated reason is an allow-list in disguise."""
    from argmax.repo import EXCLUSIONS

    assert EXCLUSIONS
    for fragment, reason in EXCLUSIONS:
        assert fragment and reason, f"exclusion {fragment!r} has no reason"
        assert len(reason) > 15, f"exclusion {fragment!r} has a token reason"


def test_gitignored_sample_stores_stay_excluded(tmp_path):
    """The sample stores are excluded on purpose, not by omission."""
    from argmax.repo import is_excluded

    for name in ("data/raw", "data/derived", "runs", ".venv"):
        d = tmp_path / name
        d.mkdir(parents=True)
        f = d / "x.md"
        f.write_text("x", encoding="utf-8")
        assert is_excluded(f, tmp_path), f"{name}/ should be excluded"


def test_datasets_md_is_not_excluded_with_the_store(tmp_path):
    """The regression this exclusion list was rewritten for.

    `data/` was excluded wholesale with the reason "never contains authored
    prose". `DATASETS.md` is authored prose, it carries the licence notes
    doc 3 s7 depends on, and the glob list this walk replaced scanned it.
    """
    from argmax.repo import is_excluded

    (tmp_path / "data").mkdir()
    doc = tmp_path / "data" / "DATASETS.md"
    doc.write_text("licence notes", encoding="utf-8")
    assert is_excluded(doc, tmp_path) is None
