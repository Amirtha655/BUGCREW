"""
The Autonomous Loop.

Observe -> Understand -> Reason -> Identify opportunity -> Assess risk ->
Allocate capital -> Execute -> Observe outcome -> Evaluate performance ->
Adapt -> Observe again.

This is the one place that wires every other module together into a single
runnable cycle, and holds the small bits of in-memory state that aren't
worth persisting for a hackathon prototype (which cycle we're on, the
adaptive multipliers per regime, and the active demo scenario).
"""
import random
from datetime import datetime, timezone

from config import settings
from db.session import SessionLocal
from db.models import DecisionRecord
from decision.decision_schema import MarketType, RegimeType, ActionType
from market.data_engine import MarketDataEngine, DEFAULT_ASSET_UNIVERSE
from market.market_router import MarketRouter
from market.regime_detector import RegimeDetector
from agents.equity_agent import EquityAgent
from agents.forex_agent import ForexAgent
from agents.commodity_agent import CommodityAgent
from ai.provider_interface import get_provider
from decision.coordinator import DecisionCoordinator
from risk.risk_guardian import RiskGuardian
from portfolio.capital_allocator import CapitalAllocator, AllocationCandidate
from portfolio.portfolio_manager import PortfolioManager
from execution.paper_executor import PaperExecutionEngine
from feedback.strategy_memory import StrategyMemory
from feedback.performance_monitor import PerformanceMonitor
from feedback.adaptation_engine import AdaptationEngine, AdaptiveState

NEW_EXPOSURE_ACTIONS = {ActionType.BUY, ActionType.INCREASE_EXPOSURE}
EXIT_ACTIONS = {ActionType.SELL, ActionType.REDUCE_EXPOSURE}

REGIME_SEVERITY = [
    RegimeType.CRISIS, RegimeType.HIGH_VOLATILITY, RegimeType.EVENT_DRIVEN,
    RegimeType.LOW_LIQUIDITY, RegimeType.TRENDING, RegimeType.NORMAL,
]


class AutonomousLoop:
    def __init__(self):
        provider = get_provider()
        self.provider_name = provider.name
        self.data_engine = MarketDataEngine(DEFAULT_ASSET_UNIVERSE)
        self.router = MarketRouter({
            MarketType.EQUITY: EquityAgent(provider),
            MarketType.FOREX: ForexAgent(provider),
            MarketType.COMMODITY: CommodityAgent(provider),
        })
        self.regime_detector = RegimeDetector(settings.risk)
        self.coordinator = DecisionCoordinator()
        self.risk_guardian = RiskGuardian(settings.risk)
        self.capital_allocator = CapitalAllocator()
        self.executor = PaperExecutionEngine()
        self.portfolio_manager = PortfolioManager(session_start_value=settings.starting_capital)
        self.strategy_memory = StrategyMemory()
        self.performance_monitor = PerformanceMonitor(evaluation_delay_cycles=3)
        self.adaptation_engine = AdaptationEngine()

        self.adaptive_states: dict[str, AdaptiveState] = {r.value: AdaptiveState() for r in RegimeType}
        self.cycle_number = 0
        self.running = False
        self.active_scenario: dict | None = None
        self.scenario_step = 0

    # ---- scenario control ----
    def load_scenario(self, scenario: dict) -> None:
        self.active_scenario = scenario
        self.scenario_step = 0

    def clear_scenario(self) -> None:
        self.active_scenario = None
        self.scenario_step = 0

    def _scripted_overrides_for_cycle(self) -> dict:
        """Returns {asset: override_dict} for any scripted events at this cycle."""
        if not self.active_scenario:
            return {}
        overrides = {}
        for step in self.active_scenario.get("events", []):
            if step["cycle"] == self.scenario_step:
                overrides[step["asset"]] = step
        return overrides

    def overall_regime(self, regimes: list[RegimeType]) -> RegimeType:
        for r in REGIME_SEVERITY:
            if r in regimes:
                return r
        return RegimeType.NORMAL

    # ---- one full cycle ----
    def run_cycle(self) -> dict:
        db = SessionLocal()
        try:
            self.cycle_number += 1
            scripted = self._scripted_overrides_for_cycle()

            events = {}
            regimes = {}
            for asset in self.data_engine.assets():
                step = scripted.get(asset)
                override = step.get("override") if step else None
                event = self.data_engine.tick(asset, override=override)
                regime = self.regime_detector.detect(event)
                events[asset] = event
                regimes[asset] = regime

            price_lookup = {a: e.price for a, e in events.items()}
            global_snapshot = self.portfolio_manager.snapshot(db, price_lookup)

            proposals = []
            proposal_meta = {}  # asset -> (event, regime, has_position)
            for asset, event in events.items():
                agent, market_type = self.router.route(event)
                regime = regimes[asset]
                has_position = asset in global_snapshot["exposure_by_asset"]
                adaptive = self.adaptive_states[regime.value]
                memory_hint = self._strategy_hint_preview(db, regime)

                proposal = agent.analyze(
                    event, regime, memory_hint,
                    available_capital=global_snapshot["available_cash"],
                    has_position=has_position,
                    adaptive_confidence_mult=adaptive.confidence_multiplier,
                    adaptive_size_mult=adaptive.size_multiplier,
                )
                proposals.append(proposal)
                proposal_meta[asset] = (event, regime, has_position)

            proposals = self.coordinator.coordinate(proposals)

            # --- risk guardian pass ---
            verdicts = {}
            for p in proposals:
                event, regime, has_position = proposal_meta[p.asset]
                snap = self.portfolio_manager.snapshot(db, price_lookup, asset_of_interest=p.asset)
                adaptive = self.adaptive_states[regime.value]
                verdict = self.risk_guardian.evaluate(
                    p, event, regime, snap,
                    emergency_stop=settings.emergency_stop,
                    adaptive_risk_factor=adaptive.risk_tightening_factor,
                )
                verdicts[p.asset] = verdict

            # --- capital allocator pass (batched across this cycle's new-exposure proposals) ---
            candidates = [
                AllocationCandidate(
                    asset=p.asset,
                    risk_approved_allocation=verdicts[p.asset].approved_allocation,
                    confidence=p.confidence,
                    expected_risk=p.expected_risk,
                )
                for p in proposals
                if p.action in NEW_EXPOSURE_ACTIONS and verdicts[p.asset].verdict.value != "REJECT"
            ]
            allocation_results = self.capital_allocator.allocate(candidates, global_snapshot["available_cash"])

            # --- execution + persistence ---
            trace = []
            evaluated_regimes_touched = set()
            for p in proposals:
                event, regime, has_position = proposal_meta[p.asset]
                verdict = verdicts[p.asset]

                if p.action in NEW_EXPOSURE_ACTIONS:
                    final_allocation = allocation_results.get(p.asset).final_allocation if p.asset in allocation_results else 0.0
                    alloc_reasoning = allocation_results.get(p.asset).reasoning if p.asset in allocation_results else []
                    current_qty = 0.0
                else:
                    final_allocation = 0.0
                    alloc_reasoning = []
                    current_qty = self.portfolio_manager.position_quantity(db, p.asset)

                execution = None
                if verdict.verdict.value != "REJECT":
                    execution = self.executor.execute(p, event, allocation=final_allocation, current_quantity=current_qty)
                    if execution.executed:
                        self.portfolio_manager.apply_execution(db, p, execution)

                record = DecisionRecord(
                    cycle_number=self.cycle_number,
                    asset=p.asset,
                    market_type=p.market_type.value,
                    price=event.price,
                    volatility=event.volatility,
                    liquidity=event.liquidity,
                    regime=regime.value,
                    event_description="; ".join(event.news) if event.news else "",
                    proposed_action=p.action.value,
                    confidence=p.confidence,
                    reasoning=p.reasoning,
                    proposed_allocation=p.suggested_allocation,
                    expected_risk=p.expected_risk,
                    expected_return_pct=p.expected_return_pct,
                    strategy_tag=p.strategy_tag,
                    ai_provider_used=p.ai_provider_used,
                    risk_verdict=verdict.verdict.value,
                    risk_reasons="; ".join(verdict.reasons),
                    risk_adjusted_allocation=verdict.approved_allocation,
                    final_allocation=final_allocation,
                    allocation_reasoning="; ".join(alloc_reasoning),
                    executed=bool(execution and execution.executed),
                    execution_price=execution.execution_price if execution else 0.0,
                    execution_quantity=execution.execution_quantity if execution else 0.0,
                    slippage_pct=execution.slippage_pct if execution else 0.0,
                    transaction_cost=execution.transaction_cost if execution else 0.0,
                    # Only an actually-executed trade has an outcome to evaluate later.
                    # HOLD/WAIT/rejected proposals never opened a position, so they must
                    # NOT count as wins or losses in Strategy Memory / Adaptation Engine.
                    outcome_status="PENDING" if (execution and execution.executed) else "SKIPPED",
                )
                db.add(record)
                trace.append({
                    "asset": p.asset,
                    "market_type": p.market_type.value,
                    "regime": regime.value,
                    "event": {
                        "price": event.price,
                        "price_change_pct": event.price_change_pct,
                        "volatility": event.volatility,
                        "liquidity": event.liquidity,
                        "news": event.news,
                    },
                    "proposal": {
                        "action": p.action.value,
                        "confidence": p.confidence,
                        "reasoning": p.reasoning,
                        "suggested_allocation": p.suggested_allocation,
                        "expected_risk": p.expected_risk,
                        "expected_return_pct": p.expected_return_pct,
                        "strategy_tag": p.strategy_tag,
                        "ai_provider_used": p.ai_provider_used,
                        "factors": p.factors,
                        "risk_factors": p.risk_factors,
                    },
                    "risk_verdict": {
                        "verdict": verdict.verdict.value,
                        "approved_allocation": verdict.approved_allocation,
                        "reasons": verdict.reasons,
                    },
                    "allocation": {"final_allocation": final_allocation, "reasoning": alloc_reasoning},
                    "execution": (
                        {
                            "executed": execution.executed,
                            "execution_price": execution.execution_price,
                            "execution_quantity": execution.execution_quantity,
                            "slippage_pct": execution.slippage_pct,
                            "transaction_cost": execution.transaction_cost,
                            "note": execution.note,
                        }
                        if execution else {"executed": False, "note": "Rejected by Risk Guardian"}
                    ),
                })

            db.commit()

            # --- outcome monitoring ---
            # Adaptation is only re-run for a regime when a NEW outcome actually landed
            # this cycle -- otherwise it would re-punish the same historical trades on
            # every single cycle and the multipliers would ratchet down forever.
            newly_evaluated = self.performance_monitor.evaluate_due(
                db, self.cycle_number, price_lookup, self.strategy_memory
            )
            for rec in newly_evaluated:
                evaluated_regimes_touched.add(rec.regime)

            # --- adaptation ---
            adaptation_events = []
            for regime_value in evaluated_regimes_touched:
                state = self.adaptive_states[regime_value]
                event_row = self.adaptation_engine.adapt(db, state, regime_value)
                if event_row:
                    adaptation_events.append({
                        "regime": regime_value,
                        "trigger": event_row.trigger,
                        "reasoning": event_row.reasoning,
                        "parameter_changed": event_row.parameter_changed,
                        "old_value": event_row.old_value,
                        "new_value": event_row.new_value,
                    })

            final_snapshot = self.portfolio_manager.snapshot(db, price_lookup)
            self.scenario_step += 1

            return {
                "cycle": self.cycle_number,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "emergency_stop": settings.emergency_stop,
                "ai_provider": self.provider_name,
                "overall_regime": self.overall_regime(list(regimes.values())).value,
                "portfolio": final_snapshot,
                "trace": trace,
                "outcomes_evaluated": [
                    {"asset": r.asset, "strategy_tag": r.strategy_tag, "regime": r.regime,
                     "expected_return_pct": r.expected_return_pct, "actual_return_pct": r.actual_return_pct,
                     "pnl": r.pnl, "summary": r.outcome_summary}
                    for r in newly_evaluated
                ],
                "adaptation_events": adaptation_events,
                "adaptive_states": {k: vars(v) for k, v in self.adaptive_states.items()},
                "strategy_leaderboard": self.strategy_memory.leaderboard(db),
            }
        finally:
            db.close()

    def _strategy_hint_preview(self, db, regime: RegimeType) -> dict:
        """A generic memory hint before we know the exact strategy_tag (which
        depends on the score we haven't computed yet) -- gives agents a
        regime-level read on recent performance. Cheap approximation, good
        enough for a hackathon: we look up the most-traded strategy tag for
        this regime so far."""
        board = self.strategy_memory.leaderboard(db)
        for row in board:
            if row["regime"] == regime.value and row["total_trades"] > 0:
                return {"success_rate": row["success_rate"], "summary": f"{row['strategy_tag']} in {regime.value}: {row['success_rate']*100:.0f}% success rate"}
        return {"success_rate": None, "summary": "No history yet for this regime"}
