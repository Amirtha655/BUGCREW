"""
SQLAlchemy models.

Design note: we keep one row per decision cycle (DecisionRecord) that carries
the FULL trace of that cycle -- proposal, risk verdict, allocation, execution,
and (once known) the outcome. That single table is what powers both the
"agent activity" trace in the UI and the outcome/performance analysis, so the
demo can show cause-and-effect without joining half a dozen tables.
"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PortfolioState(Base):
    """Singleton row (id=1) holding cash. Positions live in the Position table."""
    __tablename__ = "portfolio_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    cash: Mapped[float] = mapped_column(Float, default=100000.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset: Mapped[str] = mapped_column(String(32), index=True, unique=True)
    market_type: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class DecisionRecord(Base):
    """Full trace of one autonomous-loop cycle for one asset."""
    __tablename__ = "decision_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_number: Mapped[int] = mapped_column(Integer, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)

    # --- market context at decision time ---
    asset: Mapped[str] = mapped_column(String(32))
    market_type: Mapped[str] = mapped_column(String(16))
    price: Mapped[float] = mapped_column(Float)
    volatility: Mapped[float] = mapped_column(Float)
    liquidity: Mapped[float] = mapped_column(Float)
    regime: Mapped[str] = mapped_column(String(32))
    event_description: Mapped[str] = mapped_column(Text, default="")

    # --- AI proposal ---
    proposed_action: Mapped[str] = mapped_column(String(24))
    confidence: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)
    proposed_allocation: Mapped[float] = mapped_column(Float)
    expected_risk: Mapped[float] = mapped_column(Float)
    expected_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    strategy_tag: Mapped[str] = mapped_column(String(64), default="")
    ai_provider_used: Mapped[str] = mapped_column(String(16), default="rule_based")

    # --- risk guardian ---
    risk_verdict: Mapped[str] = mapped_column(String(16), default="")   # APPROVE / REJECT / MODIFY
    risk_reasons: Mapped[str] = mapped_column(Text, default="")
    risk_adjusted_allocation: Mapped[float] = mapped_column(Float, default=0.0)

    # --- capital allocator ---
    final_allocation: Mapped[float] = mapped_column(Float, default=0.0)
    allocation_reasoning: Mapped[str] = mapped_column(Text, default="")

    # --- execution ---
    executed: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_price: Mapped[float] = mapped_column(Float, default=0.0)
    execution_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    slippage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    transaction_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # --- outcome (filled in later by the Outcome Monitor) ---
    outcome_status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING / EVALUATED
    actual_return_pct: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_summary: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StrategyPerformance(Base):
    """Aggregated memory of how a (strategy, regime) pair has performed."""
    __tablename__ = "strategy_performance"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_tag: Mapped[str] = mapped_column(String(64), index=True)
    regime: Mapped[str] = mapped_column(String(32), index=True)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    @property
    def success_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0


class AdaptationEvent(Base):
    """A log of every time the adaptation engine actually changed a parameter."""
    __tablename__ = "adaptation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    trigger: Mapped[str] = mapped_column(Text)
    parameter_changed: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str] = mapped_column(String(64))
    new_value: Mapped[str] = mapped_column(String(64))
    reasoning: Mapped[str] = mapped_column(Text)
