import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import "./App.css";
import { useSystem } from "./state/SystemProvider";
import { Badge } from "./components/ui";
import { fmtCurrency, fmtPct } from "./utils/format";
import { regimeInfo } from "./utils/vocab";

const NAV = [
  {
    group: "Monitor",
    items: [
      { to: "/", label: "Overview", glyph: "◧", end: true },
      { to: "/markets", label: "Markets", glyph: "▤" },
      { to: "/agents", label: "Agents", glyph: "◈" },
      { to: "/portfolio", label: "Portfolio", glyph: "▦" },
    ],
  },
  {
    group: "Decision Flow",
    items: [
      { to: "/decisions", label: "Decisions", glyph: "◆" },
      { to: "/risk", label: "Risk Controls", glyph: "⛊" },
      { to: "/execution", label: "Execution", glyph: "▸" },
      { to: "/adaptation", label: "Adaptation", glyph: "↻" },
    ],
  },
  {
    group: "System",
    items: [
      { to: "/activity", label: "Activity Log", glyph: "≡" },
      { to: "/settings", label: "Settings", glyph: "⚙" },
    ],
  },
];

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem("theme") : null;
    return saved === "light" || saved === "dark" ? saved : "dark";
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("theme", theme); } catch { /* storage unavailable */ }
  }, [theme]);
  return { theme, setTheme };
}

export default function App() {
  const { latest, status, connected, backendUp } = useSystem();
  const { theme, setTheme } = useTheme();

  const portfolio = latest?.portfolio;
  const startCapital = status?.starting_capital ?? 100000;
  const pnl = portfolio ? portfolio.portfolio_value - startCapital : 0;
  const pnlPct = startCapital ? (pnl / startCapital) * 100 : 0;
  const regime = regimeInfo(latest?.overall_regime ?? "NORMAL");

  const running = status?.running ?? false;
  const stopped = status?.emergency_stop ?? false;

  return (
    <div className="shell">
      <div className="brand">
        <div className="mark">AC</div>
        <div className="name">
          AutoChain
          <span>Multi-Agent Market System</span>
        </div>
      </div>

      <header className="topbar">
        <div className="status-item">
          <span className={`dot ${stopped ? "red" : running ? "green pulse" : "gray"}`} />
          {stopped ? "Halted" : running ? "Running" : "Paused"}
        </div>
        <div className="divider" />
        <div className="status-item">
          Step <b>{status?.cycle ?? 0}</b>
        </div>
        <div className="divider" />
        <div className="status-item">
          Market condition <Badge tone={regime.tone}>{regime.label}</Badge>
        </div>
        <div className="divider" />
        <div className="status-item">
          Portfolio <b>{portfolio ? fmtCurrency(portfolio.portfolio_value) : "—"}</b>
        </div>
        <div className="status-item">
          <span className={pnl > 0 ? "pos" : pnl < 0 ? "neg" : "muted"}>
            {portfolio ? `${pnl >= 0 ? "+" : ""}${fmtCurrency(pnl)} (${fmtPct(pnlPct)})` : "—"}
          </span>
        </div>

        <div className="spacer" />

        {stopped && <Badge tone="red">Emergency stop active</Badge>}
        <div className="status-item" title={connected ? "Receiving live updates" : "Reconnecting to the system"}>
          <span className={`dot ${connected ? "green" : "red"}`} />
          {connected ? "Live" : "Offline"}
        </div>
        <button className="sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </header>

      <nav className="sidebar">
        {NAV.map((g) => (
          <div className="nav-group" key={g.group}>
            <div className="group-label">{g.group}</div>
            {g.items.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              >
                <span className="glyph">{it.glyph}</span>
                {it.label}
              </NavLink>
            ))}
          </div>
        ))}
        <div className="sidebar-foot">
          Paper trading simulation.
          <br />
          No real money is used.
        </div>
      </nav>

      <main className="main">
        {!backendUp && (
          <div className="offline-banner">
            <span className="dot red pulse" />
            <span>
              <b>Cannot reach the system.</b> The dashboard is showing the last data it
              received. Start the backend, and this will clear on its own.
            </span>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
