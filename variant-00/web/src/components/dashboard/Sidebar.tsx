"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTeamContext } from "@/context/TeamContext";

const adminNavItems = [
  { to: "/dashboard/skills", label: "Skills" },
  { to: "/dashboard/teams", label: "Teams" },
  { to: "/dashboard/feedback", label: "Feedback" },
  { to: "/dashboard/orgs", label: "Organizations" },
];

const memberNavItems = [
  { to: "/dashboard/skills", label: "Skills" },
  { to: "/dashboard/team", label: "Team" },
  { to: "/dashboard/setup", label: "Setup" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const { teams, activeTeam, activeRole, setActiveTeam } = useTeamContext();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isAdmin = activeRole === "admin";
  const navItems = isAdmin ? adminNavItems : memberNavItems;
  const subtitle = isAdmin ? "Admin Dashboard" : "Dashboard";

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setOpen(true)}
        className="fixed top-4 left-4 z-40 md:hidden p-2 rounded-md bg-white border border-gray-200 shadow-sm"
        aria-label="Open menu"
      >
        <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 w-56 bg-white border-r border-gray-200 flex flex-col
          transform transition-transform duration-200 ease-in-out
          md:static md:translate-x-0 md:min-h-screen
          ${open ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <div className="px-4 py-5 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-gray-900">Locker</h1>
            <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="md:hidden p-1 rounded text-gray-400 hover:text-gray-600"
            aria-label="Close menu"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

      {/* Team switcher (only if multiple teams) */}
      {teams.length > 1 && (
        <div className="px-3 pt-3">
          <select
            value={activeTeam?.team_id ?? ""}
            onChange={(e) => setActiveTeam(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {teams.map((t) => (
              <option key={t.team_id} value={t.team_id}>
                {t.team_name}
              </option>
            ))}
          </select>
        </div>
      )}

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.to);
          return (
            <Link key={item.to} href={item.to} onClick={() => setOpen(false)} className={`block px-3 py-2 text-sm rounded-md transition-colors ${isActive ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-100"}`}>{item.label}</Link>
          );
        })}
      </nav>
      <div className="px-3 py-4 border-t border-gray-200">
        {user && (
          <div className="px-3 mb-2">
            <p className="text-sm text-gray-700 truncate">{user.name}</p>
            <p className="text-xs text-gray-400 truncate">{user.email}</p>
          </div>
        )}
        <button onClick={logout} className="w-full px-3 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md text-left transition-colors">Sign out</button>
      </div>
      </aside>
    </>
  );
}
