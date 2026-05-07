from datetime import datetime
from pydantic import BaseModel, PositiveFloat, Field


class Odds(BaseModel):
    bookmaker: str
    outcome: str
    decimal_odds: PositiveFloat = Field(gt=1.0)
    timestamp: datetime
    market_id: str


class Market(BaseModel):
    market_id: str
    sport: str
    event_name: str
    commence_time: datetime
    outcomes: tuple[str, ...]
    odds: list[Odds]


class ArbitrageOpportunity(BaseModel):
    market: Market
    best_odds: dict[str, Odds]
    stakes: dict[str, float]
    margin: float
    detected_at: datetime
    expires_estimate: datetime | None = None