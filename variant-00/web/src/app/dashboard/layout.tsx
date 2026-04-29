"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useTeamContext } from "@/context/TeamContext";
import Login from "@/components/Login";
import Sidebar from "@/components/dashboard/Sidebar";

const ADMIN_ONLY_PREFIXES = [
  "/dashboard/orgs",
  "/dashboard/feedback",
  "/dashboard/skills/upload",
  "/dashboard/teams",
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { token } = useAuth();
  const { activeRole, loading } = useTeamContext();
  const pathname = usePathname();
  const router = useRouter();

  // F3: Redirect non-admins away from admin-only pages
  useEffect(() => {
    if (loading || !token) return;
    if (activeRole !== "admin") {
      const isAdminPage = ADMIN_ONLY_PREFIXES.some((p) =>
        pathname.startsWith(p),
      );
      if (isAdminPage) {
        router.replace("/dashboard/skills");
      }
    }
  }, [activeRole, pathname, loading, token, router]);

  if (!token) return <Login />;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
