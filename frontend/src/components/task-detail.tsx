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

  // Extract repo from identifier (e.g., "owner/repo#123" → "owner/repo")
  const repo = task.identifier.includes("#")
    ? task.identifier.split("#")[0]
    : "";

  const handleStatusChange = async (status: string) => {
    try {
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

        {/* PR link */}
        {task.pr_url && (
          <div className="mt-3 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-muted">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
            </svg>
            <a
              href={task.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent hover:underline font-mono"
            >
              {task.pr_url}
            </a>
          </div>
        )}

        {/* Repo selector */}
        <RepoSelector task={task} onRepoChanged={onTaskUpdated} />

        {/* Status selector + re-run */}
        <div className="mt-4 flex items-center gap-3">
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
          {task.pipeline_status && task.pipeline_status !== "queued" && (
            <button
              onClick={() => handleStatusChange(task.pipeline_status!)}
              className="flex items-center gap-1 text-xs px-2 py-1 rounded-md border border-border hover:bg-surface-hover transition-colors text-muted hover:text-foreground"
              title="Re-run the current stage agent"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-3.5 h-3.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
              </svg>
              Re-run
            </button>
          )}
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

function RepoSelector({ task, onRepoChanged }: { task: UnifiedTask; onRepoChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [repos, setRepos] = useState<RepoEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // Close dropdown on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleSelect = async (repoName: string) => {
    setSaving(true);
    try {
      await updateTaskRepo(task.external_ref, repoName);
      onRepoChanged();
    } catch {}
    setSaving(false);
    setOpen(false);
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
    <div className="mt-3" ref={dropdownRef}>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted">Repository:</span>
        <button
          onClick={() => { setOpen(!open); setTimeout(() => inputRef.current?.focus(), 50); }}
          className="text-xs px-2 py-1 rounded-md border border-border bg-background hover:bg-surface-hover transition-colors font-mono flex items-center gap-1.5"
        >
          {saving ? "Saving..." : task.repo || "Select repo..."}
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
      </div>

      {open && (
        <div className="mt-1 w-full max-w-md rounded-md border border-border bg-surface shadow-lg z-10 relative">
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
                <button
                  onClick={() => handleSelect(search.trim())}
                  className="hover:text-foreground transition-colors"
                >
                  No repos found. Press Enter to use <span className="font-mono">{search}</span>
                </button>
              </div>
            ) : (
              repos.map((r) => (
                <button
                  key={`${r.tracker_kind}:${r.full_name}`}
                  onClick={() => handleSelect(r.full_name)}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-surface-hover transition-colors flex items-center justify-between ${
                    task.repo === r.full_name ? "bg-accent/5 text-accent" : ""
                  }`}
                >
                  <span className="font-mono truncate">{r.full_name}</span>
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
