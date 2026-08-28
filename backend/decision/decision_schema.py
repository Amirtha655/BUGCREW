"""
The shared data contracts that flow through the whole pipeline:

MarketEvent -> (router) -> Agent -> DecisionProposal -> (Risk Guardian) -> RiskVerdict
-> (Capital Allocator) -> AllocationResult -> (Execution Engine) -> ExecutionResult

Keeping these as plain dataclasses (not tied to the DB) means every stage of
the loop can be unit tested in isolation and the DB row is just one possible
serialization of a cycle, not the shape the pipeline is forced into.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MarketType(str, Enum):
    EQUITY = "EQUITY"
    FOREX = "FOREX"
    COMMODITY = "COMMODITY"


class ActionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    INCREASE_EXPOSURE = "INCREASE_EXPOSURE"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    WAIT = "WAIT"
    STOP_NEW_POSITIONS = "STOP_NEW_POSITIONS"


class RegimeType(str, Enum):
    NORMAL = "NORMAL"
    TRENDING = "TRENDING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    CRISIS = "CRISIS"
    EVENT_DRIVEN = "EVENT_DRIVEN"


class RiskVerdictType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"


@dataclass
class MarketEvent:
    """One tick of simulated real-time market data for one asset."""
    asset: str
    market_type: MarketType
    price: float
    price_change_pct: float
    volume: Optional[float]
    volatility: float          # 0-1+ normalized measure
    liquidity: float           # 0-1, higher = more liquid
    timestamp: str
    news: list[str] = field(default_factory=list)
    event_tags: list[str] = field(default_factory=list)   # e.g. ["central_bank", "geopolitical"]
    history: list[float] = field(default_factory=list)    # recent prices, most recent last


@dataclass
class DecisionProposal:
    """What a specialized market agent (the AI layer) proposes."""
    asset: str
    market_type: MarketType
    action: ActionType
    confidence: float                  # 0-1
    reasoning: str
    suggested_allocation: float        # currency amount
    expected_risk: float               # 0-1
    expected_return_pct: float = 0.0
    strategy_tag: str = "baseline"
    ai_provider_used: str = "rule_based"
    factors: list[str] = field(default_factory=list)      # bullet-point "why"
    risk_factors: list[str] = field(default_factory=list)  # bullet-point "risk"


@dataclass
class RiskVerdict:
    verdict: RiskVerdictType
    approved_allocation: float
    reasons: list[str]
    original_allocation: float


@dataclass
class AllocationResult:
    final_allocation: float
    reasoning: list[str]


@dataclass
class ExecutionResult:
    executed: bool
    execution_price: float
    execution_quantity: float
    slippage_pct: float
    transaction_cost: float
    note: str = ""
