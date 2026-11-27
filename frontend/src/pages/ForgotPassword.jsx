import { useState } from "react";
import { Link } from "react-router-dom";
import { authService } from "../auth/authService";
import AuthLayout from "../auth/AuthLayout";
import { Button, TextInput } from "../components/ui";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!email.trim()) {
      setError("Enter the email associated with your account.");
      return;
    }
    setBusy(true);
    try {
      const res = await authService.forgotPassword(email);
      setSent(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Reset your password">
      {sent ? (
        <>
          <p role="status">{sent.message}</p>
          {sent.development?.reset_url && (
            <p className="dev-banner">
              Development reset link is available.{" "}
              <Link to={sent.development.reset_url.replace(/^https?:\/\/[^/]+/, "")}>Continue</Link>
            </p>
          )}
          <p className="auth-foot">
            <Link to="/login">Return to sign in</Link>
          </p>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <p className="muted">We will send instructions if an account exists for that email.</p>
          <TextInput id="forgot-email" label="Email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
          {error && (
            <p className="form-alert" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" busy={busy} style={{ width: "100%" }}>
            Send reset instructions
          </Button>
          <p className="auth-foot">
            <Link to="/login">Back to sign in</Link>
          </p>
        </form>
      )}
    </AuthLayout>
  );
}
