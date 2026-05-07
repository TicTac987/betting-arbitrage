# Sports Betting Arbitrage System

A Python-based research project for detecting arbitrage opportunities across sports betting markets.

This project is for **educational and portfolio purposes only**, not a guaranteed profit system.

---

## Overview

This system scans odds from multiple bookmakers and identifies situations where a guaranteed profit (arbitrage) exists by comparing price discrepancies across markets.

Core idea:

If the combined implied probability across all outcomes is less than 1, an arbitrage opportunity exists.

---

## Arbitrage Condition

For a market with decimal odds:
$$ \sum{\frac{1}{odds_i}} < 1 $$
Shows arbitrage exists
