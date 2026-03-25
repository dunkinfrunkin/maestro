"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AuthCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const hash = window.location.hash.slice(1); // remove #
    const params = new URLSearchParams(hash);
    const token = params.get("token");

    if (token) {
      localStorage.setItem("maestro-token", token);
      router.replace("/");
    } else {
      router.replace("/");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center">
        <p className="text-sm text-muted">Signing in...</p>
      </div>
    </div>
  );
}
