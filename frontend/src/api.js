/**
 * api.js – thin wrapper around the FastAPI backend.
 *
 * All functions throw on non-2xx so callers can catch + display errors.
 * The JWT is stored in localStorage under "dfr_token".
 */

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Token helpers ───────────────────────────────────────────────────────────

export function saveSession(tokenPayload) {
  localStorage.setItem("dfr_token", tokenPayload.access_token);
  localStorage.setItem("dfr_role", tokenPayload.role);
  localStorage.setItem("dfr_username", tokenPayload.username);
}

export function clearSession() {
  localStorage.removeItem("dfr_token");
  localStorage.removeItem("dfr_role");
  localStorage.removeItem("dfr_username");
}

export function getToken() {
  return localStorage.getItem("dfr_token");
}

export function getRole() {
  return localStorage.getItem("dfr_role") || "";
}

export function getUsername() {
  return localStorage.getItem("dfr_username") || "";
}

export function isLoggedIn() {
  return !!getToken();
}

// ─── Core fetch wrapper ──────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Hard timeout – fail fast instead of waiting for browser default (~2 min)
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 8000); // 8 s

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Server not responding. Is the backend running?");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || JSON.stringify(err);
    } catch (_) {/* ignore */}
    throw new Error(`${res.status}: ${detail}`);
  }

  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

// ─── Auth ────────────────────────────────────────────────────────────────────

/**
 * Login with username/password (OAuth2 form).
 * Returns { access_token, token_type, role, username }.
 */
export async function login(username, password) {
  const form = new FormData();
  form.append("username", username);
  form.append("password", password);
  const data = await apiFetch("/auth/login", { method: "POST", body: form });
  saveSession(data);
  return data;
}

export async function register(username, password, role = "rescuer") {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, role }),
  });
}

// ─── Persons ─────────────────────────────────────────────────────────────────

/**
 * Submit a found person record from the rescuer form.
 */
export async function submitFoundPerson(payload) {
  return apiFetch("/persons/found", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Submit a missing person report from a family member.
 */
export async function submitMissingPerson(payload) {
  return apiFetch("/persons/missing", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * List persons. type: "found" | "missing". q: name substring.
 */
export async function listPersons({ type, q, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (q) params.set("q", q);
  params.set("limit", limit);
  params.set("offset", offset);
  return apiFetch(`/persons?${params}`);
}

// ─── Matches ─────────────────────────────────────────────────────────────────

/**
 * List match candidates.
 * state: "under_review" | "verified" | "rejected"
 * minScore: 0–1
 */
export async function listMatches({ state, minScore = 0, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  params.set("min_score", minScore);
  params.set("limit", limit);
  params.set("offset", offset);
  return apiFetch(`/matches?${params}`);
}

export async function verifyMatch(matchId, note = "") {
  return apiFetch(`/matches/${matchId}/verify`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function rejectMatch(matchId, note = "") {
  return apiFetch(`/matches/${matchId}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function runMatching() {
  return apiFetch("/matches/run", { method: "POST" });
}

// ─── Audit ───────────────────────────────────────────────────────────────────

export async function getAuditLog() {
  return apiFetch("/audit");
}
