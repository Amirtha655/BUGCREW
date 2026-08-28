import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db.session import init_db
from engine import AutonomousLoop
from api.websocket import ConnectionManager
from api.routes import router as api_router

app = FastAPI(title="AutoChain — Autonomous Multi-Agent Market System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    init_db()
    app.state.loop = AutonomousLoop()
    app.state.running = False
    app.state.loop_task = None
    app.state.ws_manager = ConnectionManager()
    # Serialises cycles: the background loop and a manual /control/step can
    # never run one at the same time, and reset/scenario-load wait for any
    # in-flight cycle before swapping state.
    app.state.cycle_lock = asyncio.Lock()


@app.on_event("shutdown")
def on_shutdown():
    app.state.running = False


@app.get("/health")
def health():
    return {
        "status": "ok",
        "starting_capital": settings.starting_capital,
        "ai_provider": settings.ai_provider,
        "emergency_stop": settings.emergency_stop,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    manager: ConnectionManager = app.state.ws_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
