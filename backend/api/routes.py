import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from config import settings
from db.session import SessionLocal, reset_all
from db.models import DecisionRecord, AdaptationEvent
from engine import AutonomousLoop
from scenarios.scenario_definitions import list_scenarios, get_scenario

router = APIRouter(prefix="/api")


def iso_utc(dt: datetime | None) -> str:
    """Timestamps are stored as naive UTC. Emit them with an explicit UTC
    offset so browsers do not misread them as local time -- without this the
    REST history and the live WebSocket feed disagree by the local offset."""
    if dt is None:
        return ""
    return dt.replace(tzinfo=timezone.utc).isoformat()


class EmergencyStopBody(BaseModel):
    enable: bool


class ScenarioLoadBody(BaseModel):
    reset: bool = True


class SpeedBody(BaseModel):
    cycle_interval_seconds: float


@router.get("/status")
def status(request: Request):
    loop: AutonomousLoop = request.app.state.loop
    return {
        "running": request.app.state.running,
        "cycle": loop.cycle_number,
        "ai_provider": loop.provider_name,
        "emergency_stop": settings.emergency_stop,
        "active_scenario": loop.active_scenario["name"] if loop.active_scenario else None,
        "cycle_interval_seconds": settings.cycle_interval_seconds,
        "starting_capital": settings.starting_capital,
        "risk_limits": vars(settings.risk),
    }


@router.post("/control/start")
async def start(request: Request):
    app = request.app
    if not app.state.running:
        app.state.running = True
        app.state.loop_task = asyncio.create_task(_run_loop(app))
    return {"running": True}


@router.post("/control/stop")
def stop(request: Request):
    request.app.state.running = False
    return {"running": False}


@router.post("/control/step")
async def step(request: Request):
    loop: AutonomousLoop = request.app.state.loop
    result = loop.run_cycle()
    await request.app.state.ws_manager.broadcast(result)
    return result


@router.post("/control/emergency-stop")
def emergency_stop(body: EmergencyStopBody):
    settings.emergency_stop = body.enable
    return {"emergency_stop": settings.emergency_stop}


@router.post("/control/speed")
def set_speed(body: SpeedBody):
    """Changes how fast the autonomous loop cycles. The running loop reads
    this value between cycles, so a change takes effect on the next tick."""
    settings.cycle_interval_seconds = max(0.5, min(20.0, body.cycle_interval_seconds))
    return {"cycle_interval_seconds": settings.cycle_interval_seconds}


@router.post("/control/reset")
def reset(request: Request):
    """Wipes portfolio, trades, memory and adaptation back to a clean start,
    keeping whichever scenario is currently loaded."""
    app = request.app
    app.state.running = False
    current = app.state.loop.active_scenario
    reset_all()
    new_loop = AutonomousLoop()
    if current:
        new_loop.load_scenario(current)
    app.state.loop = new_loop
    return {"reset": True, "active_scenario": current["name"] if current else None}


@router.get("/scenarios")
def scenarios():
    return [
        {"name": s["name"], "title": s["title"], "description": s["description"], "duration_cycles": s["duration_cycles"]}
        for s in list_scenarios()
    ]


@router.post("/scenarios/{name}/load")
def load_scenario(name: str, request: Request, body: ScenarioLoadBody = ScenarioLoadBody()):
    scenario = get_scenario(name)
    if scenario is None:
        raise HTTPException(404, f"Unknown scenario '{name}'")

    app = request.app
    app.state.running = False  # pause the loop while we swap state under it

    if body.reset:
        reset_all()

    new_loop = AutonomousLoop()
    new_loop.load_scenario(scenario)
    app.state.loop = new_loop
    return {"loaded": name, "reset": body.reset}


@router.post("/scenarios/clear")
def clear_scenario(request: Request):
    loop: AutonomousLoop = request.app.state.loop
    loop.clear_scenario()
    return {"cleared": True}


@router.get("/portfolio")
def portfolio(request: Request):
    loop: AutonomousLoop = request.app.state.loop
    db = SessionLocal()
    try:
        price_lookup = {a: loop.data_engine.current_price(a) for a in loop.data_engine.assets()}
        return loop.portfolio_manager.snapshot(db, price_lookup)
    finally:
        db.close()


@router.get("/decisions")
def decisions(limit: int = 50):
    db = SessionLocal()
    try:
        rows = (
            db.query(DecisionRecord)
            .order_by(DecisionRecord.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id, "cycle_number": r.cycle_number, "timestamp": iso_utc(r.timestamp),
                "asset": r.asset, "market_type": r.market_type, "regime": r.regime,
                "action": r.proposed_action, "confidence": r.confidence, "reasoning": r.reasoning,
                "risk_verdict": r.risk_verdict, "risk_reasons": r.risk_reasons,
                "final_allocation": r.final_allocation, "executed": r.executed,
                "execution_price": r.execution_price, "execution_quantity": r.execution_quantity,
                "outcome_status": r.outcome_status, "actual_return_pct": r.actual_return_pct,
                "expected_return_pct": r.expected_return_pct, "pnl": r.pnl,
                "outcome_summary": r.outcome_summary, "ai_provider_used": r.ai_provider_used,
                "strategy_tag": r.strategy_tag,
                # Needed by the Risk and Execution pages to show history, not just live cycles.
                "proposed_allocation": r.proposed_allocation,
                "risk_adjusted_allocation": r.risk_adjusted_allocation,
                "allocation_reasoning": r.allocation_reasoning,
                "slippage_pct": r.slippage_pct, "transaction_cost": r.transaction_cost,
                "expected_risk": r.expected_risk, "event_description": r.event_description,
                "price": r.price, "volatility": r.volatility, "liquidity": r.liquidity,
            }
            for r in rows
        ]
    finally:
        db.close()


@router.get("/strategy-performance")
def strategy_performance(request: Request):
    loop: AutonomousLoop = request.app.state.loop
    db = SessionLocal()
    try:
        return loop.strategy_memory.leaderboard(db)
    finally:
        db.close()


@router.get("/adaptation-events")
def adaptation_events(limit: int = 20):
    db = SessionLocal()
    try:
        rows = db.query(AdaptationEvent).order_by(AdaptationEvent.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "timestamp": iso_utc(r.timestamp), "trigger": r.trigger,
                "parameter_changed": r.parameter_changed, "old_value": r.old_value,
                "new_value": r.new_value, "reasoning": r.reasoning,
            }
            for r in rows
        ]
    finally:
        db.close()


async def _run_loop(app):
    while app.state.running:
        loop: AutonomousLoop = app.state.loop
        result = loop.run_cycle()
        await app.state.ws_manager.broadcast(result)
        await asyncio.sleep(settings.cycle_interval_seconds)
