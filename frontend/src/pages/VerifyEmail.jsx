import { useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";
import { authService } from "../auth/authService";
import AuthLayout from "../auth/AuthLayout";
import { Button, TextInput } from "../components/ui";

export default function VerifyEmail() {
  const location = useLocation();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(location.state?.email || "");
  const [otp, setOtp] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const dev = location.state?.development;

  useEffect(() => {
    const token = params.get("token");
    if (!token) return;
    setBusy(true);
    authService
      .verifyEmail({ token })
      .then((res) => setStatus(res.message))
      .catch((err) => setError(err.message || "This link is invalid or has expired."))
      .finally(() => setBusy(false));
  }, [params]);

  async function submitOtp(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await authService.verifyEmail({ otp });
      setStatus(res.message);
    } catch (err) {
      setError(err.message || "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError("");
    setBusy(true);
    try {
      const res = await authService.resendVerification(email);
      setStatus(res.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Verify your email">
      {status ? (
        <>
          <p role="status">{status}</p>
          <Link className="btn" to="/login" style={{ display: "inline-block", marginTop: 16 }}>
            Continue to sign in
          </Link>
        </>
      ) : (
        <>
          <p className="muted">Enter the six-digit code from your verification message, or open the link we sent.</p>
          {dev?.otp && (
            <p className="dev-banner">Development code: {dev.otp}. This banner is never shown in production.</p>
          )}
          <form onSubmit={submitOtp}>
            <TextInput id="otp" label="Verification code" inputMode="numeric" value={otp} onChange={(e) => setOtp(e.target.value)} />
            {error && (
              <p className="form-alert" role="alert">
                {error}
              </p>
            )}
            <Button type="submit" busy={busy} style={{ width: "100%" }}>
              Verify
            </Button>
          </form>
          <div className="auth-row" style={{ marginTop: 16 }}>
            <TextInput id="resend-email" label="Resend to email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <button type="button" className="btn ghost" onClick={resend} disabled={!email || busy}>
            Resend verification
          </button>
        </>
      )}
    </AuthLayout>
  );
}
