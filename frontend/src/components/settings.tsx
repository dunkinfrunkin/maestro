"use client";

import { useEffect, useState } from "react";
import { ServiceConfig, fetchConfig } from "@/lib/api";

export function SettingsPage() {
  const [config, setConfig] = useState<ServiceConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then(setConfig)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to fetch config")
      );
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-border border-dashed p-8 text-center text-muted text-sm">
        {error === "API error: 503"
          ? "Orchestrator not connected — no WORKFLOW.md loaded"
          : error}
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-sm text-muted">Loading configuration...</div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Tracker Connection */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Tracker Connection</h2>
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <div className="flex items-center gap-3 mb-2">
            <div
              className={`w-2.5 h-2.5 rounded-full ${
                config.tracker.api_key_set
                  ? "bg-green-500"
                  : "bg-red-500"
              }`}
            />
            <span className="text-sm font-medium">
              {config.tracker.api_key_set ? "Connected" : "Not connected"}
            </span>
          </div>

          <SettingsRow label="Tracker" value={config.tracker.kind} />
          <SettingsRow label="Endpoint" value={config.tracker.endpoint} mono />
          <SettingsRow
            label="Project"
            value={config.tracker.project_slug || "—"}
            mono
          />
          <SettingsRow
            label="API Key"
            value={config.tracker.api_key_set ? "********" : "Not set"}
          />
          <SettingsRow
            label="Active States"
            value={config.tracker.active_states.join(", ")}
          />
          <SettingsRow
            label="Terminal States"
            value={config.tracker.terminal_states.join(", ")}
          />
        </div>
      </section>

      {/* Polling */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Polling</h2>
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <SettingsRow
            label="Interval"
            value={`${(config.polling.interval_ms / 1000).toFixed(0)}s`}
          />
        </div>
      </section>

      {/* Agent */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Agent</h2>
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <SettingsRow label="Command" value={config.codex.command} mono />
          <SettingsRow
            label="Max Concurrent"
            value={String(config.agent.max_concurrent_agents)}
          />
          <SettingsRow
            label="Max Retry Backoff"
            value={`${(config.agent.max_retry_backoff_ms / 1000).toFixed(0)}s`}
          />
          <SettingsRow
            label="Turn Timeout"
            value={`${(config.codex.turn_timeout_ms / 1000 / 60).toFixed(0)}m`}
          />
          <SettingsRow
            label="Stall Timeout"
            value={`${(config.codex.stall_timeout_ms / 1000).toFixed(0)}s`}
          />
        </div>
      </section>

      {/* Workspace */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Workspace</h2>
        <div className="rounded-lg border border-border bg-surface p-5 space-y-4">
          <SettingsRow label="Root" value={config.workspace.root} mono />
        </div>
      </section>
    </div>
  );
}

function SettingsRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-sm text-muted whitespace-nowrap">{label}</span>
      <span
        className={`text-sm text-right break-all ${mono ? "font-mono" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}
