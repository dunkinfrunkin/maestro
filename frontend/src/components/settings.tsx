"use client";

import { useCallback, useEffect, useState } from "react";
import {
  TrackerConnection,
  fetchConnections,
  createConnection,
  deleteConnection,
} from "@/lib/api";

export function SettingsPage() {
  const [connections, setConnections] = useState<TrackerConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await fetchConnections();
      setConnections(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connections");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: number) => {
    try {
      await deleteConnection(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Tracker Connections</h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors"
          >
            {showForm ? "Cancel" : "Add Connection"}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
            {error}
          </div>
        )}

        {showForm && (
          <ConnectionForm
            onCreated={() => {
              setShowForm(false);
              load();
            }}
            onError={setError}
          />
        )}

        {connections.length === 0 && !showForm ? (
          <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
            No tracker connections configured. Add a GitHub or Linear connection to get started.
          </div>
        ) : (
          <div className="space-y-3">
            {connections.map((conn) => (
              <div
                key={conn.id}
                className="rounded-lg border border-border bg-surface p-4"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-2 h-2 rounded-full bg-green-500" />
                      <span className="font-medium text-sm">{conn.name}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-surface-hover text-muted">
                        {conn.kind}
                      </span>
                    </div>
                    <div className="text-xs text-muted font-mono">{conn.project}</div>
                    {conn.endpoint && (
                      <div className="text-xs text-muted font-mono">{conn.endpoint}</div>
                    )}
                  </div>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    className="text-xs text-red-600 hover:text-red-800 transition-colors"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ConnectionForm({
  onCreated,
  onError,
}: {
  onCreated: () => void;
  onError: (msg: string) => void;
}) {
  const [kind, setKind] = useState("github");
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [token, setToken] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !project || !token) {
      onError("Name, project, and token are required");
      return;
    }
    setSaving(true);
    try {
      await createConnection({
        kind,
        name,
        project,
        token,
        endpoint: endpoint || undefined,
      });
      onCreated();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to create connection");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-border bg-surface p-4 mb-4 space-y-3"
    >
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-muted mb-1">Type</label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground"
          >
            <option value="github">GitHub</option>
            <option value="linear">Linear</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-muted mb-1">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My GitHub"
            className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
          />
        </div>
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">
          {kind === "github" ? "Repository (owner/repo)" : "Project Slug"}
        </label>
        <input
          type="text"
          value={project}
          onChange={(e) => setProject(e.target.value)}
          placeholder={kind === "github" ? "octocat/hello-world" : "my-project"}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
        />
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">API Token</label>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="ghp_... or lin_api_..."
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
        />
      </div>
      <div>
        <label className="block text-xs text-muted mb-1">
          Endpoint (optional, for GitHub Enterprise / custom Linear)
        </label>
        <input
          type="text"
          value={endpoint}
          onChange={(e) => setEndpoint(e.target.value)}
          placeholder={kind === "github" ? "https://api.github.com" : "https://api.linear.app/graphql"}
          className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted font-mono"
        />
      </div>
      <button
        type="submit"
        disabled={saving}
        className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50"
      >
        {saving ? "Saving..." : "Add Connection"}
      </button>
    </form>
  );
}
