import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Landing() {
  const { isAuthenticated } = useAuth();
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" className="brand" style={{ padding: 0, border: 0 }}>
          <div className="brand-mark">N</div>
          <div>
            <div className="brand-name">Nexgile WealthAgent</div>
            <div className="brand-sub">Wealth intelligence</div>
          </div>
        </Link>
        <nav>
          {isAuthenticated ? (
            <Link className="btn" to="/dashboard">
              Open portal
            </Link>
          ) : (
            <>
              <Link className="btn ghost" to="/login">
                Sign in
              </Link>
              <Link className="btn" to="/signup">
                Create account
              </Link>
            </>
          )}
        </nav>
      </header>
      <section className="landing-hero">
        <p className="kicker">Private wealth platform</p>
        <h1>One book of record for families, sponsors, and advisors.</h1>
        <p>
          Nexgile WealthAgent brings portfolio, tax, estate, philanthropy, and retirement into a single authorized view —
          with AI explanations that never move money without approval.
        </p>
        <div className="landing-actions">
          <Link className="btn" to={isAuthenticated ? "/dashboard" : "/signup"}>
            {isAuthenticated ? "Continue to dashboard" : "Get started"}
          </Link>
          <Link className="btn ghost" to="/login">
            Advisor sign in
          </Link>
        </div>
      </section>
      <section className="landing-grid">
        <article>
          <h3>Authorized intelligence</h3>
          <p>Household-scoped context, calculation-engine figures, and permission-aware document retrieval.</p>
        </article>
        <article>
          <h3>India-first presentation</h3>
          <p>All financial figures use INR, the rupee symbol, and Indian grouping — ₹28,10,334.</p>
        </article>
        <article>
          <h3>Governed actions</h3>
          <p>Rebalance previews, tax harvests, and beneficiary changes require approval. The book of record is never silently mutated.</p>
        </article>
      </section>
    </div>
  );
}
