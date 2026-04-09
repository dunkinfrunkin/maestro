"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ExecutionEntry, fetchExecutions } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800 border-green-300",
  running: "bg-blue-100 text-blue-800 border-blue-300",
  pending: "bg-gray-100 text-gray-800 border-gray-300",
  failed: "bg-red-100 text-red-800 border-red-300",
};

const formatDuration = (ms: number) => {
  if (ms === 0) return "—";
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
};

export function ExecutionsPage({ workspaceId }: { workspaceId?: number }) {
  const router = useRouter();
  const [executions, setExecutions] = useState<ExecutionEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterEngineer, setFilterEngineer] = useState<string>("");
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const load = useCallback(async (p = page) => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      const data = await fetchExecutions(workspaceId, {
        status: filterStatus || undefined,
        offset: p * pageSize,
        limit: pageSize,
      });
      setExecutions(data.executions);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch executions");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, filterStatus, page]);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh for active runs
  useEffect(() => {
    if (!workspaceId) return;
    const hasActive = executions.some(e => e.status === "running" || e.status === "pending");
    if (!hasActive) return;
    const interval = setInterval(() => load(), 5000);
    return () => clearInterval(interval);
  }, [workspaceId, executions, load]);

  const engineers = [...new Set(executions.map(e => e.triggered_by).filter(Boolean))];
  const filtered = filterEngineer
    ? executions.filter(e => e.triggered_by === filterEngineer)
    : executions;
  const totalPages = Math.ceil(total / pageSize);
  const totalCost = executions.reduce((sum, e) => sum + (e.cost_usd || 0), 0);

  return (
    <div className="space-y-4">
      {/* Summary metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div className="rounded-lg border border-border bg-surface p-3">
          <div className="text-xs text-muted">Total Runs</div>
          <div className="text-lg font-mono font-semibold">{total}</div>
        </div>
        <div className="rounded-lg border border-border bg-surface p-3">
          <div className="text-xs text-muted">Active</div>
          <div className="text-lg font-mono font-semibold">
            {executions.filter(e => e.status === "running" || e.status === "pending").length}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-surface p-3">
          <div className="text-xs text-muted">Cost (page)</div>
          <div className="text-lg font-mono font-semibold">${totalCost.toFixed(4)}</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <select
          value={filterStatus}
          onChange={(e) => { setFilterStatus(e.target.value); setPage(0); }}
          className="text-xs px-2 py-1.5 rounded-md border border-border bg-background text-foreground"
        >
          <option value="">All statuses</option>
          <option value="running">Running</option>
          <option value="pending">Pending</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={filterEngineer}
          onChange={(e) => setFilterEngineer(e.target.value)}
          className="text-xs px-2 py-1.5 rounded-md border border-border bg-background text-foreground"
        >
          <option value="">All engineers</option>
          {engineers.map(e => (
            <option key={e} value={e}>{e}</option>
          ))}
        </select>
        <span className="text-xs text-muted">{total} executions</span>
      </div>

      {error && (
        <div className="p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{error}</div>
      )}

      {/* Executions table */}
      {loading && executions.length === 0 ? (
        <div className="text-sm text-muted text-center py-8">Loading...</div>
      ) : executions.length === 0 ? (
        <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
          No executions found
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-surface-hover">
                <th className="text-left px-3 py-2 font-medium text-muted">Agent</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Engineer</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Task</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Status</th>
                <th className="text-right px-3 py-2 font-medium text-muted">Cost</th>
                <th className="text-right px-3 py-2 font-medium text-muted">Duration</th>
                <th className="text-right px-3 py-2 font-medium text-muted">Started</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((exec) => {
                const duration = exec.started_at && exec.finished_at
                  ? new Date(exec.finished_at).getTime() - new Date(exec.started_at).getTime()
                  : 0;
                // Parse task ref to get the task route: "jira:3:123" → encoded for URL
                const taskRoute = exec.task_ref ? `/tasks/${encodeURIComponent(exec.task_ref)}` : null;

                return (
                  <tr
                    key={exec.id}
                    className={`border-b border-border last:border-0 hover:bg-surface-hover transition-colors ${taskRoute ? "cursor-pointer" : ""}`}
                    onClick={() => taskRoute && router.push(taskRoute)}
                  >
                    <td className="px-3 py-2.5">
                      <span className="font-medium capitalize">{exec.agent_type.replace("_", " ")}</span>
                    </td>
                    <td className="px-3 py-2.5 text-muted">
                      {exec.triggered_by || "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="font-mono text-muted truncate max-w-[200px]" title={exec.task_ref}>
                        {exec.repo ? exec.repo.split("/").pop() : exec.task_ref.split(":").pop()}
                      </div>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] ${STATUS_COLORS[exec.status] || ""}`}>
                        {exec.status === "running" && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                        )}
                        {exec.status}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">${(exec.cost_usd || 0).toFixed(4)}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-muted">
                      {exec.status === "running" ? (
                        <span className="text-blue-600">live</span>
                      ) : formatDuration(duration)}
                    </td>
                    <td className="px-3 py-2.5 text-right text-muted">
                      {exec.started_at ? new Date(exec.started_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-muted">
            {page * pageSize + 1}–{Math.min((page + 1) * pageSize, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= totalPages - 1}
              className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
