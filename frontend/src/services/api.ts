import type { ScenarioSummary, StatusResponse, DecisionRow, AdaptationRow, StrategyLeaderboardRow, PortfolioSnapshot } from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8010";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const api = {
  status: () => req<StatusResponse>("/api/status"),
  scenarios: () => req<ScenarioSummary[]>("/api/scenarios"),
  loadScenario: (name: string, reset = true) =>
    req(`/api/scenarios/${name}/load`, { method: "POST", body: JSON.stringify({ reset }) }),
  clearScenario: () => req(`/api/scenarios/clear`, { method: "POST" }),
  start: () => req(`/api/control/start`, { method: "POST" }),
  stop: () => req(`/api/control/stop`, { method: "POST" }),
  step: () => req(`/api/control/step`, { method: "POST" }),
  reset: () => req(`/api/control/reset`, { method: "POST" }),
  setSpeed: (cycle_interval_seconds: number) =>
    req(`/api/control/speed`, { method: "POST", body: JSON.stringify({ cycle_interval_seconds }) }),
  emergencyStop: (enable: boolean) =>
    req(`/api/control/emergency-stop`, { method: "POST", body: JSON.stringify({ enable }) }),
  portfolio: () => req<PortfolioSnapshot>("/api/portfolio"),
  decisions: (limit = 200) => req<DecisionRow[]>(`/api/decisions?limit=${limit}`),
  strategyPerformance: () => req<StrategyLeaderboardRow[]>(`/api/strategy-performance`),
  adaptationEvents: (limit = 50) => req<AdaptationRow[]>(`/api/adaptation-events?limit=${limit}`),
};

export const WS_URL = BASE.replace(/^http/, "ws") + "/ws";
