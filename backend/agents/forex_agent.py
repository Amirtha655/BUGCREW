from agents.base_agent import BaseMarketAgent, clamp
from decision.decision_schema import MarketType, RegimeType

HAWKISH_TERMS = ["rate hike", "hawkish", "tightening", "strong economy", "inflation surprise"]
DOVISH_TERMS = ["rate cut", "dovish", "recession", "intervention", "devaluation", "weak economy"]


class ForexAgent(BaseMarketAgent):
    """Considers exchange-rate movement, volatility, interest-rate/central-bank events and currency momentum."""

    market_type = MarketType.FOREX
    max_daily_move_pct = 0.015

    def extract_signals(self, event) -> dict:
        momentum = clamp(event.price_change_pct / 0.02, -1.0, 1.0)
        volatility_penalty = -clamp(event.volatility / 0.03, 0.0, 1.0)
        news_text = " ".join(event.news).lower()
        hawkish = sum(1 for t in HAWKISH_TERMS if t in news_text)
        dovish = sum(1 for t in DOVISH_TERMS if t in news_text)
        rate_bias = clamp((hawkish - dovish) / 2.0, -1.0, 1.0)
        liquidity_factor = clamp((event.liquidity - 0.5) * 2, -1.0, 1.0)
        return {
            "momentum": momentum,
            "rate_bias": rate_bias,
            "volatility_penalty": volatility_penalty,
            "liquidity_factor": liquidity_factor,
        }

    def weights(self) -> dict:
        return {"momentum": 0.30, "rate_bias": 0.35, "volatility_penalty": 0.20, "liquidity_factor": 0.15}

    def factor_labels(self, event, signals) -> list[str]:
        out = []
        if signals["momentum"] > 0.25:
            out.append(f"Currency strengthening ({event.price_change_pct * 100:+.2f}%)")
        elif signals["momentum"] < -0.25:
            out.append(f"Currency weakening ({event.price_change_pct * 100:+.2f}%)")
        if signals["rate_bias"] > 0.25:
            out.append("Hawkish central bank / rate signal")
        elif signals["rate_bias"] < -0.25:
            out.append("Dovish central bank / rate signal")
        if signals["liquidity_factor"] < -0.3:
            out.append("Below-normal FX market liquidity")
        return out or ["No strong directional signal"]

    def risk_labels(self, event, signals, regime) -> list[str]:
        out = []
        if event.volatility > 0.03:
            out.append("Elevated FX volatility")
        if event.liquidity < 0.4:
            out.append("Thin liquidity, wider spreads likely")
        if regime in (RegimeType.CRISIS, RegimeType.EVENT_DRIVEN):
            out.append(f"Market regime is {regime.value} (economic event risk)")
        return out or ["No elevated risk factors"]
