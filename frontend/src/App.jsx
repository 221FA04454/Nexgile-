import { Navigate, Route, Routes } from "react-router-dom";
import { AuthGuard, GuestGuard, RoleGuard } from "./auth/authGuard";
import AppLayout from "./layout/AppLayout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import VerifyEmail from "./pages/VerifyEmail";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import { Forbidden, NotFound, ServerError, Unauthorized } from "./pages/StatusPages";
import Dashboard from "./pages/Dashboard";
import Wealth from "./pages/Wealth";
import Portfolio from "./pages/Portfolio";
import Goals from "./pages/Goals";
import Tax from "./pages/Tax";
import Estate from "./pages/Estate";
import Philanthropy from "./pages/Philanthropy";
import Retirement from "./pages/Retirement";
import Documents from "./pages/Documents";
import Messages from "./pages/Messages";
import Reports from "./pages/Reports";
import AIWealthAgent from "./pages/AIWealthAgent";
import Advisor from "./pages/Advisor";
import Integrations from "./pages/Integrations";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/login"
        element={
          <GuestGuard>
            <Login />
          </GuestGuard>
        }
      />
      <Route
        path="/signup"
        element={
          <GuestGuard>
            <Signup />
          </GuestGuard>
        }
      />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/forbidden" element={<Forbidden />} />
      <Route path="/error" element={<ServerError />} />
      <Route
        element={
          <AuthGuard>
            <AppLayout />
          </AuthGuard>
        }
      >
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="wealth" element={<Wealth />} />
        <Route path="accounts" element={<Navigate to="/wealth" replace />} />
        <Route path="portfolios" element={<Portfolio />} />
        <Route path="goals" element={<Goals />} />
        <Route path="tax" element={<Tax />} />
        <Route path="estate" element={<Estate />} />
        <Route path="philanthropy" element={<Philanthropy />} />
        <Route path="retirement" element={<Retirement />} />
        <Route path="participants" element={<Navigate to="/retirement" replace />} />
        <Route path="documents" element={<Documents />} />
        <Route path="messages" element={<Messages />} />
        <Route path="reports" element={<Reports />} />
        <Route path="ai" element={<AIWealthAgent />} />
        <Route
          path="advisor"
          element={
            <RoleGuard roles={["ADVISOR", "ADMIN"]}>
              <Advisor />
            </RoleGuard>
          }
        />
        <Route
          path="integrations"
          element={
            <RoleGuard roles={["ADVISOR", "ADMIN"]}>
              <Integrations />
            </RoleGuard>
          }
        />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
