"use client";

import { useCallback, useEffect, useState } from "react";
import { GitHubLogo, LinearLogo } from "@/components/icons";
import { ConnectionModal } from "@/components/connection-modal";
import {
  WorkspaceResponse,
  ProjectResponse,
  TrackerConnection,
  MemberResponse,
  fetchWorkspaces,
  createWorkspace,
  updateWorkspace,
  deleteWorkspace,
  fetchProjects,
  createProject,
  updateProject,
  deleteProject,
  fetchConnections,
  deleteConnection,
  fetchMembers,
  addMember,
  removeMember,
} from "@/lib/api";

type WorkspaceSubTab = "projects" | "connections" | "users";

export function SettingsPage({
  activeWorkspace,
  onWorkspacesChanged,
  onWorkspaceSwitch,
}: {
  activeWorkspace: WorkspaceResponse | null;
  onWorkspacesChanged?: () => void;
  onWorkspaceSwitch?: (ws: WorkspaceResponse) => void;
}) {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(activeWorkspace?.id ?? null);
  const [subTab, setSubTab] = useState<Record<number, WorkspaceSubTab>>({});
  const [newName, setNewName] = useState("");
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
  useEffect(() => { if (activeWorkspace) setExpandedId(activeWorkspace.id); }, [activeWorkspace]);

  const getSubTab = (id: number) => subTab[id] || "projects";
  const setWsSubTab = (id: number, tab: WorkspaceSubTab) => setSubTab((prev) => ({ ...prev, [id]: tab }));

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      const ws = await createWorkspace(newName.trim());
      setNewName("");
      setExpandedId(ws.id);
      await load();
      onWorkspacesChanged?.();
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
      onWorkspacesChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to rename");
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteWorkspace(id);
      if (expandedId === id) setExpandedId(null);
      await load();
      onWorkspacesChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="max-w-2xl">
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
        {workspaces.map((ws) => {
          const expanded = expandedId === ws.id;
          const currentSubTab = getSubTab(ws.id);
          return (
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
                      onClick={() => setExpandedId(expanded ? null : ws.id)}
                      className="flex-1 min-w-0 text-left"
                    >
                      <div className="flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
                          className={`w-4 h-4 text-muted transition-transform ${expanded ? "rotate-90" : ""}`}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                        </svg>
                        <span className="text-sm font-medium">{ws.name}</span>
                        <span className="text-xs text-muted">{ws.role}</span>
                        {activeWorkspace?.id === ws.id && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-800 border border-green-300">Active</span>
                        )}
                      </div>
                    </button>
                    <div className="flex items-center gap-2">
                      {activeWorkspace?.id !== ws.id && (
                        <button
                          onClick={() => { onWorkspaceSwitch?.(ws); }}
                          className="text-xs text-accent hover:underline transition-colors"
                        >
                          Switch
                        </button>
                      )}
                      {ws.role === "owner" && (
                        <>
                        <button onClick={() => { setEditingId(ws.id); setEditName(ws.name); }} className="text-xs text-muted hover:text-foreground transition-colors">Rename</button>
                        <button onClick={() => handleDelete(ws.id)} className="text-xs text-red-600 hover:text-red-800 transition-colors">Delete</button>
                        </>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Expanded content */}
              {expanded && (
                <div className="border-t border-border">
                  {/* Sub-tabs */}
                  <div className="flex gap-0 border-b border-border bg-background/50">
                    {(["projects", "connections", "users"] as const).map((t) => (
                      <button
                        key={t}
                        onClick={() => setWsSubTab(ws.id, t)}
                        className={`px-4 py-2 text-xs capitalize -mb-px transition-colors ${
                          currentSubTab === t
                            ? "border-b-2 border-accent text-foreground font-medium"
                            : "text-muted hover:text-foreground"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>

                  <div className="p-3 bg-background/50">
                    {currentSubTab === "projects" && (
                      <ProjectsList workspaceId={ws.id} onChanged={onWorkspacesChanged} />
                    )}
                    {currentSubTab === "connections" && (
                      <ConnectionsList workspaceId={ws.id} />
                    )}
                    {currentSubTab === "users" && (
                      <MembersList workspaceId={ws.id} isOwner={ws.role === "owner"} />
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

function ProjectsList({ workspaceId, onChanged }: { workspaceId: number; onChanged?: () => void }) {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setProjects(await fetchProjects(workspaceId)); } catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try { await createProject(workspaceId, newName.trim()); setNewName(""); await load(); onChanged?.(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to create"); }
  };

  const handleRename = async (id: number) => {
    if (!editName.trim()) return;
    try { await updateProject(workspaceId, id, editName.trim()); setEditingId(null); await load(); onChanged?.(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to rename"); }
  };

  const handleDelete = async (id: number) => {
    try { await deleteProject(workspaceId, id); await load(); onChanged?.(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to delete"); }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      <form onSubmit={handleCreate} className="flex gap-2 mb-2">
        <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New project" className="flex-1 px-2 py-1.5 text-xs rounded-md border border-border bg-background placeholder:text-muted" />
        <button type="submit" className="px-3 py-1.5 text-xs rounded-md bg-accent text-background hover:opacity-90 transition-opacity">Add</button>
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
// Connections
// ---------------------------------------------------------------------------

function ConnectionsList({ workspaceId }: { workspaceId: number }) {
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    try { setConnections(await fetchConnections()); setError(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      <div className="flex justify-end mb-2">
        <button onClick={() => setShowModal(true)} className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors">
          Add
        </button>
      </div>
      {showModal && (
        <ConnectionModal
          workspaceId={workspaceId}
          onCreated={() => { setShowModal(false); load(); }}
          onClose={() => setShowModal(false)}
        />
      )}
      {connections.length === 0 ? (
        <div className="text-xs text-muted py-2">No connections</div>
      ) : (
        <div className="space-y-1">
          {connections.map((conn) => (
            <div key={conn.id} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-surface-hover transition-colors">
              <div className="flex items-center gap-2 min-w-0">
                {conn.kind === "github" ? <GitHubLogo className="w-4 h-4 flex-shrink-0" /> : <LinearLogo className="w-4 h-4 flex-shrink-0" />}
                <span className="text-xs font-medium truncate">{conn.name}</span>
                <span className="text-[10px] text-muted truncate">{conn.project || "all repos"}</span>
              </div>
              <button onClick={async () => { await deleteConnection(conn.id); load(); }} className="text-[10px] text-red-600 hover:text-red-800 transition-colors flex-shrink-0">Remove</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Members
// ---------------------------------------------------------------------------

function MembersList({ workspaceId, isOwner }: { workspaceId: number; isOwner: boolean }) {
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addRole, setAddRole] = useState("member");

  const load = useCallback(async () => {
    try { setMembers(await fetchMembers(workspaceId)); setError(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    try { await addMember(workspaceId, addEmail, addRole); setAddEmail(""); setShowAdd(false); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to add"); }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      {isOwner && (
        <div className="flex justify-end mb-2">
          <button onClick={() => setShowAdd(!showAdd)} className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors">
            {showAdd ? "Cancel" : "Add"}
          </button>
        </div>
      )}
      {showAdd && (
        <form onSubmit={handleAdd} className="flex gap-2 mb-2">
          <input type="email" value={addEmail} onChange={(e) => setAddEmail(e.target.value)} required placeholder="user@example.com" className="flex-1 px-2 py-1.5 text-xs rounded-md border border-border bg-background placeholder:text-muted" />
          <select value={addRole} onChange={(e) => setAddRole(e.target.value)} className="px-2 py-1.5 text-xs rounded-md border border-border bg-background text-foreground">
            <option value="member">Member</option>
            <option value="owner">Owner</option>
          </select>
          <button type="submit" className="px-3 py-1.5 text-xs rounded-md bg-accent text-background hover:opacity-90 transition-opacity">Add</button>
        </form>
      )}
      <div className="space-y-1">
        {members.map((m) => (
          <div key={m.id} className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-surface-hover transition-colors">
            <div className="min-w-0">
              <div className="text-xs font-medium truncate">{m.name}</div>
              <div className="text-[10px] text-muted truncate">{m.email}</div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-[10px] text-muted">{m.role}</span>
              {isOwner && (
                <button onClick={async () => { await removeMember(workspaceId, m.id); load(); }} className="text-[10px] text-red-600 hover:text-red-800 transition-colors">Remove</button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return <div className="mb-2 p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{message}</div>;
}
