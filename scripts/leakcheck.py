#!/usr/bin/env python
"""Pre-release leakage check: does a release artifact restate the questions?

Thin wrapper. All logic is in src/argmax/persist/leakage.py.

Offline. Reads the gated question source locally, reduces it to hashed
n-grams, and scans the release tree for them. Question text is never written
anywhere, including into this command's own output: a hit prints a path, a
line, and a fingerprint prefix.

    python scripts/leakcheck.py --questions <gated.jsonl> --target data/raw \\
        [--readme <release README>] [--ngram 10]

The questions file is JSONL or JSON; every string value in each record is
fingerprinted, so question text, option text, and explanations are all
covered without naming their keys.

Exit codes: 0 clean, 1 hits or unscanned files, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from argmax.errors import ArgmaxError
from argmax.persist.leakage import (
    DEFAULT_NGRAM,
    assert_canary_present,
    assert_no_leakage,
    fingerprints,
    scan,
)


def _strings(obj: object) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _strings(v)]
    return []


def read_questions(path: Path) -> list[str]:
    """Every string in the gated source. Held in memory, never written out."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        loaded = json.loads(text)
        records = loaded if isinstance(loaded, list) else [loaded]
    return [s for r in records for s in _strings(r)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--questions",
        required=True,
        type=Path,
        help="gated question source, read locally and never written out",
    )
    ap.add_argument(
        "--target",
        required=True,
        nargs="+",
        type=Path,
        help="files or directories about to be released",
    )
    ap.add_argument(
        "--readme",
        type=Path,
        help="release README, asserted to carry the canary string",
    )
    ap.add_argument("--ngram", type=int, default=DEFAULT_NGRAM)
    args = ap.parse_args()

    if not args.questions.exists():
        print(f"no such questions file: {args.questions}", file=sys.stderr)
        return 2

    marks = fingerprints(read_questions(args.questions), args.ngram)
    if not marks:
        print(
            f"{args.questions} produced no {args.ngram}-grams; a check against "
            "an empty fingerprint set passes vacuously, which is worse than "
            "not running it",
            file=sys.stderr,
        )
        return 2

    report = scan(args.target, marks, args.ngram)
    print(report.summary())

    if args.readme:
        assert_canary_present(args.readme)

    assert_no_leakage(report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ArgmaxError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
