"use client";

import { useCallback, useEffect, useState } from "react";
import { useDashboard } from "@/lib/dashboard-context";

interface CommentEntry {
  id: number;
  task_ref: string;
  task_title: string;
  pr_url: string;
  pr_number: string;
  repo: string;
  author: string;
  triggered_by: string;
  body: string;
  is_agent: boolean;
  agent_type: string | null;
  url: string | null;
  file_path: string | null;
  line_number: number | null;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("maestro-token") : null;
  return fetch(url, {
    ...init,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init?.headers },
    cache: "no-store",
  });
}

export function CommentsPage() {
  const { activeWorkspace, activeProject } = useDashboard();
  const [comments, setComments] = useState<CommentEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const filter = "agent";

  const loadComments = useCallback(async () => {
    try {
      const qs = new URLSearchParams();
      if (activeProject?.id) qs.set("project_id", String(activeProject.id));
      if (filter !== "all") qs.set("source", filter);
      const res = await authFetch(`${API_BASE}/api/v1/comments?${qs}`);
      if (res.ok) {
        const data = await res.json();
        setComments(data);
      }
    } catch {}
    setLoading(false);
  }, [activeProject?.id, filter]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const filteredComments = comments;

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const getAgentLabel = (entry: CommentEntry) => {
    if (!entry.is_agent) return null;
    if (entry.agent_type) return entry.agent_type.charAt(0).toUpperCase() + entry.agent_type.slice(1);
    if (entry.body.includes("Implementation Agent")) return "Implementation";
    if (entry.body.includes("Review Agent")) return "Review";
    if (entry.body.includes("Risk Profile Agent")) return "Risk Profile";
    return "Agent";
  };

  return (
    <div className="p-6 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Agent Comments</h1>
      </div>

      {loading ? (
        <div className="text-sm text-muted">Loading comments...</div>
      ) : filteredComments.length === 0 ? (
        <div className="text-sm text-muted">No agent comments found.</div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-surface border-b border-border">
                <th className="text-left px-3 py-2 font-medium text-muted">Agent</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Comment</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Task</th>
                <th className="text-left px-3 py-2 font-medium text-muted">PR/MR</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Author</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Triggered By</th>
                <th className="text-left px-3 py-2 font-medium text-muted">Time</th>
                <th className="text-left px-3 py-2 font-medium text-muted"></th>
              </tr>
            </thead>
            <tbody>
              {filteredComments.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors">
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
                      {getAgentLabel(c)}
                    </span>
                  </td>
                  <td className="px-3 py-2 max-w-md">
                    <div className="truncate text-foreground">
                      {c.body.replace(/\n---\n\*Created by Maestro.*\*$/s, "").trim().split("\n")[0].substring(0, 120)}
                    </div>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <a href={`/tasks/${encodeURIComponent(c.task_ref)}`} className="text-accent hover:underline">
                      {c.task_title}
                    </a>
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {c.pr_number ? (
                      <a href={c.pr_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                        #{c.pr_number}
                      </a>
                    ) : "-"}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-muted">
                    {c.author}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-muted">
                    {c.triggered_by || "-"}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-muted">
                    {formatTime(c.created_at)}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                        View
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
