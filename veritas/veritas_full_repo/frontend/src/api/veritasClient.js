import { VERITAS_API_BASE_URL, veritasApiOrigin, isVeritasApiConfigured } from "../config.js";

function abortAfter(ms) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  return { signal: c.signal, done: () => clearTimeout(t) };
}

/**
 * GET /health on API origin (liveness).
 * @returns {Promise<{ status: string } | null>}
 */
export async function fetchHealthLiveness(timeoutMs = 5000) {
  const origin = veritasApiOrigin();
  if (!origin) return null;
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${origin}/health`, { signal, credentials: "omit" });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  } finally {
    done();
  }
}

/**
 * GET /api/v1/pipelines when base URL is configured.
 * @returns {Promise<{ data: unknown[] } | null>}
 */
export async function fetchPipelines(timeoutMs = 15000) {
  if (!isVeritasApiConfigured()) return null;
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/pipelines`, {
      signal,
      credentials: "omit",
      headers: { Accept: "application/json" },
    });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  } finally {
    done();
  }
}

export { isVeritasApiConfigured, VERITAS_API_BASE_URL };
