#!/usr/bin/env python
"""Download the gated GPQA Diamond csv to a local, git-ignored path.

Thin wrapper. The download lives here rather than in `src/argmax/datasets/`
because that package must not touch the network: doc 3 section 5.1 says
canonicalization reads the gated source locally, and tests/test_no_network.py
enforces the import rule.

Needs `HF_TOKEN` in `.env` and the GPQA terms accepted on the Hub. The file
lands under `data/`, which is ignored wholesale, so question text cannot reach
git.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

DEST = Path("data/gpqa_diamond.csv")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEST)
    args = ap.parse_args()

    load_dotenv()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print(
            "HF_TOKEN is not set. GPQA is gated: accept the terms on the Hub "
            "and put the token in .env.",
            file=sys.stderr,
        )
        return 2

    from huggingface_hub import hf_hub_download

    cached = hf_hub_download(
        "Idavidrein/gpqa", "gpqa_diamond.csv", repo_type="dataset", token=token
    )
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, args.dest)

    from argmax.datasets.gpqa import EXPECTED_PROMPT_HASH, load_problems
    from argmax.datasets.prompts_verbatim import PROMPT_TEMPLATE_HASH

    problems = load_problems(args.dest)
    print(f"wrote {args.dest}: {len(problems)} problems")
    print(f"  prompt template hash {PROMPT_TEMPLATE_HASH[:16]}", end=" ")
    matches = PROMPT_TEMPLATE_HASH == EXPECTED_PROMPT_HASH
    print("MATCHES the predecessor" if matches else "MISMATCH")
    print(f"  n_options constant: {len({p.n_options for p in problems}) == 1}")
    # Ids and hashes only. No question text is printed.
    print(f"  first problem_id {problems[0].problem_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
