"use client";

import { useEffect } from "react";

export default function AuthCallbackPage() {
  useEffect(() => {
    const hash = window.location.hash.slice(1);
    const params = new URLSearchParams(hash);
    const token = params.get("token");

    if (token) {
      localStorage.setItem("maestro-token", token);
    }

    // Hard redirect to clear the hash fragment
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
