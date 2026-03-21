"use client";

import { useCallback, useEffect, useState } from "react";
import {
  OrchestratorState,
  WorkspaceResponse,
  ProjectResponse,
  fetchState,
  fetchWorkspaces,
  fetchProjects,
  createWorkspace,
  createProject,
  triggerRefresh,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthPage } from "@/components/auth-page";
import { Sidebar, Page } from "@/components/sidebar";
import { OperationsPage } from "@/components/operations";
import { TasksPage } from "@/components/tasks";
import { AgentsPage } from "@/components/agents";
import { SettingsPage } from "@/components/settings";

const POLL_INTERVAL = 3000;

export default function Dashboard() {
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

  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  // Persist page in URL hash
  const getInitialPage = (): Page => {
    if (typeof window === "undefined") return "operations";
    const hash = window.location.hash.replace("#", "").split("/")[0];
    if (["operations", "tasks", "agents", "settings"].includes(hash)) return hash as Page;
    return "operations";
  };
  const [page, setPage] = useState<Page>(getInitialPage);

  // Sync page to URL hash
  useEffect(() => {
    window.location.hash = page;
  }, [page]);

  // Listen for hash changes (browser back/forward)
  useEffect(() => {
    const handler = () => {
      const hash = window.location.hash.replace("#", "").split("/")[0];
      if (["operations", "tasks", "agents", "settings"].includes(hash)) {
        setPage(hash as Page);
      }
    };
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);

  // Workspace state
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceResponse | null>(null);

  // Project state
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [activeProject, setActiveProject] = useState<ProjectResponse | null>(null);

  // Orchestrator state
  const [orchState, setOrchState] = useState<OrchestratorState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Load workspaces
  const loadWorkspaces = useCallback(async () => {
    try {
      let wsList = await fetchWorkspaces();
      if (wsList.length === 0) {
        const ws = await createWorkspace("My Workspace");
        wsList = [ws];
      }
      setWorkspaces(wsList);
      setActiveWorkspace((prev) => {
        if (prev && wsList.find((w) => w.id === prev.id)) return prev;
        // Restore from localStorage
        const savedId = localStorage.getItem("maestro-workspace-id");
        const saved = savedId ? wsList.find((w) => w.id === Number(savedId)) : null;
        return saved || wsList[0];
      });
    } catch {}
  }, []);

  useEffect(() => { loadWorkspaces(); }, [loadWorkspaces]);

  // Persist active workspace
  useEffect(() => {
    if (activeWorkspace) localStorage.setItem("maestro-workspace-id", String(activeWorkspace.id));
  }, [activeWorkspace]);

  // Load projects when workspace changes
  const loadProjects = useCallback(async () => {
    if (!activeWorkspace) return;
    try {
      let pList = await fetchProjects(activeWorkspace.id);
      if (pList.length === 0) {
        const p = await createProject(activeWorkspace.id, "General");
        pList = [p];
      }
      setProjects(pList);
      setActiveProject((prev) => {
        if (prev && pList.find((p) => p.id === prev.id)) return prev;
        const savedId = localStorage.getItem("maestro-project-id");
        const saved = savedId ? pList.find((p) => p.id === Number(savedId)) : null;
        return saved || pList[0];
      });
    } catch {}
  }, [activeWorkspace]);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  // Persist active project
  useEffect(() => {
    if (activeProject) localStorage.setItem("maestro-project-id", String(activeProject.id));
  }, [activeProject]);

  const reloadAll = useCallback(async () => {
    await loadWorkspaces();
    await loadProjects();
  }, [loadWorkspaces, loadProjects]);

  // Poll orchestrator state
  const refresh = useCallback(async () => {
    try {
      const data = await fetchState();
      setOrchState(data);
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
    } catch {}
  };

  const pageTitle: Record<Page, string> = {
    operations: "Operations",
    tasks: "Tasks",
    agents: "Agents",
    settings: "Settings",
  };

  return (
    <div className="flex h-screen font-[family-name:var(--font-geist-sans)]">
      <Sidebar
        activePage={page}
        onNavigate={setPage}
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        onWorkspaceChange={setActiveWorkspace}
        projects={projects}
        activeProject={activeProject}
        onProjectChange={setActiveProject}
      />

      <main className="flex-1 overflow-y-auto">
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

        {error && (
          <div className="mx-6 mt-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
            {error}
          </div>
        )}

        <div className="p-6">
          {page === "operations" && <OperationsPage state={orchState} workspaceId={activeWorkspace?.id} />}
          {page === "tasks" && <TasksPage workspaceId={activeWorkspace?.id} projectId={activeProject?.id} />}
          {page === "agents" && activeWorkspace && (
            <AgentsPage workspaceId={activeWorkspace.id} />
          )}
          {page === "settings" && (
            <SettingsPage
              activeWorkspace={activeWorkspace}
              onWorkspacesChanged={reloadAll}
              onWorkspaceSwitch={setActiveWorkspace}
            />
          )}
        </div>
      </main>
    </div>
  );
}
