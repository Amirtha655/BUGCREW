import { useSystem } from "../state/SystemProvider";
import { Panel, Badge } from "./ui";

const SPEEDS = [
  { label: "Slow", value: 6 },
  { label: "Normal", value: 4 },
  { label: "Fast", value: 2 },
  { label: "Very fast", value: 1 },
];

/**
 * Drives the real backend simulation loop. Every control here maps to an
 * actual API call that changes system state -- nothing is decorative.
 */
export function SimulationControls({ compact = false }: { compact?: boolean }) {
  const { status, scenarios, busy, control } = useSystem();
  const running = status?.running ?? false;
  const activeScenario = status?.active_scenario ?? null;
  const speed = status?.cycle_interval_seconds ?? 4;

  return (
    <Panel
      title="Simulation Control"
      sub={running ? "Running" : "Paused"}
      actions={<Badge tone={running ? "green" : "gray"}>{running ? "Live" : "Idle"}</Badge>}
    >
      <div className="row wrap" style={{ gap: 6, marginBottom: 12 }}>
        {running ? (
          <button className="danger" disabled={busy} onClick={control.stop}>Pause</button>
        ) : (
          <button className="primary" disabled={busy} onClick={control.start}>Start</button>
        )}
        <button disabled={busy || running} onClick={control.step} title="Advance exactly one decision cycle">
          Step once
        </button>
        <button disabled={busy} onClick={control.reset} title="Clear all trades and start the scenario again">
          Reset
        </button>
      </div>

      <div style={{ marginBottom: 12 }}>
        <div className="stat-tile" style={{ padding: 0 }}>
          <div className="label">Speed</div>
        </div>
        <div className="btn-group" style={{ marginTop: 5 }}>
          {SPEEDS.map((s) => (
            <button
              key={s.value}
              className={`sm${Math.abs(speed - s.value) < 0.01 ? " on" : ""}`}
              disabled={busy}
              onClick={() => control.setSpeed(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="faint" style={{ fontSize: 11, marginTop: 4 }}>
          One decision cycle every {speed}s.
        </div>
      </div>

      {!compact && (
        <>
          <div className="sep" />
          <div className="stat-tile" style={{ padding: 0, marginBottom: 7 }}>
            <div className="label">Scenario</div>
          </div>
          <div className="scenario-list">
            {scenarios.map((s) => (
              <button
                key={s.name}
                className={`scenario-item${activeScenario === s.name ? " on" : ""}`}
                disabled={busy}
                onClick={() => control.loadScenario(s.name)}
              >
                <span className="s-radio" />
                <span>
                  <span className="s-title">{s.title}</span>
                  <span className="s-desc">{s.description}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="faint" style={{ fontSize: 11, marginTop: 7 }}>
            Choosing a scenario clears the portfolio and replays a scripted sequence of
            market events through the live system.
          </div>
        </>
      )}
    </Panel>
  );
}
