"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AgentConfigResponse,
  ApiKeyStatus,
  getAgentConfig,
  getApiKeyStatus,
  updateAgentConfig,
} from "@/lib/api";
import { AgentDetailPage } from "@/components/agent-detail";

interface AgentDef {
  type: string;
  name: string;
  description: string;
  icon: string;
  triggerStatus: string;
}

const AGENTS: AgentDef[] = [
  {
    type: "implementation",
    name: "Implementation Agent",
    description: "Reads issues, writes code, creates PRs",
    icon: "M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z",
    triggerStatus: "implement",
  },
  {
    type: "review",
    name: "Review Agent",
    description: "Thorough PR review — code quality, correctness, tests, security",
    icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z",
    triggerStatus: "review",
  },
  {
    type: "risk_profile",
    name: "Risk Profile Agent",
    description: "Scores PR risk — auto-approves low risk, escalates medium/high to humans",
    icon: "M12 9v3.75m0-10.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.25-8.25-3.286Zm0 13.036h.008v.008H12v-.008Z",
    triggerStatus: "risk_profile",
  },
  {
    type: "deployment",
    name: "Deployment Agent",
    description: "Merges PR, monitors CI/CD pipeline, posts status updates",
    icon: "M15.59 14.37a6 6 0 0 1-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 0 0 6.16-12.12A14.98 14.98 0 0 0 9.631 8.41m5.96 5.96a14.926 14.926 0 0 1-5.841 2.58m-.119-8.54a6 6 0 0 0-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 0 0-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 0 1-2.448-2.448 14.9 14.9 0 0 1 .06-.312m-2.24 2.39a4.493 4.493 0 0 0-1.757 4.306 4.493 4.493 0 0 0 4.306-1.758M16.5 9a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z",
    triggerStatus: "deploy",
  },
  {
    type: "monitor",
    name: "Monitor Agent",
    description: "Checks logs, metrics, and alerts post-deployment",
    icon: "M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6",
    triggerStatus: "monitor",
  },
];

export function AgentsPage({ workspaceId }: { workspaceId: number }) {
  const [selectedAgent, setSelectedAgent] = useState<AgentDef | null>(null);
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

  if (selectedAgent) {
    return (
      <AgentDetailPage
        agent={selectedAgent}
        workspaceId={workspaceId}
        onBack={() => setSelectedAgent(null)}
      />
    );
  }

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
        const model = config?.model || "claude-sonnet-4-6";
        const modelName = config?.available_models?.find((m) => m.id === model)?.name || model;

        return (
          <div
            key={agent.type}
            onClick={() => setSelectedAgent(agent)}
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
