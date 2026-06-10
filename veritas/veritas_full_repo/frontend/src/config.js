/**
 * Build-time config (Vite). Set VITE_VERITAS_API_BASE_URL to:
 * - `/api/v1` — dev: same-origin via Vite proxy (no CORS issues)
 * - `http://127.0.0.1:6000/api/v1` — direct to API (backend must allow UI origin in ALLOWED_ORIGINS)
 *
 * In dev, defaults to `/api/v1` so the UI works without copying `.env.local` (Vite on :7000 proxies → API on :6000).
 */
function resolveVeritasApiBaseUrl() {
  const raw = import.meta.env.VITE_VERITAS_API_BASE_URL;
  if (raw != null && String(raw).trim() !== "") {
    return String(raw).replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "/api/v1";
  }
  return "";
}

export const VERITAS_API_BASE_URL = resolveVeritasApiBaseUrl();

/**
 * Optional local-only defaults for the HPC connect form (set in .env.local; never commit).
 * Vite requires the VITE_ prefix.
 */
export const hpcConnectFormDefaults = () => ({
  hostname: (import.meta.env.VITE_HPC_DEFAULT_HOSTNAME || "").trim(),
  username: (import.meta.env.VITE_HPC_DEFAULT_USERNAME || "").trim(),
  port: (import.meta.env.VITE_HPC_DEFAULT_PORT || "").trim(),
  key_path: (import.meta.env.VITE_HPC_DEFAULT_KEY_PATH || "").trim(),
  notes: (import.meta.env.VITE_HPC_DEFAULT_NOTES || "").trim(),
});

export const isVeritasApiConfigured = () => {
  const b = VERITAS_API_BASE_URL;
  if (!b) return false;
  if (b.startsWith("http://") || b.startsWith("https://")) return true;
  if (b.startsWith("/")) return true;
  return false;
};
