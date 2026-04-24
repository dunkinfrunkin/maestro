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

const AGENT_COLORS: Record<string, string> = {
  implementation: "bg-blue-100 text-blue-800 border-blue-300",
  review: "bg-purple-100 text-purple-800 border-purple-300",
  risk_profile: "bg-orange-100 text-orange-800 border-orange-300",
};

export function CommentsPage() {
  const { activeProject } = useDashboard();
  const [comments, setComments] = useState<CommentEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const loadComments = useCallback(async (p = page) => {
    try {
      setLoading(true);
      const qs = new URLSearchParams();
      if (activeProject?.id) qs.set("project_id", String(activeProject.id));
      qs.set("source", "agent");
      qs.set("offset", String(p * pageSize));
      qs.set("limit", String(pageSize));
      const res = await authFetch(`${API_BASE}/api/v1/comments?${qs}`);
      if (res.ok) {
        const data = await res.json();
        setComments(data.comments || data);
        setTotal(data.total || (data.comments || data).length);
      }
    } catch {}
    setLoading(false);
  }, [activeProject?.id, page]);

  useEffect(() => {
    loadComments();
  }, [loadComments]);

  const totalPages = Math.ceil(total / pageSize);

  const getAgentLabel = (c: CommentEntry) => {
    if (c.agent_type) return c.agent_type.charAt(0).toUpperCase() + c.agent_type.slice(1).replace("_", " ");
    if (c.body.includes("Implementation Agent")) return "Implementation";
    if (c.body.includes("Review Agent")) return "Review";
    if (c.body.includes("Risk Profile Agent")) return "Risk Profile";
    return "Agent";
  };

  const getAgentColor = (c: CommentEntry) => {
    const type = c.agent_type || (c.body.includes("Implementation") ? "implementation" : c.body.includes("Review") ? "review" : c.body.includes("Risk") ? "risk_profile" : "");
    return AGENT_COLORS[type] || "bg-gray-100 text-gray-800 border-gray-300";
  };

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  };

  const truncateBody = (body: string) => {
    const clean = body.replace(/\n---\n\*Created by Maestro.*\*$/s, "").trim();
    const firstLine = clean.split("\n")[0];
    return firstLine.length > 140 ? firstLine.substring(0, 140) + "..." : firstLine;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Agent Comments</h1>
        <span className="text-xs text-muted">{total} comment{total !== 1 ? "s" : ""}</span>
      </div>

      {loading ? (
        <div className="text-sm text-muted">Loading...</div>
      ) : comments.length === 0 ? (
        <div className="text-sm text-muted">No agent comments found.</div>
      ) : (
        <div className="rounded-lg border border-border overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-surface border-b border-border">
                <th className="text-left px-3 py-2.5 font-medium text-muted">Agent</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">Comment</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">Task</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">PR/MR</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">Author</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">Triggered By</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted">Time</th>
                <th className="text-left px-3 py-2.5 font-medium text-muted"></th>
              </tr>
            </thead>
            <tbody>
              {comments.map((c) => (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors">
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${getAgentColor(c)}`}>
                      {getAgentLabel(c)}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <div className="truncate max-w-sm text-foreground" title={c.body.split("\n")[0]}>
                      {truncateBody(c.body)}
                    </div>
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    <a href={`/tasks/${encodeURIComponent(c.task_ref)}`} className="text-accent hover:underline">
                      {c.task_title}
                    </a>
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
                    {c.pr_number ? (
                      <a href={c.pr_url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                        #{c.pr_number}
                      </a>
                    ) : "-"}
                  </td>
                  <td className="px-3 py-2.5 whitespace-nowrap text-muted">{c.author}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap text-muted">{c.triggered_by || "-"}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap text-muted">{formatTime(c.created_at)}</td>
                  <td className="px-3 py-2.5 whitespace-nowrap">
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

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-muted">
            {page * pageSize + 1}-{Math.min((page + 1) * pageSize, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= totalPages - 1}
              className="px-3 py-1.5 text-xs rounded-md border border-border hover:bg-surface-hover transition-colors disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
