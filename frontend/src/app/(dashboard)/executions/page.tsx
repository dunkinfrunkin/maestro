"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { ExecutionsPage } from "@/components/executions";

export default function Page() {
  const { activeWorkspace } = useDashboard();
  return <ExecutionsPage workspaceId={activeWorkspace?.id} />;
}
