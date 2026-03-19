"use client";

import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth";
import { WorkspaceResponse, ProjectResponse } from "@/lib/api";

type Page = "operations" | "tasks" | "agents" | "settings";

const NAV_ITEMS: { id: Page; label: string; icon: string }[] = [
  { id: "operations", label: "Operations", icon: "M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" },
  { id: "tasks", label: "Tasks", icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" },
  { id: "agents", label: "Agents", icon: "M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" },
];

export function Sidebar({
  activePage,
  onNavigate,
  workspaces,
  activeWorkspace,
  onWorkspaceChange,
  projects,
  activeProject,
  onProjectChange,
}: {
  activePage: Page;
  onNavigate: (page: Page) => void;
  workspaces: WorkspaceResponse[];
  activeWorkspace: WorkspaceResponse | null;
  onWorkspaceChange: (ws: WorkspaceResponse) => void;
  projects: ProjectResponse[];
  activeProject: ProjectResponse | null;
  onProjectChange: (p: ProjectResponse) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    };
    if (userMenuOpen) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [userMenuOpen]);

  return (
    <aside
      className={`flex flex-col h-screen bg-surface border-r border-border transition-all duration-200 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Header: Logo + Collapse */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center flex-shrink-0">
            <span className="text-background text-xs font-bold">M</span>
          </div>
          {!collapsed && (
            <span className="font-semibold text-sm tracking-tight">Maestro</span>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="rounded-md p-1 text-muted hover:bg-surface-hover hover:text-foreground transition-colors"
          title={collapsed ? "Expand" : "Collapse"}
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={`w-4 h-4 transition-transform ${collapsed ? "rotate-180" : ""}`}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5" />
          </svg>
        </button>
      </div>

      {/* Project switcher */}
      {!collapsed && projects.length > 0 && (
        <div className="px-2 py-2 border-b border-border">
          <div className="text-[10px] text-muted px-1 mb-0.5">Project</div>
          <select
            value={activeProject?.id ?? ""}
            onChange={(e) => {
              const p = projects.find((p) => p.id === Number(e.target.value));
              if (p) onProjectChange(p);
            }}
            className="w-full px-2 py-1.5 text-xs rounded-md border border-border bg-background text-foreground"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`flex items-center gap-3 w-full rounded-md px-3 py-2 text-sm transition-colors ${
              activePage === item.id
                ? "bg-surface-hover text-foreground font-medium"
                : "text-muted hover:bg-surface-hover hover:text-foreground"
            }`}
            title={collapsed ? item.label : undefined}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 flex-shrink-0">
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            {!collapsed && <span>{item.label}</span>}
          </button>
        ))}
      </nav>

      {/* Footer: User with dropdown menu */}
      <div className="border-t border-border relative" ref={menuRef}>
        {/* Dropdown menu (opens upward) */}
        {userMenuOpen && !collapsed && (
          <div className="absolute bottom-full left-0 right-0 mx-2 mb-1 rounded-lg border border-border bg-surface shadow-lg overflow-hidden">
            {/* Workspace switcher */}
            <div className="px-3 py-2 border-b border-border">
              <div className="text-[10px] text-muted mb-1">Workspace</div>
              {workspaces.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => { onWorkspaceChange(ws); setUserMenuOpen(false); }}
                  className={`flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-xs transition-colors ${
                    activeWorkspace?.id === ws.id
                      ? "bg-surface-hover text-foreground font-medium"
                      : "text-muted hover:bg-surface-hover hover:text-foreground"
                  }`}
                >
                  {ws.name}
                </button>
              ))}
            </div>

            {/* Actions */}
            <div className="py-1">
              <button
                onClick={() => { onNavigate("settings"); setUserMenuOpen(false); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-muted hover:bg-surface-hover hover:text-foreground transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                </svg>
                Settings
              </button>
              <button
                onClick={() => { logout(); setUserMenuOpen(false); }}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-red-600 hover:bg-surface-hover transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
                </svg>
                Sign out
              </button>
            </div>
          </div>
        )}

        {/* User button */}
        <button
          onClick={() => setUserMenuOpen(!userMenuOpen)}
          className="w-full px-3 py-3 flex items-center gap-2 hover:bg-surface-hover transition-colors"
        >
          <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
            <span className="text-background text-[10px] font-bold">
              {user?.name?.charAt(0).toUpperCase() || "?"}
            </span>
          </div>
          {!collapsed && user && (
            <div className="flex-1 min-w-0 text-left">
              <div className="text-xs font-medium truncate">{user.name}</div>
              <div className="text-[10px] text-muted truncate">{activeWorkspace?.name}</div>
            </div>
          )}
          {!collapsed && (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-muted flex-shrink-0">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 15 12 18.75 15.75 15m-7.5-6L12 5.25 15.75 9" />
            </svg>
          )}
        </button>
      </div>
    </aside>
  );
}

export type { Page };
