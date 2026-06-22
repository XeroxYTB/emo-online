import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const BACKEND_FALLBACK = (process.env.REACT_APP_BACKEND_FALLBACK_URL || "").replace(/\/$/, "");
export { BACKEND_URL, BACKEND_FALLBACK };

/** Base URL active après wake / fallback (sans /api). */
let activeBase = BACKEND_URL || "";

export function getActiveBase() {
  return activeBase || BACKEND_URL || "";
}

export function getApiBase() {
  const base = getActiveBase();
  return base ? `${base}/api` : "/api";
}

/** @deprecated Préférer getApiBase() — suit le backend actif après wake. */
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

/** Dernière sonde API réussie (évite wake inutile avant login). */
let apiReachable = false;

export function isApiReachable() {
  return apiReachable;
}
const RETRY_STATUSES = new Set([429, 502, 503, 504]);
const AUTH_MAX_ATTEMPTS = 8;

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

function isRetriableStatus(status) {
  return Boolean(status && RETRY_STATUSES.has(status));
}

export function formatApiError(err, fallback = "Erreur réseau") {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;
  if (status === 429) return "API saturée (Hugging Face). Attendez 2 min puis réessayez.";
  if (status === 401 || status === 403) {
    return typeof detail === "string" ? detail : "Identifiants incorrects";
  }
  if (typeof detail === "string") return detail;
  if (!err?.response) {
    return "API injoignable. Le serveur HF démarre peut‑être — attendez 1 min puis réessayez.";
  }
  return err?.message || fallback;
}

/** Requêtes auth avec retries (HF cold start / 429 uniquement). */
export async function authRequest(requestFn, options = {}) {
  const maxAttempts = options.maxAttempts ?? 4;
  let lastErr;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await requestFn();
    } catch (err) {
      lastErr = err;
      const status = err?.response?.status;
      if (!status || !isRetriableStatus(status)) break;
      if (attempt >= maxAttempts - 1) break;
      await sleep(status === 429 ? 2500 + attempt * 1200 : 1200);
    }
  }
  throw lastErr;
}

function backendCandidates() {
  const seen = new Set();
  const out = [];
  for (const b of [activeBase, BACKEND_URL, BACKEND_FALLBACK]) {
    if (b && !seen.has(b)) {
      seen.add(b);
      out.push(b);
    }
  }
  if (!out.length) out.push("");
  return out;
}

async function probePing(base, timeoutMs = 8000) {
  const url = base ? `${base}/api/ping` : "/api/ping";
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      credentials: "include",
      cache: "no-store",
      signal: ctrl.signal,
    });
    if (r.ok) {
      const data = await r.json().catch(() => ({}));
      apiReachable = true;
      return { base: base || "same-origin", google: !!data.google, waking: false };
    }
    // HF cold start / rate limit : le serveur répond quand même — ne pas bloquer le login 90s
    if (RETRY_STATUSES.has(r.status) || r.status === 429) {
      if (base) activeBase = base;
      apiReachable = true;
      return { base: base || "same-origin", google: false, waking: true };
    }
    return null;
  } catch (_) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function _fetchWithFallback(path, options = {}) {
  let lastErr;
  for (const base of backendCandidates()) {
    const url = base ? `${base}/api${path}` : `/api${path}`;
    try {
      const r = await fetch(url, options);
      if (RETRY_STATUSES.has(r.status)) {
        await sleep(1500);
        continue;
      }
      if (r.ok && base) activeBase = base;
      return r;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Service indisponible");
}

export function saveSessionToken(token) {
  if (!token) return;
  try { localStorage.setItem(SESSION_KEY, token); } catch (_) {}
}

export function clearSessionToken() {
  try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
}

export function getSessionToken() {
  try { return localStorage.getItem(SESSION_KEY) || ""; } catch (_) { return ""; }
}

/** POST JSON via fetch — plus fiable que axios pour l'auth cross-origin (HF). */
export async function apiPostJson(path, data, options = {}) {
  const timeout = options.timeout ?? 20000;
  const base = getActiveBase() || BACKEND_URL;
  if (!base) throw new Error("API non configurée");
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  const token = getSessionToken();
  const headers = { "Content-Type": "application/json", Accept: "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Emo-Session"] = token;
  }
  try {
    const res = await fetch(`${base}/api${path}`, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(data),
      signal: ctrl.signal,
    });
    activeBase = base;
    apiReachable = true;
    let json = {};
    try { json = await res.json(); } catch (_) {}
    if (!res.ok) {
      const err = new Error(typeof json.detail === "string" ? json.detail : "Erreur API");
      err.response = { status: res.status, data: json };
      throw err;
    }
    return { data: json, status: res.status };
  } catch (e) {
    if (e?.name === "AbortError") {
      const err = new Error("Délai dépassé — le serveur HF est lent.");
      err.response = null;
      throw err;
    }
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export const http = axios.create({
  baseURL: getApiBase(),
  withCredentials: true,
  timeout: 45000,
});

http.interceptors.request.use((config) => {
  config.baseURL = getApiBase();
  const token = getSessionToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    config.headers["X-Emo-Session"] = token;
  }
  return config;
});

http.interceptors.response.use(
  (res) => {
    const base = (res.config.baseURL || "").replace(/\/api\/?$/, "");
    if (base && base !== "/") activeBase = base;
    return res;
  },
  async (err) => {
    const cfg = err.config || {};
    const status = err.response?.status;
    const retries = cfg._emoRetryCount || 0;
    const maxRetries = cfg._emoMaxRetries ?? 4;
    const skipRetry = cfg._emoSkipRetry === true;
    const canRetry = !skipRetry && retries < maxRetries && status && isRetriableStatus(status);
    if (canRetry) {
      const bases = backendCandidates();
      const current = getActiveBase();
      const next = bases.find((b) => b && b !== current) || bases[0];
      if (next !== undefined) {
        cfg._emoRetryCount = retries + 1;
        activeBase = next || activeBase;
        cfg.baseURL = getApiBase();
        await sleep(status === 429 ? 2200 + retries * 900 : 800);
        return http.request(cfg);
      }
    }
    if (status === 429) {
      err.message = "API saturée (Hugging Face). Attendez 2 min puis réessayez.";
    } else if (!err.response) {
      err.message = "API injoignable. Le serveur HF démarre peut‑être — attendez 1 min puis réessayez.";
    }
    return Promise.reject(err);
  }
);

export async function streamChat({ conversation_id, content, images, image_media_types, mode, model_preference, use_agent_tools, onEvent, signal }) {
  const headers = { "Content-Type": "application/json", Accept: "text/event-stream" };
  const token = getSessionToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
    headers["X-Emo-Session"] = token;
  }
  let terminal = false;
  const finish = (evt) => {
    if (evt?.type === "done" || evt?.type === "error" || evt?.type === "cancelled") terminal = true;
    onEvent?.(evt);
  };
  let resp;
  try {
    resp = await _fetchWithFallback("/chat/stream", {
      method: "POST",
      credentials: "include",
      headers,
      signal,
      body: JSON.stringify({
        conversation_id,
        content,
        images: images?.length ? images : undefined,
        image_media_types: image_media_types?.length ? image_media_types : undefined,
        mode,
        model_preference: model_preference || "auto",
        use_agent_tools: use_agent_tools !== false,
      }),
    });
  } catch (e) {
    if (e?.name === "AbortError") {
      finish({ type: "cancelled" });
      return;
    }
    finish({ type: "error", content: "Connexion impossible." });
    return;
  }
  if (resp.status === 429) {
    finish({ type: "error", content: "Service saturé. Réessayez." });
    return;
  }
  if (!resp.ok) {
    let msg = "Une erreur est survenue.";
    try {
      const err = await resp.json();
      msg = err.detail?.message || err.detail || err.message || msg;
      if (typeof msg === "object") msg = msg.message || JSON.stringify(msg);
    } catch (_) {}
    finish({ type: "error", content: msg });
    return;
  }
  if (!resp.body) {
    finish({ type: "error", content: "Réponse vide du serveur." });
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const p of parts) {
        const line = p.trim();
        if (!line.startsWith("data:")) continue;
        const json = line.slice(5).trim();
        if (!json) continue;
        try {
          finish(JSON.parse(json));
        } catch (_) {
          // ignore malformed
        }
      }
    }
    if (!terminal) {
      finish({ type: "error", content: "Réponse interrompue." });
    }
  } catch (e) {
    if (e?.name === "AbortError") {
      finish({ type: "cancelled" });
      return;
    }
    finish({
      type: "error",
      content: e?.message?.includes("network") || e?.name === "TypeError"
        ? "Connexion perdue."
        : (e?.message || "Erreur de connexion"),
    });
  }
}

const BOOT_MESSAGE = "Chargement…";
export async function wakeBackend(options = {}) {
  const maxWaitMs = options.maxWaitMs ?? 35000;
  const onProgress = options.onProgress;
  const start = Date.now();
  let attempt = 0;
  let sawWaking = false;

  while (Date.now() - start < maxWaitMs) {
    attempt += 1;
    onProgress?.({
      attempt,
      elapsed: Date.now() - start,
      message: BOOT_MESSAGE,
    });

    for (const base of backendCandidates()) {
      const hit = await probePing(base, attempt <= 1 ? 8000 : 5000);
      if (hit) {
        if (base) activeBase = base;
        if (hit.waking) sawWaking = true;
        return {
          ok: true,
          google: !!hit.google,
          base: hit.base,
          waking: !!hit.waking,
        };
      }
    }

    const wait = Math.min(2000 + attempt * 600, 8000);
    await sleep(wait);
  }

  if (sawWaking) {
    return { ok: true, google: false, waking: true };
  }
  return { ok: false };
}
