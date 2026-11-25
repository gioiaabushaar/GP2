import type { NextConfig } from "next";

// The browser only talks to this Next.js app. Every /api/* request is forwarded
// to the FastAPI backend, so the backend needs no CORS change for local work.
const API_URL = process.env.NEXIS_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  experimental: {
    // Every page renders in the browser after login (the token is in localStorage), so the
    // dev-time "instant navigation" check only runs where a segment opts in with `instant`.
    instantInsights: { validationLevel: "manual-warning" },
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
