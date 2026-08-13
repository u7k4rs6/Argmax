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

TAG_FORMAT = re.compile(r"^argmax-prereg-[a-z0-9]+-v\d+\.\d+$")


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
