"""
Capital Allocation Engine.

Runs AFTER the Risk Guardian, across every proposal in the current cycle
that wants new exposure. Its job is different from the Risk Guardian's:
the Guardian answers "is this trade individually safe?", the Allocator
answers "given everything we want to do RIGHT NOW, how should the actual
cash be split up?". It never exceeds a proposal's risk-approved ceiling,
always keeps a cash reserve, and gives more room to higher-confidence,
lower-risk opportunities -- mirroring the worked example in the problem
statement (high confidence gets more, high risk gets less, cash is held back).
"""
from dataclasses import dataclass
from decision.decision_schema import AllocationResult


@dataclass
class AllocationCandidate:
    asset: str
    risk_approved_allocation: float
    confidence: float
    expected_risk: float


class CapitalAllocator:
    def __init__(self, cash_reserve_pct: float = 0.15):
        self.cash_reserve_pct = cash_reserve_pct

    def allocate(
        self, candidates: list[AllocationCandidate], available_cash: float
    ) -> dict[str, AllocationResult]:
        if not candidates:
            return {}

        investable = max(0.0, available_cash * (1 - self.cash_reserve_pct))
        weighted = [
            (c, c.confidence / (1.0 + c.expected_risk))
            for c in candidates
        ]
        total_weight = sum(w for _, w in weighted) or 1.0

        results: dict[str, AllocationResult] = {}
        remaining = investable
        for c, weight in weighted:
            share = investable * (weight / total_weight)
            final = min(c.risk_approved_allocation, share, remaining)
            final = round(max(0.0, final), 2)
            remaining -= final
            results[c.asset] = AllocationResult(
                final_allocation=final,
                reasoning=[
                    f"Confidence/risk-weighted share of investable capital: {share:,.0f}",
                    f"Capped at Risk Guardian ceiling: {c.risk_approved_allocation:,.0f}",
                    f"Cash reserve held back: {self.cash_reserve_pct*100:.0f}% of available capital",
                ],
            )
        return results
