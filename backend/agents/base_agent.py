"""
Shared decision engine for every specialized market agent.

Each subclass only supplies WHAT signals matter for its market and HOW
much each one is weighted (see equity_agent.py / forex_agent.py /
commodity_agent.py for the actual specialization). This base class turns
those signals into a bounded score, a bounded score into an action +
confidence, and packages everything into a DecisionProposal.

The numeric decision is 100% deterministic (no LLM in this path) so it is
always reproducible and auditable -- see ai/provider_interface.py for why.
"""
from decision.decision_schema import (
    MarketEvent, DecisionProposal, ActionType, MarketType, RegimeType,
)
from ai.provider_interface import AIProvider


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class BaseMarketAgent:
    market_type: MarketType = None
    max_daily_move_pct: float = 0.03  # used to scale "expected return" from the score

    def __init__(self, provider: AIProvider):
        self.provider = provider

    # ---- subclasses must implement these ----
    def extract_signals(self, event: MarketEvent) -> dict:
        raise NotImplementedError

    def weights(self) -> dict:
        raise NotImplementedError

    def factor_labels(self, event: MarketEvent, signals: dict) -> list[str]:
        raise NotImplementedError

    def risk_labels(self, event: MarketEvent, signals: dict, regime: RegimeType) -> list[str]:
        raise NotImplementedError

    # ---- shared pipeline ----
    def analyze(
        self,
        event: MarketEvent,
        regime: RegimeType,
        memory_hint: dict,
        available_capital: float,
        has_position: bool,
        adaptive_confidence_mult: float = 1.0,
        adaptive_size_mult: float = 1.0,
    ) -> DecisionProposal:
        signals = self.extract_signals(event)
        w = self.weights()
        score = clamp(sum(signals.get(k, 0.0) * w.get(k, 0.0) for k in w), -1.0, 1.0)

        action, confidence = self._decide_action(score, regime, has_position)
        confidence = self._apply_memory_adjustment(confidence, memory_hint)
        confidence = clamp(confidence * adaptive_confidence_mult, 0.05, 0.95)

        base_pct = clamp(0.04 + confidence * 0.22, 0.0, 0.30) * adaptive_size_mult
        can_size_up = action in (ActionType.BUY, ActionType.INCREASE_EXPOSURE)
        suggested_allocation = round(available_capital * base_pct, 2) if can_size_up else 0.0

        expected_risk = round(clamp(event.volatility * (1.15 - event.liquidity), 0.01, 0.99), 3)
        expected_return_pct = round(score * self.max_daily_move_pct * 100, 2)
        strategy_tag = self._strategy_tag(score, event)

        factors = self.factor_labels(event, signals)
        risk_factors = self.risk_labels(event, signals, regime)
        if adaptive_confidence_mult < 0.98 or adaptive_size_mult < 0.98:
            risk_factors = risk_factors + [
                f"Adaptation engine has scaled confidence x{adaptive_confidence_mult:.2f} and "
                f"position size x{adaptive_size_mult:.2f} due to recent underperformance in this regime"
            ]
        reasoning = self._template_reasoning(event, action, confidence, factors, risk_factors, regime)

        rule_based = {
            "action": action.value,
            "confidence": confidence,
            "suggested_allocation": suggested_allocation,
            "expected_risk": expected_risk,
            "expected_return_pct": expected_return_pct,
            "strategy_tag": strategy_tag,
            "reasoning": reasoning,
            "factors": factors,
            "risk_factors": risk_factors,
        }

        enriched = self._safe_enrich(event, signals, rule_based, regime, memory_hint)

        return DecisionProposal(
            asset=event.asset,
            market_type=self.market_type,
            action=action,
            confidence=round(confidence, 3),
            reasoning=enriched["reasoning"],
            suggested_allocation=suggested_allocation,
            expected_risk=expected_risk,
            expected_return_pct=expected_return_pct,
            strategy_tag=strategy_tag,
            ai_provider_used=enriched.get("provider_used", self.provider.name),
            factors=enriched["factors"],
            risk_factors=enriched["risk_factors"],
        )

    def _safe_enrich(self, event, signals, rule_based, regime, memory_hint) -> dict:
        try:
            result = self.provider.enrich(
                event=event, market_type=self.market_type, signals=signals,
                rule_based=rule_based, regime=regime, memory_hint=memory_hint,
            )
            if not result or "reasoning" not in result:
                raise ValueError("provider returned malformed result")
            return result
        except Exception:
            return {
                "reasoning": rule_based["reasoning"],
                "factors": rule_based["factors"],
                "risk_factors": rule_based["risk_factors"],
                "provider_used": "rule_based",
            }

    def _decide_action(self, score: float, regime: RegimeType, has_position: bool):
        if regime == RegimeType.CRISIS:
            action = ActionType.REDUCE_EXPOSURE if has_position else ActionType.STOP_NEW_POSITIONS
            return action, 0.85
        if score >= 0.55:
            return (ActionType.INCREASE_EXPOSURE if has_position else ActionType.BUY), clamp(abs(score), 0.05, 0.95)
        if score >= 0.20:
            return (ActionType.HOLD if has_position else ActionType.BUY), clamp(abs(score), 0.05, 0.95)
        if score > -0.20:
            return ActionType.HOLD, clamp(0.5 - abs(score), 0.05, 0.6)
        if score > -0.55:
            return (ActionType.REDUCE_EXPOSURE if has_position else ActionType.WAIT), clamp(abs(score), 0.05, 0.95)
        return (ActionType.SELL if has_position else ActionType.WAIT), clamp(abs(score), 0.05, 0.95)

    def _apply_memory_adjustment(self, confidence: float, memory_hint: dict) -> float:
        success_rate = (memory_hint or {}).get("success_rate")
        if success_rate is None:
            return confidence
        if success_rate < 0.4:
            return clamp(confidence * 0.7, 0.05, 0.95)
        if success_rate > 0.65:
            return clamp(confidence * 1.1, 0.05, 0.95)
        return confidence

    def _strategy_tag(self, score: float, event: MarketEvent) -> str:
        trend = "momentum" if abs(score) > 0.3 else "mean_reversion"
        vol = "high_volatility" if event.volatility > 0.035 else "low_volatility"
        return f"{trend}_{vol}"

    def _template_reasoning(self, event, action, confidence, factors, risk_factors, regime) -> str:
        f = "; ".join(factors) if factors else "no strong signals"
        r = "; ".join(risk_factors) if risk_factors else "no elevated risks"
        return (
            f"Proposing {action.value} on {event.asset} with {confidence * 100:.0f}% confidence. "
            f"Key factors: {f}. Market regime is {regime.value}. Risk considerations: {r}."
        )
