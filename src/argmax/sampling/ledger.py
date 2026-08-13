"""The cost ledger.

One row per completed request: sample key, token counts from the `usage`
block, the pricing snapshot used, and the derived cost. Realized spend is a
sum over this file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from argmax.persist.paths import ledger_path
from argmax.persist.writer import append_ledger


@dataclass(frozen=True)
class PricingSnapshot:
    """Per-token prices with a date. Cost figures in the paper cite the
    snapshot, not a remembered number."""

    snapshot_id: str
    date: str
    usd_per_1m_input: float
    usd_per_1m_output: float
    usd_per_1m_reasoning: float | None = None

    def cost_usd(self, usage_raw: dict[str, Any]) -> float:
        """Derive cost from the verbatim usage block.

        Reasoning tokens are priced separately only when the provider both
        reports and prices them apart; otherwise providers already fold them
        into completion_tokens and adding them again double-counts.
        """
        prompt = float(usage_raw.get("prompt_tokens") or 0)
        completion = float(usage_raw.get("completion_tokens") or 0)
        cost = (
            prompt * self.usd_per_1m_input + completion * self.usd_per_1m_output
        ) / 1_000_000
        if self.usd_per_1m_reasoning is not None:
            reasoning = float(
                usage_raw.get("reasoning_tokens")
                or (usage_raw.get("completion_tokens_details") or {}).get(
                    "reasoning_tokens"
                )
                or 0
            )
            cost += reasoning * self.usd_per_1m_reasoning / 1_000_000
        return cost


class Ledger:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ledger_path()

    def record(
        self,
        *,
        sample_key: str,
        run_id: str,
        model_slug: str,
        usage_raw: dict[str, Any],
        pricing: PricingSnapshot,
        cost_usd: float,
        timestamp_utc: str,
    ) -> None:
        append_ledger(
            {
                "sample_key": sample_key,
                "run_id": run_id,
                "model_slug": model_slug,
                "usage_raw": usage_raw,
                "pricing_snapshot_id": pricing.snapshot_id,
                "cost_usd": cost_usd,
                "timestamp_utc": timestamp_utc,
            },
            path=self.path,
        )

    def realized_spend_usd(self) -> float:
        """Sum over the file. A corrupt trailing line is skipped, not repaired."""
        if not self.path.exists():
            return 0.0
        total = 0.0
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    total += float(json.loads(line).get("cost_usd", 0.0))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue
        return total
