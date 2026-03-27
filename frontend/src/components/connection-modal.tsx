"use client";

import { useState } from "react";
import { createConnection } from "@/lib/api";
import { GitHubLogo, LinearLogo, JiraLogo, GitLabLogo } from "@/components/icons";

type ConnectionKind = "github" | "linear" | "jira" | "gitlab";
type Step = "select" | "guide" | "form";

export function ConnectionModal({
  workspaceId,
  onCreated,
  onClose,
}: {
  workspaceId: number;
  onCreated: () => void;
  onClose: () => void;
}) {
  const [step, setStep] = useState<Step>("select");
  const [kind, setKind] = useState<ConnectionKind>("github");

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
            {step !== "select" && `Connect ${PROVIDER_NAMES[kind]}`}
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
            <ProviderGuide kind={kind} onContinue={() => setStep("form")} onBack={() => setStep("select")} />
          )}
          {step === "form" && (
            <ConnectionForm
              kind={kind}
              workspaceId={workspaceId}
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

const PROVIDERS: { kind: ConnectionKind; name: string; desc: string; Logo: React.FC<{ className?: string }> }[] = [
  { kind: "github", name: "GitHub", desc: "Issues and pull requests across your repositories", Logo: GitHubLogo },
  { kind: "gitlab", name: "GitLab", desc: "Issues and merge requests from GitLab projects", Logo: GitLabLogo },
  { kind: "linear", name: "Linear", desc: "Connect to Linear project issues", Logo: LinearLogo },
  { kind: "jira", name: "Jira", desc: "Connect to Jira Cloud or Server projects", Logo: JiraLogo },
];

const PROVIDER_NAMES: Record<ConnectionKind, string> = {
  github: "GitHub", gitlab: "GitLab", linear: "Linear", jira: "Jira",
};

function TrackerSelect({ onSelect }: { onSelect: (kind: ConnectionKind) => void }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted mb-4">Choose a service to connect.</p>
      {PROVIDERS.map(({ kind, name, desc, Logo }) => (
        <button
          key={kind}
          onClick={() => onSelect(kind)}
          className="w-full flex items-center gap-4 p-4 rounded-lg border border-border hover:bg-surface-hover transition-colors text-left"
        >
          <Logo className="w-8 h-8 flex-shrink-0" />
          <div>
            <div className="text-sm font-medium">{name}</div>
            <div className="text-xs text-muted">{desc}</div>
          </div>
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step 2: Permission guides
// ---------------------------------------------------------------------------

function ProviderGuide({ kind, onContinue, onBack }: { kind: ConnectionKind; onContinue: () => void; onBack: () => void }) {
  const provider = PROVIDERS.find((p) => p.kind === kind)!;
  const Logo = provider.Logo;

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <Logo className="w-6 h-6" />
        <span className="text-sm font-medium">{GUIDE_CONFIG[kind].title}</span>
      </div>

      <ol className="space-y-3 text-sm mb-6">
        {GUIDE_CONFIG[kind].steps.map((step, i) => (
          <GuideStep key={i} number={i + 1}>{step}</GuideStep>
        ))}
      </ol>

      <div className="flex justify-between">
        <button onClick={onBack} className="px-4 py-2 text-sm text-muted hover:text-foreground transition-colors">Back</button>
        <button onClick={onContinue} className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity">
          I have my credentials
        </button>
      </div>
    </div>
  );
}

const GUIDE_CONFIG: Record<ConnectionKind, { title: string; steps: React.ReactNode[] }> = {
  github: {
    title: "GitHub Personal Access Token",
    steps: [
      <>Go to <a href="https://github.com/settings/tokens?type=beta" target="_blank" rel="noopener noreferrer" className="text-accent underline">GitHub &rarr; Settings &rarr; Developer settings &rarr; Fine-grained tokens</a></>,
      <>Click <strong>Generate new token</strong></>,
      <>Set a name (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">Maestro</code>) and expiration</>,
      <>Under <strong>Repository access</strong>, select <strong>All repositories</strong> or specific ones</>,
      <>Grant permissions: <strong>Contents</strong>, <strong>Issues</strong>, <strong>Pull requests</strong> (Read and write)</>,
      <>Click <strong>Generate token</strong> and copy it</>,
    ],
  },
  gitlab: {
    title: "GitLab Personal Access Token",
    steps: [
      <>Go to <strong>GitLab &rarr; Preferences &rarr; Access Tokens</strong></>,
      <>Click <strong>Add new token</strong></>,
      <>Set a name and expiration date</>,
      <>Select scopes: <strong>api</strong> (full access) or <strong>read_api</strong> + <strong>write_repository</strong></>,
      <>Click <strong>Create personal access token</strong> and copy it</>,
      <>Note your <strong>project ID</strong> — it&apos;s on the project&apos;s main page or in the URL</>,
    ],
  },
  linear: {
    title: "Linear API Key",
    steps: [
      <>Go to <a href="https://linear.app/settings/api" target="_blank" rel="noopener noreferrer" className="text-accent underline">Linear &rarr; Settings &rarr; API</a></>,
      <>Under <strong>Personal API keys</strong>, click <strong>Create key</strong></>,
      <>Give it a label (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">Maestro</code>)</>,
      <>Copy the key — it starts with <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">lin_api_</code></>,
      <>Note your <strong>project slug</strong> from the URL: <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">linear.app/team/your-slug</code></>,
    ],
  },
  jira: {
    title: "Jira API Token",
    steps: [
      <>Go to <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noopener noreferrer" className="text-accent underline">Atlassian &rarr; Account &rarr; Security &rarr; API tokens</a></>,
      <>Click <strong>Create API token</strong></>,
      <>Give it a label (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">Maestro</code>)</>,
      <>Copy the token</>,
      <>Note your <strong>Jira URL</strong> (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">https://yourcompany.atlassian.net</code>)</>,
      <>Note your <strong>project key</strong> (e.g., <code className="text-xs bg-surface-hover px-1 py-0.5 rounded">ENG</code>) and your <strong>email address</strong></>,
    ],
  },
};

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

const FORM_CONFIG: Record<ConnectionKind, {
  tokenLabel: string; tokenPlaceholder: string;
  projectLabel: string; projectPlaceholder: string; projectRequired: boolean; projectHelp?: string;
  endpointPlaceholder: string; extraFields?: string[];
}> = {
  github: {
    tokenLabel: "API Token", tokenPlaceholder: "github_pat_...",
    projectLabel: "Repository", projectPlaceholder: "owner/repo", projectRequired: false, projectHelp: "Leave blank for all repos",
    endpointPlaceholder: "https://api.github.com",
  },
  gitlab: {
    tokenLabel: "Personal Access Token", tokenPlaceholder: "glpat-...",
    projectLabel: "Project ID or path", projectPlaceholder: "group/project or 12345", projectRequired: true,
    endpointPlaceholder: "https://gitlab.com",
  },
  linear: {
    tokenLabel: "API Key", tokenPlaceholder: "lin_api_...",
    projectLabel: "Project slug", projectPlaceholder: "my-project", projectRequired: true,
    endpointPlaceholder: "https://api.linear.app/graphql",
  },
  jira: {
    tokenLabel: "API Token", tokenPlaceholder: "ATATT...",
    projectLabel: "Project key", projectPlaceholder: "ENG", projectRequired: true,
    endpointPlaceholder: "https://yourcompany.atlassian.net", extraFields: ["email"],
  },
};

function ConnectionForm({
  kind,
  workspaceId,
  onCreated,
  onBack,
}: {
  kind: ConnectionKind;
  workspaceId: number;
  onCreated: () => void;
  onBack: () => void;
}) {
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [token, setToken] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const config = FORM_CONFIG[kind];
  const provider = PROVIDERS.find((p) => p.kind === kind)!;
  const Logo = provider.Logo;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !token) { setError("Name and token are required"); return; }
    if (config.projectRequired && !project) { setError(`${config.projectLabel} is required`); return; }
    if (kind === "jira" && !email) { setError("Email is required for Jira Cloud"); return; }
    setSaving(true);
    setError(null);
    try {
      await createConnection({
        kind, name, project, token,
        endpoint: endpoint || undefined,
        workspace_id: workspaceId,
        ...(kind === "jira" ? { email } : {}),
      });
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
        <Logo className="w-5 h-5" />
        <span className="text-sm font-medium">{PROVIDER_NAMES[kind]} connection details</span>
      </div>

      {error && (
        <div className="p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-xs">{error}</div>
      )}

      <div>
        <label className="block text-xs text-muted mb-1">Connection name</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)}
          placeholder={`My ${PROVIDER_NAMES[kind]}`}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
      </div>

      <div>
        <label className="block text-xs text-muted mb-1">{config.tokenLabel}</label>
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)}
          placeholder={config.tokenPlaceholder}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
      </div>

      {kind === "jira" && (
        <div>
          <label className="block text-xs text-muted mb-1">Email <span className="text-muted">(your Atlassian account email)</span></label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted" />
        </div>
      )}

      <div>
        <label className="block text-xs text-muted mb-1">
          {config.projectLabel}
          {!config.projectRequired && <span className="text-muted"> (optional{config.projectHelp ? ` — ${config.projectHelp}` : ""})</span>}
        </label>
        <input type="text" value={project} onChange={(e) => setProject(e.target.value)}
          placeholder={config.projectPlaceholder}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
      </div>

      <div>
        <label className="block text-xs text-muted mb-1">Endpoint <span className="text-muted">(optional, for self-hosted)</span></label>
        <input type="text" value={endpoint} onChange={(e) => setEndpoint(e.target.value)}
          placeholder={config.endpointPlaceholder}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono" />
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
