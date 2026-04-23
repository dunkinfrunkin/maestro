"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import {
  AgentConfigResponse,
  getAgentConfig,
  getDefaultPrompt,
  updateAgentConfig,
} from "@/lib/api";
import { AgentDef } from "@/lib/agents";

const CodeMirrorEditor = dynamic(
  () => import("@uiw/react-codemirror"),
  { ssr: false, loading: () => <div className="text-sm text-muted p-4">Loading editor...</div> }
);

type Tab = "config" | "prompt";

interface ConfigDraft {
  provider: string;
  model: string;
  enabled: boolean;
  autoApproveThreshold: string;
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
  const [draft, setDraft] = useState<ConfigDraft | null>(null);
  const [defaultPrompt, setDefaultPrompt] = useState("");
  const [promptDraft, setPromptDraft] = useState("");
  const [promptDirty, setPromptDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const buildDraft = (cfg: AgentConfigResponse): ConfigDraft => ({
    provider: cfg.provider || "anthropic",
    model: cfg.model || "sonnet",
    enabled: (cfg.extra_config?.enabled as boolean) ?? true,
    autoApproveThreshold: (cfg.extra_config?.auto_approve_threshold as string) || "low",
  });

  const load = useCallback(async () => {
    try {
      const [cfg, dp] = await Promise.all([
        getAgentConfig(workspaceId, agent.type),
        getDefaultPrompt(agent.type),
      ]);
      setConfig(cfg);
      setDraft(buildDraft(cfg));
      setDefaultPrompt(dp);
      const currentPrompt = (cfg.extra_config?.custom_prompt as string) || dp;
      setPromptDraft(currentPrompt);
      setPromptDirty(false);
      setError(null);
    } catch {
      setConfig(null);
    }
  }, [workspaceId, agent.type]);

  useEffect(() => { load(); }, [load]);

  // Check if draft differs from saved config
  const configDirty = config && draft ? (
    draft.provider !== (config.provider || "anthropic") ||
    draft.model !== (config.model || "sonnet") ||
    draft.enabled !== ((config.extra_config?.enabled as boolean) ?? true) ||
    draft.autoApproveThreshold !== ((config.extra_config?.auto_approve_threshold as string) || "low")
  ) : false;

  // Get available models for current draft provider
  const availableModels = config?.providers?.find(p => p.id === draft?.provider)?.models
    || config?.available_models
    || [];

  const handleSaveConfig = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const extra = {
        ...(config?.extra_config || {}),
        enabled: draft.enabled,
        auto_approve_threshold: draft.autoApproveThreshold,
      };
      const updated = await updateAgentConfig(workspaceId, agent.type, draft.provider, draft.model, extra);
      setConfig(updated);
      setDraft(buildDraft(updated));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleSavePrompt = async () => {
    setSaving(true);
    try {
      const extra = { ...(config?.extra_config || {}), custom_prompt: promptDraft };
      const updated = await updateAgentConfig(workspaceId, agent.type, config?.provider, undefined, extra);
      setConfig(updated);
      setPromptDirty(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleResetPrompt = () => {
    setPromptDraft(defaultPrompt);
    setPromptDirty(true);
  };

  const isUsingDefault = !config?.extra_config?.custom_prompt;

  return (
    <div className="max-w-4xl">
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
            {t.id === "config" && configDirty && (
              <span className="ml-1 w-1.5 h-1.5 rounded-full bg-accent inline-block" />
            )}
            {t.id === "prompt" && promptDirty && (
              <span className="ml-1 w-1.5 h-1.5 rounded-full bg-accent inline-block" />
            )}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-2 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{error}</div>
      )}

      {/* Config tab */}
      {tab === "config" && draft && (
        <div className="space-y-6">
          {/* Provider selector */}
          {config?.providers && config.providers.length > 1 && (
            <div>
              <div className="text-sm font-medium mb-2">Provider</div>
              <div className="flex gap-2">
                {config.providers.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      const defaultModel = p.models?.[0]?.id || "sonnet";
                      setDraft({ ...draft, provider: p.id, model: defaultModel });
                    }}
                    className={`flex-1 rounded-md border px-3 py-2.5 text-center transition-colors ${
                      draft.provider === p.id
                        ? "border-accent bg-accent/5 font-medium"
                        : "border-border hover:bg-surface-hover"
                    }`}
                  >
                    <div className="text-xs font-medium">{p.name}</div>
                    <div className="text-[10px] text-muted">{p.id === "anthropic" ? "Claude CLI" : "Codex CLI"}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="text-sm font-medium mb-2">Model</div>
            <div className="space-y-1.5">
              {availableModels.map((m) => (
                <label
                  key={m.id}
                  className={`flex items-center gap-3 rounded-md border px-3 py-2.5 cursor-pointer transition-colors ${
                    draft.model === m.id
                      ? "border-accent bg-accent/5"
                      : "border-border hover:bg-surface-hover"
                  }`}
                >
                  <input
                    type="radio"
                    name="model"
                    checked={draft.model === m.id}
                    onChange={() => setDraft({ ...draft, model: m.id })}
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
              <div className="text-sm font-medium mb-2">Auto-approve threshold</div>
              <div className="text-xs text-muted mb-2">PRs at or below this risk level will be auto-approved.</div>
              <select
                value={draft.autoApproveThreshold}
                onChange={(e) => setDraft({ ...draft, autoApproveThreshold: e.target.value })}
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground"
              >
                <option value="low">Low — only auto-approve minimal risk</option>
                <option value="medium">Medium — auto-approve low and medium risk</option>
                <option value="high">High — auto-approve most PRs (not recommended)</option>
              </select>
            </div>
          )}

          <div className="flex items-center justify-between rounded-md border border-border p-3">
            <div>
              <div className="text-sm font-medium">Enabled</div>
              <div className="text-xs text-muted">Agent will be triggered when tasks move to this pipeline stage</div>
            </div>
            <button
              onClick={() => setDraft({ ...draft, enabled: !draft.enabled })}
              className={`relative w-9 h-5 rounded-full transition-colors ${draft.enabled ? "bg-green-500" : "bg-gray-300"}`}
            >
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${draft.enabled ? "translate-x-4" : ""}`} />
            </button>
          </div>

          {/* Save button */}
          <div className="flex items-center justify-between pt-2">
            <div className="text-[10px] text-muted">
              {saveSuccess ? "Saved" : configDirty ? "Unsaved changes" : "No changes"}
            </div>
            <button
              onClick={handleSaveConfig}
              disabled={!configDirty || saving}
              className="px-6 py-2.5 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-40 font-medium"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}

      {/* Prompt tab */}
      {tab === "prompt" && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-sm font-medium">System Prompt</div>
              <div className="text-xs text-muted">
                {isUsingDefault && !promptDirty ? "Using default prompt" : "Custom prompt"}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!isUsingDefault && (
                <button
                  onClick={handleResetPrompt}
                  className="text-xs text-muted hover:text-foreground transition-colors"
                >
                  Reset to default
                </button>
              )}
            </div>
          </div>

          <PromptEditor
            value={promptDraft}
            onChange={(val) => {
              setPromptDraft(val);
              setPromptDirty(true);
            }}
          />

          <div className="flex items-center justify-between mt-3">
            <div className="text-[10px] text-muted">
              {promptDirty ? "Unsaved changes" : "Saved"}
            </div>
            <button
              onClick={handleSavePrompt}
              disabled={!promptDirty || saving}
              className="px-6 py-2.5 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-40 font-medium"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function PromptEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [extensions, setExtensions] = useState<any[]>([]);

  useEffect(() => {
    import("@codemirror/lang-markdown").then((mod) => {
      setExtensions([mod.markdown()]);
    });
  }, []);

  return (
    <div
      className="rounded-md border border-border overflow-hidden resize"
      style={{ minHeight: "400px", height: "400px", minWidth: "100%" }}
    >
      <CodeMirrorEditor
        value={value}
        onChange={onChange}
        extensions={extensions}
        height="100%"
        basicSetup={{
          lineNumbers: true,
          foldGutter: false,
          highlightActiveLine: true,
          bracketMatching: true,
        }}
        theme="light"
        style={{
          fontSize: "13px",
          fontFamily: "var(--font-geist-mono), monospace",
          height: "100%",
        }}
      />
    </div>
  );
}
