"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AgentRunResponse,
  AgentLogEntry,
  PIPELINE_STATUSES,
  UnifiedTask,
  fetchTaskRuns,
  fetchRunLogs,
  updateTaskStatus,
} from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued", implement: "Implement", review: "Review",
  risk_profile: "Risk Profile", deploy: "Deploy", monitor: "Monitor",
};

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-gray-200 text-gray-800 border-gray-300",
  implement: "bg-blue-100 text-blue-800 border-blue-300",
  review: "bg-purple-100 text-purple-800 border-purple-300",
  risk_profile: "bg-orange-100 text-orange-800 border-orange-300",
  deploy: "bg-yellow-100 text-yellow-800 border-yellow-300",
  monitor: "bg-green-100 text-green-800 border-green-300",
};

const RUN_STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600 border-gray-300",
  running: "bg-blue-100 text-blue-700 border-blue-300",
  completed: "bg-green-100 text-green-700 border-green-300",
  failed: "bg-red-100 text-red-700 border-red-300",
};

export function TaskDetailPage({
  task,
  workspaceId,
  projectId,
  onBack,
  onTaskUpdated,
}: {
  task: UnifiedTask;
  workspaceId?: number;
  projectId?: number;
  onBack: () => void;
  onTaskUpdated: () => void;
}) {
  const [runs, setRuns] = useState<AgentRunResponse[]>([]);

  const loadRuns = useCallback(() => {
    if (!task.pipeline_status) return;
    fetchTaskRuns(task.external_ref).then(setRuns).catch(() => {});
  }, [task.external_ref, task.pipeline_status]);

  useEffect(() => {
    loadRuns();
    const interval = setInterval(loadRuns, 3000);
    return () => clearInterval(interval);
  }, [loadRuns]);

  const handleStatusChange = async (status: string) => {
    try {
      await updateTaskStatus(task.external_ref, status, {
        workspace_id: workspaceId,
        project_id: projectId,
        issue_title: task.title,
        issue_description: task.description || "",
        issue_url: task.url || "",
      });
      onTaskUpdated();
      loadRuns();
    } catch {}
  };

  return (
    <div className="max-w-3xl">
      {/* Back button */}
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground mb-4 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
        Back to tasks
      </button>

      {/* Header */}
      <div className="rounded-lg border border-border bg-surface p-5 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-mono text-muted">{task.identifier}</span>
          <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-muted">{task.tracker_kind}</span>
          {task.pipeline_status && (
            <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_COLORS[task.pipeline_status] || ""}`}>
              {STATUS_LABELS[task.pipeline_status] || task.pipeline_status}
            </span>
          )}
        </div>
        <h2 className="text-lg font-semibold mb-1">
          {task.url ? (
            <a href={task.url} target="_blank" rel="noopener noreferrer" className="hover:underline">{task.title}</a>
          ) : task.title}
        </h2>
        {task.description && (
          <p className="text-sm text-muted mt-2 whitespace-pre-wrap">{task.description}</p>
        )}
        {task.labels.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {task.labels.map((l) => (
              <span key={l} className="text-xs px-1.5 py-0.5 rounded-full bg-surface-hover text-muted">{l}</span>
            ))}
          </div>
        )}

        {/* Status selector */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-muted">Pipeline:</span>
          <select
            value={task.pipeline_status || ""}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="text-xs px-2 py-1 rounded-md border border-border bg-background text-foreground"
          >
            <option value="" disabled>Set status...</option>
            {PIPELINE_STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Activity Log */}
      <div className="rounded-lg border border-border bg-surface overflow-hidden">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-medium">Activity</h3>
        </div>
        <div className="p-5">
          {runs.length === 0 ? (
            <div className="text-xs text-muted">
              {task.pipeline_status ? "No agent activity yet. Agents are triggered when you move the task to a pipeline stage." : "Set a pipeline status to start."}
            </div>
          ) : (
            <div className="space-y-4">
              {runs.map((run) => (
                <RunEntry key={run.id} run={run} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RunEntry({ run }: { run: AgentRunResponse }) {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const [lastLogId, setLastLogId] = useState(0);
  const isLive = run.status === "running" || run.status === "pending";

  useEffect(() => {
    const load = async () => {
      try {
        const newLogs = await fetchRunLogs(run.id, lastLogId);
        if (newLogs.length > 0) {
          setLogs((prev) => [...prev, ...newLogs]);
          setLastLogId(newLogs[newLogs.length - 1].id);
        }
      } catch {}
    };
    load();
    if (isLive) {
      const interval = setInterval(load, 2000);
      return () => clearInterval(interval);
    }
  }, [run.id, isLive, lastLogId]);

  const logTypeIcons: Record<string, string> = {
    tool_use: "wrench",
    text: "chat",
    status: "info",
    error: "alert",
  };

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className={`w-3 h-3 rounded-full flex-shrink-0 ${
          run.status === "completed" ? "bg-green-500" :
          run.status === "running" ? "bg-blue-500 animate-pulse" :
          run.status === "failed" ? "bg-red-500" : "bg-gray-400"
        }`} />
        <div className="w-px flex-1 bg-border mt-1" />
      </div>
      <div className="flex-1 pb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium capitalize">{run.agent_type.replace("_", " ")} Agent</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${RUN_STATUS_COLORS[run.status] || ""}`}>
            {run.status}
          </span>
        </div>
        <div className="text-xs text-muted mb-2">
          {run.started_at && `Started ${new Date(run.started_at).toLocaleString()}`}
          {run.finished_at && ` — Finished ${new Date(run.finished_at).toLocaleTimeString()}`}
        </div>

        {/* Live logs */}
        {logs.length > 0 && (
          <div className="rounded-md border border-border bg-background overflow-hidden">
            <div className="max-h-64 overflow-y-auto">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`px-3 py-1.5 border-b border-border last:border-0 text-xs font-mono ${
                    log.entry_type === "error" ? "bg-red-50 text-red-700" :
                    log.entry_type === "tool_use" ? "text-blue-700" :
                    log.entry_type === "status" ? "text-muted italic" :
                    "text-foreground"
                  }`}
                >
                  <span className="text-[10px] text-muted mr-2">
                    {log.created_at ? new Date(log.created_at).toLocaleTimeString() : ""}
                  </span>
                  {log.content}
                </div>
              ))}
            </div>
          </div>
        )}

        {run.summary && !isLive && (
          <div className="text-xs bg-background rounded-md border border-border p-2 mt-2">
            {run.summary}
          </div>
        )}
        {run.error && (
          <div className="text-xs bg-red-50 text-red-700 rounded-md border border-red-200 p-2 mt-2">
            {run.error}
          </div>
        )}
        {run.cost_usd > 0 && (
          <div className="text-[10px] text-muted mt-1">Cost: ${run.cost_usd.toFixed(4)}</div>
        )}
      </div>
    </div>
  );
}
