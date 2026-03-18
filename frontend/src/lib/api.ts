const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const res = await fetch(`${API_BASE}/api/v1/state`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchServiceStatus(): Promise<ServiceStatus> {
  const res = await fetch(`${API_BASE}/`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function triggerRefresh(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/refresh`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
}
