#!/usr/bin/env python
"""Draw samples for a phase.

Thin wrapper. All logic is in src/argmax/sampling/runner.py.

PAID. Refuses to start unless ARGMAX_SPEND_CEILING_USD is set, the capability
probe covers every required field, and (for confirmatory) the tree is clean
and a prereg tag is recorded.

Resume is "run the same command again": stored sample keys are skipped.
"""

from __future__ import annotations

import argparse
import sys

from argmax.config import load_phase, require
from argmax.errors import ArgmaxError
from argmax.sampling.probe import assert_phase_supported
from argmax.sampling.runner import assert_confirmatory_preconditions, run_phase
from argmax.sampling.spend import SpendGuard


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", required=True)
    ap.add_argument(
        "--split",
        required=True,
        choices=["exploratory", "confirmatory"],
        help="no default: a default is how the wrong split gets used silently",
    )
    args = ap.parse_args()

    cfg = load_phase(args.phase)
    source = cfg["_source"]

    if cfg.get("split") and cfg["split"] != args.split:
        print(
            f"--split {args.split} contradicts {source} (split: {cfg['split']})",
            file=sys.stderr,
        )
        return 2

    assert_confirmatory_preconditions(args.split, cfg.get("prereg_tag"))

    SpendGuard()  # raises if no ceiling is set

    for slug in cfg.get("models") or []:
        assert_phase_supported(slug, cfg.get("requires") or [])

    # Raise on any value still blocked on Step 0, before anything is spent.
    require(cfg.get("M"), "M", source)
    require(cfg.get("n_grid"), "n_grid", source)

    run_phase(args.phase, args.split)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ArgmaxError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    except NotImplementedError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        raise SystemExit(3) from None
