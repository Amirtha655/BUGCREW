"""
Decision Coordinator: combines the per-asset proposals from specialized
agents in one cycle and resolves cross-market conflicts before anything
reaches the Risk Guardian.

Kept intentionally small and explicit (one real correlation rule, clearly
labeled as a heuristic) rather than a fake "cross-market model" -- this is
enough to demonstrate genuine cross-agent coordination without pretending
to be more sophisticated than it is.
"""
from decision.decision_schema import DecisionProposal, ActionType

USD_LINKED_COMMODITIES = {"GOLD", "SILVER"}
USD_ASSET = "USD/INR"


class DecisionCoordinator:
    def coordinate(self, proposals: list[DecisionProposal]) -> list[DecisionProposal]:
        usd_proposal = next((p for p in proposals if p.asset == USD_ASSET), None)
        if usd_proposal is None:
            return proposals

        usd_strength = 0.0
        if usd_proposal.action in (ActionType.BUY, ActionType.INCREASE_EXPOSURE):
            usd_strength = usd_proposal.confidence
        elif usd_proposal.action in (ActionType.SELL, ActionType.REDUCE_EXPOSURE):
            usd_strength = -usd_proposal.confidence

        if abs(usd_strength) < 0.4:
            return proposals

        for p in proposals:
            if p.asset not in USD_LINKED_COMMODITIES:
                continue
            gold_bullish = p.action in (ActionType.BUY, ActionType.INCREASE_EXPOSURE)
            if usd_strength > 0 and gold_bullish:
                old_conf = p.confidence
                p.confidence = round(max(0.05, p.confidence * 0.75), 3)
                p.reasoning += (
                    f" Cross-market note: {USD_ASSET} shows strong bullish momentum "
                    f"({usd_proposal.confidence * 100:.0f}% confidence), which typically pressures "
                    f"{p.asset} -- confidence adjusted from {old_conf*100:.0f}% to {p.confidence*100:.0f}%."
                )
                p.factors.append(f"Cross-market: strong {USD_ASSET} typically pressures {p.asset}")
            elif usd_strength < 0 and gold_bullish:
                old_conf = p.confidence
                p.confidence = round(min(0.95, p.confidence * 1.10), 3)
                p.reasoning += (
                    f" Cross-market note: {USD_ASSET} weakness reinforces the bullish case for "
                    f"{p.asset} -- confidence adjusted from {old_conf*100:.0f}% to {p.confidence*100:.0f}%."
                )
                p.factors.append(f"Cross-market: weak {USD_ASSET} supportive of {p.asset}")
        return proposals
