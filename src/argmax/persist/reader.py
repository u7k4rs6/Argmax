"""Readers for the raw store.

A corrupted trailing line from an interrupted write is tolerated and reported,
not repaired. Repairing it in place would mutate ground truth.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from argmax.schema import Sample


@dataclass
class ReadReport:
    """What the reader saw. Surfaced by callers, never swallowed."""

    path: Path
    n_ok: int = 0
    n_corrupt: int = 0
    corrupt_line_numbers: list[int] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.n_corrupt == 0


def _open(path: Path):
    return (
        gzip.open(path, "rt", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open("r", encoding="utf-8")
    )


def read_samples(path: Path) -> tuple[list[Sample], ReadReport]:
    """Read one problem's samples.

    A truncated final line is expected after an interrupted run: it is counted
    and reported, and the file is left exactly as it is.
    """
    report = ReadReport(path=path)
    out: list[Sample] = []
    if not path.exists():
        return out, report

    with _open(path) as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Sample.model_validate(json.loads(line)))
            except (json.JSONDecodeError, ValueError):
                report.n_corrupt += 1
                report.corrupt_line_numbers.append(lineno)
                continue
            report.n_ok += 1
    return out, report


def iter_raw_files(root: Path) -> Iterator[Path]:
    yield from sorted(root.rglob("*.jsonl.gz"))
    yield from sorted(root.rglob("*.jsonl"))


def existing_sample_keys(path: Path) -> set[str]:
    """Keys already stored for one problem, for the sampler's skip check.

    Read without full validation: this runs before every request and only the
    key matters.
    """
    keys: set[str] = set()
    if not path.exists():
        return keys
    with _open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                key = json.loads(line).get("sample_key")
            except json.JSONDecodeError:
                continue  # corrupt trailing line; the record is re-drawn
            if key:
                keys.add(key)
    return keys
