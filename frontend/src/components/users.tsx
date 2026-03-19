"use client";

import { useCallback, useEffect, useState } from "react";
import { MemberResponse, addMember, fetchMembers, removeMember } from "@/lib/api";

export function UsersPage({ workspaceId }: { workspaceId: number }) {
  const [members, setMembers] = useState<MemberResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addRole, setAddRole] = useState("member");

  const load = useCallback(async () => {
    try {
      setMembers(await fetchMembers(workspaceId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load members");
    }
  }, [workspaceId]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addMember(workspaceId, addEmail, addRole);
      setAddEmail("");
      setShowAdd(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    }
  };

  const handleRemove = async (memberId: number) => {
    try {
      await removeMember(workspaceId, memberId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Members</h2>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="px-3 py-1.5 text-sm rounded-md border border-border hover:bg-surface-hover transition-colors"
        >
          {showAdd ? "Cancel" : "Add Member"}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
          {error}
        </div>
      )}

      {showAdd && (
        <form onSubmit={handleAdd} className="rounded-lg border border-border bg-surface p-4 flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-muted mb-1">Email</label>
            <input
              type="email"
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
              placeholder="user@example.com"
            />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Role</label>
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value)}
              className="px-3 py-2 text-sm rounded-md border border-border bg-background text-foreground"
            >
              <option value="member">Member</option>
              <option value="owner">Owner</option>
            </select>
          </div>
          <button
            type="submit"
            className="px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity"
          >
            Add
          </button>
        </form>
      )}

      <div className="space-y-2">
        {members.map((m) => (
          <div
            key={m.id}
            className="rounded-lg border border-border bg-surface p-4 flex items-center justify-between"
          >
            <div>
              <div className="text-sm font-medium">{m.name}</div>
              <div className="text-xs text-muted">{m.email}</div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs px-2 py-0.5 rounded-full bg-surface-hover text-muted">
                {m.role}
              </span>
              <button
                onClick={() => handleRemove(m.id)}
                className="text-xs text-red-600 hover:text-red-800 transition-colors"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
