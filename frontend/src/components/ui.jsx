import React from "react";
import { formatINR } from "../currency";

export function money(n, digits = 0) {
  return formatINR(n, digits);
}

export function pct(n, digits = 1) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

export function clsx(...xs) {
  return xs.filter(Boolean).join(" ");
}

export function Card({ title, action, children, className }) {
  return (
    <section className={clsx("card", className)}>
      {(title || action) && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
          {title ? <h3>{title}</h3> : <span />}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }) {
  return <span className={clsx("badge", tone)}>{children}</span>;
}

export function Delta({ value, suffix = "", inverse = false }) {
  const n = Number(value) || 0;
  const up = inverse ? n < 0 : n > 0;
  const down = inverse ? n > 0 : n < 0;
  return <div className={clsx("delta", up && "up", down && "down")}>{suffix}{typeof value === "string" ? value : pct(n)}</div>;
}

export function Progress({ value }) {
  return (
    <div className="progress" aria-valuenow={value} role="progressbar">
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function Loading({ rows = 4 }) {
  return (
    <div className="card state">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skel" style={{ margin: "10px 0", height: 12 }} />
      ))}
      <p className="faint">Loading book of record…</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="card state">
      <p>We could not reach the wealth service.</p>
      <p className="faint">{message}</p>
      {onRetry && (
        <button className="btn ghost" onClick={onRetry} style={{ marginTop: 12 }}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ title = "Nothing to show", body }) {
  return (
    <div className="card state">
      <p>{title}</p>
      {body && <p className="faint">{body}</p>}
    </div>
  );
}

export function Status({ value }) {
  const v = (value || "").toLowerCase();
  let tone = "neutral";
  if (["current", "open", "healthy", "pass", "on track", "approved", "clear", "complete", "success", "mock", "fresh"].some((x) => v.includes(x))) tone = "ok";
  if (["watch", "review", "pending", "proposed", "informational", "stale", "unknown"].some((x) => v.includes(x))) tone = "warn";
  if (["due", "expir", "needs", "restricted", "rejected", "fail", "error"].some((x) => v.includes(x))) tone = "bad";
  return <Badge tone={tone}>{value}</Badge>;
}

export const CHART = ["#0c1b2a", "#a6854d", "#2a5880", "#1b6b58", "#8a96a1", "#c4a46a", "#5d6b78"];

export function Button({ children, variant = "primary", type = "button", busy, disabled, className, ...props }) {
  return (
    <button
      type={type}
      className={clsx("btn", variant !== "primary" && variant, className)}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...props}
    >
      {busy ? "Please wait…" : children}
    </button>
  );
}

export function Field({ id, label, hint, error, children }) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className={clsx("field", error && "has-error")}>
      <label htmlFor={id}>{label}</label>
      {typeof children === "function" ? children({ id, describedBy, error: Boolean(error) }) : children}
      {hint && !error && (
        <p id={`${id}-hint`} className="field-hint">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextInput({ id, label, error, hint, ...props }) {
  return (
    <Field id={id} label={label} error={error} hint={hint}>
      {({ describedBy }) => (
        <input id={id} aria-invalid={Boolean(error) || undefined} aria-describedby={describedBy} {...props} />
      )}
    </Field>
  );
}

export function PasswordInput({ id, label, error, hint, value, onChange, autoComplete = "current-password" }) {
  const [show, setShow] = React.useState(false);
  return (
    <Field id={id} label={label} error={error} hint={hint}>
      {({ describedBy }) => (
        <div className="password-wrap">
          <input
            id={id}
            type={show ? "text" : "password"}
            value={value}
            onChange={onChange}
            autoComplete={autoComplete}
            aria-invalid={Boolean(error) || undefined}
            aria-describedby={describedBy}
          />
          <button type="button" className="password-toggle" onClick={() => setShow((v) => !v)} aria-pressed={show}>
            {show ? "Hide" : "Show"}
          </button>
        </div>
      )}
    </Field>
  );
}

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export function EmptyState({ title = "Nothing to show", body }) {
  return <Empty title={title} body={body} />;
}

export function Skeleton({ rows = 3 }) {
  return <Loading rows={rows} />;
}
