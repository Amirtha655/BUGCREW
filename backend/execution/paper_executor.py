"""
Paper (simulated) execution engine. No real orders are ever sent anywhere.

Simulates the things that make real execution imperfect: slippage that
grows with volatility and shrinks with liquidity, a transaction cost, and
(implicitly) a same-cycle execution delay since this runs inside the
autonomous loop's own cycle cadence.
"""
import random
from decision.decision_schema import DecisionProposal, MarketEvent, ActionType, ExecutionResult

TRANSACTION_COST_RATE = 0.0015  # 0.15% simulated brokerage/spread cost
NO_OP_ACTIONS = {ActionType.HOLD, ActionType.WAIT, ActionType.STOP_NEW_POSITIONS}

# A holding worth less than this is a leftover, not a position. REDUCE_EXPOSURE
# sells half of what is held, so without a floor a position halves forever --
# 0.070 -> 0.035 -> 0.018 -> ... -> 0.000 -- never closing, filling the trade
# log with meaningless zero-unit trades and leaving stubs that still show up
# in the portfolio as an asset worth 0. Reductions that would leave less than
# this close the position instead.
MIN_POSITION_VALUE = 100.0


class PaperExecutionEngine:
    def __init__(self, seed: int = 7):
        self.rng = random.Random(seed)

    def execute(
        self,
        proposal: DecisionProposal,
        event: MarketEvent,
        allocation: float,
        current_quantity: float = 0.0,
    ) -> ExecutionResult:
        if proposal.action in NO_OP_ACTIONS:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, note="No execution: informational action only")

        slippage_pct = round(event.volatility * (1.2 - event.liquidity) * self.rng.uniform(0.5, 1.5), 5)
        buying = proposal.action in (ActionType.BUY, ActionType.INCREASE_EXPOSURE)
        direction = 1 if buying else -1
        execution_price = round(event.price * (1 + direction * slippage_pct), 4)

        if buying:
            if allocation <= 0:
                return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, note="No allocation available to execute")
            quantity = round(allocation / execution_price, 4)
            transaction_cost = round(allocation * TRANSACTION_COST_RATE, 2)
        else:
            if current_quantity <= 0:
                return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, note="No position to sell")

            sell_fraction = 1.0 if proposal.action == ActionType.SELL else 0.5
            quantity = round(current_quantity * sell_fraction, 4)

            # Close the position outright rather than leaving an untradeable
            # stub behind -- either because the whole holding is already
            # negligible, or because taking half would make the remainder so.
            held_value = current_quantity * execution_price
            remaining_value = (current_quantity - quantity) * execution_price
            if held_value < MIN_POSITION_VALUE or remaining_value < MIN_POSITION_VALUE:
                quantity = round(current_quantity, 4)

            if quantity <= 0:
                return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, note="No position to sell")
            proceeds = quantity * execution_price
            transaction_cost = round(proceeds * TRANSACTION_COST_RATE, 2)

        return ExecutionResult(
            executed=True,
            execution_price=execution_price,
            execution_quantity=quantity,
            slippage_pct=slippage_pct,
            transaction_cost=transaction_cost,
            note=f"Paper {proposal.action.value} executed",
        )
