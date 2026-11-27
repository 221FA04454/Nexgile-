import { api } from "../api/client";
import { persistSession, clearSession, homeForRole } from "./sessionManager";

export const authService = {
  publicConfig: () => api.publicConfig(),
  async login(email, password, rememberMe = true) {
    const data = await api.login(email, password, rememberMe);
    persistSession(data);
    return data;
  },
  async signup(payload) {
    return api.signup(payload);
  },
  async verifyEmail({ token, otp }) {
    return api.verifyEmail({ token, otp });
  },
  async resendVerification(email) {
    return api.resendVerification(email);
  },
  async forgotPassword(email) {
    return api.forgotPassword(email);
  },
  async resetPassword(payload) {
    return api.resetPassword(payload);
  },
  async logout() {
    try {
      await api.logout();
    } finally {
      clearSession();
    }
  },
  async me() {
    const user = await api.me();
    persistSession({ user });
    return user;
  },
  sessions: () => api.authSessions(),
  revokeSession: (id) => api.revokeSession(id),
  homeForRole,
};
