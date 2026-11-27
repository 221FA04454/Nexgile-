import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Progress, Status } from "../components/ui";

const LABELS = {
  will: "Will",
  trust: "Trust",
  power_of_attorney: "Power of attorney",
  healthcare_directive: "Healthcare directive",
};

export default function Estate() {
  const { data, loading, error, reload } = useApi(() => api.estate(), []);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Estate readiness</div>
          <h1>Estate & trusts</h1>
          <p>
            Counsel {data.attorney} · last review {data.last_review} · next {data.next_review}
          </p>
        </div>
        <div>
          <div className="faint">Readiness</div>
          <div className="metric num">{data.readiness_score}</div>
        </div>
      </div>
      <Card title="Document status">
        <Progress value={data.readiness_score} />
        <div className="grid g-4" style={{ marginTop: 16 }}>
          {Object.entries(data.documents).map(([k, v]) => (
            <div key={k} className="card" style={{ boxShadow: "none" }}>
              <div className="faint">{LABELS[k] || k}</div>
              <div style={{ marginTop: 8 }}>
                <Status value={v.replace("_", " ")} />
              </div>
            </div>
          ))}
        </div>
      </Card>
      <div className="grid g-2" style={{ marginTop: 16 }}>
        <Card title="Trust assets">
          {data.trusts.map((t) => (
            <div key={t.id} className="activity">
              <div style={{ flex: 1 }}>
                <strong>{t.name}</strong>
                <div className="faint">
                  {t.type} · trustee {t.trustee}
                </div>
              </div>
              <div>
                <div className="num">{money(t.assets)}</div>
                <Status value={t.funded ? "funded" : "unfunded"} />
              </div>
            </div>
          ))}
          <p>
            Estate tax exposure (illustrative) {money(data.estate_tax_exposure)} — federal exemption assumed unused
            portion only.
          </p>
        </Card>
        <Card title="Beneficiaries">
          <table className="data">
            <thead>
              <tr>
                <th>Name</th>
                <th>Relationship</th>
                <th>Account / trust</th>
                <th className="right">Share</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data.beneficiaries.map((b) => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td>{b.relationship}</td>
                  <td>{b.account}</td>
                  <td className="right num">{b.share_pct}%</td>
                  <td>{b.contingent ? "Contingent" : "Primary"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Review reminders">
          {data.reminders.map((r) => (
            <div className="insight warn" key={r.title}>
              <div className="tick" />
              <div>
                <strong>{r.title}</strong>
                <div className="faint">Due {r.due}</div>
              </div>
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
