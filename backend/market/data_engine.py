"""
Simulated real-time market data. No paid APIs, no external calls.

Each tracked asset does a small random walk every cycle (so the dashboard
always looks "live"), and a scenario script can override any field for a
specific asset on a specific cycle to inject a scripted event (news,
volatility spike, liquidity drop, etc.) -- this is what powers the three
replayable demo scenarios.
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from decision.decision_schema import MarketEvent, MarketType


@dataclass
class AssetConfig:
    asset: str
    market_type: MarketType
    base_price: float
    base_volatility: float = 0.01
    base_liquidity: float = 0.85
    history: list = field(default_factory=list)


class MarketDataEngine:
    def __init__(self, asset_configs: list[AssetConfig], seed: int = 42):
        self.configs = {c.asset: c for c in asset_configs}
        self.state = {
            c.asset: {
                "price": c.base_price,
                "history": [c.base_price],
                "volatility": c.base_volatility,
                "liquidity": c.base_liquidity,
            }
            for c in asset_configs
        }
        self.rng = random.Random(seed)

    def assets(self) -> list[str]:
        return list(self.configs.keys())

    def tick(self, asset: str, override: dict | None = None) -> MarketEvent:
        cfg = self.configs[asset]
        st = self.state[asset]
        override = override or {}

        if "price_change_pct" in override:
            change = override["price_change_pct"]
        else:
            change = self.rng.gauss(0, st["volatility"])

        new_price = max(0.01, st["price"] * (1 + change))
        volatility = override.get("volatility", st["volatility"])
        liquidity = override.get("liquidity", st["liquidity"])
        news = override.get("news", [])
        event_tags = override.get("event_tags", [])
        volume = override.get("volume")

        st["history"].append(round(new_price, 4))
        st["history"] = st["history"][-30:]
        st["price"] = new_price
        st["volatility"] = volatility
        st["liquidity"] = liquidity

        return MarketEvent(
            asset=asset,
            market_type=cfg.market_type,
            price=round(new_price, 4),
            price_change_pct=round(change, 5),
            volume=volume,
            volatility=round(volatility, 4),
            liquidity=round(liquidity, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
            news=news,
            event_tags=event_tags,
            history=list(st["history"]),
        )

    def current_price(self, asset: str) -> float:
        return self.state[asset]["price"]


DEFAULT_ASSET_UNIVERSE = [
    AssetConfig("TCS", MarketType.EQUITY, base_price=3800.0, base_volatility=0.012, base_liquidity=0.9),
    AssetConfig("INFY", MarketType.EQUITY, base_price=1550.0, base_volatility=0.014, base_liquidity=0.88),
    AssetConfig("USD/INR", MarketType.FOREX, base_price=83.20, base_volatility=0.004, base_liquidity=0.95),
    AssetConfig("EUR/USD", MarketType.FOREX, base_price=1.085, base_volatility=0.005, base_liquidity=0.95),
    AssetConfig("GOLD", MarketType.COMMODITY, base_price=6350.0, base_volatility=0.010, base_liquidity=0.8),
    AssetConfig("CRUDE_OIL", MarketType.COMMODITY, base_price=6800.0, base_volatility=0.018, base_liquidity=0.75),
]
