#!/usr/bin/env python
"""Curves, gates, matched-compute comparisons. Offline.

Every computation persists an artifact. Nothing here prints a number that is
not also written to a file: a printed-only number is how the predecessor ended
up with claims that could not be traced to a script.
"""

from __future__ import annotations

import argparse
import sys

from argmax.errors import ArgmaxError


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--split",
        required=True,
        choices=["exploratory", "confirmatory"],
        help="no default: a default is how the wrong split gets used silently",
    )
    ap.parse_args()
    raise NotImplementedError(
        "analyze is blocked on Step 0: the N grid and M are undecided, and "
        "the extraction ladder is not yet ported."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ArgmaxError, NotImplementedError) as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(3) from None
