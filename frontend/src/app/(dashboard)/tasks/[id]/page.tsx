"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { UnifiedTask, fetchTaskById } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";
import { TaskDetailPage } from "@/components/task-detail";

export default function Page() {
  const params = useParams();
  const router = useRouter();
  const { activeWorkspace, activeProject } = useDashboard();
  const [task, setTask] = useState<UnifiedTask | null>(null);

  useEffect(() => {
    const id = Number(params.id);
    if (!isNaN(id)) {
      fetchTaskById(id)
        .then(setTask)
        .catch(() => router.push("/tasks"));
    }
  }, [params.id, router]);

  if (!task) {
    return <div className="text-sm text-muted">Loading task...</div>;
  }

  return (
    <TaskDetailPage
      task={task}
      workspaceId={activeWorkspace?.id}
      projectId={activeProject?.id}
      onBack={() => router.push("/tasks")}
      onTaskUpdated={() =>
        fetchTaskById(Number(params.id))
          .then(setTask)
          .catch(() => {})
      }
    />
  );
}
