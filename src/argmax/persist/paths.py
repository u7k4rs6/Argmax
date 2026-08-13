"""Where raw and derived data live.

    data/raw/{split}/{benchmark}/{model_slug}/{param_hash}/{problem_id}.jsonl

`param_hash` is in the path so that a parameter change cannot contaminate an
existing sample set.

Exploratory and confirmatory are separate directory trees, not a boolean flag,
so that the wrong split cannot be selected by a default.
"""

from __future__ import annotations

from pathlib import Path

from argmax.config import DATA
from argmax.schema import Split


def raw_root(split: Split | str) -> Path:
    return DATA / "raw" / str(Split(split).value)


def raw_path(
    split: Split | str,
    benchmark: str,
    model_slug: str,
    param_hash: str,
    problem_id: str,
    *,
    gzipped: bool = True,
) -> Path:
    """Path to one problem's append-only sample file.

    JSONL gzipped at rest; see doc 4 s7 storage mechanics.
    """
    suffix = ".jsonl.gz" if gzipped else ".jsonl"
    return (
        raw_root(split) / benchmark / model_slug / param_hash / f"{problem_id}{suffix}"
    )


def derived_path(name: str) -> Path:
    return DATA / "derived" / f"{name}.parquet"


def manifest_path(run_id: str) -> Path:
    from argmax.config import RUNS

    return RUNS / run_id / "manifest.json"


def ledger_path() -> Path:
    from argmax.config import RUNS

    return RUNS / "ledger.jsonl"
