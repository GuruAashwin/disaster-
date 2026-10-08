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
 * Get the URL for a person's image
 */
export function getPersonImageUrl(personId) {
  return `${BASE}/persons/${personId}/image`;
}

/**
 * Submit a found person record from the rescuer form.
 * Optionally includes an image.
 */
export async function submitFoundPerson(payload, imageFile = null) {
  if (imageFile) {
    // Use FormData for image upload
    const formData = new FormData();
    Object.keys(payload).forEach(key => {
      formData.append(key, payload[key]);
    });
    formData.append('image', imageFile);
    
    const token = getToken();
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s for files
    
    try {
      const res = await fetch(`${BASE}/persons/found`, {
        method: "POST",
        headers,
        body: formData,
        signal: controller.signal,
      });
      
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const err = await res.json();
          detail = err.detail || JSON.stringify(err);
        } catch (_) {}
        throw new Error(`${res.status}: ${detail}`);
      }
      
      return res.json();
    } finally {
      clearTimeout(timeoutId);
    }
  } else {
    // Use JSON for text-only
    return apiFetch("/persons/found", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
}

/**
 * Submit a missing person report from a family member.
 * Optionally includes an image.
 */
export async function submitMissingPerson(payload, imageFile = null) {
  if (imageFile) {
    // Use FormData for image upload
    const formData = new FormData();
    Object.keys(payload).forEach(key => {
      formData.append(key, payload[key]);
    });
    formData.append('image', imageFile);
    
    const token = getToken();
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s for files
    
    try {
      const res = await fetch(`${BASE}/persons/missing`, {
        method: "POST",
        headers,
        body: formData,
        signal: controller.signal,
      });
      
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const err = await res.json();
          detail = err.detail || JSON.stringify(err);
        } catch (_) {}
        throw new Error(`${res.status}: ${detail}`);
      }
      
      return res.json();
    } finally {
      clearTimeout(timeoutId);
    }
  } else {
    // Use JSON for text-only
    return apiFetch("/persons/missing", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
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

// ─── Video Clothing Search ──────────────────────────────────────────────────────

/**
 * Process all videos in the video_files directory into frames
 * 
 * @returns {Promise<Object>} - Processing results
 * @throws {Error} - On server error
 */
export async function processVideos() {
  return apiFetch("/videos/process", {
    method: "POST",
  });
}

/**
 * Search authorized disaster video footage for possible clothing matches.
 * 
 * IMPORTANT: This searches clothing only. Results are "possible sightings" 
 * that require human verification. Clothing similarity is NOT identity verification.
 * 
 * @param {Object} payload - Search criteria
 * @param {string|null} payload.upper_body_color - Shirt color (14 supported colors)
 * @param {string|null} payload.lower_body_color - Pants color (14 supported colors)
 * @param {number} payload.min_match_score - Threshold 0-100 (default 60)
 * @param {number} payload.max_results - Limit results 1-1000 (default 10)
 * @returns {Promise<Object>} - Results with candidates array
 * @throws {Error} - On validation or server error
 */
export async function searchVideoByClothing(payload) {
  // Ensure at least one color is provided
  if (!payload.upper_body_color && !payload.lower_body_color) {
    throw new Error("At least one of shirt or pants color must be selected.");
  }
  
  return apiFetch("/videos/search-by-clothing", {
    method: "POST",
    body: JSON.stringify({
      upper_body_color: payload.upper_body_color || null,
      lower_body_color: payload.lower_body_color || null,
    }),
  });
}
