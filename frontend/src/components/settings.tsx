"use client";

import { useCallback, useEffect, useState } from "react";
import { GitHubLogo, LinearLogo, JiraLogo, GitLabLogo } from "@/components/icons";
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
  createConnection,
  deleteConnection,
  fetchMembers,
  addMember,
  ApiKeyStatus,
  getApiKeyStatus,
  setApiKey,
  deleteApiKey,
  removeMember,
} from "@/lib/api";

type SettingsTab = "connections" | "models" | "members" | "workspace";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "connections", label: "Connections" },
  { id: "models", label: "Models" },
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
      {tab === "models" && ws && <ModelsTab workspaceId={ws.id} />}
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

type Provider = { kind: string; name: string; desc: string; Logo: React.FC<{ className?: string }> };

const CATEGORIES: { name: string; desc: string; providers: Provider[] }[] = [
  {
    name: "Code Hosts",
    desc: "Source control, pull requests, and CI",
    providers: [
      { kind: "github", name: "GitHub", desc: "Repos, issues, and PRs", Logo: GitHubLogo },
      { kind: "gitlab", name: "GitLab", desc: "Projects, issues, and MRs", Logo: GitLabLogo },
    ],
  },
  {
    name: "Issue Trackers",
    desc: "Task management and project tracking",
    providers: [
      { kind: "linear", name: "Linear", desc: "Project issues", Logo: LinearLogo },
      { kind: "jira", name: "Jira", desc: "Cloud or Server", Logo: JiraLogo },
    ],
  },
];

const ALL_PROVIDERS = CATEGORIES.flatMap((c) => c.providers);

const FORM_CFG: Record<string, { tokenPh: string; projectLabel: string; projectPh: string; projectReq: boolean }> = {
  github: { tokenPh: "github_pat_...", projectLabel: "Repository", projectPh: "owner/repo", projectReq: false },
  gitlab: { tokenPh: "glpat-...", projectLabel: "Project ID", projectPh: "group/project", projectReq: true },
  linear: { tokenPh: "lin_api_...", projectLabel: "Project slug", projectPh: "my-project", projectReq: true },
  jira: { tokenPh: "ATATT...", projectLabel: "Project key", projectPh: "ENG", projectReq: true },
};

const FILTERS = [
  { id: "all", label: "All" },
  { id: "code", label: "Code Hosts" },
  { id: "trackers", label: "Issue Trackers" },
];

const CATEGORY_MAP: Record<string, string> = {
  github: "code", gitlab: "code", linear: "trackers", jira: "trackers",
};

function ConnectionsTab({ workspaceId }: { workspaceId: number }) {
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modalKind, setModalKind] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    try { setConnections(await fetchConnections()); setError(null); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const connByKind = new Map<string, TrackerConnection[]>();
  for (const conn of connections) {
    const list = connByKind.get(conn.kind) || [];
    list.push(conn);
    connByKind.set(conn.kind, list);
  }

  const filtered = filter === "all"
    ? ALL_PROVIDERS
    : ALL_PROVIDERS.filter((p) => CATEGORY_MAP[p.kind] === filter);

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      {/* Filter pills */}
      <div className="flex gap-2 mb-5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-3.5 py-1.5 text-xs rounded-full transition-colors ${
              filter === f.id
                ? "bg-accent text-background font-medium"
                : "bg-surface border border-border text-muted hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {filtered.map(({ kind, name, desc, Logo }) => {
          const conns = connByKind.get(kind) || [];
          const isConnected = conns.length > 0;

          return (
            <button
              key={kind}
              onClick={() => setModalKind(kind)}
              className={`rounded-lg border p-5 text-center transition-all hover:shadow-md cursor-pointer ${
                isConnected ? "border-green-300 bg-surface" : "border-border bg-surface hover:border-accent/40"
              }`}
            >
              <Logo className="w-10 h-10 mx-auto mb-3" />
              <div className="text-sm font-semibold mb-0.5">{name}</div>
              <div className="text-[10px] text-muted mb-2">{desc}</div>
              {isConnected ? (
                <span className="text-[10px] font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                  {conns.length} connected
                </span>
              ) : (
                <span className="text-[10px] text-muted">Not connected</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Modal */}
      {modalKind && (
        <ConnectionDetailModal
          kind={modalKind}
          provider={ALL_PROVIDERS.find((p) => p.kind === modalKind)!}
          connections={connByKind.get(modalKind) || []}
          workspaceId={workspaceId}
          onClose={() => setModalKind(null)}
          onChanged={load}
        />
      )}
    </div>
  );
}

function ConnectionDetailModal({
  kind, provider, connections: conns, workspaceId, onClose, onChanged,
}: {
  kind: string;
  provider: Provider;
  connections: TrackerConnection[];
  workspaceId: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [showForm, setShowForm] = useState(conns.length === 0);
  const [name, setName] = useState("");
  const [token, setToken] = useState("");
  const [project, setProject] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const cfg = FORM_CFG[kind] || FORM_CFG.github;
  const Logo = provider.Logo;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !token) { setError("Name and token required"); return; }
    if (cfg.projectReq && !project) { setError(`${cfg.projectLabel} is required`); return; }
    if (kind === "jira" && !email) { setError("Email is required for Jira"); return; }
    setSaving(true); setError(null);
    try {
      await createConnection({ kind, name, project, token, endpoint: undefined, workspace_id: workspaceId });
      setName(""); setToken(""); setProject(""); setEmail("");
      setShowForm(false);
      onChanged();
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-foreground/20" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <Logo className="w-6 h-6" />
            <h2 className="text-base font-semibold">{provider.name}</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:text-foreground hover:bg-surface-hover transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Existing connections */}
          {conns.length > 0 && (
            <div>
              <div className="text-xs text-muted uppercase tracking-wider mb-2">Active connections</div>
              <div className="space-y-2">
                {conns.map((conn) => (
                  <div key={conn.id} className="flex items-center justify-between p-3 rounded-md border border-border bg-background">
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">{conn.name}</div>
                      <div className="text-xs text-muted truncate">{conn.project || "All repositories"}</div>
                    </div>
                    <button onClick={async () => { await deleteConnection(conn.id); onChanged(); }}
                      className="text-xs text-red-600 hover:text-red-800 transition-colors flex-shrink-0 ml-3">Remove</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Add form */}
          {showForm ? (
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="text-xs text-muted uppercase tracking-wider">{conns.length > 0 ? "Add another" : "Connect"}</div>
              {error && <div className="text-xs text-red-600 p-2 bg-red-50 rounded-md">{error}</div>}
              <div>
                <label className="block text-xs text-muted mb-1">Connection name</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={`My ${provider.name}`}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
              </div>
              <div>
                <label className="block text-xs text-muted mb-1">API Token</label>
                <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder={cfg.tokenPh}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
              </div>
              {kind === "jira" && (
                <div>
                  <label className="block text-xs text-muted mb-1">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com"
                    className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
                </div>
              )}
              <div>
                <label className="block text-xs text-muted mb-1">{cfg.projectLabel}{!cfg.projectReq && " (optional)"}</label>
                <input type="text" value={project} onChange={(e) => setProject(e.target.value)} placeholder={cfg.projectPh}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="submit" disabled={saving}
                  className="flex-1 px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 disabled:opacity-50">
                  {saving ? "Connecting..." : "Connect"}
                </button>
                {conns.length > 0 && (
                  <button type="button" onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Cancel</button>
                )}
              </div>
            </form>
          ) : (
            <button onClick={() => setShowForm(true)}
              className="w-full px-4 py-2 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors">
              Add connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Models tab
// ---------------------------------------------------------------------------

const MODEL_PROVIDERS = [
  { id: "anthropic", name: "Anthropic", desc: "Claude models", models: "Claude Sonnet, Opus, Haiku", placeholder: "sk-ant-...", icon: "A" },
  { id: "openai", name: "OpenAI", desc: "GPT models", models: "GPT-4o, o1, o3", placeholder: "sk-...", icon: "O" },
  { id: "google", name: "Google", desc: "Gemini models", models: "Gemini 2.5 Pro, Flash", placeholder: "AIza...", icon: "G" },
];

function ModelsTab({ workspaceId }: { workspaceId: number }) {
  const [statuses, setStatuses] = useState<Record<string, ApiKeyStatus>>({});
  const [modalProvider, setModalProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const results: Record<string, ApiKeyStatus> = {};
      for (const p of MODEL_PROVIDERS) { results[p.id] = await getApiKeyStatus(workspaceId, p.id); }
      setStatuses(results); setError(null);
    } catch (err) { setError(err instanceof Error ? err.message : "Failed to load"); }
  }, [workspaceId]);
  useEffect(() => { load(); }, [load]);

  return (
    <div>
      {error && <ErrorBanner message={error} />}

      <Section title="Model Providers" description="Connect AI providers to power your agents. Keys are encrypted at rest.">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {MODEL_PROVIDERS.map((p) => {
            const status = statuses[p.id];
            const isConnected = status?.has_key;

            return (
              <button
                key={p.id}
                onClick={() => setModalProvider(p.id)}
                className={`rounded-lg border p-5 text-center transition-all hover:shadow-md cursor-pointer ${
                  isConnected ? "border-green-300 bg-surface" : "border-border bg-surface hover:border-accent/40"
                }`}
              >
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center mx-auto mb-3">
                  <span className="text-lg font-bold text-accent">{p.icon}</span>
                </div>
                <div className="text-sm font-semibold mb-0.5">{p.name}</div>
                <div className="text-[10px] text-muted mb-1">{p.desc}</div>
                <div className="text-[9px] text-muted mb-2">{p.models}</div>
                {isConnected ? (
                  <span className="text-[10px] font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">Connected</span>
                ) : (
                  <span className="text-[10px] text-muted">Not connected</span>
                )}
              </button>
            );
          })}
        </div>
      </Section>

      {/* Modal */}
      {modalProvider && (() => {
        const p = MODEL_PROVIDERS.find((m) => m.id === modalProvider)!;
        const status = statuses[p.id];
        return (
          <ModelProviderModal
            provider={p}
            isConnected={!!status?.has_key}
            workspaceId={workspaceId}
            onClose={() => setModalProvider(null)}
            onChanged={load}
          />
        );
      })()}
    </div>
  );
}

function ModelProviderModal({
  provider, isConnected, workspaceId, onClose, onChanged,
}: {
  provider: typeof MODEL_PROVIDERS[0];
  isConnected: boolean;
  workspaceId: number;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(!isConnected);

  const handleSave = async () => {
    if (!keyInput.trim()) return;
    setSaving(true); setError(null);
    try { await setApiKey(workspaceId, provider.id, keyInput.trim()); setKeyInput(""); setShowForm(false); onChanged(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to save"); }
    finally { setSaving(false); }
  };

  const handleRemove = async () => {
    try { await deleteApiKey(workspaceId, provider.id); onChanged(); onClose(); }
    catch (err) { setError(err instanceof Error ? err.message : "Failed to remove"); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-foreground/20" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center">
              <span className="text-sm font-bold text-accent">{provider.icon}</span>
            </div>
            <div>
              <h2 className="text-base font-semibold">{provider.name}</h2>
              <p className="text-xs text-muted">{provider.models}</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:text-foreground hover:bg-surface-hover transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 space-y-4">
          {isConnected && !showForm && (
            <div className="flex items-center justify-between p-3 rounded-md border border-green-300 bg-green-50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm font-medium">API key configured</span>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={() => setShowForm(true)} className="text-xs text-muted hover:text-foreground transition-colors">Replace</button>
                <button onClick={handleRemove} className="text-xs text-red-600 hover:text-red-800 transition-colors">Remove</button>
              </div>
            </div>
          )}

          {showForm && (
            <div className="space-y-3">
              {error && <div className="text-xs text-red-600 p-2 bg-red-50 rounded-md">{error}</div>}
              <div>
                <label className="block text-xs text-muted mb-1">API Key</label>
                <input type="password" value={keyInput} onChange={(e) => setKeyInput(e.target.value)}
                  placeholder={provider.placeholder}
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
              </div>
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={saving}
                  className="flex-1 px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 disabled:opacity-50">
                  {saving ? "Saving..." : "Save key"}
                </button>
                {isConnected && (
                  <button onClick={() => setShowForm(false)}
                    className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Cancel</button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
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
