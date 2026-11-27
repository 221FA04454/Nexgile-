import { parseApiError } from "./errors";
import {
  getAccessToken as readAccess,
  setAccessToken as writeAccess,
  getRefreshToken,
  setRefreshToken,
  setStoredUser,
  clearTokens,
} from "../auth/tokenManager";

const BASE = import.meta.env.VITE_API_URL || "";

let accessToken = readAccess();
let refreshing = null;

export function setAccessToken(token) {
  accessToken = token || "";
  writeAccess(token);
}

export function getAccessToken() {
  return accessToken || readAccess();
}

function authHeader() {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function friendlyAuthMessage(error) {
  if (error.code === "RATE_LIMITED" || error.status === 429) {
    error.message = "Too many attempts. Please wait before trying again.";
  } else if (error.code === "EMAIL_UNVERIFIED") {
    error.message = "Please verify your email address before signing in.";
  } else if (error.status === 401 && /lock/i.test(error.message || "")) {
    error.message = "Your account is temporarily locked. Please try again later.";
  } else if (error.status === 401 && /invalid email or password/i.test(error.message || "")) {
    error.message = "Invalid email or password.";
  }
  return error;
}

async function tryRefresh() {
  const res = await fetch(`${BASE}/api/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(getRefreshToken() ? { "X-Refresh-Token": getRefreshToken() } : {}),
    },
  });
  if (!res.ok) return null;
  const data = await res.json();
  setAccessToken(data.access_token);
  if (data.refresh_token) setRefreshToken(data.refresh_token);
  if (data.user) setStoredUser(data.user);
  return data;
}

async function request(path, options = {}, retry = true) {
  const url = `${BASE}${path}`;
  let res;
  try {
    res = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...authHeader(),
        ...(options.headers || {}),
      },
    });
  } catch {
    const error = new Error("The wealth service is unavailable. Check your network connection.");
    error.offline = true;
    error.code = "SERVICE_UNAVAILABLE";
    error.status = 503;
    throw error;
  }
  const isAuthPath = path.includes("/auth/");
  if (res.status === 401 && retry && !path.includes("/auth/login") && !path.includes("/auth/refresh") && !path.includes("/auth/signup")) {
    if (!refreshing) {
      refreshing = tryRefresh().finally(() => {
        refreshing = null;
      });
    }
    const refreshed = await refreshing;
    if (refreshed) return request(path, options, false);
    clearTokens();
    accessToken = "";
    if (!isAuthPath && window.location.pathname !== "/login") window.location.href = "/login";
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw friendlyAuthMessage(parseApiError(data, res.status));
  return data;
}

export const api = {
  login: async (email, password, rememberMe = true) => {
    const data = await request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });
    setAccessToken(data.access_token);
    if (data.refresh_token) setRefreshToken(data.refresh_token);
    if (data.user) setStoredUser(data.user);
    return data;
  },
  signup: (payload) => request("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  verifyEmail: (payload) => request("/api/auth/verify-email", { method: "POST", body: JSON.stringify(payload) }),
  resendVerification: (email) =>
    request("/api/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) }),
  forgotPassword: (email) => request("/api/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }),
  resetPassword: (payload) => request("/api/auth/reset-password", { method: "POST", body: JSON.stringify(payload) }),
  refresh: () => tryRefresh(),
  logout: async () => {
    try {
      await request("/api/auth/logout", {
        method: "POST",
        headers: getRefreshToken() ? { "X-Refresh-Token": getRefreshToken() } : {},
      });
    } finally {
      clearTokens();
      accessToken = "";
    }
  },
  publicConfig: () => request("/api/auth/public-config"),
  me: () => request("/api/auth/me"),
  authSessions: () => request("/api/auth/sessions"),
  revokeSession: (id) => request(`/api/auth/sessions/${id}/revoke`, { method: "POST" }),
  health: () => request("/api/health"),
  dashboard: () => request("/api/dashboard"),
  accounts: () => request("/api/accounts"),
  portfolios: () => request("/api/portfolios"),
  portfolio: (id) => request(`/api/portfolios/${id}`),
  holdings: () => request("/api/holdings"),
  goals: () => request("/api/goals"),
  tax: () => request("/api/tax/opportunities"),
  estate: () => request("/api/estate"),
  philanthropy: () => request("/api/philanthropy"),
  retirement: () => request("/api/retirement"),
  documents: () => request("/api/documents"),
  uploadDocument: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/documents/upload", { method: "POST", body: fd });
  },
  messages: () => request("/api/messages"),
  advisorClients: () => request("/api/advisors/clients"),
  client360: (id) => request(`/api/advisors/clients/${id}`),
  reports: () => request("/api/reports"),
  report: (id) => request(`/api/reports/${id}`),
  chat: (message) => request("/api/ai/chat", { method: "POST", body: JSON.stringify({ message }) }),
  aiStatus: () => request("/api/ai/status"),
  aiSources: (q) => request(`/api/ai/sources?q=${encodeURIComponent(q)}`),
  rebalancePreview: (portfolioId = 1) =>
    request("/api/rebalance/preview", { method: "POST", body: JSON.stringify({ portfolio_id: portfolioId }) }),
  approvals: () => request("/api/approvals"),
  createApproval: (payload) => request("/api/approvals", { method: "POST", body: JSON.stringify(payload) }),
  decideApproval: (id, status, notes = "") =>
    request(`/api/approvals/${id}/decide`, { method: "POST", body: JSON.stringify({ status, notes }) }),
  notifications: () => request("/api/notifications"),
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),
  audit: () => request("/api/audit"),
  integrations: () => request("/api/integrations"),
  integrationsStatus: () => request("/api/integrations/status"),
  integrationHealth: (provider) => request(`/api/integrations/${provider}/health`),
  integrationSync: (provider) => request(`/api/integrations/${provider}/sync`, { method: "POST" }),
  integrationHistory: (provider) => request(`/api/integrations/${provider}/sync-history`),
  integrationReconciliation: () => request("/api/integrations/reconciliation"),
};
