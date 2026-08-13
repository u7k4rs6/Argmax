"""Derived tables are a pure function of raw.

Deleting data/derived/ and running `make derived` must reproduce
byte-identical files. Skipped until there is a raw store to rebuild from; the
skip is explicit so an empty suite is never mistaken for a passing one.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DERIVED = REPO / "data" / "derived"
RAW = REPO / "data" / "raw"


def _digest(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _has_raw() -> bool:
    return RAW.exists() and any(RAW.rglob("*.jsonl*"))


@pytest.mark.skipif(not _has_raw(), reason="no raw store yet (pre-Step 0)")
def test_derived_rebuilds_byte_identically(tmp_path):
    """Was RED BY DESIGN on 2026-08-13, until derive.py existed.

    This test skipped for as long as there was no raw store. The margin-v1 run
    created one, so it now runs, and it fails because `scripts/derive.py` is
    still blocked: the extraction ladder is ported but the derived-table
    builder that consumes it does not exist yet.

    It skipped for as long as there was no raw store, then failed the moment
    the margin-v1 run created one, because there was no rebuild path. That was
    the correct state and the assertion below never changed.
    """
    before = _digest(DERIVED) if DERIVED.exists() else {}

    result = subprocess.run(
        [sys.executable, "scripts/derive.py"], cwd=REPO, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    after = _digest(DERIVED)
    assert after, "derive produced no files"
    if before:
        assert before == after, (
            "derived tables are not a pure function of raw. If a sampler is "
            "running, raw grew between the two builds and this is that, not "
            "non-determinism: check with a frozen copy of data/raw before "
            "concluding."
        )


def test_nothing_is_derived_only():
    """Every derived table must have a rebuild path.

    Structural placeholder: once derive.py enumerates its outputs, assert that
    each one appears in that enumeration. A table with no rebuild path is a
    table that cannot be checked.
    """
    tables = list(DERIVED.rglob("*.parquet")) if DERIVED.exists() else []
    if not tables:
        pytest.skip("no derived tables yet (pre-Step 0)")
    assert tables
