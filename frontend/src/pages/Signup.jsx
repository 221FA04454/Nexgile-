import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../auth/authService";
import { PASSWORD_RULES } from "../auth/sessionManager";
import AuthLayout from "../auth/AuthLayout";
import { Button, PasswordInput, TextInput } from "../components/ui";

export default function Signup() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    password: "",
    confirm_password: "",
    accept_terms: false,
  });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const ruleState = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, ok: r.test(form.password) })),
    [form.password]
  );

  function validate() {
    const next = {};
    if (!form.first_name.trim()) next.first_name = "First name is required.";
    if (!form.last_name.trim()) next.last_name = "Last name is required.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = "Enter a valid email address.";
    if (ruleState.some((r) => !r.ok)) next.password = "Password does not meet the requirements.";
    if (form.password !== form.confirm_password) next.confirm_password = "Passwords do not match.";
    if (!form.accept_terms) next.accept_terms = "You must accept the Terms and Privacy Policy.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!validate()) return;
    setBusy(true);
    try {
      const res = await authService.signup(form);
      navigate("/verify-email", {
        replace: true,
        state: { email: form.email, development: res.development },
      });
    } catch (err) {
      setError(err.message || "We could not create your account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Create your account">
      <p className="muted">Client registration. Advisor and sponsor access is provisioned by your firm.</p>
      <form onSubmit={submit} noValidate>
        <div className="field-grid">
          <TextInput id="first" label="First name" autoComplete="given-name" value={form.first_name} onChange={set("first_name")} error={errors.first_name} />
          <TextInput id="last" label="Last name" autoComplete="family-name" value={form.last_name} onChange={set("last_name")} error={errors.last_name} />
        </div>
        <TextInput id="email" label="Email" type="email" autoComplete="email" value={form.email} onChange={set("email")} error={errors.email} />
        <TextInput id="phone" label="Phone (optional)" type="tel" autoComplete="tel" value={form.phone} onChange={set("phone")} />
        <PasswordInput id="password" label="Password" autoComplete="new-password" value={form.password} onChange={set("password")} error={errors.password} />
        <ul className="pw-rules" aria-label="Password requirements">
          {ruleState.map((r) => (
            <li key={r.id} className={r.ok ? "ok" : ""}>
              {r.label}
            </li>
          ))}
        </ul>
        <PasswordInput
          id="confirm"
          label="Confirm password"
          autoComplete="new-password"
          value={form.confirm_password}
          onChange={set("confirm_password")}
          error={errors.confirm_password}
        />
        <label className="check">
          <input type="checkbox" checked={form.accept_terms} onChange={set("accept_terms")} />
          I accept the Terms of Use and Privacy Policy.
        </label>
        {errors.accept_terms && <p className="field-error">{errors.accept_terms}</p>}
        {error && (
          <p className="form-alert" role="alert">
            {error}
          </p>
        )}
        <Button type="submit" busy={busy} style={{ width: "100%", marginTop: 12 }}>
          Create account
        </Button>
      </form>
      <p className="auth-foot">
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
