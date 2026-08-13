#!/usr/bin/env python
"""Rebuild derived tables from raw. Offline, deterministic, idempotent.

Deleting data/derived/ and running this must reproduce byte-identical files.
tests/test_recompute.py asserts it.
"""

from __future__ import annotations

import argparse
import sys

from argmax.errors import ArgmaxError


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    raise NotImplementedError(
        "derive is blocked on Step 0: the extraction ladder must first be "
        "ported verbatim from the published self-consistency-backfire repo "
        "(see src/argmax/extract/ladder.py), and the N grid must be decided."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ArgmaxError, NotImplementedError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(3) from None
