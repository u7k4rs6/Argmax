"""Config loading, and the `[BLOCKED: Step 0]` sentinel.

Every quantity that costs money is undecided until Step 0 returns real
numbers. Rather than let a plausible default leak into a run, configs carry
the literal string `[BLOCKED: Step 0]` and reading one raises.

Write none of these into any document until the audit or the fallback probe
returns real numbers.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from argmax.errors import StepZeroBlocked

BLOCKED = "[BLOCKED: Step 0]"

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS = REPO_ROOT / "configs"
DATA = REPO_ROOT / "data"
RUNS = REPO_ROOT / "runs"

#: What unblocks each decision. Quoted from doc 2 s9 so the error message says
#: what to go and measure rather than only what is missing.
UNBLOCKED_BY = {
    "max_tokens": "p95 output tokens, truncation curve",
    "M": "cost per sample",
    "n_grid": "cost per sample",
    "models": "total cost envelope",
    "tiers": "total cost envelope",
    "logprob_subsample_fraction": "mean output length, see doc 4 s7",
}


def is_blocked(value: Any) -> bool:
    return isinstance(value, str) and value.strip().startswith("[BLOCKED")


def require(value: Any, field: str, source: str) -> Any:
    """Return `value`, or raise if it is still blocked on Step 0.

    Call this at the point of use, not at load time: a config may legitimately
    hold blocked fields that a given code path never reads.
    """
    if is_blocked(value):
        raise StepZeroBlocked(field, source, UNBLOCKED_BY.get(field, ""))
    if value is None:
        raise StepZeroBlocked(field, source, UNBLOCKED_BY.get(field, ""))
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_model(slug: str) -> dict[str, Any]:
    cfg = load_yaml(CONFIGS / "models" / f"{slug}.yaml")
    cfg["_source"] = f"configs/models/{slug}.yaml"
    return cfg


def load_benchmark(name: str) -> dict[str, Any]:
    cfg = load_yaml(CONFIGS / "benchmarks" / f"{name}.yaml")
    cfg["_source"] = f"configs/benchmarks/{name}.yaml"
    return cfg


def load_phase(phase_id: str) -> dict[str, Any]:
    cfg = load_yaml(CONFIGS / "phases" / f"{phase_id}.yaml")
    cfg["_source"] = f"configs/phases/{phase_id}.yaml"
    return cfg


def spend_ceiling_usd() -> float:
    """The hard ceiling. No default: a default becomes the real limit."""
    from argmax.errors import NoSpendCeilingSet

    raw = os.environ.get("ARGMAX_SPEND_CEILING_USD", "").strip()
    if not raw:
        raise NoSpendCeilingSet(
            "ARGMAX_SPEND_CEILING_USD is not set. There is no default ceiling. "
            "Set it in the shell that runs the phase."
        )
    return float(raw)
