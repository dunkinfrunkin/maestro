"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
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

const POLL_INTERVAL = 3000;

interface DashboardCtx {
  workspaces: WorkspaceResponse[];
  activeWorkspace: WorkspaceResponse | null;
  setActiveWorkspace: (ws: WorkspaceResponse) => void;
  projects: ProjectResponse[];
  activeProject: ProjectResponse | null;
  setActiveProject: (p: ProjectResponse) => void;
  orchState: OrchestratorState | null;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  reloadAll: () => Promise<void>;
  loadWorkspaces: () => Promise<void>;
  loadProjects: () => Promise<void>;
  handleRefresh: () => Promise<void>;
}

const DashboardContext = createContext<DashboardCtx>({
  workspaces: [],
  activeWorkspace: null,
  setActiveWorkspace: () => {},
  projects: [],
  activeProject: null,
  setActiveProject: () => {},
  orchState: null,
  error: null,
  lastUpdated: null,
  refresh: async () => {},
  reloadAll: async () => {},
  loadWorkspaces: async () => {},
  loadProjects: async () => {},
  handleRefresh: async () => {},
});

export function DashboardProvider({ children }: { children: React.ReactNode }) {
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

  const handleRefresh = useCallback(async () => {
    try {
      await triggerRefresh();
      await refresh();
    } catch {}
  }, [refresh]);

  return (
    <DashboardContext.Provider
      value={{
        workspaces,
        activeWorkspace,
        setActiveWorkspace,
        projects,
        activeProject,
        setActiveProject,
        orchState,
        error,
        lastUpdated,
        refresh,
        reloadAll,
        loadWorkspaces,
        loadProjects,
        handleRefresh,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboard() {
  return useContext(DashboardContext);
}
