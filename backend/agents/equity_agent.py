from agents.base_agent import BaseMarketAgent, clamp
from decision.decision_schema import MarketType, RegimeType

POSITIVE_TERMS = ["upgrade", "beat", "beats estimates", "strong guidance", "record profit", "buyback", "earnings surprise"]
NEGATIVE_TERMS = ["downgrade", "miss", "misses estimates", "guidance cut", "lawsuit", "investigation", "fraud", "profit warning"]


class EquityAgent(BaseMarketAgent):
    """Considers price movement, momentum, volume/liquidity, volatility and company news."""

    market_type = MarketType.EQUITY
    max_daily_move_pct = 0.03

    def extract_signals(self, event) -> dict:
        momentum = clamp(event.price_change_pct / 0.05, -1.0, 1.0)
        volume_signal = clamp((event.liquidity - 0.5) * 2, -1.0, 1.0)
        volatility_penalty = -clamp(event.volatility / 0.05, 0.0, 1.0)
        news_text = " ".join(event.news).lower()
        pos = sum(1 for t in POSITIVE_TERMS if t in news_text)
        neg = sum(1 for t in NEGATIVE_TERMS if t in news_text)
        news_bias = clamp((pos - neg) / 2.0, -1.0, 1.0)
        return {
            "momentum": momentum,
            "volume_signal": volume_signal,
            "volatility_penalty": volatility_penalty,
            "news_bias": news_bias,
        }

    def weights(self) -> dict:
        return {"momentum": 0.35, "news_bias": 0.30, "volume_signal": 0.15, "volatility_penalty": 0.20}

    def factor_labels(self, event, signals) -> list[str]:
        out = []
        if signals["momentum"] > 0.25:
            out.append(f"Strong upward price momentum ({event.price_change_pct * 100:+.2f}%)")
        elif signals["momentum"] < -0.25:
            out.append(f"Negative price momentum ({event.price_change_pct * 100:+.2f}%)")
        if signals["news_bias"] > 0.25:
            out.append("Positive company/earnings news")
        elif signals["news_bias"] < -0.25:
            out.append("Negative company/earnings news")
        if signals["volume_signal"] > 0.2:
            out.append("Healthy trading volume/liquidity")
        elif signals["volume_signal"] < -0.2:
            out.append("Thin trading volume/liquidity")
        return out or ["No strong directional signal"]

    def risk_labels(self, event, signals, regime) -> list[str]:
        out = []
        if event.volatility > 0.035:
            out.append("Elevated price volatility")
        if event.liquidity < 0.4:
            out.append("Low liquidity may increase slippage")
        if regime in (RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY):
            out.append(f"Market regime is {regime.value}")
        return out or ["No elevated risk factors"]
