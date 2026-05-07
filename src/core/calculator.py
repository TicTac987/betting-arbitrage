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
import math

from core.result import ArbitrageResult

# Module-level constants
MIN_OUTCOMES: Final[int] = 2
MAX_OUTCOMES: Final[int] = 64
"""Sanity ceiling. Realistic bookmaker markets stay well below this; any
input larger is almost certainly a bug in the caller's outcome set."""
 
MIN_DECIMAL_ODDS: Final[float] = 1.0
"""Decimal odds must be strictly greater than 1.0 to represent a payout
above stake. Books offer 1.01 as the floor in practice."""

MIN_MARGIN_TOLERANCE: Final[float] = 1e-9
"""Floor for treating ``margin`` as positive. Below this the result is
indistinguishable from float-rounding noise on ``sum(1/o_i)``."""

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
        
    Modelling assumptions and limitations
    -------------------------------------
    This calculator is a *pure mathematical kernel*. It assumes:

    1. **Per-leg fractional commission on net winnings.** This is a
       simplification of real exchange commission models. Betfair Australia,
       for example, applies commission to *market net profit* (winnings on
       all bets in the same market netted together), modulated by base rate
       and customer discount rate. The per-leg model here is exact only
       when each leg is in a different market.

    2. **Infinite liquidity.** Real bookmakers and exchanges have finite
       depth at any displayed price. A computed stake of $50 may only
       partially fill at the advertised odds, with the remainder filling
       at worse prices. This calculator does not model market depth.

    3. **Zero latency, zero slippage.** Odds are assumed to hold between
       detection and placement. In practice the second leg can move
       between the first and second clicks; live systems must price this
       slippage into the margin requirement.

    4. **Continuous stakes.** Real bets are quantised to cents and have
       per-book minimum stakes. The closed-form ``s_i = R / o_eff_i``
       generally produces non-placeable amounts that must be rounded,
       slightly perturbing the equal-payoff condition.


    Use ``min_margin`` (e.g. 0.005 for 0.5%) to require an economic edge
    large enough to plausibly survive (1)–(4).
    """
    
    
    def __init__(self, commission_per_leg: Sequence[float] | None = None) -> None:
        if commission_per_leg is None:
            self._commission: tuple[float, ...] | None = None
        else:
            commission = tuple(commission_per_leg)
            self._validate_commissions(commission)   # validate first
            self._commission = commission            # assign second
            
    # Public API
    def find_arbitrage(
        self,
        odds: Sequence[float],
        total_stake: float = 100.0,
        min_margin:  float = MIN_MARGIN_TOLERANCE
        ) -> ArbitrageResult:
        """
        Detect and size an arbitrage across N outcomes.

        Parameters
        ----------
        odds : Sequence[float]
            Decimal odds, each finite and > 1.0.
        total_stake : float
            Total bankroll S. Must be finite and positive. Default 100.0.
        min_margin : float
            Required margin for ``is_arbitrage`` to be True. Default is
            the numerical-noise floor (~1e-9). Pass a higher value (e.g.
            0.005 for 0.5%) to require an economically meaningful edge.

        Raises
        ------
        ValueError
            On any invalid input (odds count, odds value, stake value,
            commission/odds length mismatch, non-finite min_margin).
        """
        self._validate_odds(odds)
        self._validate_pairing(odds)
        if not math.isfinite(total_stake) or total_stake <= 0:
            raise ValueError(
                f"total_stake must be finite and positive, got {total_stake!r}"
            )
        if not math.isfinite(min_margin):
            raise ValueError(f"min_margin must be finite, got {min_margin!r}")

        effective = self._effective_odds(odds)
        inv_sum   = sum(1.0 / o for o in effective)
        margin    = 1.0 - inv_sum

        guaranteed_return = total_stake / inv_sum
        stakes = tuple(guaranteed_return / o for o in effective)
        profit = guaranteed_return - total_stake

        return ArbitrageResult(
            is_arbitrage=margin > min_margin,
            odds=tuple(odds),
            effective_odds=effective,
            stakes=stakes,
            total_stake=total_stake,
            guaranteed_return=guaranteed_return,
            profit=profit,
            margin=margin,
        )
    
    # Internals
    def _validate_pairing(self, odds: Sequence[float]) -> None:
        """Check that the configured commission vector matches odds length."""
        if self._commission is None:
            return
        if len(self._commission) != len(odds):
            raise ValueError(
                f"commission_per_leg has length {len(self._commission)} "
                f"but {len(odds)} odds were supplied"
            )

    def _effective_odds(self, odds: Sequence[float]) -> tuple[float, ...]:
        """Apply the commission transformation o -> 1 + (o-1)*(1-c).

        Pure transformation; pairing length must already be validated.
        """
        if self._commission is None:
            return tuple(odds)
        return tuple(
            1.0 + (o - 1.0) * (1.0 - c)
            for o, c in zip(odds, self._commission, strict=True)
        )

    @staticmethod
    def _validate_odds(odds: Sequence[float]) -> None:
        n = len(odds)
        if n < MIN_OUTCOMES:
            raise ValueError(
                f"At least {MIN_OUTCOMES} outcomes required, got {n}"
            )
        if n > MAX_OUTCOMES:
            raise ValueError(
                f"At most {MAX_OUTCOMES} outcomes supported, got {n}"
            )
        for i, o in enumerate(odds):
            if not math.isfinite(o) or o <= MIN_DECIMAL_ODDS:
                raise ValueError(
                    f"odds[{i}] = {o!r} is not a valid decimal odd "
                    f"(must be finite and > {MIN_DECIMAL_ODDS})"
                )

    @staticmethod
    def _validate_commissions(commission: Sequence[float]) -> None:
        for i, c in enumerate(commission):
            if not math.isfinite(c) or not (MIN_COMMISSION <= c < MAX_COMMISSION):
                raise ValueError(
                    f"commission_per_leg[{i}] = {c!r} is out of range "
                    f"[{MIN_COMMISSION}, {MAX_COMMISSION}) or non-finite"
                )