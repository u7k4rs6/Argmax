"""The spend guard.

Credits are the binding constraint, so overspend is treated as a security
incident class rather than an operational annoyance.

    projected (from the capability probe's MEASURED tokens)
  + realized  (sum over runs/ledger.jsonl)
  > ARGMAX_SPEND_CEILING_USD   ->  refuse to start

The projection uses measured tokens because a projection from a guessed token
count is the same mistake the ceiling exists to catch.
"""

from __future__ import annotations

from dataclasses import dataclass

from argmax.config import spend_ceiling_usd
from argmax.errors import SpendCeilingExceeded
from argmax.sampling.ledger import Ledger, PricingSnapshot


@dataclass(frozen=True)
class Projection:
    n_requests: int
    mean_prompt_tokens: float
    mean_completion_tokens: float
    pricing: PricingSnapshot

    def usd(self) -> float:
        per_request = self.pricing.cost_usd(
            {
                "prompt_tokens": self.mean_prompt_tokens,
                "completion_tokens": self.mean_completion_tokens,
            }
        )
        return per_request * self.n_requests


class SpendGuard:
    def __init__(self, ledger: Ledger | None = None) -> None:
        self.ledger = ledger or Ledger()
        # Raises NoSpendCeilingSet at construction, i.e. before anything is
        # spent, rather than at the first request.
        self.ceiling = spend_ceiling_usd()

    def check(self, projections: list[Projection]) -> float:
        """Pre-flight. Returns headroom in USD, or raises."""
        projected = sum(p.usd() for p in projections)
        realized = self.ledger.realized_spend_usd()
        total = projected + realized
        if total > self.ceiling:
            raise SpendCeilingExceeded(
                f"projected ${projected:,.2f} + realized ${realized:,.2f} "
                f"= ${total:,.2f} exceeds ARGMAX_SPEND_CEILING_USD "
                f"= ${self.ceiling:,.2f}"
            )
        return self.ceiling - total

    def check_live(self, additional_usd: float = 0.0) -> None:
        """In-flight check, called between requests so a run stops at the
        ceiling instead of discovering it afterwards."""
        realized = self.ledger.realized_spend_usd() + additional_usd
        if realized > self.ceiling:
            raise SpendCeilingExceeded(
                f"realized ${realized:,.2f} crossed the ceiling "
                f"${self.ceiling:,.2f} mid-run; stopping"
            )
