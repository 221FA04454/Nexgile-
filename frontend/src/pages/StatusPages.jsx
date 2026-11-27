import { Link } from "react-router-dom";

function StatusPage({ code, title, body, action }) {
  return (
    <div className="status-page">
      <div className="auth-card">
        <div className="kicker">{code}</div>
        <h1>{title}</h1>
        <p className="muted">{body}</p>
        {action}
      </div>
    </div>
  );
}

export function Unauthorized() {
  return (
    <StatusPage
      code="401"
      title="Sign in required"
      body="Your session is missing or has expired. Sign in again to continue."
      action={
        <Link className="btn" to="/login">
          Sign in
        </Link>
      }
    />
  );
}

export function Forbidden() {
  return (
    <StatusPage
      code="403"
      title="You do not have access"
      body="This area is limited to authorized roles. Return to your portal or contact your advisor."
      action={
        <Link className="btn" to="/dashboard">
          Return to portal
        </Link>
      }
    />
  );
}

export function NotFound() {
  return (
    <StatusPage
      code="404"
      title="Page not found"
      body="That address is not part of the WealthAgent portal."
      action={
        <Link className="btn" to="/">
          Go home
        </Link>
      }
    />
  );
}

export function ServerError() {
  return (
    <StatusPage
      code="500"
      title="Something went wrong"
      body="The wealth service could not complete this request. Try again shortly."
      action={
        <Link className="btn ghost" to="/dashboard">
          Return to portal
        </Link>
      }
    />
  );
}
