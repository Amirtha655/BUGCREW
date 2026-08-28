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
- Seven replayable demo scenarios, including a normal market, a sudden shock
  (regime flips to CRISIS), repeated losses that trigger visible adaptation,
  a liquidity drop, and a concentration limit being hit.

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

### 3. Tests

The Risk Guardian and the Adaptation Engine -- the safety claim and the
autonomy claim -- are covered by unit tests:

```bash
cd backend
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
```

Type-check the frontend with `npx tsc --noEmit -p tsconfig.app.json`.

### 4. Using the dashboard

The UI is a ten-page operations console. The sidebar covers **Overview,
Markets, Agents, Portfolio, Risk Controls, Decisions, Execution, Adaptation,
Activity** and **Settings**; the simulation controls (Start / Pause / Step /
Reset / Speed / Emergency Stop) sit in the top bar on every page.

1. Go to **Settings** and pick a scenario. Loading one resets the portfolio
   and loads a scripted sequence of events.
2. **Start** runs the loop continuously; **Step** advances exactly one cycle
   for a controlled walkthrough.
3. **Decisions** shows the full pipeline for any single decision -- what the
   agent proposed, what the Risk Guardian did to it, what was allocated, and
   what was executed.
4. **Emergency Stop** immediately blocks all new positions system-wide
   (existing positions can still be exited).

A good walkthrough:

- **Settings -> "Safety Limit Reached" -> Start.** Risk Controls shows a
  proposal being cut down, then refused outright.
- **Settings -> "Strategy Underperformance" -> Start**, wait ~40s. Adaptation
  shows the before/after settings and why they changed.
- **Settings -> "Sudden Price Shock" -> Start.** Overview flips to Crisis and
  the agents stand down.

Note that each cycle makes one LLM call per asset, so with a Groq key
configured a cycle takes several seconds regardless of the speed setting.

## Environment variables (backend/.env)

- `AI_PROVIDER` — `groq` (default) or anything else to force rule-based only.
- `GROQ_API_KEY` — optional, free key from console.groq.com.
- `GROQ_MODEL` — defaults to `openai/gpt-oss-120b`.
- `DATABASE_URL` — defaults to a local SQLite file, no setup needed.
