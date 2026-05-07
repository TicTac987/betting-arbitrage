# arb-finder

**Arbitrage Detection & Quantitative Sports Betting Toolkit**

A modular, educational Python project for detecting arbitrage opportunities in Australian sports betting markets (AFL, NRL, NBA, horse racing). Built as a learning/portfolio piece drawing analogies to derivatives pricing and quantitative finance systems.

**Status**: Educational / Research Project. Profitability claims should be treated skeptically.

## Overview

This project formalizes arbitrage mathematics (analogous to no-arbitrage conditions in options pricing), implements a clean detection engine, and provides a foundation for live scanning while highlighting real-world frictions in Australian markets (2025–2026).

**Target audience**: Developers with physics/math or quant finance backgrounds interested in stochastic processes, optimization, and market microstructure applied to betting.

## Key Features (MVP)

- Pure-math arbitrage calculator with optimal stake sizing (2-way & 3-way)
- Odds normalization (decimal ↔ American ↔ fractional)
- Data models using Pydantic/dataclasses
- Modular architecture with asyncio-ready polling stubs
- Backtesting framework foundation

## Arbitrage Mathematics

### No-Arbitrage Condition

Analogous to derivatives pricing: an arbitrage exists when the sum of implied probabilities across the "best" odds for each mutually exclusive outcome is < 1 (after removing overround).

For a market with outcomes \( i = 1 \dots n \):

\[
\sum_{i=1}^n \frac{1}{o_i^*} < 1
\]

where \( o_i^* = \max_j (o_{i,j}) \) is the best decimal odds for outcome \( i \) across bookmakers \( j \).

**Overround decomposition**: Margin is rarely uniform. Skewed margins create "soft edges" — outcomes where one bookie's implied probability is significantly lower than the market consensus. These are the most exploitable for value + arb combinations.

### Stake Sizing (Constrained Optimization)

For total stake \( S \), solve:

\[
\max_{s_1,\dots,s_n} \min_k \left( s_k \cdot o_k - S + s_k \right)
\]

subject to \( \sum s_i = S \), \( s_i \geq 0 \).

**Closed-form for 2-way** (odds \( o_1, o_2 \)):

\[
s_1 = S \cdot \frac{o_2}{o_1 + o_2}, \quad s_2 = S \cdot \frac{o_1}{o_1 + o_2}
\]

Guaranteed profit: \( \pi = S \left( \frac{o_1 o_2}{o_1 + o_2} - 1 \right) \)

Extend similarly for 3-way (use linear solver or proportional allocation).

**After-cost formula**:
\[
\pi_{net} = \pi - c_{exchange} - f_{withdrawal} - \text{rounding losses}
\]

### Worked Example (2-way)

Book A: Home @ 2.10  
Book B: Away @ 1.95  

Sum of best implied probs: \( 1/2.10 + 1/1.95 \approx 0.476 + 0.513 = 0.989 \) → ~1.1% arb.

For \( S = 1000 \):  
\( s_{Home} \approx 481.93 \) → payout ~1012  
\( s_{Away} \approx 518.07 \) → payout ~1010 (minor rounding)  
Net ~1.0% after costs (realistic).

**Real-world failure modes**:
- Latency windows: 100–2000 ms typical for soft books.
- Liquidity ceilings: low on niche markets.
- Account restrictions ("gubbing"): common on corporate books within weeks/months for consistent winners. Betfair Exchange more tolerant but has commission (usually 5%) and liquidity limits.


