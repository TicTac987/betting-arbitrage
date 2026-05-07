"""Conversions between decimal, American (moneyline), and fractional odds.

All public methods are pure functions exposed as static methods on
``OddsNormalizer`` for namespacing. Decimal is the canonical internal
representation throughout the project; conversions exist for ingestion
(e.g., scraping a US-formatted source) and presentation only.

References
----------
- Decimal odds ``d``: total return per unit stake on a winning bet,
  including stake. Implied probability = ``1 / d``.
- American odds ``a``: positive ``a`` means a +``a`` payout on a 100
  unit stake; negative ``a`` means staking ``|a|`` to win 100. ``a == 0``
  is undefined.
- Fractional odds ``n/d``: net winnings of ``n`` per ``d`` staked.
  Implied probability = ``d / (n + d)``.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Final


MIN_DECIMAL_ODDS: Final[float] = 1.0
"""Decimal odds floor; values must be strictly greater."""

EVEN_DECIMAL_ODDS: Final[float] = 2.0
"""Boundary at which American odds switch sign convention."""

AMERICAN_BASE: Final[int] = 100
"""Reference unit for American odds quotation."""

DEFAULT_FRACTION_DENOMINATOR_LIMIT: Final[int] = 100
"""Cap on denominator when approximating decimal -> fractional. Higher
values give finer approximation at the cost of less human-readable
fractions (e.g., 47/53 vs 9/10)."""


class OddsNormalizer:
    """Pure conversion utilities between odds formats.

    All methods are static. Round-trip identity holds modulo the
    rounding inherent in American (integer) and fractional (rational
    with bounded denominator) representations.
    """

    # ------------------------------------------------------------------ #
    # Decimal <-> American
    # ------------------------------------------------------------------ #

    @staticmethod
    def american_to_decimal(american: int) -> float:
        """Convert American odds to decimal.

        Parameters
        ----------
        american : int
            American moneyline odds. Must be non-zero.

        Returns
        -------
        float
            Decimal odds, > 1.0.

        Raises
        ------
        ValueError
            If ``american`` is zero.

        Examples
        --------
        >>> OddsNormalizer.american_to_decimal(150)
        2.5
        >>> OddsNormalizer.american_to_decimal(-200)
        1.5
        """
        if american == 0:
            raise ValueError("American odds cannot be zero")
        if american > 0:
            return 1.0 + american / AMERICAN_BASE
        return 1.0 + AMERICAN_BASE / abs(american)

    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert decimal odds to American (moneyline) odds.

        Parameters
        ----------
        decimal_odds : float
            Decimal odds. Must be > 1.0.

        Returns
        -------
        int
            American odds, rounded to nearest integer. The sign follows
            the standard convention: positive for ``decimal >= 2.0``
            (underdogs), negative for ``decimal < 2.0`` (favourites).

        Raises
        ------
        ValueError
            If ``decimal_odds <= 1.0``.

        Examples
        --------
        >>> OddsNormalizer.decimal_to_american(2.5)
        150
        >>> OddsNormalizer.decimal_to_american(1.5)
        -200
        """
        OddsNormalizer._validate_decimal(decimal_odds)
        if decimal_odds >= EVEN_DECIMAL_ODDS:
            return round((decimal_odds - 1.0) * AMERICAN_BASE)
        return -round(AMERICAN_BASE / (decimal_odds - 1.0))

    # ------------------------------------------------------------------ #
    # Decimal <-> Fractional
    # ------------------------------------------------------------------ #

    @staticmethod
    def fractional_to_decimal(numerator: int, denominator: int) -> float:
        """Convert fractional odds ``n/d`` to decimal odds.

        Parameters
        ----------
        numerator : int
            The "n" in n/d. Must be positive.
        denominator : int
            The "d" in n/d. Must be positive.

        Returns
        -------
        float
            Decimal odds = 1 + n/d.

        Examples
        --------
        >>> OddsNormalizer.fractional_to_decimal(5, 2)
        3.5
        >>> OddsNormalizer.fractional_to_decimal(1, 4)
        1.25
        """
        if numerator <= 0 or denominator <= 0:
            raise ValueError(
                f"Fractional parts must be positive, got {numerator}/{denominator}"
            )
        return 1.0 + numerator / denominator

    @staticmethod
    def decimal_to_fractional(
        decimal_odds: float,
        max_denominator: int = DEFAULT_FRACTION_DENOMINATOR_LIMIT,
    ) -> tuple[int, int]:
        """Convert decimal odds to a reduced fractional approximation.

        Uses ``Fraction.limit_denominator`` to find the closest
        rational approximation under the supplied denominator cap.

        Parameters
        ----------
        decimal_odds : float
            Decimal odds. Must be > 1.0.
        max_denominator : int, optional
            Maximum denominator for the approximation, default
            ``DEFAULT_FRACTION_DENOMINATOR_LIMIT``.

        Returns
        -------
        tuple[int, int]
            ``(numerator, denominator)`` in lowest terms.

        Examples
        --------
        >>> OddsNormalizer.decimal_to_fractional(3.5)
        (5, 2)
        >>> OddsNormalizer.decimal_to_fractional(2.5)
        (3, 2)
        """
        OddsNormalizer._validate_decimal(decimal_odds)
        f = Fraction(decimal_odds - 1.0).limit_denominator(max_denominator)
        return f.numerator, f.denominator

    # ------------------------------------------------------------------ #
    # Probability helper
    # ------------------------------------------------------------------ #

    @staticmethod
    def implied_probability(decimal_odds: float) -> float:
        """Implied probability ``q = 1/o`` from decimal odds.

        Note this is the raw bookmaker-implied probability and includes
        the bookmaker's overround; for a single-book market, the sum
        across outcomes will exceed 1.

        Parameters
        ----------
        decimal_odds : float
            Decimal odds. Must be > 1.0.

        Returns
        -------
        float
            Implied probability in (0, 1).
        """
        OddsNormalizer._validate_decimal(decimal_odds)
        return 1.0 / decimal_odds

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_decimal(decimal_odds: float) -> None:
        if not (decimal_odds > MIN_DECIMAL_ODDS) or decimal_odds == float("inf"):
            raise ValueError(
                f"Decimal odds must be finite and > {MIN_DECIMAL_ODDS}, "
                f"got {decimal_odds!r}"
            )