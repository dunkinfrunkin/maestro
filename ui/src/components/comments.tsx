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
        <div className="text-sm text-muted">No comments found.</div>
      ) : (
        <div className="space-y-3">
          {filteredComments.map((c) => (
            <div key={c.id} className="border border-border rounded-lg p-4 bg-background">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium">{c.author}</span>
                  {c.is_agent && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200">
                      {getAgentLabel(c)}
                    </span>
                  )}
                  {!c.is_agent && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 border border-green-200">
                      Human
                    </span>
                  )}
                  <span className="text-[10px] text-muted">{c.repo}</span>
                  {c.pr_number && (
                    <a
                      href={c.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-accent hover:underline"
                    >
                      #{c.pr_number}
                    </a>
                  )}
                </div>
                <span className="text-[10px] text-muted flex-shrink-0">{formatTime(c.created_at)}</span>
              </div>

              {c.file_path && (
                <div className="mt-1 text-[10px] text-muted font-mono">
                  {c.file_path}{c.line_number ? `:${c.line_number}` : ""}
                </div>
              )}

              <div className="mt-2 text-xs text-foreground whitespace-pre-wrap leading-relaxed">
                {c.body.replace(/\n---\n\*Created by Maestro.*\*$/, "").trim()}
              </div>

              {c.url && (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-2 text-[10px] text-accent hover:underline"
                >
                  View on {c.repo.includes("gitlab") ? "GitLab" : "GitHub"}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
