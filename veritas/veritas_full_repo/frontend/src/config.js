/**
 * Build-time config (Vite). Set VITE_VERITAS_API_BASE_URL to your API prefix, e.g. https://api.example.com/api/v1
 */
export const VERITAS_API_BASE_URL = (import.meta.env.VITE_VERITAS_API_BASE_URL || "").replace(/\/$/, "");

/** Same host as the API — used for GET /health and GET /ready at server root. */
export function veritasApiOrigin() {
  if (!VERITAS_API_BASE_URL) return "";
  try {
    return new URL(VERITAS_API_BASE_URL).origin;
  } catch {
    return "";
  }
}

export const isVeritasApiConfigured = () =>
  Boolean(VERITAS_API_BASE_URL && VERITAS_API_BASE_URL.startsWith("http"));
