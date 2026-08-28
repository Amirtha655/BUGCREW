# HANDOFF

Context for whoever picks this project up next.

Project: **Autonomous AI Agents for Real-Time Financial Markets** — a hackathon
prototype of a self-directing, risk-controlled, paper-trading system.
Nothing here touches real money or a real broker.

Last updated: 2026-08-28, end of the stabilisation session
(previous entry: end of the frontend redesign session).

---

## 1. What has been built

### Backend (`/backend`) — Python 3.13 + FastAPI + SQLite
Complete and working. Implements the full autonomous loop:

> Observe → Understand → Reason → Identify opportunity → Assess risk →
> Allocate capital → Execute → Observe outcome → Evaluate → Adapt → repeat

| Component | File | What it does |
|---|---|---|
| Market data | `market/data_engine.py` | Simulated live prices (random walk) for 6 assets, with scripted event overrides |
| Market router | `market/market_router.py` | Decides which specialist agent handles an asset |
| Regime detector | `market/regime_detector.py` | Classifies conditions: NORMAL / TRENDING / HIGH_VOLATILITY / LOW_LIQUIDITY / EVENT_DRIVEN / CRISIS |
| Specialist agents | `agents/{equity,forex,commodity}_agent.py` | Market-specific signals + weights, on a shared base (`base_agent.py`) |
| Coordinator | `decision/coordinator.py` | Cross-market conflict resolution (USD strength vs. gold) |
| **Risk Guardian** | `risk/risk_guardian.py` | Deterministic APPROVE / MODIFY / REJECT. **No LLM code runs here.** |
| Capital allocator | `portfolio/capital_allocator.py` | Splits cash across a cycle's opportunities, confidence/risk-weighted, keeps a 15% reserve |
| Paper execution | `execution/paper_executor.py` | Simulated fills with slippage + transaction cost |
| Portfolio | `portfolio/portfolio_manager.py` | Cash, positions, exposure, P&L |
| Outcome monitor | `feedback/performance_monitor.py` | Grades trades ~3 cycles after execution |
| Strategy memory | `feedback/strategy_memory.py` | Win/loss tally per (strategy, regime) |
| **Adaptation engine** | `feedback/adaptation_engine.py` | Really changes future behaviour after losses |
| Orchestrator | `engine.py` | Wires one full cycle together |
| API | `api/routes.py`, `main.py` | REST + WebSocket |

### Frontend (`/frontend`) — React 19 + TypeScript + Vite
**Fully redesigned this session** from a single dense page into a 10-page
operations console styled as professional financial software.

---

## 2. Current architecture

### The AI boundary (important — do not blur this)
The LLM **never** decides anything financial. Action, confidence and money
amounts are all computed by deterministic scoring in `agents/base_agent.py`.
The LLM's only job is rewriting an already-final decision into readable
English (`ai/llm_provider.py`). If the API key is missing or the call fails,
it silently falls back to `ai/rule_based_provider.py` templates and the system
keeps running. The `ai_provider_used` field records which one actually ran, so
the UI never claims LLM involvement that did not happen.

### Frontend structure
```
src/
  main.tsx                    Hash router, 10 routes
  App.tsx                     Shell: topbar + compact sidebar + <Outlet/>
  state/SystemProvider.tsx    SINGLE SOURCE OF TRUTH (see below)
  services/api.ts             All REST calls
  components/
    ui/index.tsx              Panel, DataTable, StatTile, Badge, Meter, InfoLabel…
    PipelineFlow.tsx          The decision-stages story component
    SimulationControls.tsx    Start/Pause/Step/Reset/Speed/Scenario
  utils/
    vocab.ts                  ALL plain-English wording lives here
    format.ts                 Currency / percent / time formatting
  pages/                      Overview, Markets, Agents, Portfolio, Risk,
                              Decisions, Execution, Adaptation, Activity, Settings
```

**`SystemProvider` is the key design decision.** Every page reads from it, so
the same decision is described identically everywhere (a hard requirement).
It merges two sources:
- **Live**: WebSocket `/ws` pushes a full cycle payload each tick.
- **History**: REST (`/api/decisions`, `/api/adaptation-events`) seeded on
  mount so a page refresh does not show empty panels.

It also derives the **activity log** from each cycle (`deriveActivity`), and
computes `focus` — the decision the UI highlights (auto-follows the most
notable one; a user click pins it via `pinnedAsset`).

**`utils/vocab.ts` is the other key piece.** It holds:
- `T` — every metric's plain label + hover explanation + technical term
- `REGIME` / `ACTION` / `VERDICT` — plain-English maps with tone colours
- `ASSET_NAME` — full names so raw tickers never appear alone
- `humanize()` — rewrites backend sentences (which contain `HIGH_VOLATILITY`,
  `volatility`, `exposure`, raw symbols) into the same plain wording used
  everywhere else. **Apply it to any backend-authored string you render.**

### Design language
Neutral slate palette, light + dark themes via `data-theme` on `<html>`
(persisted in localStorage). Colour is reserved for meaning only:
green = gain/approved, red = loss/blocked, amber = caution, blue = system info.
Dense tables, 13px base, tabular numerals, 4–6px radii, no gradients/shadows/glow.

---

## 3. What is working

Verified in-browser this session, all 10 pages, no console errors, no layout overflow:

- All 10 routes render with real data; navigation works
- Live WebSocket updates with auto-reconnect
- Light + dark themes; responsive down to 375px (no horizontal overflow)
- Sortable/filterable/searchable tables
- **Groq LLM is live and working** (`openai/gpt-oss-120b`) — verified the model
  writes the reasoning while leaving action/confidence untouched
- All three risk verdicts occur with genuine data:
  APPROVE, MODIFY (₹15,360 → ₹5,395), REJECT
- Adaptation genuinely fires and visibly tightens settings
  (1.00× → 0.85× → 0.72× confidence) with a before/after view
- All 7 scenarios drive real regime/behaviour changes
- Emergency stop, Start/Pause/Step/Reset/Speed all hit real endpoints

---

## 4. What is incomplete / known issues

1. **`max_single_trade` (₹20,000) almost never binds.** Suggested size is
   `capital × (0.04 + confidence × 0.22)`, so it needs confidence > 0.73 to
   reach the cap, which rarely happens. The MODIFY verdict is currently
   demonstrated via the *per-asset concentration* limit instead. Fixing this
   properly means tuning agent scoring — deliberately not done, since changing
   decision logic was out of scope.
2. **CRISIS never produces a REJECT.** In CRISIS the agent already self-restrains
   to `STOP_NEW_POSITIONS`, which requests no capital, so the Guardian's CRISIS
   rejection branch is effectively unreachable. Harmless but dead code.
3. **A holding can drift above its 25% cap.** Limits are enforced at trade time;
   if the price then rises the position exceeds the cap. The Risk page explains
   this honestly rather than hiding it. No forced-sale logic exists.
4. **Restarting the backend without reloading the browser** leaves stale cycle
   numbers on the chart X-axis (backend restarts at 1, browser keeps old
   history). A page refresh fixes it. Only affects development.
5. **`useLiveFeed` history is memory-only** — capped at 120 cycles, lost on
   refresh. The portfolio chart therefore only covers the current session.
6. ~~**No tests.**~~ Fixed -- `backend/tests/` now covers `risk_guardian.py`
   and `adaptation_engine.py` (34 tests). Nothing else is covered yet; the
   agents, engine, allocator and executor are still manual-verification only.
7. **`decisions` are fetched with `limit=200`** — a very long run will truncate
   older rows in the UI. No pagination.
8. **A cycle takes ~8.6s wall-clock with Groq enabled**, because each of the 6
   assets gets its own sequential LLM call. That is longer than the default 4s
   cycle interval, so `cycle_interval_seconds` (the Speed control) does not
   really set the cadence — LLM latency does. The calls are independent and
   only rewrite prose, so making them concurrent would cut a cycle to ~1.5s
   without touching any decision logic. Not done yet.
9. **`backend/.venv` in the inherited copy was built on another machine** (it
   pointed at a Python install under another user's home directory) and could
   not run at all. It has been rebuilt; the dead one is parked at
   `backend/.venv-broken-amirtha/` and is safe to delete.

---

## 5. Bugs found and fixed (do not reintroduce)

- **HOLD/WAIT counted as losing trades.** Non-executed decisions were marked
  `EVALUATED` with `pnl=0`, so the adaptation engine saw them as losses and
  ratcheted risk limits down forever. Now marked `SKIPPED`. (`engine.py`)
- **Adaptation re-fired every cycle** on the same stale trades. Now only runs
  for a regime when a *new* outcome landed that cycle. (`engine.py`)
- **`StrategyPerformance` counters were `None`** on first insert (Python-side
  column defaults only apply on flush). Now set explicitly.
- **Timestamps disagreed between pages.** DB stores naive UTC; `isoformat()`
  omitted the offset so browsers read REST times as local, while WebSocket
  times were correct — a 5.5h discrepancy. Fixed with `iso_utc()` in
  `api/routes.py`. **Any new timestamp field must use it.**
- **`ai_provider_used` lied.** It reported `groq` even when the call failed and
  the rule-based fallback ran. Now reports what actually executed.
- **Groq 404 / 400.** `llama-3.3-70b-versatile` is retired on this account, and
  `gpt-oss` reasoning models burn the token budget before emitting JSON.
  Fixed: model `openai/gpt-oss-120b`, `max_tokens: 1200`,
  `reasoning_effort: "low"` (~1s per call).

---

- **The autonomous loop blocked the whole server.** `run_cycle()` is
  synchronous and makes one blocking Groq call per asset (~8.6s total), but it
  was called directly inside the async loop and inside `/control/step` — so for
  the entire duration of every cycle the process served no REST responses and
  pushed no WebSocket frames. It now runs on a worker thread via
  `asyncio.to_thread`, guarded by `app.state.cycle_lock`. Measured after the
  fix: REST latency during a running cycle is ~10-15ms.
  **Anything that calls `run_cycle()` must take that lock.**
- **`/control/reset` and `/scenarios/{name}/load` could swap state mid-cycle.**
  They set `running = False` but never waited for an in-flight cycle, so they
  could wipe the database underneath one. Both now take the cycle lock, which
  makes the pause real.

## 6. Important decisions

- **The LLM explains, it never decides.** Keeps every money decision
  reproducible and auditable. Preserve this boundary.
- **Risk Guardian is plain deterministic Python** and structurally cannot be
  bypassed by the AI. This is the project's core safety claim.
- **Adaptation is rule-based/statistical, not model retraining** — an honest
  choice for hackathon scope, and it is real (it measurably changes later
  decisions), not cosmetic.
- **One shared state provider** rather than per-page fetching, so pages can
  never disagree about the same decision.
- **All plain-English wording centralised in `vocab.ts`** rather than scattered
  through JSX, so terminology stays consistent.
- **Scenarios are pure data.** Three were added this session
  (concentration_limit, liquidity_drop, negative_news, high_volatility) to
  exercise real code paths that were otherwise never reached — no decision
  logic was changed to make demos look better.
- **Hash router** (`createHashRouter`) so deep links work without dev-server
  rewrite rules.

---

## 7. How to run

**Backend** (from `/backend`):
```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python -m uvicorn main:app --port 8010 --reload
```

**Frontend** (from `/frontend`):
```bash
npm install
npm run dev
```

Open the printed URL (default `http://localhost:5173`).
Go to **Settings** → pick a scenario → **Start**.

Type-check with:
```bash
npx tsc --noEmit -p tsconfig.app.json
```

**Tests** (from `/backend`):
```bash
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest
```

### Demo route for a judge
1. **Settings** → "Safety Limit Reached" → Start.
   → **Risk Controls** shows the AI asking for more and being cut down, then refused.
2. **Settings** → "Strategy Underperformance" → Start, wait ~40s.
   → **Adaptation** shows before/after settings and why they changed.
3. **Settings** → "Sudden Price Shock" → Start.
   → **Overview** market condition flips to Crisis; the agent stands down.
4. **Decisions** at any point → the full pipeline for one decision.

---

## 8. Environment variables

`/backend/.env` (gitignored; template in `.env.example`):

| Variable | Purpose |
|---|---|
| `AI_PROVIDER` | `groq` (default). Any other value forces rule-based explanations. |
| `GROQ_API_KEY` | Free key from console.groq.com. **A working key is already in `.env`.** Optional — system runs without it. |
| `GROQ_MODEL` | Defaults to `openai/gpt-oss-120b`. Note `llama-3.3-70b-versatile` is retired. |
| `DATABASE_URL` | Defaults to local SQLite; no setup needed. |

Frontend: `VITE_API_BASE` (optional, defaults to `http://localhost:8010`).

> Security note: the Groq key was shared in plaintext chat during development.
> It is in `.env`, which is gitignored, but **rotate it before making this repo
> public.**

---

## 9. Where the last session ended

A stabilisation session, picking up from the completed frontend redesign.
Nothing is half-written. What changed:

1. **The project is now a git repository.** It had none. The first commit is
   the inherited code, untouched, so everything after it reads as a diff.
2. **Rebuilt `backend/.venv`** — the inherited one pointed at a Python install
   belonging to another user and could not start the backend at all.
3. **Fixed the event-loop blocking** described in section 5.
4. **Added 34 tests** for the Risk Guardian and the Adaptation Engine, plus
   `requirements-dev.txt` and `pytest.ini` to run them.
5. **Brought `README.md` up to date** — it still described the old single-page
   UI and claimed three scenarios when there are seven.

Verified after the changes: 34 tests pass, frontend type-checks clean, the
backend runs a full cycle end to end with Groq live, and the server stays
responsive (~10-15ms) throughout a cycle.

## 10. Suggested next steps

1. **Rotate the Groq API key** (see security note above). Still outstanding —
   it has to be done by hand at console.groq.com, and the key has now been
   copied between machines.
2. **Make the per-asset LLM calls concurrent** (issue 8 above). Biggest
   remaining win for how the demo feels: ~8.6s per cycle down to ~1.5s, with no
   change to any decision logic.
3. **Persist cycle history** so the portfolio chart survives a refresh — add a
   `GET /api/history` returning portfolio value per cycle and seed the chart
   from it, instead of relying on in-memory WebSocket history.
4. **Widen test coverage** to the engine and the allocator. The two hardest
   claims are covered; the wiring between them is not.
5. **Make `max_single_trade` reachable** if you want that specific MODIFY story:
   either raise `base_pct`, or lower the limit. Requires a deliberate decision
   about agent scoring.
6. **Paginate `/api/decisions`** before any long-running demo.
7. **Consider a Markets detail route** (`/markets/:asset`) — currently detail is
   an inline expansion, which is fine but not deep-linkable.
8. **Delete `backend/.venv-broken-amirtha/`** once the rebuilt venv has proven
   itself.
9. Minor: `main.py` still uses the deprecated `@app.on_event` startup hooks;
   FastAPI wants a `lifespan` handler now. Harmless today.
