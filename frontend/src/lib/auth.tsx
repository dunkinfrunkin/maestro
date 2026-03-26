"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuthUser {
  id: number;
  email: string;
  name: string;
}

interface AuthConfig {
  auth_disabled?: boolean;
  sso_enabled: boolean;
  issuer?: string;
  client_id?: string;
}

interface AuthCtx {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  authConfig: AuthConfig | null;
  loginWithEmail: (email: string) => Promise<void>;
  loginWithSSO: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  user: null,
  token: null,
  loading: true,
  authConfig: null,
  loginWithEmail: async () => {},
  loginWithSSO: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null);

  // Fetch auth config (SSO enabled?)
  useEffect(() => {
    fetch(`${API_BASE}/api/v1/auth/config`)
      .then((r) => r.json())
      .then(setAuthConfig)
      .catch(() => setAuthConfig({ sso_enabled: false }));
  }, []);

  // Check for existing token or auth-disabled mode
  useEffect(() => {
    if (authConfig?.auth_disabled) {
      // Auth disabled — fetch /me without token, backend returns dev user
      fetchMe("disabled")
        .then((u) => { setUser(u); setToken("disabled"); })
        .catch(() => {})
        .finally(() => setLoading(false));
      return;
    }
    if (authConfig === null) return; // Still loading config

    const stored = localStorage.getItem("maestro-token");
    if (stored) {
      setToken(stored);
      fetchMe(stored)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("maestro-token");
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [authConfig]);

  const loginWithEmail = useCallback(async (email: string) => {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    localStorage.setItem("maestro-token", data.token);
    setToken(data.token);
    setUser(data.user);
  }, []);

  const loginWithSSO = useCallback(() => {
    // Redirect to backend SSO endpoint — it handles the OIDC redirect
    window.location.href = `${API_BASE}/api/v1/auth/sso`;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("maestro-token");
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, loading, authConfig, loginWithEmail, loginWithSSO, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("maestro-token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchMe(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Invalid token");
  return res.json();
}
