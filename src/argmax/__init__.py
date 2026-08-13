"""Argmax: accuracy-versus-compute curves from stored completions.

Read files/02-technical-architecture.md before changing anything here.
"""

from argmax.errors import (
    CapabilityMissing,
    DirtyTreeError,
    SpendCeilingExceeded,
    StepZeroBlocked,
)
from argmax.schema import SCHEMA_VERSION

__all__ = [
    "SCHEMA_VERSION",
    "StepZeroBlocked",
    "SpendCeilingExceeded",
    "CapabilityMissing",
    "DirtyTreeError",
]
