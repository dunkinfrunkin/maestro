"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AgentConfigResponse,
  ApiKeyStatus,
  getAgentConfig,
  getApiKeyStatus,
  updateAgentConfig,
} from "@/lib/api";

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
  const [keyStatus, setKeyStatus] = useState<ApiKeyStatus | null>(null);

  useEffect(() => {
    getApiKeyStatus(workspaceId, "anthropic").then(setKeyStatus).catch(() => {});
  }, [workspaceId]);

  const isActive = keyStatus?.has_key ?? false;

  return (
    <div className="max-w-2xl space-y-4">
      {!isActive && (
        <div className="text-xs text-muted rounded-md border border-border border-dashed p-3">
          Add your Anthropic API key in <strong>Settings &rarr; API Keys</strong> to activate agents.
        </div>
      )}
      {AGENTS.map((agent) => (
        <AgentCard key={agent.type} agent={agent} workspaceId={workspaceId} isActive={isActive} />
      ))}
    </div>
  );
}

function AgentCard({ agent, workspaceId, isActive }: { agent: AgentDef; workspaceId: number; isActive: boolean }) {
  const [config, setConfig] = useState<AgentConfigResponse | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setConfig(await getAgentConfig(workspaceId, agent.type));
      setError(null);
    } catch {
      setConfig(null);
    }
  }, [workspaceId, agent.type]);

  useEffect(() => { load(); }, [load]);

  const handleModelChange = async (model: string) => {
    try {
      const updated = await updateAgentConfig(workspaceId, agent.type, model);
      setConfig(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  const handleExtraConfigChange = async (key: string, value: unknown) => {
    try {
      const extra = { ...(config?.extra_config || {}), [key]: value };
      const updated = await updateAgentConfig(workspaceId, agent.type, undefined, extra);
      setConfig(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-500"}`}>
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
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-hover text-muted">
            on {agent.triggerStatus}
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
            className={`w-4 h-4 text-muted transition-transform ${expanded ? "rotate-90" : ""}`}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border p-4 space-y-4">
          {error && (
            <div className="p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{error}</div>
          )}

          <div>
            <div className="text-xs font-medium mb-2">Model</div>
            <div className="space-y-1.5">
              {(config?.available_models || [
                { id: "claude-sonnet-4-6", name: "Claude Sonnet 4.6", description: "Best speed/intelligence balance" },
                { id: "claude-opus-4-6", name: "Claude Opus 4.6", description: "Most capable, best for complex tasks" },
                { id: "claude-haiku-4-5-20251001", name: "Claude Haiku 4.5", description: "Fastest, good for simple tasks" },
              ]).map((m) => (
                <label
                  key={m.id}
                  className={`flex items-center gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-colors ${
                    (config?.model || "claude-sonnet-4-6") === m.id
                      ? "border-accent bg-accent/5"
                      : "border-border hover:bg-surface-hover"
                  }`}
                >
                  <input
                    type="radio"
                    name={`model-${agent.type}`}
                    checked={(config?.model || "claude-sonnet-4-6") === m.id}
                    onChange={() => handleModelChange(m.id)}
                    className="accent-accent"
                  />
                  <div>
                    <div className="text-xs font-medium">{m.name}</div>
                    <div className="text-[10px] text-muted">{m.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {agent.type === "risk_profile" && (
            <div>
              <div className="text-xs font-medium mb-2">Auto-approve threshold</div>
              <div className="text-[10px] text-muted mb-2">
                PRs at or below this risk level will be auto-approved.
              </div>
              <select
                value={(config?.extra_config?.auto_approve_threshold as string) || "low"}
                onChange={(e) => handleExtraConfigChange("auto_approve_threshold", e.target.value)}
                className="w-full px-3 py-2 text-xs rounded-md border border-border bg-background text-foreground"
              >
                <option value="low">Low — only auto-approve minimal risk</option>
                <option value="medium">Medium — auto-approve low and medium risk</option>
                <option value="high">High — auto-approve most PRs (not recommended)</option>
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
