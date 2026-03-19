"use client";

import { OrchestratorState, RunAttempt, RetryEntry } from "@/lib/api";

export function AgentsPage({ state }: { state: OrchestratorState | null }) {
  const running = state ? Object.values(state.running) : [];
  const retrying = state ? Object.values(state.retrying) : [];
  const allAgents = [
    ...running.map((a) => ({ ...a, type: "running" as const })),
    ...retrying.map((r) => ({ ...r, type: "retrying" as const })),
  ];

  return (
    <div className="space-y-8">
      {/* Agent Sessions */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Agent Sessions</h2>
        {allAgents.length === 0 ? (
          <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
            No active agent sessions
          </div>
        ) : (
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-surface border-b border-border text-left">
                  <th className="px-4 py-3 font-medium text-muted">Issue</th>
                  <th className="px-4 py-3 font-medium text-muted">Status</th>
                  <th className="px-4 py-3 font-medium text-muted">Attempt</th>
                  <th className="px-4 py-3 font-medium text-muted">Started</th>
                  <th className="px-4 py-3 font-medium text-muted">Details</th>
                </tr>
              </thead>
              <tbody>
                {running.map((attempt) => (
                  <AgentRow key={attempt.issue_id} attempt={attempt} />
                ))}
                {retrying.map((entry) => (
                  <RetryRow key={entry.issue_id} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Configuration */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Configuration</h2>
        {state ? (
          <div className="grid gap-4 md:grid-cols-2">
            <ConfigCard
              title="Concurrency"
              items={[
                {
                  label: "Running agents",
                  value: String(Object.keys(state.running).length),
                },
                {
                  label: "Retry queue",
                  value: String(Object.keys(state.retrying).length),
                },
              ]}
            />
            <ConfigCard
              title="Token Usage"
              items={[
                {
                  label: "Input tokens",
                  value: state.codex_totals.total_input_tokens.toLocaleString(),
                },
                {
                  label: "Output tokens",
                  value: state.codex_totals.total_output_tokens.toLocaleString(),
                },
                {
                  label: "Total runtime",
                  value: formatDuration(state.codex_totals.total_seconds_running),
                },
              ]}
            />
          </div>
        ) : (
          <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
            Configuration unavailable — orchestrator not connected
          </div>
        )}
      </section>
    </div>
  );
}

function AgentRow({ attempt }: { attempt: RunAttempt }) {
  return (
    <tr className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors">
      <td className="px-4 py-3 font-mono font-medium">
        {attempt.issue_identifier}
      </td>
      <td className="px-4 py-3">
        <StatusBadge status={attempt.status} />
      </td>
      <td className="px-4 py-3">#{attempt.attempt_number}</td>
      <td className="px-4 py-3 text-muted">
        {attempt.started_at
          ? new Date(attempt.started_at).toLocaleTimeString()
          : "—"}
      </td>
      <td className="px-4 py-3 text-muted">
        {attempt.error ? (
          <span className="text-red-600">{attempt.error}</span>
        ) : (
          attempt.workspace_path || "—"
        )}
      </td>
    </tr>
  );
}

function RetryRow({ entry }: { entry: RetryEntry }) {
  return (
    <tr className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors">
      <td className="px-4 py-3 font-mono font-medium">
        {entry.issue_identifier}
      </td>
      <td className="px-4 py-3">
        <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-300">
          retrying
        </span>
      </td>
      <td className="px-4 py-3">#{entry.attempt_number}</td>
      <td className="px-4 py-3 text-muted">
        {new Date(entry.scheduled_at).toLocaleTimeString()}
      </td>
      <td className="px-4 py-3 text-muted">
        Backoff: {(entry.backoff_ms / 1000).toFixed(0)}s
      </td>
    </tr>
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

function ConfigCard({
  title,
  items,
}: {
  title: string;
  items: { label: string; value: string }[];
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <h3 className="text-sm font-medium mb-3">{title}</h3>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between text-sm">
            <span className="text-muted">{item.label}</span>
            <span className="font-mono">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}
