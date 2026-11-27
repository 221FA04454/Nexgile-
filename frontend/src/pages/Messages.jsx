import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, Status } from "../components/ui";

export default function Messages() {
  const { data, loading, error, reload } = useApi(() => api.messages(), []);
  const [active, setActive] = useState(null);
  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const list = data.messages || [];
  const current = list.find((m) => m.id === active) || list[0];

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Secure messaging</div>
          <h1>Messages</h1>
          <p>Archived for compliance. Do not send trading instructions by email.</p>
        </div>
      </div>
      <div className="grid g-sidebar">
        <Card title="Inbox">
          {list.map((m) => (
            <button
              key={m.id}
              className="demo-role"
              style={{ width: "100%", marginBottom: 8, borderColor: current?.id === m.id ? "var(--gold)" : undefined }}
              onClick={() => setActive(m.id)}
            >
              <strong>{m.subject}</strong>
              <span>
                {m.sender} · {m.role} · {m.read ? "Read" : "Unread"}
              </span>
            </button>
          ))}
        </Card>
        {current && (
          <Card title="Thread">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, marginTop: 0 }}>{current.subject}</h2>
              <Status value={current.read ? "read" : "unread"} />
            </div>
            <p className="faint">
              {current.sender} · {current.created_at}
            </p>
            <p>{current.body}</p>
          </Card>
        )}
      </div>
    </div>
  );
}
