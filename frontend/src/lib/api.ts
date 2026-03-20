const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("maestro-token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function authFetch(url: string, init?: RequestInit): Promise<Response> {
  return fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
    cache: "no-store",
  });
}

// ---------------------------------------------------------------------------
// Workspaces & Projects
// ---------------------------------------------------------------------------

export interface WorkspaceResponse {
  id: number;
  name: string;
  slug: string;
  role: string;
  created_at: string;
}

export interface ProjectResponse {
  id: number;
  workspace_id: number;
  name: string;
  slug: string;
  created_at: string;
}

export interface MemberResponse {
  id: number;
  user_id: number;
  email: string;
  name: string;
  role: string;
}

export async function fetchWorkspaces(): Promise<WorkspaceResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function createWorkspace(name: string): Promise<WorkspaceResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function updateWorkspace(id: number, name: string): Promise<WorkspaceResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function deleteWorkspace(id: number): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function fetchProjects(workspaceId: number): Promise<ProjectResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/projects`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function createProject(workspaceId: number, name: string): Promise<ProjectResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function updateProject(workspaceId: number, projectId: number, name: string): Promise<ProjectResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/projects/${projectId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function deleteProject(workspaceId: number, projectId: number): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/projects/${projectId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function fetchMembers(workspaceId: number): Promise<MemberResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/members`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function addMember(workspaceId: number, email: string, role: string): Promise<MemberResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function removeMember(workspaceId: number, memberId: number): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/members/${memberId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export interface RunAttempt {
  issue_id: string;
  issue_identifier: string;
  workspace_path: string;
  attempt_number: number;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface RetryEntry {
  issue_id: string;
  issue_identifier: string;
  attempt_number: number;
  scheduled_at: string;
  backoff_ms: number;
}

export interface CodexTotals {
  total_input_tokens: number;
  total_output_tokens: number;
  total_seconds_running: number;
}

export interface OrchestratorState {
  running: Record<string, RunAttempt>;
  retrying: Record<string, RetryEntry>;
  codex_totals: CodexTotals;
  rate_limits: Record<string, unknown>;
}

export interface ServiceStatus {
  service: string;
  version: string;
  status: string;
  orchestrator: boolean;
}

export async function fetchState(): Promise<OrchestratorState> {
  const res = await authFetch(`${API_BASE}/api/v1/state`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchServiceStatus(): Promise<ServiceStatus> {
  const res = await authFetch(`${API_BASE}/`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface ServiceConfig {
  tracker: {
    kind: string;
    endpoint: string;
    project_slug: string;
    api_key_set: boolean;
    active_states: string[];
    terminal_states: string[];
  };
  polling: { interval_ms: number };
  workspace: { root: string };
  agent: { max_concurrent_agents: number; max_retry_backoff_ms: number };
  codex: { command: string; turn_timeout_ms: number; stall_timeout_ms: number };
}

export async function fetchConfig(): Promise<ServiceConfig> {
  const res = await authFetch(`${API_BASE}/api/v1/config`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Connections
// ---------------------------------------------------------------------------

export interface TrackerConnection {
  id: number;
  kind: string;
  name: string;
  project: string;
  endpoint: string;
  has_token: boolean;
  created_at: string;
}

export async function fetchConnections(): Promise<TrackerConnection[]> {
  const res = await authFetch(`${API_BASE}/api/v1/connections`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function createConnection(body: {
  kind: string;
  name: string;
  project: string;
  token: string;
  endpoint?: string;
  workspace_id?: number;
}): Promise<TrackerConnection> {
  const res = await authFetch(`${API_BASE}/api/v1/connections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function deleteConnection(id: number): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/connections/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export interface UnifiedTask {
  external_ref: string;
  tracker_kind: string;
  connection_id: number;
  identifier: string;
  title: string;
  description: string | null;
  state: string;
  priority: number | null;
  labels: string[];
  url: string | null;
  created_at: string | null;
  updated_at: string | null;
  pipeline_status: string | null;
}

export const PIPELINE_STATUSES = [
  "queued",
  "implement",
  "review",
  "risk_profile",
  "deploy",
  "monitor",
] as const;

export type PipelineStatus = (typeof PIPELINE_STATUSES)[number];

export async function fetchTasks(params?: {
  connection_id?: number;
  search?: string;
  label?: string;
  pipeline_status?: string;
}): Promise<UnifiedTask[]> {
  const url = new URL(`${API_BASE}/api/v1/tasks`);
  if (params?.connection_id) url.searchParams.set("connection_id", String(params.connection_id));
  if (params?.search) url.searchParams.set("search", params.search);
  if (params?.label) url.searchParams.set("label", params.label);
  if (params?.pipeline_status) url.searchParams.set("pipeline_status", params.pipeline_status);
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function updateTaskStatus(
  externalRef: string,
  status: string,
  context?: {
    workspace_id?: number;
    project_id?: number;
    issue_title?: string;
    issue_description?: string;
    issue_url?: string;
  },
): Promise<{ agent_run_id?: number }> {
  const res = await authFetch(`${API_BASE}/api/v1/tasks/${externalRef}/status`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, ...context }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface AgentRunResponse {
  id: number;
  agent_type: string;
  task_pipeline_id: number;
  status: string;
  model: string;
  summary: string;
  error: string;
  cost_usd: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export async function fetchAgentRuns(workspaceId: number): Promise<AgentRunResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/agent-runs`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function removeTaskStatus(externalRef: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/tasks/${externalRef}/status`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

export async function fetchTaskRuns(externalRef: string): Promise<AgentRunResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/tasks/${externalRef}/runs`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchActiveRuns(workspaceId: number): Promise<AgentRunResponse[]> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/active-runs`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface AgentLogEntry {
  id: number;
  entry_type: string;
  content: string;
  created_at: string | null;
}

export async function fetchRunLogs(runId: number, afterId: number = 0): Promise<AgentLogEntry[]> {
  const url = `${API_BASE}/api/v1/agent-runs/${runId}/logs${afterId ? `?after_id=${afterId}` : ""}`;
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function triggerRefresh(): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/refresh`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

// ---------------------------------------------------------------------------
// API Keys
// ---------------------------------------------------------------------------

export interface ApiKeyStatus {
  provider: string;
  has_key: boolean;
  updated_at: string | null;
}

export async function getApiKeyStatus(workspaceId: number, provider: string): Promise<ApiKeyStatus> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/api-keys/${provider}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function setApiKey(workspaceId: number, provider: string, key: string): Promise<ApiKeyStatus> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/api-keys/${provider}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function deleteApiKey(workspaceId: number, provider: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/api-keys/${provider}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Agent Config
// ---------------------------------------------------------------------------

export interface AgentConfigResponse {
  agent_type: string;
  model: string;
  active: boolean;
  available_models: { id: string; name: string; description: string }[];
  extra_config: Record<string, unknown>;
}

export async function getAgentConfig(workspaceId: number, agentType: string): Promise<AgentConfigResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/agents/${agentType}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function updateAgentConfig(
  workspaceId: number,
  agentType: string,
  model?: string,
  extraConfig?: Record<string, unknown>,
): Promise<AgentConfigResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/workspaces/${workspaceId}/agents/${agentType}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, extra_config: extraConfig }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
