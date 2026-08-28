/**
 * One place that turns the system's technical vocabulary into plain English.
 *
 * Every page pulls its labels and explanations from here, so wording stays
 * consistent and a reader with no finance background can follow along. Each
 * entry keeps the technical term as a secondary line rather than hiding it.
 */

export interface Term {
  label: string;
  help: string;
  technical?: string;
}

export const T: Record<string, Term> = {
  portfolioValue: {
    label: "Portfolio Value",
    help: "Everything the system holds right now: unspent cash plus whatever the current investments are worth.",
  },
  availableCash: {
    label: "Available Cash",
    help: "Money not currently invested. This is what the system can still spend on new trades.",
  },
  amountInvested: {
    label: "Amount Invested",
    help: "How much money is currently tied up in open positions rather than sitting in cash.",
    technical: "Exposure",
  },
  todaysResult: {
    label: "Session Result",
    help: "Money made or lost since this simulation run started.",
    technical: "Session P&L",
  },
  moneyAtRisk: {
    label: "Money at Risk",
    help: "The share of the portfolio currently invested. The more that is invested, the more a price fall would cost.",
    technical: "Portfolio exposure %",
  },
  priceActivity: {
    label: "Price Activity",
    help: "How quickly and sharply the price is moving. High activity means bigger, faster swings in both directions.",
    technical: "Volatility",
  },
  tradability: {
    label: "Tradability",
    help: "How easily the asset can be bought or sold without pushing the price against you. Low tradability makes trading expensive.",
    technical: "Liquidity",
  },
  marketCondition: {
    label: "Market Condition",
    help: "The system's read on what kind of market this is right now. It changes how cautious the system behaves.",
    technical: "Market regime",
  },
  confidence: {
    label: "Confidence",
    help: "How strongly the agent believes in this decision, from its own signal analysis. Higher confidence earns a larger share of capital.",
  },
  riskCheck: {
    label: "Safety Check",
    help: "An independent rule-based check that runs after the AI proposes a trade. It can approve it, shrink it, or block it entirely.",
    technical: "Risk Guardian",
  },
  moneyAssigned: {
    label: "Money Assigned",
    help: "How much cash was actually committed to this trade after the safety check and capital sharing.",
    technical: "Capital allocation",
  },
  expectedRisk: {
    label: "Expected Risk",
    help: "The system's estimate of how risky this specific trade is, from 0 (calm) to 1 (very risky).",
  },
  slippage: {
    label: "Price Slippage",
    help: "The gap between the price the system aimed for and the price it actually got. Wider gaps happen in fast or thin markets.",
  },
  transactionCost: {
    label: "Trading Fee",
    help: "The simulated cost charged for placing the trade, like a broker's fee and spread.",
  },
  maxSingleTrade: {
    label: "Largest Single Trade",
    help: "The most money the system is allowed to put into any one trade, no matter how confident it is.",
  },
  maxAssetExposure: {
    label: "Most in One Asset",
    help: "The largest share of the portfolio allowed in a single asset, so the system cannot bet everything on one thing.",
    technical: "Max asset exposure",
  },
  maxPortfolioExposure: {
    label: "Most Invested at Once",
    help: "The largest share of the portfolio that can be invested at the same time. The rest stays as cash.",
    technical: "Max portfolio exposure",
  },
  maxDailyLoss: {
    label: "Daily Loss Limit",
    help: "If losses for the session reach this level, the system stops opening new positions.",
  },
  minLiquidity: {
    label: "Minimum Tradability",
    help: "If an asset is harder to trade than this, the system refuses to buy it at all.",
  },
  strategy: {
    label: "Strategy",
    help: "The broad approach behind a decision. 'Momentum' follows a trend; 'mean reversion' expects the price to settle back.",
  },
  successRate: {
    label: "Success Rate",
    help: "The share of completed trades using this approach that ended in profit.",
  },
  adaptation: {
    label: "System Adaptation",
    help: "Automatic adjustments the system makes to its own behaviour after reviewing how recent trades actually turned out.",
  },
  confidenceMultiplier: {
    label: "Confidence Setting",
    help: "A dial the system turns down on itself after losses, making it less sure and therefore less aggressive.",
  },
  sizeMultiplier: {
    label: "Trade Size Setting",
    help: "A dial that shrinks every new trade while recent results have been poor.",
  },
  riskFactor: {
    label: "Safety Limit Setting",
    help: "A dial that tightens the safety limits themselves, so even approved trades get smaller.",
  },
  expectedVsActual: {
    label: "Expected vs Actual",
    help: "What the system predicted the price would do, next to what it really did. This is how it grades itself.",
  },
};

/** Market condition (regime) explained in plain language. */
export const REGIME: Record<string, { label: string; explain: string; tone: string }> = {
  NORMAL: {
    label: "Normal",
    explain: "Prices are moving as usual. The system is trading at its normal size.",
    tone: "green",
  },
  TRENDING: {
    label: "Trending",
    explain: "Prices are moving steadily in one direction. The system looks for moves to follow.",
    tone: "blue",
  },
  HIGH_VOLATILITY: {
    label: "High Activity",
    explain: "Prices are swinging more than usual. The system is cutting trade sizes in half.",
    tone: "amber",
  },
  LOW_LIQUIDITY: {
    label: "Hard to Trade",
    explain: "There are few buyers and sellers, so trading is expensive. The system is avoiding large trades.",
    tone: "amber",
  },
  EVENT_DRIVEN: {
    label: "News Driven",
    explain: "A news event is moving the market. The system is trading more cautiously than normal.",
    tone: "violet",
  },
  CRISIS: {
    label: "Crisis",
    explain: "Conditions are severe. The system has stopped opening any new positions.",
    tone: "red",
  },
};

export function regimeInfo(regime: string) {
  return REGIME[regime] ?? { label: regime, explain: "", tone: "gray" };
}

/** Actions in plain language. */
export const ACTION: Record<string, { label: string; explain: string; tone: string }> = {
  BUY: { label: "Buy", explain: "Open a new position in this asset.", tone: "green" },
  SELL: { label: "Sell", explain: "Close the position in this asset completely.", tone: "red" },
  HOLD: { label: "Hold", explain: "Keep things as they are — no trade needed.", tone: "gray" },
  INCREASE_EXPOSURE: { label: "Add More", explain: "Put more money into a position already held.", tone: "green" },
  REDUCE_EXPOSURE: { label: "Reduce", explain: "Sell part of the position to lower risk.", tone: "amber" },
  WAIT: { label: "Wait", explain: "Stay out for now and keep watching.", tone: "gray" },
  STOP_NEW_POSITIONS: { label: "Stop Buying", explain: "Conditions are unsafe — open nothing new.", tone: "red" },
};

export function actionInfo(action: string) {
  return ACTION[action] ?? { label: action, explain: "", tone: "gray" };
}

/** Risk verdicts in plain language. */
export const VERDICT: Record<string, { label: string; explain: string; tone: string }> = {
  APPROVE: { label: "Approved", explain: "The trade passed every safety rule and went ahead unchanged.", tone: "green" },
  MODIFY: { label: "Reduced", explain: "The trade broke a safety limit, so it was shrunk to a permitted size.", tone: "amber" },
  REJECT: { label: "Blocked", explain: "The trade broke a safety rule and was refused entirely.", tone: "red" },
};

export function verdictInfo(v: string) {
  return VERDICT[v] ?? { label: v, explain: "", tone: "gray" };
}

export const MARKET_LABEL: Record<string, string> = {
  EQUITY: "Equity",
  FOREX: "Currency",
  COMMODITY: "Commodity",
};

export const AGENT_LABEL: Record<string, string> = {
  EQUITY: "Equity Agent",
  FOREX: "Currency Agent",
  COMMODITY: "Commodity Agent",
};

export const AGENT_SCOPE: Record<string, string> = {
  EQUITY: "Company shares. Reads price direction, trading volume and company news.",
  FOREX: "Currency pairs. Reads exchange-rate moves and central bank / interest-rate signals.",
  COMMODITY: "Physical goods like gold and oil. Reads supply, demand and geopolitical events.",
};

/** Asset display names so the UI never shows raw symbols alone. */
export const ASSET_NAME: Record<string, string> = {
  TCS: "Tata Consultancy Services",
  INFY: "Infosys",
  "USD/INR": "US Dollar / Indian Rupee",
  "EUR/USD": "Euro / US Dollar",
  GOLD: "Gold",
  CRUDE_OIL: "Crude Oil",
};

/**
 * The symbol as a product would print it. The backend uses CRUDE_OIL as an
 * identifier, and an underscore on screen reads as a database key rather than
 * a ticker.
 */
export const assetTicker = (asset: string): string => asset.replace(/_/g, " ");

/**
 * Backend-generated sentences (rule-engine reasoning, risk reasons, adaptation
 * notes) use internal constants like "HIGH_VOLATILITY" and raw ticker symbols.
 * This rewrites those into the same plain wording used elsewhere in the UI so
 * the reader never meets two names for the same thing. Meaning is unchanged.
 */
export function humanize(text: string): string {
  if (!text) return text;
  let out = text;

  for (const [code, info] of Object.entries(REGIME)) {
    out = out.replace(new RegExp(`\\b${code}\\b`, "g"), info.label);
  }
  for (const [code, info] of Object.entries(ACTION)) {
    out = out.replace(new RegExp(`\\b${code}\\b`, "g"), info.label.toUpperCase());
  }
  for (const [symbol, name] of Object.entries(ASSET_NAME)) {
    out = out.replace(new RegExp(symbol.replace(/[/]/g, "\\/"), "g"), name);
  }

  return out
    // Specific backend phrases first, so the generic word swaps below don't
    // produce awkward half-translated sentences.
    .replace(/max single-asset exposure/gi, "the single-asset limit")
    .replace(/max portfolio exposure/gi, "the total-invested limit")
    .replace(/max single-trade limit/gi, "the largest-single-trade limit")
    .replace(/\bmarket regime\b/gi, "market condition")
    .replace(/\s+regime\b/gi, " conditions")
    .replace(/\bvolatility\b/gi, "price activity")
    .replace(/\bliquidity\b/gi, "tradability")
    .replace(/\bexposure\b/gi, "amount invested")
    .replace(/\bPerformance degradation detected\b/gi, "Results have been getting worse")
    .replace(/\bportfolio\b/g, "portfolio");
}

/** Turns a 0-1 volatility number into a plain word. */
export function activityLevel(vol: number): { label: string; tone: string } {
  if (vol >= 0.07) return { label: "Extreme", tone: "red" };
  if (vol >= 0.035) return { label: "High", tone: "amber" };
  if (vol >= 0.018) return { label: "Moderate", tone: "blue" };
  return { label: "Normal", tone: "green" };
}

/** Turns a 0-1 liquidity number into a plain word. */
export function tradabilityLevel(liq: number): { label: string; tone: string } {
  if (liq >= 0.8) return { label: "Easy", tone: "green" };
  if (liq >= 0.5) return { label: "Moderate", tone: "blue" };
  if (liq >= 0.3) return { label: "Difficult", tone: "amber" };
  return { label: "Very Difficult", tone: "red" };
}

/** What the system is doing about an asset, in one word. */
export function systemStance(action: string, executed: boolean): { label: string; tone: string } {
  if (executed) return { label: "Acted", tone: "blue" };
  if (action === "STOP_NEW_POSITIONS") return { label: "Standing Down", tone: "red" };
  if (action === "WAIT") return { label: "Waiting", tone: "gray" };
  if (action === "HOLD") return { label: "Watching", tone: "gray" };
  return { label: "Considering", tone: "amber" };
}

/**
 * The backend tags a decision "momentum" only when its combined signal is
 * strong; anything weaker is tagged "mean_reversion". So the honest plain
 * reading is "clear trend to follow" vs "no clear trend".
 */
export function strategyLabel(tag: string): string {
  if (!tag) return "—";
  const trend = tag.startsWith("momentum") ? "Following a clear trend" : "No clear trend";
  const vol = tag.endsWith("high_volatility") ? "choppy prices" : "calm prices";
  return `${trend}, ${vol}`;
}
