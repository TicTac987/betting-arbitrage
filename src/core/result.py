"""Result type returned by the arbitrage calculator."""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArbitrageResult:
    """
    Outcome of an arbitrage check on a single market.

    Frozen, hashable, no validation overhead. Distinct from
    ``ArbitrageOpportunity`` (in models.py), which is the richer
    Pydantic record persisted to storage.
    """

    is_arbitrage: bool
    odds: tuple[float, ...]
    effective_odds: tuple[float, ...]
    stakes: tuple[float, ...]
    total_stake: float
    guaranteed_return: float
    profit: float
    margin: float

    @property
    def n_outcomes(self) -> int:
        return len(self.odds)

    @property
    def return_on_capital(self) -> float:
        """Profit as a fraction of total stake. Equals margin / (1 - margin)."""
        return self.profit / self.total_stake