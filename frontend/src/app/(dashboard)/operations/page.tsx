"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { CentcomPage } from "@/components/centcom";

export default function Page() {
  const { activeWorkspace } = useDashboard();
  return <CentcomPage workspaceId={activeWorkspace?.id} />;
}
