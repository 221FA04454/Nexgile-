import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { formatINRCompact } from "../currency";
import { Badge, Card, CHART, ErrorState, Loading, money, pct, Status } from "../components/ui";

export default function Portfolio() {
  const { data, loading, error, reload } = useApi(() => api.portfolios(), []);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function rebalance() {
    setBusy(true);
    setMsg("");
    try {
      const p = await api.rebalancePreview(data.portfolio.id);
      setPreview(p);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function requestApproval() {
    await api.createApproval({
      action: "rebalance",
      entity_type: "Portfolio",
      entity_id: String(data.portfolio.id),
      notes: "Client requested rebalance preview approval",
      new_value: { preview: true },
    });
    setMsg("Approval submitted. Book of record is unchanged.");
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const s = data.summary;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">{data.portfolio.strategy}</div>
          <h1>{data.portfolio.name}</h1>
          <p>
            Risk {data.risk.score} · {data.risk.label} · vs {data.benchmark.name} YTD {pct(data.benchmark.excess_ytd)} excess
          </p>
        </div>
        <button className="btn" onClick={rebalance} disabled={busy}>
          {busy ? "Building preview…" : "Rebalance portfolio"}
        </button>
      </div>

      <div className="grid g-4">
        <Card title="Market value">
          <div className="metric num">{money(s.total_market_value)}</div>
          <div className={s.day_change >= 0 ? "delta up" : "delta down"}>
            {money(s.day_change)} ({pct(s.day_change_pct)})
          </div>
        </Card>
        <Card title="Cost basis">
          <div className="metric num">{money(s.total_cost_basis)}</div>
        </Card>
        <Card title="Unrealized G/L">
          <div className="metric num">{money(s.unrealized_gain_loss)}</div>
        </Card>
        <Card title="YTD vs benchmark">
          <div className="metric num">{s.ytd_return_pct}%</div>
          <div className="faint">
            Benchmark {data.benchmark.ytd}% · excess {pct(data.benchmark.excess_ytd)}
          </div>
        </Card>
      </div>

      <div className="grid g-3" style={{ marginTop: 16 }}>
        <Card title="Asset allocation">
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={s.allocation} dataKey="value" nameKey="name" innerRadius={60} outerRadius={88}>
                  {s.allocation.map((_, i) => (
                    <Cell key={i} fill={CHART[i % CHART.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => money(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Sector exposure">
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={s.sectors} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => money(v)} />
                <Bar dataKey="value" fill="#132536" radius={3} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Geographic exposure">
          {s.geos.map((g) => (
            <div key={g.name} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid #eee8dd" }}>
              <span>{g.name}</span>
              <strong className="num">{g.pct}%</strong>
            </div>
          ))}
          <div className="faint" style={{ marginTop: 12 }}>
            Method: {data.risk.method}. {data.risk.limitations[0]}
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 16 }}>
        <Card title="Performance vs 60/40 blend">
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <AreaChart data={data.performance}>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={(v) => formatINRCompact(v)} />
                <Tooltip formatter={(v) => money(v)} />
                <Area type="monotone" dataKey="portfolio" stroke="#0c1b2a" fill="#cfc6b4" fillOpacity={0.35} />
                <Area type="monotone" dataKey="benchmark" stroke="#a6854d" fill="transparent" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 16 }}>
        <Card title="Holdings">
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Name</th>
                  <th className="right">Qty</th>
                  <th className="right">Price</th>
                  <th className="right">Market value</th>
                  <th className="right">Cost basis</th>
                  <th className="right">Gain/Loss</th>
                  <th className="right">Weight</th>
                </tr>
              </thead>
              <tbody>
                {s.holdings.map((h) => (
                  <tr key={h.id}>
                    <td className="sym">{h.symbol}</td>
                    <td>{h.name}</td>
                    <td className="right num">{h.quantity.toLocaleString()}</td>
                    <td className="right num">{money(h.price, 2)}</td>
                    <td className="right num">{money(h.market_value)}</td>
                    <td className="right num">{money(h.cost_basis)}</td>
                    <td className="right num" style={{ color: h.gain_loss >= 0 ? "var(--up)" : "var(--down)" }}>
                      {money(h.gain_loss)} ({pct(h.gain_loss_pct)})
                    </td>
                    <td className="right num">{h.weight}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="faint" style={{ marginTop: 10 }}>
            As of {s.as_of} · {s.assumptions[0]} · {s.limitations[0]}
          </p>
        </Card>
      </div>

      {preview && (
        <div className="modal-back" onClick={() => setPreview(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="kicker">Preview only</div>
            <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, marginTop: 0 }}>Rebalance proposal</h2>
            <p className="muted">
              This preview does not modify the book of record. Approval required before any trade.
            </p>
            <Badge tone="warn">Approval required</Badge>
            <div className="grid g-2" style={{ marginTop: 16 }}>
              <Card title="Current allocation">
                {preview.current_allocation.map((a) => (
                  <div key={a.name} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                    <span>{a.name}</span>
                    <span className="num">{a.pct}%</span>
                  </div>
                ))}
              </Card>
              <Card title="Target allocation">
                {preview.target_allocation.map((a) => (
                  <div key={a.name} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                    <span>{a.name}</span>
                    <span className="num">{a.pct}%</span>
                  </div>
                ))}
              </Card>
            </div>
            <Card title="Proposed trades" style={{ marginTop: 12 }}>
              <table className="data">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th className="right">Amount</th>
                    <th className="right">Est. gain</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.proposed_trades.map((t) => (
                    <tr key={t.symbol + t.side}>
                      <td className="sym">{t.symbol}</td>
                      <td>
                        <Status value={t.side} />
                      </td>
                      <td className="right num">{money(t.amount)}</td>
                      <td className="right num">{money(t.est_gain)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p>
                Estimated capital gains {money(preview.estimated_capital_gains)} · estimated tax impact{" "}
                {money(preview.estimated_tax_impact)}
              </p>
            </Card>
            {msg && <p className="faint">{msg}</p>}
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn" onClick={requestApproval}>
                Submit for approval
              </button>
              <button className="btn ghost" onClick={() => setPreview(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
