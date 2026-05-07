"""
calculator.py
================

Pure-math arbitrage detection and stake-sizing.
 
The calculator is stateless from an inputs-vs-outputs perspective; instances
exist purely to bind configuration (commission per leg) at construction
time, which is convenient for the live scanner where each (book-A, book-B)
pair has a fixed commission profile.
"""

from __future__ import annotations
from collections.abc import Sequence
from typing import Final
 
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent  
sys.path.insert(0, str(project_root / "src"))

from core.result import ArbitrageResult


# Module-level constants
MIN_OUTCOMES: Final[int] = 2
MAX_OUTCOMES: Final[int] = 64
"""Sanity ceiling. Realistic bookmaker markets stay well below this; any
input larger is almost certainly a bug in the caller's outcome set."""
 
MIN_DECIMAL_ODDS: Final[float] = 1.0
"""Decimal odds must be strictly greater than 1.0 to represent a payout
above stake. Books offer 1.01 as the floor in practice."""
 
MIN_COMMISSION: Final[float] = 0.0
MAX_COMMISSION: Final[float] = 1.0



class ArbitrageCalculator:
    """
    Detect and size arbitrage positions across N mutually exclusive outcomes.
 
    Given decimal odds ``o_i`` (one per outcome, typically the maximum
    across all polled bookmakers), the calculator solves the constrained
    optimisation problem
 
        maximise   R
        subject to s_i * o_eff_i = R   for all i      (equal payoff)
                   sum_i s_i = S                       (budget)
                   s_i >= 0
 
    where ``o_eff_i = 1 + (o_i - 1) * (1 - c_i)`` applies a per-leg
    commission ``c_i in [0, 1)`` (e.g., 0.06 for Betfair Australia sport,
    0.10 for NSW/ACT racing or NRL).
 
    The closed-form solution is
 
        R   = S / sum_i (1 / o_eff_i)
        s_i = R / o_eff_i
 
    with arbitrage iff ``sum_i (1 / o_eff_i) < 1``.
 
    Parameters
    ----------
    commission_per_leg : Sequence[float] | None, optional
        Per-leg fractional commission applied to net winnings. Length must
        match the number of odds passed to ``find_arbitrage``. Defaults to
        zero on every leg if ``None``.
    """
    
    def __init__(
            self,
            commission_per_leg: Sequence[float] | None = None,
    ) -> None:
        if commission_per_leg is not None:
            self.commission: tuple[float, ...] | None = tuple(commission_per_leg)
            self._validate_commissions(self._commission)
            
        else:
            self._commission_
            
    # Public API
    def find_arbitrage(
        self,
        odds: Sequence[float],
        total_stake: float = 100.0,
    ) -> ArbitrageResult:
        """Detect and size an arbitrage across N outcomes.
 
        Parameters
        ----------
        odds : Sequence[float]
            Decimal odds for each outcome. Each must be > 1.0. Order
            defines indexing of all returned vectors. Length is the
            number of outcomes ``N``, with ``MIN_OUTCOMES <= N <= MAX_OUTCOMES``.
        total_stake : float, optional
            Total bankroll to allocate, ``S``. Must be positive.
            Default 100.0 (units are currency-agnostic).
 
        Returns
        -------
        ArbitrageResult
            Stakes, return, profit, and margin. ``is_arbitrage`` is True
            iff the inverse-effective-odds sum is strictly less than 1.
 
        Raises
        ------
        ValueError
            If fewer than ``MIN_OUTCOMES`` or more than ``MAX_OUTCOMES``
            odds are supplied; if any odds are <= 1.0 or non-finite;
            if a commission vector was configured with mismatched length;
            or if ``total_stake`` is non-positive.
        """