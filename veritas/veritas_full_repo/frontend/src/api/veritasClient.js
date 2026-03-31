import { VERITAS_API_BASE_URL, isVeritasApiConfigured } from "../config.js";

function abortAfter(ms) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  return { signal: c.signal, done: () => clearTimeout(t) };
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

/**
 * POST /api/v1/jobs/preview/{request_id} — same body as submit; no SSH/sbatch.
 * @param {string|number} requestId
 * @param {Record<string, unknown>} body SlurmJobSubmitRequest JSON
 * @returns {Promise<{ ok: true, data: object } | { ok: false, status?: number, message: string }>}
 */
/**
 * GET /api/v1/hpc/summary — queue counts, active connection, hpc_mode.
 */
export async function fetchHpcSummary(timeoutMs = 15000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/hpc/summary`, {
      signal,
      credentials: "omit",
      headers: { Accept: "application/json" },
    });
    const text = await r.text();
    let j = null;
    try {
      j = text ? JSON.parse(text) : null;
    } catch {
      j = null;
    }
    if (!r.ok) {
      const detail = j?.detail;
      const msg = typeof detail === "string" ? detail : text || r.statusText;
      return { ok: false, status: r.status, message: msg };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    return { ok: false, message: e?.name === "AbortError" ? "Timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

/**
 * POST /api/v1/hpc/connect — SSH validation + persist active connection.
 */
export async function connectHpc(payload, timeoutMs = 60000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/hpc/connect`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    const text = await r.text();
    let j = null;
    try {
      j = text ? JSON.parse(text) : null;
    } catch {
      j = null;
    }
    if (!r.ok) {
      const detail = j?.detail;
      let msg;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join("; ");
      else msg = text || r.statusText || `HTTP ${r.status}`;
      return { ok: false, status: r.status, message: msg };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    return { ok: false, message: e?.name === "AbortError" ? "Timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

/**
 * POST /api/v1/hpc/test-connection — SSH only, no DB.
 */
export async function testHpcConnection(payload, timeoutMs = 60000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/hpc/test-connection`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    const text = await r.text();
    let j = null;
    try {
      j = text ? JSON.parse(text) : null;
    } catch {
      j = null;
    }
    if (!r.ok) {
      const detail = j?.detail;
      let msg;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join("; ");
      else msg = text || r.statusText || `HTTP ${r.status}`;
      return { ok: false, status: r.status, message: msg };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    return { ok: false, message: e?.name === "AbortError" ? "Timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

/**
 * POST /api/v1/jobs/submit/{request_id} — Slurm job (SSH/sbatch when HPC_MODE=slurm).
 */
export async function submitSlurmJob(requestId, body, timeoutMs = 120000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1 for the Vite proxy)." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/jobs/submit/${encodeURIComponent(String(requestId))}`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    const text = await r.text();
    let j = null;
    try {
      j = text ? JSON.parse(text) : null;
    } catch {
      j = null;
    }
    if (!r.ok) {
      const detail = j?.detail;
      let msg;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join("; ");
      else msg = text || r.statusText || `HTTP ${r.status}`;
      return { ok: false, status: r.status, message: msg };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    const name = e?.name;
    return { ok: false, message: name === "AbortError" ? "Submit timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

export async function previewSlurmJob(requestId, body, timeoutMs = 90000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1 for the Vite proxy)." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const r = await fetch(`${VERITAS_API_BASE_URL}/jobs/preview/${encodeURIComponent(String(requestId))}`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      signal,
    });
    const text = await r.text();
    let j = null;
    try {
      j = text ? JSON.parse(text) : null;
    } catch {
      j = null;
    }
    if (!r.ok) {
      const detail = j?.detail;
      let msg;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail)) msg = detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join("; ");
      else msg = text || r.statusText || `HTTP ${r.status}`;
      return { ok: false, status: r.status, message: msg };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    const name = e?.name;
    return { ok: false, message: name === "AbortError" ? "Preview request timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

export { isVeritasApiConfigured, VERITAS_API_BASE_URL };
