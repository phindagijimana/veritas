/**
 * Build-time config (Vite). Set VITE_VERITAS_API_BASE_URL to:
 * - `/api/v1` — dev: same-origin via Vite proxy (no CORS issues)
 * - `http://127.0.0.1:6000/api/v1` — direct to API (backend must allow UI origin in ALLOWED_ORIGINS)
 */
export const VERITAS_API_BASE_URL = (import.meta.env.VITE_VERITAS_API_BASE_URL || "").replace(/\/$/, "");

export const isVeritasApiConfigured = () => {
  const b = VERITAS_API_BASE_URL;
  if (!b) return false;
  if (b.startsWith("http://") || b.startsWith("https://")) return true;
  if (b.startsWith("/")) return true;
  return false;
};
