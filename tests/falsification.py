"""The falsification suite.

Run by `make verify`. It asserts stored verdicts against pre-registered
thresholds, AND asserts the threshold values themselves. A regenerated result
whose threshold was quietly edited must fail loudly rather than pass against a
moved line.

A test here may fail BY DESIGN when a hypothesis is genuinely falsified. Such
tests are marked with the hypothesis id and a comment stating that red is the
expected state and why. The predecessor's `test_h3` is the model. Do not
"fix" one of those without reading its comment.

Pre-Step 0 status: there are no verdicts yet, because there are no
pre-registered hypotheses yet. The structural tests below run now; the
verdict tests skip until PREREGISTRATION.md has rows, and the skip is loud so
that an empty suite is never mistaken for a passing one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PREREG = REPO / "PREREGISTRATION.md"

#: Doc 2 s8.3 fixes the shape, `argmax-prereg-<phase>-v<major>.<minor>`, and
#: constrains neither the case nor the punctuation of the phase name. This
#: pattern has been widened twice for being stricter than the doc it enforces:
#: once for `threadA`, once for a hyphenated phase name. Hyphens belong,
#: because this repo's own phase ids carry them (`margin-v1`). The shape is
#: unchanged and still anchored, so the version suffix remains unambiguous.
TAG_FORMAT = re.compile(r"^argmax-prereg-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*-v\d+\.\d+$")


def _table_rows(section: str) -> list[list[str]]:
    """Parse one markdown table out of PREREGISTRATION.md."""
    text = PREREG.read_text(encoding="utf-8")
    body = text.split(f"## {section}", 1)
    if len(body) < 2:
        return []
    rows = []
    for line in body[1].splitlines():
        line = line.strip()
        if line.startswith("## "):
            break
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0].lower() in {"tag", "id", "claim id", "threshold name"}:
            continue
        if cells and cells[0].startswith("_("):
            continue  # the placeholder row
        rows.append(cells)
    return rows


# --- structural: these run before any data exists ---------------------------


def test_preregistration_file_exists():
    assert PREREG.exists(), "PREREGISTRATION.md is the tag registry; it is not optional"


def test_every_registered_tag_matches_the_naming_format():
    """Format is argmax-prereg-<phase>-v<major>.<minor>, no exceptions.

    The predecessor ended with `pre-pilot-v6.0` and `backfire-prereg-v1.0`
    covering different hypothesis sets and nearly cited the wrong one.
    """
    for row in _table_rows("Registry"):
        tag = row[0].strip("`")
        assert TAG_FORMAT.match(tag), f"malformed prereg tag: {tag!r}"


def test_every_hypothesis_names_the_fields_that_decide_it():
    """If no field decides it, either add the field or drop the hypothesis.

    This is the mechanism that prevents defect 3 from recurring.
    """
    for row in _table_rows("Hypotheses"):
        hyp_id, _statement, fields = row[0], row[1], row[2]
        assert fields.strip(), f"hypothesis {hyp_id} names no deciding field"


def test_every_hypothesis_belongs_to_a_registered_tag():
    tags = {row[0].strip("`") for row in _table_rows("Registry")}
    for row in _table_rows("Hypotheses"):
        tag = row[-1].strip("`")
        assert tag in tags, f"hypothesis {row[0]} cites unregistered tag {tag!r}"


# --- claim coverage: the fix for defect 3 -----------------------------------


def test_every_registered_claim_resolves_to_backing_rows():
    """No sentence describing a compute-matched comparison may exist without
    rows in the budget_matched table.

    This turns a prose-discipline problem into a test.
    """
    claims = _table_rows("Claims")
    if not claims:
        pytest.skip("no claims registered yet (pre-Step 0)")

    from argmax.persist.paths import derived_path

    for row in claims:
        claim_id, _sentence, table = row[0], row[1], row[2]
        path = derived_path(table.strip("`"))
        assert path.exists(), f"claim {claim_id} cites missing table {table}"
        # Row-level coverage is asserted once the table format is fixed; the
        # existence check above is the floor, not the ceiling.


# --- verdicts and thresholds ------------------------------------------------


def test_thresholds_are_literal_values_in_the_registry():
    """Threshold VALUES are asserted, not just the verdicts computed from them.

    A verdict that validates against a moved threshold passes every naive
    test.
    """
    rows = _table_rows("Thresholds")
    if not rows:
        pytest.skip("no thresholds registered yet (pre-Step 0)")
    for row in rows:
        name, value = row[0], row[1]
        assert value.strip(), f"threshold {name} has no literal value"
        float(value.strip("`"))  # must parse as a number, not prose


def test_stored_verdicts_match_recomputed_verdicts():
    """The core assertion. Skipped until confirmatory results exist."""
    from argmax.persist.paths import derived_path

    verdicts = derived_path("verdicts")
    if not verdicts.exists():
        pytest.skip("no stored verdicts yet (pre-Step 0)")
    pytest.fail(
        "implement once the verdict table format is fixed: reload each stored "
        "verdict, recompute it from the stored artifact rows, and assert both "
        "the outcome and the threshold value"
    )


def test_manifest_grid_fits_M():
    """A CI at the curve's endpoint requires M > max(grid).

    Asserted against the manifest rather than silently allowed, so that a bare
    endpoint is a deliberate choice.
    """
    from argmax.config import RUNS

    manifests = sorted(RUNS.glob("*/manifest.json"))
    if not manifests:
        pytest.skip("no runs yet (pre-Step 0)")

    import json

    for path in manifests:
        m = json.loads(path.read_text(encoding="utf-8"))
        grid, M = m.get("n_grid") or [], m.get("M")
        if grid and M is not None:
            assert max(grid) <= M, f"{path}: grid tops out above M"


# --- example of a test that is red by design --------------------------------
#
# @pytest.mark.falsification
# def test_h3_gate_does_not_beat_flat_sampling():
#     """H3: RED IS THE EXPECTED STATE.
#
#     H3 was falsified on the confirmatory split at argmax-prereg-<phase>-vX.Y.
#     This test asserts the falsification so that a future change which
#     silently "fixes" it is caught. Do not delete or skip it. If it turns
#     green, something changed in the pipeline, not in the world.
#     """


# --- citation provenance: the same shape as claim coverage -----------------
#
# A claim_id must resolve to artifact rows. A quoted figure from the
# predecessor must resolve to the published paper. Both are the same rule:
# a number in a document names where it came from, and the suite fails when it
# does not.

CITATION = "arXiv:2608.11403"

#: Files in the predecessor's repository that are drafts, not the published
#: artifact. Their headline numbers disagree with it. See PROVENANCE.md.
SUPERSEDED_SOURCES = (
    "backfire_paper_draft",
    "PILOT_WRITEUP",
    "TODO_full_study",
    "preregistration_backfire",
)

#: A superseded name may appear when a document is disclosing that it once
#: cited one. Naming the mistake is how the correction is auditable.
EXEMPT_MARKERS = ("supersed", "Correction", "correction", "must cite", "may cite")

ALLOWED_ARTIFACTS = (
    "paper/backfire_preprint.pdf",
    "paper/backfire_colm_submission.pdf",
)

#: `paper/*.md` is here because the draft is the document where a citation to
#: a superseded source does the most damage, and it was outside this scan
#: until the draft existed.
DOC_GLOBS = (
    "*.md",
    "files/*.md",
    "notes/*.md",
    "docs/**/*.md",
    "data/*.md",
    "paper/*.md",
)


def _documents() -> list[Path]:
    seen: dict[str, Path] = {}
    for pattern in DOC_GLOBS:
        for path in REPO.glob(pattern):
            if path.is_file():
                seen[str(path)] = path
    return sorted(seen.values())


def test_documents_exist_to_check():
    """Guards against the scan silently covering nothing."""
    assert len(_documents()) >= 5


def test_no_document_cites_a_superseded_predecessor_draft():
    """The drafts disagree with the published paper on its headline numbers.

    One of them reached a scope decision in this repository, which is why this
    is a test rather than a convention.
    """
    offenders = []
    for path in _documents():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not any(name in line for name in SUPERSEDED_SOURCES):
                continue
            if any(marker in line for marker in EXEMPT_MARKERS):
                continue  # disclosing the error, not repeating it
            offenders.append(f"{path.relative_to(REPO)}:{lineno}: {line.strip()[:90]}")
    assert not offenders, (
        "a document cites a superseded predecessor draft as a source:\n  "
        + "\n  ".join(offenders)
    )


def test_every_document_citing_the_paper_names_a_source_artifact():
    """A citation with no artifact beside it cannot be checked by a reader.

    PROVENANCE.md carries the digests; a citing document has to name which
    artifact it read, so that "the paper says X" is falsifiable.
    """
    offenders = []
    for path in _documents():
        text = path.read_text(encoding="utf-8")
        if CITATION not in text:
            continue
        if not any(artifact in text for artifact in ALLOWED_ARTIFACTS):
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, (
        f"documents cite {CITATION} without naming the artifact they read "
        f"({', '.join(ALLOWED_ARTIFACTS)}): {offenders}"
    )


def test_provenance_records_the_paper_and_its_unverified_version():
    """The digest is recorded because the arXiv version number is not stamped
    on the artifact. Recording a guessed version would be worse than recording
    that nobody has checked."""
    text = (REPO / "PROVENANCE.md").read_text(encoding="utf-8")
    assert CITATION in text
    assert "59d4dea8eba80b2a8bc05554c16b57fc854f5b3c6a7b0fd0e4e76b6c585ad6cc" in text
    assert "version number is not stamped" in text
