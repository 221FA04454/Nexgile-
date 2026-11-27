import { clearTokens, getStoredUser, setAccessToken, setRefreshToken, setStoredUser } from "./tokenManager";

export function persistSession(data) {
  if (data?.access_token) setAccessToken(data.access_token);
  if (data?.refresh_token) setRefreshToken(data.refresh_token);
  if (data?.user) setStoredUser(data.user);
}

export function clearSession() {
  clearTokens();
}

export function currentUser() {
  return getStoredUser();
}

export function homeForRole(role) {
  if (role === "ADVISOR") return "/advisor";
  if (role === "SPONSOR" || role === "PARTICIPANT") return "/retirement";
  return "/dashboard";
}

export const PASSWORD_RULES = [
  { id: "length", label: "At least 10 characters", test: (v) => (v || "").length >= 10 },
  { id: "upper", label: "One uppercase letter", test: (v) => /[A-Z]/.test(v || "") },
  { id: "lower", label: "One lowercase letter", test: (v) => /[a-z]/.test(v || "") },
  { id: "number", label: "One number", test: (v) => /\d/.test(v || "") },
  { id: "special", label: "One special character", test: (v) => /[^A-Za-z0-9]/.test(v || "") },
];
