"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AgentConfigResponse,
  ApiKeyStatus,
  getAgentConfig,
  getApiKeyStatus,
} from "@/lib/api";
import { AGENTS } from "@/lib/agents";

export function AgentsPage({ workspaceId }: { workspaceId: number }) {
  const router = useRouter();
  const [keyStatus, setKeyStatus] = useState<ApiKeyStatus | null>(null);
  const [configs, setConfigs] = useState<Record<string, AgentConfigResponse>>({});

  useEffect(() => {
    getApiKeyStatus(workspaceId, "anthropic").then(setKeyStatus).catch(() => {});
    // Load all agent configs for the list view
    AGENTS.forEach((a) => {
      getAgentConfig(workspaceId, a.type).then((c) => {
        setConfigs((prev) => ({ ...prev, [a.type]: c }));
      }).catch(() => {});
    });
  }, [workspaceId]);

  const isActive = keyStatus?.has_key ?? false;

  return (
    <div className="max-w-2xl space-y-4">
      {!isActive && (
        <div className="text-xs text-muted rounded-md border border-border border-dashed p-3">
          Add your Anthropic API key in <strong>Settings &rarr; API Keys</strong> to activate agents.
        </div>
      )}
      {AGENTS.map((agent) => {
        const config = configs[agent.type];
        const enabled = (config?.extra_config?.enabled ?? true) as boolean;
        const model = config?.model || "sonnet";
        const modelName = config?.available_models?.find((m) => m.id === model)?.name || model;

        return (
          <div
            key={agent.type}
            onClick={() => router.push(`/agents/${agent.type}`)}
            className={`rounded-lg border border-border bg-surface p-4 cursor-pointer hover:bg-surface-hover transition-colors ${!enabled ? "opacity-60" : ""}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive && enabled ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-500"}`}>
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d={agent.icon} />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium">{agent.name}</div>
                  <div className="text-xs text-muted">{agent.description}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-muted">{modelName}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-muted">
                  on {agent.triggerStatus}
                </span>
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-muted">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
