import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { authService } from "../auth/authService";
import { PASSWORD_RULES } from "../auth/sessionManager";
import AuthLayout from "../auth/AuthLayout";
import { Button, PasswordInput } from "../components/ui";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  const rules = useMemo(() => PASSWORD_RULES.map((r) => ({ ...r, ok: r.test(password) })), [password]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (rules.some((r) => !r.ok)) {
      setError("Password does not meet the requirements.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (!token) {
      setError("This reset link is invalid or has expired.");
      return;
    }
    setBusy(true);
    try {
      const res = await authService.resetPassword({ token, password, confirm_password: confirm });
      setDone(res.message);
    } catch (err) {
      setError(err.message || "This reset link is invalid or has expired.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Choose a new password">
      {done ? (
        <>
          <p role="status">{done}</p>
          <Link className="btn" to="/login" style={{ display: "inline-block", marginTop: 16 }}>
            Sign in
          </Link>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <PasswordInput id="new-pass" label="New password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <ul className="pw-rules">
            {rules.map((r) => (
              <li key={r.id} className={r.ok ? "ok" : ""}>
                {r.label}
              </li>
            ))}
          </ul>
          <PasswordInput id="confirm-pass" label="Confirm new password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          {error && (
            <p className="form-alert" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" busy={busy} style={{ width: "100%" }}>
            Update password
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
