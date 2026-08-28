"""Adaptation Engine tests.

This is the project's autonomy claim: after a run of losses the system really
does change how it behaves next time, rather than only logging that it noticed.
These tests check the multipliers move, that they move in the right direction,
that they are bounded, and that the engine only counts trades it should.
"""
from db.models import AdaptationEvent
from decision.decision_schema import RegimeType
from feedback.adaptation_engine import AdaptationEngine, AdaptiveState

from conftest import add_outcome

NORMAL = RegimeType.NORMAL.value


def losing_run(db, n=5, regime=NORMAL):
    """n evaluated trades, all losses -- a 0% success rate."""
    for i in range(n):
        add_outcome(db, regime=regime, pnl=-500.0, age_seconds=n - i)


def winning_run(db, n=5, regime=NORMAL):
    for i in range(n):
        add_outcome(db, regime=regime, pnl=+500.0, age_seconds=n - i)


# --- it does nothing without evidence ------------------------------------

def test_does_not_adapt_on_an_empty_history(db):
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None
    assert state.confidence_multiplier == 1.0


def test_does_not_adapt_on_fewer_than_three_evaluated_trades(db):
    """Two losses is noise, not a pattern."""
    losing_run(db, n=2)
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None
    assert state.confidence_multiplier == 1.0


def test_ignores_trades_from_a_different_regime(db):
    """What happened in a crisis must not tighten normal-market behaviour."""
    losing_run(db, n=5, regime=RegimeType.CRISIS.value)
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None
    assert state.confidence_multiplier == 1.0


def test_ignores_non_executed_decisions(db):
    """HOLD/WAIT/rejected rows are SKIPPED, never EVALUATED -- counting them
    as losses is the bug recorded in HANDOFF.md section 5, which ratcheted
    the limits down forever."""
    for i in range(5):
        add_outcome(db, pnl=0.0, status="SKIPPED", age_seconds=5 - i)
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None
    assert state.confidence_multiplier == 1.0


def test_does_nothing_when_performance_is_merely_average(db):
    """3 of 5 profitable is 60%: below the improve threshold, above the
    degrade threshold -- the engine should sit still."""
    for i, pnl in enumerate([500.0, 500.0, 500.0, -500.0, -500.0]):
        add_outcome(db, pnl=pnl, age_seconds=5 - i)
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None


# --- degradation ----------------------------------------------------------

def test_a_run_of_losses_tightens_confidence_size_and_risk(db):
    losing_run(db)
    state = AdaptiveState()

    event = AdaptationEngine().adapt(db, state, NORMAL)

    assert event is not None
    assert state.confidence_multiplier == 0.85
    assert state.size_multiplier == 0.8
    assert state.risk_tightening_factor == 0.85


def test_degradation_is_recorded_with_before_and_after_values(db):
    losing_run(db)
    state = AdaptiveState()

    event = AdaptationEngine().adapt(db, state, NORMAL)

    assert event.old_value == "1.0, 1.0, 1.0"
    assert event.new_value == "0.85, 0.8, 0.85"
    assert "0/5" in event.trigger
    assert db.query(AdaptationEvent).count() == 1


def test_repeated_losses_keep_tightening_but_stop_at_the_floor(db):
    """Confidence must never collapse to zero -- the system stays able to
    recover once performance improves."""
    losing_run(db)
    state = AdaptiveState()
    engine = AdaptationEngine()

    for _ in range(20):
        engine.adapt(db, state, NORMAL)

    assert state.confidence_multiplier == 0.5
    assert state.size_multiplier >= 0.4
    assert state.risk_tightening_factor >= 0.5


# --- recovery -------------------------------------------------------------

def test_good_performance_restores_a_tightened_state(db):
    state = AdaptiveState(confidence_multiplier=0.5, size_multiplier=0.5,
                          risk_tightening_factor=0.5)
    winning_run(db)

    event = AdaptationEngine().adapt(db, state, NORMAL)

    assert event is not None
    assert state.confidence_multiplier == 0.55
    assert state.size_multiplier == 0.55
    assert state.risk_tightening_factor == 0.55


def test_recovery_never_exceeds_the_original_limits(db):
    """Winning does not earn the system more rope than it started with."""
    state = AdaptiveState(confidence_multiplier=0.98, size_multiplier=0.98,
                          risk_tightening_factor=0.98)
    winning_run(db)
    engine = AdaptationEngine()

    for _ in range(10):
        engine.adapt(db, state, NORMAL)

    assert state.confidence_multiplier == 1.0
    assert state.size_multiplier == 1.0
    assert state.risk_tightening_factor == 1.0


def test_does_not_adapt_upward_when_already_at_full_strength(db):
    winning_run(db)
    state = AdaptiveState()

    assert AdaptationEngine().adapt(db, state, NORMAL) is None


# --- the multipliers are the ones the rest of the system consumes ---------

def test_tightened_state_actually_shrinks_a_later_risk_decision(db):
    """End-to-end on the claim that adaptation changes real later decisions:
    feed the adapted risk factor into the Guardian and check the approved
    allocation drops."""
    from conftest import make_event, make_proposal, make_snapshot
    from config import RiskLimits
    from decision.decision_schema import RiskVerdictType
    from risk.risk_guardian import RiskGuardian

    losing_run(db)
    state = AdaptiveState()
    AdaptationEngine().adapt(db, state, NORMAL)

    guardian = RiskGuardian(RiskLimits())
    args = (make_proposal(allocation=18_000.0), make_event(), RegimeType.NORMAL,
            make_snapshot())

    before = guardian.evaluate(*args, emergency_stop=False, adaptive_risk_factor=1.0)
    after = guardian.evaluate(*args, emergency_stop=False,
                              adaptive_risk_factor=state.risk_tightening_factor)

    assert before.verdict is RiskVerdictType.APPROVE
    assert before.approved_allocation == 18_000.0
    assert after.verdict is RiskVerdictType.MODIFY
    assert after.approved_allocation == 17_000.0  # 20,000 cap x 0.85
    assert after.approved_allocation < before.approved_allocation
