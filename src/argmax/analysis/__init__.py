"""Curves, gates, matched compute.

Every computation here is a pure function of stored raw data and produces a
PERSISTED ARTIFACT, never a printed number. No module in this package may
import an HTTP client; tests/test_no_network.py enforces it.
"""

from argmax.analysis.curves import vote_curve
from argmax.analysis.gates import evaluate_gate
from argmax.analysis.matched_compute import compare_at_budget

__all__ = ["vote_curve", "evaluate_gate", "compare_at_budget"]
