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

const SESSION_KEY = "emo_session_token";
const RETRY_STATUSES = new Set([429, 502, 503, 504]);

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
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

async function probePing(base, timeoutMs = 20000) {
  const url = base ? `${base}/api/ping` : "/api/ping";
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, {
      credentials: "include",
      cache: "no-store",
      signal: ctrl.signal,
    });
    if (!r.ok) return null;
    const data = await r.json().catch(() => ({}));
    return { base: base || "same-origin", google: !!data.google };
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
  throw lastErr || new Error("Service momentanément indisponible");
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
    const canRetry = !cfg._emoRetried && (RETRY_STATUSES.has(status) || !err.response);
    if (canRetry) {
      const bases = backendCandidates();
      const current = getActiveBase();
      const next = bases.find((b) => b && b !== current) || bases[0];
      if (next !== undefined) {
        cfg._emoRetried = true;
        activeBase = next || activeBase;
        cfg.baseURL = getApiBase();
        await sleep(status === 429 ? 2500 : 800);
        return http.request(cfg);
      }
    }
    if (status === 429) {
      err.message = "Service momentanément saturé. Réessaie dans quelques secondes.";
    } else if (!err.response) {
      err.message = "Connexion impossible pour le moment. Vérifie ta connexion et réessaie.";
    }
    return Promise.reject(err);
  }
);

export async function streamChat({ conversation_id, content, mode, model_preference, use_agent_tools, onEvent, signal }) {
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
    finish({ type: "error", content: "Connexion impossible pour le moment. Réessaie." });
    return;
  }
  if (resp.status === 429) {
    finish({ type: "error", content: "Service momentanément saturé. Réessaie dans quelques secondes." });
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
      finish({ type: "error", content: "Réponse interrompue. Réessaie." });
    }
  } catch (e) {
    if (e?.name === "AbortError") {
      finish({ type: "cancelled" });
      return;
    }
    finish({
      type: "error",
      content: e?.message?.includes("network") || e?.name === "TypeError"
        ? "Connexion perdue. Réessaie."
        : (e?.message || "Erreur de connexion"),
    });
  }
}

const BOOT_MESSAGES = [
  "Préparation de ton espace…",
  "Connexion sécurisée…",
  "Presque prêt…",
  "Encore quelques secondes…",
];

/**
 * Réveille le backend (cold-start HF). Jusqu'à ~90s, messages pro sans jargon technique.
 * @returns {{ ok: boolean, google?: boolean, base?: string }}
 */
export async function wakeBackend(options = {}) {
  const maxWaitMs = options.maxWaitMs ?? 90000;
  const onProgress = options.onProgress;
  const start = Date.now();
  let attempt = 0;

  while (Date.now() - start < maxWaitMs) {
    attempt += 1;
    onProgress?.({
      attempt,
      elapsed: Date.now() - start,
      message: BOOT_MESSAGES[Math.min(attempt - 1, BOOT_MESSAGES.length - 1)],
    });

    for (const base of backendCandidates()) {
      const hit = await probePing(base, attempt <= 2 ? 25000 : 15000);
      if (hit) {
        if (base) activeBase = base;
        return { ok: true, google: hit.google, base: hit.base };
      }
    }

    const wait = Math.min(2000 + attempt * 600, 8000);
    await sleep(wait);
  }

  return { ok: false };
}
