import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Badge, Card, CHART, ErrorState, Loading, money, pct, Progress, Status } from "../components/ui";

export default function Dashboard() {
  const { data, loading, error, reload } = useApi(() => api.dashboard(), []);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const d = data;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">{d.household.name}</div>
          <h1>Household dashboard</h1>
          <p>
            {d.lineage.display?.as_of} · {d.lineage.display?.label}
          </p>
        </div>
        <div className="chip">Source {d.lineage.provider} · v{d.lineage.version}</div>
      </div>

      <div className="grid g-4">
        <Card title="Net worth">
          <div className="metric num">{money(d.net_worth.total)}</div>
          <div className="delta up">Today {money(d.net_worth.change_today)} ({pct(d.net_worth.change_today_pct)})</div>
          <div className="faint">YTD {money(d.net_worth.change_ytd)} ({pct(d.net_worth.change_ytd_pct)})</div>
        </Card>
        <Card title="Portfolio value">
          <div className="metric num">{money(d.portfolio.invested_assets)}</div>
          <div className={d.portfolio.daily_change >= 0 ? "delta up" : "delta down"}>
            Daily {money(d.portfolio.daily_change)} ({pct(d.portfolio.daily_change_pct)})
          </div>
          <div className="faint">YTD return {d.portfolio.ytd_return}%</div>
        </Card>
        <Card title="Cash & liquidity">
          <div className="metric num">{money(d.cash.available)}</div>
          <div className="faint">Emergency reserve {money(d.cash.emergency_reserve)}</div>
          <div className="faint">Upcoming needs {money(d.cash.upcoming_needs)} · {d.cash.label}</div>
        </Card>
        <Card title="Retirement goal">
          {d.goals[0] && (
            <>
              <div className="metric num">{d.goals[0].pct}%</div>
              <Progress value={d.goals[0].pct} />
              <div className="faint" style={{ marginTop: 8 }}>
                {money(d.goals[0].current)} of {money(d.goals[0].target)} · {Math.round(d.goals[0].probability * 100)}% probability
              </div>
            </>
          )}
        </Card>
      </div>

      <div className="grid g-sidebar" style={{ marginTop: 16 }}>
        <Card title="Allocation">
          <div style={{ height: 240 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={d.allocation} dataKey="value" nameKey="name" innerRadius={68} outerRadius={96} paddingAngle={2}>
                  {d.allocation.map((_, i) => (
                    <Cell key={i} fill={CHART[i % CHART.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => money(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {d.allocation.map((a, i) => (
              <span key={a.name} className="faint">
                <span style={{ color: CHART[i], fontWeight: 600 }}>●</span> {a.name} {a.pct}%
              </span>
            ))}
          </div>
        </Card>
        <Card title="AI insights">
          {d.insights.map((ins) => (
            <div key={ins.title} className={ins.severity === "warning" ? "insight warn" : "insight"}>
              <div className="tick" />
              <div>
                <strong>{ins.title}</strong>
                <div className="faint">{ins.body}</div>
              </div>
            </div>
          ))}
        </Card>
      </div>

      <div className="grid g-2" style={{ marginTop: 16 }}>
        <Card title="Goals">
          {d.goals.map((g) => (
            <div key={g.id} style={{ marginBottom: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{g.category}</strong>
                <Status value={g.projected_status} />
              </div>
              <div className="faint" style={{ margin: "4px 0 6px" }}>
                {money(g.current)} / {money(g.target)} · {g.pct}%
              </div>
              <Progress value={g.pct} />
            </div>
          ))}
        </Card>
        <Card title="Tax opportunities">
          {d.tax_opportunities.map((t) => (
            <div key={t.id} className="insight">
              <div className="tick" />
              <div>
                <strong>{t.title}</strong>
                <div className="faint">{t.detail}</div>
                {t.benefit > 0 && <Badge tone="ok">Benefit {money(t.benefit)}</Badge>}
              </div>
            </div>
          ))}
        </Card>
      </div>

      <div style={{ marginTop: 16 }}>
        <Card title="Recent activity">
          {d.activity.map((a) => (
            <div className="activity" key={a.id}>
              <Badge tone="info">{a.type}</Badge>
              <div style={{ flex: 1 }}>
                <div>{a.description}</div>
                <div className="faint">{a.date} · {a.actor}</div>
              </div>
              <div className="num">{a.amount ? money(a.amount) : ""}</div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
