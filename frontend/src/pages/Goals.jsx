import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Progress, Status } from "../components/ui";

export default function Goals() {
  const { data, loading, error, reload } = useApi(() => api.goals(), []);
  const [scenario, setScenario] = useState("Base Case");
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Planning</div>
          <h1>Goals & scenarios</h1>
          <p>Scenarios are isolated from the book of record. Changing a case never writes holdings.</p>
        </div>
      </div>
      <div className="tabs">
        {["Base Case", "Optimistic", "Conservative"].map((n) => (
          <button key={n} className={scenario === n ? "tab active" : "tab"} onClick={() => setScenario(n)}>
            {n}
          </button>
        ))}
      </div>
      <div className="grid g-2">
        {data.goals.map((g) => {
          const sc = g.scenarios.find((s) => s.name === scenario) || g.scenarios[0];
          return (
            <Card key={g.id} title={g.category}>
              <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, margin: "0 0 8px" }}>{g.name}</h2>
              <div className="metric-sm num">
                {money(g.current)} <span className="faint">of {money(g.target)}</span>
              </div>
              <div style={{ margin: "10px 0" }}>
                <Progress value={g.pct} />
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                <Status value={g.projected_status} />
                <span className="chip">Target {g.target_date}</span>
                <span className="chip">{g.pct}% funded</span>
              </div>
              <p className="faint">{g.notes}</p>
              <p>
                Linked accounts: {g.linked_accounts.join(", ")} · annual contribution {money(g.annual_contribution)}
              </p>
              <div className="card" style={{ boxShadow: "none", marginTop: 8 }}>
                <h3>{scenario} (isolated)</h3>
                <div>
                  Projected value <strong className="num">{money(sc.projected_value)}</strong>
                </div>
                <div>
                  Growth {(sc.growth_rate * 100).toFixed(1)}% · probability {(sc.probability * 100).toFixed(0)}%
                </div>
                <div className="faint">isolated={String(sc.isolated)} · does not affect book of record</div>
              </div>
            </Card>
          );
        })}
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Monte Carlo — retirement capital (illustrative)">
          <div className="grid g-4">
            <div>
              <div className="faint">P10</div>
              <div className="metric-sm num">{money(data.monte_carlo.p10)}</div>
            </div>
            <div>
              <div className="faint">Median</div>
              <div className="metric-sm num">{money(data.monte_carlo.p50)}</div>
            </div>
            <div>
              <div className="faint">P90</div>
              <div className="metric-sm num">{money(data.monte_carlo.p90)}</div>
            </div>
            <div>
              <div className="faint">Paths ≥ {money(data.goals?.find((g) => (g.category || "").toLowerCase() === "retirement")?.target || 3000000)}</div>
              <div className="metric-sm num">{data.monte_carlo.success_rate}%</div>
            </div>
          </div>
          <p className="faint" style={{ marginTop: 12 }}>
            {data.monte_carlo.method} · {data.monte_carlo.assumptions[0]} · {data.monte_carlo.limitations[0]}
          </p>
        </Card>
      </div>
    </div>
  );
}
