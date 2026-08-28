"""
Portfolio state: cash, positions, exposure, P&L. This is the source of
truth the Risk Guardian and Capital Allocator both read from, and the only
place executions are allowed to change money.

Note on "daily" loss: since a hackathon demo compresses what would be a
full trading day into a short live session, "daily_pnl_pct" here means
"since this session started" -- that's the practical equivalent for a
continuously-running paper-trading demo.
"""
from db.models import PortfolioState, Position
from decision.decision_schema import DecisionProposal, ExecutionResult, ActionType

BUY_ACTIONS = {ActionType.BUY, ActionType.INCREASE_EXPOSURE}


class PortfolioManager:
    def __init__(self, session_start_value: float):
        self.session_start_value = session_start_value

    def snapshot(self, db, price_lookup: dict, asset_of_interest: str | None = None) -> dict:
        state = db.get(PortfolioState, 1)
        positions = db.query(Position).filter(Position.quantity > 0).all()

        exposure_by_asset = {}
        total_exposure = 0.0
        for pos in positions:
            price = price_lookup.get(pos.asset, pos.avg_entry_price)
            value = pos.quantity * price
            exposure_by_asset[pos.asset] = value
            total_exposure += value

        portfolio_value = state.cash + total_exposure
        daily_pnl_pct = (
            (portfolio_value - self.session_start_value) / self.session_start_value
            if self.session_start_value else 0.0
        )

        return {
            "cash": state.cash,
            "available_cash": state.cash,
            "portfolio_value": portfolio_value,
            "total_exposure": total_exposure,
            "exposure_by_asset": exposure_by_asset,
            "open_position_count": len(positions),
            "has_position_in_asset": asset_of_interest in exposure_by_asset if asset_of_interest else False,
            "daily_pnl_pct": daily_pnl_pct,
            "realized_pnl": state.realized_pnl,
            "positions": {p.asset: {"quantity": p.quantity, "avg_entry_price": p.avg_entry_price} for p in positions},
        }

    def position_quantity(self, db, asset: str) -> float:
        pos = db.query(Position).filter(Position.asset == asset).first()
        return pos.quantity if pos else 0.0

    def apply_execution(self, db, proposal: DecisionProposal, execution: ExecutionResult) -> float:
        """Applies a filled execution to cash + position. Returns realized P&L (0 for buys)."""
        if not execution.executed:
            return 0.0

        state = db.get(PortfolioState, 1)
        pos = db.query(Position).filter(Position.asset == proposal.asset).first()
        buying = proposal.action in BUY_ACTIONS
        realized = 0.0

        if buying:
            cost = execution.execution_quantity * execution.execution_price + execution.transaction_cost
            state.cash -= cost
            if pos is None:
                pos = Position(
                    asset=proposal.asset,
                    market_type=proposal.market_type.value,
                    quantity=execution.execution_quantity,
                    avg_entry_price=execution.execution_price,
                )
                db.add(pos)
            else:
                total_qty = pos.quantity + execution.execution_quantity
                pos.avg_entry_price = (
                    (pos.avg_entry_price * pos.quantity + execution.execution_price * execution.execution_quantity)
                    / total_qty
                )
                pos.quantity = total_qty
        else:
            proceeds = execution.execution_quantity * execution.execution_price - execution.transaction_cost
            state.cash += proceeds
            if pos is not None:
                realized = (
                    (execution.execution_price - pos.avg_entry_price) * execution.execution_quantity
                    - execution.transaction_cost
                )
                state.realized_pnl += realized
                pos.quantity = max(0.0, pos.quantity - execution.execution_quantity)

        db.commit()
        return realized
