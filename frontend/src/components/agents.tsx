"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AgentConfigResponse,
  ApiKeyStatus,
  getAgentConfig,
  getApiKeyStatus,
  updateAgentConfig,
} from "@/lib/api";

export function AgentsPage({ workspaceId }: { workspaceId: number }) {
  return (
    <div className="max-w-2xl space-y-6">
      <ImplementationAgent workspaceId={workspaceId} />
    </div>
  );
}

function ImplementationAgent({ workspaceId }: { workspaceId: number }) {
  const [config, setConfig] = useState<AgentConfigResponse | null>(null);
  const [keyStatus, setKeyStatus] = useState<ApiKeyStatus | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [cfg, ks] = await Promise.all([
        getAgentConfig(workspaceId, "implementation"),
        getApiKeyStatus(workspaceId, "anthropic"),
      ]);
      setConfig(cfg);
      setKeyStatus(ks);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }, [workspaceId]);

  useEffect(() => { load(); }, [load]);

  const handleModelChange = async (model: string) => {
    try {
      const updated = await updateAgentConfig(workspaceId, "implementation", model);
      setConfig(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  const isActive = keyStatus?.has_key ?? false;

  return (
    <div className="rounded-lg border border-border bg-surface overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive ? "bg-green-100 text-green-700" : "bg-gray-200 text-gray-500"}`}>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
            </svg>
          </div>
          <div>
            <div className="text-sm font-medium">Implementation Agent</div>
            <div className="text-xs text-muted">Reads issues, writes code, creates PRs</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${
            isActive
              ? "bg-green-100 text-green-700 border-green-300"
              : "bg-gray-100 text-gray-500 border-gray-300"
          }`}>
            {isActive ? "Active" : "Inactive"}
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
            className={`w-4 h-4 text-muted transition-transform ${expanded ? "rotate-90" : ""}`}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </button>

      {/* Expanded config */}
      {expanded && (
        <div className="border-t border-border p-4 space-y-5">
          {error && (
            <div className="p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">
              {error}
            </div>
          )}

          {/* Status hint */}
          {!isActive && (
            <div className="text-xs text-muted rounded-md border border-border border-dashed p-3">
              Add your Anthropic API key in <strong>Settings &rarr; API Keys</strong> to activate this agent.
            </div>
          )}

          {/* Model Selection */}
          <div>
            <div className="text-xs font-medium mb-2">Model</div>
            <div className="space-y-1.5">
              {(config?.available_models || []).map((m) => (
                <label
                  key={m.id}
                  className={`flex items-center gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-colors ${
                    config?.model === m.id
                      ? "border-accent bg-accent/5"
                      : "border-border hover:bg-surface-hover"
                  }`}
                >
                  <input
                    type="radio"
                    name="model"
                    checked={config?.model === m.id}
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
        </div>
      )}
    </div>
  );
}
