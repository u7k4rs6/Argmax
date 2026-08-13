"""Append-only writers.

Raw files are never rewritten, never sorted, never deduplicated in place. The
only supported mutation is appending a line.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from argmax.persist.paths import ledger_path
from argmax.schema import Sample


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "at", encoding="utf-8") as fh:  # type: ignore[operator]
        fh.write(line)
        fh.write("\n")
        fh.flush()


def append_sample(path: Path, sample: Sample) -> None:
    """Write one sample record. Validation happens in the Sample constructor,
    so a record that reaches here already conforms."""
    _append_line(path, sample.model_dump_json())


def append_ledger(row: dict[str, Any], path: Path | None = None) -> None:
    """One row per completed request.

    Realized spend is a sum over this file, not a guess and not a dashboard
    reading.
    """
    _append_line(
        path or ledger_path(), json.dumps(row, sort_keys=True, ensure_ascii=False)
    )


def write_manifest(path: Path, manifest_json: str) -> None:
    """Manifests are written once, at run end, and not appended to."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest_json, encoding="utf-8")
