"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CentcomMetrics, CentcomRun, fetchCentcomMetrics } from "@/lib/api";

const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
};

const formatNumber = (n: number) => {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
};

export function CentcomPage({ workspaceId }: { workspaceId?: number }) {
  const router = useRouter();
  const [metrics, setMetrics] = useState<CentcomMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await fetchCentcomMetrics(workspaceId);
      setMetrics(data);
    } catch {}
    setLoading(false);
  }, [workspaceId]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  // Clock tick for uptime feel
  useEffect(() => {
    const t = setInterval(() => setTick(k => k + 1), 1000);
    return () => clearInterval(t);
  }, []);

  if (loading || !metrics) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-xs font-mono text-muted uppercase tracking-widest animate-pulse">
          Establishing link...
        </div>
      </div>
    );
  }

  const running = metrics.status_counts.running || 0;
  const pending = metrics.status_counts.pending || 0;
  const completed = metrics.status_counts.completed || 0;
  const failed = metrics.status_counts.failed || 0;
  const active = running + pending;
  const successRate = metrics.total_runs > 0
    ? Math.round((completed / metrics.total_runs) * 100)
    : 0;

  return (
    <div className="space-y-4 font-mono">
      {/* ── SITREP BAR ── */}
      <div className="border border-border rounded-md p-3 flex items-center justify-between bg-surface">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full border-2 ${
            active > 0 ? "bg-green-500 border-green-400 animate-pulse" : "bg-gray-400 border-gray-300"
          }`} />
          <span className="text-xs uppercase tracking-wider font-semibold">
            {active > 0 ? `${active} AGENT${active > 1 ? "S" : ""} DEPLOYED` : "STANDING BY"}
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10px] text-muted uppercase tracking-wider">
          <span>{metrics.total_runs} OPS TOTAL</span>
          <span className="text-green-700">{completed} SUCCESS</span>
          <span className="text-red-700">{failed} FAIL</span>
          <span>{successRate}% RATE</span>
        </div>
      </div>

      {/* ── WORKERS ── */}
      <div className="border border-border rounded-md overflow-hidden">
        <div className="px-3 py-2 border-b border-border bg-surface flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-3.5 h-3.5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" />
            </svg>
            <span className="text-[10px] uppercase tracking-widest font-semibold">Workers</span>
            <span className="text-[10px] text-muted">({metrics.workers.length} online)</span>
          </div>
        </div>
        {metrics.workers.length === 0 ? (
          <div className="px-3 py-4 text-center">
            <div className="text-[10px] uppercase tracking-widest text-muted">No workers connected</div>
            <div className="text-[9px] text-muted mt-1">Agents running in inline mode</div>
          </div>
        ) : (
          <div className="divide-y divide-border">
            {metrics.workers.map((w) => {
              const memPercent = w.memory_total_mb > 0 ? Math.round((w.memory_used_mb / w.memory_total_mb) * 100) : 0;
              return (
                <div key={w.id} className="px-3 py-2.5">
                  <div className="flex items-center gap-3 text-[11px] mb-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <span className="font-semibold">{w.hostname}</span>
                      <span className="text-muted ml-2">#{w.id}</span>
                    </div>
                    <div className="flex items-center gap-3 text-muted flex-shrink-0 text-[10px]">
                      <span>{w.active_jobs}/{w.concurrency} slots</span>
                      <span className="text-green-700 font-semibold">~{w.estimated_capacity} deployable</span>
                      {w.started_at && (
                        <span>up {formatDuration((Date.now() - new Date(w.started_at).getTime()) / 1000)}</span>
                      )}
                    </div>
                  </div>
                  {/* Resource bars */}
                  <div className="grid grid-cols-2 gap-3 pl-5">
                    <div>
                      <div className="flex items-center justify-between text-[9px] uppercase tracking-widest text-muted mb-1">
                        <span>CPU {w.cpu_count} cores</span>
                        <span>{w.cpu_percent}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            w.cpu_percent > 80 ? "bg-red-500" : w.cpu_percent > 50 ? "bg-orange-500" : "bg-green-500"
                          }`}
                          style={{ width: `${Math.min(w.cpu_percent, 100)}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-[9px] uppercase tracking-widest text-muted mb-1">
                        <span>MEM {(w.memory_used_mb / 1024).toFixed(1)}/{(w.memory_total_mb / 1024).toFixed(0)}GB</span>
                        <span>{memPercent}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            memPercent > 80 ? "bg-red-500" : memPercent > 50 ? "bg-orange-500" : "bg-green-500"
                          }`}
                          style={{ width: `${memPercent}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── PRIMARY READOUT ── */}
      <div className="grid grid-cols-4 gap-2">
        <Readout
          label="ACTIVE"
          value={active}
          status={active > 0 ? "hot" : "cold"}
        />
        <Readout
          label="COMPLETED"
          value={completed}
          status="good"
        />
        <Readout
          label="FAILED"
          value={failed}
          status={failed > 0 ? "warn" : "cold"}
        />
        <Readout
          label="SUCCESS RATE"
          value={`${successRate}%`}
          status={successRate >= 80 ? "good" : successRate >= 50 ? "warn" : "crit"}
        />
      </div>

      {/* ── RESOURCE GRID ── */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
        <DataCell label="COST" value={`$${metrics.total_cost.toFixed(2)}`} />
        <DataCell label="IN TOKENS" value={formatNumber(metrics.total_input_tokens)} />
        <DataCell label="OUT TOKENS" value={formatNumber(metrics.total_output_tokens)} />
        <DataCell label="RUNTIME" value={formatDuration(metrics.total_runtime_seconds)} />
        <DataCell label="PEAK MEM" value={metrics.peak_memory_mb > 0 ? `${metrics.peak_memory_mb.toFixed(0)}MB` : "—"} />
        <DataCell label="TASKS" value={String(metrics.tasks_completed)} />
      </div>

      {/* ── ACTIVE OPS ── */}
      <div className="border border-border rounded-md overflow-hidden">
        <div className="px-3 py-2 border-b border-border bg-surface flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${active > 0 ? "bg-green-500 animate-pulse" : "bg-gray-400"}`} />
            <span className="text-[10px] uppercase tracking-widest font-semibold">Active Operations</span>
            <span className="text-[10px] text-muted">({metrics.active_runs.length})</span>
          </div>
          <button
            onClick={() => router.push("/executions")}
            className="text-[10px] uppercase tracking-wider text-muted hover:text-foreground transition-colors"
          >
            All Ops &rarr;
          </button>
        </div>
        {metrics.active_runs.length === 0 ? (
          <div className="px-3 py-6 text-center">
            <div className="text-[10px] uppercase tracking-widest text-muted">No active deployments</div>
          </div>
        ) : (
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border text-[9px] uppercase tracking-widest text-muted">
                <th className="text-left px-3 py-1.5 font-medium">Status</th>
                <th className="text-left px-3 py-1.5 font-medium">Agent</th>
                <th className="text-left px-3 py-1.5 font-medium">Target</th>
                <th className="text-left px-3 py-1.5 font-medium">Operator</th>
                <th className="text-right px-3 py-1.5 font-medium">Elapsed</th>
              </tr>
            </thead>
            <tbody>
              {metrics.active_runs.map((run) => (
                <tr
                  key={run.id}
                  className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors cursor-pointer"
                  onClick={() => router.push(`/tasks/${encodeURIComponent(run.task_ref)}`)}
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2 rounded-full ${
                        run.status === "running" ? "bg-green-500 animate-pulse" : "bg-yellow-500 animate-pulse"
                      }`} />
                      <span className="uppercase text-[10px]">{run.status === "running" ? "LIVE" : "QUEUE"}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2 font-semibold uppercase">{run.agent_type.replace("_", " ")}</td>
                  <td className="px-3 py-2 text-muted">{run.repo ? run.repo.split("/").pop() : "—"}</td>
                  <td className="px-3 py-2 text-muted">{run.triggered_by || "—"}</td>
                  <td className="px-3 py-2 text-right">
                    {run.started_at ? (
                      <LiveTimer startedAt={run.started_at} tick={tick} />
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── RECENT OPS ── */}
      {metrics.recent_runs.length > 0 && (
        <div className="border border-border rounded-md overflow-hidden">
          <div className="px-3 py-2 border-b border-border bg-surface flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-widest font-semibold">Recent Operations</span>
            <button
              onClick={() => router.push("/executions")}
              className="text-[10px] uppercase tracking-wider text-muted hover:text-foreground transition-colors"
            >
              All Ops &rarr;
            </button>
          </div>
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-border text-[9px] uppercase tracking-widest text-muted">
                <th className="text-left px-3 py-1.5 font-medium">Result</th>
                <th className="text-left px-3 py-1.5 font-medium">Agent</th>
                <th className="text-left px-3 py-1.5 font-medium">Target</th>
                <th className="text-left px-3 py-1.5 font-medium">Operator</th>
                <th className="text-right px-3 py-1.5 font-medium">Duration</th>
                <th className="text-right px-3 py-1.5 font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {metrics.recent_runs.map((run) => {
                const duration = run.started_at && run.finished_at
                  ? formatDuration((new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000)
                  : "—";
                return (
                  <tr
                    key={run.id}
                    className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors cursor-pointer"
                    onClick={() => router.push(`/tasks/${encodeURIComponent(run.task_ref)}`)}
                  >
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center gap-1 text-[10px] uppercase font-semibold ${
                        run.status === "completed" ? "text-green-700" : "text-red-700"
                      }`}>
                        {run.status === "completed" ? "OK" : "FAIL"}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-semibold uppercase">{run.agent_type.replace("_", " ")}</td>
                    <td className="px-3 py-2 text-muted">{run.repo ? run.repo.split("/").pop() : "—"}</td>
                    <td className="px-3 py-2 text-muted">{run.triggered_by || "—"}</td>
                    <td className="px-3 py-2 text-right text-muted">{duration}</td>
                    <td className="px-3 py-2 text-right">${(run.cost_usd || 0).toFixed(4)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Readout: primary metric with status indicator ──
function Readout({ label, value, status }: {
  label: string;
  value: string | number;
  status: "hot" | "good" | "warn" | "crit" | "cold";
}) {
  const border = {
    hot: "border-green-500/50",
    good: "border-green-600/30",
    warn: "border-orange-500/40",
    crit: "border-red-500/40",
    cold: "border-border",
  }[status];

  const accent = {
    hot: "bg-green-500",
    good: "bg-green-600",
    warn: "bg-orange-500",
    crit: "bg-red-500",
    cold: "bg-gray-400",
  }[status];

  return (
    <div className={`border ${border} rounded-md p-3 bg-surface relative overflow-hidden`}>
      <div className={`absolute top-0 left-0 w-full h-0.5 ${accent}`} />
      <div className="text-[9px] uppercase tracking-widest text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold tracking-tight">{value}</div>
    </div>
  );
}

// ── DataCell: secondary metric ──
function DataCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-border rounded-md p-2.5 bg-surface">
      <div className="text-[8px] uppercase tracking-widest text-muted mb-1">{label}</div>
      <div className="text-sm font-bold tracking-tight">{value}</div>
    </div>
  );
}

// ── LiveTimer: ticking elapsed time ──
function LiveTimer({ startedAt, tick }: { startedAt: string; tick: number }) {
  const elapsed = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return (
    <span className="tabular-nums text-green-700">
      {String(m).padStart(2, "0")}:{String(s).padStart(2, "0")}
    </span>
  );
}
