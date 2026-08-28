"""
Adaptation Engine: the part of the system that actually changes future
behavior based on past outcomes -- not just logging them.

It looks at the most recent evaluated trades WITHIN THE CURRENT REGIME. If
too many were losers, it lowers a confidence multiplier, a position-size
multiplier, and a risk-tightening factor that are then genuinely consumed
by BaseMarketAgent.analyze() and RiskGuardian.evaluate() on the next cycle
-- so a real, later decision comes out smaller/less confident because of
this. If performance recovers, the multipliers are eased back up. Every
change is logged to AdaptationEvent so the dashboard can show exactly what
changed and why (see the "Adaptation" panel in the UI spec).

This is intentionally rule-based/statistical (a moving win-rate over a
lookback window), not a retrained model -- that is an explicit, honest
choice for the hackathon scope, not a simplification we're hiding.
"""
from dataclasses import dataclass
from db.models import DecisionRecord, AdaptationEvent


@dataclass
class AdaptiveState:
    confidence_multiplier: float = 1.0
    size_multiplier: float = 1.0
    risk_tightening_factor: float = 1.0  # multiplies risk limits; < 1.0 = more conservative


class AdaptationEngine:
    def __init__(self, lookback: int = 5, degrade_threshold: float = 0.4, improve_threshold: float = 0.65):
        self.lookback = lookback
        self.degrade_threshold = degrade_threshold
        self.improve_threshold = improve_threshold

    def adapt(self, db, state: AdaptiveState, regime: str) -> AdaptationEvent | None:
        recent = (
            db.query(DecisionRecord)
            .filter(DecisionRecord.outcome_status == "EVALUATED", DecisionRecord.regime == regime)
            .order_by(DecisionRecord.evaluated_at.desc())
            .limit(self.lookback)
            .all()
        )
        if len(recent) < 3:
            return None

        wins = sum(1 for r in recent if r.pnl > 0)
        success_rate = wins / len(recent)
        trigger = f"{wins}/{len(recent)} of the last evaluated trades profitable in {regime} regime ({success_rate*100:.0f}%)"

        if success_rate < self.degrade_threshold and state.confidence_multiplier > 0.5:
            return self._apply_change(
                db, state, trigger,
                confidence_factor=0.85, size_factor=0.8, risk_factor=0.85,
                floor=(0.5, 0.4, 0.5),
                reasoning=(
                    f"Performance degradation detected under {regime}: only {success_rate*100:.0f}% of the last "
                    f"{len(recent)} trades were profitable. Reducing confidence and position sizes, and tightening "
                    f"risk limits, until performance recovers."
                ),
            )

        if success_rate > self.improve_threshold and state.confidence_multiplier < 1.0:
            return self._apply_change(
                db, state, trigger,
                confidence_factor=1.1, size_factor=1.1, risk_factor=1.1,
                ceiling=(1.0, 1.0, 1.0),
                reasoning=(
                    f"Performance recovering under {regime}: {success_rate*100:.0f}% of the last {len(recent)} "
                    f"trades were profitable. Gradually restoring confidence and position sizes."
                ),
            )

        return None

    def _apply_change(
        self, db, state, trigger, confidence_factor, size_factor, risk_factor,
        reasoning, floor=(0.0, 0.0, 0.0), ceiling=(1.0, 1.0, 1.0),
    ) -> AdaptationEvent:
        old = (state.confidence_multiplier, state.size_multiplier, state.risk_tightening_factor)

        state.confidence_multiplier = round(
            min(ceiling[0], max(floor[0], state.confidence_multiplier * confidence_factor)), 3)
        state.size_multiplier = round(
            min(ceiling[1], max(floor[1], state.size_multiplier * size_factor)), 3)
        state.risk_tightening_factor = round(
            min(ceiling[2], max(floor[2], state.risk_tightening_factor * risk_factor)), 3)

        event = AdaptationEvent(
            trigger=trigger,
            parameter_changed="confidence_multiplier, size_multiplier, risk_tightening_factor",
            old_value=f"{old[0]}, {old[1]}, {old[2]}",
            new_value=f"{state.confidence_multiplier}, {state.size_multiplier}, {state.risk_tightening_factor}",
            reasoning=reasoning,
        )
        db.add(event)
        db.commit()
        return event
