"use client";

import { useCallback, useEffect, useState } from "react";
import { GitHubLogo, LinearLogo, JiraLogo, GitLabLogo } from "@/components/icons";
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
  ApiKeyStatus,
  getApiKeyStatus,
  setApiKey,
  deleteApiKey,
  removeMember,
} from "@/lib/api";

type SettingsTab = "connections" | "api-keys" | "members" | "workspace";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "connections", label: "Connections" },
  { id: "api-keys", label: "API Keys" },
  { id: "members", label: "Members" },
  { id: "workspace", label: "Workspace" },
];

export function SettingsPage({
  activeWorkspace,
  onWorkspacesChanged,
  onWorkspaceSwitch,
}: {
  activeWorkspace: WorkspaceResponse | null;
  onWorkspacesChanged?: () => void;
  onWorkspaceSwitch?: (ws: WorkspaceResponse) => void;
}) {
  const [tab, setTab] = useState<SettingsTab>("connections");
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setWorkspaces(await fetchWorkspaces()); } catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const ws = activeWorkspace;
  const isOwner = ws?.role === "owner";

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      {/* Tab bar */}
      <div className="flex gap-0 border-b border-border mb-6">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-5 py-3 text-sm -mb-px transition-colors ${
              tab === t.id
                ? "border-b-2 border-accent text-foreground font-semibold"
                : "text-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "connections" && ws && <ConnectionsTab workspaceId={ws.id} />}
      {tab === "api-keys" && ws && <ApiKeysTab workspaceId={ws.id} />}
      {tab === "members" && ws && <MembersTab workspaceId={ws.id} isOwner={isOwner} />}
      {tab === "workspace" && ws && (
        <WorkspaceTab workspace={ws} isOwner={isOwner} onReload={() => { load(); onWorkspacesChanged?.(); }} onWorkspacesChanged={onWorkspacesChanged} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// General — workspace + projects management
// ---------------------------------------------------------------------------

function WorkspaceTab({
  workspace,
  isOwner,
  onReload,
  onWorkspacesChanged,
}: {
  workspace: WorkspaceResponse;
  isOwner: boolean;
  onReload: () => void;
  onWorkspacesChanged?: () => void;
}) {
  const [editingWs, setEditingWs] = useState(false);
  const [editName, setEditName] = useState(workspace.name);
  const [error, setError] = useState<string | null>(null);

  const handleRename = async () => {
    if (!editName.trim()) return;
    try { await updateWorkspace(workspace.id, editName.trim()); setEditingWs(false); onReload(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete workspace "${workspace.name}"? This cannot be undone.`)) return;
    try { await deleteWorkspace(workspace.id); onReload(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  };

  return (
    <div className="space-y-8">
      {error && <ErrorBanner message={error} />}

      <Section title="Workspace" description="Manage workspace name and settings. Switch workspaces from the sidebar menu.">
        <div className="rounded-lg border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            {editingWs ? (
              <div className="flex items-center gap-3 flex-1">
                <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus
                  className="px-3 py-2 text-sm rounded-md border border-border bg-background flex-1 max-w-xs"
                  onKeyDown={(e) => e.key === "Enter" && handleRename()} />
                <button onClick={handleRename} className="text-sm text-accent hover:underline">Save</button>
                <button onClick={() => setEditingWs(false)} className="text-sm text-muted hover:text-foreground">Cancel</button>
              </div>
            ) : (
              <div>
                <h3 className="text-base font-semibold">{workspace.name}</h3>
                <p className="text-xs text-muted mt-0.5">Role: {workspace.role}</p>
              </div>
            )}
            {isOwner && !editingWs && (
              <div className="flex items-center gap-3">
                <button onClick={() => { setEditingWs(true); setEditName(workspace.name); }}
                  className="text-sm text-muted hover:text-foreground transition-colors">Rename</button>
                <button onClick={handleDelete}
                  className="text-sm text-red-600 hover:text-red-800 transition-colors">Delete</button>
              </div>
            )}
          </div>
        </div>
      </Section>

      <Section title="Projects" description="Projects group tasks and agent configurations within this workspace.">
        <ProjectsList workspaceId={workspace.id} onChanged={onWorkspacesChanged} />
      </Section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Connections tab
// ---------------------------------------------------------------------------

function ConnectionsTab({ workspaceId }: { workspaceId: number }) {
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);

  const load = useCallback(async () => {
    try { setConnections(await fetchConnections()); setError(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const logoFor = (kind: string) => {
    if (kind === "github") return <GitHubLogo className="w-5 h-5 flex-shrink-0" />;
    if (kind === "gitlab") return <GitLabLogo className="w-5 h-5 flex-shrink-0" />;
    if (kind === "linear") return <LinearLogo className="w-5 h-5 flex-shrink-0" />;
    if (kind === "jira") return <JiraLogo className="w-5 h-5 flex-shrink-0" />;
    return null;
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      <Section title="Connections" description="Connect issue trackers and code hosts to pull tasks into the pipeline.">
        {connections.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center">
            <p className="text-sm text-muted mb-3">No connections yet</p>
            <button onClick={() => setShowModal(true)}
              className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
              Add connection
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {connections.map((conn) => (
              <div key={conn.id} className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
                <div className="flex items-center gap-3 min-w-0">
                  {logoFor(conn.kind)}
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{conn.name}</div>
                    <div className="text-xs text-muted truncate">{conn.project || "All repositories"}</div>
                  </div>
                </div>
                <button onClick={async () => { await deleteConnection(conn.id); load(); }}
                  className="text-sm text-red-600 hover:text-red-800 transition-colors flex-shrink-0">Remove</button>
              </div>
            ))}
            <button onClick={() => setShowModal(true)}
              className="px-4 py-2 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors">
              Add connection
            </button>
          </div>
        )}
      </Section>

      {showModal && (
        <ConnectionModal
          workspaceId={workspaceId}
          onCreated={() => { setShowModal(false); load(); }}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// API Keys tab
// ---------------------------------------------------------------------------

const API_KEY_PROVIDERS = [
  { id: "anthropic", name: "Anthropic", description: "Claude API key — powers all agents", placeholder: "sk-ant-..." },
];

function ApiKeysTab({ workspaceId }: { workspaceId: number }) {
  const [statuses, setStatuses] = useState<Record<string, ApiKeyStatus>>({});
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const results: Record<string, ApiKeyStatus> = {};
      for (const p of API_KEY_PROVIDERS) { results[p.id] = await getApiKeyStatus(workspaceId, p.id); }
      setStatuses(results); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  const handleSave = async (provider: string) => {
    if (!keyInput.trim()) return;
    setSaving(true);
    try { await setApiKey(workspaceId, provider, keyInput.trim()); setKeyInput(""); setEditingProvider(null); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to save"); }
    finally { setSaving(false); }
  };

  const handleDelete = async (provider: string) => {
    try { await deleteApiKey(workspaceId, provider); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to delete"); }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      <Section title="API Keys" description="Manage API keys for LLM providers. Keys are encrypted at rest.">
        <div className="space-y-3">
          {API_KEY_PROVIDERS.map((p) => {
            const status = statuses[p.id];
            const isEditing = editingProvider === p.id;
            return (
              <div key={p.id} className="rounded-lg border border-border bg-surface p-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${status?.has_key ? "bg-green-500" : "bg-gray-300"}`} />
                    <span className="text-sm font-semibold">{p.name}</span>
                    {status?.has_key && <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded-full">Connected</span>}
                  </div>
                  {status?.has_key && !isEditing && (
                    <div className="flex items-center gap-3">
                      <button onClick={() => { setEditingProvider(p.id); setKeyInput(""); }} className="text-sm text-muted hover:text-foreground transition-colors">Replace</button>
                      <button onClick={() => handleDelete(p.id)} className="text-sm text-red-600 hover:text-red-800 transition-colors">Remove</button>
                    </div>
                  )}
                </div>
                <p className="text-xs text-muted mb-3">{p.description}</p>

                {(!status?.has_key || isEditing) && (
                  <div className="flex gap-3">
                    <input type="password" value={keyInput} onChange={(e) => setKeyInput(e.target.value)}
                      placeholder={p.placeholder}
                      className="flex-1 px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
                    <button onClick={() => handleSave(p.id)} disabled={saving}
                      className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50">
                      {saving ? "..." : "Save"}
                    </button>
                    {isEditing && (
                      <button onClick={() => setEditingProvider(null)} className="px-3 py-2 text-sm text-muted hover:text-foreground transition-colors">Cancel</button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Members tab
// ---------------------------------------------------------------------------

function MembersTab({ workspaceId, isOwner }: { workspaceId: number; isOwner: boolean }) {
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

      <Section title="Members" description="Manage who has access to this workspace.">
        {isOwner && !showAdd && (
          <div className="mb-4">
            <button onClick={() => setShowAdd(true)}
              className="px-4 py-2 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors">
              Invite member
            </button>
          </div>
        )}

        {showAdd && (
          <form onSubmit={handleAdd} className="flex gap-3 mb-4 p-4 rounded-lg border border-border bg-surface">
            <input type="email" value={addEmail} onChange={(e) => setAddEmail(e.target.value)} required
              placeholder="user@example.com"
              className="flex-1 px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
            <select value={addRole} onChange={(e) => setAddRole(e.target.value)}
              className="px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground">
              <option value="member">Member</option>
              <option value="owner">Owner</option>
            </select>
            <button type="submit" className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">Add</button>
            <button type="button" onClick={() => setShowAdd(false)} className="px-3 py-2 text-sm text-muted hover:text-foreground">Cancel</button>
          </form>
        )}

        <div className="space-y-2">
          {members.map((m) => (
            <div key={m.id} className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center flex-shrink-0">
                  <span className="text-background text-xs font-bold">{m.name?.charAt(0).toUpperCase() || "?"}</span>
                </div>
                <div>
                  <div className="text-sm font-medium">{m.name}</div>
                  <div className="text-xs text-muted">{m.email}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted capitalize">{m.role}</span>
                {isOwner && (
                  <button onClick={async () => { await removeMember(workspaceId, m.id); load(); }}
                    className="text-sm text-red-600 hover:text-red-800 transition-colors">Remove</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function ProjectsList({ workspaceId, onChanged }: { workspaceId: number; onChanged?: () => void }) {
  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setProjects(await fetchProjects(workspaceId)); } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try { await createProject(workspaceId, newName.trim()); setNewName(""); await load(); onChanged?.(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  };

  return (
    <div>
      {error && <ErrorBanner message={error} />}
      <form onSubmit={handleCreate} className="flex gap-3 mb-4">
        <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New project name"
          className="flex-1 max-w-sm px-3 py-2 text-sm rounded-md border border-border bg-surface placeholder:text-muted" />
        <button type="submit" className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">Add project</button>
      </form>
      {projects.length === 0 ? (
        <p className="text-sm text-muted">No projects yet</p>
      ) : (
        <div className="space-y-2">
          {projects.map((p) => (
            <div key={p.id} className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
              {editingId === p.id ? (
                <div className="flex items-center gap-3 flex-1">
                  <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)} autoFocus
                    className="px-3 py-1.5 text-sm rounded-md border border-border bg-background flex-1 max-w-xs"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); updateProject(workspaceId, p.id, editName.trim()).then(() => { setEditingId(null); load(); onChanged?.(); }); }
                    }} />
                  <button onClick={async () => { await updateProject(workspaceId, p.id, editName.trim()); setEditingId(null); load(); onChanged?.(); }}
                    className="text-sm text-accent hover:underline">Save</button>
                  <button onClick={() => setEditingId(null)} className="text-sm text-muted hover:text-foreground">Cancel</button>
                </div>
              ) : (
                <>
                  <span className="text-sm font-medium">{p.name}</span>
                  <div className="flex items-center gap-3">
                    <button onClick={() => { setEditingId(p.id); setEditName(p.name); }}
                      className="text-sm text-muted hover:text-foreground transition-colors">Rename</button>
                    <button onClick={async () => { await deleteProject(workspaceId, p.id); load(); onChanged?.(); }}
                      className="text-sm text-red-600 hover:text-red-800 transition-colors">Delete</button>
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

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-lg font-semibold mb-1">{title}</h2>
      <p className="text-sm text-muted mb-4">{description}</p>
      {children}
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return <div className="mb-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">{message}</div>;
}
