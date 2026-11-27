import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, Status } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export default function Integrations() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useApi(() => api.integrations(), []);
  const recon = useApi(() => api.integrationReconciliation(), []);
  const status = useApi(() => api.integrationsStatus(), []);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  async function sync(provider) {
    setBusy(provider);
    setNotice("");
    try {
      const res = await api.integrationSync(provider);
      setNotice(`${provider}: ${res.status} · received ${res.records_received || 0}`);
      reload();
      recon.reload();
      status.reload();
    } catch (e) {
      setNotice(e.message);
    } finally {
      setBusy("");
    }
  }

  if (user && !["ADVISOR", "ADMIN"].includes(user.role)) {
    return (
      <Card title="Integrations">
        <p>Integration operations are limited to advisor and admin roles.</p>
      </Card>
    );
  }
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const rows = data?.integrations || [];
  const exceptions = recon.data?.exceptions || [];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Operations</div>
          <h1>Integrations</h1>
          <p>Sandbox providers only. PostgreSQL remains the book of record. No live trades, messages, or credentials.</p>
        </div>
        {status.data && (
          <div className="chip">
            {status.data.providers} providers · {status.data.open_reconciliation} recon · live {status.data.live_providers}
          </div>
        )}
      </div>
      {notice && <p className="faint">{notice}</p>}
      <Card title="Providers">
        <table className="data">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Category</th>
              <th>Status</th>
              <th>Last sync</th>
              <th>Freshness</th>
              <th className="right">Records</th>
              <th>Retry</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.provider}>
                <td>
                  <strong>{r.name}</strong>
                  <div className="faint">{r.provider}</div>
                </td>
                <td>{r.category}</td>
                <td>
                  <Status value={r.status} />
                </td>
                <td>{r.last_sync ? String(r.last_sync).slice(0, 19) : "—"}</td>
                <td>
                  <Status value={r.freshness} />
                </td>
                <td className="right num">{r.records_processed}</td>
                <td>{r.retry_status}</td>
                <td>
                  <button className="btn ghost" disabled={busy === r.provider} onClick={() => sync(r.provider)}>
                    {busy === r.provider ? "Syncing…" : "Sync"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div style={{ marginTop: 16 }}>
        <Card title="Reconciliation exceptions">
          {exceptions.length === 0 && <p className="faint">No open exceptions. Unmatched inbound records are held for review and never auto-inserted.</p>}
          {exceptions.map((ex) => (
            <div className="activity" key={ex.id}>
              <div style={{ flex: 1 }}>
                <strong>
                  {ex.provider} · {ex.type}
                </strong>
                <div className="faint">
                  {ex.entity_type} {ex.external_id} · {ex.status}
                </div>
              </div>
              <Status value={ex.severity} />
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
