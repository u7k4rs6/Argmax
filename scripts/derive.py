#!/usr/bin/env python
"""Rebuild derived tables from raw. Offline, deterministic, idempotent.

Thin wrapper. All logic is in src/argmax/persist/derive.py.

Deleting data/derived/ and running this must reproduce byte-identical files.
tests/test_recompute.py asserts it.
"""

from __future__ import annotations

import argparse
import json
import sys

from argmax.errors import ArgmaxError
from argmax.persist.derive import build


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    summary = build()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ArgmaxError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(3) from None
