"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  PIPELINE_STATUSES,
  StatusInfo,
  UnifiedTask,
  fetchStatuses,
  fetchTasks,
  updateTaskStatus,
  removeTaskStatus,
  TrackerConnection,
  fetchConnections,
} from "@/lib/api";

const COLOR_MAP: Record<string, string> = {
  gray: "bg-gray-200 text-gray-800 border-gray-300",
  blue: "bg-blue-100 text-blue-800 border-blue-300",
  purple: "bg-purple-100 text-purple-800 border-purple-300",
  teal: "bg-teal-100 text-teal-800 border-teal-300",
  yellow: "bg-yellow-100 text-yellow-800 border-yellow-300",
  orange: "bg-orange-100 text-orange-800 border-orange-300",
  green: "bg-green-100 text-green-800 border-green-300",
  red: "bg-red-100 text-red-800 border-red-300",
};

export function TasksPage({ workspaceId, projectId }: { workspaceId?: number; projectId?: number }) {
  const router = useRouter();
  const [statuses, setStatuses] = useState<StatusInfo[]>([]);
  const [tasks, setTasks] = useState<UnifiedTask[]>([]);
  const [total, setTotal] = useState(0);
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [search, setSearch] = useState("");
  const [filterConnection, setFilterConnection] = useState<number | undefined>();
  const [filterPipeline, setFilterPipeline] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const loadTasks = useCallback(async (p = page) => {
    try {
      setLoading(true);
      const data = await fetchTasks({
        connection_id: filterConnection,
        search: search || undefined,
        pipeline_status: filterPipeline || undefined,
        offset: p * pageSize,
        limit: pageSize,
      });
      setTasks(data.tasks);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [search, filterConnection, filterPipeline, page]);

  useEffect(() => {
    fetchConnections().then(setConnections).catch(() => {});
    fetchStatuses().then(setStatuses).catch(() => {});
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleStatusChange = async (task: UnifiedTask, status: string) => {
    try {
      if (status === "") {
        await removeTaskStatus(task.external_ref);
      } else {
        const repo = task.repo || (task.identifier.includes("#") ? task.identifier.split("#")[0] : "");
        if (!repo) {
          setError("A repository must be set before changing pipeline status. Open the task and set a repository first.");
          return;
        }
        await updateTaskStatus(task.external_ref, status, {
          workspace_id: workspaceId,
          project_id: projectId,
          repo,
          issue_title: task.title,
          issue_description: task.description || "",
          issue_url: task.url || "",
        });
      }
      await loadTasks();
    } catch {
      await loadTasks();
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search tasks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { setPage(0); loadTasks(0); } }}
          className="flex-1 min-w-[200px] px-3 py-2 text-sm rounded-md border border-border bg-surface placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <select
          value={filterConnection ?? ""}
          onChange={(e) => {
            setFilterConnection(e.target.value ? Number(e.target.value) : undefined);
            setPage(0);
          }}
          className="px-3 py-2 text-sm rounded-md border border-border bg-surface text-foreground"
        >
          <option value="">All connections</option>
          {connections.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} ({c.kind})
            </option>
          ))}
        </select>
        <select
          value={filterPipeline}
          onChange={(e) => { setFilterPipeline(e.target.value); setPage(0); }}
          className="px-3 py-2 text-sm rounded-md border border-border bg-surface text-foreground"
        >
          <option value="">All statuses</option>
          <option value="none">No status</option>
          {statuses.filter(s => s.active).map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <button
          onClick={() => { setPage(0); loadTasks(0); }}
          className="px-3 py-2 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors"
        >
          Search
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
          {error}
        </div>
      )}

      {/* Tasks list */}
      {loading ? (
        <div className="text-sm text-muted">Loading tasks...</div>
      ) : tasks.length === 0 ? (
        <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
          {connections.length === 0
            ? "No tracker connections configured. Add one in Settings."
            : "No tasks found"}
        </div>
      ) : (
        <>
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskCard
                key={task.external_ref}
                task={task}
                onStatusChange={handleStatusChange}
                onClick={() => router.push(task.id ? `/tasks/${task.id}` : `/tasks/${encodeURIComponent(task.external_ref)}`)}
              />
            ))}
          </div>
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-muted">
                {page * pageSize + 1}–{Math.min((page + 1) * pageSize, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 0}
                  onClick={() => setPage(page - 1)}
                  className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage(page + 1)}
                  className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function TaskCard({
  task,
  onStatusChange,
  onClick,
}: {
  task: UnifiedTask;
  onStatusChange: (task: UnifiedTask, status: string) => void;
  onClick: () => void;
}) {
  return (
    <div
      className="rounded-lg border border-border bg-surface p-4 cursor-pointer hover:bg-surface-hover transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted">{task.identifier}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-muted">{task.tracker_kind}</span>
            <span className="text-xs text-muted">{task.state}</span>
          </div>
          <div className="font-medium text-sm">{task.title}</div>
          {task.labels.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {task.labels.map((label) => (
                <span key={label} className="text-xs px-1.5 py-0.5 rounded-full bg-surface-hover text-muted">{label}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          {task.pipeline_status ? (
            <>
              <span className={`text-xs px-2 py-1 rounded-full border ${COLOR_MAP[statuses.find(s => s.value === task.pipeline_status)?.color || "gray"] || COLOR_MAP.gray}`}>
                {statuses.find(s => s.value === task.pipeline_status)?.label || task.pipeline_status}
              </span>
              <select
                value={task.pipeline_status}
                onChange={(e) => onStatusChange(task, e.target.value)}
                className="text-xs px-2 py-1 rounded-md border border-border bg-surface text-foreground"
              >
                {statuses.filter(s => s.active).map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
                <option value="">Remove</option>
              </select>
            </>
          ) : (
            <select
              value=""
              onChange={(e) => onStatusChange(task, e.target.value)}
              className="text-xs px-2 py-1 rounded-md border border-border bg-surface text-muted"
            >
              <option value="" disabled>Set status...</option>
              {statuses.filter(s => s.active).map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          )}
        </div>
      </div>
    </div>
  );
}
