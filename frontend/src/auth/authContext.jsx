import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api, getAccessToken, setAccessToken } from "../api/client";
import { authService } from "./authService";
import { clearSession, persistSession } from "./sessionManager";
import { getStoredUser } from "./tokenManager";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getAccessToken());
  const [user, setUser] = useState(() => getStoredUser());
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      if (getAccessToken()) {
        try {
          const me = await api.me();
          if (!cancelled) {
            persistSession({ user: me });
            setUser(me);
            setToken(getAccessToken());
          }
        } catch {
          const refreshed = await api.refresh().catch(() => null);
          if (!cancelled && refreshed?.user) {
            persistSession(refreshed);
            setToken(refreshed.access_token);
            setUser(refreshed.user);
          } else if (!cancelled) {
            clearSession();
            setToken("");
            setUser(null);
          }
        }
        if (!cancelled) setReady(true);
        return;
      }
      const refreshed = await api.refresh().catch(() => null);
      if (cancelled) return;
      if (refreshed?.user) {
        persistSession(refreshed);
        setToken(refreshed.access_token);
        setUser(refreshed.user);
      }
      setReady(true);
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(
    () => ({
      token,
      user,
      ready,
      isAuthenticated: Boolean(token && user),
      async login(email, password, rememberMe = true) {
        const data = await authService.login(email, password, rememberMe);
        setToken(data.access_token);
        setUser(data.user);
        return data.user;
      },
      async logout() {
        await authService.logout();
        setAccessToken("");
        setToken("");
        setUser(null);
      },
    }),
    [token, user, ready]
  );

  if (!ready) {
    return (
      <div className="boot-screen" role="status">
        <div className="boot-mark">N</div>
        <p>Restoring your secure session…</p>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
