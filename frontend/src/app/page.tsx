"use client";

import { useCallback, useEffect, useState } from "react";
import { OrchestratorState, fetchState, triggerRefresh } from "@/lib/api";
import { Sidebar, Page } from "@/components/sidebar";
import { OperationsPage } from "@/components/operations";
import { AgentsPage } from "@/components/agents";
import { SettingsPage } from "@/components/settings";
import { TasksPage } from "@/components/tasks";

const POLL_INTERVAL = 3000;

export default function Dashboard() {
  const [page, setPage] = useState<Page>("operations");
  const [state, setState] = useState<OrchestratorState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchState();
      setState(data);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch state");
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleRefresh = async () => {
    try {
      await triggerRefresh();
      await refresh();
    } catch {
      // handled by polling
    }
  };

  const pageTitle: Record<Page, string> = {
    operations: "Operations",
    tasks: "Tasks",
    agents: "Agents",
    settings: "Settings",
  };

  return (
    <div className="flex h-screen font-[family-name:var(--font-geist-sans)]">
      <Sidebar activePage={page} onNavigate={setPage} />

      <main className="flex-1 overflow-y-auto">
        {/* Top bar */}
        <header className="sticky top-0 z-10 flex items-center justify-between px-6 h-14 border-b border-border bg-background/80 backdrop-blur-sm">
          <h1 className="text-lg font-semibold">{pageTitle[page]}</h1>
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

        {/* Error banner */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
            {error}
          </div>
        )}

        {/* Page content */}
        <div className="p-6">
          {page === "operations" && <OperationsPage state={state} />}
          {page === "tasks" && <TasksPage />}
          {page === "agents" && <AgentsPage state={state} />}
          {page === "settings" && <SettingsPage />}
        </div>
      </main>
    </div>
  );
}
