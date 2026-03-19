"use client";

import { useState } from "react";
import { createConnection } from "@/lib/api";
import { GitHubLogo, LinearLogo } from "@/components/icons";

type Step = "select" | "guide" | "form";

export function ConnectionModal({
  onCreated,
  onClose,
}: {
  onCreated: () => void;
  onClose: () => void;
}) {
  const [step, setStep] = useState<Step>("select");
  const [kind, setKind] = useState<"github" | "linear">("github");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-foreground/20" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-base font-semibold">
            {step === "select" && "Add Connection"}
            {step === "guide" && (kind === "github" ? "Connect GitHub" : "Connect Linear")}
            {step === "form" && (kind === "github" ? "Connect GitHub" : "Connect Linear")}
          </h2>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:text-foreground hover:bg-surface-hover transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          {step === "select" && (
            <TrackerSelect
              onSelect={(k) => { setKind(k); setStep("guide"); }}
            />
          )}
          {step === "guide" && (
            kind === "github"
              ? <GitHubGuide onContinue={() => setStep("form")} onBack={() => setStep("select")} />
              : <LinearGuide onContinue={() => setStep("form")} onBack={() => setStep("select")} />
          )}
          {step === "form" && (
            <ConnectionForm
              kind={kind}
              onCreated={() => { onCreated(); onClose(); }}
              onBack={() => setStep("guide")}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 1: Select tracker
// ---------------------------------------------------------------------------

function TrackerSelect({ onSelect }: { onSelect: (kind: "github" | "linear") => void }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted mb-4">Choose a tracker to connect.</p>
      <button
        onClick={() => onSelect("github")}
        className="w-full flex items-center gap-4 p-4 rounded-lg border border-border hover:bg-surface-hover transition-colors text-left"
      >
        <GitHubLogo className="w-8 h-8 flex-shrink-0" />
        <div>
          <div className="text-sm font-medium">GitHub</div>
          <div className="text-xs text-muted">Connect to GitHub Issues across your repositories</div>
        </div>
      </button>
      <button
        onClick={() => onSelect("linear")}
        className="w-full flex items-center gap-4 p-4 rounded-lg border border-border hover:bg-surface-hover transition-colors text-left"
      >
        <LinearLogo className="w-8 h-8 flex-shrink-0" />
        <div>
          <div className="text-sm font-medium">Linear</div>
          <div className="text-xs text-muted">Connect to Linear project issues</div>
        </div>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2: Permission guides
// ---------------------------------------------------------------------------

function GitHubGuide({ onContinue, onBack }: { onContinue: () => void; onBack: () => void }) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <GitHubLogo className="w-6 h-6" />
        <span className="text-sm font-medium">GitHub Personal Access Token</span>
      </div>

      <ol className="space-y-3 text-sm mb-6">
        <GuideStep number={1}>
          Go to <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener noreferrer" className="text-accent underline">GitHub Settings &rarr; Developer settings &rarr; Personal access tokens &rarr; Fine-grained tokens</a>
        </GuideStep>
        <GuideStep number={2}>
          Click <strong>Generate new token</strong>
        </GuideStep>
        <GuideStep number={3}>
          Set a descriptive name (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">Maestro</code>) and expiration
        </GuideStep>
        <GuideStep number={4}>
          Under <strong>Repository access</strong>, select either:
          <ul className="mt-1 ml-4 space-y-1 text-muted">
            <li>&bull; <strong>All repositories</strong> — access all repos</li>
            <li>&bull; <strong>Only select repositories</strong> — pick specific ones</li>
          </ul>
        </GuideStep>
        <GuideStep number={5}>
          Under <strong>Permissions &rarr; Repository permissions</strong>, grant:
          <ul className="mt-1 ml-4 space-y-1 text-muted">
            <li>&bull; <strong>Contents</strong> — Read and write</li>
            <li>&bull; <strong>Issues</strong> — Read and write</li>
            <li>&bull; <strong>Pull requests</strong> — Read and write</li>
            <li>&bull; <strong>Metadata</strong> — Read-only (auto-selected)</li>
          </ul>
        </GuideStep>
        <GuideStep number={6}>
          Click <strong>Generate token</strong> and copy it
        </GuideStep>
      </ol>

      <div className="flex justify-between">
        <button onClick={onBack} className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Back</button>
        <button onClick={onContinue} className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
          I have my token
        </button>
      </div>
    </div>
  );
}

function LinearGuide({ onContinue, onBack }: { onContinue: () => void; onBack: () => void }) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <LinearLogo className="w-6 h-6" />
        <span className="text-sm font-medium">Linear API Key</span>
      </div>

      <ol className="space-y-3 text-sm mb-6">
        <GuideStep number={1}>
          Go to <a href="https://linear.app/settings/api" target="_blank" rel="noopener noreferrer" className="text-accent underline">Linear Settings &rarr; API</a>
        </GuideStep>
        <GuideStep number={2}>
          Under <strong>Personal API keys</strong>, click <strong>Create key</strong>
        </GuideStep>
        <GuideStep number={3}>
          Give it a label (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">Maestro</code>)
        </GuideStep>
        <GuideStep number={4}>
          Copy the generated key — it starts with <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">lin_api_</code>
        </GuideStep>
        <GuideStep number={5}>
          Note your <strong>project slug</strong> — it&apos;s in the URL when viewing your project:
          <div className="mt-1 text-xs text-muted font-mono bg-surface-hover px-2 py-1 rounded">
            linear.app/team/<strong>your-slug</strong>/...
          </div>
        </GuideStep>
      </ol>

      <div className="flex justify-between">
        <button onClick={onBack} className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Back</button>
        <button onClick={onContinue} className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
          I have my key
        </button>
      </div>
    </div>
  );
}

function GuideStep({ number, children }: { number: number; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-accent text-background text-[10px] font-bold flex items-center justify-center mt-0.5">
        {number}
      </span>
      <span>{children}</span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Step 3: Form
// ---------------------------------------------------------------------------

function ConnectionForm({
  kind,
  onCreated,
  onBack,
}: {
  kind: "github" | "linear";
  onCreated: () => void;
  onBack: () => void;
}) {
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [token, setToken] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !token) { setError("Name and token are required"); return; }
    if (kind === "linear" && !project) { setError("Project slug is required for Linear"); return; }
    setSaving(true);
    setError(null);
    try {
      await createConnection({ kind, name, project, token, endpoint: endpoint || undefined });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create connection");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center gap-3 mb-2">
        {kind === "github" ? <GitHubLogo className="w-5 h-5" /> : <LinearLogo className="w-5 h-5" />}
        <span className="text-sm font-medium">{kind === "github" ? "GitHub" : "Linear"} connection details</span>
      </div>

      {error && (
        <div className="p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">
          {error}
        </div>
      )}

      <div>
        <label className="block text-xs text-muted mb-1">Connection name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={kind === "github" ? "My GitHub" : "My Linear"}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
        />
      </div>

      <div>
        <label className="block text-xs text-muted mb-1">
          {kind === "github" ? "API Token" : "API Key"}
        </label>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder={kind === "github" ? "github_pat_..." : "lin_api_..."}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
        />
      </div>

      {kind === "github" ? (
        <div>
          <label className="block text-xs text-muted mb-1">
            Repository <span className="text-muted">(optional — leave blank for all repos)</span>
          </label>
          <input
            type="text"
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="owner/repo"
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
          />
        </div>
      ) : (
        <div>
          <label className="block text-xs text-muted mb-1">Project slug</label>
          <input
            type="text"
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="my-project"
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
          />
        </div>
      )}

      <div>
        <label className="block text-xs text-muted mb-1">
          Endpoint <span className="text-muted">(optional, for self-hosted instances)</span>
        </label>
        <input
          type="text"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder={kind === "github" ? "https://api.github.com" : "https://api.linear.app/graphql"}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
        />
      </div>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Back</button>
        <button type="submit" disabled={saving} className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50">
          {saving ? "Connecting..." : "Connect"}
        </button>
      </div>
    </form>
  );
}
