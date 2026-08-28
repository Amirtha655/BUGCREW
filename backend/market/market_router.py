"""
Decides which specialized agent should handle an incoming market event.

Modular by design: adding a new market (e.g. Fixed Income) is just
registering a new MarketType -> agent mapping, no changes needed here.
"""
from decision.decision_schema import MarketType

FOREX_ASSETS = {"USD/INR", "EUR/USD", "GBP/USD", "USD/JPY", "USD/CNY"}
COMMODITY_ASSETS = {"GOLD", "SILVER", "CRUDE_OIL", "NATURAL_GAS", "COPPER"}


def identify_market_type(asset: str) -> MarketType:
    """Fallback identifier used when an event doesn't already carry a market_type
    (e.g. a raw event feed keyed only by asset symbol)."""
    if "/" in asset or asset.upper() in FOREX_ASSETS:
        return MarketType.FOREX
    if asset.upper() in COMMODITY_ASSETS:
        return MarketType.COMMODITY
    return MarketType.EQUITY


class MarketRouter:
    def __init__(self, agents: dict):
        self.agents = agents  # MarketType -> agent instance

    def route(self, event):
        market_type = event.market_type or identify_market_type(event.asset)
        agent = self.agents.get(market_type)
        if agent is None:
            raise ValueError(f"No agent registered for market type {market_type}")
        return agent, market_type
