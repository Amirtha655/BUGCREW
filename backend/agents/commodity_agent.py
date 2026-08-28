from agents.base_agent import BaseMarketAgent, clamp
from decision.decision_schema import MarketType, RegimeType

SUPPLY_TIGHT_TERMS = ["supply disruption", "export ban", "opec cut", "drought", "shortage", "production cut"]
SUPPLY_LOOSE_TERMS = ["oversupply", "bumper harvest", "opec increase", "demand slump", "stockpile build"]
GEOPOLITICAL_TERMS = ["war", "conflict", "sanctions", "geopolitical tension", "attack", "embargo"]


class CommodityAgent(BaseMarketAgent):
    """Considers price movement, volatility, supply/demand events and geopolitical risk."""

    market_type = MarketType.COMMODITY
    max_daily_move_pct = 0.04

    def extract_signals(self, event) -> dict:
        momentum = clamp(event.price_change_pct / 0.04, -1.0, 1.0)
        volatility_penalty = -clamp(event.volatility / 0.05, 0.0, 1.0)
        news_text = " ".join(event.news).lower()
        tight = sum(1 for t in SUPPLY_TIGHT_TERMS if t in news_text)
        loose = sum(1 for t in SUPPLY_LOOSE_TERMS if t in news_text)
        supply_demand_bias = clamp((tight - loose) / 2.0, -1.0, 1.0)
        geo = sum(1 for t in GEOPOLITICAL_TERMS if t in news_text)
        # Geopolitical tension typically pushes commodity (safe-haven/supply-risk) prices UP.
        geopolitical_bias = clamp(geo / 2.0, 0.0, 1.0)
        return {
            "momentum": momentum,
            "supply_demand_bias": supply_demand_bias,
            "geopolitical_bias": geopolitical_bias,
            "volatility_penalty": volatility_penalty,
        }

    def weights(self) -> dict:
        return {"momentum": 0.25, "supply_demand_bias": 0.30, "geopolitical_bias": 0.20, "volatility_penalty": 0.25}

    def factor_labels(self, event, signals) -> list[str]:
        out = []
        if signals["momentum"] > 0.25:
            out.append(f"Upward price move ({event.price_change_pct * 100:+.2f}%)")
        elif signals["momentum"] < -0.25:
            out.append(f"Downward price move ({event.price_change_pct * 100:+.2f}%)")
        if signals["supply_demand_bias"] > 0.25:
            out.append("Supply-tightening event detected")
        elif signals["supply_demand_bias"] < -0.25:
            out.append("Supply-loosening event detected")
        if signals["geopolitical_bias"] > 0.25:
            out.append("Geopolitical risk premium building")
        return out or ["No strong directional signal"]

    def risk_labels(self, event, signals, regime) -> list[str]:
        out = []
        if event.volatility > 0.045:
            out.append("Elevated commodity price volatility")
        if event.liquidity < 0.4:
            out.append("Low liquidity may increase slippage")
        if regime in (RegimeType.CRISIS, RegimeType.EVENT_DRIVEN):
            out.append(f"Market regime is {regime.value}")
        return out or ["No elevated risk factors"]
