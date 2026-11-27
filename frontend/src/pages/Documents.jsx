import { useState } from "react";
import { api } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Card, ErrorState, Loading, Status } from "../components/ui";

const CATS = ["All", "Tax", "Estate", "Trust", "Investment", "Retirement", "Statements", "Other"];

export default function Documents() {
  const { data, loading, error, reload } = useApi(() => api.documents(), []);
  const [cat, setCat] = useState("All");
  const [msg, setMsg] = useState("");

  async function onFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await api.uploadDocument(file);
      setMsg(`Stored metadata for ${res.name}. AI classification: ${res.ai_classification}.`);
      reload();
    } catch (err) {
      setMsg(err.message);
    }
  }

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const rows = (data.documents || []).filter((d) => cat === "All" || d.category === cat);

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Vault</div>
          <h1>Documents</h1>
          <p>Classification is model-assisted and should be confirmed by the document owner.</p>
        </div>
        <label className="btn" style={{ display: "inline-block" }}>
          Upload
          <input type="file" hidden onChange={onFile} />
        </label>
      </div>
      <div className="tabs">
        {CATS.map((c) => (
          <button key={c} className={cat === c ? "tab active" : "tab"} onClick={() => setCat(c)}>
            {c}
          </button>
        ))}
      </div>
      {msg && <p className="faint">{msg}</p>}
      <Card title={`${rows.length} files`}>
        {rows.length === 0 ? (
          <div className="state">No documents in this category.</div>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Uploaded</th>
                <th>Version</th>
                <th>Expiry / review</th>
                <th>Owner</th>
                <th>Status</th>
                <th>AI class</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{d.type}</td>
                  <td>{d.uploaded_on}</td>
                  <td>{d.version}</td>
                  <td>{d.expiry_or_review || "—"}</td>
                  <td>{d.owner}</td>
                  <td>
                    <Status value={d.status.replace("_", " ")} />
                  </td>
                  <td className="faint">{d.ai_classification}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
