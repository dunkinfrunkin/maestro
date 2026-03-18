"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CodexTotals,
  OrchestratorState,
  RetryEntry,
  RunAttempt,
  fetchState,
  triggerRefresh,
} from "@/lib/api";

const POLL_INTERVAL = 3000;

export default function Dashboard() {
  const [state, setState] = useState<OrchestratorState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchState();
      setState(data);
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
    } catch {
      // refresh error handled by polling
    }
  };

  const running = state ? Object.values(state.running) : [];
  const retrying = state ? Object.values(state.retrying) : [];

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-[family-name:var(--font-geist-sans)]">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Maestro</h1>
          <p className="text-sm opacity-60">Symphony orchestration dashboard</p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-xs opacity-40">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={handleRefresh}
            className="px-3 py-1.5 text-sm rounded-md border border-foreground/20 hover:bg-foreground/5 transition-colors"
          >
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-6 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Metrics */}
      {state && <MetricsBar totals={state.codex_totals} running={running.length} retrying={retrying.length} />}

      {/* Running Agents */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">
          Running Agents
          <span className="ml-2 text-sm font-normal opacity-50">({running.length})</span>
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

      {/* Retry Queue */}
      <section>
        <h2 className="text-lg font-semibold mb-3">
          Retry Queue
          <span className="ml-2 text-sm font-normal opacity-50">({retrying.length})</span>
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
    </div>
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
      <MetricCard label="Input Tokens" value={totals.total_input_tokens.toLocaleString()} />
      <MetricCard label="Output Tokens" value={totals.total_output_tokens.toLocaleString()} />
      <MetricCard
        label="Runtime"
        value={formatDuration(totals.total_seconds_running)}
      />
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-foreground/10 p-4">
      <div className="text-xs opacity-50 mb-1">{label}</div>
      <div className="text-xl font-mono font-semibold">{value}</div>
    </div>
  );
}

function RunningCard({ attempt }: { attempt: RunAttempt }) {
  return (
    <div className="rounded-lg border border-foreground/10 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono font-semibold">{attempt.issue_identifier}</span>
        <StatusBadge status={attempt.status} />
      </div>
      <div className="text-sm opacity-60 space-y-1">
        <div>Attempt #{attempt.attempt_number}</div>
        {attempt.started_at && (
          <div>Started: {new Date(attempt.started_at).toLocaleTimeString()}</div>
        )}
        {attempt.error && (
          <div className="text-red-400 mt-1">{attempt.error}</div>
        )}
      </div>
    </div>
  );
}

function RetryCard({ entry }: { entry: RetryEntry }) {
  return (
    <div className="rounded-lg border border-foreground/10 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono font-semibold">{entry.issue_identifier}</span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
          retry #{entry.attempt_number}
        </span>
      </div>
      <div className="text-sm opacity-60">
        <div>Backoff: {(entry.backoff_ms / 1000).toFixed(0)}s</div>
        <div>Scheduled: {new Date(entry.scheduled_at).toLocaleTimeString()}</div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    preparing_workspace: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    building_prompt: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    launching_agent: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    streaming_turn: "bg-green-500/10 text-green-400 border-green-500/20",
    succeeded: "bg-green-500/10 text-green-400 border-green-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
    timed_out: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    stalled: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    canceled: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  };

  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${
        colors[status] || "bg-gray-500/10 text-gray-400 border-gray-500/20"
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-foreground/5 border-dashed p-8 text-center opacity-40 text-sm">
      {message}
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}
