"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { TasksPage } from "@/components/tasks";

export default function Page() {
  const { activeWorkspace, activeProject } = useDashboard();
  return <TasksPage workspaceId={activeWorkspace?.id} projectId={activeProject?.id} />;
}
