#!/usr/bin/env python
"""Refresh the bibliography verification cache and report every mismatch.

    python scripts/verify_bib.py            # report against the cache
    python scripts/verify_bib.py --refresh  # re-fetch from the arXiv API

Argument parsing only; the logic is in `argmax.bib`. The suite reads the cache
this writes and never touches the network itself.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from argmax.bib import (  # noqa: E402
    compare,
    fetch_arxiv,
    load_cache,
    parse_bib,
    save_cache,
)

REPO = Path(__file__).resolve().parents[1]
BIB = REPO / "paper" / "tex" / "references.bib"
CACHE = REPO / "paper" / "tex" / "references.verified.json"
PROV = REPO / "paper" / "tex" / "references.provenance.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-fetch from arXiv")
    args = ap.parse_args()

    entries = parse_bib(BIB.read_text(encoding="utf-8"))
    cache = load_cache(CACHE)
    today = datetime.now(UTC).date().isoformat()

    with_id = [e for e in entries if e.arxiv_id]
    without = [e for e in entries if not e.arxiv_id]
    print(f"{len(entries)} entries: {len(with_id)} with an arXiv id, {len(without)} without")

    if args.refresh:
        for e in with_id:
            meta = fetch_arxiv(e.arxiv_id)
            cache[e.key] = {"arxiv_id": e.arxiv_id, "verified_utc": today, **meta}
            print(f"  fetched {e.key} ({e.arxiv_id})")
        save_cache(CACHE, cache)

    mismatches = []
    unverified = []
    for e in with_id:
        rec = cache.get(e.key)
        if not rec:
            unverified.append(e.key)
            continue
        mismatches.extend(compare(e, rec))

    print()
    for m in mismatches:
        print(m)
    print(f"\nmismatches: {len(mismatches)}")
    if unverified:
        print(f"NOT IN CACHE (run --refresh): {unverified}")

    prov = load_cache(PROV)
    missing = [e.key for e in without if e.key not in prov]
    print(f"entries needing a recorded source: {len(without)}, missing: {len(missing)}")
    for k in missing:
        print(f"  {k}")
    return 1 if (mismatches or unverified or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
