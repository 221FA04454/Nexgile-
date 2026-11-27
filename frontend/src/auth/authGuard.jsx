import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./authContext";

export function AuthGuard({ children }) {
  const { isAuthenticated, ready } = useAuth();
  const location = useLocation();
  if (!ready) return null;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}

export function GuestGuard({ children }) {
  const { isAuthenticated, user, ready } = useAuth();
  if (!ready) return null;
  if (isAuthenticated) {
    const role = user?.role;
    const home = role === "ADVISOR" ? "/advisor" : role === "SPONSOR" || role === "PARTICIPANT" ? "/retirement" : "/dashboard";
    return <Navigate to={home} replace />;
  }
  return children;
}

export function RoleGuard({ roles, children }) {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user?.role) && user?.role !== "ADMIN") {
    return <Navigate to="/forbidden" replace />;
  }
  return children;
}
