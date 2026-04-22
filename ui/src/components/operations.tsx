"use client";

import { useEffect, useState } from "react";
import {
  AgentRunResponse,
  CodexTotals,
  OrchestratorState,
  RetryEntry,
  RunAttempt,
  fetchActiveRuns,
} from "@/lib/api";

export function OperationsPage({ state, workspaceId }: { state: OrchestratorState | null; workspaceId?: number }) {
  const running = state ? Object.values(state.running) : [];
  const retrying = state ? Object.values(state.retrying) : [];
  const [activeRuns, setActiveRuns] = useState<AgentRunResponse[]>([]);

  useEffect(() => {
    if (!workspaceId) return;
    const load = () => fetchActiveRuns(workspaceId).then(setActiveRuns).catch(() => {});
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [workspaceId]);

  return (
    <>
      {/* Active Agent Runs */}
      {activeRuns.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3">
            Active Agents
            <span className="ml-2 text-sm font-normal text-muted">({activeRuns.length})</span>
          </h2>
          <div className="space-y-2">
            {activeRuns.map((run) => (
              <div key={run.id} className="rounded-lg border border-border bg-surface p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${run.status === "running" ? "bg-blue-500 animate-pulse" : "bg-gray-400"}`} />
                  <div>
                    <div className="text-xs font-medium capitalize">{(run as any).agent_type?.replace("_", " ") || "agent"}</div>
                    <div className="text-[10px] text-muted">{(run as any).task_ref || ""}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full border bg-blue-100 text-blue-700 border-blue-300">
                    {run.status}
                  </span>
                  <span className="text-[10px] text-muted">
                    {run.started_at ? new Date(run.started_at).toLocaleTimeString() : ""}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {state && (
        <MetricsBar
          totals={state.codex_totals}
          running={running.length}
          retrying={retrying.length}
        />
      )}

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">
          Running Agents
          <span className="ml-2 text-sm font-normal text-muted">
            ({running.length})
          </span>
        </h2>
        {running.length === 0 ? (
          <EmptyState message="No agents currently running" />
        ) : (
          <div className="grid gap-3">
            {running.map((attempt) => (
              <RunningCard key={attempt.issue_id} attempt={attempt} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">
          Retry Queue
          <span className="ml-2 text-sm font-normal text-muted">
            ({retrying.length})
          </span>
        </h2>
        {retrying.length === 0 ? (
          <EmptyState message="No issues queued for retry" />
        ) : (
          <div className="grid gap-3">
            {retrying.map((entry) => (
              <RetryCard key={entry.issue_id} entry={entry} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function MetricsBar({
  totals,
  running,
  retrying,
}: {
  totals: CodexTotals;
  running: number;
  retrying: number;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
      <MetricCard label="Running" value={running} />
      <MetricCard label="Retrying" value={retrying} />
      <MetricCard
        label="Input Tokens"
        value={totals.total_input_tokens.toLocaleString()}
      />
      <MetricCard
        label="Output Tokens"
        value={totals.total_output_tokens.toLocaleString()}
      />
      <MetricCard
        label="Runtime"
        value={formatDuration(totals.total_seconds_running)}
      />
    </div>
  );
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className="text-xl font-mono font-semibold">{value}</div>
    </div>
  );
}

function RunningCard({ attempt }: { attempt: RunAttempt }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono font-semibold">
          {attempt.issue_identifier}
        </span>
        <StatusBadge status={attempt.status} />
      </div>
      <div className="text-sm text-muted space-y-1">
        <div>Attempt #{attempt.attempt_number}</div>
        {attempt.started_at && (
          <div>
            Started: {new Date(attempt.started_at).toLocaleTimeString()}
          </div>
        )}
        {attempt.error && (
          <div className="text-red-600 mt-1">
            {attempt.error}
          </div>
        )}
      </div>
    </div>
  );
}

function RetryCard({ entry }: { entry: RetryEntry }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono font-semibold">
          {entry.issue_identifier}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-300">
          retry #{entry.attempt_number}
        </span>
      </div>
      <div className="text-sm text-muted">
        <div>Backoff: {(entry.backoff_ms / 1000).toFixed(0)}s</div>
        <div>
          Scheduled: {new Date(entry.scheduled_at).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    preparing_workspace:
      "bg-blue-100 text-blue-800 border-blue-300",
    building_prompt:
      "bg-blue-100 text-blue-800 border-blue-300",
    launching_agent:
      "bg-purple-100 text-purple-800 border-purple-300",
    streaming_turn:
      "bg-green-100 text-green-800 border-green-300",
    succeeded:
      "bg-green-100 text-green-800 border-green-300",
    failed:
      "bg-red-100 text-red-800 border-red-300",
    timed_out:
      "bg-orange-100 text-orange-800 border-orange-300",
    stalled:
      "bg-orange-100 text-orange-800 border-orange-300",
    canceled:
      "bg-gray-100 text-gray-800 border-gray-300",
  };

  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${
        colors[status] ||
        "bg-gray-100 text-gray-800 border-gray-300"
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
      {message}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}
