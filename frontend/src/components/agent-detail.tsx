"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AgentConfigResponse,
  getAgentConfig,
  updateAgentConfig,
} from "@/lib/api";

type Tab = "config" | "prompt";

// Agent system prompts (read-only display for now)
const AGENT_PROMPTS: Record<string, string> = {
  implementation: `You are an implementation agent. Your job is to:
1. Read the issue requirements
2. Read the relevant code
3. Implement the changes
4. Write/update tests
5. Create a branch, commit, push, and open a PR

On follow-up runs, checkout the PR branch, read ALL review comments, address EVERY one, and push fixes.`,

  review: `You are a senior code reviewer. Your job is to:
1. Checkout the PR branch
2. Read the changed files with the Read tool
3. Identify issues with exact file paths and line numbers
4. Post inline review comments via gh api
5. Output REVIEW_VERDICT: APPROVE or REQUEST_CHANGES`,

  risk_profile: `You assess PRs for deployment risk across 7 dimensions:
Change Scope, Blast Radius, Complexity, Reversibility, Test Coverage, Security Surface, Dependency Changes.

Score each 1-5, compute overall risk level (LOW/MEDIUM/HIGH/CRITICAL).
Post risk assessment as PR comment. Auto-approve if LOW.`,

  deployment: `You handle PR deployment:
1. Verify CI checks passing
2. Merge PR with squash merge
3. Monitor deployment pipeline
4. Report status updates`,

  monitor: `You verify deployment health:
1. Check GitHub Actions status
2. Look for error spikes in logs
3. Check response times and metrics
4. Classify issues by severity (P0-P3)
5. Recommend rollback if P0`,
};

interface AgentDef {
  type: string;
  name: string;
  description: string;
}

export function AgentDetailPage({
  agent,
  workspaceId,
  onBack,
}: {
  agent: AgentDef;
  workspaceId: number;
  onBack: () => void;
}) {
  const [tab, setTab] = useState<Tab>("config");
  const [config, setConfig] = useState<AgentConfigResponse | null>(null);
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
    <div className="max-w-2xl">
      {/* Back */}
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-muted hover:text-foreground mb-4 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
        Back to agents
      </button>

      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold">{agent.name}</h2>
        <p className="text-sm text-muted">{agent.description}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border">
        {([
          { id: "config" as Tab, label: "Configuration" },
          { id: "prompt" as Tab, label: "Prompt" },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm -mb-px transition-colors ${
              tab === t.id
                ? "border-b-2 border-accent text-foreground font-medium"
                : "text-muted hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{error}</div>
      )}

      {/* Config tab */}
      {tab === "config" && (
        <div className="space-y-6">
          {/* Model */}
          <div>
            <div className="text-sm font-medium mb-2">Model</div>
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
                    name="model"
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

          {/* Agent-specific config */}
          {agent.type === "risk_profile" && (
            <div>
              <div className="text-sm font-medium mb-2">Auto-approve threshold</div>
              <div className="text-xs text-muted mb-2">
                PRs at or below this risk level will be auto-approved.
              </div>
              <select
                value={(config?.extra_config?.auto_approve_threshold as string) || "low"}
                onChange={(e) => handleExtraConfigChange("auto_approve_threshold", e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground"
              >
                <option value="low">Low — only auto-approve minimal risk</option>
                <option value="medium">Medium — auto-approve low and medium risk</option>
                <option value="high">High — auto-approve most PRs (not recommended)</option>
              </select>
            </div>
          )}

          {/* Enable/Disable */}
          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <div className="text-sm font-medium">Enabled</div>
              <div className="text-xs text-muted">Agent will be triggered when tasks move to this pipeline stage</div>
            </div>
            <button
              onClick={() => handleExtraConfigChange("enabled", !(config?.extra_config?.enabled ?? true))}
              className={`relative w-9 h-5 rounded-full transition-colors ${(config?.extra_config?.enabled ?? true) ? "bg-green-500" : "bg-gray-300"}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${(config?.extra_config?.enabled ?? true) ? "translate-x-4" : ""}`} />
            </button>
          </div>
        </div>
      )}

      {/* Prompt tab */}
      {tab === "prompt" && (
        <div>
          <div className="text-sm font-medium mb-2">System Prompt</div>
          <div className="text-xs text-muted mb-3">
            This prompt is sent to Claude Code CLI when the agent runs.
          </div>
          <div className="rounded-md border border-border bg-background p-4 font-mono text-xs whitespace-pre-wrap text-foreground leading-relaxed">
            {AGENT_PROMPTS[agent.type] || "No prompt configured."}
          </div>
        </div>
      )}
    </div>
  );
}
