export interface MarketEventView {
  price: number;
  price_change_pct: number;
  volatility: number;
  liquidity: number;
  news: string[];
}

export interface ProposalView {
  action: string;
  confidence: number;
  reasoning: string;
  suggested_allocation: number;
  expected_risk: number;
  expected_return_pct: number;
  strategy_tag: string;
  ai_provider_used: string;
  factors: string[];
  risk_factors: string[];
}

export interface RiskVerdictView {
  verdict: "APPROVE" | "REJECT" | "MODIFY";
  approved_allocation: number;
  reasons: string[];
}

export interface AllocationView {
  final_allocation: number;
  reasoning: string[];
}

export interface ExecutionView {
  executed: boolean;
  execution_price?: number;
  execution_quantity?: number;
  slippage_pct?: number;
  transaction_cost?: number;
  note?: string;
}

export interface TraceEntry {
  asset: string;
  market_type: string;
  regime: string;
  event: MarketEventView;
  proposal: ProposalView;
  risk_verdict: RiskVerdictView;
  allocation: AllocationView;
  execution: ExecutionView;
}

export interface OutcomeView {
  asset: string;
  strategy_tag: string;
  regime: string;
  expected_return_pct: number;
  actual_return_pct: number;
  pnl: number;
  summary: string;
}

export interface AdaptationEventView {
  regime: string;
  trigger: string;
  reasoning: string;
  parameter_changed: string;
  old_value: string;
  new_value: string;
}

export interface AdaptiveStateView {
  confidence_multiplier: number;
  size_multiplier: number;
  risk_tightening_factor: number;
}

export interface StrategyLeaderboardRow {
  strategy_tag: string;
  regime: string;
  success_rate: number;
  total_trades: number;
  total_pnl: number;
}

export interface PortfolioSnapshot {
  cash: number;
  available_cash: number;
  portfolio_value: number;
  total_exposure: number;
  exposure_by_asset: Record<string, number>;
  open_position_count: number;
  daily_pnl_pct: number;
  realized_pnl: number;
  positions: Record<string, { quantity: number; avg_entry_price: number }>;
}

export interface CyclePayload {
  cycle: number;
  timestamp: string;
  emergency_stop: boolean;
  ai_provider: string;
  overall_regime: string;
  portfolio: PortfolioSnapshot;
  trace: TraceEntry[];
  outcomes_evaluated: OutcomeView[];
  adaptation_events: AdaptationEventView[];
  adaptive_states: Record<string, AdaptiveStateView>;
  strategy_leaderboard: StrategyLeaderboardRow[];
}

export interface ScenarioSummary {
  name: string;
  title: string;
  description: string;
  duration_cycles: number;
}

/** A persisted decision row from /api/decisions (survives page reloads). */
export interface DecisionRow {
  id: number;
  cycle_number: number;
  timestamp: string;
  asset: string;
  market_type: string;
  regime: string;
  action: string;
  confidence: number;
  reasoning: string;
  risk_verdict: string;
  risk_reasons: string;
  final_allocation: number;
  executed: boolean;
  execution_price: number;
  execution_quantity: number;
  outcome_status: string;
  actual_return_pct: number;
  expected_return_pct: number;
  pnl: number;
  outcome_summary: string;
  ai_provider_used: string;
  strategy_tag: string;
  proposed_allocation: number;
  risk_adjusted_allocation: number;
  allocation_reasoning: string;
  slippage_pct: number;
  transaction_cost: number;
  expected_risk: number;
  event_description: string;
  price: number;
  volatility: number;
  liquidity: number;
}

export interface AdaptationRow {
  id: number;
  timestamp: string;
  trigger: string;
  parameter_changed: string;
  old_value: string;
  new_value: string;
  reasoning: string;
}

/** One line in the derived system activity log. */
export type ActivityKind = "MARKET" | "AGENT" | "RISK" | "CAPITAL" | "EXECUTION" | "OUTCOME" | "ADAPTATION" | "SYSTEM";

export interface ActivityEvent {
  id: string;
  cycle: number;
  timestamp: string;
  kind: ActivityKind;
  asset?: string;
  message: string;
  tone?: string;
}

export interface StatusResponse {
  running: boolean;
  cycle: number;
  ai_provider: string;
  emergency_stop: boolean;
  active_scenario: string | null;
  cycle_interval_seconds: number;
  starting_capital: number;
  risk_limits: Record<string, number>;
}
