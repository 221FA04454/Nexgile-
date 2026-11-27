import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, Status } from "../components/ui";

export default function Reports() {
  const { data, loading, error, reload } = useApi(() => api.reports(), []);
  const [preview, setPreview] = useState(null);

  async function open(id) {
    const p = await api.report(id);
    setPreview(p);
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Client reporting</div>
          <h1>Reports</h1>
          <p>Select a pack to preview. Production will export PDF/ICS with compliance archive.</p>
        </div>
      </div>
      <div className="grid g-3">
        {data.reports.map((r) => (
          <button key={r.id} className="card" style={{ textAlign: "left" }} onClick={() => open(r.id)}>
            <h3>{r.type.replaceAll("_", " ")}</h3>
            <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500, margin: "0 0 8px", fontSize: 20 }}>{r.name}</h2>
            <p className="faint">{r.summary}</p>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{r.period}</span>
              <Status value={r.status} />
            </div>
          </button>
        ))}
      </div>
      {preview && (
        <div className="modal-back" onClick={() => setPreview(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="kicker">Confidential — {preview.as_of}</div>
            <h2 style={{ fontFamily: "var(--serif)", fontWeight: 500 }}>
              {preview.report.name}
            </h2>
            <p>
              Prepared for {preview.prepared_for} · {preview.household}
              <br />
              Prepared by {preview.prepared_by}
            </p>
            {preview.sections.map((s) => (
              <div key={s.heading} style={{ margin: "16px 0" }}>
                <h3>{s.heading}</h3>
                <p>{s.body}</p>
              </div>
            ))}
            <p className="faint">{preview.disclaimer}</p>
            <button className="btn ghost" onClick={() => setPreview(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
