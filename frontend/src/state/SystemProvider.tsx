import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, WS_URL } from "../services/api";
import type {
  CyclePayload, StatusResponse, ScenarioSummary, DecisionRow,
  AdaptationRow, ActivityEvent, TraceEntry,
} from "../types";
import { regimeInfo, actionInfo, verdictInfo, humanize, ASSET_NAME } from "../utils/vocab";

/**
 * Single source of truth for the whole application.
 *
 * Live cycles arrive over the WebSocket; history is seeded once from the REST
 * API so a page reload does not show empty panels. Every page reads from this
 * context, so the same decision is described identically everywhere.
 */

interface SystemState {
  latest: CyclePayload | null;
  history: CyclePayload[];
  status: StatusResponse | null;
  scenarios: ScenarioSummary[];
  decisions: DecisionRow[];
  adaptations: AdaptationRow[];
  activity: ActivityEvent[];
  connected: boolean;
  busy: boolean;
  /** The decision the UI is currently focused on (auto-follows, or user-pinned). */
  focus: TraceEntry | null;
  pinnedAsset: string | null;
  setPinnedAsset: (asset: string | null) => void;
  refreshAll: () => Promise<void>;
  control: {
    start: () => Promise<void>;
    stop: () => Promise<void>;
    step: () => Promise<void>;
    reset: () => Promise<void>;
    setSpeed: (s: number) => Promise<void>;
    emergencyStop: (enable: boolean) => Promise<void>;
    loadScenario: (name: string) => Promise<void>;
  };
}

const Ctx = createContext<SystemState | null>(null);

export function useSystem(): SystemState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSystem must be used inside <SystemProvider>");
  return ctx;
}

const assetName = (a: string) => ASSET_NAME[a] ?? a;

/**
 * Turns one cycle into readable operations-log lines.
 * Only meaningful events are logged -- routine "hold, nothing to do" results
 * are skipped so the log stays scannable instead of repeating six rows a cycle.
 */
function deriveActivity(cycle: CyclePayload, prevRegime: string | null): ActivityEvent[] {
  const out: ActivityEvent[] = [];
  const ts = cycle.timestamp;
  const push = (kind: ActivityEvent["kind"], message: string, asset?: string, tone?: string) =>
    out.push({ id: `${cycle.cycle}-${kind}-${asset ?? ""}-${out.length}`, cycle: cycle.cycle, timestamp: ts, kind, asset, message, tone });

  if (prevRegime && prevRegime !== cycle.overall_regime) {
    const info = regimeInfo(cycle.overall_regime);
    push("MARKET", `Market condition changed to ${info.label}. ${info.explain}`, undefined, info.tone);
  }

  for (const t of cycle.trace) {
    if (t.event.news.length > 0) {
      push("MARKET", `${assetName(t.asset)}: ${t.event.news[0]}`, t.asset, "violet");
    }
    if (Math.abs(t.event.price_change_pct) >= 0.02) {
      const dir = t.event.price_change_pct > 0 ? "rose" : "fell";
      push("MARKET", `${assetName(t.asset)} ${dir} ${Math.abs(t.event.price_change_pct * 100).toFixed(2)}% in one step`, t.asset,
        t.event.price_change_pct > 0 ? "green" : "red");
    }
  }

  for (const t of cycle.trace) {
    const act = actionInfo(t.proposal.action);
    const actionable = !["HOLD", "WAIT"].includes(t.proposal.action);
    if (actionable) {
      push("AGENT", `${t.market_type === "FOREX" ? "Currency" : t.market_type === "EQUITY" ? "Equity" : "Commodity"} Agent proposed "${act.label}" on ${assetName(t.asset)} at ${(t.proposal.confidence * 100).toFixed(0)}% confidence`, t.asset, act.tone);
    }

    if (t.risk_verdict.verdict !== "APPROVE") {
      const v = verdictInfo(t.risk_verdict.verdict);
      push("RISK", `Safety check ${v.label.toLowerCase()} the ${assetName(t.asset)} trade — ${humanize(t.risk_verdict.reasons[0] ?? "")}`, t.asset, v.tone);
    } else if (t.allocation.final_allocation > 0) {
      push("RISK", `Safety check approved the ${assetName(t.asset)} trade`, t.asset, "green");
    }

    if (t.allocation.final_allocation > 0) {
      push("CAPITAL", `Assigned ₹${Math.round(t.allocation.final_allocation).toLocaleString("en-IN")} to ${assetName(t.asset)}`, t.asset, "blue");
    }

    if (t.execution.executed) {
      push("EXECUTION", `${act.label} completed on ${assetName(t.asset)} — ${t.execution.execution_quantity?.toFixed(3)} units at ₹${t.execution.execution_price?.toFixed(2)}`, t.asset, "blue");
    }
  }

  for (const o of cycle.outcomes_evaluated) {
    const good = o.pnl >= 0;
    push("OUTCOME", `${assetName(o.asset)} result: ${good ? "gain" : "loss"} of ₹${Math.abs(Math.round(o.pnl)).toLocaleString("en-IN")} (expected ${o.expected_return_pct.toFixed(2)}%, actual ${o.actual_return_pct.toFixed(2)}%)`, o.asset, good ? "green" : "red");
  }

  for (const a of cycle.adaptation_events) {
    push("ADAPTATION", humanize(a.reasoning), undefined, "amber");
  }

  return out;
}

export function SystemProvider({ children }: { children: ReactNode }) {
  const [latest, setLatest] = useState<CyclePayload | null>(null);
  const [history, setHistory] = useState<CyclePayload[]>([]);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [decisions, setDecisions] = useState<DecisionRow[]>([]);
  const [adaptations, setAdaptations] = useState<AdaptationRow[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pinnedAsset, setPinnedAsset] = useState<string | null>(null);

  const prevRegime = useRef<string | null>(null);

  const refreshAll = useCallback(async () => {
    const [s, d, a] = await Promise.allSettled([api.status(), api.decisions(200), api.adaptationEvents(50)]);
    if (s.status === "fulfilled") setStatus(s.value);
    if (d.status === "fulfilled") setDecisions(d.value);
    if (a.status === "fulfilled") setAdaptations(a.value);
  }, []);

  useEffect(() => {
    api.scenarios().then(setScenarios).catch(() => {});
    refreshAll();
    const id = setInterval(() => api.status().then(setStatus).catch(() => {}), 3000);
    return () => clearInterval(id);
  }, [refreshAll]);

  // --- websocket ---
  useEffect(() => {
    let cancelled = false;
    let retry: number | undefined;
    let ws: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) retry = window.setTimeout(connect, 2000);
      };
      ws.onerror = () => ws?.close();
      ws.onmessage = (msg) => {
        try {
          const data: CyclePayload = JSON.parse(msg.data);
          setLatest(data);
          setHistory((prev) => [...prev.slice(-119), data]);
          const events = deriveActivity(data, prevRegime.current);
          prevRegime.current = data.overall_regime;
          if (events.length) setActivity((prev) => [...prev.slice(-400), ...events]);
        } catch {
          /* ignore malformed frame */
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      if (retry) window.clearTimeout(retry);
      ws?.close();
    };
  }, []);

  // Pull persisted rows again whenever a cycle produced something durable.
  useEffect(() => {
    if (!latest) return;
    if (latest.adaptation_events.length > 0 || latest.outcomes_evaluated.length > 0 || latest.trace.some((t) => t.execution.executed)) {
      api.decisions(200).then(setDecisions).catch(() => {});
      api.adaptationEvents(50).then(setAdaptations).catch(() => {});
    }
  }, [latest]);

  /** The decision the UI focuses on: user's pick if still present, else the most notable one. */
  const focus = useMemo<TraceEntry | null>(() => {
    if (!latest) return null;
    if (pinnedAsset) {
      const pinned = latest.trace.find((t) => t.asset === pinnedAsset);
      if (pinned) return pinned;
    }
    const executed = latest.trace.find((t) => t.execution.executed);
    if (executed) return executed;
    const blocked = latest.trace.find((t) => t.risk_verdict.verdict !== "APPROVE");
    if (blocked) return blocked;
    const actionable = latest.trace.find((t) => !["HOLD", "WAIT"].includes(t.proposal.action));
    if (actionable) return actionable;
    return [...latest.trace].sort((a, b) => b.proposal.confidence - a.proposal.confidence)[0] ?? null;
  }, [latest, pinnedAsset]);

  const wrap = useCallback(async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await refreshAll();
    } finally {
      setBusy(false);
    }
  }, [refreshAll]);

  const clearLocal = () => {
    setHistory([]);
    setActivity([]);
    setLatest(null);
    setPinnedAsset(null);
    prevRegime.current = null;
  };

  const control = useMemo(() => ({
    start: () => wrap(api.start),
    stop: () => wrap(api.stop),
    step: () => wrap(api.step),
    reset: () => wrap(async () => { await api.reset(); clearLocal(); }),
    setSpeed: (s: number) => wrap(() => api.setSpeed(s)),
    emergencyStop: (enable: boolean) => wrap(() => api.emergencyStop(enable)),
    loadScenario: (name: string) => wrap(async () => { await api.loadScenario(name, true); clearLocal(); }),
  }), [wrap]);

  const value: SystemState = {
    latest, history, status, scenarios, decisions, adaptations, activity,
    connected, busy, focus, pinnedAsset, setPinnedAsset, refreshAll, control,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
