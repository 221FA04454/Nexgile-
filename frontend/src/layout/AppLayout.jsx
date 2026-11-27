import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Landmark,
  PieChart,
  Target,
  Receipt,
  ScrollText,
  HeartHandshake,
  Umbrella,
  FolderArchive,
  MessageSquare,
  FileBarChart,
  Sparkles,
  Briefcase,
  Cable,
  Settings,
  Search,
  Bell,
  Menu,
  LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/client";

const NAV = [
  { section: "Overview", items: [{ to: "/dashboard", label: "Dashboard", icon: LayoutDashboard }] },
  {
    section: "Wealth",
    items: [
      { to: "/wealth", label: "Wealth", icon: Landmark },
      { to: "/portfolios", label: "Portfolios", icon: PieChart },
      { to: "/goals", label: "Goals", icon: Target },
      { to: "/tax", label: "Tax", icon: Receipt },
      { to: "/estate", label: "Estate", icon: ScrollText },
      { to: "/philanthropy", label: "Philanthropy", icon: HeartHandshake },
      { to: "/retirement", label: "Retirement", icon: Umbrella },
    ],
  },
  {
    section: "Workspace",
    items: [
      { to: "/documents", label: "Documents", icon: FolderArchive },
      { to: "/messages", label: "Messages", icon: MessageSquare },
      { to: "/reports", label: "Reports", icon: FileBarChart },
      { to: "/ai", label: "AI WealthAgent", icon: Sparkles },
      { to: "/advisor", label: "Advisor Workstation", icon: Briefcase, roles: ["ADVISOR", "ADMIN"] },
      { to: "/integrations", label: "Integrations", icon: Cable, roles: ["ADVISOR", "ADMIN"] },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [notes, setNotes] = useState([]);
  const [showNotes, setShowNotes] = useState(false);

  useEffect(() => {
    api.notifications().then((d) => setNotes(d.notifications || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!q.trim()) {
      setResults(null);
      return;
    }
    const t = setTimeout(() => {
      api.search(q).then(setResults).catch(() => setResults(null));
    }, 220);
    return () => clearTimeout(t);
  }, [q]);

  const unread = notes.filter((n) => !n.read).length;
  const nav = useMemo(
    () =>
      NAV.map((s) => ({
        ...s,
        items: s.items.filter((i) => !i.roles || i.roles.includes(user?.role) || user?.role === "ADMIN"),
      })),
    [user]
  );

  return (
    <div className="app-shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark">N</div>
          <div>
            <div className="brand-name">Nexgile WealthAgent</div>
            <div className="brand-sub">Private client</div>
          </div>
        </div>
        <nav className="nav">
          {nav.map((s) => (
            <div key={s.section}>
              <div className="nav-section">{s.section}</div>
              {s.items.map((i) => {
                const Icon = i.icon;
                return (
                  <NavLink key={i.to} to={i.to} end={i.to === "/dashboard"} onClick={() => setOpen(false)}>
                    <Icon />
                    {i.label}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          Book of record · v3
          <div>As of Sep 7, 2026</div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setOpen((v) => !v)} aria-label="Menu">
            <Menu size={16} />
          </button>
          <div className="search-wrap">
            <Search />
            <input
              placeholder="Search clients, accounts, holdings, documents…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            {results && (
              <div className="search-pop">
                {Object.entries(results.results || {}).map(([cat, items]) =>
                  items.length ? (
                    <div key={cat}>
                      <div className="search-cat">{cat}</div>
                      {items.map((it) => (
                        <div className="search-item" key={cat + it.id}>
                          <span>{it.label}</span>
                          <small>{it.sub}</small>
                        </div>
                      ))}
                    </div>
                  ) : null
                )}
                {!Object.values(results.results || {}).some((x) => x.length) && (
                  <div className="state">No matches</div>
                )}
              </div>
            )}
          </div>
          <div className="top-meta">
            <div className="chip asof-full">As of Sep 7, 2026 · Updated 5 minutes ago</div>
            <div style={{ position: "relative" }}>
              <button className="icon-btn" onClick={() => setShowNotes((v) => !v)} aria-label="Notifications">
                <Bell size={16} />
                {unread > 0 && <span className="dot" />}
              </button>
              {showNotes && (
                <div className="notif-pop">
                  {notes.map((n) => (
                    <div key={n.id} className="insight">
                      <div className="tick" />
                      <div>
                        <strong>{n.title}</strong>
                        <div className="faint">{n.body}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="profile-chip">
              <div className="avatar">{user?.initials || "AM"}</div>
              <div>
                <strong>{user?.name}</strong>
                <span>{user?.title}</span>
              </div>
              <span className="role-pill">{user?.role}</span>
              <button
                className="icon-btn"
                title="Sign out"
                onClick={async () => {
                  await logout();
                  navigate("/login");
                }}
              >
                <LogOut size={14} />
              </button>
            </div>
          </div>
        </header>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
