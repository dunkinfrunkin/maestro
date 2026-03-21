"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { UnifiedTask, fetchTaskById, fetchTaskDetail } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";
import { TaskDetailPage } from "@/components/task-detail";

export default function Page() {
  const params = useParams();
  const router = useRouter();
  const { activeWorkspace, activeProject } = useDashboard();
  const [task, setTask] = useState<UnifiedTask | null>(null);

  const loadTask = () => {
    const idStr = params.id as string;
    const id = Number(idStr);
    if (!isNaN(id) && id > 0) {
      // Numeric ID — fetch by pipeline ID
      return fetchTaskById(id).then(setTask);
    } else {
      // External ref (e.g., github:3:15)
      return fetchTaskDetail(decodeURIComponent(idStr)).then(setTask);
    }
  };

  useEffect(() => {
    loadTask().catch(() => router.push("/tasks"));
  }, [params.id]);

  if (!task) {
    return <div className="text-sm text-muted">Loading task...</div>;
  }

  return (
    <TaskDetailPage
      task={task}
      workspaceId={activeWorkspace?.id}
      projectId={activeProject?.id}
      onBack={() => router.push("/tasks")}
      onTaskUpdated={() => loadTask().catch(() => {})}
    />
  );
}
