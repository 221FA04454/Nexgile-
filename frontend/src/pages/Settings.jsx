import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";
import { Card, Status } from "../components/ui";

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [approvals, setApprovals] = useState([]);
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    api.approvals().then((d) => setApprovals(d.approvals || [])).catch(() => {});
    api.health().then(setHealth).catch(() => {});
    api.authSessions().then((d) => setSessions(d.sessions || [])).catch(() => {});
  }, []);

  async function decide(id, status) {
    await api.decideApproval(id, status, "Portal decision");
    const d = await api.approvals();
    setApprovals(d.approvals || []);
  }

  async function revoke(id) {
    await api.revokeSession(id);
    const d = await api.authSessions();
    setSessions(d.sessions || []);
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Preferences</div>
          <h1>Settings</h1>
          <p>Profile, session security, and approval queue.</p>
        </div>
      </div>
      <div className="grid g-2">
        <Card title="Signed-in profile">
          <p>
            <strong>{user?.name}</strong>
            <br />
            {user?.email}
            <br />
            {user?.title}
          </p>
          <span className="role-pill">{user?.role}</span>
          <p className="faint">
            Email {user?.email_verified ? "verified" : "unverified"} · MFA {user?.mfa_enabled ? "enabled" : "not enabled"}
          </p>
          <button
            className="btn ghost"
            style={{ marginTop: 12 }}
            onClick={async () => {
              await logout();
              navigate("/login", { replace: true });
            }}
          >
            Sign out
          </button>
        </Card>
        <Card title="Platform">
          <p>As-of date: September 7, 2026</p>
          <p>Book currency: INR (₹ · en-IN)</p>
          <p>API health: {health?.status || "unknown"}</p>
          <p>
            Database: {health?.database?.backend || "—"} ({health?.database?.status || "unknown"})
          </p>
          <p>
            Redis: {health?.redis?.backend || "—"} ({health?.redis?.status || "unknown"})
          </p>
          <p className="faint">Optional LLM generation is configured on the API server only. The browser never receives provider credentials.</p>
        </Card>
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Active sessions">
          {sessions.length === 0 && <p className="faint">No sessions.</p>}
          {sessions.map((s) => (
            <div className="activity" key={s.id}>
              <div style={{ flex: 1 }}>
                <strong>{s.revoked ? "Revoked" : "Active"}</strong>
                <div className="faint">{s.user_agent || "Unknown device"}</div>
                <div className="faint">
                  {s.ip_address} · {s.created_at}
                </div>
              </div>
              {!s.revoked && (
                <button className="btn ghost" onClick={() => revoke(s.id)}>
                  Revoke
                </button>
              )}
            </div>
          ))}
        </Card>
      </div>
      <div style={{ marginTop: 16 }}>
        <Card title="Approval queue">
          {approvals.length === 0 && <p className="faint">No approvals.</p>}
          {approvals.map((a) => (
            <div className="activity" key={a.id}>
              <div style={{ flex: 1 }}>
                <strong>
                  {a.action} · {a.entity_type}
                </strong>
                <div className="faint">
                  {a.requested_by} · {a.created_at}
                </div>
                <div className="faint">{a.notes}</div>
              </div>
              <Status value={a.status} />
              {a.status === "pending" && (
                <>
                  <button className="btn" onClick={() => decide(a.id, "approved")}>
                    Approve
                  </button>
                  <button className="btn danger" onClick={() => decide(a.id, "rejected")}>
                    Reject
                  </button>
                </>
              )}
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}
