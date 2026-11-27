import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Status } from "../components/ui";

export default function Tax() {
  const { data, loading, error, reload } = useApi(() => api.tax(), []);
  const [note, setNote] = useState("");

  async function submitHarvest() {
    const res = await api.createApproval({
      action: "tax_harvest",
      entity_type: "Harvest",
      entity_id: "batch-2026-09",
      notes: "Harvest INTC, NKE; BND on watch",
      new_value: { symbols: ["INTC", "NKE"] },
    });
    setNote(`Approval #${res.id} queued. No lots have been sold.`);
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Tax overlay</div>
          <h1>Tax opportunities</h1>
          <p>Federal illustration only. California and AMT are not modeled. Harvests require approval.</p>
        </div>
        <button className="btn" onClick={submitHarvest}>
          Submit harvest for approval
        </button>
      </div>
      <div className="grid g-4">
        <Card title="Estimated tax liability">
          <div className="metric num">{money(data.estimated_liability)}</div>
        </Card>
        <Card title="Capital gains budget">
          <div className="metric num">{money(data.capital_gains_budget.remaining)}</div>
          <div className="faint">
            Used {money(data.capital_gains_budget.used)} of {money(data.capital_gains_budget.limit)}
          </div>
        </Card>
        <Card title="Carryforward losses">
          <div className="metric num">{money(data.carryforward_losses)}</div>
        </Card>
        <Card title="RMD status">
          <div className="metric-sm">{data.rmd.status.replace("_", " ")}</div>
          <div className="faint">First projected year 2052</div>
        </Card>
      </div>
      <div className="grid g-2" style={{ marginTop: 16 }}>
        {data.opportunities.map((o) => (
          <Card key={o.id} title={o.type.replace("_", " ")}>
            <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, margin: "0 0 8px", fontSize: 20 }}>{o.title}</h2>
            <p className="muted">{o.detail}</p>
            {o.benefit > 0 && <div>Estimated benefit {money(o.benefit)}</div>}
            <Status value={o.status} />
          </Card>
        ))}
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Tax-loss harvesting">
          <table className="data">
            <thead>
              <tr>
                <th>Security</th>
                <th className="right">Unrealized loss</th>
                <th className="right">Potential tax benefit</th>
                <th>Wash sale</th>
                <th>Replacement</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.harvests.map((h) => (
                <tr key={h.id}>
                  <td>
                    <div className="sym">{h.symbol}</div>
                    <div className="faint">{h.name}</div>
                  </td>
                  <td className="right num" style={{ color: "var(--down)" }}>
                    {money(h.unrealized_loss)}
                  </td>
                  <td className="right num">{money(h.potential_tax_benefit)}</td>
                  <td>
                    <Status value={h.wash_sale_status} />
                  </td>
                  <td className="sym">{h.replacement}</td>
                  <td>
                    <Status value={h.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.wash_sales.map((w) => (
            <p className="faint" key={w.symbol}>
              Wash-sale window {w.symbol}: {w.start} → {w.end}
            </p>
          ))}
          {note && <p>{note}</p>}
        </Card>
      </div>
    </div>
  );
}
