"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { OperationsPage } from "@/components/operations";

export default function Page() {
  const { orchState, activeWorkspace } = useDashboard();
  return <OperationsPage state={orchState} workspaceId={activeWorkspace?.id} />;
}
