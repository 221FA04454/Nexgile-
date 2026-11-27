import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Progress, Status } from "../components/ui";

export default function Retirement() {
  const { data, loading, error, reload } = useApi(() => api.retirement(), []);
  const [view, setView] = useState("sponsor");
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const s = data.sponsor;
  const p = data.participant;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">{s.plan_name}</div>
          <h1>Retirement</h1>
          <p>{s.sponsor_name} · {s.compliance_status}</p>
        </div>
        <div className="tabs" style={{ margin: 0 }}>
          <button className={view === "sponsor" ? "tab active" : "tab"} onClick={() => setView("sponsor")}>
            Sponsor
          </button>
          <button className={view === "participant" ? "tab active" : "tab"} onClick={() => setView("participant")}>
            Participant
          </button>
        </div>
      </div>

      {view === "sponsor" ? (
        <>
          <div className="grid g-4">
            <Card title="Plan assets">
              <div className="metric num">{money(s.plan_assets)}</div>
            </Card>
            <Card title="Participation">
              <div className="metric num">{Math.round(s.participation_rate * 100)}%</div>
              <div className="faint">{s.participants.toLocaleString()} participants</div>
            </Card>
            <Card title="Avg deferral">
              <div className="metric num">{(s.avg_deferral_rate * 100).toFixed(1)}%</div>
            </Card>
            <Card title="Plan health">
              <Status value={s.plan_health} />
              <div className="faint" style={{ marginTop: 8 }}>
                Fees {s.fees_bps} bps · match {s.employer_match} · vesting {s.vesting}
              </div>
            </Card>
          </div>
          <div className="grid g-2" style={{ marginTop: 16 }}>
            <Card title="Investment lineup">
              <table className="data">
                <thead>
                  <tr>
                    <th>Fund</th>
                    <th>Ticker</th>
                    <th>Category</th>
                    <th className="right">ER</th>
                    <th className="right">YTD</th>
                  </tr>
                </thead>
                <tbody>
                  {s.lineup.map((o) => (
                    <tr key={o.ticker}>
                      <td>{o.name}</td>
                      <td className="sym">{o.ticker}</td>
                      <td>{o.category}</td>
                      <td className="right">{o.er}%</td>
                      <td className="right">{o.ytd}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
            <div>
              <Card title="Fees">
                {s.fees.map((f) => (
                  <div key={f.type} className="activity">
                    <div style={{ flex: 1 }}>
                      {f.type} · {f.notes}
                    </div>
                    <strong>{f.bps} bps</strong>
                  </div>
                ))}
              </Card>
              <div style={{ height: 16 }} />
              <Card title="Compliance tests">
                {s.tests.map((t) => (
                  <div key={t.name} className="activity">
                    <div style={{ flex: 1 }}>
                      {t.name} {t.year}
                      <div className="faint">{t.notes}</div>
                    </div>
                    <Status value={t.result} />
                  </div>
                ))}
              </Card>
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="grid g-4">
            <Card title="Account balance">
              <div className="metric num">{money(p.balance)}</div>
            </Card>
            <Card title="Employee YTD">
              <div className="metric num">{money(p.employee_ytd)}</div>
            </Card>
            <Card title="Employer match YTD">
              <div className="metric num">{money(p.employer_ytd)}</div>
            </Card>
            <Card title="Vested">
              <div className="metric num">{p.vested_pct}%</div>
            </Card>
          </div>
          <div className="grid g-2" style={{ marginTop: 16 }}>
            <Card title="Retirement readiness">
              <div className="metric num">{p.readiness.score}</div>
              <Progress value={p.readiness.score} />
              <p>
                Status <Status value={p.readiness.status} /> · income replacement {p.readiness.income_replacement}%
              </p>
              <p className="faint">
                {p.readiness.assumptions[0]} · {p.readiness.limitations[0]}
              </p>
            </Card>
            <Card title="Income projection & beneficiaries">
              <div>Projected retirement income {money(p.income_projection)} / year (today’s rupees)</div>
              <div>Contribution rate {(p.contribution_rate * 100).toFixed(0)}%</div>
              <ul>
                {p.beneficiaries.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
