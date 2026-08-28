"""
Strategy Memory: remembers how each (strategy_tag, regime) combination has
performed historically, and hands that back to agents as a "memory_hint"
so future decisions can be informed by past results. This is NOT machine
learning -- it's a running win/loss tally per bucket, which is honest about
what it is (see feedback/adaptation_engine.py for the actual behavior-change
mechanism that reads this data).
"""
from db.models import StrategyPerformance


class StrategyMemory:
    def record_outcome(self, db, strategy_tag: str, regime: str, pnl: float, success: bool) -> None:
        row = db.query(StrategyPerformance).filter_by(strategy_tag=strategy_tag, regime=regime).first()
        if row is None:
            # Python-side column defaults only apply on flush, not on attribute
            # access -- set them explicitly so the += below doesn't hit None.
            row = StrategyPerformance(strategy_tag=strategy_tag, regime=regime, total_trades=0, wins=0, losses=0, total_pnl=0.0)
            db.add(row)
        row.total_trades += 1
        if success:
            row.wins += 1
        else:
            row.losses += 1
        row.total_pnl += pnl
        db.commit()

    def get_hint(self, db, strategy_tag: str, regime: str) -> dict:
        row = db.query(StrategyPerformance).filter_by(strategy_tag=strategy_tag, regime=regime).first()
        if row is None or row.total_trades == 0:
            return {"success_rate": None, "summary": "No history yet for this strategy/regime combination", "total_trades": 0}
        rate = row.success_rate
        label = strategy_tag.replace("_", " ").title()
        return {
            "success_rate": rate,
            "summary": f"{label} in {regime}: {rate*100:.0f}% success rate over {row.total_trades} trades",
            "total_trades": row.total_trades,
        }

    def leaderboard(self, db) -> list[dict]:
        rows = db.query(StrategyPerformance).all()
        return sorted(
            [
                {
                    "strategy_tag": r.strategy_tag,
                    "regime": r.regime,
                    "success_rate": r.success_rate,
                    "total_trades": r.total_trades,
                    "total_pnl": r.total_pnl,
                }
                for r in rows
            ],
            key=lambda x: -x["total_trades"],
        )
