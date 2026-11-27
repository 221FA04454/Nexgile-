import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, money, Status } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function Advisor() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useApi(() => api.advisorClients(), []);
  const [detail, setDetail] = useState(null);
  const [detailErr, setDetailErr] = useState("");

  async function open(id) {
    setDetailErr("");
    try {
      setDetail(await api.client360(id));
    } catch (e) {
      setDetailErr(e.message);
    }
  }

  if (user && !["ADVISOR", "ADMIN"].includes(user.role)) {
    return (
      <Card title="Advisor workstation">
        <p>This workstation is limited to advisor and admin roles. Sign in as Sarah Wilson to continue.</p>
      </Card>
    );
  }
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Private client group</div>
          <h1>Advisor workstation</h1>
          <p>Book of households under coverage. Open a row for the client 360 and meeting prep.</p>
        </div>
      </div>
      {detailErr && <p style={{ color: "var(--down)" }}>{detailErr}</p>}
      <Card title="Clients">
        <table className="data">
          <thead>
            <tr>
              <th>Client</th>
              <th>Household</th>
              <th className="right">AUM</th>
              <th>Risk</th>
              <th>Goals</th>
              <th>Tax opportunity</th>
              <th>Next meeting</th>
              <th>Alerts</th>
            </tr>
          </thead>
          <tbody>
            {data.clients.map((c) => (
              <tr key={c.id} onClick={() => open(c.id)} style={{ cursor: "pointer" }}>
                <td>{c.client}</td>
                <td>{c.household}</td>
                <td className="right num">{money(c.aum)}</td>
                <td>{c.risk}</td>
                <td>{c.goals}</td>
                <td>
                  <Status value={c.tax_opportunity ? "yes" : "none"} />
                </td>
                <td>{String(c.next_meeting).slice(0, 16)}</td>
                <td>{c.alerts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div style={{ marginTop: 16 }}>
        <Card title="Tasks">
          {data.tasks.map((t) => (
            <div className="activity" key={t.id}>
              <div style={{ flex: 1 }}>
                <strong>{t.title}</strong>
                <div className="faint">
                  {t.owner} · due {t.due}
                </div>
              </div>
              <Status value={t.priority} />
              <Status value={t.status.replace("_", " ")} />
            </div>
          ))}
        </Card>
      </div>
      {detail && !detail.error && (
        <div className="modal-back" onClick={() => setDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="kicker">Client 360</div>
            <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, marginTop: 0 }}>
              {detail.household.client} · {detail.household.name}
            </h2>
            <div className="grid g-4">
              <div>
                <div className="faint">Net worth</div>
                <strong className="num">{money(detail.net_worth.total)}</strong>
              </div>
              <div>
                <div className="faint">Invested</div>
                <strong className="num">{money(detail.portfolio.invested_assets)}</strong>
              </div>
              <div>
                <div className="faint">YTD</div>
                <strong>{detail.portfolio.ytd_return}%</strong>
              </div>
              <div>
                <div className="faint">Risk</div>
                <strong>{detail.household.risk}</strong>
              </div>
            </div>
            <h3>Accounts</h3>
            {detail.accounts.map((a) => (
              <div key={a.id} className="activity">
                <div style={{ flex: 1 }}>{a.name}</div>
                <span className="num">{money(a.market_value)}</span>
              </div>
            ))}
            <h3>Goals</h3>
            {detail.goals.map((g) => (
              <div key={g.id} className="faint">
                {g.category}: {g.pct}% · {g.projected_status}
              </div>
            ))}
            <h3>Meeting preparation</h3>
            <p>
              {detail.meeting_prep.title} · {detail.meeting_prep.when}
            </p>
            <p>{detail.meeting_prep.agenda}</p>
            <ul>
              {detail.meeting_prep.talking_points.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
            <h3>Open tasks</h3>
            {detail.tasks.map((t) => (
              <div key={t.id}>
                {t.title} — {t.due} ({t.status})
              </div>
            ))}
            <button className="btn ghost" style={{ marginTop: 16 }} onClick={() => setDetail(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
