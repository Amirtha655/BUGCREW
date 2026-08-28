"""
Risk Guardian: the single deterministic gate between any AI proposal and
real capital. No LLM code runs in this file. Every proposal that wants new
exposure passes through here and comes out APPROVED as-is, REJECTED, or
MODIFIED (allocation cut down). This is what makes it safe to let the AI
layer be creative -- it can never spend money the Risk Guardian didn't allow.
"""
from decision.decision_schema import (
    DecisionProposal, RiskVerdict, RiskVerdictType, ActionType, RegimeType, MarketEvent,
)
from config import RiskLimits

NEW_EXPOSURE_ACTIONS = {ActionType.BUY, ActionType.INCREASE_EXPOSURE}


class RiskGuardian:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def evaluate(
        self,
        proposal: DecisionProposal,
        event: MarketEvent,
        regime: RegimeType,
        portfolio_snapshot: dict,
        emergency_stop: bool,
        adaptive_risk_factor: float = 1.0,
    ) -> RiskVerdict:
        allocation = proposal.suggested_allocation

        if proposal.action not in NEW_EXPOSURE_ACTIONS or allocation <= 0:
            return RiskVerdict(RiskVerdictType.APPROVE, allocation, ["No new capital at risk"], allocation)

        if emergency_stop:
            return RiskVerdict(RiskVerdictType.REJECT, 0.0,
                                ["Emergency stop is active: no new positions allowed"], allocation)

        if regime == RegimeType.CRISIS:
            return RiskVerdict(RiskVerdictType.REJECT, 0.0,
                                ["Market regime is CRISIS: new positions blocked"], allocation)

        if portfolio_snapshot["daily_pnl_pct"] <= -self.limits.max_daily_loss_pct:
            return RiskVerdict(RiskVerdictType.REJECT, 0.0,
                                [f"Daily loss limit reached ({self.limits.max_daily_loss_pct*100:.0f}%): new positions blocked"],
                                allocation)

        if event.liquidity < self.limits.min_liquidity_score:
            return RiskVerdict(RiskVerdictType.REJECT, 0.0,
                                [f"Liquidity ({event.liquidity:.2f}) below minimum required ({self.limits.min_liquidity_score:.2f})"],
                                allocation)

        if (not portfolio_snapshot["has_position_in_asset"]
                and portfolio_snapshot["open_position_count"] >= self.limits.max_position_count):
            return RiskVerdict(RiskVerdictType.REJECT, 0.0,
                                [f"Max open position count reached ({self.limits.max_position_count})"], allocation)

        reasons: list[str] = []
        adjusted = allocation

        # The Adaptation Engine can make the Guardian itself more conservative
        # (< 1.0) after a run of losses in this regime -- a real risk-threshold
        # tightening, not just smaller AI-suggested sizes.
        effective_max_single_trade = self.limits.max_single_trade * adaptive_risk_factor
        effective_max_asset_pct = self.limits.max_asset_exposure_pct * adaptive_risk_factor
        effective_max_portfolio_pct = self.limits.max_portfolio_exposure_pct * adaptive_risk_factor
        if adaptive_risk_factor < 0.98:
            reasons.append(f"Risk limits tightened to {adaptive_risk_factor*100:.0f}% by Adaptation Engine")

        if adjusted > effective_max_single_trade:
            adjusted = effective_max_single_trade
            reasons.append(f"Reduced to max single-trade limit ({effective_max_single_trade:,.0f})")

        portfolio_value = portfolio_snapshot["portfolio_value"]
        current_asset_exposure = portfolio_snapshot["exposure_by_asset"].get(proposal.asset, 0.0)
        max_asset_allowed = portfolio_value * effective_max_asset_pct
        remaining_asset_room = max(0.0, max_asset_allowed - current_asset_exposure)
        if adjusted > remaining_asset_room:
            adjusted = remaining_asset_room
            reasons.append(f"Reduced to stay within max single-asset exposure ({effective_max_asset_pct*100:.0f}% of portfolio)")

        total_exposure = portfolio_snapshot["total_exposure"]
        max_portfolio_allowed = portfolio_value * effective_max_portfolio_pct
        remaining_portfolio_room = max(0.0, max_portfolio_allowed - total_exposure)
        if adjusted > remaining_portfolio_room:
            adjusted = remaining_portfolio_room
            reasons.append(f"Reduced to stay within max portfolio exposure ({self.limits.max_portfolio_exposure_pct*100:.0f}%)")

        available_cash = portfolio_snapshot["available_cash"]
        if adjusted > available_cash:
            adjusted = available_cash
            reasons.append("Reduced to available cash")

        if regime == RegimeType.HIGH_VOLATILITY:
            adjusted *= 0.5
            reasons.append("Position size halved: HIGH_VOLATILITY regime")
        elif regime == RegimeType.LOW_LIQUIDITY:
            adjusted *= 0.5
            reasons.append("Position size halved: LOW_LIQUIDITY regime")
        elif regime == RegimeType.EVENT_DRIVEN:
            adjusted *= 0.75
            reasons.append("Position size reduced 25%: EVENT_DRIVEN regime")

        adjusted = round(max(0.0, adjusted), 2)

        if adjusted <= 0:
            return RiskVerdict(RiskVerdictType.REJECT, 0.0, reasons or ["No capital room available"], allocation)
        if adjusted < allocation:
            return RiskVerdict(RiskVerdictType.MODIFY, adjusted, reasons, allocation)
        return RiskVerdict(RiskVerdictType.APPROVE, adjusted, ["All risk checks passed"], allocation)
