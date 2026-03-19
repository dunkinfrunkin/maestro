"use client";

import { useCallback, useEffect, useState } from "react";
import {
  PIPELINE_STATUSES,
  PipelineStatus,
  UnifiedTask,
  fetchTasks,
  updateTaskStatus,
  removeTaskStatus,
  TrackerConnection,
  fetchConnections,
} from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  implement: "Implement",
  review: "Review",
  risk_profile: "Risk Profile",
  deploy: "Deploy",
  monitor: "Monitor",
};

const STATUS_COLORS: Record<string, string> = {
  queued: "bg-gray-200 text-gray-800 border-gray-300",
  implement: "bg-blue-100 text-blue-800 border-blue-300",
  review: "bg-purple-100 text-purple-800 border-purple-300",
  risk_profile: "bg-orange-100 text-orange-800 border-orange-300",
  deploy: "bg-yellow-100 text-yellow-800 border-yellow-300",
  monitor: "bg-green-100 text-green-800 border-green-300",
};

export function TasksPage({ workspaceId, projectId }: { workspaceId?: number; projectId?: number }) {
  const [tasks, setTasks] = useState<UnifiedTask[]>([]);
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [search, setSearch] = useState("");
  const [filterConnection, setFilterConnection] = useState<number | undefined>();
  const [filterPipeline, setFilterPipeline] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchTasks({
        connection_id: filterConnection,
        search: search || undefined,
        pipeline_status: filterPipeline || undefined,
      });
      setTasks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [search, filterConnection, filterPipeline]);

  useEffect(() => {
    fetchConnections().then(setConnections).catch(() => {});
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleStatusChange = async (task: UnifiedTask, status: string) => {
    try {
      if (status === "") {
        await removeTaskStatus(task.external_ref);
      } else {
        await updateTaskStatus(task.external_ref, status, {
          workspace_id: workspaceId,
          project_id: projectId,
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

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search tasks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && loadTasks()}
          className="flex-1 min-w-[200px] px-3 py-2 text-sm rounded-md border border-border bg-surface placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <select
          value={filterConnection ?? ""}
          onChange={(e) =>
            setFilterConnection(e.target.value ? Number(e.target.value) : undefined)
          }
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
          onChange={(e) => setFilterPipeline(e.target.value)}
          className="px-3 py-2 text-sm rounded-md border border-border bg-surface text-foreground"
        >
          <option value="">All statuses</option>
          <option value="none">No status</option>
          {PIPELINE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <button
          onClick={loadTasks}
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
        <div className="space-y-2">
          {tasks.map((task) => (
            <TaskCard
              key={task.external_ref}
              task={task}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TaskCard({
  task,
  onStatusChange,
}: {
  task: UnifiedTask;
  onStatusChange: (task: UnifiedTask, status: string) => void;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-muted">{task.identifier}</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-muted">
              {task.tracker_kind}
            </span>
            <span className="text-xs text-muted">{task.state}</span>
          </div>
          <div className="font-medium text-sm mb-1">
            {task.url ? (
              <a
                href={task.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline"
              >
                {task.title}
              </a>
            ) : (
              task.title
            )}
          </div>
          {task.labels.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {task.labels.map((label) => (
                <span
                  key={label}
                  className="text-xs px-1.5 py-0.5 rounded-full bg-surface-hover text-muted"
                >
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Pipeline status selector */}
        <div className="flex-shrink-0">
          {task.pipeline_status ? (
            <div className="flex items-center gap-2">
              <span
                className={`text-xs px-2 py-1 rounded-full border ${
                  STATUS_COLORS[task.pipeline_status] || "bg-gray-200 text-gray-800 border-gray-300"
                }`}
              >
                {STATUS_LABELS[task.pipeline_status] || task.pipeline_status}
              </span>
              <select
                value={task.pipeline_status}
                onChange={(e) => onStatusChange(task, e.target.value)}
                className="text-xs px-2 py-1 rounded-md border border-border bg-surface text-foreground"
              >
                {PIPELINE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
                <option value="">Remove status</option>
              </select>
            </div>
          ) : (
            <select
              value=""
              onChange={(e) => onStatusChange(task, e.target.value)}
              className="text-xs px-2 py-1 rounded-md border border-border bg-surface text-muted"
            >
              <option value="" disabled>
                Set status...
              </option>
              {PIPELINE_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
    </div>
  );
}
