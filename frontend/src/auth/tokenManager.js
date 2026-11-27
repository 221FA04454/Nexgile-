const ACCESS_KEY = "wa_access";
const REFRESH_KEY = "wa_refresh";
const USER_KEY = "wa_user";

export function getAccessToken() {
  return sessionStorage.getItem(ACCESS_KEY) || "";
}

export function setAccessToken(token) {
  if (token) sessionStorage.setItem(ACCESS_KEY, token);
  else sessionStorage.removeItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return sessionStorage.getItem(REFRESH_KEY) || "";
}

export function setRefreshToken(token) {
  if (token) sessionStorage.setItem(REFRESH_KEY, token);
  else sessionStorage.removeItem(REFRESH_KEY);
}

export function getStoredUser() {
  try {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  else sessionStorage.removeItem(USER_KEY);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem(USER_KEY);
}
