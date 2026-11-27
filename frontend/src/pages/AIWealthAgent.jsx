import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/ui";

export const SUGGESTED_PROMPTS = [
  "How is my portfolio performing?",
  "What tax opportunities do I have?",
  "Am I on track for retirement?",
  "What documents need my attention?",
  "Summarize my household finances.",
];

export default function AIWealthAgent() {
  const [log, setLog] = useState([
    {
      role: "assistant",
      text: "I answer from your authorized household book of record as of September 7, 2026. I do not place trades or give advice.",
    },
  ]);
  const [text, setText] = useState("");
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.aiStatus().then(setStatus).catch(() => {});
  }, []);

  async function send(message) {
    const q = (message || text).trim();
    if (!q) return;
    setText("");
    setLog((l) => [...l, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.chat(q);
      setLog((l) => [...l, { role: "assistant", text: res.answer || res.reply }]);
      setMeta(res);
    } catch (e) {
      setLog((l) => [...l, { role: "assistant", text: e.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="kicker">Assistant</div>
          <h1>AI WealthAgent</h1>
          <p>Permission-aware answers with sources, as-of date, assumptions, and advisor review. Not financial advice.</p>
        </div>
        {status && (
          <div className="chip">
            {status.provider} · RAG {status.rag_backend}
          </div>
        )}
      </div>
      <div className="chat-page">
        <Card>
          <div className="prompts">
            {SUGGESTED_PROMPTS.map((p) => (
              <button key={p} onClick={() => send(p)}>
                {p}
              </button>
            ))}
          </div>
          <div className="chat-log">
            {log.map((m, i) => (
              <div key={i} className={m.role === "user" ? "bubble user" : "bubble"}>
                {m.text}
              </div>
            ))}
            {busy && <div className="faint">Consulting the authorized book of record…</div>}
          </div>
          <form
            className="chat-input"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask about the household book…" />
            <button className="btn" disabled={busy}>
              Send
            </button>
          </form>
        </Card>
        <div>
          <Card title="Answer context">
            {meta ? (
              <>
                <div className="faint">Answer</div>
                <p>{meta.answer || meta.reply}</p>
                <div className="faint">As of</div>
                <p>{meta.as_of}</p>
                <div className="faint">Sources</div>
                <ul>
                  {(meta.sources || []).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <div className="faint">Assumptions</div>
                <ul>
                  {(meta.assumptions || []).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <div className="faint">Limitations</div>
                <ul>
                  {(meta.limitations || []).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <div className="chip" style={{ marginTop: 8 }}>
                  Advisor review required
                </div>
                {meta.intent === "TAX_OPPORTUNITY" && (
                  <p>
                    <Link to="/tax">Review Opportunity</Link>
                  </p>
                )}
                {meta.intent === "DOCUMENT_QUERY" && (
                  <p>
                    <Link to="/documents">Open document vault</Link>
                  </p>
                )}
                <p className="faint">{meta.advisor_review_indicator}</p>
                <p className="faint">{meta.disclaimer}</p>
              </>
            ) : (
              <p className="faint">Send a question to load sources, assumptions, and limitations.</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
