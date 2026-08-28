"""
Outcome Monitor: a few cycles after a trade executes, compares what actually
happened to the price against what the agent expected, records the P&L,
and feeds the result into Strategy Memory.
"""
from datetime import datetime, timezone
from db.models import DecisionRecord

BUY_LIKE = {"BUY", "INCREASE_EXPOSURE"}


class PerformanceMonitor:
    def __init__(self, evaluation_delay_cycles: int = 3):
        self.evaluation_delay_cycles = evaluation_delay_cycles

    def evaluate_due(self, db, current_cycle: int, price_lookup: dict, strategy_memory) -> list[DecisionRecord]:
        pending = (
            db.query(DecisionRecord)
            .filter(
                DecisionRecord.executed == True,  # noqa: E712
                DecisionRecord.outcome_status == "PENDING",
                DecisionRecord.cycle_number <= current_cycle - self.evaluation_delay_cycles,
            )
            .all()
        )
        evaluated = []
        for rec in pending:
            current_price = price_lookup.get(rec.asset)
            if current_price is None or rec.execution_price <= 0:
                continue

            raw_return_pct = round(((current_price - rec.execution_price) / rec.execution_price) * 100, 3)
            direction = 1 if rec.proposed_action in BUY_LIKE else -1
            directional_return_pct = raw_return_pct * direction
            pnl = round((directional_return_pct / 100.0) * rec.execution_quantity * rec.execution_price, 2)
            success = directional_return_pct > 0

            rec.actual_return_pct = directional_return_pct
            rec.pnl = pnl
            rec.outcome_status = "EVALUATED"
            rec.evaluated_at = datetime.now(timezone.utc)
            rec.outcome_summary = (
                f"Expected {rec.expected_return_pct:+.2f}%, actual {directional_return_pct:+.2f}% "
                f"({'Outperformed' if success else 'Underperformed'})"
            )
            strategy_memory.record_outcome(db, rec.strategy_tag, rec.regime, pnl, success)
            evaluated.append(rec)

        if evaluated:
            db.commit()
        return evaluated
