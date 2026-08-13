"""The skip registry describes tests that exist.

A registry entry is permission for a specific test to not run. Permission left
behind after the test was renamed or deleted is permission nobody granted, so
the entries are checked against the source.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.conftest import EXPECTED_DEFAULT_SKIP_COUNT, EXPECTED_SKIPS

REPO = Path(__file__).resolve().parents[1]


def _test_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }


@pytest.mark.parametrize("nodeid", sorted(EXPECTED_SKIPS))
def test_every_registered_skip_names_a_real_test(nodeid: str):
    relpath, _, name = nodeid.partition("::")
    path = REPO / relpath
    assert path.exists(), f"{nodeid} points at a file that does not exist"
    assert name in _test_names(path), f"{nodeid} points at a test that does not exist"


def test_every_registered_reason_says_what_would_unblock_it():
    """ "pre-Step 0" is the only reason anything here is allowed to skip."""
    for nodeid, reason in EXPECTED_SKIPS.items():
        assert "pre-Step 0" in reason, (
            f"{nodeid} skips for a reason that is not the Step 0 block: {reason!r}"
        )


def test_the_default_suite_expects_the_two_recompute_skips():
    """The count is stated as a literal so that changing it is a visible edit."""
    default_run = {n for n in EXPECTED_SKIPS if n.startswith("tests/test_")}
    assert len(default_run) == EXPECTED_DEFAULT_SKIP_COUNT
    assert all("test_recompute.py" in n for n in default_run)
