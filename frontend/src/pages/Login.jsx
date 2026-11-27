import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";
import { homeForRole } from "../auth/sessionManager";
import AuthLayout from "../auth/AuthLayout";
import { Button, PasswordInput, TextInput } from "../components/ui";

export const DEMOS = [
  { role: "CLIENT", name: "Alex Morgan", email: "alex.morgan@nexgile.demo", note: "Household principal" },
  { role: "ADVISOR", name: "Sarah Wilson", email: "sarah.wilson@nexgile.demo", note: "Private client group" },
  { role: "SPONSOR", name: "Maria Chen", email: "maria.chen@nexgile.demo", note: "Helios Dynamics 401(k)" },
  { role: "PARTICIPANT", name: "Priya Shah", email: "priya.shah@nexgile.demo", note: "Plan participant" },
  { role: "ADMIN", name: "Platform Admin", email: "admin@nexgile.demo", note: "Operations" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    api
      .publicConfig()
      .then((c) => {
        setDemo(Boolean(c.demo_login_enabled));
        if (c.demo_login_enabled) {
          setEmail("alex.morgan@nexgile.demo");
          setPassword("demo123");
        }
      })
      .catch(() => setDemo(false));
  }, []);

  function validate() {
    const next = {};
    if (!email.trim()) next.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email address.";
    if (!password) next.password = "Password is required.";
    setFieldErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setBusy(true);
    try {
      const user = await login(email, password, remember);
      const from = location.state?.from;
      navigate(from && from !== "/login" ? from : homeForRole(user.role), { replace: true });
    } catch (err) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Sign in to the portal">
      {demo ? (
        <>
          <p className="muted">Development directory is enabled for this environment only.</p>
          <div className="demo-roles" role="list">
            {DEMOS.map((d) => (
              <button
                type="button"
                key={d.email}
                className={email === d.email ? "demo-role active" : "demo-role"}
                onClick={() => setEmail(d.email)}
              >
                <strong>
                  {d.name} · {d.role}
                </strong>
                <span>{d.note}</span>
              </button>
            ))}
          </div>
        </>
      ) : (
        <p className="muted">Use your organization credentials.</p>
      )}
      <form onSubmit={submit} noValidate>
        <TextInput
          id="login-email"
          label="Email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />
        <PasswordInput
          id="login-password"
          label="Password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
        />
        <div className="auth-row">
          <label className="check">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            Remember this device
          </label>
          <Link to="/forgot-password">Forgot password</Link>
        </div>
        {error && (
          <p className="form-alert" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" busy={busy} style={{ width: "100%", marginTop: 8 }}>
          Sign in
        </Button>
      </form>
      <p className="auth-foot">
        New to WealthAgent? <Link to="/signup">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
