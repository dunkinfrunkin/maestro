"use client";

import { useParams, useRouter } from "next/navigation";
import { useDashboard } from "@/lib/dashboard-context";
import { AgentDetailPage } from "@/components/agent-detail";
import { AGENTS } from "@/lib/agents";

export default function Page() {
  const params = useParams();
  const router = useRouter();
  const { activeWorkspace } = useDashboard();
  const agent = AGENTS.find((a) => a.type === params.type);

  if (!agent) {
    router.push("/agents");
    return null;
  }

  if (!activeWorkspace) return null;

  return (
    <AgentDetailPage
      agent={agent}
      workspaceId={activeWorkspace.id}
      onBack={() => router.push("/agents")}
    />
  );
}
