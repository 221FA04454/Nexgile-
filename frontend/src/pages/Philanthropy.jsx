import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Progress, Status } from "../components/ui";

export default function Philanthropy() {
  const { data, loading, error, reload } = useApi(() => api.philanthropy(), []);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const p = data.plan;
  const pctDone = Math.round((p.donated_ytd / p.annual_target) * 100);

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Giving plan</div>
          <h1>Philanthropy</h1>
          <p>{p.mission}</p>
        </div>
      </div>
      <div className="grid g-4">
        <Card title="Annual target">
          <div className="metric num">{money(p.annual_target)}</div>
        </Card>
        <Card title="Donated YTD">
          <div className="metric num">{money(p.donated_ytd)}</div>
          <Progress value={pctDone} />
        </Card>
        <Card title="Remaining">
          <div className="metric num">{money(p.remaining)}</div>
        </Card>
        <Card title="Tax deduction estimate">
          <div className="metric num">{money(p.tax_deduction_estimate)}</div>
        </Card>
      </div>
      <div className="grid g-3" style={{ marginTop: 16 }}>
        <Card title="Donor-advised fund">
          <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, marginTop: 0 }}>{data.daf.name}</h2>
          <div>Balance {money(data.daf.balance)}</div>
          <div>YTD grants {money(data.daf.ytd_grants)}</div>
          <div className="faint">{data.daf.sponsor}</div>
        </Card>
        <Card title="Private foundation">
          <Status value={data.foundation.status.replace("_", " ")} />
          <p className="faint">{data.foundation.note}</p>
        </Card>
        <Card title="Qualified charitable distribution">
          <Status value={data.qcd.eligible ? "eligible" : "not yet eligible"} />
          <p className="faint">{data.qcd.reason}</p>
        </Card>
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Charitable gifts & securities">
          <table className="data">
            <thead>
              <tr>
                <th>Charity</th>
                <th>Type</th>
                <th className="right">Amount</th>
                <th className="right">Deduction</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.gifts.map((g) => (
                <tr key={g.id}>
                  <td>{g.charity}</td>
                  <td>{g.type}</td>
                  <td className="right num">{money(g.amount)}</td>
                  <td className="right num">{money(g.deduction)}</td>
                  <td>{g.date}</td>
                  <td>
                    <Status value={g.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
