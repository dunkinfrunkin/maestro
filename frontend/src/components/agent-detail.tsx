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

// Dynamic import for WYSIWYG markdown editor
const MDXEditorComponent = dynamic(
  () => import("@mdxeditor/editor").then((mod) => mod.MDXEditor),
  { ssr: false, loading: () => <div className="text-sm text-muted p-4">Loading editor...</div> }
);

type Tab = "config" | "prompt";

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
  const [defaultPrompt, setDefaultPrompt] = useState("");
  const [promptDraft, setPromptDraft] = useState("");
  const [promptDirty, setPromptDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [cfg, dp] = await Promise.all([
        getAgentConfig(workspaceId, agent.type),
        getDefaultPrompt(agent.type),
      ]);
      setConfig(cfg);
      setDefaultPrompt(dp);
      // Use custom prompt from DB if set, otherwise default
      const currentPrompt = (cfg.extra_config?.custom_prompt as string) || dp;
      setPromptDraft(currentPrompt);
      setPromptDirty(false);
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

  const handleSavePrompt = async () => {
    setSaving(true);
    try {
      await handleExtraConfigChange("custom_prompt", promptDraft);
      setPromptDirty(false);
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
      {tab === "config" && (
        <div className="space-y-6">
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

          {agent.type === "risk_profile" && (
            <div>
              <div className="text-sm font-medium mb-2">Auto-approve threshold</div>
              <div className="text-xs text-muted mb-2">PRs at or below this risk level will be auto-approved.</div>
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
              className="px-4 py-2 text-xs rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Prompt"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function PromptEditor({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [plugins, setPlugins] = useState<any[] | null>(null);
  const [editorKey, setEditorKey] = useState(0);
  const [initialValue, setInitialValue] = useState(value);

  // Load plugins dynamically
  useEffect(() => {
    import("@mdxeditor/editor").then((mod) => {
      setPlugins([
        mod.headingsPlugin(),
        mod.listsPlugin(),
        mod.quotePlugin(),
        mod.linkPlugin(),
        mod.linkDialogPlugin(),
        mod.codeBlockPlugin({ defaultCodeBlockLanguage: "bash" }),
        mod.codeMirrorPlugin({
          codeBlockLanguages: { bash: "Bash", js: "JavaScript", python: "Python", json: "JSON", "": "Plain" },
        }),
        mod.thematicBreakPlugin(),
        mod.markdownShortcutPlugin(),
        mod.toolbarPlugin({
          toolbarContents: () => {
            const { BoldItalicUnderlineToggles, BlockTypeSelect, ListsToggle, CreateLink, InsertCodeBlock } = mod;
            return (
              <>
                <BoldItalicUnderlineToggles />
                <BlockTypeSelect />
                <ListsToggle />
                <CreateLink />
                <InsertCodeBlock />
              </>
            );
          },
        }),
      ]);
    });
  }, []);

  // Remount editor when value changes externally (initial load, reset)
  useEffect(() => {
    if (value !== initialValue) {
      setInitialValue(value);
      setEditorKey((k) => k + 1);
    }
  }, [value, initialValue]);

  if (!plugins) {
    return <div className="text-sm text-muted p-4">Loading editor...</div>;
  }

  return (
    <div className="rounded-md border border-border overflow-hidden [&_.mdxeditor]:bg-background [&_.mdxeditor-toolbar]:bg-surface [&_.mdxeditor-toolbar]:border-b [&_.mdxeditor-toolbar]:border-border [&_.mdxeditor-toolbar]:px-2 [&_[contenteditable]]:text-foreground [&_[contenteditable]]:text-sm [&_[contenteditable]]:leading-relaxed [&_[contenteditable]]:min-h-[300px] [&_[contenteditable]]:px-4 [&_[contenteditable]]:py-3">
      <MDXEditorComponent
        key={editorKey}
        markdown={initialValue}
        onChange={onChange}
        plugins={plugins}
      />
    </div>
  );
}
