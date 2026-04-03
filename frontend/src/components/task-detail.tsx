"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AgentRunResponse,
  AgentLogEntry,
  PIPELINE_STATUSES,
  UnifiedTask,
  RepoEntry,
  fetchTaskRuns,
  fetchRunLogs,
  updateTaskStatus,
  fetchRepos,
  updateTaskRepo,
} from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued", implement: "Implement", review: "Review",
  risk_profile: "Risk Profile", deploy: "Deploy", monitor: "Monitor",
};

const formatDuration = (ms: number) => {
  if (ms === 0) return "0s";
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  } else {
    return `${seconds}s`;
  }
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

const AGENT_COLORS: Record<string, { completed: string; failed: string; running: string; pending: string }> = {
  implementation: {
    completed: "bg-green-600 text-white",
    failed: "bg-green-800 text-white",
    running: "bg-green-500 text-white animate-pulse",
    pending: "bg-green-300 text-green-800"
  },
  review: {
    completed: "bg-purple-600 text-white",
    failed: "bg-purple-800 text-white",
    running: "bg-purple-500 text-white animate-pulse",
    pending: "bg-purple-300 text-purple-800"
  },
  risk_profile: {
    completed: "bg-orange-600 text-white",
    failed: "bg-orange-800 text-white",
    running: "bg-orange-500 text-white animate-pulse",
    pending: "bg-orange-300 text-orange-800"
  },
  deployment: {
    completed: "bg-blue-600 text-white",
    failed: "bg-blue-800 text-white",
    running: "bg-blue-500 text-white animate-pulse",
    pending: "bg-blue-300 text-blue-800"
  },
  monitor: {
    completed: "bg-teal-600 text-white",
    failed: "bg-teal-800 text-white",
    running: "bg-teal-500 text-white animate-pulse",
    pending: "bg-teal-300 text-teal-800"
  }
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

  // Extract repo from identifier (e.g., "owner/repo#123" → "owner/repo")
  const repo = task.identifier.includes("#")
    ? task.identifier.split("#")[0]
    : "";

  const handleStatusChange = async (status: string) => {
    try {
      console.log("[MAESTRO] handleStatusChange", { status, title: task.title, descLen: task.description?.length, url: task.url });
      await updateTaskStatus(task.external_ref, status, {
        workspace_id: workspaceId,
        project_id: projectId,
        repo,
        issue_title: task.title,
        issue_description: task.description || "",
        issue_url: task.url || "",
      });
      onTaskUpdated();
      loadRuns();
    } catch {}
  };

  // Calculate totals
  const totalCost = runs.reduce((sum, run) => sum + (run.cost_usd || 0), 0);
  const totalInputTokens = runs.reduce((sum, run) => sum + (run.input_tokens || 0), 0);
  const totalOutputTokens = runs.reduce((sum, run) => sum + (run.output_tokens || 0), 0);

  // Calculate total time (sum of all individual run durations)
  const totalDuration = runs.reduce((sum, run) => {
    if (run.started_at && run.finished_at) {
      const start = new Date(run.started_at).getTime();
      const end = new Date(run.finished_at).getTime();
      return sum + (end - start);
    }
    return sum;
  }, 0);


  return (
    <div className="w-full">
      {/* Back button */}
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground mb-4 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
        Back to tasks
      </button>

      <div className="flex gap-6 w-full">
        <div className="flex-1 min-w-0">

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
          <div className="text-sm text-muted mt-2 prose prose-sm prose-neutral dark:prose-invert max-w-none
            prose-headings:text-foreground prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2
            prose-p:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
            prose-code:text-xs prose-code:bg-surface-hover prose-code:px-1 prose-code:py-0.5 prose-code:rounded
            prose-pre:bg-surface-hover prose-pre:border prose-pre:border-border prose-pre:rounded-md
            prose-a:text-accent prose-a:no-underline hover:prose-a:underline
            prose-strong:text-foreground prose-hr:border-border">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{task.description}</ReactMarkdown>
          </div>
        )}
        {task.labels.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-3">
            {task.labels.map((l) => (
              <span key={l} className="text-xs px-1.5 py-0.5 rounded-full bg-surface-hover text-muted">{l}</span>
            ))}
          </div>
        )}

        </div>

        {/* Agent Execution Trace */}
        <ExecutionTrace runs={runs} task={task} />

        {/* Activity Log */}
        <div className="rounded-lg border border-border bg-surface overflow-hidden mt-4">
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
                  <RunEntry
                    key={run.id}
                    run={run}
                    onRerun={() => handleStatusChange(run.agent_type === "implementation" ? "implement" : run.agent_type === "risk_profile" ? "risk_profile" : run.agent_type)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 flex-shrink-0">
        <div className="sticky top-20 space-y-4">

          {/* Task Settings */}
          <div className="rounded-lg border border-border bg-surface p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Task Settings
            </h3>

            <div className="space-y-4">
              {/* Task Link */}
              {task.url && (
                <div>
                  <div className="text-xs text-muted mb-2">Issue Link</div>
                  <a
                    href={task.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-accent hover:underline p-2 rounded border border-border hover:bg-surface-hover transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    {task.identifier}
                  </a>
                </div>
              )}

              {/* Repository */}
              <div>
                <div className="text-xs text-muted mb-2">Repository</div>
                <RepoSelector task={task} projectId={projectId} onRepoChanged={onTaskUpdated} />
              </div>

              {/* Pipeline Status */}
              <div>
                <div className="text-xs text-muted mb-2">Pipeline Status</div>
                <div className="flex gap-2">
                  <select
                    value={task.pipeline_status || ""}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    className="flex-1 text-xs px-2 py-1 rounded-md border border-border bg-background text-foreground"
                  >
                    <option value="" disabled>Set status...</option>
                    {PIPELINE_STATUSES.map((s) => (
                      <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                    ))}
                  </select>
                  {task.pipeline_status && task.pipeline_status !== "queued" && (
                    <button
                      onClick={() => handleStatusChange(task.pipeline_status!)}
                      className="flex items-center justify-center w-8 h-6 rounded-md border border-border hover:bg-surface-hover transition-colors text-muted hover:text-foreground"
                      title="Re-run the current stage agent"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {/* PR Link */}
              {task.pr_url && (
                <div>
                  <div className="text-xs text-muted mb-2">Pull Request</div>
                  <a
                    href={task.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-xs text-accent hover:underline p-2 rounded border border-border hover:bg-surface-hover transition-colors font-mono"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    <span className="truncate">
                      {task.pr_url.replace(/^https?:\/\//, '')}
                    </span>
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Task Metrics */}
          <div className="rounded-lg border border-border bg-surface p-5">
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Task Metrics
            </h3>

            <div className="space-y-4">
              <div className="bg-surface-hover/50 rounded-md p-3">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"/>
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd"/>
                  </svg>
                  <span className="text-xs font-medium text-muted">Total Cost</span>
                </div>
                <div className="font-mono text-lg font-semibold text-foreground">
                  ${totalCost.toFixed(4)}
                </div>
              </div>

              <div className="bg-surface-hover/50 rounded-md p-3">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs font-medium text-muted">Total Tokens</span>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-muted">Input:</span>
                    <span className="font-mono">{totalInputTokens.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-muted">Output:</span>
                    <span className="font-mono">{totalOutputTokens.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-xs pt-1 border-t border-border">
                    <span className="text-muted font-medium">Total:</span>
                    <span className="font-mono font-semibold">{(totalInputTokens + totalOutputTokens).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="bg-surface-hover/50 rounded-md p-3">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span className="text-xs font-medium text-muted">Agent Runs</span>
                </div>
                <div className="font-mono text-lg font-semibold text-foreground">
                  {runs.length}
                </div>
              </div>

              <div className="bg-surface-hover/50 rounded-md p-3">
                <div className="flex items-center gap-2 mb-2">
                  <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-xs font-medium text-muted">Total Time</span>
                </div>
                <div className="font-mono text-lg font-semibold text-foreground">
                  {formatDuration(totalDuration)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
}

function ExecutionTrace({ runs, task }: { runs: AgentRunResponse[]; task: UnifiedTask }) {
  const [showModal, setShowModal] = useState(false);

  // Calculate waterfall chart data
  const sortedRuns = [...runs].sort((a, b) => new Date(a.started_at || 0).getTime() - new Date(b.started_at || 0).getTime());
  const earliestStart = sortedRuns[0]?.started_at ? new Date(sortedRuns[0].started_at).getTime() : Date.now();
  const latestEnd = Math.max(...sortedRuns.map(r => r.finished_at ? new Date(r.finished_at).getTime() : Date.now()));
  const totalDuration = latestEnd - earliestStart || 1;

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden mt-4">
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <svg className="w-4 h-4 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Execution Trace
        </h3>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1 text-xs text-muted hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-surface-hover"
          title="Expand trace view"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          Expand
        </button>
      </div>

      <div className="p-5">
        {runs.length === 0 ? (
          <div className="text-xs text-muted">
            {task.pipeline_status ? "No agent execution yet. Agents are triggered when you move the task to a pipeline stage." : "Set a pipeline status to start."}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[700px]">
              {/* Agent runs */}
              <div className="space-y-2">
                {sortedRuns.map((run) => {
                const startTime = run.started_at ? new Date(run.started_at).getTime() : earliestStart;
                const endTime = run.finished_at ? new Date(run.finished_at).getTime() : Date.now();
                const runDuration = endTime - startTime;
                const leftPercent = ((startTime - earliestStart) / totalDuration) * 100;
                const widthPercent = Math.max((runDuration / totalDuration) * 100, 3);

                return (
                  <div key={run.id} className="flex items-center h-12">
                    {/* Chart bar area - full width */}
                    <div className="w-full relative h-10 bg-surface-hover rounded-md">
                      <div
                        className={`
                          absolute h-full rounded-md flex flex-col justify-center px-4 py-3 text-xs transition-colors overflow-hidden
                          ${AGENT_COLORS[run.agent_type]?.[run.status as keyof typeof AGENT_COLORS[string]] || 'bg-gray-500 text-white'}
                        `}
                        style={{
                          left: `${leftPercent}%`,
                          width: `${widthPercent}%`,
                          minWidth: '140px'
                        }}
                      >
                        <div className="flex items-center justify-between leading-tight">
                          <div>
                            <div className="font-semibold truncate capitalize">
                              {run.agent_type.replace('_', ' ')}
                            </div>
                            <div className="text-xs opacity-80 leading-tight">
                              {formatDuration(runDuration)}
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="font-mono text-xs">
                              ${(run.cost_usd || 0).toFixed(4)}
                            </div>
                            <div className="font-mono text-xs opacity-80">
                              {(run.input_tokens || 0).toLocaleString()}/{(run.output_tokens || 0).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

              {/* Time axis */}
              <div className="mt-3 pt-2 border-t border-border">
                <div className="relative h-4">
                  {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
                    <div
                      key={fraction}
                      className="absolute bottom-0 text-xs text-muted font-mono"
                      style={{
                        left: `${fraction * 100}%`,
                        transform: fraction === 0 ? 'translateX(0%)' : fraction === 1 ? 'translateX(-100%)' : 'translateX(-50%)'
                      }}
                    >
                      {fraction === 0 ? '0s' : formatDuration(totalDuration * fraction)}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Expanded Modal */}
      {showModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowModal(false)}
        >
          <div
            className="bg-surface border border-border rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden shadow-xl"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-background">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <svg className="w-5 h-5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Execution Trace
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="flex items-center justify-center w-8 h-8 rounded-md hover:bg-surface-hover transition-colors text-muted hover:text-foreground"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              {/* Agent runs - larger format */}
              <div className="space-y-4 mb-6">
                {sortedRuns.map((run) => {
                  const startTime = run.started_at ? new Date(run.started_at).getTime() : earliestStart;
                  const endTime = run.finished_at ? new Date(run.finished_at).getTime() : Date.now();
                  const runDuration = endTime - startTime;
                  const leftPercent = ((startTime - earliestStart) / totalDuration) * 100;
                  const widthPercent = Math.max((runDuration / totalDuration) * 100, 5);

                  return (
                    <div key={run.id} className="flex items-center h-16">
                      {/* Agent info */}
                      <div className="w-36 text-sm pr-4 flex-shrink-0">
                        <div className="font-semibold capitalize text-foreground">{run.agent_type.replace('_', ' ')}</div>
                        <div className="text-xs text-muted">{run.model || 'sonnet'}</div>
                        <div className="text-xs text-muted">
                          {run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'Pending'}
                        </div>
                      </div>

                      {/* Large chart bar */}
                      <div className="flex-1 relative h-12 bg-surface-hover rounded-md">
                        <div
                          className={`
                            absolute h-full rounded-md flex items-center justify-between px-4 text-sm transition-colors overflow-hidden
                            ${AGENT_COLORS[run.agent_type]?.[run.status as keyof typeof AGENT_COLORS[string]] || 'bg-gray-500 text-white'}
                          `}
                          style={{
                            left: `${leftPercent}%`,
                            width: `${widthPercent}%`,
                            minWidth: '200px'
                          }}
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-semibold">
                              {formatDuration(runDuration)}
                            </span>
                            <span className="text-xs opacity-90 capitalize">
                              {run.status}
                            </span>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <div className="font-mono text-sm">
                              ${(run.cost_usd || 0).toFixed(4)}
                            </div>
                            <div className="font-mono text-xs opacity-90">
                              {(run.input_tokens || 0).toLocaleString()}/{(run.output_tokens || 0).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Time axis */}
              <div className="mt-6 pt-4 border-t border-border">
                <div className="relative h-6 ml-36">
                  {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
                    <div
                      key={fraction}
                      className="absolute bottom-0 text-xs text-muted font-mono"
                      style={{
                        left: `${fraction * 100}%`,
                        transform: fraction === 0 ? 'translateX(0%)' : fraction === 1 ? 'translateX(-100%)' : 'translateX(-50%)'
                      }}
                    >
                      {fraction === 0 ? '0s' : formatDuration(totalDuration * fraction)}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RunEntry({ run, onRerun }: { run: AgentRunResponse; onRerun: () => void }) {
  const [logs, setLogs] = useState<AgentLogEntry[]>([]);
  const lastLogIdRef = useRef(0);
  const isLive = run.status === "running" || run.status === "pending";

  useEffect(() => {
    lastLogIdRef.current = 0;
    setLogs([]);
    const load = async () => {
      try {
        const newLogs = await fetchRunLogs(run.id, lastLogIdRef.current);
        if (newLogs.length > 0) {
          setLogs((prev) => [...prev, ...newLogs]);
          lastLogIdRef.current = newLogs[newLogs.length - 1].id;
        }
      } catch {}
    };
    load();
    if (isLive) {
      const interval = setInterval(load, 2000);
      return () => clearInterval(interval);
    }
  }, [run.id, isLive]);

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
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium capitalize">{run.agent_type.replace("_", " ")} Agent</span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${RUN_STATUS_COLORS[run.status] || ""}`}>
              {run.status}
            </span>
          </div>
          {(run.status === "completed" || run.status === "failed") && (
            <button
              onClick={onRerun}
              className="flex items-center gap-1 text-[10px] text-muted hover:text-foreground transition-colors"
              title="Re-run this agent"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3 h-3">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
              Re-run
            </button>
          )}
        </div>
        <div className="text-xs text-muted mb-2">
          {run.started_at && `Started ${new Date(run.started_at).toLocaleString()}`}
          {run.finished_at && ` — Finished ${new Date(run.finished_at).toLocaleTimeString()}`}
        </div>
        <div className="text-xs text-muted mb-2 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.736 6.979C9.208 6.193 9.696 6 10 6s.792.193 1.264.979a1 1 0 001.715-1.029C12.279 4.784 11.232 4 10 4s-2.279.784-2.979 1.95c-.285.475-.507 1.043-.507 1.55 0 .502.169.926.507 1.4.338.473.841.8 1.429.8.588 0 1.091-.327 1.429-.8A1 1 0 0010.736 7.979C10.264 7.193 9.776 7 9.472 7s-.792.193-1.264.979a1 1 0 11-1.715-1.029C6.193 5.784 7.24 5 8.472 5s2.279.784 2.979 1.95z"/>
            </svg>
            <span className="font-mono">${(run.cost_usd || 0).toFixed(4)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <span className="font-mono text-xs">
              {(run.input_tokens || 0).toLocaleString()}→{(run.output_tokens || 0).toLocaleString()}
            </span>
          </div>
          {run.started_at && run.finished_at && (
            <div className="flex items-center gap-1.5">
              <svg className="w-3 h-3 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-mono text-xs">
                {formatDuration(new Date(run.finished_at).getTime() - new Date(run.started_at).getTime())}
              </span>
            </div>
          )}
        </div>

        {/* Live logs */}
        {logs.length > 0 && (
          <div className="rounded-md border border-border bg-background overflow-hidden">
            <div className="max-h-[500px] overflow-y-auto">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`px-3 py-1.5 border-b border-border last:border-0 text-xs font-mono ${
                    log.entry_type === "error" ? "bg-red-50 text-red-700" :
                    log.entry_type === "tool_use" ? "text-blue-700" :
                    log.entry_type === "tool_result" ? "text-gray-500 text-[10px] pl-6" :
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

function RepoSelector({ task, projectId, onRepoChanged }: { task: UnifiedTask; projectId?: number; onRepoChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [repos, setRepos] = useState<RepoEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [localRepo, setLocalRepo] = useState(task.repo || "");
  const [showFullName, setShowFullName] = useState(false);
  useEffect(() => {
    setLocalRepo(task.repo || "");
    setShowFullName(false); // Reset display when repo changes
  }, [task.repo]);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get the repo name (last part after final /)
  const getDisplayName = (repoPath: string) => {
    if (!repoPath) return "";
    const parts = repoPath.split("/");
    return parts[parts.length - 1];
  };

  const loadRepos = useCallback(async (q: string) => {
    if (!q.trim()) { setRepos([]); return; }
    setLoading(true);
    try {
      const data = await fetchRepos(q);
      setRepos(data);
    } catch {
      setRepos([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Close dropdown on click outside or escape key
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowFullName(false); // Reset to short name when closing
        setSearch(""); // Clear search when closing
        setRepos([]); // Clear repos list
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        setShowFullName(false);
        setSearch(""); // Clear search when closing
        setRepos([]); // Clear repos list
      }
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const handleSelect = async (repoName: string) => {
    setLocalRepo(repoName);
    setOpen(false);
    setShowFullName(false); // Reset to short name after selection
    setSearch(""); // Clear search after selection
    setRepos([]); // Clear repos list
    setSaving(true);
    try {
      await updateTaskRepo(task.external_ref, repoName, projectId);
      onRepoChanged();
    } catch {
      setLocalRepo(task.repo || ""); // revert on failure
    }
    setSaving(false);
  };

  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const handleSearch = (val: string) => {
    setSearch(val);
    clearTimeout(debounceRef.current);
    if (!val.trim()) { setRepos([]); setLoading(false); return; }
    setLoading(true);
    debounceRef.current = setTimeout(() => loadRepos(val), 300);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          if (!open) {
            setShowFullName(true);
            setSearch(localRepo || ""); // Pre-populate search with current repo
            clearTimeout(debounceRef.current); // Clear any pending searches
            if (localRepo) {
              loadRepos(localRepo); // Trigger search with current repo
            }
          }
          setOpen(!open);
          setTimeout(() => inputRef.current?.focus(), 50);
        }}
        className="w-full text-xs px-2 py-1.5 rounded-md border border-border bg-background hover:bg-surface-hover transition-colors font-mono flex items-center justify-between"
        title={localRepo && !saving ? localRepo : undefined}
      >
        <span className="truncate">
          {saving
            ? "Saving..."
            : localRepo
              ? (showFullName ? localRepo : getDisplayName(localRepo))
              : "Select repo..."
          }
        </span>
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3 ml-2 flex-shrink-0">
          <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="absolute top-full left-0 right-0 mt-1 rounded-md border border-border bg-surface shadow-lg z-10">
          <div className="p-2 border-b border-border">
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && search.trim()) {
                  handleSelect(search.trim());
                }
              }}
              placeholder="Search or type repo path..."
              className="w-full px-2 py-1.5 text-xs rounded border border-border bg-background placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent font-mono"
            />
          </div>
          <div className="max-h-48 overflow-y-auto">
            {!search.trim() ? (
              <div className="px-3 py-2 text-xs text-muted">Type to search repos...</div>
            ) : loading ? (
              <div className="px-3 py-2 text-xs text-muted">Searching...</div>
            ) : repos.length === 0 ? (
              <div className="px-3 py-2 text-xs text-muted">
                {search.trim() === localRepo ? (
                  <div className="flex items-start gap-2">
                    <svg className="w-3 h-3 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <div>
                      <div className="text-green-700 font-medium">Current repository</div>
                      <div className="font-mono text-xs text-muted mt-1 break-all">{search}</div>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => handleSelect(search.trim())}
                    className="hover:text-foreground transition-colors"
                  >
                    No repos found. Press Enter to use <span className="font-mono">{search}</span>
                  </button>
                )}
              </div>
            ) : (
              repos.map((r) => (
                <button
                  key={`${r.tracker_kind}:${r.full_name}`}
                  onClick={() => handleSelect(r.full_name)}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-surface-hover transition-colors flex items-center justify-between ${
                    localRepo === r.full_name ? "bg-accent/5 text-accent" : ""
                  }`}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    {localRepo === r.full_name && (
                      <svg className="w-3 h-3 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                    <span className="font-mono truncate">{r.full_name}</span>
                  </div>
                  <span className="text-[10px] text-muted ml-2 flex-shrink-0">{r.tracker_kind}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
