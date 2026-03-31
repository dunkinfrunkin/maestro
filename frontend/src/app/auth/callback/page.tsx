"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function AuthCallbackPage() {
  useEffect(() => {
    // Check for token in hash fragment (from backend HTML redirect)
    const hash = window.location.hash.slice(1);
    const hashParams = new URLSearchParams(hash);
    const hashToken = hashParams.get("token");

    if (hashToken) {
      localStorage.setItem("maestro-token", hashToken);
      window.location.href = "/";
      return;
    }

    // If we have a code param, forward to the backend callback to exchange it
    const searchParams = new URLSearchParams(window.location.search);
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (code) {
      // Redirect to backend callback which will exchange the code and return HTML
      // that sets localStorage and redirects back
      const backendCallback = `${API_BASE}/auth/callback?code=${encodeURIComponent(code)}${state ? `&state=${encodeURIComponent(state)}` : ""}`;
      window.location.href = backendCallback;
      return;
    }

    // No token or code — go home
    window.location.href = "/";
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <p className="text-sm text-muted">Signing in...</p>
      </div>
    </div>
  );
}
