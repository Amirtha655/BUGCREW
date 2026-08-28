"""Risk Guardian tests.

The Guardian is the project's core safety claim: it is the only thing that can
authorise new capital, and no AI code can bypass it. These tests pin that claim
down against the real shipped limits in config.RiskLimits.
"""
import pytest

from conftest import make_event, make_proposal, make_snapshot
from decision.decision_schema import ActionType, RegimeType, RiskVerdictType
from risk.risk_guardian import RiskGuardian


@pytest.fixture
def guardian(limits):
    return RiskGuardian(limits)


def evaluate(guardian, *, proposal=None, event=None, regime=RegimeType.NORMAL,
             snapshot=None, emergency_stop=False, adaptive_risk_factor=1.0):
    return guardian.evaluate(
        proposal or make_proposal(),
        event or make_event(),
        regime,
        snapshot or make_snapshot(),
        emergency_stop=emergency_stop,
        adaptive_risk_factor=adaptive_risk_factor,
    )


# --- the happy path -------------------------------------------------------

def test_approves_a_proposal_inside_every_limit(guardian):
    verdict = evaluate(guardian)

    assert verdict.verdict is RiskVerdictType.APPROVE
    assert verdict.approved_allocation == 10_000.0
    assert verdict.original_allocation == 10_000.0


# --- hard rejections ------------------------------------------------------

def test_emergency_stop_blocks_all_new_exposure(guardian):
    verdict = evaluate(guardian, emergency_stop=True)

    assert verdict.verdict is RiskVerdictType.REJECT
    assert verdict.approved_allocation == 0.0


def test_crisis_regime_blocks_new_positions(guardian):
    verdict = evaluate(guardian, regime=RegimeType.CRISIS)

    assert verdict.verdict is RiskVerdictType.REJECT
    assert verdict.approved_allocation == 0.0


def test_daily_loss_limit_blocks_new_positions(guardian, limits):
    snapshot = make_snapshot(daily_pnl_pct=-limits.max_daily_loss_pct)

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.REJECT
    assert "Daily loss limit" in verdict.reasons[0]


def test_illiquid_market_is_rejected(guardian, limits):
    event = make_event(liquidity=limits.min_liquidity_score - 0.05)

    verdict = evaluate(guardian, event=event)

    assert verdict.verdict is RiskVerdictType.REJECT
    assert "Liquidity" in verdict.reasons[0]


def test_position_count_limit_blocks_a_new_asset(guardian, limits):
    snapshot = make_snapshot(
        open_position_count=limits.max_position_count,
        has_position_in_asset=False,
    )

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.REJECT


def test_position_count_limit_does_not_block_adding_to_a_held_asset(guardian, limits):
    """The cap is on how many positions exist, not on topping one up."""
    snapshot = make_snapshot(
        open_position_count=limits.max_position_count,
        has_position_in_asset=True,
    )

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is not RiskVerdictType.REJECT


def test_rejects_when_no_capital_room_remains(guardian):
    """Asset already at its 25% cap: there is nothing left to allocate."""
    snapshot = make_snapshot(exposure_by_asset={"TCS": 25_000.0})

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.REJECT
    assert verdict.approved_allocation == 0.0


# --- modifications (the allocation gets cut down) -------------------------

def test_caps_at_max_single_trade(guardian, limits):
    proposal = make_proposal(allocation=30_000.0)

    verdict = evaluate(guardian, proposal=proposal)

    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == limits.max_single_trade
    assert verdict.original_allocation == 30_000.0


def test_caps_at_remaining_single_asset_exposure_room(guardian):
    """25% of 100,000 is 25,000; 20,000 is already held, so 5,000 is left."""
    snapshot = make_snapshot(exposure_by_asset={"TCS": 20_000.0})

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == 5_000.0


def test_caps_at_remaining_total_portfolio_exposure_room(guardian):
    """80% of 100,000 is 80,000; 78,000 is deployed, so 2,000 is left."""
    snapshot = make_snapshot(total_exposure=78_000.0, available_cash=50_000.0)

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == 2_000.0


def test_never_allocates_more_cash_than_is_available(guardian):
    snapshot = make_snapshot(available_cash=3_000.0)

    verdict = evaluate(guardian, snapshot=snapshot)

    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == 3_000.0


@pytest.mark.parametrize(
    "regime, expected",
    [
        (RegimeType.HIGH_VOLATILITY, 5_000.0),   # halved
        (RegimeType.LOW_LIQUIDITY, 5_000.0),     # halved
        (RegimeType.EVENT_DRIVEN, 7_500.0),      # reduced 25%
    ],
)
def test_hostile_regimes_shrink_the_position(guardian, regime, expected):
    verdict = evaluate(guardian, regime=regime)

    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == expected


# --- interaction with the Adaptation Engine -------------------------------

def test_adaptation_can_tighten_the_guardians_own_limits(guardian):
    """risk_tightening_factor scales the Guardian's own limits, not just the
    size the agent asked for: at 50% the 20,000 single-trade cap becomes
    10,000, so a 15,000 request that would otherwise have been approved
    outright is cut down instead."""
    proposal = make_proposal(allocation=15_000.0)

    approved_untightened = evaluate(guardian, proposal=proposal)
    verdict = evaluate(guardian, proposal=proposal, adaptive_risk_factor=0.5)

    assert approved_untightened.verdict is RiskVerdictType.APPROVE
    assert verdict.verdict is RiskVerdictType.MODIFY
    assert verdict.approved_allocation == 10_000.0
    assert any("tightened" in r for r in verdict.reasons)


# --- exits are never blocked ---------------------------------------------

@pytest.mark.parametrize("action", [ActionType.HOLD, ActionType.WAIT, ActionType.SELL,
                                    ActionType.REDUCE_EXPOSURE, ActionType.STOP_NEW_POSITIONS])
def test_actions_that_risk_no_new_capital_are_always_approved(guardian, action):
    """Emergency stop and CRISIS block new exposure, but must not trap the
    system in its existing positions -- selling out stays available."""
    proposal = make_proposal(action=action, allocation=0.0)

    verdict = evaluate(
        guardian, proposal=proposal, regime=RegimeType.CRISIS, emergency_stop=True,
    )

    assert verdict.verdict is RiskVerdictType.APPROVE
    assert verdict.reasons == ["No new capital at risk"]


def test_known_gap_crisis_rejection_is_unreachable_for_a_self_restrained_agent(guardian):
    """Characterisation test for HANDOFF.md issue #2.

    In CRISIS the agents already downgrade themselves to STOP_NEW_POSITIONS,
    which requests no capital -- so the Guardian returns early and its CRISIS
    branch never runs. The branch is dead code, not a hole: nothing is
    approved that spends money. If agent behaviour in CRISIS ever changes,
    this test breaks and the branch becomes live again.
    """
    proposal = make_proposal(action=ActionType.STOP_NEW_POSITIONS, allocation=0.0)
    verdict = evaluate(guardian, proposal=proposal, regime=RegimeType.CRISIS)

    assert verdict.verdict is RiskVerdictType.APPROVE
    assert verdict.approved_allocation == 0.0
