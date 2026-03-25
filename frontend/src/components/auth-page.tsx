"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export function AuthPage() {
  const { loginWithEmail, loginWithSSO, authConfig } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginWithEmail(email);
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
          <img src="/logo.png" alt="Maestro" className="w-8 h-8 rounded-md" />
          <span className="text-xl font-semibold tracking-tight">Maestro</span>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold mb-1 text-center">Sign in</h2>
          <p className="text-xs text-muted text-center mb-5">
            {authConfig?.sso_enabled
              ? "Sign in with your company account"
              : "Enter your email to continue"}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-100 border border-red-300 text-red-800 text-sm">
              {error}
            </div>
          )}

          {/* SSO button — only if configured */}
          {authConfig?.sso_enabled && (
            <>
              <button
                onClick={loginWithSSO}
                className="w-full px-4 py-2.5 text-sm rounded-md bg-foreground text-background hover:opacity-90 transition-opacity flex items-center justify-center gap-2 mb-4"
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </button>

              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-muted">or</span>
                <div className="flex-1 h-px bg-border" />
              </div>
            </>
          )}

          {/* Email login */}
          <form onSubmit={handleEmailLogin} className="space-y-3">
            <div>
              <label className="block text-xs text-muted mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@company.com"
                className="w-full px-3 py-2 text-sm rounded-md border border-border bg-background placeholder:text-muted"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-4 py-2 text-sm rounded-md bg-accent text-background hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? "..." : "Continue with email"}
            </button>
          </form>
        </div>

        <p className="text-[10px] text-muted text-center mt-4">
          No password required. We'll create your account automatically.
        </p>
      </div>
    </div>
  );
}
