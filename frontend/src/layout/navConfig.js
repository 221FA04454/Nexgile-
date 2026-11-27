export const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/wealth", label: "Wealth" },
  { to: "/portfolios", label: "Portfolios" },
  { to: "/goals", label: "Goals" },
  { to: "/tax", label: "Tax" },
  { to: "/estate", label: "Estate" },
  { to: "/philanthropy", label: "Philanthropy" },
  { to: "/retirement", label: "Retirement" },
  { to: "/documents", label: "Documents" },
  { to: "/messages", label: "Messages" },
  { to: "/reports", label: "Reports" },
  { to: "/ai", label: "AI WealthAgent" },
  { to: "/advisor", label: "Advisor Workstation", roles: ["ADVISOR", "ADMIN"] },
  { to: "/integrations", label: "Integrations", roles: ["ADVISOR", "ADMIN"] },
  { to: "/settings", label: "Settings" },
];

export function visibleNav(role) {
  return NAV_ITEMS.filter((i) => !i.roles || i.roles.includes(role) || role === "ADMIN");
}
