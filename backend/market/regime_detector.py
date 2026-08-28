"""
Classifies current market conditions into a regime. The regime is what
lets the rest of the system "adapt its behavior" per-cycle (smaller
positions in high volatility, no new positions in a crisis, etc.) even
before the slower Adaptation Engine kicks in (see feedback/adaptation_engine.py).
"""
from decision.decision_schema import RegimeType

CRISIS_NEWS_TERMS = {"crash", "crisis", "default", "bank run", "circuit breaker", "trading halt", "collapse"}


class RegimeDetector:
    def __init__(self, risk_limits):
        self.risk_limits = risk_limits

    def detect(self, event) -> RegimeType:
        vol = event.volatility
        liq = event.liquidity
        move = abs(event.price_change_pct)
        news_text = " ".join(event.news).lower()

        if any(term in news_text for term in CRISIS_NEWS_TERMS):
            return RegimeType.CRISIS
        if vol >= self.risk_limits.crisis_volatility_threshold and liq < self.risk_limits.min_liquidity_score:
            return RegimeType.CRISIS
        if (event.news or event.event_tags) and vol >= self.risk_limits.high_volatility_threshold:
            return RegimeType.EVENT_DRIVEN
        if liq < self.risk_limits.min_liquidity_score:
            return RegimeType.LOW_LIQUIDITY
        if vol >= self.risk_limits.high_volatility_threshold:
            return RegimeType.HIGH_VOLATILITY
        if move >= 0.015:
            return RegimeType.TRENDING
        return RegimeType.NORMAL
