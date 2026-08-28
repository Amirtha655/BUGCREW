"""Shared fixtures.

The two modules under test are deliberately pure: the Risk Guardian is a
function of (proposal, event, regime, portfolio snapshot) and the Adaptation
Engine is a function of (recent evaluated trades). Neither needs the app, the
network, or the real database, so these fixtures build only what they consume.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import RiskLimits
from db.models import Base, DecisionRecord
from decision.decision_schema import (
    ActionType, DecisionProposal, MarketEvent, MarketType, RegimeType,
)


@pytest.fixture
def limits() -> RiskLimits:
    """The shipped production limits -- tests assert against real numbers."""
    return RiskLimits()


@pytest.fixture
def db():
    """A throwaway in-memory database, isolated from the app's SQLite file."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_event(
    asset: str = "TCS",
    *,
    price: float = 3800.0,
    volatility: float = 0.012,
    liquidity: float = 0.9,
    price_change_pct: float = 0.01,
) -> MarketEvent:
    return MarketEvent(
        asset=asset,
        market_type=MarketType.EQUITY,
        price=price,
        price_change_pct=price_change_pct,
        volume=1000.0,
        volatility=volatility,
        liquidity=liquidity,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def make_proposal(
    asset: str = "TCS",
    *,
    action: ActionType = ActionType.BUY,
    allocation: float = 10_000.0,
    confidence: float = 0.6,
) -> DecisionProposal:
    return DecisionProposal(
        asset=asset,
        market_type=MarketType.EQUITY,
        action=action,
        confidence=confidence,
        reasoning="test proposal",
        suggested_allocation=allocation,
        expected_risk=0.2,
    )


def make_snapshot(
    *,
    portfolio_value: float = 100_000.0,
    available_cash: float = 100_000.0,
    total_exposure: float = 0.0,
    exposure_by_asset: dict | None = None,
    daily_pnl_pct: float = 0.0,
    has_position_in_asset: bool = False,
    open_position_count: int = 0,
) -> dict:
    """The subset of PortfolioManager.snapshot() that the Guardian reads."""
    return {
        "portfolio_value": portfolio_value,
        "available_cash": available_cash,
        "total_exposure": total_exposure,
        "exposure_by_asset": exposure_by_asset or {},
        "daily_pnl_pct": daily_pnl_pct,
        "has_position_in_asset": has_position_in_asset,
        "open_position_count": open_position_count,
    }


def add_outcome(
    db,
    *,
    regime: RegimeType | str = RegimeType.NORMAL,
    pnl: float,
    status: str = "EVALUATED",
    age_seconds: int = 0,
    strategy_tag: str = "momentum",
) -> DecisionRecord:
    """Insert one already-evaluated trade for the Adaptation Engine to read.

    `age_seconds` controls evaluated_at, which is what the engine orders by
    when it takes its lookback window.
    """
    regime_value = regime.value if isinstance(regime, RegimeType) else regime
    record = DecisionRecord(
        cycle_number=1,
        asset="TCS",
        market_type="EQUITY",
        price=3800.0,
        volatility=0.012,
        liquidity=0.9,
        regime=regime_value,
        proposed_action="BUY",
        confidence=0.6,
        reasoning="test",
        proposed_allocation=10_000.0,
        expected_risk=0.2,
        strategy_tag=strategy_tag,
        outcome_status=status,
        pnl=pnl,
        evaluated_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
    )
    db.add(record)
    db.commit()
    return record
