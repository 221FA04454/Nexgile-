import { Link } from "react-router-dom";

export default function AuthLayout({ kicker, title, children, footer }) {
  return (
    <div className="auth-shell">
      <aside className="auth-brand" aria-label="Nexgile WealthAgent">
        <Link to="/" className="brand" style={{ padding: 0, border: 0 }}>
          <div className="brand-mark">N</div>
          <div>
            <div className="brand-name">Nexgile WealthAgent</div>
            <div className="brand-sub">Private client</div>
          </div>
        </Link>
        <div>
          <p className="auth-kicker">{kicker || "Discretion. Clarity. Stewardship."}</p>
          <h1>Institutional wealth, held to a private-client standard.</h1>
          <p>
            Portfolio construction, tax-aware planning, estate readiness, and retirement plan health — with an AI
            assistant that never trades without approval.
          </p>
        </div>
        <ul className="auth-trust">
          <li>Bank-grade session security</li>
          <li>Household-scoped authorization</li>
          <li>Books of record in INR (₹)</li>
        </ul>
        <p className="faint">Not an offer of securities. © 2026 Nexgile</p>
      </aside>
      <main className="auth-main">
        <div className="auth-card">
          <div className="kicker">Secure access</div>
          <h2>{title}</h2>
          {children}
          {footer}
        </div>
      </main>
    </div>
  );
}
