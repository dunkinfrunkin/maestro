"use client";

import { useDashboard } from "@/lib/dashboard-context";
import { SettingsPage } from "@/components/settings";

export default function Page() {
  const { activeWorkspace, setActiveWorkspace, reloadAll } = useDashboard();
  return (
    <SettingsPage
      activeWorkspace={activeWorkspace}
      onWorkspacesChanged={reloadAll}
      onWorkspaceSwitch={setActiveWorkspace}
    />
  );
}
