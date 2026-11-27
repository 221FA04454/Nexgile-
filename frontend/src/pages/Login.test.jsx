import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login, { DEMOS } from "./Login";
import Signup from "./Signup";
import ForgotPassword from "./ForgotPassword";
import { AuthProvider } from "../auth/authContext";
import { AuthGuard } from "../auth/authGuard";
import { clearTokens } from "../auth/tokenManager";

describe("login demo directory", () => {
  it("lists the five development roles when demo mode is enabled", () => {
    expect(DEMOS.map((d) => d.role).sort()).toEqual(["ADMIN", "ADVISOR", "CLIENT", "PARTICIPANT", "SPONSOR"]);
  });
});

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

describe("login rendering and validation", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  beforeEach(() => {
    clearTokens();
    vi.stubGlobal(
      "fetch",
      vi.fn((url) => {
        if (String(url).includes("/auth/public-config")) {
          return jsonResponse({ demo_login_enabled: false, password_policy: { min_length: 10 } });
        }
        if (String(url).includes("/auth/refresh")) return jsonResponse({ error: { message: "no" } }, 401);
        if (String(url).includes("/auth/login")) {
          return jsonResponse({ error: { code: "UNAUTHORIZED", message: "Invalid email or password." } }, 401);
        }
        return jsonResponse({}, 404);
      })
    );
  });

  it("renders email and password fields", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByLabelText("Email")).toBeTruthy());
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
  });

  it("shows validation when submitted empty", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => screen.getByRole("button", { name: "Sign in" }));
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/email is required/i)).toBeTruthy();
  });

  it("shows a friendly error on failed login", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => screen.getByLabelText("Email"));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/invalid email or password/i)).toBeTruthy();
  });
});

describe("signup validation", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  beforeEach(() => {
    clearTokens();
    vi.stubGlobal(
      "fetch",
      vi.fn((url) => {
        if (String(url).includes("/auth/refresh")) return jsonResponse({}, 401);
        return jsonResponse({ error: { message: "no" } }, 401);
      })
    );
  });

  it("requires matching passwords and terms", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Signup />
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => screen.getByRole("button", { name: /create account/i }));
    fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "Riya" } });
    fireEvent.change(screen.getByLabelText(/last name/i), { target: { value: "Mehta" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "riya@example.com" } });
    fireEvent.change(screen.getByLabelText(/^password$/i), { target: { value: "SecurePass1!" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "other" } });
    fireEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByText(/passwords do not match/i)).toBeTruthy();
  });
});

describe("forgot password", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  it("renders the email recovery form", async () => {
    clearTokens();
    vi.stubGlobal(
      "fetch",
      vi.fn((url) => {
        if (String(url).includes("/auth/refresh")) return jsonResponse({}, 401);
        return jsonResponse({}, 401);
      })
    );
    render(
      <MemoryRouter>
        <AuthProvider>
          <ForgotPassword />
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByLabelText("Email")).toBeTruthy());
    expect(screen.getByRole("button", { name: /send reset instructions/i })).toBeTruthy();
  });
});

describe("protected route", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  it("redirects unauthenticated users to login", async () => {
    clearTokens();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse({}, 401))
    );
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <AuthProvider>
          <AuthGuard>
            <div>secret</div>
          </AuthGuard>
        </AuthProvider>
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.queryByText("secret")).toBeNull());
  });
});
