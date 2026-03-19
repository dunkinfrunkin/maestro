"use client";

import { useCallback, useEffect, useState } from "react";
import {
  WorkspaceResponse,
  ProjectResponse,
  TrackerConnection,
  fetchWorkspaces,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
  fetchProjects,
  createProject,
  updateProject,
  deleteProject,
  fetchConnections,
  createConnection,
  deleteConnection,
} from "@/lib/api";

type SettingsTab = "workspaces" | "connections";

export function SettingsPage({
  activeWorkspace,
  onWorkspacesChanged,
}: {
  activeWorkspace: WorkspaceResponse | null;
  onWorkspacesChanged?: () => void;
}) {
  const [tab, setTab] = useState<SettingsTab>("workspaces");

  return (
    <div className="max-w-2xl">
      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border">
        {([
          { id: "workspaces", label: "Workspaces" },
          { id: "connections", label: "Connections" },
        ] as const).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm -mb-px transition-colors ${
              tab === t.id
                ? "border-b-2 border-accent text-foreground font-medium"
                : "text-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "workspaces" && (
        <WorkspacesTab
          activeWorkspace={activeWorkspace}
          onChanged={onWorkspacesChanged}
        />
      )}
      {tab === "connections" && <ConnectionsSection />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workspaces tab (workspaces with nested projects)
// ---------------------------------------------------------------------------

function WorkspacesTab({
  activeWorkspace,
  onChanged,
}: {
  activeWorkspace: WorkspaceResponse | null;
  onChanged?: () => void;
}) {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [newName, setNewName] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(activeWorkspace?.id ?? null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setWorkspaces(await fetchWorkspaces());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-expand active workspace
  useEffect(() => {
    if (activeWorkspace) setExpandedId(activeWorkspace.id);
  }, [activeWorkspace]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const ws = await createWorkspace(newName.trim());
      setNewName("");
      setExpandedId(ws.id);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    }
  };

  const handleRename = async (id: number) => {
    if (!editName.trim()) return;
    try {
      await updateWorkspace(id, editName.trim());
      setEditingId(null);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteWorkspace(id);
      if (expandedId === id) setExpandedId(null);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      <form onSubmit={handleCreate} className="flex gap-2 mb-4">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New workspace name"
          className="flex-1 px-3 py-2 text-sm rounded-md border border-border bg-surface placeholder:text-muted"
        />
        <button type="submit" className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
          Create
        </button>
      </form>

      <div className="space-y-2">
        {workspaces.map((ws) => (
          <div key={ws.id} className="rounded-lg border border-border bg-surface overflow-hidden">
            {/* Workspace header */}
            <div className="p-3 flex items-center justify-between gap-3">
              {editingId === ws.id ? (
                <form onSubmit={(e) => { e.preventDefault(); handleRename(ws.id); }} className="flex-1 flex gap-2">
                  <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus className="flex-1 px-2 py-1 text-sm rounded-md border border-border bg-background" />
                  <button type="submit" className="text-xs text-accent hover:underline">Save</button>
                  <button type="button" onClick={() => setEditingId(null)} className="text-xs text-muted hover:underline">Cancel</button>
                </form>
              ) : (
                <>
                  <button
                    onClick={() => setExpandedId(expandedId === ws.id ? null : ws.id)}
                    className="flex-1 min-w-0 text-left"
                  >
                    <div className="flex items-center gap-2">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        strokeWidth={1.5}
                        stroke="currentColor"
                        className={`w-4 h-4 text-muted transition-transform ${expandedId === ws.id ? "rotate-90" : ""}`}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                      </svg>
                      <span className="text-sm font-medium">{ws.name}</span>
                      <span className="text-xs text-muted">{ws.role}</span>
                    </div>
                  </button>
                  {ws.role === "owner" && (
                    <div className="flex items-center gap-2">
                      <button onClick={() => { setEditingId(ws.id); setEditName(ws.name); }} className="text-xs text-muted hover:text-foreground transition-colors">Rename</button>
                      <button onClick={() => handleDelete(ws.id)} className="text-xs text-red-600 hover:text-red-800 transition-colors">Delete</button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Nested projects */}
            {expandedId === ws.id && (
              <div className="border-t border-border bg-background/50 p-3">
                <ProjectsList workspaceId={ws.id} onChanged={onChanged} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Projects (nested under a workspace)
// ---------------------------------------------------------------------------

function ProjectsList({
  workspaceId,
  onChanged,
}: {
  workspaceId: number;
  onChanged?: () => void;
}) {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setProjects(await fetchProjects(workspaceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    }
  }, [workspaceId]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await createProject(workspaceId, newName.trim());
      setNewName("");
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    }
  };

  const handleRename = async (id: number) => {
    if (!editName.trim()) return;
    try {
      await updateProject(workspaceId, id, editName.trim());
      setEditingId(null);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteProject(workspaceId, id);
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div>
      <div className="text-xs font-medium text-muted mb-2">Projects</div>
      {error && <ErrorBanner message={error} />}

      <form onSubmit={handleCreate} className="flex gap-2 mb-2">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New project"
          className="flex-1 px-2 py-1.5 text-xs rounded-md border border-border bg-background placeholder:text-muted"
        />
        <button type="submit" className="px-3 py-1.5 text-xs rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
          Add
        </button>
      </form>

      {projects.length === 0 ? (
        <div className="text-xs text-muted py-2">No projects yet</div>
      ) : (
        <div className="space-y-1">
          {projects.map((p) => (
            <div key={p.id} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-surface-hover transition-colors">
              {editingId === p.id ? (
                <form onSubmit={(e) => { e.preventDefault(); handleRename(p.id); }} className="flex-1 flex gap-2">
                  <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus className="flex-1 px-2 py-0.5 text-xs rounded border border-border bg-background" />
                  <button type="submit" className="text-[10px] text-accent hover:underline">Save</button>
                  <button type="button" onClick={() => setEditingId(null)} className="text-[10px] text-muted hover:underline">Cancel</button>
                </form>
              ) : (
                <>
                  <div className="text-xs">{p.name}</div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => { setEditingId(p.id); setEditName(p.name); }} className="text-[10px] text-muted hover:text-foreground transition-colors">Rename</button>
                    <button onClick={() => handleDelete(p.id)} className="text-[10px] text-red-600 hover:text-red-800 transition-colors">Delete</button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Connections tab
// ---------------------------------------------------------------------------

function ConnectionsSection() {
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      setConnections(await fetchConnections());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connections");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: number) => {
    try {
      await deleteConnection(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      <div className="flex justify-end mb-3">
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors"
        >
          {showForm ? "Cancel" : "Add Connection"}
        </button>
      </div>

      {showForm && (
        <ConnectionForm
          onCreated={() => { setShowForm(false); load(); }}
          onError={setError}
        />
      )}

      {connections.length === 0 && !showForm ? (
        <div className="rounded-lg border border-border border-dashed p-6 text-center text-muted text-sm">
          No connections. Add a GitHub or Linear connection to pull tasks.
        </div>
      ) : (
        <div className="space-y-2">
          {connections.map((conn) => (
            <div key={conn.id} className="rounded-lg border border-border bg-surface p-3 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500" />
                  <span className="text-sm font-medium">{conn.name}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-muted">{conn.kind}</span>
                </div>
                <div className="text-xs text-muted font-mono mt-0.5">
                  {conn.project || "All accessible repos"}
                </div>
              </div>
              <button onClick={() => handleDelete(conn.id)} className="text-xs text-red-600 hover:text-red-800 transition-colors">
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ConnectionForm({
  onCreated,
  onError,
}: {
  onCreated: () => void;
  onError: (msg: string) => void;
}) {
  const [kind, setKind] = useState("github");
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [token, setToken] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !token) { onError("Name and token are required"); return; }
    if (kind === "linear" && !project) { onError("Project slug is required for Linear"); return; }
    setSaving(true);
    try {
      await createConnection({ kind, name, project, token, endpoint: endpoint || undefined });
      onCreated();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to create connection");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-border bg-surface p-4 mb-3 space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-muted mb-1">Type</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)} className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground">
            <option value="github">GitHub</option>
            <option value="linear">Linear</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="My GitHub" className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
        </div>
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">
          {kind === "github" ? "Repository (optional — leave blank for all repos)" : "Project Slug"}
        </label>
        <input type="text" value={project} onChange={(e) => setProject(e.target.value)} placeholder={kind === "github" ? "owner/repo or leave blank" : "my-project"} className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">API Token</label>
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="ghp_... or lin_api_..." className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">Endpoint (optional)</label>
        <input type="text" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder={kind === "github" ? "https://api.github.com" : "https://api.linear.app/graphql"} className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
      </div>
      <button type="submit" disabled={saving} className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50">
        {saving ? "Saving..." : "Add Connection"}
      </button>
    </form>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-3 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
      {message}
    </div>
  );
}
