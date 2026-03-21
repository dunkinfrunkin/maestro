"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { AgentsPage } from "@/components/agents";

export default function Page() {
  const { activeWorkspace } = useDashboard();
  if (!activeWorkspace) return null;
  return <AgentsPage workspaceId={activeWorkspace.id} />;
}
