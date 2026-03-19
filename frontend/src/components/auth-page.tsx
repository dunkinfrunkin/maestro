"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export function AuthPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, name, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center font-[family-name:var(--font-geist-sans)]">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-8">
          <div className="w-8 h-8 rounded-md bg-accent flex items-center justify-center">
            <span className="text-background text-sm font-bold">M</span>
          </div>
          <span className="text-xl font-semibold tracking-tight">Maestro</span>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold mb-4 text-center">
            {mode === "login" ? "Sign in" : "Create account"}
          </h2>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-muted mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
              />
            </div>
            {mode === "register" && (
              <div>
                <label className="block text-xs text-muted mb-1">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
                />
              </div>
            )}
            <div>
              <label className="block text-xs text-muted mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading
                ? "..."
                : mode === "login"
                ? "Sign in"
                : "Create account"}
            </button>
          </form>

          <div className="mt-4 text-center text-sm text-muted">
            {mode === "login" ? (
              <>
                No account?{" "}
                <button
                  onClick={() => { setMode("register"); setError(null); }}
                  className="text-accent hover:underline"
                >
                  Create one
                </button>
              </>
            ) : (
              <>
                Have an account?{" "}
                <button
                  onClick={() => { setMode("login"); setError(null); }}
                  className="text-accent hover:underline"
                >
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
