"""Paper execution engine tests.

The engine is what turns an approved allocation into a fill. These tests
mostly exist to pin down position closing: REDUCE_EXPOSURE sells half of what
is held, which without a floor halves a holding forever and never closes it.
"""
import pytest

from conftest import make_event, make_proposal
from decision.decision_schema import ActionType
from execution.paper_executor import MIN_POSITION_VALUE, PaperExecutionEngine


@pytest.fixture
def engine():
    return PaperExecutionEngine()


# --- actions that never reach the market ---------------------------------

@pytest.mark.parametrize("action", [ActionType.HOLD, ActionType.WAIT, ActionType.STOP_NEW_POSITIONS])
def test_informational_actions_do_not_execute(engine, action):
    result = engine.execute(make_proposal(action=action, allocation=0.0), make_event(), allocation=0.0)

    assert result.executed is False
    assert result.execution_quantity == 0.0


def test_buying_without_an_allocation_does_not_execute(engine):
    result = engine.execute(make_proposal(action=ActionType.BUY), make_event(), allocation=0.0)

    assert result.executed is False


def test_selling_without_a_position_does_not_execute(engine):
    result = engine.execute(
        make_proposal(action=ActionType.SELL, allocation=0.0), make_event(),
        allocation=0.0, current_quantity=0.0,
    )

    assert result.executed is False
    assert "No position" in result.note


# --- buying ---------------------------------------------------------------

def test_buying_converts_the_allocation_into_units(engine):
    event = make_event(price=1000.0)

    result = engine.execute(make_proposal(action=ActionType.BUY), event, allocation=10_000.0)

    assert result.executed is True
    assert result.execution_quantity == pytest.approx(10_000.0 / result.execution_price, rel=1e-3)
    assert result.transaction_cost > 0


def test_buying_slips_the_price_up_and_selling_slips_it_down(engine):
    event = make_event(price=1000.0)

    bought = engine.execute(make_proposal(action=ActionType.BUY), event, allocation=10_000.0)
    sold = engine.execute(
        make_proposal(action=ActionType.SELL, allocation=0.0), event,
        allocation=0.0, current_quantity=10.0,
    )

    assert bought.execution_price > event.price
    assert sold.execution_price < event.price


# --- closing out ----------------------------------------------------------

def test_selling_closes_the_whole_position(engine):
    result = engine.execute(
        make_proposal(action=ActionType.SELL, allocation=0.0), make_event(price=1000.0),
        allocation=0.0, current_quantity=8.0,
    )

    assert result.execution_quantity == 8.0


def test_reducing_a_large_position_sells_half(engine):
    result = engine.execute(
        make_proposal(action=ActionType.REDUCE_EXPOSURE, allocation=0.0), make_event(price=1000.0),
        allocation=0.0, current_quantity=8.0,  # 8,000 held, 4,000 would remain
    )

    assert result.execution_quantity == 4.0


def test_reducing_closes_the_position_when_the_remainder_would_be_dust(engine):
    """The regression this file exists for.

    Halving a position repeatedly never reaches zero, so the trade log filled
    with 0.000-unit "Reduce" trades and the portfolio kept an asset worth 0.
    A reduction that would leave less than MIN_POSITION_VALUE now closes out.
    """
    price = 1000.0
    held = (MIN_POSITION_VALUE * 1.5) / price  # halving would leave ~75, under the floor

    result = engine.execute(
        make_proposal(action=ActionType.REDUCE_EXPOSURE, allocation=0.0), make_event(price=price),
        allocation=0.0, current_quantity=held,
    )

    assert result.execution_quantity == pytest.approx(held, rel=1e-3), "should sell the lot, not half"


def test_reducing_an_already_negligible_position_closes_it(engine):
    price = 1000.0
    held = (MIN_POSITION_VALUE * 0.2) / price

    result = engine.execute(
        make_proposal(action=ActionType.REDUCE_EXPOSURE, allocation=0.0), make_event(price=price),
        allocation=0.0, current_quantity=held,
    )

    assert result.executed is True
    assert result.execution_quantity == pytest.approx(held, rel=1e-3)


def test_repeated_reductions_terminate_instead_of_halving_forever(engine):
    """Simulates what the running system actually did: reduce, then reduce
    what is left, over and over. This must reach zero in a few steps rather
    than producing an endless tail of near-zero trades."""
    price = 1000.0
    held = 20.0  # 20,000
    trades = []

    for _ in range(40):
        result = engine.execute(
            make_proposal(action=ActionType.REDUCE_EXPOSURE, allocation=0.0), make_event(price=price),
            allocation=0.0, current_quantity=held,
        )
        if not result.executed:
            break
        trades.append(result.execution_quantity)
        held = round(held - result.execution_quantity, 4)
        if held <= 0:
            break

    assert held == 0.0, "position never closed"
    assert len(trades) < 12, f"took {len(trades)} trades to close a position"
    assert all(q > 0 for q in trades), "executed a zero-unit trade"
    # No trade should be so small it renders as 0.000 units in the UI.
    assert all(round(q, 3) > 0 for q in trades), f"dust trades present: {trades}"
