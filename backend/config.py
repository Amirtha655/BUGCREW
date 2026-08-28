"""
Central configuration for the whole system.

Everything that should be tunable without touching code lives here:
starting capital, risk limits, cycle speed, and which AI provider to use.
The Risk Guardian reads RiskLimits directly, so changing a number here
changes what the system will actually allow.
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RiskLimits:
    max_single_trade: float = 20000.0          # max INR in one trade
    max_asset_exposure_pct: float = 0.25        # max % of portfolio value in one asset
    max_portfolio_exposure_pct: float = 0.80    # max % of portfolio value in the market at once
    max_daily_loss_pct: float = 0.05            # stop new positions after this much daily loss
    max_position_count: int = 8                 # max number of simultaneous open positions
    min_liquidity_score: float = 0.3            # reject trades below this liquidity (0-1)
    high_volatility_threshold: float = 0.035    # above this, position sizes get cut
    crisis_volatility_threshold: float = 0.07   # above this, stop new positions entirely


@dataclass
class SystemConfig:
    starting_capital: float = 100000.0
    currency_symbol: str = "₹"
    cycle_interval_seconds: float = 4.0
    emergency_stop: bool = False
    risk: RiskLimits = field(default_factory=RiskLimits)

    # AI provider: "groq" uses the free Groq API if GROQ_API_KEY is set,
    # otherwise (or on any failure) the system automatically falls back
    # to the deterministic rule-based provider.
    ai_provider: str = os.getenv("AI_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    db_url: str = os.getenv("DATABASE_URL", "sqlite:///./market_agent.db")


settings = SystemConfig()
