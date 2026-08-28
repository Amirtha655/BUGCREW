# Autonomous AI Agents for Real-Time Financial Markets

A hackathon prototype of an autonomous, multi-agent, paper-trading system.
**No real money, no real orders, ever** — everything is simulated.

## What this demonstrates

The full loop: **Observe -> Understand -> Reason -> Identify opportunity ->
Assess risk -> Allocate capital -> Execute -> Observe outcome -> Evaluate
performance -> Adapt -> Observe again.**

- A **Market Router** identifies whether an event is Equity / Forex / Commodity
  and hands it to a specialized agent (`backend/market/market_router.py`).
- Three specialized agents (`backend/agents/`) each score the opportunity with
  market-specific factors and weights (deterministic, not an LLM).
- A **Decision Coordinator** resolves cross-market conflicts (e.g. USD strength
  vs. Gold) (`backend/decision/coordinator.py`).
- A **Risk Guardian** (`backend/risk/risk_guardian.py`) is the only thing that
  can actually authorize spending money — it APPROVES, REJECTS, or MODIFIES
  every proposal. The AI can never bypass it.
- A **Capital Allocator** splits available cash across everything the system
  wants to do this cycle, confidence/risk-weighted, with a cash reserve.
- A **Paper Execution Engine** simulates slippage and transaction cost.
- **Strategy Memory** + a real **Adaptation Engine** track win/loss history per
  (strategy, regime) and measurably shrink confidence/position size/risk
  limits after a run of losses — then restore them as performance recovers.
- Three replayable demo scenarios: a normal market, a sudden shock (regime
  flips to CRISIS), and repeated losses that trigger visible adaptation.

The AI layer (`backend/ai/`) never invents the action/confidence/allocation —
those numbers come from deterministic scoring. An LLM (Groq, free tier), if
configured, is used **only** to write a clearer natural-language explanation
of a decision that was already made. Without a Groq key, everything still
runs — it silently uses the built-in rule-based explanation templates instead.

## Project structure

```
/backend    Python + FastAPI. See backend/config.py for all tunable limits.
/frontend   React + TypeScript + Vite. Multi-page operations console,
            live over WebSocket. See HANDOFF.md for the UI architecture.
```

## Running it

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on macOS/Linux
```

Optional: copy `backend/.env.example` to `backend/.env` and add a free Groq
API key (get one at console.groq.com, no credit card needed) to get richer
LLM-written explanations. Not required — the system works without it.

```bash
cd backend
.venv/Scripts/python -m uvicorn main:app --port 8010 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (default `http://localhost:5173`).

### 3. Using the dashboard

1. Pick one of the three scenario buttons at the top (this resets the
   portfolio and loads a scripted sequence of events).
2. Click **Start Loop** to let it run continuously, or **Step Cycle** to
   advance one cycle at a time for a controlled walkthrough.
3. Click any row in **Agent Activity** to see the full WHAT / WHY / RISK /
   WHAT CHANGED / WHY APPROVED explanation for that decision.
4. **Emergency Stop** immediately blocks all new positions system-wide
   (existing positions can still be exited).

## Environment variables (backend/.env)

- `AI_PROVIDER` — `groq` (default) or anything else to force rule-based only.
- `GROQ_API_KEY` — optional, free key from console.groq.com.
- `GROQ_MODEL` — defaults to `openai/gpt-oss-120b`.
- `DATABASE_URL` — defaults to a local SQLite file, no setup needed.
