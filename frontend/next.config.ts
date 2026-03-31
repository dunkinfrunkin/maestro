import type { NextConfig } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    // beforeFiles runs BEFORE page routes, so /auth/* hits the backend
    // even though a page exists at /auth/callback. This keeps everything
    // on the same origin — cookies and localStorage just work.
    return {
      beforeFiles: [
        { source: "/auth/:path*", destination: `${API_URL}/auth/:path*` },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
