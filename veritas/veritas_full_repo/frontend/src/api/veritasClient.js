import { VERITAS_API_BASE_URL, isVeritasApiConfigured } from "../config.js";

const TOKEN_STORAGE_KEY = "veritas.authToken";

export function getAuthToken() {
  try {
    return typeof localStorage !== "undefined" ? localStorage.getItem(TOKEN_STORAGE_KEY) : null;
  } catch {
    return null;
  }
}

export function setAuthToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* ignore quota / privacy errors */
  }
}

export function clearAuthToken() {
  setAuthToken(null);
}

function abortAfter(ms) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  return { signal: c.signal, done: () => clearTimeout(t) };
}

function authHeaders(extra = {}) {
  const token = getAuthToken();
  const h = { Accept: "application/json", ...extra };
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

function parseJsonSafe(text) {
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return null;
  }
}

function formatErrorBody(j, text, status, statusText) {
  const detail = j?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d))).join("; ");
  }
  return text || statusText || `HTTP ${status}`;
}

/**
 * Core fetch wrapper used by all client functions below.
 * Attaches the bearer token automatically and normalizes JSON / error shapes.
 */
async function apiFetch(path, { method = "GET", body, timeoutMs = 15000, configRequired = true } = {}) {
  if (configRequired && !isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL (e.g. /api/v1 for the Vite proxy)." };
  }
  const { signal, done } = abortAfter(timeoutMs);
  try {
    const init = {
      method,
      credentials: "omit",
      headers: authHeaders(body !== undefined ? { "Content-Type": "application/json" } : {}),
      signal,
    };
    if (body !== undefined) init.body = JSON.stringify(body);
    const r = await fetch(`${VERITAS_API_BASE_URL}${path}`, init);
    const text = await r.text();
    const j = parseJsonSafe(text);
    if (!r.ok) {
      return { ok: false, status: r.status, message: formatErrorBody(j, text, r.status, r.statusText) };
    }
    return { ok: true, data: j?.data ?? j };
  } catch (e) {
    return { ok: false, message: e?.name === "AbortError" ? "Request timed out." : e?.message || "Network error" };
  } finally {
    done();
  }
}

/* ───────────── auth ───────────── */

/**
 * GET /api/v1/auth/mode — { enabled, mode }. Used by LoginGate.
 */
export async function fetchAuthMode(timeoutMs = 5000) {
  return apiFetch("/auth/mode", { timeoutMs });
}

/**
 * POST /api/v1/auth/login — returns { access_token, user }. Stores token on success.
 */
export async function login(email, password, timeoutMs = 15000) {
  const r = await apiFetch("/auth/login", { method: "POST", body: { email, password }, timeoutMs });
  if (!r.ok) return r;
  // Login endpoint returns TokenResponse directly (not wrapped in { data: ... }).
  const payload = r.data || {};
  const token = payload.access_token;
  if (token) setAuthToken(token);
  return { ok: true, data: payload };
}

/**
 * POST /api/v1/auth/register — role is always "researcher" server-side.
 */
export async function register(email, password, fullName, timeoutMs = 15000) {
  const body = { email, password, full_name: fullName || null };
  const r = await apiFetch("/auth/register", { method: "POST", body, timeoutMs });
  if (!r.ok) return r;
  const payload = r.data || {};
  const token = payload.access_token;
  if (token) setAuthToken(token);
  return { ok: true, data: payload };
}

/**
 * GET /api/v1/auth/me — { data: { email, role, ... } }.
 */
export async function fetchCurrentUser(timeoutMs = 10000) {
  return apiFetch("/auth/me", { timeoutMs });
}

export function logout() {
  clearAuthToken();
}

/**
 * GET /api/v1/auth/tokens — current user's PATs (no plaintext).
 */
export async function fetchApiTokens(timeoutMs = 15000) {
  const r = await apiFetch("/auth/tokens", { timeoutMs });
  if (!r.ok) return r;
  return { ok: true, data: Array.isArray(r.data) ? r.data : [] };
}

/**
 * POST /api/v1/auth/tokens — returns { data: <item>, token: <plaintext shown once> }.
 */
export async function createApiToken({ label, expiresInDays }, timeoutMs = 15000) {
  const body = { label };
  if (expiresInDays) body.expires_in_days = Number(expiresInDays);
  const r = await apiFetch("/auth/tokens", { method: "POST", body, timeoutMs });
  if (!r.ok) return r;
  // The endpoint returns the wrapper { data: ..., token: ... } directly (not nested in another data).
  return { ok: true, data: r.data };
}

/**
 * DELETE /api/v1/auth/tokens/{id} — revoke. 204 on success.
 */
export async function revokeApiToken(id, timeoutMs = 10000) {
  return apiFetch(`/auth/tokens/${encodeURIComponent(String(id))}`, { method: "DELETE", timeoutMs });
}

/* ───────────── admin: users + audit ───────────── */

/**
 * GET /api/v1/admin/users — admin-only. Returns rows of {email, role, is_active, full_name}.
 */
export async function fetchAdminUsers(timeoutMs = 15000) {
  const r = await apiFetch("/admin/users", { timeoutMs });
  if (!r.ok) return r;
  return { ok: true, data: Array.isArray(r.data) ? r.data : [] };
}

/**
 * PATCH /api/v1/admin/users/{email}/role — change role to admin|researcher.
 */
export async function setUserRole(email, role, timeoutMs = 15000) {
  return apiFetch(`/admin/users/${encodeURIComponent(email)}/role`, {
    method: "PATCH",
    body: { role },
    timeoutMs,
  });
}

/**
 * POST /api/v1/admin/users/{email}/reset-password — returns { data: { email, password } }
 * where password is plaintext shown ONCE; clients must deliver it out-of-band.
 */
export async function resetUserPassword(email, timeoutMs = 30000) {
  return apiFetch(`/admin/users/${encodeURIComponent(email)}/reset-password`, {
    method: "POST",
    timeoutMs,
  });
}

/* ───────────── notifications ───────────── */

/**
 * GET /api/v1/notifications?unread_only=&limit=
 */
export async function fetchNotifications({ unreadOnly = false, limit = 50 } = {}, timeoutMs = 15000) {
  const params = new URLSearchParams();
  if (unreadOnly) params.set("unread_only", "true");
  if (limit) params.set("limit", String(limit));
  return apiFetch(`/notifications?${params.toString()}`, { timeoutMs });
}

export async function markNotificationRead(id, timeoutMs = 10000) {
  return apiFetch(`/notifications/${encodeURIComponent(String(id))}/read`, { method: "POST", timeoutMs });
}

export async function markAllNotificationsRead(timeoutMs = 10000) {
  return apiFetch("/notifications/read-all", { method: "POST", timeoutMs });
}

/**
 * GET /api/v1/admin/audit?limit=&action=&actor_email=&subject_id=
 */
export async function fetchAuditEvents({ limit = 100, action, actorEmail, subjectId } = {}, timeoutMs = 15000) {
  const params = new URLSearchParams();
  if (limit) params.set("limit", String(limit));
  if (action) params.set("action", action);
  if (actorEmail) params.set("actor_email", actorEmail);
  if (subjectId) params.set("subject_id", subjectId);
  const r = await apiFetch(`/admin/audit?${params.toString()}`, { timeoutMs });
  if (!r.ok) return r;
  return { ok: true, data: Array.isArray(r.data) ? r.data : [] };
}

/* ───────────── pipelines ───────────── */

export async function fetchPipelines(timeoutMs = 15000) {
  if (!isVeritasApiConfigured()) return null;
  const r = await apiFetch("/pipelines", { timeoutMs });
  if (!r.ok) return null;
  // Preserve legacy contract: returns `{ data: [...] }` or null.
  return { data: r.data ?? [] };
}

/* ───────────── hpc ───────────── */

export async function fetchHpcSummary(timeoutMs = 15000) {
  return apiFetch("/hpc/summary", { timeoutMs });
}

export async function connectHpc(payload, timeoutMs = 60000) {
  return apiFetch("/hpc/connect", { method: "POST", body: payload, timeoutMs });
}

export async function testHpcConnection(payload, timeoutMs = 60000) {
  return apiFetch("/hpc/test-connection", { method: "POST", body: payload, timeoutMs });
}

/* ───────────── jobs ───────────── */

export async function submitSlurmJob(requestId, body, timeoutMs = 120000) {
  return apiFetch(`/jobs/submit/${encodeURIComponent(String(requestId))}`, {
    method: "POST",
    body,
    timeoutMs,
  });
}

export async function previewSlurmJob(requestId, body, timeoutMs = 90000) {
  return apiFetch(`/jobs/preview/${encodeURIComponent(String(requestId))}`, {
    method: "POST",
    body,
    timeoutMs,
  });
}

/**
 * GET /api/v1/jobs/{job_id}/logs?stream=stdout|stderr.
 * Returns the last ~256 KB; `data.truncated` says whether the head was dropped.
 */
export async function fetchJobLogs(jobId, stream = "stdout", timeoutMs = 30000) {
  const s = stream === "stderr" ? "stderr" : "stdout";
  return apiFetch(`/jobs/${encodeURIComponent(String(jobId))}/logs?stream=${s}`, { timeoutMs });
}

/* ───────────── reports ───────────── */

/**
 * GET /api/v1/reports/{request_id} — full report detail including artifacts.
 */
export async function fetchReportDetail(requestId, timeoutMs = 15000) {
  return apiFetch(`/reports/${encodeURIComponent(String(requestId))}`, { timeoutMs });
}

/**
 * Download a report artifact (pdf/json/csv/html) as a blob, attaching the
 * bearer token, and trigger a browser save.
 *
 * Returns { ok, status?, message? } so callers can render an inline error.
 */
export async function downloadReportFile(requestId, fmt, timeoutMs = 60000) {
  if (!isVeritasApiConfigured()) {
    return { ok: false, message: "Set VITE_VERITAS_API_BASE_URL." };
  }
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const r = await fetch(
      `${VERITAS_API_BASE_URL}/reports/${encodeURIComponent(String(requestId))}/download/${encodeURIComponent(fmt)}/file`,
      {
        method: "GET",
        credentials: "omit",
        headers: authHeaders(),
        signal: controller.signal,
      },
    );
    if (!r.ok) {
      const text = await r.text();
      const j = parseJsonSafe(text);
      return { ok: false, status: r.status, message: formatErrorBody(j, text, r.status, r.statusText) };
    }
    const blob = await r.blob();
    // Filename: prefer the Content-Disposition the server sets.
    let filename = `${requestId}-report.${fmt.toLowerCase()}`;
    const dispo = r.headers.get("Content-Disposition") || "";
    const m = /filename="?([^";]+)"?/i.exec(dispo);
    if (m) filename = m[1];
    if (typeof document !== "undefined") {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    return { ok: true };
  } catch (e) {
    return { ok: false, message: e?.name === "AbortError" ? "Download timed out." : e?.message || "Network error" };
  } finally {
    clearTimeout(t);
  }
}

/* ───────────── leaderboard ───────────── */

/**
 * GET /api/v1/leaderboard — published entries (consented runs).
 */
export async function fetchLeaderboard(timeoutMs = 15000) {
  const r = await apiFetch("/leaderboard", { timeoutMs });
  if (!r.ok) return r;
  return { ok: true, data: Array.isArray(r.data) ? r.data : [] };
}

/* ───────────── requests ───────────── */

export async function fetchEvaluationRequests(timeoutMs = 15000) {
  const r = await apiFetch("/requests", { timeoutMs });
  if (!r.ok) return r;
  return { ok: true, data: Array.isArray(r.data) ? r.data : [] };
}

export async function createEvaluationRequest(body, timeoutMs = 30000) {
  return apiFetch("/requests", { method: "POST", body, timeoutMs });
}

export { isVeritasApiConfigured, VERITAS_API_BASE_URL };
