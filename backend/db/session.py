from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from db.models import Base, PortfolioState, Position, DecisionRecord, StrategyPerformance, AdaptationEvent

engine = create_engine(
    settings.db_url,
    connect_args={"check_same_thread": False} if settings.db_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.get(PortfolioState, 1) is None:
            db.add(PortfolioState(id=1, cash=settings.starting_capital, realized_pnl=0.0))
            db.commit()


def reset_all() -> None:
    """Wipes all trading state back to a fresh start -- used when a new demo
    scenario is loaded so it isn't polluted by the previous run's trades."""
    with SessionLocal() as db:
        db.query(DecisionRecord).delete()
        db.query(Position).delete()
        db.query(StrategyPerformance).delete()
        db.query(AdaptationEvent).delete()
        state = db.get(PortfolioState, 1)
        state.cash = settings.starting_capital
        state.realized_pnl = 0.0
        db.commit()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
