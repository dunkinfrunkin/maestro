"use client";

import { useAuth } from "@/lib/auth";
import { AuthPage } from "@/components/auth-page";
import { DashboardProvider, useDashboard } from "@/lib/dashboard-context";
import { Sidebar } from "@/components/sidebar";
import { usePathname } from "next/navigation";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();

  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center text-muted text-sm">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <DashboardProvider>
      <DashboardInner>{children}</DashboardInner>
    </DashboardProvider>
  );
}

function DashboardInner({ children }: { children: React.ReactNode }) {
  const { error, lastUpdated, handleRefresh } = useDashboard();
  const pathname = usePathname();

  const pageTitle = pathname.startsWith("/tasks")
    ? "Tasks"
    : pathname.startsWith("/executions")
    ? "Executions"
    : pathname.startsWith("/agents")
    ? "Agents"
    : pathname.startsWith("/settings")
    ? "Settings"
    : "Operations";

  return (
    <div className="flex h-screen font-[family-name:var(--font-geist-sans)]">
      <Sidebar />

      <main className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 flex items-center justify-between px-6 h-14 border-b border-border bg-background/80 backdrop-blur-sm">
          <h1 className="text-lg font-semibold">{pageTitle}</h1>
          <div className="flex items-center gap-4">
            {lastUpdated && (
              <span className="text-xs text-muted">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={handleRefresh}
              className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors"
            >
              Refresh
            </button>
          </div>
        </header>

        {error && (
          <div className="mx-6 mt-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
            {error}
          </div>
        )}

        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
